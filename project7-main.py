import time
import json
import re
import requests
import platform
from pathlib import Path
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# -------------------
# Helpers
# -------------------
def safe_filename(name: str, max_length: int = 100) -> str:
    safe = re.sub(r'[\\/*?:"<>|]', "_", name.strip())
    safe = safe.rstrip(" .,")
    if len(safe) > max_length:
        import hashlib
        hash_suffix = hashlib.md5(safe.encode()).hexdigest()[:6]
        safe = safe[:max_length-7] + "_" + hash_suffix
    return safe or "Unnamed"

def windows_longpath(p: Path) -> str:
    if platform.system().lower().startswith("win"):
        try:
            p_abs = p if p.is_absolute() else p.resolve(strict=False)
        except Exception:
            p_abs = (Path.cwd() / p)
        p_str = str(p_abs)
        if p_str.startswith("\\\\?\\"):
            return p_str
        return "\\\\?\\" + p_str
    return str(p)

def download_file(url, dest_path: Path):
    try:
        if dest_path.exists():
            return
        r = requests.get(url, timeout=20, stream=True)
        if r.status_code == 200:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(windows_longpath(dest_path), "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            print(f"📥 Saved: {dest_path}")
        else:
            print(f"⚠️ Failed download: {url}")
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")


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
# Load index page
# -------------------
# list_url = "https://www.oneclub.org/awards/theoneshow/-archive/awards/2025/all/all/select"
list_url = "https://www.oneclub.org/awards/theoneshow/-archive/awards/1991/all/all/select"
driver.get(list_url)
time.sleep(3)

# Accept cookies (global)
try:
    accept_btn = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-tid='banner-accept']"))
    )
    accept_btn.click()
    print("✅ Accepted cookies on index page")
    time.sleep(1)
except:
    print("ℹ️ No cookies banner on index page")

# -------------------
# Hybrid scrolling + click until all projects loaded
# -------------------
project_links = set()
scroll_count = 0
retries = 0
max_retries = 5
backup_file = Path("project_links_backup.txt")

while True:
    scroll_count += 1
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2.5)  # wait for lazy load

    soup = BeautifulSoup(driver.page_source, "html.parser")
    new_links = [a["href"] for a in soup.select(".filter-grid-item .box-item a.item-heading")]

    before = len(project_links)
    project_links.update(new_links)
    added = len(project_links) - before
    print(f"🔄 Scroll {scroll_count}: found {len(new_links)} links on page, added {added} new (total {len(project_links)})")

    # Save new unique links to backup file
    if added > 0:
        with open(backup_file, "a", encoding="utf-8") as f:
            for link in new_links:
                if link not in project_links:  # safeguard (though set already filters)
                    continue
                f.write(link + "\n")
        print(f"💾 Backup updated with {added} new links (total {len(project_links)})")
        retries = 0
    else:
        retries += 1
        print(f"⚠️ No new links this scroll (retry {retries}/{max_retries})")

        # Try clicking the plus button if no new links
        try:
            load_more = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".load-more a"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
            ActionChains(driver).move_to_element(load_more).click().perform()
            print("   ⬇️ Clicked 'Load More' button as fallback")
            time.sleep(1.5)
            retries = 0  # reset since we tried another method
            continue
        except:
            pass

    # Stop conditions
    try:
        load_more = driver.find_element(By.CSS_SELECTOR, ".load-more a")
        if not load_more.is_displayed():
            print("✅ 'Load More' button disappeared — all projects loaded")
            break
    except:
        print("✅ No 'Load More' button found — all projects loaded")
        break

    if retries >= max_retries:
        print("✅ No new links detected after multiple attempts — stopping scroll loop")
        break

project_links = list(project_links)
print(f"🔗 Found total {len(project_links)} unique projects")



# -------------------
# Process each project
# -------------------
for idx, link in enumerate(project_links, 1):
    project_url = link if link.startswith("http") else f"https://www.oneclub.org{link}"
    print(f"\n▶️ Opening project {idx}/{len(project_links)}: {project_url}")
    driver.get(project_url)
    time.sleep(0.1)

    # Accept cookies inside project page
    try:
        accept_btn = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-tid='banner-accept']"))
        )
        accept_btn.click()
        print("   ✅ Accepted cookies on project page")
        time.sleep(0.1)
    except:
        pass

    psoup = BeautifulSoup(driver.page_source, "html.parser")

    # -------- Basic fields --------
    award_name = psoup.select_one(".box-black-top .row h2 span")
    award_text = award_name.get_text(strip=True) if award_name else None
    if award_text:
        award_text = re.sub(r"\bPencil\b", "", award_text, flags=re.I).strip()

    project_title = psoup.select_one(".box-black-top h1")
    project_title_text = project_title.get_text(strip=True) if project_title else "Unnamed"

    agency_text, client_text = None, None
    for span in psoup.select("h4 span:has(b)"):
        if "Agency" in span.get_text():
            agency_text = span.find("b").get_text(strip=True)
        if "Client" in span.get_text():
            client_text = span.find("b").get_text(strip=True)

    category = psoup.find("h4", {"class": "font-grey"})
    category_text = category.get_text(strip=True) if category else "Uncategorized"

    award_div = psoup.find("div", class_="pen-awards-box")
    award_text_final = award_div.h6.get_text(strip=True) if award_div else None
    if award_text_final:
        award_text_final = re.sub(r"\bPencil\b", "", award_text_final, flags=re.I).strip()

    # -------- Clean category --------
    category_text_cleaned = None
    if award_text:
        category_text_cleaned = re.sub(r"\b(19|20)\d{2}\b", "", award_text)  # remove years
        category_text_cleaned = re.sub(r"\bOne\s*Show\b", "", category_text_cleaned, flags=re.I)
        category_text_cleaned = re.sub(r"[-–:|]+", " ", category_text_cleaned)
        category_text_cleaned = re.sub(r"\s{2,}", " ", category_text_cleaned).strip()
    if not category_text_cleaned:
        category_text_cleaned = "Uncategorized"

    # -------- Descriptions --------
    descriptions = []
    for section in psoup.select("div.row > div.col-xs-12"):
        h3 = section.find("h3")
        div = section.find("div", class_="font-grey")
        if h3 and div:
            descriptions.append({
                "heading": h3.get_text(strip=True),
                "text": div.get_text(" ", strip=True)
            })

    # -------- Year --------
    year = None
    if project_title_text:
        m = re.search(r"\b(19|20)\d{2}\b", project_title_text)
        if m: year = m.group(0)
    if not year and award_text:
        m = re.search(r"\b(19|20)\d{2}\b", award_text)
        if m: year = m.group(0)
    if not year:
        year = "Unknown"

    # -------- Credits --------
    credits = []
    for c in psoup.select(".credits-container .row > div"):
        role = c.find("h4")
        names = c.find("h6")
        if role and names:
            names_clean = [n.strip() for n in names.get_text("\n", strip=True).split("\n") if n.strip()]
            for nm in names_clean:
                credits.append({"role": role.get_text(strip=True), "name": nm})

    # -------- Tags --------
    tags_div = psoup.select_one(".tag-social-bar .left")
    tags = [a.get_text(strip=True) for a in tags_div.find_all("a")] if tags_div else []

    # -------- Media --------
    image_urls, video_list = [], []
    bullets = driver.find_elements(By.CSS_SELECTOR, ".ug-bullet")

    if bullets:
        print(f"   🎯 Found {len(bullets)} bullets, iterating...")
        for bidx, bullet in enumerate(bullets, 1):
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", bullet)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", bullet)
                time.sleep(0.5)

                msoup = BeautifulSoup(driver.page_source, "html.parser")

                img = msoup.select_one(".ug-slide-wrapper[style*='z-index: 3'] img")
                if img:
                    src = img.get("src")
                    if src and src not in image_urls:
                        image_urls.append(src)
                        print(f"      🖼️ Collected image {len(image_urls)}")

                try:
                    play_btn = driver.find_element(
                        By.CSS_SELECTOR,
                        ".ug-slide-wrapper[style*='z-index: 3'] .ug-button-videoplay"
                    )
                    if play_btn.is_displayed():
                        driver.execute_script("arguments[0].click();", play_btn)
                        time.sleep(0.5)

                        video_tag = driver.find_element(By.CSS_SELECTOR, ".ug-videoplayer video")
                        video_src = video_tag.get_attribute("src")
                        poster = video_tag.get_attribute("poster")

                        if video_src and not any(v["video_url"] == video_src for v in video_list):
                            video_list.append({"video_url": video_src, "thumbnail": poster})
                            print(f"      🎬 Collected video {len(video_list)}")

                        close_btn = driver.find_element(By.CSS_SELECTOR, ".ug-videoplayer-button-close")
                        driver.execute_script("arguments[0].click();", close_btn)
                        time.sleep(0.3)
                except:
                    pass

            except Exception as e:
                print(f"      ⚠️ Skipped bullet {bidx}: {e}")
    else:
        print("   ⚠️ No bullets found → grabbing default media")
        msoup = BeautifulSoup(driver.page_source, "html.parser")
        img = msoup.select_one(".ug-item-wrapper img")
        if img:
            image_urls.append(img.get("src"))
        video = msoup.select_one(".ug-videoplayer video")
        if video:
            video_list.append({"video_url": video.get("src"), "thumbnail": video.get("poster")})

    # -------- Save files --------
    if not project_title_text or project_title_text == "Unnamed":
        # if project name is null, fallback to client + year
        folder_name = safe_filename(f"{client_text}_{year}" if client_text else f"Unnamed_{year}")
    else:
        folder_name = safe_filename(project_title_text)

    project_dir = Path("The One Show 2") / year / safe_filename(category_text_cleaned) / folder_name
    project_dir.mkdir(parents=True, exist_ok=True)
    # project_dir = Path("The One Show") / year / safe_filename(category_text_cleaned) / safe_filename(project_title_text)
    # project_dir.mkdir(parents=True, exist_ok=True)

    # for i, img_url in enumerate(image_urls, 1):
    #     dest = project_dir / f"{safe_filename(project_title_text)}_{i}.jpg"
    #     download_file(img_url, dest)

    # for i, v in enumerate(video_list, 1):
    #     dest = project_dir / f"{safe_filename(project_title_text)}_{i}.mp4"
    #     download_file(v["video_url"], dest)
    # Save images
    for i, img_url in enumerate(image_urls, 1):
        dest = project_dir / f"{folder_name}_{i}.jpg"
        download_file(img_url, dest)

    # Save videos
    for i, v in enumerate(video_list, 1):
        dest = project_dir / f"{folder_name}_{i}.mp4"
        download_file(v["video_url"], dest)

    # -------- Save JSON --------
    data = {
        "origin": {"name": "The One Show", "url": project_url},
        "name": project_title_text,
        "type": "video" if video_list else "image",
        "sector": ", ".join(tags) if tags else None,
        "countries": None,
        "brands": client_text,
        "agency": agency_text,
        "year": year,
        "award": award_text_final,
        "category": category_text_cleaned,
        "subCategory": category_text,
        "description": descriptions,
        "credits": credits,
        "image_urls": image_urls,
        "videos": video_list,
        "tags": None,
        "product": None
    }

    # with open(project_dir / f"{safe_filename(project_title_text)}.json", "w", encoding="utf-8") as f:
    #     json.dump(data, f, ensure_ascii=False, indent=2)

    # print(f"✅ Finished {project_title_text}")
    with open(project_dir / f"{folder_name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Finished {folder_name}")

driver.quit()
