import os

# ✅ Set your root directory
BASE_DIR = "data"

def rename_campaign_files(base_dir):
    for year in os.listdir(base_dir):
        year_path = os.path.join(base_dir, year)
        if not os.path.isdir(year_path):
            continue

        for campaign in os.listdir(year_path):
            campaign_path = os.path.join(year_path, campaign)
            if not os.path.isdir(campaign_path):
                continue

            # Rename metadata.json
            old_meta = os.path.join(campaign_path, "metadata.json")
            if os.path.exists(old_meta):
                new_meta = os.path.join(campaign_path, f"{campaign}.json")
                os.rename(old_meta, new_meta)
                print(f"✅ Renamed: {old_meta} -> {new_meta}")

            # Rename video files
            video_files = sorted([f for f in os.listdir(campaign_path) if f.lower().endswith(".mp4")])
            for idx, video_file in enumerate(video_files, start=1):
                old_video = os.path.join(campaign_path, video_file)
                new_video = os.path.join(campaign_path, f"{campaign}_{idx}.mp4")
                os.rename(old_video, new_video)
                print(f"🎞️ Renamed: {old_video} -> {new_video}")

if __name__ == "__main__":
    rename_campaign_files(BASE_DIR)
