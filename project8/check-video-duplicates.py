import os
import hashlib
from pathlib import Path
import shutil

def file_hash(filepath, chunk_size=8192):
    """Generate MD5 hash for a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def remove_duplicates_and_count(base_folder, extensions=("*.mp4", "*.mkv", "*.webm")):
    base = Path(base_folder)
    duplicates_root = base / "Duplicates"
    duplicates_root.mkdir(exist_ok=True)

    total_unique = 0
    per_year_counts = {}

    # loop through each year folder
    for year_folder in base.iterdir():
        if year_folder.is_dir() and year_folder.name.isdigit():
            print(f"\n🔎 Checking year {year_folder.name}")
            seen_hashes = {}
            year_count = 0

            # duplicates for this year
            year_dup_folder = duplicates_root / year_folder.name
            year_dup_folder.mkdir(parents=True, exist_ok=True)

            # loop over all supported extensions
            for ext in extensions:
                for file in year_folder.rglob(ext):
                    h = file_hash(file)
                    if h in seen_hashes:
                        print(f"Duplicate found: {file} -> moving to {year_dup_folder}")
                        shutil.move(str(file), year_dup_folder / file.name)
                    else:
                        seen_hashes[h] = file
                        year_count += 1

            per_year_counts[year_folder.name] = year_count
            total_unique += year_count

    print("\n📊 Final Counts (after removing duplicates):")
    for year, count in sorted(per_year_counts.items()):
        print(f"  {year}: {count} unique videos")
    print(f"\n✅ Total unique videos across all years: {total_unique}")

# Example usage
remove_duplicates_and_count("SuperBowlAds")
