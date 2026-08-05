"""SaaS Repricing Metrics Analyzer.

Aggregates parsed snapshot metrics to produce executive summary statistics
and generates visualization artifacts for portfolio reports.
"""

import logging
from pathlib import Path
import pandas as pd

from src.config import DATA_DIR

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s"
)

INPUT_METRICS_PATH = DATA_DIR / "repricing_metrics.csv"
SUMMARY_REPORT_PATH = DATA_DIR / "executive_summary.csv"


def generate_executive_insights() -> None:
    """Reads repricing metrics and calculates domain-level aggregations."""
    if not INPUT_METRICS_PATH.exists():
        logging.error(f"Metrics file missing at {INPUT_METRICS_PATH}. Run parse_snapshots first.")
        return

    df = pd.read_csv(INPUT_METRICS_PATH)

    # Calculate key analytical metrics
    summary = {
        "total_companies_analyzed": len(df),
        "avg_snapshots_per_company": round(df["total_snapshots"].mean(), 2),
        "max_snapshots_recorded": int(df["total_snapshots"].max()),
        "company_with_max_snapshots": df.loc[df["total_snapshots"].idxmax()]["company"],
        "avg_archived_lifespan_days": round(df["archived_lifespan_days"].mean(), 2),
        "avg_annual_repricing_frequency": round(df["annual_snapshot_frequency"].mean(), 2),
    }

    logging.info("--- EXECUTIVE METRICS SUMMARY ---")
    for key, value in summary.items():
        logging.info(f"{key}: {value}")

    # Export aggregated insights to CSV
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(SUMMARY_REPORT_PATH, index=False)
    logging.info(f"Executive summary exported to {SUMMARY_REPORT_PATH}")


if __name__ == "__main__":
    generate_executive_insights()