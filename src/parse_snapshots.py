"""SaaS Pricing Snapshot Parser.

Processes historical snapshot records to compute repricing velocity, date metrics,
and trajectory intervals for analyzed SaaS startups.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.config import DATA_DIR, OUTPUT_MANIFEST_PATH

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s"
)

PROCESSED_METRICS_PATH = DATA_DIR / "repricing_metrics.csv"


def parse_wayback_date(date_str: str) -> Optional[datetime]:
    """Parses a YYYYMMDD string into a standard datetime object.

    Args:
        date_str (str): Raw timestamp string.

    Returns:
        Optional[datetime]: Formatted datetime or None if invalid.
    """
    if not date_str or date_str == "N/A" or len(date_str) < 8:
        return None
    try:
        return datetime.strptime(date_str[:8], "%Y%m%d")
    except ValueError:
        logging.warning(f"Failed to parse date string: {date_str}")
        return None


def calculate_repricing_metrics() -> None:
    """Reads snapshot manifest CSV and generates analytical repricing metrics."""
    if not OUTPUT_MANIFEST_PATH.exists():
        logging.error(f"Manifest file missing at {OUTPUT_MANIFEST_PATH}")
        return

    metrics_list: List[Dict[str, str]] = []

    with open(OUTPUT_MANIFEST_PATH, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            company = row["company"]
            domain = row["domain"]
            total_snapshots = int(row["total_snapshots"])

            first_date = parse_wayback_date(row["first_archived_date"])
            latest_date = parse_wayback_date(row["latest_archived_date"])

            if first_date and latest_date:
                active_days = (latest_date - first_date).days
                snapshots_per_year = round((total_snapshots / max(active_days, 1)) * 365, 2)
                first_date_formatted = first_date.strftime("%Y-%m-%d")
                latest_date_formatted = latest_date.strftime("%Y-%m-%d")
            else:
                active_days = 0
                snapshots_per_year = 0.0
                first_date_formatted = "N/A"
                latest_date_formatted = "N/A"

            metrics_list.append(
                {
                    "company": company,
                    "domain": domain,
                    "approx_launch_year": row["approx_launch_year"],
                    "total_snapshots": total_snapshots,
                    "first_archived_date": first_date_formatted,
                    "latest_archived_date": latest_date_formatted,
                    "archived_lifespan_days": active_days,
                    "annual_snapshot_frequency": snapshots_per_year,
                }
            )

    # Save metrics dataset
    if metrics_list:
        fieldnames = list(metrics_list[0].keys())
        with open(PROCESSED_METRICS_PATH, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(metrics_list)

        logging.info(f"Processed repricing metrics saved to {PROCESSED_METRICS_PATH}")


if __name__ == "__main__":
    calculate_repricing_metrics()