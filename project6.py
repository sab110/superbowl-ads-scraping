# import time
# import json
# from selenium import webdriver
# from bs4 import BeautifulSoup
# import undetected_chromedriver as uc
# import os

# # Setup Chrome
# options = uc.ChromeOptions()
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-gpu")
# options.add_argument("--disable-blink-features=AutomationControlled")
# options.add_argument("--window-size=1920,1080")
# options.add_argument("--disable-extensions")
# options.add_argument("--start-maximized")
# options.add_argument("--disable-infobars")
# options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

# driver = webdriver.Chrome(options=options)

# output_file = "data.jsonl"

# # --- Resume Support: Load already scraped (url, category) pairs ---
# scraped_keys = set()
# if os.path.exists(output_file):
#     with open(output_file, "r", encoding="utf-8") as f:
#         for line in f:
#             try:
#                 obj = json.loads(line.strip())
#                 if "origin" in obj and "url" in obj["origin"]:
#                     key = (obj["origin"]["url"], obj.get("category"))
#                     scraped_keys.add(key)
#             except:
#                 continue
#     print(f"🔄 Resume enabled. Found {len(scraped_keys)} already-scraped (url, category) pairs.")

# # Loop over years 2012 → 2025
# for year in range(2012, 2026):
#     base_url = f"https://www.unblock.coffee/cnns/?adsyear={year}"
#     print(f"\n🔎 Year {year}: Visiting {base_url}")
#     driver.get(base_url)
#     time.sleep(2)

#     # Parse main page for category links
#     soup = BeautifulSoup(driver.page_source, "html.parser")
#     category_links = [a["href"] for a in soup.select("section.award-categories-grid a.award-category-card")]
#     print(f"  Found {len(category_links)} categories for {year}")

#     # Loop through each category
#     for cidx, category_url in enumerate(category_links, start=1):
#         category_name = category_url.split("/")[-1].split("?")[0]
#         print(f"  [{cidx}/{len(category_links)}] Category: {category_name}")
#         driver.get(category_url)
#         time.sleep(2)

#         cat_soup = BeautifulSoup(driver.page_source, "html.parser")
#         project_items = cat_soup.select("div.item")

#         print(f"     Found {len(project_items)} projects in category.")

#         # Loop through projects directly from category page
#         for pidx, item in enumerate(project_items, start=1):
#             link_tag = item.select_one("div.campaign-thumb a")
#             project_url = link_tag["href"] if link_tag else None

#             key = (project_url, category_name)
#             if not project_url or key in scraped_keys:
#                 print(f"       -> Skipping (already scraped or no link): {project_url} in {category_name}")
#                 continue

#             print(f"       -> Scraping Project {pidx}/{len(project_items)}: {project_url}")

#             # Extract directly from item
#             name_tag = item.select_one("h4 a")
#             name = name_tag.get_text(strip=True) if name_tag else None

#             award_tag = item.select_one(".level2, .level3, .level4, .level5")
#             award = award_tag.get_text(strip=True) if award_tag else None

#             agency = None
#             agency_tag = item.find("b", string="Agency:")
#             if agency_tag and agency_tag.find_next("a"):
#                 agency = agency_tag.find_next("a").get_text(strip=True)

#             brand = None
#             brand_tag = item.find("b", string="Brand:")
#             if brand_tag and brand_tag.find_next("a"):
#                 brand = brand_tag.find_next("a").get_text(strip=True)

#             country = None
#             small = item.select_one("p small")
#             if small:
#                 country = small.get_text(strip=True).strip("()")

#             # Collect image
#             images = []
#             img_tag = item.select_one("div.campaign-thumb img")
#             if img_tag and img_tag.get("src"):
#                 images.append(img_tag["src"])

#             # Build JSON object
#             project_obj = {
#                 "origin": {
#                     "name": "unblock.coffee",
#                     "url": project_url
#                 },
#                 "name": name,
#                 "type": "campaign",
#                 "sector": None,
#                 "countries": country,
#                 "brands": brand,
#                 "agency": agency,
#                 "year": str(year),
#                 "award": award,
#                 "category": category_name,
#                 "subCategory": None,
#                 "description": None,
#                 "credits": [],
#                 "image_urls": images,
#                 "videos": [],
#                 "tags": None,
#                 "product": None
#             }

#             # Save immediately
#             with open(output_file, "a", encoding="utf-8") as f:
#                 f.write(json.dumps(project_obj, ensure_ascii=False) + "\n")

#             scraped_keys.add(key)
#             print("          ✅ Saved")

# driver.quit()
# print(f"\n✅ Finished scraping. Data saved to {output_file}")


import os
import re
import time
import json
import requests
from urllib.parse import urlparse
from pathlib import Path
from selenium import webdriver
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

# -------------------
# Helpers
# -------------------
def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name.strip()) or "Unnamed"

def download_file(url, dest_path):
    try:
        r = requests.get(url, timeout=20, stream=True)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            print(f"      📥 Saved: {dest_path}")
        else:
            print(f"      ⚠️ Failed download: {url}")
    except Exception as e:
        print(f"      ❌ Error downloading {url}: {e}")

def get_detail(proj_soup, label):
    tag = proj_soup.find("span", string=label)
    if tag and tag.find_next("a"):
        return tag.find_next("a").get_text(strip=True)
    return None

# -------------------
# Setup Chrome
# -------------------
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("user-agent=Mozilla/5.0")

driver = webdriver.Chrome(options=options)

# -------------------
# Root directory
# -------------------
ROOT_DIR = "CNN"
Path(ROOT_DIR).mkdir(exist_ok=True)

# -------------------
# Main Loop
# -------------------
for year in range(2012, 2026):
    base_url = f"https://www.unblock.coffee/cnns/?adsyear={year}"
    print(f"\n🔎 Year {year}: {base_url}")
    driver.get(base_url)
    # time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    category_links = [a["href"] for a in soup.select("section.award-categories-grid a.award-category-card")]
    print(f"  Found {len(category_links)} categories")

    for category_url in category_links:
        category_name = category_url.split("/")[-1].split("?")[0]
        category_path = Path(ROOT_DIR) / str(year) / category_name
        category_path.mkdir(parents=True, exist_ok=True)

        print(f"\n  ▶ Category: {category_name}")
        driver.get(category_url)
        # time.sleep(2)

        cat_soup = BeautifulSoup(driver.page_source, "html.parser")
        project_items = cat_soup.select("div.item")
        print(f"     Found {len(project_items)} projects")

        for idx, item in enumerate(project_items, start=1):
            link_tag = item.select_one("div.campaign-thumb a")
            project_url = link_tag["href"] if link_tag else None
            if not project_url:
                continue

            # Award from category listing
            award_tag = item.select_one(".level2, .level3, .level4, .level5")
            award = award_tag.get_text(strip=True) if award_tag else None

            # Extract directly from item
            name_tag = item.select_one("h4 a")
            name = name_tag.get_text(strip=True) if name_tag else "Unnamed"
            safe_name = safe_filename(name)
            print(f"    [{idx}/{len(project_items)}] {project_url} [{award}]")

            # --- Open project detail page ---
            driver.get(project_url)
            time.sleep(0.5)
            proj_soup = BeautifulSoup(driver.page_source, "html.parser")

            # Name
            # name_tag = proj_soup.select_one("h1, h2, .campaign-title, h4 a")
            # name = name_tag.get_text(strip=True) if name_tag else "Unnamed"
            # safe_name = safe_filename(name)

            # Project folder by project name
            project_path = category_path / safe_name
            counter = 1
            while project_path.exists():  # avoid duplicates
                project_path = category_path / f"{safe_name}_{counter}"
                counter += 1
            project_path.mkdir(parents=True, exist_ok=True)

            # Details
            brand = get_detail(proj_soup, "Brand")
            agency = get_detail(proj_soup, "Agency")
            country = get_detail(proj_soup, "Country")
            sector = get_detail(proj_soup, "Sector")

            # Credits
            credits = []
            for row in proj_soup.select("#creatives tr, #credits tr"):
                role = row.find("td", class_="creative-role")
                person = row.find("td", class_="creative-name")
                if role and person:
                    credits.append({
                        "role": role.get_text(strip=True),
                        "name": person.get_text(strip=True)
                    })

            # Media
            images, videos = [], []
            for media in proj_soup.select(".gallery-container a.galeria"):
                video_data = media.get("data-video")
                thumb = media.get("data-poster") or media.get("data-thumb")
                img_src = media.get("href") or media.get("data-src") or media.get("src")

                if video_data and "src" in video_data:
                    m = re.search(r'"src":"(.*?)"', video_data)
                    if m:
                        videos.append({
                            "video_url": m.group(1).replace("\\/", "/"),
                            "thumbnail": thumb
                        })
                elif img_src:
                    images.append(img_src)

            # Download images with project name prefix
            for i, img_url in enumerate(images, start=1):
                ext = os.path.splitext(urlparse(img_url).path)[-1] or ".jpg"
                dest = project_path / f"{safe_name}_{i}{ext}"
                download_file(img_url, dest)

            # Download videos with project name prefix
            for i, vid in enumerate(videos, start=1):
                vid_url = vid["video_url"]
                ext = os.path.splitext(urlparse(vid_url).path)[-1] or ".mp4"
                dest = project_path / f"{safe_name}_{i}{ext}"
                download_file(vid_url, dest)

            # Build metadata
            project_obj = {
                "origin": {"name": "unblock.coffee", "url": project_url},
                "name": name,
                "type": "video" if videos else "image",
                "sector": sector,
                "countries": country,
                "brands": brand,
                "agency": agency,
                "year": str(year),
                "award": award,
                "category": category_name,
                "subCategory": None,
                "description": None,
                "credits": credits,
                "image_urls": images,
                "videos": videos,
                "tags": None,
                "product": None
            }

            # Save {project_name}.json
            with open(project_path / f"{safe_name}.json", "w", encoding="utf-8") as f:
                json.dump(project_obj, f, indent=2, ensure_ascii=False)

            print(f"          ✅ Saved project: {name}")

driver.quit()
print("\n✅ Finished scraping")
