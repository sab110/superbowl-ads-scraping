# # Links capture for palmares pages with infinite scroll
# import time
# from bs4 import BeautifulSoup
# import undetected_chromedriver as uc
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException, NoSuchElementException

# base_url = "https://competition.leclubdesda.org"
# start_url = base_url + "/#/palmares"

# options = uc.ChromeOptions()
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-gpu")
# options.add_argument("--window-size=1920,1080")

# driver = uc.Chrome(use_subprocess=True, options=options)
# driver.get(start_url)

# # Wait for first link to appear
# WebDriverWait(driver, 15).until(
#     EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='#/palmares/']"))
# )

# print("⚡ Starting auto-scroll until no more results...")

# # Keep scrolling until "more-loading" disappears completely
# while True:
#     # Scroll down
#     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#     time.sleep(2)

#     try:
#         # Check if loader is still visible
#         loader = driver.find_element(By.CSS_SELECTOR, "div.more-loading")
#         if not loader.is_displayed():
#             print("✅ Loader disappeared, reached end of page.")
#             break
#     except NoSuchElementException:
#         print("✅ Loader element not found, finished loading.")
#         break

# # Now parse final HTML
# html = driver.page_source
# soup = BeautifulSoup(html, "html.parser")

# links = []
# for a in soup.find_all("a", href=True):
#     if a["href"].startswith("#/palmares/"):
#         full_url = base_url + a["href"]
#         if full_url not in links:
#             links.append(full_url)

# with open("palmares_links.txt", "w", encoding="utf-8") as f:
#     f.write("\n".join(links))

# print(f"🎉 Done! Saved {len(links)} links to palmares_links.txt")

# driver.quit()
# del driver


# Links capture + metadata for palmares pages with infinite scroll
import time
import json
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

base_url = "https://competition.leclubdesda.org"
start_url = base_url + "/#/palmares"

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = uc.Chrome(use_subprocess=True, options=options)
driver.get(start_url)

# Wait for first link to appear
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='#/palmares/']"))
)

print("⚡ Starting auto-scroll until no more results...")

# Keep scrolling until "more-loading" disappears completely
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    try:
        loader = driver.find_element(By.CSS_SELECTOR, "div.more-loading")
        if not loader.is_displayed():
            print("✅ Loader disappeared, reached end of page.")
            break
    except NoSuchElementException:
        print("✅ Loader element not found, finished loading.")
        break

# Parse final HTML
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

projects = []

for card in soup.select("div.gutter.creation-category"):
    link_tag = card.select_one("a[href^='#/palmares/']")
    if not link_tag:
        continue
    href = link_tag["href"]
    project_url = base_url + href

    # extract details
    agency_name = card.select_one("strong.campagne-name")
    annonceur = card.select_one("span.annonceur-name")
    creation = card.select_one("span.creation-name")
    category_parent = card.select_one("span.category-name.category-parent-name strong")
    category_child = card.select_one("span.category-name.category-child-name")
    award = card.select_one("span.category-name.award-name strong")

    # cover image from style attr
    bg_div = card.select_one("div.bg")
    cover_image = None
    if bg_div and "background-image" in bg_div.get("style", ""):
        style = bg_div["style"]
        cover_image = style.split("url(")[1].split(")")[0].strip('"')

    project_data = {
        "origin": {"name": "leclubdesda.org", "url": project_url},
        "name": creation.text.strip() if creation else None,
        "type": None,
        "sector": None,
        "countries": "France",
        "brands": annonceur.text.strip() if annonceur else None,
        "agency": agency_name.text.strip() if agency_name else None,
        "year": 2025,
        "award": award.text.strip() if award else None,
        "category": category_parent.text.strip() if category_parent else None,
        "subCategory": category_child.text.strip() if category_child else None,
        "description": None,
        "credits": [],
        "image_urls": [cover_image] if cover_image else [],
        "videos": [],
        "tags": None,
        "product": None
    }

    projects.append(project_data)

# Save all projects in JSON
with open("palmares_data.json", "w", encoding="utf-8") as f:
    json.dump(projects, f, indent=2, ensure_ascii=False)

print(f"🎉 Done! Saved {len(projects)} projects to palmares_data.json")

driver.quit()
del driver
