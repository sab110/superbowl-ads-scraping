import json
from pathlib import Path

# ====== SETTINGS ======
ROOT_DIR = Path(r"adsoftheworld\professional")  # change if needed
OUTPUT_TXT = Path("origin_urls.txt")                         # final URLs (one per line)
BAD_LOG   = Path("bad_json_files.txt")                       # files we couldn't parse
DEDUP     = True                                             # avoid duplicate URLs
VERBOSE   = False                                            # print per-file messages
# ======================


def load_json_tolerant(p: Path):
    """
    Load JSON trying utf-8 first, then utf-8-sig (BOM).
    Returns dict on success, or None on failure.
    """
    # 1) Try normal UTF-8
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        pass
    except json.JSONDecodeError:
        # Might be BOM or other issue—fall through to next attempts
        pass

    # 2) Try with BOM support
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def extract_origin_url_from_file(p: Path):
    data = load_json_tolerant(p)
    if not isinstance(data, dict):
        return None
    origin = data.get("origin")
    if isinstance(origin, dict):
        url = origin.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


def main():
    if not ROOT_DIR.is_dir():
        print(f"Directory does not exist: {ROOT_DIR}")
        return

    # Prepare outputs
    seen = set()
    if OUTPUT_TXT.exists():
        # If re-running, keep already written URLs to avoid duplicates
        with open(OUTPUT_TXT, "r", encoding="utf-8") as f:
            for line in f:
                u = line.strip()
                if u:
                    seen.add(u)

    bad_files = []

    with open(OUTPUT_TXT, "a", encoding="utf-8") as out:
        # Use rglob to hit every JSON file once
        for jp in ROOT_DIR.rglob("*.json"):
            url = extract_origin_url_from_file(jp)
            if url:
                if not DEDUP or url not in seen:
                    out.write(url + "\n")
                    out.flush()  # keep progress on disk
                    if DEDUP:
                        seen.add(url)
                if VERBOSE:
                    print(f"OK: {jp}")
            else:
                bad_files.append(str(jp))
                if VERBOSE:
                    print(f"BAD JSON: {jp}")

    if bad_files:
        with open(BAD_LOG, "w", encoding="utf-8") as log:
            log.write("\n".join(bad_files))
        print(f"⚠️ Logged {len(bad_files)} problematic files to {BAD_LOG.resolve()}")

    print(f"✅ Done. Wrote origin URLs to {OUTPUT_TXT.resolve()}")
    if DEDUP:
        print(f"Unique URLs: {len(seen)}")


if __name__ == "__main__":
    main()
