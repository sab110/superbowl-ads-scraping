import os
import json
import re

def safe_windows_name(name: str) -> str:
    """Keep accents but replace illegal Windows characters with space and strip trailing dots/spaces."""
    illegal = [":", "/", "\\", "*", "?", '"', "<", ">", "|"]
    for ch in illegal:
        name = name.replace(ch, " ")
    # collapse multiple spaces
    name = " ".join(name.split())
    # strip trailing dots and spaces (Windows forbids them)
    return name.rstrip(". ").strip()

def rename_projects(base_dir):
    for year in os.listdir(base_dir):
        year_path = os.path.join(base_dir, year)
        if not os.path.isdir(year_path):
            continue

        for category in os.listdir(year_path):
            category_path = os.path.join(year_path, category)
            if not os.path.isdir(category_path):
                continue

            for project in os.listdir(category_path):
                project_path = os.path.join(category_path, project)
                if not os.path.isdir(project_path):
                    continue

                # --- Find JSON file ---
                json_file = None
                for f in os.listdir(project_path):
                    if f.lower().endswith(".json"):
                        json_file = os.path.join(project_path, f)
                        break

                project_name = project  # fallback if JSON missing

                if json_file and os.path.exists(json_file):
                    try:
                        with open(json_file, "r", encoding="utf-8-sig") as f:
                            data = json.load(f)
                        if "name" in data and data["name"]:
                            project_name = data["name"].strip()
                    except Exception as e:
                        print(f"⚠️ Could not read {json_file}: {e}")

                # Sanitize project name
                project_name = safe_windows_name(project_name)

                # --- Preserve duplicate suffix (_1, _2, etc.) ---
                base_name = project_name
                if "_" in project and project.split("_")[-1].isdigit():
                    suffix = "_" + project.split("_")[-1]
                    project_name = base_name + suffix

                new_project_path = os.path.join(category_path, project_name)

                # --- Rename folder ---
                if new_project_path != project_path:
                    try:
                        os.rename(project_path, new_project_path)
                        print(f"📁 Folder renamed: {project_path} → {new_project_path}")
                        project_path = new_project_path
                    except Exception as e:
                        print(f"⚠️ Could not rename folder {project_path}: {e}")

                # --- Rename files inside ---
                for file in os.listdir(project_path):
                    old_path = os.path.join(project_path, file)
                    if not os.path.isfile(old_path):
                        continue

                    lower_file = file.lower()
                    new_name = None

                    # JSON → rename to project.json
                    if lower_file.endswith(".json"):
                        new_name = f"{project_name}.json"

                    # image_1 / video_1 convention
                    elif lower_file.startswith("image_") or lower_file.startswith("video_"):
                        suffix = file.split("_", 1)[-1]
                        new_name = f"{project_name}_{suffix}"

                    # space-number convention: "foo 1.jpg"
                    else:
                        match = re.match(r"(.+?) (\d+)(.*)(\.[a-z0-9]+)$", file, re.IGNORECASE)
                        if match:
                            # projectname 1 thumb.jpg → projectname_1 thumb.jpg
                            prefix, num, extra, ext = match.groups()
                            new_name = f"{project_name}_{num}{extra}{ext}"

                    if new_name:
                        new_name = safe_windows_name(new_name)
                        new_path = os.path.join(project_path, new_name)

                        if old_path != new_path:
                            try:
                                os.rename(old_path, new_path)
                                print(f"✅ File renamed: {old_path} → {new_path}")
                            except Exception as e:
                                print(f"⚠️ Could not rename file {old_path}: {e}")

if __name__ == "__main__":
    base_dir = "CNN"  # adjust path as needed
    rename_projects(base_dir)
    print("\n🎉 All folders + files renamed (handles spaces before numbers too).")
