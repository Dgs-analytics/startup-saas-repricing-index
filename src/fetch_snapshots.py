"""Wayback Machine CDX Snapshot Fetcher.

Queries the Internet Archive CDX API to retrieve historical pricing page metadata
for target SaaS domains. Includes automatic retry logic, status filtering, and CSV export.
"""

import csv
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from src.config import (
    BACKOFF_FACTOR_SECONDS,
    DEFAULT_RATE_LIMIT_DELAY,
    MAX_RETRIES,
    OUTPUT_MANIFEST_PATH,
    REQUEST_TIMEOUT_SECONDS,
    SEED_FILE_PATH,
    USER_AGENT,
    WAYBACK_CDX_ENDPOINT,
    validate_environment,
)

# Configure logging output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s"
)


def fetch_domain_snapshots(
    domain: str, path_suffix: str = "/pricing"
) -> List[List[str]]:
    """Queries the CDX API for successful HTTP 200 captures of a target URL.

    Args:
        domain (str): Target root domain (e.g., 'convertkit.com').
        path_suffix (str): URL path to evaluate. Defaults to '/pricing'.

    Returns:
        List[List[str]]: Filtered list of [timestamp, original_url, statuscode] records.
    """
    target_url = f"{domain.strip().lower()}{path_suffix}"
    query_params = {
        "url": target_url,
        "output": "json",
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
    }

    encoded_url = f"{WAYBACK_CDX_ENDPOINT}?{urllib.parse.urlencode(query_params)}"
    request = urllib.request.Request(
        encoded_url, headers={"User-Agent": USER_AGENT}
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(
                request, timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                if response.status == 200:
                    raw_data = response.read().decode("utf-8")
                    parsed_json = json.loads(raw_data)

                    # Exclude API header row
                    if len(parsed_json) > 1:
                        snapshots = parsed_json[1:]
                        logging.info(
                            f"Fetched {len(snapshots)} valid snapshots for {domain}"
                        )
                        return snapshots

                    logging.warning(
                        f"No successful captures recorded for {domain}"
                    )
                    return []

        except Exception as err:
            wait_time = BACKOFF_FACTOR_SECONDS**attempt
            logging.warning(
                f"Attempt {attempt}/{MAX_RETRIES} failed for {domain}: {err}. Retrying in {wait_time}s..."
            )
            time.sleep(wait_time)

    logging.error(
        f"Exhausted all {MAX_RETRIES} retries for {domain}. Returning empty dataset."
    )
    return []


def process_seed_manifest() -> Optional[List[Dict[str, str]]]:
    """Reads seed domain CSV, executes archival fetch, and structures summary records.

    Returns:
        Optional[List[Dict[str, str]]]: Aggregated dataset ready for export.
    """
    validate_environment()

    records = []
    with open(SEED_FILE_PATH, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            company = row.get("company", "Unknown")
            domain = row.get("domain", "")

            if not domain:
                continue

            logging.info(f"Processing target domain: {company} ({domain})")
            snapshots = fetch_domain_snapshots(domain)

            first_archived = snapshots[0][0][:8] if snapshots else "N/A"
            latest_archived = snapshots[-1][0][:8] if snapshots else "N/A"

            records.append(
                {
                    "company": company,
                    "domain": domain,
                    "approx_launch_year": row.get("approx_launch_year", "N/A"),
                    "total_snapshots": len(snapshots),
                    "first_archived_date": first_archived,
                    "latest_archived_date": latest_archived,
                }
            )

            time.sleep(DEFAULT_RATE_LIMIT_DELAY)

    return records


def export_summary_manifest(records: List[Dict[str, str]]) -> None:
    """Exports processed snapshot summary records to CSV.

    Args:
        records (List[Dict[str, str]]): List of dictionary records to write.
    """
    if not records:
        logging.error("No data collected to export.")
        return

    fieldnames = list(records[0].keys())
    OUTPUT_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(
        OUTPUT_MANIFEST_PATH, mode="w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logging.info(f"Successfully generated summary report at {OUTPUT_MANIFEST_PATH}")


if __name__ == "__main__":
    extracted_data = process_seed_manifest()
    if extracted_data:
        export_summary_manifest(extracted_data)