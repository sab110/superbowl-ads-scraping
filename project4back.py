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
from requests.adapters import HTTPAdapter, Retry
import sys
import platform

# =========================
# Config
# =========================
CAMPAIGN_LIST_FILE = "professional_urls_done.txt"  # one URL per line
OUTPUT_ROOT = Path(r"adsoftheworld\professional")
HEADLESS = True
REQUEST_TIMEOUT = 25
PAGE_LOAD_RETRIES = 3
SLEEP_BETWEEN_PAGES = 0.1  # seconds
YT_DLP_COOKIES = None  # e.g., "cookies.txt" if you need auth-only YouTube videos

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.adsoftheworld.com/"
}

DIRECT_VIDEO_EXTS = (".mp4", ".webm", ".mkv", ".mov")

# Path length/filename caps to avoid Windows MAX_PATH problems
SLUG_MAX_LEN = 80
FILEBASE_MAX_LEN = 60

# =========================
# Requests session with retries
# =========================
def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["HEAD", "GET"])
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=16, pool_maxsize=32)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(REQUEST_HEADERS)
    return s

SESSION = make_session()

# =========================
# Helpers
# =========================

def safe_slug(s: Optional[str], max_len: int = SLUG_MAX_LEN) -> str:
    if not s:
        s = "untitled"
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("/", "-")
    s = re.sub(r"[^A-Za-z0-9 _\-.()]+", "", s)
    s = s.strip().replace(" ", "_")
    return s[:max_len] if max_len else s

def short_base(s: str, max_len: int = FILEBASE_MAX_LEN) -> str:
    s = re.sub(r"[^A-Za-z0-9_\-.()]+", "", s)
    return s[:max_len] if len(s) > max_len else s

def windows_longpath(p: Path) -> str:
    """
    Convert to absolute path and prefix with \\?\ on Windows so long paths work.
    """
    if platform.system().lower().startswith("win"):
        try:
            p_abs = p if p.is_absolute() else p.resolve(strict=False)
        except Exception:
            # Fallback if resolve fails (e.g., on very deep new paths)
            p_abs = (Path.cwd() / p)
        p_str = str(p_abs)
        if p_str.startswith("\\\\?\\"):
            return p_str
        return "\\\\?\\" + p_str
    return str(p)

def get_selenium_driver() -> webdriver.Chrome:
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # Quiet software WebGL warnings
    options.add_argument("--use-gl=swiftshader")
    options.add_argument("--enable-unsafe-swiftshader")
    options.add_argument("--disable-software-rasterizer")
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
                parts = u.path.split("/")
                if len(parts) > 2 and parts[2]:
                    return parts[2]
            qs = parse_qs(u.query)
            vid = (qs.get("v") or [None])[0]
            if vid:
                return vid
        if "youtu.be" in u.netloc:
            vid = u.path.lstrip("/").split("?")[0]
            if vid:
                return vid
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

# Normalize embed/player URLs to canonical
def normalize_video_url(u: str) -> str:
    try:
        pu = urlparse(u)
        host = pu.netloc.lower()
        path = pu.path

        # YouTube embed → watch?v=ID
        if "youtube.com" in host and path.startswith("/embed/"):
            parts = path.split("/")
            if len(parts) > 2 and parts[2]:
                vid = parts[2].split("?")[0]
                return f"https://www.youtube.com/watch?v={vid}"
            # best-effort: try query 'v'
            qs = parse_qs(pu.query)
            vid = (qs.get("v") or [None])[0]
            if vid:
                return f"https://www.youtube.com/watch?v={vid}"
            return u  # fallback

        # youtu.be short → canonical watch
        if "youtu.be" in host:
            vid = path.lstrip("/").split("?")[0]
            if vid:
                return f"https://www.youtube.com/watch?v={vid}"
            return u

        # Vimeo player → https://vimeo.com/ID
        if "vimeo.com" in host and "/video/" in path:
            seg = path.split("/video/")[1]
            vid = seg.split("/")[0].split("?")[0]
            if vid:
                return f"https://vimeo.com/{vid}"
            return u

        return u
    except Exception:
        return u

def download_with_requests(url: str, out_path: Path) -> bool:
    try:
        resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        resp.raise_for_status()
        out_path_parent = out_path.parent
        out_path_parent.mkdir(parents=True, exist_ok=True)
        tmp_path = out_path.with_suffix(out_path.suffix + ".part")
        with open(windows_longpath(tmp_path), "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)
        os.replace(windows_longpath(tmp_path), windows_longpath(out_path))
        return True
    except Exception as e:
        print(f"[WARN] Failed to download {url}: {e}")
        return False

def download_video_yt_dlp(video_url: str, output_path: Path) -> bool:
    try:
        url = normalize_video_url(video_url)
        if not url or url.strip() == "" or url.lower().endswith("/embed/"):
            print(f"[WARN] Skipping yt-dlp; invalid URL after normalize: {video_url}")
            return False
        cmd = [
            "yt-dlp",
            "--referer", "https://www.adsoftheworld.com/",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", str(output_path),   # avoid \\?\ with external tools
            "--",
            url
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
            h = SESSION.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            ct = h.headers.get("Content-Type", "").lower()
            return ct.startswith("video/") or "octet-stream" in ct
        except Exception:
            return False
    except Exception:
        return False

def download_video_requests(video_url: str, output_path: Path) -> bool:
    try:
        with SESSION.get(video_url, timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = output_path.with_suffix(output_path.suffix + ".part")
            with open(windows_longpath(tmp_path), "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 512):
                    if chunk:
                        f.write(chunk)
            os.replace(windows_longpath(tmp_path), windows_longpath(output_path))
        return True
    except Exception as e:
        print(f"[WARN] requests download failed for {video_url}: {e}")
        return False

def download_video_preferring_requests(video_url: str, output_path: Path) -> bool:
    video_url = normalize_video_url(video_url)
    lower = video_url.lower()
    if "youtube.com" in lower or "youtu.be" in lower or "vimeo.com" in lower:
        return download_video_yt_dlp(video_url, output_path)
    if is_direct_video_url(video_url):
        ok = download_video_requests(video_url, output_path)
        if ok:
            return True
        return download_video_yt_dlp(video_url, output_path)
    return download_video_yt_dlp(video_url, output_path)

# Skip logic
def already_downloaded(title_slug: str, expected_name: str, url: str) -> bool:
    out_dir = OUTPUT_ROOT / title_slug
    json_file = out_dir / f"{title_slug}.json"
    if not out_dir.exists() or not json_file.exists():
        return False
    try:
        with open(windows_longpath(json_file), "r", encoding="utf-8-sig") as f:
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
    title_raw = extract_text_or_none(title_node) or "untitled"
    title_slug = safe_slug(title_raw, SLUG_MAX_LEN)

    desc_container = soup.find("div", class_="mb-4 whitespace-pre-line flex flex-col gap-4")
    description = None
    if desc_container:
        p = desc_container.find("p")
        description = extract_text_or_none(p)

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
    title_slug = safe_slug(result.get("title_slug") or "untitled", SLUG_MAX_LEN)
    data = result["data"]
    images = result["images"]
    videos = result["videos"]

    out_dir = OUTPUT_ROOT / title_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    base = short_base(title_slug, FILEBASE_MAX_LEN)

    # Videos (failures won't block JSON)
    for i, v in enumerate(videos, start=1):
        vurl = v.get("video_url", "")
        if not vurl:
            continue
        video_path = out_dir / f"{base}_{i}.mp4"
        ok = download_video_preferring_requests(vurl, video_path)
        if not ok:
            fallback = out_dir / f"v{i}.mp4"
            download_video_preferring_requests(vurl, fallback)

    # Images (failures won't block JSON)
    for i, img_url in enumerate(images, start=1):
        if not img_url:
            continue
        img_path = out_dir / f"{base}_{i}.jpg"
        ok = download_with_requests(img_url, img_path)
        if not ok:
            fallback = out_dir / f"img{i}.jpg"
            download_with_requests(img_url, fallback)

    # JSON (always try to save)
    json_file = out_dir / f"{base}.json"
    try:
        with open(windows_longpath(json_file), "w", encoding="utf-8-sig") as f:
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
        urls = urls[4000:6000]  # Limit for testing
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
