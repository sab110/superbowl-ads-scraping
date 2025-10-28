import os
import re
import time
import json
import requests
import subprocess
from pathlib import Path
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------------
# Helper functions
# -------------

def clean_name(text: str, max_length: int = 80) -> str:
    """Remove special characters for safe filenames and shorten to avoid Windows path issues."""
    safe = re.sub(r'[^a-zA-Z0-9_]+', '_', text.strip())
    return safe[:max_length].rstrip("_")  # ensure no trailing underscores


def download_videopress(driver, save_dir, base_name):
    """Try to download VideoPress videos."""
    videos_downloaded = 0
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='videopress.com/embed']")
        for idx, iframe in enumerate(iframes, start=1):
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            try:
                play_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.vjs-big-play-button"))
                )
                play_button.click()
                time.sleep(2)
                video = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "video.vjs-tech"))
                )
                video_url = video.get_attribute("src")
                if video_url:
                    filename = save_dir / f"{base_name}_{idx}.mp4"
                    r = requests.get(video_url, stream=True)
                    with open(filename, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                    print(f"✅ Saved VideoPress video: {filename}")
                    videos_downloaded += 1
            except Exception:
                pass
    finally:
        driver.switch_to.default_content()
    return videos_downloaded


def download_youtube(driver, save_dir, base_name):
    """Find and download YouTube videos inside iframes using yt-dlp."""
    videos_downloaded = 0
    iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='youtube.com/embed']")

    for idx, iframe in enumerate(iframes, start=1):
        src = iframe.get_attribute("src")
        driver.switch_to.default_content()
        driver.switch_to.frame(iframe)

        try:
            play_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-large-play-button"))
            )
            play_btn.click()
            time.sleep(2)
        except Exception:
            pass

        if src and "youtube.com" in src:
            video_id = src.split("/")[-1].split("?")[0]
            yt_url = f"https://www.youtube.com/watch?v={video_id}"

            filename = save_dir / f"{base_name}_{idx}.mp4"
            print(f"⬇️ Downloading YouTube video: {yt_url}")

            try:
                subprocess.run(
                    ["yt-dlp", "-o", str(filename), yt_url],
                    check=True
                )
                print(f"✅ Saved YouTube video: {filename}")
                videos_downloaded += 1
            except Exception as e:
                print(f"⚠️ Failed to download YouTube video: {e}")

        driver.switch_to.default_content()

    return videos_downloaded


# -------------
# Main scraping loop
# -------------

def process_entry(driver, entry, log_file):
    url = entry["link"]
    year = entry["year"]
    title = entry["title"]

    safe_name = clean_name(title)

    save_dir = Path("SuperBowlAds") / year
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔎 Processing: {title} ({year})")
    print(f"   URL: {url}")

    try:
        driver.get(url)
        time.sleep(3)
    except Exception as e:
        print(f"❌ Failed to load {url}: {e}")
        return

    total_downloads = 0

    # Try VideoPress
    total_downloads += download_videopress(driver, save_dir, safe_name)

    # Try YouTube if nothing found
    if total_downloads == 0:
        total_downloads += download_youtube(driver, save_dir, safe_name)

    # Log ONLY the link if no video found
    if total_downloads == 0:
        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(url + "\n")
        print("⚠️ No video found, logged URL.")

# -------------
# Run
# -------------

if __name__ == "__main__":
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
    options.add_argument("user-agent=Mozilla/5.0")

    driver = webdriver.Chrome(options=options)

    # Load JSON data
    with open(r"data2.json", "r", encoding="utf-8") as f:
        entries = json.load(f)

    log_file = "log.txt"
    for entry in entries:
        process_entry(driver, entry, log_file)

    driver.quit()
