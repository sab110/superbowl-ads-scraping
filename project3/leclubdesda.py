import os
import re
import json
import time
import requests
import subprocess
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

log_file = open("failed_links_2.txt", "a", encoding="utf-8")

# ====== MAPPINGS ======
award_map = {
    "9": "Gold", "13": "Silver", "10": "Bronze", "5": "Shortlist"
}
category_map = {
    "2": "Comm. extérieure & Print", "4": "Comm. Films & Divertissements", "11": "Comm. Direct Activation",
    "29": "Comm. Grandes causes", "43": "Comm. Mode", "3": "Comm. Craft Image",
    "24": "Bertrand Suchet - Rédaction & Audio", "38": "Comm. Craft Direction Artistique",
    "42": "Excellence", "40": "Produits digitaux", "39": "Innovations digitales",
    "10": "Digital Communication", "33": "Prod Films", "7": "Prod Clip Musical",
    "21": "Prod Son", "25": "Prod VFX & Animation", "14": "Branding design",
    "41": "Design d’espaces", "16": "Typographie", "32": "Design graphique",
    "6": "Motion design", "15": "Concours Etudiant", "44": "Concours Futurs désirables"
}

# ====== UTILS ======
def slugify(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text.strip().lower())

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
    log_file.write(f"Failed to download {url} after {retries} attempts\n")
    print(f"❌ Failed to download {url}")

# ====== SELENIUM SETUP ======
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0")
driver = webdriver.Chrome(options=options)

# ====== SETUP ======
# years = [str(y) for y in range(1976, 1991)]
years =  [str(y) for y in range(2023, 1979, -1)] + [
    "1973-1974", "1974-1975", "1971-1972", "1970-1971", "1969-1970", "1968-1969"] 

award_ids = ["5", "9", "10", "13"]
category_ids = list(category_map.keys())
pages = list(range(1, 50))

# ====== LOOP ======
for year in years:
    # for award_id in award_ids:
    #     award = award_map.get(award_id, "Unknown")
    #     for cat_id in category_ids:
    #         category = category_map.get(cat_id, "Unknown Category")
    #         for page in pages:
    #             url = f"https://leclubdesda.org/archives/{page}?recompense_id={award_id}&category_parent_id={cat_id}&annee={year}"
    #             print(f"\n🔎 Scraping: {award} | {category} | {year} | Page {page}")
    #             driver.get(url)
    #             time.sleep(1.2)
    for award_id in award_ids:
            award = award_map.get(award_id, "Unknown")
            for page in pages:
                url = f"https://leclubdesda.org/archives/{page}?recompense_id={award_id}&annee={year}"
                print(f"\n🔎 Scraping: {award} | {year} | Page {page}")
                driver.get(url)
                time.sleep(1.2)
                articles = driver.find_elements(By.CLASS_NAME, 'css-13v8y1l')
                if not articles:
                    print("❌ No projects found. Moving to next category/year/award...")
                    break

                project_links = [a.find_element(By.TAG_NAME, 'a').get_attribute('href') for a in articles]
                print(f"✅ Found {len(project_links)} projects")

                for link in project_links:
                    try:
                        driver.get(link)
                        time.sleep(0.2)
                        soup = BeautifulSoup(driver.page_source, 'html.parser')

                        title = soup.find('div', class_='css-3uuujb')
                        title = title.text.strip() if title else "No title"
                        category = soup.find('h3',class_='css-css-k0mqxh')
                        category = category.text.strip() if category else None
                        subcategory = soup.find('h3', class_='css-i074xz')
                        subcategory = subcategory.text.strip() if subcategory else None

                        agency = brand = None
                        try:
                            ab = soup.find('p', class_='css-pbt03z').find_all('a')
                            agency = ab[0].text.strip() if len(ab) > 0 else None
                            brand = ab[1].text.strip() if len(ab) > 1 else None
                        except: pass

                        credits = []
                        detected_year = year
                        for block in soup.find_all('div', class_='css-1t817sz'):
                            r = block.find('h3', class_='css-ndugta')
                            n = block.find('div', class_='css-azlh8x')
                            if r and n:
                                if r.text.strip().lower() == 'année':
                                    detected_year = n.text.strip()
                                elif r.text.strip().lower() != 'ref':
                                    credits.append({"role": r.text.strip(), "name": n.text.strip()})

                        image_urls = []
                        image_container = soup.find('div', class_='css-4kfmss')
                        if image_container:
                            image_tags = image_container.find_all('img', class_='css-0')
                            image_urls = [img['src'] for img in image_tags if img.get('src')]

                        videos = []
                        iframe = soup.find('iframe')
                        if iframe and 'player.vimeo.com/video/' in iframe['src']:
                            vimeo_id_match = re.search(r'/video/(\d+)', iframe['src'])
                            if vimeo_id_match:
                                vid = vimeo_id_match.group(1)
                                oembed = f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vid}'
                                thumb = requests.get(oembed).json().get('thumbnail_url', None)
                                videos.append({"video_url": iframe['src'], "thumbnail": thumb})

                        folder = os.path.join("scrapedata", detected_year, category, slugify(title))
                        os.makedirs(folder, exist_ok=True)

                        metadata = {
                            "origin": {"name": "leclubdesda.org", "url": link},
                            "name": title, "type": "video" if videos else "image",
                            "sector": None, "countries": "France", "brands": brand, "agency": agency,
                            "year": detected_year, "award": award, "category": category,
                            "subCategory": subcategory, "description": None,
                            "credits": credits, "image_urls": image_urls, "videos": videos,
                            "tags": None, "product": None
                        }
                        with open(os.path.join(folder, f"{title}.json"), "w", encoding="utf-8-sig") as f:
                            json.dump(metadata, f, indent=2, ensure_ascii=False)

                        for i, img_url in enumerate(image_urls, 1):
                            ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
                            download_file(img_url, os.path.join(folder, f"{title}_{i}{ext}"))

                        for i, vid in enumerate(videos, 1):
                            v_url = vid.get("video_url")
                            if v_url and not v_url.startswith("blob"):
                                out = os.path.join(folder, f"{title}_{i}.mp4")
                                try:
                                    subprocess.run([
                                        "yt-dlp",
                                        "--referer", "https://leclubdesda.org",
                                        "-f", "bestvideo+bestaudio/best",
                                        "--merge-output-format", "mp4",
                                        "-o", out,
                                        v_url
                                    ], check=True)
                                except subprocess.CalledProcessError as e:
                                    print(f"yt-dlp failed for {v_url}: {e}")
                                    log_file.write(f"Video Download Error: {v_url} | Reason: {e}\n")

                            thumb = vid.get("thumbnail")
                            if thumb:
                                ext = os.path.splitext(thumb.split("?")[0])[1] or ".jpg"
                                download_file(thumb, os.path.join(folder, f"{title}_{i}_thumb{ext}"))

                    except Exception as e:
                        print(f"❌ Error on {link}: {e}")
                        log_file.write(f"Project Error: {link} | Reason: {e}\n")

print("\n🎉 Finished scraping all data")
log_file.close()
driver.quit()
