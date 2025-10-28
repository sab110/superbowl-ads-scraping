import time
import re
from pathlib import Path
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# -------------------
# Chrome setup
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
# Open base page
# -------------------
base_url = "https://www.oneclub.org/awards/youngones/-archive/awards/2025/all/all/select"
driver.get(base_url)
time.sleep(2)

# Accept cookies if present
try:
    WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-tid='banner-accept']"))
    ).click()
    print("✅ Accepted cookies")
except:
    print("ℹ️ No cookies banner")

# -------------------
# Open the YEAR dropdown (not the Filter one) and collect year URLs
# -------------------
year_urls = []

try:
    # Find the dropdown whose header label is exactly "Year"
    year_dropdown_button = WebDriverWait(driver, 8).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'filter-row-col')]"
            "[.//h2[normalize-space()='Year']]"
            "//button[contains(@class,'dropdown-toggle')]"
        ))
    )
    year_dropdown_button.click()
    time.sleep(0.5)

    # Now read the links inside that opened Year menu only
    year_links = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'filter-row-col')]"
        "[.//h2[normalize-space()='Year']]"
        "//div[contains(@class,'filter-select-menu')]"
        "//ul[contains(@class,'dropdown-menu')]//a[contains(@class,'datafilter-opt')]"
    )

    for yl in year_links:
        href = yl.get_attribute("href")
        if href:
            if not href.startswith("http"):
                href = "https://www.oneclub.org" + href
            year_urls.append(href)

    print(f"✅ Found {len(year_urls)} year archive URLs")

except Exception as e:
    print(f"⚠️ Could not open Year dropdown or read links: {e}")

# Safety: fall back to at least the current page if nothing found
if not year_urls:
    year_urls = [base_url]

# -------------------
# Output file & de-dupe set (supports resume)
# -------------------
output_file = Path("youngones_awards_project_links.txt")
all_seen = set(output_file.read_text(encoding="utf-8").splitlines()) if output_file.exists() else set()

# -------------------
# For each year page, collect project links with hybrid scrolling
# -------------------
for yidx, list_url in enumerate(year_urls, 1):
    year_match = re.search(r"/awards/(\d{4})/", list_url)
    year_str = year_match.group(1) if year_match else "unknown"

    print(f"\n📅 Collecting for year {year_str} ({yidx}/{len(year_urls)})")
    driver.get(list_url)
    time.sleep(1)

    scroll_count, retries = 0, 0
    max_retries = 5

    while True:
        scroll_count += 1

        # Scroll to the bottom to trigger lazy load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)  # allow new cards to render

        soup = BeautifulSoup(driver.page_source, "html.parser")
        raw_links = [a.get("href") for a in soup.select(".filter-grid-item .box-item a.item-heading") if a.get("href")]

        # Convert to absolute and dedupe against global all_seen
        added_links = []
        for link in raw_links:
            full_url = link if link.startswith("http") else f"https://www.oneclub.org{link}"
            if full_url not in all_seen:
                all_seen.add(full_url)
                added_links.append(full_url)

        # Append immediately
        if added_links:
            with open(output_file, "a", encoding="utf-8") as f:
                for url in added_links:
                    f.write(url + "\n")
            print(f"   🔄 Scroll {scroll_count}: appended {len(added_links)} new (total {len(all_seen)})")
            retries = 0
        else:
            retries += 1
            print(f"   ⚠️ No new links this scroll (retry {retries}/{max_retries})")

            # Fallback: try clicking the 'Load More' button if scrolling alone didn't append anything new
            try:
                load_more = WebDriverWait(driver, 1.5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".load-more a"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                ActionChains(driver).move_to_element(load_more).click().perform()
                print("   ⬇️ Clicked 'Load More' button as fallback")
                time.sleep(1)
                retries = 0
                continue
            except:
                pass

        # Stop conditions: 'Load More' gone or too many dry scrolls
        try:
            load_more = driver.find_element(By.CSS_SELECTOR, ".load-more a")
            if not load_more.is_displayed():
                print("✅ 'Load More' gone — finished this year")
                break
        except:
            print("✅ No 'Load More' button — finished this year")
            break

        if retries >= max_retries:
            print("✅ Max retries hit — finished this year")
            break

print(f"\n✅ Done. Total unique project links saved: {len(all_seen)} → {output_file}")
driver.quit()
