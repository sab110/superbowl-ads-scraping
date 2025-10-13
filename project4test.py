import os
import re
import json
import time
import subprocess
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from lxml import html

# =========================
# Config
# =========================
CAMPAIGN_LIST_FILE = "professional_campaign_urls.txt"  # one URL per line
OUTPUT_ROOT = Path(r"adsoftheworld\professional")
HEADLESS = True
REQUEST_TIMEOUT = 20
PAGE_LOAD_RETRIES = 3
SLEEP_BETWEEN_PAGES = 1  # seconds
YT_DLP_COOKIES = None  # e.g., "cookies.txt" if you need auth-only YouTube videos

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.adsoftheworld.com/"
}

DIRECT_VIDEO_EXTS = (".mp4", ".webm", ".mkv", ".mov")

# =========================
# Helpers
# =========================

def safe_slug(s: str, max_len: int = 120) -> str:
    if not s:
        return "untitled"
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("/", "-")
    s = re.sub(r"[^A-Za-z0-9 _\-.()]+", "", s)
    s = s.strip().replace(" ", "_")
    return s[:max_len] if max_len else s

def get_selenium_driver() -> webdriver.Chrome:
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0")
    try:
        return webdriver.Chrome(options=options)
    except WebDriverException as e:
        raise RuntimeError(f"Failed to start Chrome driver: {e}")

def robust_get(driver: webdriver.Chrome, url: str, retries: int = PAGE_LOAD_RETRIES) -> Optional[str]:
    for attempt in range(1, retries + 1):
        try:
            driver.get(url)
            return driver.page_source
        except Exception as e:
            print(f"[WARN] Load attempt {attempt}/{retries} failed for {url}: {e}")
            time.sleep(1.5 * attempt)
    print(f"[ERROR] Could not load page after {retries} attempts: {url}")
    return None

def extract_text_or_none(node) -> Optional[str]:
    try:
        return node.get_text(strip=True) if node else None
    except Exception:
        return None

def parse_youtube_id(iframe_src: str) -> Optional[str]:
    try:
        u = urlparse(iframe_src)
        if "youtube.com" in u.netloc:
            if u.path.startswith("/embed/"):
                return u.path.split("/")[2]
            qs = parse_qs(u.query)
            return (qs.get("v") or [None])[0]
        if "youtu.be" in u.netloc:
            return u.path.lstrip("/")
    except Exception:
        pass
    return None

def parse_vimeo_id(iframe_src: str) -> Optional[str]:
    try:
        u = urlparse(iframe_src)
        if "vimeo.com" in u.netloc:
            parts = [p for p in u.path.split("/") if p]
            return parts[-1] if parts else None
    except Exception:
        pass
    return None

def download_with_requests(url: str, out_path: Path) -> bool:
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
        r.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"[WARN] Failed to download {url}: {e}")
        return False

def download_video_yt_dlp(video_url: str, output_path: Path) -> bool:
    try:
        cmd = [
            "yt-dlp",
            "--referer", "https://www.adsoftheworld.com/",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", str(output_path)
        ]
        if YT_DLP_COOKIES and Path(YT_DLP_COOKIES).exists():
            cmd.extend(["--cookies", YT_DLP_COOKIES])
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"[WARN] yt-dlp failed for {video_url}: {e}")
        return False

def is_direct_video_url(url: str) -> bool:
    try:
        lower = url.lower()
        if any(host in lower for host in ("youtube.com", "youtu.be", "vimeo.com")):
            return False
        if any(lower.split("?")[0].endswith(ext) for ext in DIRECT_VIDEO_EXTS):
            return True
        try:
            h = requests.head(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            ct = h.headers.get("Content-Type", "").lower()
            return ct.startswith("video/") or "octet-stream" in ct
        except Exception:
            return False
    except Exception:
        return False

def download_video_requests(video_url: str, output_path: Path) -> bool:
    try:
        with requests.get(video_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"[WARN] requests download failed for {video_url}: {e}")
        return False

def download_video_preferring_requests(video_url: str, output_path: Path) -> bool:
    lower = video_url.lower()
    if "youtube.com" in lower or "youtu.be" in lower or "vimeo.com" in lower:
        return download_video_yt_dlp(video_url, output_path)
    if is_direct_video_url(video_url):
        ok = download_video_requests(video_url, output_path)
        if ok:
            return True
        return download_video_yt_dlp(video_url, output_path)
    return download_video_yt_dlp(video_url, output_path)

# NEW: skip logic
def already_downloaded(title_slug: str, expected_name: str, url: str) -> bool:
    """
    Skip if:
      - Folder exists AND
      - JSON <title_slug>.json exists AND
      - JSON has same origin.url AND same name
    """
    out_dir = OUTPUT_ROOT / title_slug
    json_file = out_dir / f"{title_slug}.json"
    if not out_dir.exists() or not json_file.exists():
        return False
    try:
        with open(json_file, "r", encoding="utf-8-sig") as f:
            existing = json.load(f)
        same_url = existing.get("origin", {}).get("url") == url
        same_name = existing.get("name") == expected_name
        if same_url and same_name:
            print(f"[SKIP] Already downloaded: {existing.get('name')} ({url})")
            return True
    except Exception as e:
        print(f"[WARN] Could not read/compare JSON for {title_slug}: {e}")
    return False

# =========================
# Core parsing per campaign
# =========================

def parse_campaign(driver: webdriver.Chrome, url: str) -> Optional[Dict[str, Any]]:
    page = robust_get(driver, url)
    if not page:
        return None

    soup = BeautifulSoup(page, "html.parser")

    title_node = soup.find("h1", class_="text-2xl karlasemibold")
    title_raw = extract_text_or_none(title_node)
    title_slug = safe_slug(title_raw)

     # Description
    try:
        description_tag = soup.find('div', class_='mb-4 whitespace-pre-line flex flex-col gap-4')
        description = "\n\n".join(p.get_text(strip=True) for p in description_tag.find_all('p')) if description_tag else None
    except Exception as e:
        print(f"Description error: {e}")
        description = None

    credits = []
    try:
        credits_div = soup.find("div", class_="col-span-2")
        if credits_div:
            tree = html.fromstring(str(credits_div))
            lines = tree.xpath("//p[text()='Credits']/following-sibling::div//p/text()")
            for line in lines:
                if ":" in line:
                    role, name = line.split(":", 1)
                    role = role.strip()
                    name = name.strip()
                    if role.lower() == "brand":
                        continue
                    if role or name:
                        credits.append({"role": role, "name": name})
    except Exception as e:
        print(f"[WARN] Failed to parse credits: {e}")

    year = None
    try:
        cd = soup.find("p", class_="mb-6 text-sm")
        cd_text = extract_text_or_none(cd) or ""
        m = re.search(r"\b(\d{4})\b", cd_text)
        year = m.group(1) if m else None
    except Exception:
        pass

    categories = {
        "brand": None,
        "agency": None,
        "countries": None,
        "category": [],
        "subCategory": []
    }
    try:
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            if "brands" in href and categories["brand"] is None:
                categories["brand"] = text
            elif "agencies" in href and categories["agency"] is None:
                categories["agency"] = text
            elif ('country' in href or 'countries' in href) and not categories['countries']:
                categories["countries"] = text
            elif "medium_types" in href:
                if text and text not in categories["category"]:
                    categories["category"].append(text)
            elif "industries" in href and not categories["subCategory"]:
                categories['subCategory'].append(text)
    except Exception as e:
        print(f"[WARN] Failed to parse categories: {e}")

    image_urls: List[str] = []
    videos: List[Dict[str, str]] = []
    try:
        for div in soup.find_all("div", class_="bg-white my-3"):
            vtag = div.find("video", src=True)
            if vtag:
                vurl = vtag.get("src")
                poster = vtag.get("poster")
                if vurl:
                    videos.append({
                        "video_url": vurl,
                        "thumbnail": poster if poster else ""
                    })
            iframe = div.find("iframe", src=True)
            if iframe:
                src = iframe["src"]
                if "youtube" in src or "youtu.be" in src:
                    vid = parse_youtube_id(src)
                    thumb = f"https://img.youtube.com/vi/{vid}/0.jpg" if vid else ""
                    videos.append({"video_url": src, "thumbnail": thumb})
                elif "vimeo" in src:
                    vid = parse_vimeo_id(src)
                    thumb = f"https://vumbnail.com/{vid}.jpg" if vid else ""
                    videos.append({"video_url": src, "thumbnail": thumb})
            img = div.find("img", src=True)
            if img and img.get("src"):
                image_urls.append(img["src"])
    except Exception as e:
        print(f"[WARN] Failed to parse media: {e}")

    output = {
        "origin": {"name": "adsoftheworld.com", "url": url},
        "name": title_raw or title_slug.replace("_", " "),
        "type": "video" if videos else "image",
        "sector": categories['subCategory'],
        "countries": categories["countries"],
        "brands": categories["brand"],
        "agency": categories["agency"],
        "year": year,
        "award": None,
        "category": categories["category"],
        "subCategory": categories["subCategory"],
        "description": description,
        "credits": credits,
        "image_urls": image_urls,
        "videos": videos,
        "tags": None,
        "product": None
    }

    return {
        "title_slug": title_slug or "untitled",
        "data": output,
        "images": image_urls,
        "videos": videos
    }

def process_and_save_campaign(result: Dict[str, Any]) -> None:
    title_slug = result["title_slug"]
    data = result["data"]
    images = result["images"]
    videos = result["videos"]

    out_dir = OUTPUT_ROOT / title_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, v in enumerate(videos, start=1):
        vurl = v.get("video_url", "")
        if not vurl:
            continue
        video_path = out_dir / f"{title_slug}_{i}.mp4"
        download_video_preferring_requests(vurl, video_path)

    for i, img_url in enumerate(images, start=1):
        if not img_url:
            continue
        img_path = out_dir / f"{title_slug}_{i}.jpg"
        download_with_requests(img_url, img_path)

    json_file = out_dir / f"{title_slug}.json"
    try:
        with open(json_file, "w", encoding="utf-8-sig") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved: {json_file}")
    except Exception as e:
        print(f"[ERROR] Failed to write JSON {json_file}: {e}")

# =========================
# Main
# =========================

def read_campaign_links(file_path: str) -> List[str]:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Campaign list file not found: {file_path}")
    urls = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls

def main():
    try:
        urls = read_campaign_links(CAMPAIGN_LIST_FILE)
        urls = urls[46605:50000]  # Limit for testing
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    if not urls:
        print("[INFO] No campaign URLs found.")
        return

    try:
        driver = get_selenium_driver()
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    try:
        for idx, url in enumerate(urls, start=1):
            print(f"\n=== ({idx}/{len(urls)}) {url} ===")
            try:
                result = parse_campaign(driver, url)
                if not result:
                    print("[WARN] Skipping campaign due to previous errors.")
                    continue

                # Skip if same folder + JSON name + URL
                expected_name = result["data"]["name"]
                if already_downloaded(result["title_slug"], expected_name, url):
                    continue

                process_and_save_campaign(result)
            except Exception as e:
                print(f"[ERROR] Unexpected error for {url}: {e}")
            time.sleep(SLEEP_BETWEEN_PAGES)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
