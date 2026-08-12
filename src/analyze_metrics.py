"""
src/analyze_metrics.py

Phase 3 of the pipeline: reads the computed repricing_metrics.csv and
produces a single-row executive summary of the whole 13-company dataset.
"""

import logging
import pandas as pd

from config import PROCESSED_DATA_DIR, REPORTS_DIR

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("analyze_metrics")

INPUT_METRICS_PATH = PROCESSED_DATA_DIR / "repricing_metrics.csv"
SUMMARY_REPORT_PATH = REPORTS_DIR / "executive_summary.csv"


def generate_executive_insights() -> None:
    """Reads repricing metrics and calculates portfolio-level aggregations."""
    if not INPUT_METRICS_PATH.exists():
        logger.error(f"Metrics file missing at {INPUT_METRICS_PATH}. Run parse_snapshots first.")
        return

    df = pd.read_csv(INPUT_METRICS_PATH)
    df = df[df["total_snapshots"] > 0]  # exclude companies with no usable data

    if df.empty:
        logger.error("No companies with usable snapshot data found. Cannot generate summary.")
        return

    summary = {
        "total_companies_analyzed": len(df),
        "avg_snapshots_per_company": round(df["total_snapshots"].mean(), 2),
        "max_snapshots_recorded": int(df["total_snapshots"].max()),
        "company_with_max_snapshots": df.loc[df["total_snapshots"].idxmax()]["company"],
        "avg_archived_lifespan_days": round(df["archived_lifespan_days"].mean(), 2),
        "avg_annual_repricing_frequency": round(df["annual_snapshot_frequency"].mean(), 2),
    }

    logger.info("--- EXECUTIVE METRICS SUMMARY ---")
    for key, value in summary.items():
        logger.info(f"{key}: {value}")

    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(SUMMARY_REPORT_PATH, index=False)
    logger.info(f"Executive summary exported to {SUMMARY_REPORT_PATH}")


if __name__ == "__main__":
    generate_executive_insights()