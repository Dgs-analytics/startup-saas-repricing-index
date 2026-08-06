"""Master Execution Pipeline for SaaS Repricing Index."""

import logging
import sys
from datetime import datetime

from src.analyze_metrics import generate_executive_insights
from src.config import validate_environment
from src.fetch_snapshots import export_summary_manifest, process_seed_manifest
from src.parse_snapshots import calculate_repricing_metrics
from src.visualize import generate_charts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def run_pipeline() -> None:
    """Executes the end-to-end SaaS repricing analytics workflow."""
    start_time = datetime.now()
    logging.info("=== STARTING SAAS REPRICING ANALYTICS PIPELINE ===")

    validate_environment()

    logging.info("Phase 1/4: Querying Internet Archive CDX API...")
    extracted_records = process_seed_manifest()

    if not extracted_records:
        logging.error("Pipeline aborted: Failed to retrieve domain snapshots.")
        return

    export_summary_manifest(extracted_records)

    logging.info("Phase 2/4: Calculating historical lifespan and frequency metrics...")
    calculate_repricing_metrics()

    logging.info("Phase 3/4: Aggregating executive summary statistics...")
    generate_executive_insights()

    logging.info("Phase 4/4: Generating data visualization artifacts...")
    generate_charts()

    elapsed = (datetime.now() - start_time).total_seconds()
    logging.info(f"=== PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS ===")


if __name__ == "__main__":
    run_pipeline()