"""
src/download_snapshots.py

Downloads raw HTML pages from the Wayback Machine using harvested CDX metadata.
Saves HTML files locally into data/raw_html/<company>/<timestamp>.html
"""

import json
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import RAW_CDX_DIR, RAW_HTML_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("download_snapshots")


def get_http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def download_html_for_company(company_name: str, session: requests.Session) -> int:
    cdx_file = RAW_CDX_DIR / f"{company_name}_cdx.json"
    if not cdx_file.exists():
        logger.warning(f"No CDX metadata file found for {company_name} at {cdx_file}")
        return 0

    with open(cdx_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    valid_records = []
    last_digest = None
    for r in records:
        if isinstance(r, dict):
            status = str(r.get("statuscode", ""))
            digest = r.get("digest", "")
            timestamp = r.get("timestamp", "")
            original = r.get("original", "")
        elif isinstance(r, list) and len(r) >= 5:
            if r[0] == "timestamp":
                continue  # CDX header row
            timestamp, original, mime, status, digest = r[0], r[1], r[2], r[3], r[4]
        else:
            continue

        if status == "200" and digest != last_digest:
            valid_records.append({"timestamp": timestamp, "original": original, "digest": digest})
            last_digest = digest

    company_html_dir = RAW_HTML_DIR / company_name
    company_html_dir.mkdir(parents=True, exist_ok=True)

    downloaded_count = 0
    logger.info(f"[{company_name}] Found {len(valid_records)} unique HTML snapshots to process...")

    for item in valid_records:
        ts = item["timestamp"]
        orig = item["original"]
        out_path = company_html_dir / f"{ts}.html"

        if out_path.exists() and out_path.stat().st_size > 0:
            downloaded_count += 1
            continue

        wayback_url = f"https://web.archive.org/web/{ts}id_/{orig}"
        try:
            res = session.get(wayback_url, timeout=(10.0, 30.0))
            if res.status_code == 200:
                with open(out_path, "w", encoding="utf-8", errors="ignore") as out_f:
                    out_f.write(res.text)
                downloaded_count += 1
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to download {wayback_url}: {e}")

    logger.info(f"[{company_name}] Completed: {downloaded_count}/{len(valid_records)} HTML pages saved.")
    return downloaded_count


def download_all_html() -> None:
    """Phase 1b of the pipeline: downloads real HTML for every company that
    has CDX metadata on disk. Safe to re-run -- already-downloaded pages
    are skipped automatically."""
    if not RAW_CDX_DIR.exists():
        logger.error(f"CDX directory '{RAW_CDX_DIR}' missing. Run fetch_snapshots first.")
        return

    session = get_http_session()
    cdx_files = [f.stem.replace("_cdx", "") for f in RAW_CDX_DIR.glob("*_cdx.json")]

    for company_name in cdx_files:
        download_html_for_company(company_name, session)


def main():
    download_all_html()


if __name__ == "__main__":
    main()