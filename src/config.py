"""Global Configuration & Path Directory Manager.

Single source of truth for every file path used across this pipeline.
Every other script imports paths from here instead of defining its own.
"""

import sys
from pathlib import Path

# Base Repository Root
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Input Data Paths ---
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_CDX_DIR = DATA_DIR / "raw_cdx"
RAW_HTML_DIR = DATA_DIR / "raw_html"
RAW_SNAPSHOTS_DIR = DATA_DIR / "raw_snapshots"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SEED_CSV_PATH = DATA_DIR / "seed_domains.csv"

# --- Output Paths ---
OUTPUT_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
REPORTS_DIR = OUTPUT_DIR / "reports"

# --- Directories that must exist before the pipeline runs ---
_REQUIRED_DIRS = [
    RAW_DATA_DIR,
    RAW_CDX_DIR,
    RAW_HTML_DIR,
    RAW_SNAPSHOTS_DIR,
    PROCESSED_DATA_DIR,
    FIGURES_DIR,
    REPORTS_DIR,
]

for directory in _REQUIRED_DIRS:
    directory.mkdir(parents=True, exist_ok=True)


def validate_environment() -> None:
    """Checks that the project is set up correctly before the pipeline runs.

    Confirms the seed domains CSV exists (the pipeline cannot run without it)
    and that all required data/output directories are present. Exits with a
    clear error message if anything critical is missing, rather than letting
    the pipeline fail partway through with a confusing traceback.
    """
    if not SEED_CSV_PATH.exists():
        print(
            f"FATAL: seed domains file not found at '{SEED_CSV_PATH}'.\n"
            f"This file defines the 13 companies tracked by this project "
            f"and is required to run the pipeline."
        )
        sys.exit(1)

    for directory in _REQUIRED_DIRS:
        if not directory.exists():
            print(f"FATAL: required directory missing: '{directory}'")
            sys.exit(1)

    print("Environment validated: seed CSV and all required directories present.")