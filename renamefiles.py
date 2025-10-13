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


# import os
# from pathlib import Path
# from collections import defaultdict

# # Base folder
# BASE_DIR = Path("Epica")

# # Years to check
# YEARS = [str(year) for year in range(2024, 2012, -1)]

# for year in YEARS:
#     year_path = BASE_DIR / year
#     if not year_path.exists():
#         print(f"❌ Skipping missing year folder: {year_path}")
#         continue

#     for category in year_path.iterdir():
#         if not category.is_dir():
#             continue

#         for campaign in category.iterdir():
#             if not campaign.is_dir():
#                 continue

#             campaign_name = campaign.name.replace(" ", "-").replace("/", "-")
            
#             # Group files by extension
#             files_by_ext = defaultdict(list)
#             for file in campaign.iterdir():
#                 if file.is_file():
#                     files_by_ext[file.suffix].append(file)

#             for ext, files in files_by_ext.items():
#                 files.sort()  # Sort to keep consistent order
#                 for idx, file in enumerate(files, start=1):
#                     if len(files) == 1:
#                         new_name = f"{campaign_name}{ext}"
#                     else:
#                         new_name = f"{campaign_name}_{idx}{ext}"
                    
#                     new_path = file.parent / new_name
#                     file.rename(new_path)
#                     print(f"✅ Renamed: {file.name} → {new_name}")

# import os
# import re
# from pathlib import Path

# # Path to your 'student' folder
# base_path = Path("adsoftheworld\professional")

# # Regex: keep letters, numbers, spaces, underscores, and hyphens
# def clean_name(name):
#     # Replace unwanted characters with a space
#     cleaned = re.sub(r"[^a-zA-Z0-9\s_-]", "", name)
#     # Replace multiple spaces with a single space and strip ends
#     cleaned = re.sub(r"\s+", " ", cleaned).strip()
#     return cleaned

# for folder in base_path.iterdir():
#     if folder.is_dir():
#         new_name = clean_name(folder.name)
#         if new_name != folder.name:
#             new_path = folder.parent / new_name
#             # Avoid overwriting existing folders
#             if not new_path.exists():
#                 print(f"Renaming: '{folder.name}' → '{new_name}'")
#                 os.rename(folder, new_path)
#             else:
#                 print(f"⚠ Skipped '{folder.name}' — target name '{new_name}' already exists.")


# import os
# from pathlib import Path

# ROOT = Path(r"adsoftheworld\student")

# def replace_underscores_in_folders(root: Path):
#     for folder_path, dirs, files in os.walk(root, topdown=False):
#         folder = Path(folder_path)
#         # Skip the root itself
#         if folder == root:
#             continue
#         # Replace underscores with spaces
#         clean_name = folder.name.replace("_", " ").strip()
#         if clean_name != folder.name:
#             target = folder.parent / clean_name
#             # Avoid overwriting if target exists
#             if not target.exists():
#                 folder.rename(target)
#                 print(f"Renamed folder: {folder.name} → {clean_name}")
#             else:
#                 print(f"⚠️ Target folder already exists: {target}")

# if __name__ == "__main__":
#     replace_underscores_in_folders(ROOT)


import os
import re
import uuid
from pathlib import Path

# ====== SETTINGS ======
ROOT_DIR = Path(r"adsoftheworld\professional").resolve()
DRY_RUN = False
IGNORE_NAMES = {".DS_Store", "Thumbs.db"}
MAX_FULLPATH = 240  # keep a margin below 260
# ======================

_illegal = re.compile(r'[<>:"/\\|?*\u0000-\u001F]')
def sanitize(name: str) -> str:
    name = _illegal.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def to_long_path(p: Path) -> str:
    """Return a string usable with Win32 long-path prefix on Windows."""
    if os.name == "nt":
        abs_str = str(p.resolve())
        if abs_str.startswith("\\\\?\\"):
            return abs_str
        return "\\\\?\\" + abs_str
    return str(p)

def fit_name(dirpath: Path, base_stem: str, ext: str, extra_suffix: str = "") -> str:
    """Ensure dirpath/base_stem+extra+ext stays under MAX_FULLPATH; truncate stem if needed."""
    base_stem = sanitize(base_stem)
    extra_suffix = sanitize(extra_suffix)
    ext = ext.lower()

    # measure using absolute path (without \\?\ prefix for counting)
    abs_dir = str(dirpath.resolve())
    static_len = len(abs_dir) + 1 + len(extra_suffix) + len(ext)
    max_stem = max(10, MAX_FULLPATH - static_len)
    if len(base_stem) > max_stem:
        base_stem = base_stem[:max_stem].rstrip(" ._-")

    return f"{base_stem}{extra_suffix}{ext}"

def rename_folder_files(d: Path):
    files = [
        p for p in d.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.name not in IGNORE_NAMES
    ]
    if not files:
        return

    files.sort(key=lambda p: p.name.lower())
    folder_name = sanitize(d.name)
    single = (len(files) == 1)

    # Desired canonical names
    desired = []
    for i, src in enumerate(files, start=1):
        stem = folder_name if single else f"{folder_name}_{i}"
        final_name = fit_name(d, stem, src.suffix)
        desired.append((src, final_name))

    # Phase 1: move to very-short temp names (reduces long-path risk)
    temps = []
    for src, _ in desired:
        tmp = src.with_name(f"~t{uuid.uuid4().hex[:8]}{src.suffix.lower()}")
        if DRY_RUN:
            print(f"[DRY] {src} -> {tmp}")
        else:
            os.rename(to_long_path(src), to_long_path(tmp))
        temps.append((tmp, _))

    # Phase 2: move temps to final names (ensure uniqueness, keep path under cap)
    for tmp, final_name in temps:
        final_path = tmp.with_name(final_name)

        # If exists, bump -k (do not repeat folder name)
        if final_path.exists():
            base, ext = Path(final_name).stem, Path(final_name).suffix
            k = 2
            while True:
                bumped = fit_name(tmp.parent, base, ext, extra_suffix=f"-{k}")
                candidate = tmp.with_name(bumped)
                if not candidate.exists():
                    final_path = candidate
                    break
                k += 1

        if DRY_RUN:
            print(f"[DRY] {tmp} -> {final_path}")
        else:
            os.rename(to_long_path(tmp), to_long_path(final_path))

def main():
    if not ROOT_DIR.exists() or not ROOT_DIR.is_dir():
        print(f"Root '{ROOT_DIR}' does not exist or is not a directory.")
        return

    # IMPORTANT: use absolute paths during walk
    for dirpath, _, _ in os.walk(str(ROOT_DIR)):
        rename_folder_files(Path(dirpath))

if __name__ == "__main__":
    main()
