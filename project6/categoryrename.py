import os
import json

# Path to your main folder (replace with your base path)
BASE_DIR = r"CNN"

for root, dirs, files in os.walk(BASE_DIR, topdown=True):
    # Rename category folders if they contain "-"
    for i, d in enumerate(dirs):
        if "-" in d:
            new_d = d.replace("-", " ")
            old_path = os.path.join(root, d)
            new_path = os.path.join(root, new_d)
            os.rename(old_path, new_path)
            dirs[i] = new_d  # update walk reference so os.walk doesn't get confused

    # Update JSON category values
    for file in files:
        if file.endswith(".json"):
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "category" in data and isinstance(data["category"], str):
                    data["category"] = data["category"].replace("-", " ")

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"Updated: {file_path}")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")
