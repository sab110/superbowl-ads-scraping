import json
from pathlib import Path

# file paths
logs_file = Path("log.txt")
data_file = Path("data2.json")   # or your actual data.json
output_file = Path("data3.json")

# 1. Load all skipped links from logs.txt
with open(logs_file, "r", encoding="utf-8") as f:
    skipped_links = set(line.strip() for line in f if line.strip())

# 2. Load full data.json
with open(data_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 3. Filter objects whose link is in skipped_links
filtered = [obj for obj in data if obj.get("link") in skipped_links]

# 4. Save to data2.json
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(filtered, f, indent=4, ensure_ascii=False)

print(f"✅ Extracted {len(filtered)} objects into {output_file}")
