import os
import re
import json
import subprocess
import requests
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from lxml import html
from selenium.common.exceptions import TimeoutException, WebDriverException
import urllib3
import socket
import undetected_chromedriver as uc

# ---------------------------
# Helpers: filenames & video
# ---------------------------
def sanitize_filename(name, max_length=80):
    name = re.sub(r'[<>:"/\\|?*\n\r]+', '', name)  # forbid chars
    name = name.replace('.', ' ')                  # remove dots
    name = re.sub(r'\s+', ' ', name).strip()       # condense whitespace
    name = name.replace(' ', '_')                  # underscores
    return name[:max_length].strip('_')

YOUTUBE_ID_RE = re.compile(r'(?:v=|/embed/|/shorts/|/v/|watch\\?v=)([A-Za-z0-9_-]{11})')

def extract_youtube_id(url: str):
    if "youtu.be/" in url:
        vid = url.split("youtu.be/")[-1].split("?")[0]
        return vid if len(vid) == 11 else None
    m = YOUTUBE_ID_RE.search(url)
    return m.group(1) if m else None

def youtube_thumb_from_url(url: str):
    vid = extract_youtube_id(url)
    return f"https://img.youtube.com/vi/{vid}/0.jpg" if vid else None

def normalize_video_url(v_url: str) -> str:
    if "youtube.com" in v_url or "youtu.be" in v_url:
        vid = extract_youtube_id(v_url)
        return f"https://www.youtube.com/watch?v={vid}" if vid else v_url
    if "player.vimeo.com/video/" in v_url:
        return v_url.split("?")[0]
    return v_url

# ---------------------------
# Robust navigation
# ---------------------------
def safe_get(driver, url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            driver.set_page_load_timeout(30)
            driver.get(url)
            return True
        except (TimeoutException, WebDriverException, urllib3.exceptions.ReadTimeoutError, socket.timeout) as e:
            print(f"⚠️ Attempt {attempt + 1} failed for {url} due to: {type(e).__name__}")
            time.sleep(delay)
        except Exception as e:
            print(f"❌ Unknown error on attempt {attempt + 1} for {url}: {e}")
            time.sleep(delay)
    print(f"❌ Skipping due to repeated timeouts or errors: {url}")
    return False

FAILED_URLS = []

# ====== SELENIUM SETUP ======
# options = Options()
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-gpu")
# options.add_argument("--disable-software-rasterizer")
# options.add_argument("--disable-webgl")
# options.add_argument("--window-size=1920,1080")
# options.add_argument("--start-maximized")
# options.add_argument("user-agent=Mozilla/5.0")
# options.add_argument("--log-level=3")
# options.add_argument("--headless=new")
# options.add_experimental_option("excludeSwitches", ["enable-logging"])
# driver = webdriver.Chrome(options=options)

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
options.add_argument("--disable-webgl")
options.add_argument("--window-size=1920,1080")
options.add_argument("--start-maximized")
options.add_argument("--user-agent=Mozilla/5.0")

# Optional: headless mode (only enable if stable)
options.add_argument("--headless=new")

driver = uc.Chrome(options=options, use_subprocess=True)

# ====== (Optional/unused) Page list ======
BASE_URL = "https://www.adsoftheworld.com/professional?page="
ALL_PAGES = [f"{BASE_URL}{i}" for i in range(16, 1432)]

# ====== UTILITY: FILE DOWNLOAD ======
def download_file(url, dest_path, retries=3):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    for attempt in range(retries):
        try:
            r = requests.get(url, stream=True, timeout=15)
            if r.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                return
        except Exception as e:
            print(f"Retry {attempt+1}/{retries} failed for {url}: {e}")
            # time.sleep(0.2)
    print(f"❌ Failed to download {url}")

# ====== Load URLs to process (REVERSE ORDER) ======
with open("professional_campaign_urls.txt", "r", encoding="utf-8") as f:
    article_urls = [line.strip() for line in f if line.strip()]
# article_urls.reverse()
print(f"↩️ Processing in reverse order: {len(article_urls)} URLs")
article_urls =article_urls[40018:41000]  # Limit to 1000 for testing
# ====== STEP 3: LOOP THROUGH EACH ARTICLE ======
for url in article_urls:
    driver.get("about:blank")

    if not safe_get(driver, url):
        FAILED_URLS.append(url)
        continue

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    # time.sleep(0.1)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Title
    try:
        title_tag = soup.find('h1', class_='text-2xl karlasemibold')
        if not title_tag:
            print(f"❌ Skipping due to missing title: {url}")
            continue
        title = title_tag.text.strip()
        safe_title = sanitize_filename(title)
        print(f"\n🎯 Processing: {safe_title}")
    except Exception as e:
        print(f"Title error: {e}")
        continue

    # Description
    try:
        description_tag = soup.find('div', class_='mb-4 whitespace-pre-line flex flex-col gap-4')
        description = "\n\n".join(p.get_text(strip=True) for p in description_tag.find_all('p')) if description_tag else None
    except Exception as e:
        print(f"Description error: {e}")
        description = None

    # Credits
    try:
        credits_content = str(soup.find('div', class_='col-span-2'))
        tree = html.fromstring(credits_content)
        credits_section = tree.xpath("//p[text()='Credits']/following-sibling::div//p/text()")
        credits = []
        for line in credits_section:
            if ":" in line:
                role, name = line.split(":", 1)
                role = role.strip()
                name = name.strip()
                if role.lower() == "brand":
                    continue
                credits.append({"role": role, "name": name})
    except Exception as e:
        print(f"Credits error: {e}")
        credits = []

    # Year
    try:
        campaign_description = soup.find('p', class_='mb-6 text-sm').text
        year_match = re.search(r'\b(\d{4})\b', campaign_description)
        year = year_match.group(1) if year_match else None
    except Exception as e:
        print(f"Year error: {e}")
        year = None

    # Categories
    try:
        categories = {
            "brand": None,
            "agency": None,
            "countries": None,
            "category": [],
            "subCategory": []
        }
        for link in soup.find_all('a', href=True):
            href, text = link['href'], link.text.strip()
            if 'brands' in href and not categories['brand']:
                categories['brand'] = text
            elif 'agencies' in href and not categories['agency']:
                categories['agency'] = text
            elif ('country' in href or 'countries' in href) and not categories['countries']:
                categories['countries'] = text
            elif 'medium_types' in href:
                categories['category'].append(text)
            elif 'industries' in href and not categories['subCategory']:
                categories['subCategory'].append(text)
    except Exception as e:
        print(f"Category error: {e}")

    # Media (videos & images)
    videos, image_urls = [], []
    try:
        iframe = soup.find('iframe')
        if iframe and 'player.vimeo.com/video/' in iframe.get('src', ''):
            v_src = normalize_video_url(iframe['src'])
            try:
                vimeo_id = re.search(r'/video/(\\d+)', v_src).group(1)
                thumb = requests.get(
                    f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vimeo_id}', timeout=10
                ).json().get('thumbnail_url')
            except Exception:
                thumb = None
            videos.append({"video_url": v_src, "thumbnail": thumb})

        for div in soup.find_all('div', class_='bg-white my-3'):
            video_tag = div.find('video', src=True, poster=True)
            if video_tag:
                videos.append({"video_url": normalize_video_url(video_tag['src']), "thumbnail": video_tag['poster']})

            iframe_tag = div.find('iframe', src=True)
            if iframe_tag:
                v_url = normalize_video_url(iframe_tag['src'])
                if 'youtube' in v_url or 'youtu.be' in v_url:
                    thumb = youtube_thumb_from_url(v_url)
                    videos.append({"video_url": v_url, "thumbnail": thumb})
                elif 'vimeo' in v_url:
                    try:
                        vid = v_url.rstrip('/').split('/')[-1]
                        thumb = f"https://vumbnail.com/{vid}.jpg"
                    except Exception:
                        thumb = None
                    videos.append({"video_url": v_url, "thumbnail": thumb})

            img_tag = div.find('img', src=True)
            if img_tag:
                image_urls.append(img_tag['src'])
    except Exception as e:
        print(f"Media error: {e}")

    # Paths
    output_dir = os.path.join("adsoftheworld", "professional", safe_title)
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{safe_title}.json")
    if os.path.exists(json_path):
        print(f"⏭️ Already exists: {safe_title}")
        continue

    # ---------------------------
    # yt-dlp: YouTube vs everything else
    # ---------------------------
    for i, vid in enumerate(videos, 1):
        v_url = vid.get("video_url")
        if not v_url or v_url.startswith("blob"):
            continue

        v_url = normalize_video_url(v_url)
        out_tpl = os.path.join(output_dir, f"{safe_title}_{i}.%(ext)s")

        is_youtube = ("youtube.com" in v_url) or ("youtu.be" in v_url)

        if is_youtube:
            # Prefer DASH MP4 (137+140), then WebM (248+251), then single-file fallbacks
            yt_formats = "137+140/248+251/22/18/best"
            cmd = [
                "yt-dlp",
                "--force-ipv4",
                "-N", "4",                   # parallel chunks
                "--geo-bypass",
                "--hls-prefer-ffmpeg",       # ffmpeg > native for HLS
                "--no-part",                 # avoid .part clutter
                "-R", "5",                   # retries
                "--fragment-retries", "15",
                "-f", yt_formats,
                "--merge-output-format", "mp4",
                "-o", out_tpl,
                v_url
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                # Final fallback: let yt-dlp pick "best"
                print(f"⚠️ YT primary formats failed, falling back → {v_url}")
                fallback = [
                    "yt-dlp",
                    "--force-ipv4",
                    "-N", "4",
                    "--geo-bypass",
                    "--hls-prefer-ffmpeg",
                    "--no-part",
                    "-R", "5",
                    "--fragment-retries", "15",
                    "-f", "bestvideo*+bestaudio/best",
                    "--merge-output-format", "mp4",
                    "-o", out_tpl,
                    v_url
                ]
                try:
                    subprocess.run(fallback, check=True)
                except subprocess.CalledProcessError as e2:
                    print(f"yt-dlp failed for YouTube: {v_url} → {e2}")

        else:
            # Vimeo/direct/mp4 etc — keep a referer (some gates check it)
            cmd = [
                "yt-dlp",
                "--force-ipv4",
                "--referer", "https://leclubdesda.org",
                "-f", (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                    "bestvideo[ext=webm]+bestaudio[ext=webm]/"
                    "best[ext=mp4]/best"
                ),
                "--merge-output-format", "mp4",
                "-o", out_tpl,
                v_url
            ]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                print(f"⚠️ Primary failed, falling back simple best → {v_url}")
                fallback = [
                    "yt-dlp",
                    "--force-ipv4",
                    "--referer", "https://leclubdesda.org",
                    "-f", "best[ext=mp4]/best",
                    "-o", out_tpl,
                    v_url
                ]
                try:
                    subprocess.run(fallback, check=True)
                except subprocess.CalledProcessError as e2:
                    print(f"yt-dlp failed: {v_url} → {e2}")

        # thumbnail (if any)
        thumb = vid.get("thumbnail")
        if thumb:
            ext = os.path.splitext(thumb.split("?")[0])[1] or ".jpg"
            download_file(thumb, os.path.join(output_dir, f"{safe_title}_{i}_thumb{ext}"))

    # Download images
    for i, img_url in enumerate(image_urls):
        img_path = os.path.join(output_dir, f"{safe_title}_{i+1}.jpg")
        download_file(img_url, img_path)

    # Save metadata
    output_json = {
        "origin": {"name": "adsoftheworld.com", "url": url},
        "name": title,
        "type": "video" if videos else "image",
        "sector": categories['subCategory'],
        "countries": categories['countries'],
        "brands": categories['brand'],
        "agency": categories['agency'],
        "year": year,
        "award": None,
        "category": categories['category'],
        "subCategory": categories['subCategory'],
        "description": description,
        "credits": credits,
        "image_urls": image_urls,
        "videos": videos,
        "tags": None,
        "product": None
    }

    with open(json_path, 'w', encoding="utf-8-sig") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {safe_title} to {output_dir}")

# At the end
if FAILED_URLS:
    with open("failed_urls_2.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(FAILED_URLS))

driver.quit()
