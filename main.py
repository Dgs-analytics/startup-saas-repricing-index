"""Master Execution Pipeline for SaaS Repricing Index."""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Make everything inside src/ importable by simple module name
# (e.g. `import config` instead of `import src.config`), matching
# how every file inside src/ imports its own dependencies.
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from analyze_metrics import generate_executive_insights
from config import validate_environment
from fetch_snapshots import export_summary_manifest, process_seed_manifest
from download_snapshots import download_all_html
from parse_snapshots import calculate_repricing_metrics
from visualize import generate_index_visuals

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

    logging.info("Phase 1b/4: Downloading real HTML snapshots for all companies...")
    download_all_html()

    logging.info("Phase 2/4: Calculating historical lifespan and frequency metrics...")
    calculate_repricing_metrics()

    logging.info("Phase 3/4: Aggregating executive summary statistics...")
    generate_executive_insights()

    logging.info("Phase 4/4: Generating index visualization artifacts...")
    generate_index_visuals()

    elapsed = (datetime.now() - start_time).total_seconds()
    logging.info(f"=== PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS ===")


if __name__ == "__main__":
    run_pipeline()