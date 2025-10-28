import os
import re
import time
import requests
import subprocess
from pathlib import Path
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# -------------
# Helper functions
# -------------

def clean_name(text: str) -> str:
    """Remove special characters for safe filenames."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', text.lower())

def download_videopress(driver, base_url, save_dir, base_name):
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
        # get src BEFORE switching into iframe
        src = iframe.get_attribute("src")

        driver.switch_to.default_content()
        driver.switch_to.frame(iframe)

        try:
            # Click play button if present
            play_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-large-play-button"))
            )
            play_btn.click()
            time.sleep(2)
        except Exception:
            pass

        # Build YouTube watch URL from iframe src
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

def process_url(driver, url, log_file):
    print(f"\n🔎 Processing {url}")
    driver.get(url)
    time.sleep(2)

    # Parse year (first 4-digit number in URL)
    m_year = re.search(r"(\d{4})", url)
    year = m_year.group(1) if m_year else "unknown"

    # Parse base name (last slug in URL path)
    slug = url.strip("/").split("/")[-1]
    base_name = clean_name(slug)

    save_dir = Path("Videos") / year
    save_dir.mkdir(parents=True, exist_ok=True)

    total_downloads = 0

    # Try VideoPress
    total_downloads += download_videopress(driver, url, save_dir, base_name)

    # Try YouTube if nothing found
    if total_downloads == 0:
        total_downloads += download_youtube(driver, save_dir, base_name)

    # If still nothing, log it
    if total_downloads == 0:
        with open(log_file, "a") as lf:
            lf.write(url + "\n")
        print("⚠️ No video found, logged URL.")


# -------------
# Run
# -------------

if __name__ == "__main__":
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

    urls = [
        # "https://www.superbowl-ads.com/1998-doritos-ali-landry/",
        "https://www.superbowl-ads.com/ozzy-osbourne-super-bowl-ads/",
        "https://www.superbowl-ads.com/haagen-dazs-super-bowl-2025-ad-campaign/",
        "https://www.superbowl-ads.com/godaddy-cannes-lions-super-bowl-ad/",
        "https://www.superbowl-ads.com/carls-jr-super-bowl-lix-ad-free-hangover-burger-2-10-25/"
    ]

    log_file = "log.txt"
    for url in urls:
        process_url(driver, url, log_file)

    driver.quit()
