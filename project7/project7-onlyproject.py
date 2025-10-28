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
        if not url or dest_path.exists():
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
# Read project links from file
# -------------------
links_file = Path(r"project7\ProjectUrls\adce_awards_project_links.txt")
if not links_file.exists():
    print("❌ oneasia_awards_project_links.txt not found!")
    driver.quit()
    exit()

with open(links_file, "r", encoding="utf-8") as f:
    project_links = [line.strip() for line in f if line.strip()]

print(f"✅ Loaded {len(project_links)} project links from {links_file}")

# -------------------
# Process each project
# -------------------
for idx, project_url in enumerate(project_links, 1):
    print(f"\n▶️ Project {idx}/{len(project_links)}: {project_url}")
    driver.get(project_url)
    time.sleep(0.5)

    psoup = BeautifulSoup(driver.page_source, "html.parser")

    # --- Metadata
    award_name = psoup.select_one(".box-black-top .row h2 span")
    award_text = award_name.get_text(strip=True) if award_name else None
    if award_text:
        award_text = re.sub(r"\bPencil\b", "", award_text, flags=re.I).strip()

    project_title = psoup.select_one(".box-black-top h1")
    project_title_text = project_title.get_text(strip=True) if project_title else "Unnamed"
    agency_text = client_text = None
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
    # category_text_cleaned = None
    # if award_text:
    #     category_text_cleaned = re.sub(r"\b(19|20)\d{2}\b", "", award_text)  # remove years
    #     category_text_cleaned = re.sub(r"\bOne\s*Show\b", "", category_text_cleaned, flags=re.I)
    #     category_text_cleaned = re.sub(r"[-–:|]+", " ", category_text_cleaned)
    #     category_text_cleaned = re.sub(r"\s{2,}", " ", category_text_cleaned).strip()
    # if not category_text_cleaned:
    #     category_text_cleaned = "Uncategorized"
    category_text_cleaned = None
    if award_text:
        category_text_cleaned = award_text

        # Remove years (e.g., 1990–2099)
        category_text_cleaned = re.sub(r"\b(19|20)\d{2}\b", "", category_text_cleaned)

        # Remove award brand names dynamically
        unwanted_brands = [
            "One Show",
            "TDC Awards",
            "OneAsia",
            "ADC Awards",
            "ADCE Awards",
            "Young Ones",
            "ADC Europe"
        ]
        for brand in unwanted_brands:
            category_text_cleaned = re.sub(rf"\b{re.escape(brand)}\b", "", category_text_cleaned, flags=re.I)

        # Clean up leftover symbols and spaces
        category_text_cleaned = re.sub(r"[-–:|]+", " ", category_text_cleaned)   # replace separators with space
        category_text_cleaned = re.sub(r"\s{2,}", " ", category_text_cleaned).strip()  # collapse spaces

    if not category_text_cleaned:
        category_text_cleaned = "Uncategorized"


    # -------- Tags --------
    tags_div = psoup.select_one(".tag-social-bar .left")
    tags = [a.get_text(strip=True) for a in tags_div.find_all("a")] if tags_div else []

    # -------- Descriptions --------
    # descriptions = []
    # for section in psoup.select("div.row > div.col-xs-12"):
    #     h3 = section.find("h3")
    #     div = section.find("div", class_="font-grey")
    #     if h3 and div:
    #         descriptions.append({
    #             "heading": h3.get_text(strip=True),
    #             "text": div.get_text(" ", strip=True)
    #         })
    # -------- Descriptions --------
    descriptions = []
    for section in psoup.select("div.row > div.col-xs-12"):
        h3 = section.find("h3")
        div = section.find("div", class_="font-grey")

        if h3 and div:
            # Case 1: has heading and text
            descriptions.append({
                "heading": h3.get_text(strip=True),
                "text": div.get_text(" ", strip=True)
            })
        elif div:
            # Case 2: only text block, no heading
            descriptions.append({
                "heading": None,
                "text": div.get_text(" ", strip=True)
            })


    # -------- Credits --------
    credits = []
    for c in psoup.select(".credits-container .row > div"):
        role = c.find("h4")
        names = c.find("h6")
        if role and names:
            names_clean = [n.strip() for n in names.get_text("\n", strip=True).split("\n") if n.strip()]
            for nm in names_clean:
                credits.append({"role": role.get_text(strip=True), "name": nm})

    # -------- Year --------
    year = None
    if award_text:
        m = re.search(r"\b(19|20)\d{2}\b", award_text)
        if m: year = m.group(0)
    if not year and project_title_text:
        m = re.search(r"\b(19|20)\d{2}\b", project_title_text)
        if m: year = m.group(0)
    if not year:
        year = "Unknown"

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

    # --- Folder naming
    # if not project_title_text or project_title_text == "Unnamed":
    #     folder_name = safe_filename(f"{client_text}_{year}" if client_text else f"Unnamed_{year}")
    # else:
    #     folder_name = safe_filename(project_title_text)

    # project_dir = Path("The One Show Data") / year / safe_filename(category_text_cleaned) / folder_name
    # project_dir.mkdir(parents=True, exist_ok=True)
    # --- Folder naming
    if not project_title_text or project_title_text == "Unnamed":
        folder_name = safe_filename(f"{client_text}_{year}" if client_text else f"Unnamed_{year}")
    else:
        folder_name = safe_filename(project_title_text)

    base_dir = Path("ADCE Awards") / year / safe_filename(category_text_cleaned)

    # ensure uniqueness (_1, _2, etc.)
    project_dir = base_dir / folder_name
    counter = 1
    while project_dir.exists():
        project_dir = base_dir / f"{folder_name}_{counter}"
        counter += 1

    project_dir.mkdir(parents=True, exist_ok=True)



    # --- Save media
    for i, img_url in enumerate(image_urls, 1):
        dest = project_dir / f"{folder_name}_{i}.jpg"
        download_file(img_url, dest)
    for i, v in enumerate(video_list, 1):
        dest = project_dir / f"{folder_name}_{i}.mp4"
        download_file(v["video_url"], dest)

    # -------- Save JSON --------
    data = {
        "origin": {"name": "ADCE Awards", "url": project_url},
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
    # with open(project_dir / f"{folder_name}.json", "w", encoding="utf-8") as f:
    #     json.dump(data, f, ensure_ascii=False, indent=2)

    # print(f"✅ Saved {folder_name}")
        # -------- Save JSON --------
    # json_name = safe_filename(folder_name) + ".json"   # <-- sanitize JSON filename
    # with open(project_dir / json_name, "w", encoding="utf-8") as f:
    #     json.dump(data, f, ensure_ascii=False, indent=2)

    # print(f"✅ Saved {folder_name}")

    json_name = safe_filename(folder_name) + ".json"
    json_path = project_dir / json_name

    with open(windows_longpath(json_path), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {folder_name}")


driver.quit()
