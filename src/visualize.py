"""
src/visualize.py

Phase 4 of the pipeline: generates the three index charts from the
computed repricing metrics and annual trends. All 13 seed companies are
grouped into cohorts for the radar chart -- Miro is intentionally excluded
since it is not part of this project's scope.
"""

import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import (
    PROCESSED_DATA_DIR,
    FIGURES_DIR,
    BG_COLOR,
    CARD_BG,
    TEXT_COLOR,
    GRID_COLOR,
    NEON_CYAN,
    NEON_PINK,
    CHART_COLORS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("visualize")

METRICS_PATH = PROCESSED_DATA_DIR / "repricing_metrics.csv"
TRENDS_PATH = PROCESSED_DATA_DIR / "annual_repricing_trends.csv"

COHORT_MAP = {
    "GitHub": "Developer Tools", "Linear": "Developer Tools",
    "Vercel": "Developer Tools", "Stripe": "Developer Tools",
    "Notion": "Productivity", "Airtable": "Productivity",
    "Coda": "Productivity", "Slack": "Productivity",
    "HubSpot": "Enterprise & CRM", "Zoom": "Enterprise & CRM",
    "Figma": "Creative & Marketing", "Canva": "Creative & Marketing",
    "ConvertKit": "Creative & Marketing",
}

def apply_theme() -> None:
    plt.rcParams.update({
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": CARD_BG,
        "axes.edgecolor": GRID_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "axes.grid": True,
        "grid.color": GRID_COLOR,
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
        "text.color": TEXT_COLOR,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "font.family": "sans-serif",
    })


def chart1_time_series_index() -> None:
    if not TRENDS_PATH.exists():
        logger.warning("Trends file missing, skipping chart 1.")
        return

    df_trends = pd.read_csv(TRENDS_PATH)
    if df_trends.empty:
        logger.warning("Trends file empty, skipping chart 1.")
        return

    fig, ax = plt.subplots(figsize=(11, 6))
    companies = df_trends["company"].unique()
    colors = CHART_COLORS

    for idx, company in enumerate(companies):
        c_data = df_trends[df_trends["company"] == company].sort_values(by="year")
        ax.plot(
            c_data["year"], c_data["snapshot_count"],
            marker="o", linewidth=1.8, label=company,
            color=colors[idx % len(colors)]
        )

    ax.set_yscale("log")
    ax.set_title("SAAS REPRICING INDEX: ANNUAL PRICING-CHANGE TRENDS", fontsize=12, fontweight="bold", color=NEON_CYAN, pad=20)
    ax.set_xlabel("Calendar Year", fontweight="bold", color=TEXT_COLOR, fontsize=10)
    ax.set_ylabel("Detected Pricing-Page Changes (Log Scale)", fontweight="bold", color=TEXT_COLOR, fontsize=10)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax.legend(
        facecolor=CARD_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
        loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8, ncol=1
    )

    plt.savefig(FIGURES_DIR / "chart1_time_series_index.png", dpi=300, bbox_inches="tight")
    plt.close()
    logger.info("Saved chart1_time_series_index.png")


def chart2_radar_cohort_grid() -> None:
    if not METRICS_PATH.exists():
        logger.warning("Metrics file missing, skipping chart 2.")
        return

    df = pd.read_csv(METRICS_PATH)
    df = df[df["total_snapshots"] > 0].copy()
    if df.empty:
        logger.warning("No companies with usable data, skipping chart 2.")
        return

    df["cohort"] = df["company"].map(COHORT_MAP)
    df = df.dropna(subset=["cohort"])

    categories = ["Total Volume", "Lifespan", "Annual Freq", "Cadence Density"]
    df["norm_vol"] = (df["total_snapshots"] / df["total_snapshots"].max()) * 100
    df["norm_life"] = (df["archived_lifespan_days"] / df["archived_lifespan_days"].max()) * 100
    df["norm_freq"] = (df["annual_snapshot_frequency"] / df["annual_snapshot_frequency"].max()) * 100

    valid_density = pd.to_numeric(df["median_days_between_changes"], errors="coerce")
    inv_density = 1 / valid_density.replace(0, np.nan)
    df["norm_density"] = (inv_density / inv_density.max() * 100).fillna(0)

    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    cohorts = ["Developer Tools", "Productivity", "Enterprise & CRM", "Creative & Marketing"]
    palette = [
        ["#00f2fe", "#ff007f", "#ffea00", "#76ff03"],
        ["#ff007f", "#00f2fe", "#7928ca", "#ff9100"],
        ["#7928ca", "#00e676"],
        ["#00e676", "#ff007f", "#00f2fe"],
    ]

    fig, axes = plt.subplots(2, 2, figsize=(15, 12), subplot_kw=dict(polar=True), facecolor=BG_COLOR)
    axes = axes.flatten()

    for idx, cohort_name in enumerate(cohorts):
        ax = axes[idx]
        ax.set_facecolor(CARD_BG)
        c_df = df[df["cohort"] == cohort_name]
        c_colors = palette[idx]

        for c_idx, (_, row) in enumerate(c_df.iterrows()):
            values = [row["norm_vol"], row["norm_life"], row["norm_freq"], row["norm_density"]]
            values += values[:1]
            color = c_colors[c_idx % len(c_colors)]
            ax.plot(angles, values, linewidth=2.2, linestyle="solid", label=row["company"], color=color)
            ax.fill(angles, values, color=color, alpha=0.08)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, color=TEXT_COLOR, fontweight="bold", fontsize=9)
        ax.set_rlabel_position(30)
        ax.tick_params(colors="#8b949e", labelsize=7)
        ax.grid(color=GRID_COLOR, linestyle="--", linewidth=1, alpha=0.8)
        ax.set_title(cohort_name.upper(), fontsize=11, fontweight="bold",
                     color=NEON_CYAN if idx % 2 == 0 else NEON_PINK, pad=20)
        ax.legend(facecolor=CARD_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
                  loc="upper left", bbox_to_anchor=(1.08, 1.05), fontsize=8)

    plt.suptitle("COHORT ARCHETYPES: SECTOR RADAR PROFILES", color=TEXT_COLOR, fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "chart2_strategic_matrix.png", dpi=300, bbox_inches="tight")
    plt.close()
    logger.info("Saved chart2_strategic_matrix.png")


def chart3_neon_lollipop_plot() -> None:
    if not METRICS_PATH.exists():
        logger.warning("Metrics file missing, skipping chart 3.")
        return

    df = pd.read_csv(METRICS_PATH)
    df = df[df["total_snapshots"] > 0].copy()
    df["median_days_between_changes"] = pd.to_numeric(df["median_days_between_changes"], errors="coerce")
    df_clean = df.dropna(subset=["median_days_between_changes"]).sort_values(
        by="median_days_between_changes", ascending=False
    )
    if df_clean.empty:
        logger.warning("No companies with a computable median gap, skipping chart 3.")
        return

    fig, ax = plt.subplots(figsize=(9, 7))
    y_coords = np.arange(len(df_clean))
    gaps = df_clean["median_days_between_changes"]

    ax.hlines(y=y_coords, xmin=0, xmax=gaps, color=GRID_COLOR, alpha=0.8, linewidth=1.5)
    ax.hlines(y=y_coords, xmin=0, xmax=gaps, color=NEON_CYAN, alpha=0.4, linewidth=3)
    ax.scatter(gaps, y_coords, color=NEON_CYAN, s=80, zorder=3, edgecolor=TEXT_COLOR, linewidth=1.5)

    ax.set_yticks(y_coords)
    ax.set_yticklabels(df_clean["company"], fontweight="bold", color=TEXT_COLOR)

    max_gap = gaps.max()
    ax.set_xlim(0, max_gap * 1.22)

    for y, x in zip(y_coords, gaps):
        ax.text(x + (max_gap * 0.02), y, f"{x:.1f}d", va="center", fontweight="bold", color=NEON_PINK, fontsize=9)

    ax.set_title("REVISION CADENCE: MEDIAN DAYS BETWEEN PRICING CHANGES", fontsize=12, fontweight="bold", color=NEON_CYAN, pad=20)
    ax.set_xlabel("Median Days Elapsed Between Changes", fontweight="bold", color=TEXT_COLOR, fontsize=10)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)

    plt.savefig(FIGURES_DIR / "chart3_interval_distribution.png", dpi=300, bbox_inches="tight")
    plt.close()
    logger.info("Saved chart3_interval_distribution.png")


def generate_index_visuals() -> None:
    apply_theme()
    chart1_time_series_index()
    chart2_radar_cohort_grid()
    chart3_neon_lollipop_plot()
    logger.info("Chart generation complete.")


if __name__ == "__main__":
    generate_index_visuals()