from pathlib import Path

# ===== CONFIG =====
ORIGINAL_FILE = Path(r"missing_urls.txt")
OTHER_FILE = Path(r"origin_urls.txt")
OUTPUT_FILE = Path(r"professional_urls_done.txt")
# ==================

def load_urls(file_path: Path):
    with file_path.open("r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def main():
    original_urls = load_urls(ORIGINAL_FILE)
    other_urls = load_urls(OTHER_FILE)

    missing_urls = sorted(original_urls - other_urls)

    OUTPUT_FILE.write_text("\n".join(missing_urls), encoding="utf-8")

    print(f"[DONE] Original count: {len(original_urls)}")
    print(f"[DONE] Other count: {len(other_urls)}")
    print(f"[DONE] Missing count: {len(missing_urls)}")
    print(f"[DONE] Saved missing URLs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
