# import json

# # Path to your JSON file
# JSON_FILE = r"palmares_data.json"

# def count_objects(json_file):
#     with open(json_file, "r", encoding="utf-8") as f:
#         data = json.load(f)
    
#     if isinstance(data, list):
#         count = len(data)
#         print(f"✅ Total objects in JSON: {count}")
#         return count
#     else:
#         print("⚠️ JSON is not a list at the top level.")
#         return 0

# if __name__ == "__main__":
#     count_objects(JSON_FILE)

import json

# Load your JSON file
with open("palmares_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

seen = set()
duplicates = []

for obj in data:
    url = obj.get("origin", {}).get("url", "").strip()

    if url in seen:
        duplicates.append(obj)
    else:
        seen.add(url)

print(f"🔎 Total objects: {len(data)}")
print(f"⚠️ Duplicates found by URL: {len(duplicates)}")

if duplicates:
    print("\nDuplicate entries:")
    for dup in duplicates:
        print(f"- {dup.get('name', 'NoName')} ({dup['origin']['url']})")
