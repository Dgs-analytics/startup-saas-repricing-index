"""
src/audit.py

Verifies that the Internet Archive CDX index has usable pricing-page data
for every company defined in seed_domains.csv, before committing to a full
harvest. This is a pre-flight check, not part of the main pipeline run.
"""

import time
import requests

from config import SEED_CSV_PATH
from fetch_snapshots import load_targets_from_csv

CDX_URL = "https://web.archive.org/cdx/search/cdx"
HEADERS = {
    "User-Agent": "SaaSPricingAuditBot/3.0 (+https://github.com/Dgs-analytics/startup-saas-repricing-index)"
}


def query_cdx(url_target: str) -> tuple[int, str]:
    """Queries the CDX API for status-200, deduplicated capture counts."""
    params = {
        "url": url_target,
        "output": "json",
        "fl": "timestamp,statuscode,digest",
        "filter": "statuscode:200",
        "collapse": "digest",
    }

    for attempt in range(3):
        try:
            res = requests.get(CDX_URL, params=params, headers=HEADERS, timeout=30)
            if res.status_code == 200:
                data = res.json()
                count = len(data) - 1 if len(data) > 1 else 0
                return count, "PASS"
            elif res.status_code in (429, 503):
                time.sleep(2 * (attempt + 1))
            else:
                return 0, f"HTTP {res.status_code}"
        except requests.exceptions.Timeout:
            time.sleep(2 * (attempt + 1))
        except Exception:
            return 0, "ERROR"

    return 0, "TIMEOUT"


def run_audit() -> None:
    targets = load_targets_from_csv(SEED_CSV_PATH)
    if not targets:
        print("No targets loaded from seed_domains.csv. Nothing to audit.")
        return

    print(f"{'Company':<15} | {'CDX Status':<12} | {'Records Found':<15} | {'Data Viability'}")
    print("-" * 65)

    usable_count = 0

    for target in targets:
        count, status = query_cdx(target["url"])
        final_status = "PASS" if count >= 10 else ("LOW DATA" if count > 0 else status)
        viability = "USABLE" if final_status == "PASS" else "DISQUALIFIED"
        if final_status == "PASS":
            usable_count += 1

        print(f"{target['display_name']:<15} | {final_status:<12} | {count:<15} | {viability}")
        time.sleep(1.0)

    print("-" * 65)
    print(f"VERIFIED USABLE COUNT: {usable_count} / {len(targets)}")


if __name__ == "__main__":
    run_audit()