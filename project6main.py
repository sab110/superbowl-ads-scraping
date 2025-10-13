import time
import json
from selenium import webdriver
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import os

# Setup Chrome
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

driver = webdriver.Chrome(options=options)

output_file = "data.jsonl"

# --- Resume Support: Load already scraped (url, category, award, year) ---
scraped_keys = set()
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                if "origin" in obj and "url" in obj["origin"]:
                    key = (
                        obj["origin"]["url"],
                        obj.get("category"),
                        obj.get("award"),
                        obj.get("year")
                    )
                    scraped_keys.add(key)
            except:
                continue
    print(f"🔄 Resume enabled. Found {len(scraped_keys)} already-scraped (url, category, award, year) entries.")

# Loop over years 2012 → 2025
for year in range(2012, 2026):
    base_url = f"https://www.unblock.coffee/cnns/?adsyear={year}"
    print(f"\n🔎 Year {year}: Visiting {base_url}")
    driver.get(base_url)
    time.sleep(2)

    # Parse main page for category links
    soup = BeautifulSoup(driver.page_source, "html.parser")
    category_links = [a["href"] for a in soup.select("section.award-categories-grid a.award-category-card")]
    print(f"  Found {len(category_links)} categories for {year}")

    # Loop through each category
    for cidx, category_url in enumerate(category_links, start=1):
        category_name = category_url.split("/")[-1].split("?")[0]
        print(f"  [{cidx}/{len(category_links)}] Category: {category_name}")
        driver.get(category_url)
        time.sleep(2)

        cat_soup = BeautifulSoup(driver.page_source, "html.parser")
        project_items = cat_soup.select("div.item")

        print(f"     Found {len(project_items)} projects in category.")

        # Loop through projects directly from category page
        for pidx, item in enumerate(project_items, start=1):
            link_tag = item.select_one("div.campaign-thumb a")
            project_url = link_tag["href"] if link_tag else None

            # Extract award before skip check
            award_tag = item.select_one(".level2, .level3, .level4, .level5")
            award = award_tag.get_text(strip=True) if award_tag else None

            key = (project_url, category_name, award, str(year))
            if not project_url or key in scraped_keys:
                print(f"       -> Skipping (already scraped): {project_url} in {category_name} [{award}] {year}")
                continue

            print(f"       -> Scraping Project {pidx}/{len(project_items)}: {project_url}")

            # Extract directly from item
            name_tag = item.select_one("h4 a")
            name = name_tag.get_text(strip=True) if name_tag else None

            agency = None
            agency_tag = item.find("b", string="Agency:")
            if agency_tag and agency_tag.find_next("a"):
                agency = agency_tag.find_next("a").get_text(strip=True)

            brand = None
            brand_tag = item.find("b", string="Brand:")
            if brand_tag and brand_tag.find_next("a"):
                brand = brand_tag.find_next("a").get_text(strip=True)

            country = None
            small = item.select_one("p small")
            if small:
                country = small.get_text(strip=True).strip("()")

            # Collect image
            images = []
            img_tag = item.select_one("div.campaign-thumb img")
            if img_tag and img_tag.get("src"):
                images.append(img_tag["src"])

            # Build JSON object
            project_obj = {
                "origin": {
                    "name": "unblock.coffee",
                    "url": project_url
                },
                "name": name,
                "type": "campaign",
                "sector": None,
                "countries": country,
                "brands": brand,
                "agency": agency,
                "year": str(year),
                "award": award,
                "category": category_name,
                "subCategory": None,
                "description": None,
                "credits": [],
                "image_urls": images,
                "videos": [],
                "tags": None,
                "product": None
            }

            # Save immediately
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(project_obj, ensure_ascii=False) + "\n")

            scraped_keys.add(key)
            print("          ✅ Saved")

driver.quit()
print(f"\n✅ Finished scraping. Data saved to {output_file}")
