import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

skipped_log = open("skipped_urls.txt", "a", encoding="utf-8")

# Initialize undetected ChromeDriver
options = uc.ChromeOptions()
# options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

driver = uc.Chrome(use_subprocess=True, options=options)

def sanitize_filename(name):
    return "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).rstrip()

def create_folders(base_path, year, category):
    year_folder = os.path.join(base_path, str(year))
    category_folder = os.path.join(year_folder, category)
    os.makedirs(category_folder, exist_ok=True)
    return category_folder

def download_media(url, path):
    try:
        r = requests.get(url, timeout=10)
        with open(path, 'wb') as f:
            f.write(r.content)
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")

# Award types and categories
recompense_ids = {
    9: "Gold",
    13: "Silver",
    10: "Bronze",
    5: "Shortlist"
}

category_parent_ids = {
    2: "Comm. extérieure & Print",
    4: "Comm. Films & Divertissements",
    11: "Comm. Direct Activation",
    29: "Comm. Grandes causes",
    43: "Comm. Mode",
    3: "Comm. Craft Image",
    24: "Bertrand Suchet - Rédaction & Audio",
    38: "Comm. Craft Direction Artistique",
    42: "Excellence",
    40: "Produits digitaux",
    39: "Innovations digitales",
    10: "Digital Communication",
    33: "Prod Films",
    7: "Prod Clip Musical",
    21: "Prod Son",
    25: "Prod VFX & Animation",
    14: "Branding design",
    41: "Design d’espaces",
    16: "Typographie",
    32: "Design graphique",
    6: "Motion design",
    15: "Concours Etudiant",
    44: "Concours Futurs désirables"
}
# Year list includes both single years and ranges
# years = [
#         '1968-1969', '1969-1970', '1970-1971', '1971-1972', '1973-1974', '1974-1975',
#         *[str(year) for year in range(1976, 1990)]
#     ]
years = ['2023']

def scrape_data():
    base_url = "https://leclubdesda.org/archives"
    output_base = "leclubdesda_data"
    os.makedirs(output_base, exist_ok=True)

    for year in years:
        for recompense_id, award in recompense_ids.items():
            for cat_id, cat_name in category_parent_ids.items():
                folder = create_folders(output_base, year, cat_name)

                for page in range(1, 3):
                    url = f"{base_url}/{page}?recompense_id={recompense_id}&category_parent_id={cat_id}&annee={year}"
                    print(f"🔍 Visiting: {url}")
                    driver.get(url)
                    time.sleep(2)

                    # ⏯ Click the "Rechercher" button
                    try:
                        search_button = driver.find_element(By.ID, "searchBt")
                        search_button.click()
                        time.sleep(3)
                    except Exception as e:
                        print(f"⚠️ Couldn't click search button: {e}")
                        skipped_log.write(f"search_button_missing: {url}\n")
                        skipped_log.flush()
                        continue

                    # ⏬ Scrape projects
                    projects = driver.find_elements(By.CLASS_NAME, 'css-13v8y1l')
                    if not projects:
                        print("⚠️ No projects found.")
                        skipped_log.write(f"{url}\n")
                        skipped_log.flush()
                        break

                    for article in projects:
                        try:
                            link_elem = article.find_element(By.TAG_NAME, 'a')
                            project_href = link_elem.get_attribute("href")
                            project_url = "https://leclubdesda.org" + project_href
                            driver.get(project_url)
                            time.sleep(3)

                            soup = BeautifulSoup(driver.page_source, "html.parser")

                            project_data = {
                                "origin": {"name": "leclubdesda.org", "url": project_url},
                                "name": None,
                                "type": "video",
                                "sector": None,
                                "countries": "France",
                                "brands": None,
                                "agency": None,
                                "year": year,
                                "award": award,
                                "category": None,
                                "subCategory": None,
                                "description": None,
                                "credits": [],
                                "image_urls": [],
                                "videos": [],
                                "tags": None,
                                "product": None
                            }

                            title_div = soup.select_one("div.css-3uuujb")
                            if title_div:
                                project_data["name"] = title_div.text.strip()

                            cat = soup.select_one("h3.css-k0mqxh")
                            if cat:
                                project_data["category"] = cat.text.strip()

                            subcat = soup.select_one("h3.css-i074xz")
                            if subcat:
                                project_data["subCategory"] = subcat.text.strip()

                            agency_brand_p = soup.select_one("p.css-pbt03z")
                            if agency_brand_p and "pour" in agency_brand_p.text:
                                parts = agency_brand_p.text.split("pour")
                                project_data["agency"] = parts[0].strip()
                                project_data["brands"] = parts[1].strip()

                            credit_blocks = soup.select("div.css-1t817sz")
                            for block in credit_blocks:
                                role_elem = block.select_one("h3")
                                role = role_elem.text.strip() if role_elem else None
                                names = [a.text.strip() for a in block.select("a")]
                                if not names:
                                    fallback = block.select_one("div.css-azlh8x")
                                    if fallback:
                                        names = [fallback.text.strip()]
                                for name in names:
                                    if role and name:
                                        project_data["credits"].append({
                                            "role": role,
                                            "name": name
                                        })
                                    if role and role.lower() == "année":
                                        project_data["year"] = name

                            image_blocks = soup.select("div.css-4kfmss div.css-o7drpz img")
                            for img in image_blocks:
                                src = img.get("src")
                                if src and src.startswith("http"):
                                    project_data["image_urls"].append(src)

                            iframe = soup.select_one("iframe[src*='vimeo.com'], iframe[src*='.mp4']")
                            if iframe:
                                video_src = iframe.get("src")
                                project_data["videos"].append({
                                    "video_url": video_src,
                                    "thumbnail": project_data["image_urls"][0] if project_data["image_urls"] else None
                                })

                            if not project_data["videos"]:
                                project_data["type"] = "image"

                            safe_name = sanitize_filename(project_data["name"] or "project")
                            json_path = os.path.join(folder, f"{safe_name}.json")
                            with open(json_path, "w", encoding="utf-8-sig") as f:
                                json.dump(project_data, f, indent=2, ensure_ascii=False)
                            print(f"✅ Saved: {safe_name}")

                            for i, img_url in enumerate(project_data["image_urls"], start=1):
                                ext = os.path.splitext(img_url)[-1].split('?')[0] or '.jpg'
                                filename = f"{safe_name}_{i}{ext}"
                                download_media(img_url, os.path.join(folder, filename))

                            for video in project_data["videos"]:
                                download_media(video["video_url"], os.path.join(folder, os.path.basename(video["video_url"])))

                        except Exception as e:
                            print(f"⚠️ Error while processing project: {e}")
                            continue

    driver.quit()

# Run
scrape_data()
