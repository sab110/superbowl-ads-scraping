import os
import re
import json
import time
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

# === CONFIGURATION ===
BASE_URL = "https://winners.epica-awards.com"
YEARS = list(range(2024, 2012, -1))
OUTPUT_ROOT = "Epica"

# === UTILITY FUNCTIONS ===
def slugify(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '-', text.lower()).strip('-')

def get_unique_folder(path):
    counter = 1
    orig = path
    while os.path.exists(path):
        path = f"{orig}_{counter}"
        counter += 1
    return path

# === SCRAPER FUNCTIONS ===
def extract_metadata_and_media(driver, campaign_url, year):
    driver.get(campaign_url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    article = soup.find("article", class_="award__article")
    if not article:
        print(f"⚠️ No main article found in {campaign_url}")
        return None

    # Title
    title_tag = article.find("h4")
    title = title_tag.text.strip('" \n') if title_tag else "Untitled"

    # Meta Info
    meta_div = soup.find("div", class_="app__meta app__meta--award meta")
    category = meta_div.find("div", class_="meta__category").text.strip() if meta_div else None
    award = meta_div.find("div", class_="meta__award").text.strip() if meta_div else None

    # Credits
    credits = []
    agency = None
    product = None
    credits_section = soup.find("div", class_="award__credits")
    if credits_section:
            for li in credits_section.find_all("li"):
                role_tag = li.find("b")
                if role_tag:
                    role = role_tag.text.strip()
                    name = li.text.replace(role_tag.text, "").strip(": \n")
                    if name:
                        # Skip roles that are handled separately
                        skip_roles = ["title", "product", "advertiser"]
                        if role.lower() not in skip_roles:
                            credits.append({"role": role, "name": name})
                        if "advertiser" in role.lower():
                            agency = name
                        if "product" in role.lower():
                            product = name

    # Gallery (videos & images)
    gallery_section = soup.find("section", id="gallery")
    image_urls = []
    video_url = None
    poster_url = None
    if gallery_section:
        for a in gallery_section.select("a.galeria"):
            if a.has_attr("data-video"):
                video_url = a["data-video"]
            if a.has_attr("data-image"):
                image_urls.append(a["data-image"])
            elif a.img and a.img.has_attr("src"):
                image_urls.append(a.img["src"])

    if not image_urls and article.find("img"):
        image_urls.append(article.find("img")["src"])

    if article.find("video"):
        v = article.find("video")
        if v.find("source"):
            video_url = v.find("source").get("src")
        poster_url = v.get("poster")
        if poster_url and poster_url not in image_urls:
            image_urls.insert(0, poster_url)

    # Final metadata
    return {
        "origin": {"name": "epica-awards.com", "url": campaign_url},
        "name": title,
        "type": "video" if video_url else "image",
        "agency": agency,
        "year": str(year),
        "award": award,
        "category": category,
        "product": product,
        "credits": credits,
        "video_url": video_url,
        "poster_url": poster_url,
        "image_urls": image_urls
    }

# === MAIN SCRAPER ===
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
driver = uc.Chrome(use_subprocess=True, options=options)

for year in YEARS:
    print(f"\n📆 Year {year}")
    driver.get(f"{BASE_URL}/{year}")
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Category extraction
    sections = soup.select("div.listing__sections section.listing__section")
    categories = [(a.text.strip(), urljoin(BASE_URL, a["href"])) 
                  for section in sections 
                  for a in section.select("div.listing__items a.listing__item") if a.get("href")]

    if not categories:
        print(f"❌ No categories found for {year}")
        continue

    for cat_name, cat_url in categories:
        cat_slug = slugify(cat_name)
        print(f"📂 Category: {cat_name} → {cat_url}")
        driver.get(cat_url)
        time.sleep(2)

        cat_soup = BeautifulSoup(driver.page_source, "html.parser")
        project_section = cat_soup.find('section', class_='app__cards')
        if not project_section:
            print(f"⚠️ No campaign section found for {cat_name}")
            continue

        project_articles = project_section.find_all('a', href=True)
        campaign_links = list(set(urljoin(BASE_URL, a['href']) for a in project_articles))
        print(f"🔗 Found {len(campaign_links)} campaign(s)")

        for campaign_url in campaign_links:
            print(f"🔍 Processing: {campaign_url}")
            metadata = extract_metadata_and_media(driver, campaign_url, year)
            if not metadata:
                print("⚠️ Skipping campaign (metadata issue)")
                continue

            proj_slug = slugify(metadata["name"])
            folder = get_unique_folder(os.path.join(OUTPUT_ROOT, str(year), cat_slug, proj_slug))
            os.makedirs(folder, exist_ok=True)

            # Save metadata
            with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8-sig") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # Save video
            if metadata["video_url"]:
                try:
                    vdata = requests.get(metadata["video_url"]).content
                    with open(os.path.join(folder, "video.mp4"), "wb") as vf:
                        vf.write(vdata)
                    print("✅ Video saved")
                except Exception as e:
                    print(f"⚠️ Video download failed: {e}")

            # Save all images
            for idx, img_url in enumerate(metadata["image_urls"]):
                try:
                    idata = requests.get(img_url).content
                    with open(os.path.join(folder, f"image_{idx+1}.jpg"), "wb") as imgf:
                        imgf.write(idata)
                    print(f"🖼️ Image {idx+1} saved")
                except Exception as e:
                    print(f"⚠️ Image {idx+1} download failed: {e}")

driver.quit()
print("\n🎉 Done scraping all campaigns.")
