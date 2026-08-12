"""
src/fetch_snapshots.py

Harvests CDX metadata from Internet Archive's Web Archive API for the 13
SaaS target domains defined in data/seed_domains.csv, then builds a summary
manifest of what was actually retrieved for each company.
"""

import csv
import json
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import RAW_CDX_DIR, SEED_CSV_PATH, DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("fetch_snapshots")

SUMMARY_MANIFEST_PATH = DATA_DIR / "snapshot_manifest.csv"


def load_targets_from_csv(csv_path=SEED_CSV_PATH) -> List[Dict[str, str]]:
    """Reads the 13 company targets from seed_domains.csv."""
    targets = []
    if not csv_path.exists():
        logger.error(f"Seed domains CSV not found at '{csv_path}'.")
        return targets

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row["company"].strip()
            domain = row["domain"].strip()
            path = row["pricing_path"].strip()

            if path.startswith("/"):
                path = path[1:]

            full_url = f"{domain}/{path}" if path else domain
            targets.append({
                "name": company.lower(),
                "display_name": company,
                "domain": domain,
                "url": full_url
            })

    logger.info(f"Loaded {len(targets)} target domains from '{csv_path}'.")
    return targets


def get_cdx_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "SaaS-Repricing-Index-Research/1.0 (contact@yourdomain.com)"
    })

    retries = Retry(
        total=5,
        backoff_factor=2.0,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def target_already_harvested(target_name: str) -> bool:
    file_path = RAW_CDX_DIR / f"{target_name}_cdx.json"
    return file_path.exists() and file_path.stat().st_size > 0


def fetch_cdx_metadata_for_target(
    session: requests.Session,
    target: Dict[str, str],
    from_date: str = "20100101",
    to_date: str = "20261231"
) -> Optional[List[List[str]]]:
    endpoint = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": target["url"],
        "output": "json",
        "fl": "timestamp,original,mimetype,statuscode,digest,length",
        "from": from_date,
        "to": to_date,
        "collapse": "timestamp:8",
        "filter": "statuscode:200"
    }

    logger.info(f"Issuing CDX API request for target '{target['name']}' ({target['url']})...")

    try:
        response = session.get(endpoint, params=params, timeout=(10.0, 60.0))
        response.raise_for_status()
        data = response.json()

        if not data or len(data) <= 1:
            logger.warning(f"No snapshot metadata returned for target '{target['name']}'.")
            return None

        logger.info(f"Successfully retrieved {len(data) - 1} CDX records for target '{target['name']}'.")
        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP/Network error harvesting target '{target['name']}': {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode CDX JSON response for target '{target['name']}': {str(e)}")
        return None


def harvest_single_target(
    target: Dict[str, str],
    force_refetch: bool = False
) -> bool:
    target_name = target["name"]
    file_path = RAW_CDX_DIR / f"{target_name}_cdx.json"

    if not force_refetch and target_already_harvested(target_name):
        logger.info(f"Target '{target_name}' already harvested. Skipping due to local cache.")
        return True

    RAW_CDX_DIR.mkdir(parents=True, exist_ok=True)
    session = get_cdx_session()

    cdx_data = fetch_cdx_metadata_for_target(session, target)
    if cdx_data is None:
        return False

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cdx_data, f, indent=2)
        logger.info(f"Saved CDX metadata to '{file_path}'.")
        return True
    except IOError as e:
        logger.error(f"Disk write error for target '{target_name}': {str(e)}")
        return False


def harvest_all_targets(
    targets: Optional[List[Dict[str, str]]] = None,
    max_workers: int = 2,
    force_refetch: bool = False
) -> Dict[str, bool]:
    if targets is None:
        targets = load_targets_from_csv()

    results = {}
    logger.info(f"Starting CDX harvest for {len(targets)} targets with max_workers={max_workers}.")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_target = {
            executor.submit(harvest_single_target, target, force_refetch): target
            for target in targets
        }

        for future in as_completed(future_to_target):
            target = future_to_target[future]
            target_name = target["name"]
            try:
                status = future.result()
                results[target_name] = status
            except Exception as e:
                logger.critical(f"Unhandled execution exception for target '{target_name}': {str(e)}")
                results[target_name] = False

    successful = sum(1 for status in results.values() if status)
    logger.info(f"CDX harvest complete. Completed successfully: {successful}/{len(targets)} targets.")
    return results


def process_seed_manifest() -> List[Dict[str, str]]:
    """Phase 1 of the pipeline: harvest CDX metadata for all 13 seed companies.

    Returns the list of target dicts that were processed, so main.py can
    confirm the harvest produced something before continuing.
    """
    targets = load_targets_from_csv()
    if not targets:
        logger.error("No targets loaded from seed CSV. Aborting harvest.")
        return []

    harvest_all_targets(targets)
    return targets


def export_summary_manifest(targets: List[Dict[str, str]]) -> None:
    """Builds snapshot_manifest.csv: one row per company showing how many
    real, status-200 snapshots were actually retrieved, based on the CDX
    JSON files saved to disk. This replaces any hand-written or fabricated
    manifest with numbers computed directly from real harvested data.
    """
    rows = []

    for target in targets:
        target_name = target["name"]
        cdx_file = RAW_CDX_DIR / f"{target_name}_cdx.json"

        if not cdx_file.exists():
            rows.append({
                "company": target["display_name"],
                "domain": target["domain"],
                "total_snapshots": 0,
                "first_snapshot_timestamp": "NONE",
                "last_snapshot_timestamp": "NONE",
            })
            continue

        with open(cdx_file, "r", encoding="utf-8") as f:
            records = json.load(f)

        timestamps = []
        for row in records:
            if isinstance(row, dict):
                ts = row.get("timestamp", "")
                if ts:
                    timestamps.append(ts)
            elif isinstance(row, list) and row:
                if row[0] == "timestamp":
                    continue  # CDX header row
                timestamps.append(row[0])

        if timestamps:
            rows.append({
                "company": target["display_name"],
                "domain": target["domain"],
                "total_snapshots": len(timestamps),
                "first_snapshot_timestamp": min(timestamps),
                "last_snapshot_timestamp": max(timestamps),
            })
        else:
            rows.append({
                "company": target["display_name"],
                "domain": target["domain"],
                "total_snapshots": 0,
                "first_snapshot_timestamp": "NONE",
                "last_snapshot_timestamp": "NONE",
            })

    with open(SUMMARY_MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "domain", "total_snapshots",
            "first_snapshot_timestamp", "last_snapshot_timestamp"
        ])
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Exported snapshot manifest to '{SUMMARY_MANIFEST_PATH}' ({len(rows)} companies).")


def main():
    targets = process_seed_manifest()
    if targets:
        export_summary_manifest(targets)


if __name__ == "__main__":
    main()