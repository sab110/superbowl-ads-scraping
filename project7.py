import time
import json
import re
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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
# Target Page
# -------------------
# base_url = "https://www.oneclub.org/awards/theoneshow/-award/58707/pink-chip/"
base_url ="https://www.oneclub.org/awards/theoneshow/-award/25347/the-refugee-nation/"
driver.get(base_url)
time.sleep(2)

# -------------------
# Accept cookies if button appears
# -------------------
try:
    accept_btn = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-tid='banner-accept']"))
    )
    accept_btn.click()
    time.sleep(1)
except:
    pass  # no cookie banner

soup = BeautifulSoup(driver.page_source, "html.parser")

# -------------------
# Basic Fields
# -------------------
award_name = soup.select_one(".box-black-top .row h2 span")
award_text = award_name.get_text(strip=True) if award_name else None

project_title = soup.select_one(".box-black-top h1")
project_title_text = project_title.get_text(strip=True) if project_title else None

# -------------------
# Agency
# -------------------
agency_text = None
for span in soup.select("h4 span:has(b)"):
    if "Agency" in span.get_text():
        b_tag = span.find("b")
        if b_tag:
            agency_text = b_tag.get_text(strip=True)

# -------------------
# Client
# -------------------
client_text = None
for span in soup.select("h4 span:has(b)"):
    if "Client" in span.get_text():
        b_tag = span.find("b")
        if b_tag:
            client_text = b_tag.get_text(strip=True)

# -------------------
# Category (sub)
# -------------------
category = soup.find("h4", {"class": "font-grey"})
category_text = category.get_text(strip=True) if category else None

# -------------------
# Award
# -------------------
award_div = soup.find("div", class_="pen-awards-box")
award_text_final = award_div.h6.get_text(strip=True) if award_div else None

# -------------------
# Descriptions (headings + text)
# -------------------
descriptions = []
for section in soup.select("div.row > div.col-xs-12"):
    h3 = section.find("h3")
    div = section.find("div", class_="font-grey")
    if h3 and div:
        descriptions.append({
            "heading": h3.get_text(strip=True),
            "text": div.get_text(" ", strip=True)
        })

# -------------------
# Extract year
# -------------------
year = None
if project_title_text:
    match = re.search(r"\b(19|20)\d{2}\b", project_title_text)
    if match:
        year = match.group(0)

if not year and award_text:
    match = re.search(r"\b(19|20)\d{2}\b", award_text)
    if match:
        year = match.group(0)

# -------------------
# Credits
# -------------------
credits = []
for c in soup.select(".credits-container .row > div"):
    role = c.find("h4")
    names = c.find("h6")
    if role and names:
        names_clean = [n.strip() for n in names.get_text("\n", strip=True).split("\n") if n.strip()]
        for nm in names_clean:
            credits.append({
                "role": role.get_text(strip=True),
                "name": nm
            })

# -------------------
# Sector / Tags
# -------------------
tags_div = soup.select_one(".tag-social-bar .left")
tags = [a.get_text(strip=True) for a in tags_div.find_all("a")] if tags_div else []

# -------------------
# Media (iterate using bullets)
# -------------------
image_urls = []
video_list = []

bullets = driver.find_elements(By.CSS_SELECTOR, ".ug-bullet")
for bullet in bullets:
    ActionChains(driver).move_to_element(bullet).click().perform()
    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Image
    img = soup.select_one(".ug-slide-wrapper[style*='z-index: 3'] img")
    if img:
        src = img.get("src")
        if src and src not in image_urls:
            image_urls.append(src)

    # Video
    try:
        play_btn = driver.find_element(By.CSS_SELECTOR, ".ug-slide-wrapper[style*='z-index: 3'] .ug-button-videoplay")
        if play_btn.is_displayed():
            ActionChains(driver).move_to_element(play_btn).click().perform()
            time.sleep(1)

            video_tag = driver.find_element(By.CSS_SELECTOR, ".ug-videoplayer video")
            video_src = video_tag.get_attribute("src")
            poster = video_tag.get_attribute("poster")

            if video_src and not any(v["video_url"] == video_src for v in video_list):
                video_list.append({
                    "video_url": video_src,
                    "thumbnail": poster
                })

            close_btn = driver.find_element(By.CSS_SELECTOR, ".ug-videoplayer-button-close")
            ActionChains(driver).move_to_element(close_btn).click().perform()
            time.sleep(1)
    except:
        pass

# -------------------
# Keep both images and videos
# -------------------
final_videos = video_list if video_list else None
final_images = image_urls  # always keep images, even if video exists

# -------------------
# Final JSON
# -------------------
data = {
    "origin": {
        "name": "The One Show",
        "url": base_url
    },
    "name": project_title_text,
    "type": "video" if final_videos else "image",
    "sector": ", ".join(tags) if tags else None,
    "countries": None,
    "brands": client_text,
    "agency": agency_text,
    "year": year,
    "award": award_text_final,
    "category": award_text,
    "subCategory": category_text,
    "description": descriptions,
    "credits": credits,
    "image_urls": final_images,   # keep images regardless
    "videos": final_videos,       # add video if exists
    "tags": None,
    "product": None
}


print(json.dumps(data, indent=2, ensure_ascii=False))
driver.quit()
