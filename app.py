import os
import json
import time
import shutil
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import undetected_chromedriver as uc

BASE_URL = "https://www.unblock.coffee"
YEARLY_URLS = {
    # 2025: "https://www.unblock.coffee/selection/superbowl-commercials-2025/",
    # 2024: "https://www.unblock.coffee/selection/superbowl-commercials-2024/",
    # 2023: "https://www.unblock.coffee/selection/superbowl-commercials-2023/",
    2022: "https://www.unblock.coffee/selection/superbowl-commercials-2022/",
    2021: "https://www.unblock.coffee/selection/2021-super-bowl-commercials/",
    2020: "https://www.unblock.coffee/selection/super-bowl-liv-2020-ads/"
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_with_selenium(url):
    print(f"🌐 Opening browser for: {url}")
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options)
    driver.get(url)
    time.sleep(2)

    for _ in range(5):  # Scroll to load all campaigns
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    html = driver.page_source
    driver.quit()
    return html

def extract_campaign_links(url):
    html = fetch_with_selenium(url)
    soup = BeautifulSoup(html, "html.parser")
    links = {
        a["href"] for a in soup.find_all("a", href=True)
        if "/campaign/" in a["href"]
    }
    print(f"✅ Found {len(links)} campaigns")
    return list(links)

def fetch_html(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text

def download_video(url, save_path):
    try:
        print(f"⬇️ Downloading: {url}")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(save_path, "wb") as f:
                shutil.copyfileobj(r.raw, f)
        print(f"✅ Saved to: {save_path}")
    except Exception as e:
        print(f"❌ Download failed: {e}")

def sanitize(name):
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in name).strip()

def parse_campaign(relative_url, year):
    url = urljoin(BASE_URL, relative_url)
    print(f"📄 Parsing: {url}")
    try:
        soup = BeautifulSoup(fetch_html(url), "html.parser")
    except Exception as e:
        print(f"❌ Error loading page: {e}")
        return None

    # Basic Info
    name = soup.select_one("h1.campaign-name")
    name = name.text.strip() if name else "Untitled"
    description = None
    for sel in ["div.description", "div.content", "div.summary"]:
        el = soup.select_one(sel)
        if el:
            description = el.get_text(strip=True)
            break

    info_map = {"brand": None, "agency": None, "country": None, "sector": None}
    for li in soup.select("#campaign-info li"):
        label = li.select_one("span.title")
        value = li.select_one("a")
        if label and value:
            label = label.text.strip().lower()
            val = value.text.strip()
            if "brand" in label:
                info_map["brand"] = val
            elif "agency" in label:
                info_map["agency"] = val
            elif "country" in label:
                info_map["country"] = val
            elif "sector" in label:
                info_map["sector"] = val

    # Credits
    credits = []
    for row in soup.select("table#creatives tr"):
        name_el = row.select_one("td.creative-name a")
        role_el = row.select_one("td.creative-role")
        if name_el and role_el:
            credits.append({
                "name": name_el.text.strip(),
                "role": role_el.text.strip()
            })

    # Videos
    videos = []
    for tag in soup.select("a.galeria"):
        data_video = tag.get("data-video")
        poster = tag.get("data-poster")
        if data_video:
            try:
                json_data = json.loads(unquote(data_video))
                for source in json_data.get("source", []):
                    if "src" in source:
                        videos.append({
                            "thumbnail": poster,
                            "video_url": source["src"]
                        })
            except Exception as e:
                print(f"⚠️ Failed parsing video: {e}")

    images = []
    for img in soup.select("div.gallery-container img"):
        src = img.get("src")
        if src and src.startswith("http"):
            images.append(src)


    return {
        "origin": {"name": "unblock.coffee", "url": url},
        "name": name,
        "type": "video",
        "sector": info_map["sector"],
        "countries": [info_map["country"]] if info_map["country"] else [],
        "brands": [info_map["brand"]] if info_map["brand"] else [],
        "agency": info_map["agency"],
        "year": str(year),
        "award": None,
        "category": None,
        "subCategory": None,
        "description": description,
        "credits": credits,
        "awards": None,
        "images": images,
        "videos": videos,
        "tags": None
    }

def scrape_all():
    for year, index_url in YEARLY_URLS.items():
        print(f"\n📅 Year {year}")
        os.makedirs(str(year), exist_ok=True)
        links = extract_campaign_links(index_url)

        for link in tqdm(links, desc=f"Scraping {year}"):
            data = parse_campaign(link, year)
            if not data:
                continue

            campaign_folder = os.path.join(str(year), sanitize(data["name"]))
            os.makedirs(campaign_folder, exist_ok=True)

            # Save metadata
            with open(os.path.join(campaign_folder, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Save videos
            for i, vid in enumerate(data["videos"]):
                video_url = vid.get("video_url")
                if not video_url: continue
                ext = video_url.split(".")[-1].split("?")[0]
                path = os.path.join(campaign_folder, f"video_{i+1}.{ext}")
                if not os.path.exists(path):
                    download_video(video_url, path)

if __name__ == "__main__":
    scrape_all()
