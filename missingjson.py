import os
import shutil
from pathlib import Path

# ====== SETTINGS ======
ROOT_DIR = Path(r"adsoftheworld\professional")  # Change path if needed
OUTPUT_TXT = Path("missing_json_folders.txt")  # Save missing folder names here
DELETE_FOLDERS = True  # Set False to just record, not delete
# ======================

def find_and_delete_folders_missing_json(root_dir: Path, output_file: Path, delete_folders: bool):
    missing_folders = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip root directory itself
        if Path(dirpath) == root_dir:
            continue

        # Check if any JSON file exists in the current folder
        has_json = any(fname.lower().endswith(".json") for fname in filenames)

        if not has_json:
            folder_path = Path(dirpath)
            missing_folders.append(folder_path.name)

            if delete_folders:
                try:
                    shutil.rmtree(folder_path)
                    print(f"🗑 Deleted: {folder_path}")
                except Exception as e:
                    print(f"❌ Error deleting {folder_path}: {e}")

    # Save results to TXT
    with open(output_file, "w", encoding="utf-8") as f:
        for folder_name in missing_folders:
            f.write(folder_name + "\n")

    print(f"✅ Processed {len(missing_folders)} folders without JSON.")
    print(f"📄 Saved list to: {output_file.resolve()}")

if __name__ == "__main__":
    if ROOT_DIR.exists() and ROOT_DIR.is_dir():
        find_and_delete_folders_missing_json(ROOT_DIR, OUTPUT_TXT, DELETE_FOLDERS)
    else:
        print(f"Directory does not exist: {ROOT_DIR}")
