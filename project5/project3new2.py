# import os, time, json, requests, subprocess
# from bs4 import BeautifulSoup
# import undetected_chromedriver as uc
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# def sanitize_filename(name):
#     if not name:
#         return "project"
#     name = name.replace("-", " ").replace("_", " ")
#     return "".join(c for c in name if c.isalnum() or c == " ").strip()

# def download_file(url, path):
#     try:
#         r = requests.get(url, timeout=20)
#         with open(path, "wb") as f:
#             f.write(r.content)
#         print(f"⬇️ Saved: {path}")
#     except Exception as e:
#         print(f"❌ Failed {url}: {e}")

# def download_vimeo(url, path):
#     """Download Vimeo video using yt-dlp (must be installed)."""
#     try:
#         subprocess.run(
#             ["yt-dlp", "-o", path, url],
#             check=True
#         )
#         print(f"🎬 Downloaded video: {path}")
#     except Exception as e:
#         print(f"⚠️ Could not download video {url}: {e}")

# options = uc.ChromeOptions()
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-gpu")
# options.add_argument("--window-size=1920,1080")

# driver = uc.Chrome(use_subprocess=True, options=options)

# def scrape_project(url):
#     print(f"🔍 Visiting: {url}")
#     driver.get(url)

#     # Wait until sidenav loads
#     try:
#         WebDriverWait(driver, 15).until(
#             EC.presence_of_element_located((By.CSS_SELECTOR, "md-sidenav h1"))
#         )
#     except:
#         print("❌ Timed out waiting for project content")
#         return

#     soup = BeautifulSoup(driver.page_source, "html.parser")

#     project = {
#         "origin": {"name": "competition.leclubdesda.org", "url": url},
#         "name": None,
#         "type": None,
#         "sector": None,
#         "countries": "France",
#         "brands": None,
#         "agency": None,
#         "year": None,
#         "award": None,
#         "category": None,
#         "subCategory": None,
#         "description": None,
#         "credits": [],
#         "image_urls": [],
#         "videos": [],
#         "tags": None,
#         "product": None
#     }

#     # --- Name ---
#     title = soup.select_one("md-sidenav h1")
#     if title:
#         project["name"] = title.get_text(strip=True)

#     # --- Categories / Description / Credits ---
#     infos = soup.select("div.content-info")
#     for info in infos:
#         title_text = info.select_one(".title")
#         if not title_text:
#             continue
#         t = title_text.get_text(strip=True)
#         if "Catégorie" in t:
#             cats = [c for c in info.stripped_strings if c != "Catégorie"]
#             if len(cats) > 0:
#                 project["category"] = cats[0]
#             if len(cats) > 1:
#                 project["subCategory"] = cats[1]
#         elif "Synopsis" in t:
#             project["description"] = " ".join(s for s in info.stripped_strings if s != "Synopsis")
#         elif "Crédits" in t:
#             for card in info.find_all("md-card"):
#                 role = card.select_one("div.hour")
#                 name = card.select_one("div.name")
#                 if role and name:
#                     clean_role = " ".join(role.get_text(strip=True).split())
#                     clean_name = " ".join(name.get_text(strip=True).split())
#                     project["credits"].append({
#                         "role": clean_role,
#                         "name": clean_name
#                     })


#     # --- Video(s) ---
#     for iframe in soup.select("div.creation-video iframe"):
#         src = iframe.get("src")
#         if src:
#             project["videos"].append({"video_url": src})
#     if project["videos"]:
#         project["type"] = "video"

#     # --- Images ---
#     for img in soup.select("div.creation-image img"):
#         src = img.get("src")
#         if src:
#             project["image_urls"].append(src)
#     if not project["videos"] and project["image_urls"]:
#         project["type"] = "image"

#     # --- Save JSON ---
#     safe_name = sanitize_filename(project["name"])
#     out_dir = os.path.join("competition_leclubdesda", safe_name)
#     os.makedirs(out_dir, exist_ok=True)
#     json_path = os.path.join(out_dir, f"{safe_name}.json")
#     with open(json_path, "w", encoding="utf-8") as f:
#         json.dump(project, f, indent=2, ensure_ascii=False)
#     print(f"✅ Saved JSON: {json_path}")

#     # --- Download images ---
#     for i, img in enumerate(project["image_urls"], start=1):
#         ext = os.path.splitext(img)[-1].split("?")[0] or ".jpg"
#         fname = f"{safe_name} {i}{ext}"
#         download_file(img, os.path.join(out_dir, fname))

#     # --- Download videos (optional with yt-dlp) ---
#     for i, video in enumerate(project["videos"], start=1):
#         fname = os.path.join(out_dir, f"{safe_name} {i}.mp4")
#         download_vimeo(video["video_url"], fname)

# # Run for your example
# scrape_project("https://competition.leclubdesda.org/#/palmares/8805k618")

# driver.quit()


import os, time, json, requests, subprocess
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def sanitize_filename(name):
    if not name:
        return "project"
    name = name.replace("-", " ").replace("_", " ")
    return "".join(c for c in name if c.isalnum() or c == " ").strip()

def download_file(url, path):
    try:
        r = requests.get(url, timeout=20)
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"⬇️ Saved: {path}")
    except Exception as e:
        print(f"❌ Failed {url}: {e}")

def download_vimeo(url, path):
    """Download Vimeo video using yt-dlp (must be installed)."""
    try:
        subprocess.run(
            ["yt-dlp", "-o", path, url],
            check=True
        )
        print(f"🎬 Downloaded video: {path}")
    except Exception as e:
        print(f"⚠️ Could not download video {url}: {e}")

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = uc.Chrome(use_subprocess=True, options=options)

def scrape_project(entry):
    url = entry["origin"]["url"]
    print(f"🔍 Visiting: {url}")
    driver.get(url)

    # Wait until sidenav loads
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "md-sidenav h1"))
        )
    except:
        print("❌ Timed out waiting for project content")
        return

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Start with provided metadata, fallback to scraping
    project = entry.copy()

    # --- Name (override if site gives it) ---
    title = soup.select_one("md-sidenav h1")
    if title:
        project["name"] = title.get_text(strip=True)

    # --- Categories / Description / Credits ---
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

    # --- Video(s) ---
    for iframe in soup.select("div.creation-video iframe"):
        src = iframe.get("src")
        if src and {"video_url": src} not in project["videos"]:
            project["videos"].append({"video_url": src})
    if project["videos"]:
        project["type"] = "video"

    # --- Images ---
    for img in soup.select("div.creation-image img"):
        src = img.get("src")
        if src and src not in project["image_urls"]:
            project["image_urls"].append(src)
    if not project["videos"] and project["image_urls"]:
        project["type"] = "image"

    # --- Save JSON ---
    safe_name = sanitize_filename(project["name"])
    out_dir = os.path.join("test2", safe_name)
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{safe_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved JSON: {json_path}")

    # --- Download images ---
    for i, img in enumerate(project["image_urls"], start=1):
        ext = os.path.splitext(img)[-1].split("?")[0] or ".jpg"
        fname = f"{safe_name} {i}{ext}"
        download_file(img, os.path.join(out_dir, fname))

    # --- Download videos (optional with yt-dlp) ---
    for i, video in enumerate(project["videos"], start=1):
        fname = os.path.join(out_dir, f"{safe_name} {i}.mp4")
        download_vimeo(video["video_url"], fname)

# 🔄 Main loop: load JSON list and iterate
with open("data-copy.json", "r", encoding="utf-8") as f:
    entries = json.load(f)

for entry in entries:
    scrape_project(entry)

driver.quit()
