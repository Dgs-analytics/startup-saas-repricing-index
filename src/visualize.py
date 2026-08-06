"""SaaS Repricing Visualization Engine.

Generates analytical charts from parsed snapshot metrics for executive presentations.
"""

import logging
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

INPUT_METRICS_PATH = DATA_DIR / "repricing_metrics.csv"
OUTPUT_CHART_PATH = DATA_DIR / "repricing_velocity.png"


def generate_charts() -> None:
    """Generates bar charts comparing snapshot counts across analyzed SaaS companies."""
    if not INPUT_METRICS_PATH.exists():
        logging.error(f"Metrics file missing at {INPUT_METRICS_PATH}")
        return

    df = pd.read_csv(INPUT_METRICS_PATH)
    df = df.sort_values(by="total_snapshots", ascending=False)

    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")

    palette = sns.color_palette("viridis", len(df))
    ax = sns.barplot(x="total_snapshots", y="company", data=df, palette=palette)

    plt.title("Historical Pricing Page Change Velocity (Wayback Captures)", fontsize=14, pad=15)
    plt.xlabel("Total Archived Snapshots (HTTP 200)", fontsize=12)
    plt.ylabel("SaaS Company", fontsize=12)

    # Annotate bars with exact values
    for index, value in enumerate(df["total_snapshots"]):
        ax.text(value + 30, index, f"{value:,}", va="center", fontsize=10, fontweight="bold")

    plt.tight_layout()
    OUTPUT_CHART_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_CHART_PATH, dpi=300)
    plt.close()

    logging.info(f"Visualization chart successfully saved to {OUTPUT_CHART_PATH}")


if __name__ == "__main__":
    generate_charts()