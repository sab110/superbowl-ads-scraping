from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import re
import time
import undetected_chromedriver as uc
import os

# Read URLs from file
with open(r"project8\urls.txt", "r") as f:
    urls = [line.strip() for line in f.readlines() if line.strip()]

# Configure Selenium (headless Chrome)
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.90 Safari/537.36")

driver = webdriver.Chrome(options=options)

output_file = "superbowl_ads_archive.json"

# Initialize file if not exists
if not os.path.exists(output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

for url in urls:
    # Extract year from URL
    match = re.search(r"(19|20)\d{2}", url)
    year = match.group(0) if match else None

    print(f"\n📂 Scraping year {year} from {url} ...")
    try:
        driver.get(url)
        time.sleep(3)  # wait for page to fully load
    except Exception as e:
        print(f"❌ Failed to load {url}: {e}")
        continue

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Each ad is inside <article class="cactus-post-item">
    articles = soup.find_all("article", class_="cactus-post-item")

    year_ads = []

    for article in articles:
        title_tag = article.find("h3", class_="cactus-post-title")
        link_tag = title_tag.find("a") if title_tag else None

        title = link_tag.get_text(strip=True) if link_tag else None
        link = link_tag["href"] if link_tag else None

        project = {
            "title": title,
            "link": link,
            "year": year,
            "source_page": url
        }

        year_ads.append(project)
        print(f"   ✅ Extracted: {title}")

    # Append year_ads to the JSON file immediately
    if year_ads:
        with open(output_file, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data.extend(year_ads)
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"💾 Saved {len(year_ads)} ads for {year} into {output_file}")

driver.quit()

print("\n🎉 Scraping completed!")
