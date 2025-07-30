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
def extract_metadata_and_media(driver, campaign_url, year,agency, award, advertiser, country,title):
    driver.get(campaign_url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    article = soup.find("article", class_="award__article")
    if not article:
        print(f"⚠️ No main article found in {campaign_url}")
        return None

    # Title
    # title_tag = article.find("h4")
    # title = title_tag.text.strip('" \n') if title_tag else None

    # Meta Info
    meta_div = soup.find("div", class_="app__meta app__meta--award meta")
    # category = meta_div.find("div", class_="meta__category").text.strip() if meta_div else None
    # Extract all meta__category values and pick the last one
    category_divs = soup.find_all("div", class_="meta__category")
    category = category_divs[-1].get_text(strip=True) if category_divs else None

    # award = meta_div.find("div", class_="meta__award").text.strip() if meta_div else None

    # Credits
    credits = []
    # advertiser = None
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
                        # if "advertiser" in role.lower():
                            # advertiser = name
                        if "product" in role.lower():
                            product = name

    # Gallery (videos & images) — revised to get ALL from all media sections
    image_urls = []
    # video_url = None
    # poster_url = None
    video_entries = []


    media_sections = soup.find_all("section", class_="award__section--with-media")
    for section in media_sections:
        media_div = section.find("div", class_="award__media")
        if not media_div:
            continue

        # Extract <video> (if any)
        # video = media_div.find("video")
        # if video:
        #     if video.find("source"):
        #         video_url = video.find("source").get("src")
        #     poster_url = video.get("poster")
        #     if poster_url and poster_url not in image_urls:
        #         image_urls.append(poster_url)
        #     continue # skip <img> if video is found in this block

        for video in media_div.find_all("video"):
            source_tag = video.find("source")
            video_url = source_tag.get("src") if source_tag else None
            poster_url = video.get("poster")
            if video_url:
                video_entries.append({
                    "video_url": video_url,
                    "thumbnail": poster_url
                })
                if poster_url and poster_url not in image_urls:
                    image_urls.append(poster_url)


        # Extract <img> inside <a>
        a_tag = media_div.find("a", href=True)
        if a_tag:
            img_tag = a_tag.find("img")
            if img_tag and img_tag.get("src"):
                image_url = img_tag["src"]
                if image_url not in image_urls:
                    image_urls.append(image_url)

    # Final metadata
    return {
        "origin": {"name": "epica-awards.com", "url": campaign_url},
        "name": title if title else None,
        "type": "video" if video_entries else "image",
        "sector": None,
        "countries": country if country else None,
        "brands": advertiser if advertiser else None,
        "agency": agency if agency else None,
        "year": str(year) if year else None,
        "award": award if award else None,
        "category": category if category else None,
        "subCategory": None,
        "description": article.find("p", class_="award__description").text.strip() if article.find("p", class_="award__description") else None,
        "credits": credits,
        "image_urls": image_urls,
        # "videos": [{
        # "thumbnail": poster_url if poster_url else None,
        # "video_url": video_url if video_url else None
        # }] if video_url else [],
        "videos": video_entries,
        "tags": None,
        "product": product if product else None

    }

# === MAIN SCRAPER ===
# options = uc.ChromeOptions()
# # options.add_argument("--headless=new")
# options.add_argument("--disable-gpu")
# options.add_argument("--window-size=1920,1080")
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-blink-features=AutomationControlled")
# driver = uc.Chrome(use_subprocess=True, options=options)

options = uc.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")

# Optional but useful:
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
options.add_argument(f"user-agent={user_agent}")

# Final driver launch
driver = uc.Chrome(use_subprocess=True, options=options)

for year in YEARS:
    print(f"\n📆 Year {year}")
    driver.get(f"{BASE_URL}/{year}")
    time.sleep(0.1)
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
        time.sleep(0.1)

        cat_soup = BeautifulSoup(driver.page_source, "html.parser")
        project_section = cat_soup.find('section', class_='app__cards')
        if not project_section:
            print(f"⚠️ No campaign section found for {cat_name}")
            continue

        # project_articles = project_section.find_all('a', href=True)
        # campaign_links = list(set(urljoin(BASE_URL, a['href']) for a in project_articles))
        # print(f"🔗 Found {len(campaign_links)} campaign(s)")

        project_cards = project_section.find_all('div', class_='app__card')

        for card in project_cards:
            # Extract campaign URL from internal <a>
            a_tag = card.find("a", class_="card__link", href=True)
            if not a_tag:
                print("⚠️ Skipping card (no <a> tag)")
                continue
            campaign_url = urljoin(BASE_URL, a_tag['href'])
            print(f"🔍 Processing: {campaign_url}")

            # Extract metadata from card__meta
            agency = award = advertiser = country = None
            card_meta = card.find("div", class_="card__meta")
            title = card.find("div", class_="card__title").text.strip() if card.find("div", class_="card__title") else None
            title = title.replace('"', '').strip() if title else None
            if card_meta:
                for row in card_meta.find_all("div", class_="card__row"):
                    label_tag = row.find("span", class_="card__label")
                    value_tag = row.find("span", class_="card__value")
                    if not label_tag or not value_tag:
                        continue
                    label = label_tag.text.strip().lower()
                    value = value_tag.text.strip()
                    if "entrant" in label:
                        agency = value
                    elif "award" in label:
                        award = value
                    elif "advertiser" in label:
                        advertiser = value
                    elif "country" in label:
                        country = value

            # Now pass all values to metadata extraction
            metadata = extract_metadata_and_media(driver, campaign_url, year, agency, award, advertiser, country,title)

            if not metadata:
                print("⚠️ Skipping campaign (metadata issue)")
                continue

            # proj_slug = slugify(metadata["name"])
            # folder = get_unique_folder(os.path.join(OUTPUT_ROOT, str(year), slugify(metadata["category"]), title))
            folder = get_unique_folder(os.path.join(OUTPUT_ROOT, str(year), slugify(metadata["category"]), slugify(title)))
            os.makedirs(folder, exist_ok=True)
            safe_title = re.sub(r'[<>:"/\\|?*]', '-', title)  # Replace invalid filename characters
            print(f"📂 Saving to: {safe_title}")
            with open(os.path.join(folder, f"{safe_title}.json"), "w", encoding="utf-8-sig") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # if metadata["videos"]:
            #     video_data = metadata["videos"][0]  # first video
            #     if video_data.get("video_url"):
            #         try:
            #             vdata = requests.get(video_data["video_url"]).content
            #             with open(os.path.join(folder, "video.mp4"), "wb") as vf:
            #                 vf.write(vdata)
            #             print("✅ Video saved")
            #         except Exception as e:
            #             print(f"⚠️ Video download failed: {e}")

            if metadata["videos"]:
                for idx, video_data in enumerate(metadata["videos"]):
                    if video_data.get("video_url"):
                        try:
                            vdata = requests.get(video_data["video_url"]).content
                            with open(os.path.join(folder, f"{safe_title}_{idx+1}.mp4"), "wb") as vf:
                                vf.write(vdata)
                            print(f"🎥 Video {idx+1} saved")
                        except Exception as e:
                            print(f"⚠️ Video {idx+1} download failed: {e}")


            for idx, img_url in enumerate(metadata["image_urls"]):
                try:
                    idata = requests.get(img_url).content
                    with open(os.path.join(folder, f"{safe_title}_{idx+1}.jpg"), "wb") as imgf:
                        imgf.write(idata)
                    print(f"🖼️ Image {idx+1} saved")
                except Exception as e:
                    print(f"⚠️ Image {idx+1} download failed: {e}")


driver.quit()
print("\n🎉 Done scraping all campaigns.")
