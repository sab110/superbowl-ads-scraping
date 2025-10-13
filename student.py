import os
import re
import json
import subprocess
import requests
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from lxml import html
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import TimeoutException, WebDriverException
import urllib3
import socket

def safe_get(driver, url, retries=3, delay=3):
    for attempt in range(retries):
        try:
            driver.set_page_load_timeout(60)
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
# driver = webdriver.Chrome(options=options)

import undetected_chromedriver as uc

# ====== SELENIUM SETUP (Undetected) ======
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
# options.add_argument("--headless=new")

driver = uc.Chrome(options=options, use_subprocess=True)


# ====== STEP 1: GENERATE PAGE URLS ======
BASE_URL = "https://www.adsoftheworld.com/student?page="
ALL_PAGES = [f"{BASE_URL}{i}" for i in range(1, 85)]

def sanitize_filename(name, max_length=80):
    name = re.sub(r'[<>:"/\\|?*\n\r]+', '', name)
    name = name.strip().replace("...", "")  # Remove ellipsis
    return name[:max_length].strip()
# ====== STEP 2: COLLECT ARTICLE LINKS ======
# article_urls = set()

# for page_url in ALL_PAGES:
#     print(f"🔍 Scraping: {page_url}")
#     # driver.get(page_url)
#     # time.sleep(1)
    
#     if not safe_get(driver, page_url):
#         continue
#     time.sleep(1)

#     soup = BeautifulSoup(driver.page_source, 'html.parser')

#     # Each campaign card div has class 'campaign_card_*'
#     campaign_cards = soup.find_all("div", id=re.compile(r"^campaign_card_\d+"))

#     for card in campaign_cards:
#         link_tag = card.find("a", href=True)
#         if link_tag and link_tag['href'].startswith("/campaigns/"):
#             full_url = f"https://www.adsoftheworld.com{link_tag['href']}"
#             article_urls.add(full_url)

# # Save all collected URLs to file
# with open("student_campaign_urls.txt", "w", encoding="utf-8") as f:
#     f.write("\n".join(article_urls))

# print(f"✅ Total unique campaigns found: {len(article_urls)} and saved to student_campaign_urls.txt")

# ====== UTILITY: VIDEO & FILE DOWNLOAD ======
def download_file(url, dest_path, retries=3):
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
            time.sleep(2)
    print(f"❌ Failed to download {url}")

with open("student_campaign_urls.txt", "r", encoding="utf-8") as f:
    article_urls = [line.strip() for line in f.readlines() if line.strip()]

# ====== STEP 3: LOOP THROUGH EACH ARTICLE ======
for url in article_urls:
    # driver.get(url)
    # time.sleep(1)
    # Reset page to blank to avoid JS leftovers
    driver.get("about:blank")
    time.sleep(0.5)

    if not safe_get(driver, url):
        FAILED_URLS.append(url)
        continue

    # Trigger lazy loading (important for full rendering)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Title
    try:
            title_tag = soup.find('h1', class_='text-2xl karlasemibold')
            if not title_tag:
                print(f"❌ Skipping due to missing title: {url}")
                continue
            title = title_tag.text.strip().replace(" ", "_")
            print(f"\n🎯 Processing: {title}")
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
        if iframe and 'player.vimeo.com/video/' in iframe['src']:
            vimeo_id = re.search(r'/video/(\d+)', iframe['src']).group(1)
            thumb = requests.get(f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vimeo_id}').json().get('thumbnail_url')
            videos.append({"video_url": iframe['src'], "thumbnail": thumb})

        for div in soup.find_all('div', class_='bg-white my-3'):
            if (video_tag := div.find('video', src=True, poster=True)):
                videos.append({"video_url": video_tag['src'], "thumbnail": video_tag['poster']})
            if (iframe_tag := div.find('iframe', src=True)):
                v_url = iframe_tag['src']
                if 'youtube' in v_url:
                    vid = v_url.split('/')[4]
                    thumb = f"https://img.youtube.com/vi/{vid}/0.jpg"
                    videos.append({"video_url": v_url, "thumbnail": thumb})
                elif 'vimeo' in v_url:
                    vid = v_url.split('/')[-1]
                    thumb = f"https://vumbnail.com/{vid}.jpg"
                    videos.append({"video_url": v_url, "thumbnail": thumb})
            if (img_tag := div.find('img', src=True)):
                image_urls.append(img_tag['src'])
    except Exception as e:
        print(f"Media error: {e}")

    safe_title = sanitize_filename(title.replace("_", " "))
    output_dir = os.path.join("adsoftheworld", "student", safe_title)
    json_path = os.path.join(output_dir, f"{safe_title}.json")
    if os.path.exists(json_path):
        print(f"⏭️ Already exists: {safe_title}")
        continue


    # Save folder
    # output_dir = os.path.join("adsoftheworld", "student", title.replace("_", " "))
    os.makedirs(output_dir, exist_ok=True)

    # Save videos
    for i, vid in enumerate(videos, 1):
        v_url = vid.get("video_url")
        if v_url and not v_url.startswith("blob"):
            video_path = os.path.join(output_dir, f"{title}_{i}.mp4")
            try:
                subprocess.run([
                    "yt-dlp", "--referer", "https://www.adsoftheworld.com",
                    "-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4",
                    "-o", video_path, v_url
                ], check=True)
            except subprocess.CalledProcessError:
                print(f"yt-dlp failed: {v_url}")

            thumb = vid.get("thumbnail")
            if thumb:
                ext = os.path.splitext(thumb.split("?")[0])[1] or ".jpg"
                download_file(thumb, os.path.join(output_dir, f"{safe_title}_{i}_thumb{ext}"))

    # Save images
    for i, img_url in enumerate(image_urls):
        img_path = os.path.join(output_dir, f"{safe_title}_{i+1}.jpg")
        download_file(img_url, img_path)

    # Save metadata
    output_json = {
        "origin": {"name": "adsoftheworld.com", "url": url},
        "name": title.replace("_", " "),
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
        "tags": "Student",
        "product": None
    }

    with open(os.path.join(output_dir, f"{safe_title}.json"), 'w', encoding="utf-8-sig") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {safe_title} to {output_dir}")
# At the end
with open("failed_urls.txt", "w") as f:
    f.write("\n".join(FAILED_URLS))

driver.quit()