"""Central configuration settings for the SaaS Repricing Index pipeline.

Defines relative directory paths, API endpoints, rate limits, and request headers
to prevent hardcoded path failures across different operating systems.
"""

import sys
from pathlib import Path

# Base Directory Resolution
BASE_DIR = Path(__file__).resolve().parent.parent

# File & Directory Paths
DATA_DIR = BASE_DIR / "data"
SEED_FILE_PATH = DATA_DIR / "seed_domains.csv"
OUTPUT_MANIFEST_PATH = DATA_DIR / "snapshot_manifest.csv"

# API & Network Settings
WAYBACK_CDX_ENDPOINT = "http://web.archive.org/cdx/search/cdx"
USER_AGENT = "SaaS-Pricing-Research-Bot/1.0 (+https://github.com/Dgs-analytics/startup-saas-repricing-index)"
REQUEST_TIMEOUT_SECONDS = 15
BACKOFF_FACTOR_SECONDS = 2.0
MAX_RETRIES = 3
DEFAULT_RATE_LIMIT_DELAY = 1.0  # Seconds between requests to prevent IP throttling


def validate_environment() -> None:
    """Verifies that mandatory source data files exist before pipeline execution."""
    if not SEED_FILE_PATH.exists():
        sys.exit(
            f"[FATAL ERROR] Missing seed dataset at {SEED_FILE_PATH}. "
            "Please ensure data/seed_domains.csv exists before running."
        )