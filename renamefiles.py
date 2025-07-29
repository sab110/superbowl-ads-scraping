# import os

# # ✅ Set your root directory
# BASE_DIR = "data"

# def rename_campaign_files(base_dir):
#     for year in os.listdir(base_dir):
#         year_path = os.path.join(base_dir, year)
#         if not os.path.isdir(year_path):
#             continue

#         for campaign in os.listdir(year_path):
#             campaign_path = os.path.join(year_path, campaign)
#             if not os.path.isdir(campaign_path):
#                 continue

#             # Rename metadata.json
#             old_meta = os.path.join(campaign_path, "metadata.json")
#             if os.path.exists(old_meta):
#                 new_meta = os.path.join(campaign_path, f"{campaign}.json")
#                 os.rename(old_meta, new_meta)
#                 print(f"✅ Renamed: {old_meta} -> {new_meta}")

#             # Rename video files
#             video_files = sorted([f for f in os.listdir(campaign_path) if f.lower().endswith(".mp4")])
#             for idx, video_file in enumerate(video_files, start=1):
#                 old_video = os.path.join(campaign_path, video_file)
#                 new_video = os.path.join(campaign_path, f"{campaign}_{idx}.mp4")
#                 os.rename(old_video, new_video)
#                 print(f"🎞️ Renamed: {old_video} -> {new_video}")

# if __name__ == "__main__":
#     rename_campaign_files(BASE_DIR)


# import os
# import json
# from pathlib import Path

# def fix_json_encoding(base_folder):
#     for year_dir in Path(base_folder).iterdir():
#         if year_dir.is_dir():
#             for campaign_dir in year_dir.iterdir():
#                 if campaign_dir.is_dir():
#                     for file in campaign_dir.glob("*.json"):
#                         try:
#                             with open(file, "r", encoding="utf-8", errors="replace") as f:
#                                 data = json.load(f)

#                             # Re-serialize to normalize encoding
#                             with open(file, "w", encoding="utf-8") as f:
#                                 json.dump(data, f, ensure_ascii=False, indent=2)

#                             print(f"✅ Fixed encoding: {file}")
#                         except Exception as e:
#                             print(f"❌ Error processing {file}: {e}")

# # Usage
# fix_json_encoding("data")


import os
from pathlib import Path
from collections import defaultdict

# Base folder
BASE_DIR = Path("Epica")

# Years to check
YEARS = [str(year) for year in range(2024, 2012, -1)]

for year in YEARS:
    year_path = BASE_DIR / year
    if not year_path.exists():
        print(f"❌ Skipping missing year folder: {year_path}")
        continue

    for category in year_path.iterdir():
        if not category.is_dir():
            continue

        for campaign in category.iterdir():
            if not campaign.is_dir():
                continue

            campaign_name = campaign.name.replace(" ", "-").replace("/", "-")
            
            # Group files by extension
            files_by_ext = defaultdict(list)
            for file in campaign.iterdir():
                if file.is_file():
                    files_by_ext[file.suffix].append(file)

            for ext, files in files_by_ext.items():
                files.sort()  # Sort to keep consistent order
                for idx, file in enumerate(files, start=1):
                    if len(files) == 1:
                        new_name = f"{campaign_name}{ext}"
                    else:
                        new_name = f"{campaign_name}_{idx}{ext}"
                    
                    new_path = file.parent / new_name
                    file.rename(new_path)
                    print(f"✅ Renamed: {file.name} → {new_name}")
