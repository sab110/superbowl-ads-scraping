# import os
# import re
# import json
# import time
# import requests
# import subprocess
# from urllib.parse import urlparse, parse_qs
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from urllib.parse import urlparse

# # ========== MAPPINGS ==========
# award_map = {
#     "9": "Gold", "13": "Silver", "10": "Bronze", "5": "Shortlist"
# }
# category_map = {
#     "2": "Comm. extérieure & Print", "4": "Comm. Films & Divertissements", "11": "Comm. Direct Activation",
#     "29": "Comm. Grandes causes", "43": "Comm. Mode", "3": "Comm. Craft Image",
#     "24": "Bertrand Suchet - Rédaction & Audio", "38": "Comm. Craft Direction Artistique",
#     "42": "Excellence", "40": "Produits digitaux", "39": "Innovations digitales",
#     "10": "Digital Communication", "33": "Prod Films", "7": "Prod Clip Musical",
#     "21": "Prod Son", "25": "Prod VFX & Animation", "14": "Branding design",
#     "41": "Design d’espaces", "16": "Typographie", "32": "Design graphique",
#     "6": "Motion design", "15": "Concours Etudiant", "44": "Concours Futurs désirables"
# }

# # ========== UTILS ==========
# def slugify(text):
#     return re.sub(r'[^a-zA-Z0-9_-]', '_', text.strip().lower())

# def download_file(url, dest_path, retries=3):
#     for attempt in range(retries):
#         try:
#             r = requests.get(url, stream=True, timeout=15)
#             if r.status_code == 200:
#                 with open(dest_path, 'wb') as f:
#                     for chunk in r.iter_content(1024):
#                         f.write(chunk)
#                 return
#         except Exception as e:
#             print(f"Retry {attempt+1}/{retries} failed for {url}: {e}")
#             time.sleep(2)
#     print(f"❌ Failed to download {url}")


# def clean_vimeo_url(embed_url):
#     match = re.search(r'/video/(\d+)', embed_url)
#     if match:
#         return f"https://vimeo.com/{match.group(1)}"
#     return None

# def download_vimeo_video(video_url, dest_path):
#     try:
#         subprocess.run(["yt-dlp", "-o", dest_path, video_url], check=True)
#     except subprocess.CalledProcessError as e:
#         print(f"yt_dlp failed for {video_url}: {e}")

# # ========== SELENIUM SETUP ==========
# options = Options()
# # options.add_argument("--headless=new")
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-gpu")
# options.add_argument("--window-size=1920,1080")
# options.add_argument("--start-maximized")
# options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
# driver = webdriver.Chrome(options=options)

# # ========== CONFIG ==========
# base_url = "https://leclubdesda.org/archives/1?recompense_id=9&category_parent_id=4&annee=2023"
# parsed = urlparse(base_url)
# query = parse_qs(parsed.query)
# award_id = query.get("recompense_id", [""])[0]
# cat_id = query.get("category_parent_id", [""])[0]
# year = query.get("annee", [""])[0]
# award = award_map.get(award_id, "Unknown")
# category = category_map.get(cat_id, "Unknown Category")

# # ========== SCRAPE ENTRIES ==========
# driver.get(base_url)
# time.sleep(5)
# project_links = []
# articles = driver.find_elements(By.CLASS_NAME, 'css-13v8y1l')
# for article in articles:
#     try:
#         link = article.find_element(By.TAG_NAME, 'a').get_attribute('href')
#         if link:
#             project_links.append(link)
#     except Exception as e:
#         print(f"Error extracting link: {e}")
# print(f"Found {len(project_links)} projects in {category} [{award}]")

# # ========== PROCESS PROJECTS ==========
# for project_link in project_links:
#     driver.get(project_link)
#     time.sleep(5)
#     soup = BeautifulSoup(driver.page_source, 'html.parser')

#     title = soup.find('div', class_='css-3uuujb')
#     title = title.text.strip() if title else "No title"

#     subcategory = soup.find('h3', class_='css-i074xz')
#     subcategory = subcategory.text.strip() if subcategory else None

#     try:
#         agency_brand_tag = soup.find('p', class_='css-pbt03z')
#         links = agency_brand_tag.find_all('a')
#         agency = links[0].text.strip() if len(links) > 0 else None
#         brand = links[1].text.strip() if len(links) > 1 else None
#     except:
#         agency = brand = None

#     year_detected = year
#     credits = []
#     try:
#         blocks = soup.find_all('div', class_='css-1t817sz')
#         for block in blocks:
#             role_tag = block.find('h3', class_='css-ndugta')
#             name_tag = block.find('div', class_='css-azlh8x')
#             if not role_tag or not name_tag:
#                 continue
#             role = role_tag.text.strip()
#             name = name_tag.text.strip()
#             if role.lower() == 'année':
#                 year_detected = name
#             elif role.lower() != 'ref':
#                 credits.append({"role": role, "name": name})
#     except: pass

#     image_urls = []
#     try:
#         image_tags = soup.find_all('img', class_='css-0')
#         for img in image_tags:
#             src = img.get('src')
#             if src:
#                 image_urls.append(src)
#     except: pass

#     # videos = []
#     # try:
#     #     iframe = soup.find('iframe')
#     #     if iframe and 'player.vimeo.com/video/' in iframe['src']:
#     #         video_url = iframe['src']
#     #         match = re.search(r'/video/(\d+)', video_url)
#     #         if match:
#     #             vimeo_id = match.group(1)
#     #             oembed = f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vimeo_id}'
#     #             response = requests.get(oembed)
#     #             thumbnail = response.json().get('thumbnail_url') if response.ok else None
#     #             videos.append({
#     #                 "video_url": video_url,
#     #                 "thumbnail": thumbnail
#     #             })
#     # except: pass
#     # ========== VIDEO HANDLING ==========

#     videos = []
#     try:
#         iframe = soup.find('iframe')
#         if iframe and 'player.vimeo.com/video/' in iframe['src']:
#             embed_url = iframe['src']
#             vimeo_id_match = re.search(r'/video/(\d+)', embed_url)
#             if vimeo_id_match:
#                 vimeo_id = vimeo_id_match.group(1)
#                 oembed = f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vimeo_id}'
#                 response = requests.get(oembed)
#                 thumbnail = response.json().get('thumbnail_url') if response.ok else None
#                 videos.append({
#                     "video_url": embed_url,  # use iframe src directly
#                     "thumbnail": thumbnail
#                 })
#     except Exception as e:
#         print(f"Error parsing video: {e}")



#     # ========== FOLDER STRUCTURE ==========
#     base_dir = "leclubdesda"
#     category_folder = os.path.join(base_dir, year_detected, category)
#     project_folder = os.path.join(category_folder, slugify(title))
#     os.makedirs(project_folder, exist_ok=True)

#     # ========== SAVE METADATA ==========
#     metadata = {
#         "origin": {"name": "leclubdesda.org", "url": project_link},
#         "name": title,
#         "type": "video" if videos else "image",
#         "sector": None,
#         "countries": "France",
#         "brands": brand,
#         "agency": agency,
#         "year": year_detected,
#         "award": award,
#         "category": category,
#         "subCategory": subcategory,
#         "description": None,
#         "credits": credits,
#         "image_urls": image_urls,
#         "videos": videos,
#         "tags": None,
#         "product": None
#     }
#     with open(os.path.join(project_folder, "metadata.json"), "w", encoding="utf-8") as f:
#         json.dump(metadata, f, indent=2, ensure_ascii=False)

#     # ========== DOWNLOAD IMAGES ==========
#     for idx, img_url in enumerate(image_urls, 1):
#         ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
#         filename = os.path.join(project_folder, f"{title}_{idx}{ext}")
#         download_file(img_url, filename)

#     # # ========== DOWNLOAD VIDEOS & THUMBNAILS ==========
#     # for idx, vid in enumerate(videos, 1):
#     #     vimeo_clean = clean_vimeo_url(vid["video_url"])
#     #     if vimeo_clean:
#     #         try:
#     #             subprocess.run([
#     #                 "yt-dlp",
#     #                 "-o", os.path.join(project_folder, f"{title}_{idx}.mp4"),
#     #                 vimeo_clean
#     #             ], check=True)
#     #         except subprocess.CalledProcessError as e:
#     #             print(f"yt_dlp failed for {vimeo_clean}: {e}")
#     # ========== DOWNLOAD VIDEOS & THUMBNAILS ==========

#     for idx, vid in enumerate(videos, 1):
#         video_url = vid.get("video_url")
#         if video_url and not video_url.startswith("blob:"):
#             dest_path = os.path.join(project_folder, f"{title}_{idx}.mp4")
#             try:
#                 subprocess.run([
#                     "yt-dlp",
#                     "--referer", "https://leclubdesda.org",
#                     "-o", dest_path,
#                     video_url
#                 ], check=True)
#             except subprocess.CalledProcessError as e:
#                 print(f"yt_dlp failed for {video_url}: {e}")

#         # download thumbnail if available
#         if vid.get("thumbnail"):
#             ext = os.path.splitext(vid["thumbnail"].split("?")[0])[1] or ".jpg"
#             thumb_path = os.path.join(project_folder, f"{title}_{idx}_thumb{ext}")
#             download_file(vid["thumbnail"], thumb_path)



# print("✅ All projects scraped and saved.")
# driver.quit()


import os
import re
import json
import time
import requests
import subprocess
import itertools
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

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
    print(f"❌ Failed to download {url}")

def clean_vimeo_url(embed_url):
    match = re.search(r'/video/(\d+)', embed_url)
    if match:
        return f"https://vimeo.com/{match.group(1)}"
    return None

# ====== SELENIUM SETUP ======
options = Options()
# options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
driver = webdriver.Chrome(options=options)

# ====== DYNAMIC COMBINATION SETUP ======
year = "2023"
award_ids = ["9", "13", "10", "5"]
category_ids = list(category_map.keys())
pages = list(range(1, 16))
combinations = list(itertools.product(award_ids, category_ids, pages))

# ====== MAIN LOOP ======
for award_id, category_id, page in combinations:
    award = award_map.get(award_id, "Unknown")
    category = category_map.get(category_id, "Unknown Category")
    base_url = f"https://leclubdesda.org/archives/{page}?recompense_id={award_id}&category_parent_id={category_id}&annee={year}"

    print(f"\n🔎 Scraping: {award} | {category} | Page {page}")
    driver.get(base_url)
    time.sleep(4)
    articles = driver.find_elements(By.CLASS_NAME, 'css-13v8y1l')
    if not articles:
        print("⚠️ No projects found. Skipping to next combination.")
        continue

    project_links = []
    for article in articles:
        try:
            link = article.find_element(By.TAG_NAME, 'a').get_attribute('href')
            if link:
                project_links.append(link)
        except:
            pass
    if not project_links:
        continue

    print(f"✅ Found {len(project_links)} projects")

    for project_link in project_links:
        try:
            driver.get(project_link)
            time.sleep(4)
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            title = soup.find('div', class_='css-3uuujb')
            title = title.text.strip() if title else "No title"

            subcategory = soup.find('h3', class_='css-i074xz')
            subcategory = subcategory.text.strip() if subcategory else None

            agency = brand = None
            try:
                agency_brand_tag = soup.find('p', class_='css-pbt03z')
                links = agency_brand_tag.find_all('a')
                agency = links[0].text.strip() if len(links) > 0 else None
                brand = links[1].text.strip() if len(links) > 1 else None
            except: pass

            year_detected = year
            credits = []
            try:
                blocks = soup.find_all('div', class_='css-1t817sz')
                for block in blocks:
                    role_tag = block.find('h3', class_='css-ndugta')
                    name_tag = block.find('div', class_='css-azlh8x')
                    if not role_tag or not name_tag:
                        continue
                    role = role_tag.text.strip()
                    name = name_tag.text.strip()
                    if role.lower() == 'année':
                        year_detected = name
                    elif role.lower() != 'ref':
                        credits.append({"role": role, "name": name})
            except: pass

            image_urls = []
            try:
                image_tags = soup.find_all('img', class_='css-0')
                for img in image_tags:
                    src = img.get('src')
                    if src:
                        image_urls.append(src)
            except: pass

            videos = []
            try:
                iframe = soup.find('iframe')
                if iframe and 'player.vimeo.com/video/' in iframe['src']:
                    embed_url = iframe['src']
                    vimeo_id_match = re.search(r'/video/(\d+)', embed_url)
                    if vimeo_id_match:
                        vimeo_id = vimeo_id_match.group(1)
                        oembed = f'https://vimeo.com/api/oembed.json?url=https://vimeo.com/{vimeo_id}'
                        response = requests.get(oembed)
                        thumbnail = response.json().get('thumbnail_url') if response.ok else None
                        videos.append({
                            "video_url": embed_url,
                            "thumbnail": thumbnail
                        })
            except Exception as e:
                print(f"⚠️ Video parse error: {e}")

            # Folder structure
            base_dir = "leclubdesda"
            category_folder = os.path.join(base_dir, year_detected, category)
            project_folder = os.path.join(category_folder, slugify(title))
            os.makedirs(project_folder, exist_ok=True)

            # Save metadata
            metadata = {
                "origin": {"name": "leclubdesda.org", "url": project_link},
                "name": title,
                "type": "video" if videos else "image",
                "sector": None,
                "countries": "France",
                "brands": brand,
                "agency": agency,
                "year": year_detected,
                "award": award,
                "category": category,
                "subCategory": subcategory,
                "description": None,
                "credits": credits,
                "image_urls": image_urls,
                "videos": videos,
                "tags": None,
                "product": None
            }
            with open(os.path.join(project_folder, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Download images
            for idx, img_url in enumerate(image_urls, 1):
                ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
                filename = os.path.join(project_folder, f"{title}_{idx}{ext}")
                download_file(img_url, filename)

            # Download videos & thumbnails
            for idx, vid in enumerate(videos, 1):
                video_url = vid.get("video_url")
                if video_url and not video_url.startswith("blob:"):
                    dest_path = os.path.join(project_folder, f"{title}_{idx}.mp4")
                    try:
                        subprocess.run([
                            "yt-dlp", "--referer", "https://leclubdesda.org",
                            "-o", dest_path, video_url
                        ], check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"yt_dlp failed for {video_url}: {e}")

                if vid.get("thumbnail"):
                    ext = os.path.splitext(vid["thumbnail"].split("?")[0])[1] or ".jpg"
                    thumb_path = os.path.join(project_folder, f"{title}_{idx}_thumb{ext}")
                    download_file(vid["thumbnail"], thumb_path)

        except Exception as e:
            print(f"❌ Failed to process project: {project_link}\n{e}")

print("✅ All scraping finished.")
driver.quit()
