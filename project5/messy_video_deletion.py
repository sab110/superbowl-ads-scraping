import os
from pathlib import Path

# Root folder (adjust this to your actual path)
root = Path("adsoftheworld/professionals_done")

# Iterate through all subdirectories and files
for subdir, _, files in os.walk(root):
    for file in files:
        if file.endswith(".part"):
            file_path = Path(subdir) / file
            try:
                os.remove(file_path)
                print(f"✅ Deleted: {file_path}")
            except Exception as e:
                print(f"❌ Could not delete {file_path}: {e}")
