# import os
# import re
# import json
# import time
# import requests
# from urllib.parse import urlparse, parse_qs
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from lxml import html

# # ====== SELENIUM SETUP ======
# options = Options()
# options.add_argument("--no-sandbox")
# options.add_argument("--disable-dev-shm-usage")
# options.add_argument("--disable-gpu")
# options.add_argument("--window-size=1920,1080")
# options.add_argument("--start-maximized")
# options.add_argument("user-agent=Mozilla/5.0")
# driver = webdriver.Chrome(options=options)
# url = 'https://www.adsoftheworld.com/campaigns/the-biggest-dream'
# driver.get(url)
# soup = BeautifulSoup(driver.page_source, 'html.parser')

# # Title extraction
# title = soup.find('h1', class_='text-2xl karlasemibold')
# title = title.text.strip() if title else None
# print(f"Title: {title}")

# # Description extraction
# description = soup.find('div', class_='mb-4 whitespace-pre-line flex flex-col gap-4').find('p')
# description = description.text.strip() if description else None
# print("Description:", description)

# # Credits extraction
# credits_content = str(soup.find('div', class_='col-span-2'))
# tree = html.fromstring(credits_content)

# # Use XPath to extract the credits section after the "Credits" header
# credits_section = tree.xpath("//p[text()='Credits']/following-sibling::div//p/text()")

# # Format the extracted credits into the required structure, excluding "Brand" role
# credits = []
# for line in credits_section:
#     if ":" in line:
#         role, name = line.split(":", 1)
#         role = role.strip()
#         name = name.strip()

#         # Skip the "Brand" role
#         if role.lower() == "brand":
#             continue

#         credits.append({"role": role, "name": name})

# # Year extraction
# campaign_description = soup.find('p', class_='mb-6 text-sm').text
# year_match = re.search(r'\b(\d{4})\b', campaign_description)
# year = year_match.group(1) if year_match else None
# print(f"Year: {year}")

# # Initialize a dictionary to store the categories
# categories = {
#     "brand": None,
#     "agency": None,
#     "countries": None,
#     "category": [],
#     "subCategory": None
# }

# # Extract all <a> tags with href attributes
# category_links = soup.find_all('a', href=True)

# # Loop through each <a> tag and classify based on href keyword
# for link in category_links:
#     href = link['href']
#     text = link.text.strip()

#     # Classify based on href value
#     if 'brands' in href and categories['brand'] is None:  # Only store the first brand
#         categories['brand'] = text
#     elif 'agencies' in href and categories['agency'] is None:  # Only store the first agency
#         categories['agency'] = text
#     elif 'country' in href and categories['countries'] is None:  # Only store the first country
#         categories['countries'] = text
#     elif 'medium_types' in href:  # Multiple mediums can be added
#         categories['category'].append(text)
#     elif 'industries' in href and categories['subCategory'] is None:  # Only store the first industry
#         categories['subCategory'] = text

# print(f"Brand: {categories['brand']}")
# print(f"Agency: {categories['agency']}")
# print(f"Country: {categories['countries']}")
# print(f"Medium: {categories['category']}")
# print(f"Industries: {categories['subCategory']}")

# # Media extraction
# # Initialize the lists for image URLs and video URLs
# image_urls = []
# videos = []

# # Extract direct video URLs from <video> tags within divs with class 'bg-white my-3'
# for div in soup.find_all('div', class_='bg-white my-3'):
#     video_tag = div.find('video', src=True, poster=True)
#     if video_tag:
#         video_url = video_tag['src']
#         poster_url = video_tag['poster']
#         videos.append({
#             "video_url": video_url,
#             "thumbnail": poster_url  # Poster as thumbnail
#         })

# # Extract embedded video URLs (from iframe tags) inside divs with class 'bg-white my-3'
# for div in soup.find_all('div', class_='bg-white my-3'):
#     iframe_tag = div.find('iframe', src=True)
#     if iframe_tag:
#         video_url = iframe_tag['src']
        
#         # Check if the video is from YouTube
#         if 'youtube' in video_url:
#             video_id = video_url.split('/')[4]  # Extract YouTube video ID
#             thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg"  # Thumbnail URL format
#             videos.append({
#                 "video_url": video_url,
#                 "thumbnail": thumbnail_url
#             })
        
#         # Check if the video is from Vimeo
#         elif 'vimeo' in video_url:
#             video_id = video_url.split('/')[-1]  # Extract Vimeo video ID
#             thumbnail_url = f"https://vumbnail.com/{video_id}.jpg"  # Use vumbnail for Vimeo thumbnail
#             videos.append({
#                 "video_url": video_url,
#                 "thumbnail": thumbnail_url
#             })

# # Extract image URLs (from img src)
# for div in soup.find_all('div', class_='bg-white my-3'):
#     img_tag = div.find('img', src=True)
#     if img_tag:
#         image_urls.append(img_tag['src'])

# # Prepare the output dictionary
# output = {
#     "origin": {
#         "name": "adsoftheworld.com",  # Example origin name
#         "url": url
#     },
#     "name": title,
#     "type": "video" if videos else "image",  # Determine type based on presence of videos
#     "sector": None,  
#     "countries": categories['countries'],
#     "brands": categories['brand'],
#     "agency": categories['agency'],
#     "year": year,
#     "award": None,
#     "category": categories['category'],
#     "subCategory": categories['subCategory'],
#     "description": description,
#     "credits": credits,
#     "image_urls": image_urls,
#     "videos": videos,
#     "tags": None, 
#     "product": None  
# }

# # Save the output as a JSON file
# with open(f"{title}.json", 'w',encoding="utf-8-sig") as f:
#     json.dump(output, f, indent=2,ensure_ascii=False)

# print(f"Output saved to {title}.json")



import os
import re
import json
import subprocess
import requests
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from lxml import html

# ====== SELENIUM SETUP ======
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0")
driver = webdriver.Chrome(options=options)
url = 'https://www.adsoftheworld.com/campaigns/the-biggest-dream'
driver.get(url)
soup = BeautifulSoup(driver.page_source, 'html.parser')

# Title extraction
title = soup.find('h1', class_='text-2xl karlasemibold')
title = title.text.strip().replace(" ", "_") if title else None  # Replace spaces with underscores in title
print(f"Title: {title}")

# Description extraction
description = soup.find('div', class_='mb-4 whitespace-pre-line flex flex-col gap-4').find('p')
description = description.text.strip() if description else None
print("Description:", description)

# Credits extraction
credits_content = str(soup.find('div', class_='col-span-2'))
tree = html.fromstring(credits_content)

# Use XPath to extract the credits section after the "Credits" header
credits_section = tree.xpath("//p[text()='Credits']/following-sibling::div//p/text()")

# Format the extracted credits into the required structure, excluding "Brand" role
credits = []
for line in credits_section:
    if ":" in line:
        role, name = line.split(":", 1)
        role = role.strip()
        name = name.strip()

        # Skip the "Brand" role
        if role.lower() == "brand":
            continue

        credits.append({"role": role, "name": name})

# Year extraction
campaign_description = soup.find('p', class_='mb-6 text-sm').text
year_match = re.search(r'\b(\d{4})\b', campaign_description)
year = year_match.group(1) if year_match else None
print(f"Year: {year}")

# Initialize a dictionary to store the categories
categories = {
    "brand": None,
    "agency": None,
    "countries": None,
    "category": [],
    "subCategory": None
}

# Extract all <a> tags with href attributes
category_links = soup.find_all('a', href=True)

# Loop through each <a> tag and classify based on href keyword
for link in category_links:
    href = link['href']
    text = link.text.strip()

    # Classify based on href value
    if 'brands' in href and categories['brand'] is None:  # Only store the first brand
        categories['brand'] = text
    elif 'agencies' in href and categories['agency'] is None:  # Only store the first agency
        categories['agency'] = text
    elif 'country' in href and categories['countries'] is None:  # Only store the first country
        categories['countries'] = text
    elif 'medium_types' in href:  # Multiple mediums can be added
        categories['category'].append(text)
    elif 'industries' in href and categories['subCategory'] is None:  # Only store the first industry
        categories['subCategory'] = text

print(f"Brand: {categories['brand']}")
print(f"Agency: {categories['agency']}")
print(f"Country: {categories['countries']}")
print(f"Medium: {categories['category']}")
print(f"Industries: {categories['subCategory']}")

# Media extraction
# Initialize the lists for image URLs and video URLs
image_urls = []
videos = []

# Extract direct video URLs from <video> tags within divs with class 'bg-white my-3'
for div in soup.find_all('div', class_='bg-white my-3'):
    video_tag = div.find('video', src=True, poster=True)
    if video_tag:
        video_url = video_tag['src']
        poster_url = video_tag['poster']
        videos.append({
            "video_url": video_url,
            "thumbnail": poster_url  # Poster as thumbnail
        })

# Extract embedded video URLs (from iframe tags) inside divs with class 'bg-white my-3'
for div in soup.find_all('div', class_='bg-white my-3'):
    iframe_tag = div.find('iframe', src=True)
    if iframe_tag:
        video_url = iframe_tag['src']
        
        # Check if the video is from YouTube
        if 'youtube' in video_url:
            video_id = video_url.split('/')[4]  # Extract YouTube video ID
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg"  # Thumbnail URL format
            videos.append({
                "video_url": video_url,
                "thumbnail": thumbnail_url
            })
        
        # Check if the video is from Vimeo
        elif 'vimeo' in video_url:
            video_id = video_url.split('/')[-1]  # Extract Vimeo video ID
            thumbnail_url = f"https://vumbnail.com/{video_id}.jpg"  # Use vumbnail for Vimeo thumbnail
            videos.append({
                "video_url": video_url,
                "thumbnail": thumbnail_url
            })

# Extract image URLs (from img src)
for div in soup.find_all('div', class_='bg-white my-3'):
    img_tag = div.find('img', src=True)
    if img_tag:
        image_urls.append(img_tag['src'])

# Function to download videos using yt-dlp with audio and video merge
def download_video(video_url, output_path):
    subprocess.run([
        "yt-dlp",
        "--referer", "https://www.adsoftheworld.com/",
        "-f", "bestvideo+bestaudio/best",  # Download best video and audio separately
        "--merge-output-format", "mp4",  # Merge the video and audio into a single MP4 file
        "-o", output_path,  # Set output file path
        video_url
    ], check=True)

# Create output folder for saving videos and images
output_dir = f"adsoftheworld/{title.replace('_', ' ')}"  # Replace underscores with spaces in the folder name
os.makedirs(output_dir, exist_ok=True)

# Download and save videos
for i, video in enumerate(videos):
    video_url = video['video_url']
    video_path = os.path.join(output_dir, f"{title} {i + 1}.mp4")  # Use spaces in filename
    download_video(video_url, video_path)

# Download and save images with naming conventions (image_1.jpg, image_2.jpg)
for i, img_url in enumerate(image_urls):
    img_name = f"{title} {i + 1}.jpg"  # Naming convention with spaces
    img_path = os.path.join(output_dir, img_name)
    img_data = requests.get(img_url).content
    with open(img_path, 'wb') as img_file:
        img_file.write(img_data)

# Prepare the output dictionary with local paths of images and videos
output = {
    "origin": {
        "name": "adsoftheworld.com",
        "url": url
    },
    "name": title.replace("_", " "),  # Replace underscores with spaces in the title
    "type": "video" if videos else "image", 
    "sector": None,
    "countries": categories['countries'],
    "brands": categories['brand'],
    "agency": categories['agency'],
    "year": year,
    "award": None,
    "category": categories['category'],
    "subCategory": categories['subCategory'],
    "description": description,
    "credits": credits,
    "image_urls": image_urls,  # Local image paths
    "videos": videos,  # Local video paths
    "tags": None,
    "product": None
}

# Save the output as a JSON file
json_file = os.path.join(output_dir, f"{title}.json")
with open(json_file, 'w', encoding="utf-8-sig") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Files and metadata saved to {output_dir}")
