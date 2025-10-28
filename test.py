import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

skipped_log = open("skipped_urls.txt", "a", encoding="utf-8")

# Initialize undetected ChromeDriver
options = uc.ChromeOptions()
# options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")

driver = uc.Chrome(use_subprocess=True, options=options)
base_url = f"https://www.unblock.coffee/cnns/?adsyear=2024"
driver.get(base_url)