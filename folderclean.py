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


# import os
# import uuid
# from pathlib import Path

# # ========= settings =========
# ROOT_DIR = Path(r"D:\Media\Ads\adsoftheworld\professional")  # <-- change me
# DRY_RUN = False  # True = preview only
# IGNORE_NAMES = {".DS_Store", "Thumbs.db"}  # skip these
# # ===========================

# def rename_folder_files(d: Path):
#     # files directly in folder (skip hidden + ignored)
#     files = [
#         p for p in d.iterdir()
#         if p.is_file() and not p.name.startswith(".") and p.name not in IGNORE_NAMES
#     ]
#     if not files:
#         return

#     files.sort(key=lambda p: p.name.lower())
#     folder_name = d.name
#     single = (len(files) == 1)

#     # We will force **canonical** names so folder name appears only once
#     desired = []
#     for i, src in enumerate(files, start=1):
#         stem = folder_name if single else f"{folder_name}_{i}"
#         desired_name = stem + src.suffix.lower()
#         desired.append((src, desired_name))

#     # Phase 1: move everything to unique temp names to avoid collisions
#     temps = []
#     for src, _final in desired:
#         tmp = src.with_name(f"__tmp__{uuid.uuid4().hex}{src.suffix}")
#         if DRY_RUN:
#             print(f"[DRY] {src.name}  ->  {tmp.name}")
#         else:
#             src.rename(tmp)
#         temps.append((tmp, _final))

#     # Phase 2: move temps to their **exact** final names
#     for tmp, final_name in temps:
#         final_path = tmp.with_name(final_name)

#         # In the unlikely event something else already exists with that name,
#         # bump a numeric suffix but NEVER repeat the folder name.
#         if final_path.exists():
#             base_stem = final_path.stem  # e.g., FolderName or FolderName_3
#             ext = final_path.suffix
#             k = 2
#             while True:
#                 candidate = tmp.with_name(f"{base_stem}-{k}{ext}")
#                 if not candidate.exists():
#                     final_path = candidate
#                     break
#                 k += 1

#         if DRY_RUN:
#             print(f"[DRY] {tmp.name}  ->  {final_path.name}")
#         else:
#             tmp.rename(final_path)

# def main():
#     if not ROOT_DIR.exists() or not ROOT_DIR.is_dir():
#         print(f"Root '{ROOT_DIR}' does not exist or is not a directory.")
#         return

#     # Walk all subfolders (and nested)
#     for dirpath, _, _ in os.walk(ROOT_DIR):
#         rename_folder_files(Path(dirpath))

# if __name__ == "__main__":
#     main()


import os
from pathlib import Path

# ====== SETTINGS ======
ROOT_DIR = Path(r"adsoftheworld\professional")  # Change path if needed
DRY_RUN = False  # True = just preview changes without renaming
# ======================

def rename_folders_and_files(root_dir: Path):
    # Rename folders (deepest first)
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        # Folders
        for dirname in dirnames:
            if "_" in dirname:
                old_path = Path(dirpath) / dirname
                new_name = dirname.replace("_", " ")
                new_path = Path(dirpath) / new_name

                if DRY_RUN:
                    print(f"[DRY] Folder: {old_path} -> {new_path}")
                else:
                    old_path.rename(new_path)
                    print(f"Renamed folder: {old_path} -> {new_path}")

        # Files
        for filename in filenames:
            if "_" in filename:
                old_file_path = Path(dirpath) / filename
                new_file_name = filename.replace("_", " ")
                new_file_path = Path(dirpath) / new_file_name

                if DRY_RUN:
                    print(f"[DRY] File: {old_file_path} -> {new_file_path}")
                else:
                    old_file_path.rename(new_file_path)
                    print(f"Renamed file: {old_file_path} -> {new_file_path}")

if __name__ == "__main__":
    if ROOT_DIR.exists() and ROOT_DIR.is_dir():
        rename_folders_and_files(ROOT_DIR)
    else:
        print(f"Directory does not exist: {ROOT_DIR}")
