import os, json, requests, subprocess, unicodedata, re
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------ Helpers ------------------

def sanitize_filename(name):
    if not name:
        return "project"
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("utf-8")
    name = name.replace("-", " ").replace("_", " ")
    name = re.sub(r"[^A-Za-z0-9 ]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:100]

def make_unique_folder(base_dir, name):
    counter = 1
    folder_name = name
    while os.path.exists(os.path.join(base_dir, folder_name)):
        folder_name = f"{name}_{counter}"
        counter += 1
    return folder_name

def download_file(url, path):
    try:
        r = requests.get(url, timeout=20)
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"⬇️ Saved: {path}")
    except Exception as e:
        print(f"❌ Failed {url}: {e}")

def download_vimeo(url, path):
    try:
        subprocess.run(
            ["yt-dlp", "-o", path, url],
            check=True
        )
        print(f"🎬 Downloaded video: {path}")
    except Exception as e:
        print(f"⚠️ Could not download video {url}: {e}")

# ------------------ Scraper ------------------

def scrape_project(entry, driver):
    url = entry["origin"]["url"]
    print(f"🔍 Visiting: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "md-sidenav h1"))
        )
    except:
        print("❌ Timed out waiting for project content")
        return

    soup = BeautifulSoup(driver.page_source, "html.parser")
    project = entry.copy()

    title = soup.select_one("md-sidenav h1")
    if title:
        project["name"] = title.get_text(strip=True)

    infos = soup.select("div.content-info")
    for info in infos:
        title_text = info.select_one(".title")
        if not title_text:
            continue
        t = title_text.get_text(strip=True)
        if "Catégorie" in t:
            cats = [c for c in info.stripped_strings if c != "Catégorie"]
            if len(cats) > 0:
                project["category"] = cats[0]
            if len(cats) > 1:
                project["subCategory"] = cats[1]
        elif "Synopsis" in t:
            project["description"] = " ".join(s for s in info.stripped_strings if s != "Synopsis")
        elif "Crédits" in t:
            for card in info.find_all("md-card"):
                role = card.select_one("div.hour")
                name = card.select_one("div.name")
                if role and name:
                    clean_role = " ".join(role.get_text(strip=True).split())
                    clean_name = " ".join(name.get_text(strip=True).split())
                    project["credits"].append({
                        "role": clean_role,
                        "name": clean_name
                    })

    for iframe in soup.select("div.creation-video iframe"):
        src = iframe.get("src")
        if src and {"video_url": src} not in project["videos"]:
            project["videos"].append({"video_url": src})
    if project["videos"]:
        project["type"] = "video"

    for img in soup.select("div.creation-image img"):
        src = img.get("src")
        if src and src not in project["image_urls"]:
            project["image_urls"].append(src)
    if not project["videos"] and project["image_urls"]:
        project["type"] = "image"

    # --- Build Paths ---
    safe_name = sanitize_filename(project["name"])
    year = str(project.get("year", "unknown"))
    category = sanitize_filename(project.get("category", "uncategorized"))

    base_dir = os.path.normpath(os.path.join("competition_leclubdesda_main", year, category))
    os.makedirs(base_dir, exist_ok=True)

    folder_name = make_unique_folder(base_dir, safe_name)
    out_dir = os.path.normpath(os.path.join(base_dir, folder_name))
    os.makedirs(out_dir, exist_ok=True)

    # --- Save JSON ---
    json_path = os.path.normpath(os.path.join(out_dir, f"{folder_name}.json"))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved JSON: {json_path}")

    # --- Download images ---
    for i, img in enumerate(project["image_urls"], start=1):
        ext = os.path.splitext(img)[-1].split("?")[0] or ".jpg"
        fname = f"{folder_name}_{i}{ext}"
        download_file(img, os.path.join(out_dir, fname))

    # --- Download videos ---
    for i, video in enumerate(project["videos"], start=1):
        fname = os.path.join(out_dir, f"{folder_name}_{i}.mp4")
        download_vimeo(video["video_url"], fname)

# ------------------ Main ------------------

if __name__ == "__main__":
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = uc.Chrome(use_subprocess=True, options=options)

    with open("competition-data.json", "r", encoding="utf-8") as f:
        entries = json.load(f)

    for entry in entries:
        scrape_project(entry, driver)

    driver.quit()
