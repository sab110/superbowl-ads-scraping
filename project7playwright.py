import time
import json
import re
import requests
import platform
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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
            p_abs = Path.cwd() / p
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
# Main Scraper with Playwright
# -------------------
def scrape_projects():
    links_file = Path(r"project7\ProjectUrls\oneasia_awards_project_links.txt")
    if not links_file.exists():
        print("❌ Links file not found!")
        return

    with open(links_file, "r", encoding="utf-8") as f:
        project_links = [line.strip() for line in f if line.strip()]

    print(f"✅ Loaded {len(project_links)} project links from {links_file}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114 Safari/537.36"
        )
        page = context.new_page()

        for idx, project_url in enumerate(project_links, 1):
            print(f"\n▶️ Project {idx}/{len(project_links)}: {project_url}")
            page.goto(project_url, wait_until="networkidle")
            time.sleep(0.2)

            # Hide overlay if it exists
            overlay = page.query_selector("div.player-not-allowed")
            if overlay:
                page.evaluate("el => el.style.display = 'none'", overlay)
                print("🛑 Overlay hidden")


            # Get page source after interaction
            psoup = BeautifulSoup(page.content(), "html.parser")

            # -----------------------------
            # Your SAME SELENIUM LOGIC HERE
            # -----------------------------
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

            # Category cleanup
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
                    "ADC Europe",
                    "ONE Asia"
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

            # Media (images/videos directly from gallery)
            # -------- Media --------
            image_urls, video_list = [], []
            bullets = page.query_selector_all(".ug-bullet")

            if bullets:
                print(f"   🎯 Found {len(bullets)} bullets, iterating...")
                for bidx, bullet in enumerate(bullets, 1):
                    try:
                        bullet.scroll_into_view_if_needed()
                        time.sleep(0.2)
                        bullet.click()
                        time.sleep(0.5)

                        msoup = BeautifulSoup(page.content(), "html.parser")

                        img = msoup.select_one(".ug-slide-wrapper[style*='z-index: 3'] img")
                        if img:
                            src = img.get("src")
                            if src and src not in image_urls:
                                image_urls.append(src)
                                print(f"      🖼️ Collected image {len(image_urls)}")

                        play_btn = page.query_selector(".ug-slide-wrapper[style*='z-index: 3'] .ug-button-videoplay")
                        if play_btn and play_btn.is_visible():
                            play_btn.click()
                            time.sleep(0.5)

                            video_tag = page.query_selector(".ug-videoplayer video")
                            if video_tag:
                                video_src = video_tag.get_attribute("src")
                                poster = video_tag.get_attribute("poster")
                                if video_src and not any(v["video_url"] == video_src for v in video_list):
                                    video_list.append({"video_url": video_src, "thumbnail": poster})
                                    print(f"      🎬 Collected video {len(video_list)}")

                            close_btn = page.query_selector(".ug-videoplayer-button-close")
                            if close_btn:
                                close_btn.click()
                                time.sleep(0.3)

                    except Exception as e:
                        print(f"      ⚠️ Skipped bullet {bidx}: {e}")
            else:
                print("   ⚠️ No bullets found → grabbing default media")
                msoup = BeautifulSoup(page.content(), "html.parser")
                img = msoup.select_one(".ug-item-wrapper img")
                if img:
                    image_urls.append(img.get("src"))
                video = msoup.select_one(".ug-videoplayer video")
                if video:
                    video_list.append({"video_url": video.get("src"), "thumbnail": video.get("poster")})


            # --- Folder naming
            folder_name = safe_filename(project_title_text)
            project_dir = Path("OneAsia Awards") / year / safe_filename(category_text_cleaned) / folder_name
            project_dir.mkdir(parents=True, exist_ok=True)

            # Save media
            # --- Save media
            for i, img_url in enumerate(image_urls, 1):
                dest = project_dir / f"{folder_name}_{i}.jpg"
                download_file(img_url, dest)
            for i, v in enumerate(video_list, 1):
                dest = project_dir / f"{folder_name}_{i}.mp4"
                download_file(v["video_url"], dest)

            # Save JSON
             # -------- Save JSON --------
            data = {
                "origin": {"name": "OneAsia Awards", "url": project_url},
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
            json_name = safe_filename(folder_name) + ".json"
            json_path = project_dir / json_name

            with open(windows_longpath(json_path), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ Saved {folder_name}")

        browser.close()


if __name__ == "__main__":
    scrape_projects()
