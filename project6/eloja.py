import os
import re
import time
import json
import requests
import platform
from urllib.parse import urlparse
from pathlib import Path
from selenium import webdriver
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import base64

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
            return  # Skip if already downloaded
        r = requests.get(url, timeout=20, stream=True)
        if r.status_code == 200:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(windows_longpath(dest_path), "wb") as f:
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
# Awards dictionary
# -------------------
AWARDS = {
    "ADC": "https://www.unblock.coffee/adc/?adsyear={year}",
    
    
}


def download_avif_with_selenium(driver, url, dest_path: Path):
    try:
        if dest_path.exists():
            return

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        script = """
        const url = arguments[0];
        const callback = arguments[1];

        fetch(url)
            .then(r => r.blob())
            .then(b => {
                const reader = new FileReader();
                reader.onloadend = () => callback(reader.result);
                reader.readAsDataURL(b);
            })
            .catch(e => callback("ERROR:" + e));
        """

        data = driver.execute_async_script(script, url)

        if isinstance(data, str) and data.startswith("ERROR:"):
            print(f"      ❌ AVIF blocked: {url}")
            return

        header, encoded = data.split(",", 1)
        binary = base64.b64decode(encoded)

        with open(dest_path, "wb") as f:
            f.write(binary)

        print(f"      📥 Saved AVIF (selenium): {dest_path}")

    except Exception as e:
        print(f"      ❌ Selenium AVIF error for {url}: {e}")


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

# driver = webdriver.Chrome(options=options)
driver = uc.Chrome(options=options)

# -------------------
# Main Loop
# -------------------
for award_name, base_pattern in AWARDS.items():
    award_root = Path(award_name)
    award_root.mkdir(exist_ok=True)
    print(f"\n🏆 Processing Award: {award_name}")

    # Reverse loop: 2025 → 2012
    for year in range(2025, 2018, -1):
    # for year in range(2025, 2024, -1):  # 2025 only
    # for year in [2022, 2021,2019,2018,2017.2016]:
        base_url = base_pattern.format(year=year)
        print(f"\n🔎 {award_name} | Year {year}: {base_url}")
        driver.get(base_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Only include valid category links
        category_links = []
        for a in soup.select("section.award-categories-grid a.award-category-card, ol.categories-list a"):
            href = a.get("href")
            if not href:
                continue
            if f"adsyear={year}" in href:
                category_links.append(href)


        if not category_links:
            print(f"   ⚠️ No categories found for {award_name} {year}. Skipping year.")
            continue

        print(f"   Found {len(category_links)} categories")

        for category_url in category_links:
            category_name = category_url.split("/")[-1].split("?")[0]
            category_path = award_root / str(year) / category_name
            category_path.mkdir(parents=True, exist_ok=True)

            print(f"\n  ▶ Category: {category_name}")
            driver.get(category_url)

            cat_soup = BeautifulSoup(driver.page_source, "html.parser")
            project_items = cat_soup.select("div.item")

            if not project_items:
                print(f"     ⚠️ No projects in {category_name} for {year}")
                continue

            print(f"     Found {len(project_items)} projects")

            for idx, item in enumerate(project_items, start=1):
                link_tag = item.select_one("div.campaign-thumb a")
                project_url = link_tag["href"] if link_tag else None
                if not project_url:
                    continue

                award_tag = item.select_one(".level2, .level3, .level4, .level5")
                award_txt = award_tag.get_text(strip=True) if award_tag else None

                name_tag = item.select_one("h4 a")
                name = name_tag.get_text(strip=True) if name_tag else "Unnamed"

                folder_name = safe_filename(name, max_length=50)
                file_safe_name = safe_filename(name, max_length=100)
                print(f"    [{idx}/{len(project_items)}] {project_url} [{award_txt}]")

                project_path = category_path / folder_name
                counter = 1
                while project_path.exists():
                    project_path = category_path / f"{folder_name}_{counter}"
                    counter += 1
                project_path.mkdir(parents=True, exist_ok=True)

                json_file = project_path / f"{file_safe_name}.json"
                if json_file.exists():
                    print(f"       ⏭️ Skipping (already downloaded): {name}")
                    continue

                driver.get(project_url)
                proj_soup = BeautifulSoup(driver.page_source, "html.parser")

                brand = get_detail(proj_soup, "Brand")
                agency = get_detail(proj_soup, "Agency")
                country = get_detail(proj_soup, "Country")
                sector = get_detail(proj_soup, "Sector")

                # ---- Credits (handles both HTML styles) ----
                credits = []

                # Case 1: Table rows with role + name
                for row in proj_soup.select("#creatives tr, #credits tr"):
                    role = row.find("td", class_="creative-role")
                    person = row.find("td", class_="creative-name")
                    if role and person:
                        credits.append({"role": role.get_text(strip=True), "name": person.get_text(strip=True)})

                # Case 2: Section with <h3> heading and only creative-name
                for section in proj_soup.select("section#campaign-credits div.campaign-details-list"):
                    heading = section.find("h3")
                    if not heading:
                        continue
                    role_heading = heading.get_text(strip=True)
                    for person in section.select("td.creative-name"):
                        pname = person.get_text(strip=True)
                        if pname:
                            credits.append({"role": role_heading, "name": pname})

                images, videos = [], []
                for media in proj_soup.select(".gallery-container a.galeria"):
                    video_data = media.get("data-video")
                    thumb = media.get("data-poster") or media.get("data-thumb")
                    img_src = media.get("href") or media.get("data-src") or media.get("src")

                    if video_data and "src" in video_data:
                        m = re.search(r'"src":"(.*?)"', video_data)
                        if m:
                            videos.append({"video_url": m.group(1).replace("\\/", "/"), "thumbnail": thumb})
                    elif img_src:
                        images.append(img_src)

                # Download images
                for i, img_url in enumerate(images, start=1):
                    ext = os.path.splitext(urlparse(img_url).path)[-1] or ".jpg"
                    dest = project_path / f"{file_safe_name}_{i}{ext}"
                    # download_file(img_url, dest)
                    # AVIF must be downloaded via Selenium
                    if ext.lower() == ".avif":
                        download_avif_with_selenium(driver, img_url, dest)
                    else:
                        download_file(img_url, dest)


                # Download videos
                for i, vid in enumerate(videos, start=1):
                    vid_url = vid["video_url"]
                    ext = os.path.splitext(urlparse(vid_url).path)[-1] or ".mp4"
                    dest = project_path / f"{file_safe_name}_{i}{ext}"
                    download_file(vid_url, dest)

                project_obj = {
                    "origin": {"name": award_name, "url": project_url},
                    "name": name,
                    "type": "video" if videos else "image",
                    "sector": sector,
                    "countries": country,
                    "brands": brand,
                    "agency": agency,
                    "year": str(year),
                    "award": award_txt,
                    "category": category_name,
                    "subCategory": None,
                    "description": None,
                    "credits": credits,
                    "image_urls": images,
                    "videos": videos,
                    "tags": None,
                    "product": None
                }

                with open(windows_longpath(json_file), "w", encoding="utf-8") as f:
                    json.dump(project_obj, f, indent=2, ensure_ascii=False)

                print(f"          ✅ Saved project: {name}")

driver.quit()
print("\n✅ Finished scraping all awards")
