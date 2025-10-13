# videosdownload.py
import csv
import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

from yt_dlp import YoutubeDL
from datetime import datetime

# NEW imports for direct downloads
import requests
from http.cookiejar import MozillaCookieJar
from urllib.parse import urlparse

# ---------- Settings ----------
VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov", ".avi"}
VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "player.vimeo.com", "video.adsoftheworld.com")
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)

HERE = Path(__file__).resolve().parent
STUDENT_ROOT = HERE / "adsoftheworld" / "professional"
COOKIES_TXT = HERE / "cookies.txt"
COOKIES_JSON = HERE / "cookies.json"
# ------------------------------

# NEW constants for the direct path
DIRECT_FILE_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
)


def ensure_cookies_txt() -> Optional[Path]:
    """
    Return path to a cookies.txt file suitable for yt-dlp.
    If cookies.txt is missing but cookies.json exists, convert it.
    """
    if COOKIES_TXT.exists():
        return COOKIES_TXT
    if not COOKIES_JSON.exists():
        return None
    try:
        convert_cookies_json_to_netscape(COOKIES_JSON, COOKIES_TXT)
        print(f"  • Converted cookies.json -> {COOKIES_TXT.name}")
        return COOKIES_TXT if COOKIES_TXT.exists() else None
    except Exception as e:
        print(f"  ! Failed to convert cookies.json: {e}")
        return None


def convert_cookies_json_to_netscape(json_path: Path, out_path: Path) -> None:
    """
    Convert a cookies.json (array of cookie objects) to Netscape cookies.txt.
    Handles common fields: domain, path, name, value, secure, httpOnly,
    expiry/expirationDate/expires.
    """
    raw = json_path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    if not isinstance(data, list):
        # Some tools wrap in {"cookies":[...]}
        data = data.get("cookies", [])
    lines = ["# Netscape HTTP Cookie File", "# This file was generated from cookies.json\n"]
    for c in data:
        domain = c.get("domain") or c.get("host") or ""
        if not domain:
            continue
        path = c.get("path", "/")
        name = c.get("name") or ""
        value = c.get("value") or ""
        secure = "TRUE" if c.get("secure") else "FALSE"

        # expiry fields in seconds; fall back to far-future if missing
        exp = (
            c.get("expirationDate")
            or c.get("expiry")
            or c.get("expires")
        )
        if isinstance(exp, str):
            # try parse RFC/ISO dates if any; else ignore
            try:
                exp = int(datetime.fromisoformat(exp).timestamp())
            except Exception:
                exp = None
        if not isinstance(exp, (int, float)):
            exp = 1999999999  # ~2033

        # hostOnly flag toggles leading dot
        host_only = c.get("hostOnly")
        if host_only is True and domain.startswith("."):
            domain = domain.lstrip(".")
        if host_only is False and not domain.startswith("."):
            domain = "." + domain

        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"

        lines.append(
            "\t".join(
                [
                    domain,
                    include_subdomains,
                    path,
                    secure,
                    str(int(exp)),
                    name,
                    value,
                ]
            )
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def folder_has_any_video(p: Path) -> bool:
    return any(f.is_file() and f.suffix.lower() in VIDEO_EXTS for f in p.iterdir())


def find_json(p: Path) -> Optional[Path]:
    for f in p.iterdir():
        if f.is_file() and f.suffix.lower() == ".json":
            return f
    return None


def extract_video_info(json_path: Path) -> Tuple[List[str], Optional[str]]:
    """Return (urls, referer). Handle BOM and fallback URL scan."""
    raw = json_path.read_text(encoding="utf-8-sig")
    urls: List[str] = []
    referer: Optional[str] = None

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            origin = data.get("origin") or {}
            referer = origin.get("url") or origin.get("page")
            vids = data.get("videos") or []
            if isinstance(vids, list):
                for v in vids:
                    if isinstance(v, dict):
                        u = v.get("video_url") or v.get("url")
                        if u:
                            urls.append(u)
                    elif isinstance(v, str):
                        urls.append(v)
    except Exception:
        pass

    if not urls:
        for u in URL_RE.findall(raw):
            lo = u.lower()
            if any(h in lo for h in VIDEO_HOSTS):
                urls.append(u)

    # De-dup preserve order
    seen = set()
    dedup = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    return dedup, referer


def normalize_youtube_embed(url: str) -> str:
    m = re.search(r"youtube\.com/embed/([a-zA-Z0-9_-]{6,})", url)
    return f"https://www.youtube.com/watch?v={m.group(1)}" if m else url


def prepare_url(u: str) -> str:
    u = u.strip()
    if "youtube.com/embed/" in u:
        u = normalize_youtube_embed(u)
    return u


# ---------- NEW: direct-download helpers ----------

def has_direct_file_extension(url: str) -> bool:
    """Quick check based on URL path suffix (ignores querystring)."""
    try:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in DIRECT_FILE_EXTS)
    except Exception:
        return False


def looks_direct_file(url: str) -> bool:
    """
    Cheap pre-filter before doing a HEAD:
    - Obvious file extension OR a known CDN host that usually serves files.
    """
    host = urlparse(url).netloc.lower()
    if has_direct_file_extension(url):
        return True
    likely_file_hosts = {
        "video.adsoftheworld.com",
        "cdn.adsoftheworld.com",
    }
    return any(host.endswith(h) for h in likely_file_hosts)


def load_requests_cookies(cookies_path: Optional[Path]) -> Optional[MozillaCookieJar]:
    """Load cookies.txt into a CookieJar usable by requests."""
    if not cookies_path or not cookies_path.exists():
        return None
    cj = MozillaCookieJar(str(cookies_path))
    try:
        cj.load(ignore_discard=True, ignore_expires=True)
        return cj
    except Exception:
        return None


def try_head_is_video(url: str, headers: dict, cookies) -> bool:
    """Confirm via HEAD if Content-Type starts with video/ (best-effort)."""
    try:
        r = requests.head(url, headers=headers, cookies=cookies, allow_redirects=True, timeout=15)
        ct = r.headers.get("Content-Type", "").lower()
        return ct.startswith("video/")
    except Exception:
        return False


def download_via_requests(url: str, out_path: Path, referer: Optional[str], cookies) -> bool:
    """
    Stream the file to disk with requests. Returns True on success.
    """
    headers = {"User-Agent": DEFAULT_UA}
    if referer:
        headers["Referer"] = referer

    # As a safety check, skip if HEAD says it's not a video, unless it's clearly a file by extension.
    if not has_direct_file_extension(url):
        if not try_head_is_video(url, headers, cookies):
            return False

    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    try:
        with requests.get(url, headers=headers, cookies=cookies, stream=True, timeout=30) as r:
            r.raise_for_status()
            with tmp_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
        tmp_path.replace(out_path)
        return True
    except Exception as e:
        # Clean up partial file on failure
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        print(f"  ✖ Direct download failed ({e})")
        return False


# ---------- HYBRID downloader (UPDATED) ----------
def download_urls_to_folder(
    urls: List[str],
    out_dir: Path,
    base_name: str,
    referer: Optional[str],
    cookies_path: Optional[Path],
    failures_writer: csv.writer,
):
    if not urls:
        print("  • No video URLs found.")
        return

    # Prepare requests cookies (if any)
    requests_cookies = load_requests_cookies(cookies_path)

    # yt-dlp common opts
    fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    common = {
        "noplaylist": True,
        "ignoreerrors": True,
        "overwrites": False,
        "quiet": False,
        "format": fmt,
    }
    if cookies_path and cookies_path.exists():
        common["cookies"] = str(cookies_path)
    else:
        print("  ! No cookies available — private/age-restricted embeds may fail.")
    if referer:
        common["http_headers"] = {"Referer": referer}

    for idx, raw_url in enumerate(urls, 1):
        url = prepare_url(raw_url)
        suffix = "" if len(urls) == 1 else f"_{idx}"
        # Prefer mp4 naming; yt-dlp will switch extension if different
        preferred_name = f"{base_name}{suffix}.mp4"
        out_file = out_dir / preferred_name

        print(f"  ↓ Downloading ({idx}/{len(urls)}): {url}")

        # 1) Fast path for obvious direct-file links
        used_direct = False
        if looks_direct_file(url):
            if out_file.exists():
                print("    • Already downloaded (direct) → skipping.")
                continue
            if download_via_requests(url, out_file, referer, requests_cookies):
                print("    • Direct download complete.")
                used_direct = True

        if used_direct:
            continue

        # 2) Fallback to yt-dlp
        outtmpl = str((out_dir / f"{base_name}{suffix}.%(ext)s"))
        opts = dict(common)
        opts["outtmpl"] = outtmpl
        try:
            with YoutubeDL(opts) as ydl:
                ret = ydl.download([url])
                if ret != 0:
                    failures_writer.writerow([str(out_dir), base_name, url, "nonzero_return"])
        except Exception as e:
            print(f"  ✖ Download failed: {url} ({e})")
            failures_writer.writerow([str(out_dir), base_name, url, str(e)])


def main():
    if not STUDENT_ROOT.exists():
        print(f"Path does not exist: {STUDENT_ROOT}")
        return

    cookies_path = ensure_cookies_txt()

    failures_path = HERE / "failed_downloads.csv"
    with failures_path.open("w", newline="", encoding="utf-8") as fcsv:
        failures_writer = csv.writer(fcsv)
        failures_writer.writerow(["folder", "basename", "url", "error"])

        for campaign_dir in sorted(p for p in STUDENT_ROOT.iterdir() if p.is_dir()):
            print(f"\n▶ {campaign_dir.name}")

            if folder_has_any_video(campaign_dir):
                print("  • Video already present → skipping.")
                continue

            json_path = find_json(campaign_dir)
            if not json_path:
                print("  • No JSON file found → skipping.")
                continue

            try:
                urls, referer = extract_video_info(json_path)
            except Exception as e:
                print(f"  ✖ Failed to read JSON: {json_path} ({e})")
                failures_writer.writerow([str(campaign_dir), campaign_dir.name, "(none)", f"json_read_error: {e}"])
                continue

            download_urls_to_folder(urls, campaign_dir, campaign_dir.name, referer, cookies_path, failures_writer)

    print(f"\nDone. Failures (if any) logged to: {failures_path}")


if __name__ == "__main__":
    main()
