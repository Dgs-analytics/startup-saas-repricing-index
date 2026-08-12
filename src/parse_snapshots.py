"""
src/parse_snapshots.py

Phase 2 of the pipeline: parses saved HTML snapshots into deduplicated
pricing-page change events, then aggregates those events into per-company
repricing metrics. Every number produced here is computed directly from
real snapshot dates -- nothing is estimated or filled in with a formula.
"""

import csv
import hashlib
import json
import logging
import re
import statistics
from collections import defaultdict
from datetime import datetime

from bs4 import BeautifulSoup

from config import RAW_HTML_DIR, PROCESSED_DATA_DIR, SEED_CSV_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("parse_snapshots")

CLEAN_EVENTS_PATH = PROCESSED_DATA_DIR / "clean_pricing_events.json"
METRICS_CSV_PATH = PROCESSED_DATA_DIR / "repricing_metrics.csv"
TRENDS_CSV_PATH = PROCESSED_DATA_DIR / "annual_repricing_trends.csv"


def load_targets() -> List[Dict[str, str]]:
    """Reads the 13 companies and their pricing URLs from seed_domains.csv."""
    targets = []
    with open(SEED_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            path = row["pricing_path"].strip()
            if path.startswith("/"):
                path = path[1:]
            targets.append({
                "company": row["company"].strip(),
                "domain": row["domain"].strip(),
                "pricing_path": path,
            })
    return targets


def clean_html_to_text(html_content: str) -> str:
    """Strips scripts, styles, and boilerplate, leaving visible page text."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer"]):
        tag.extract()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 200:
        json_matches = re.findall(r'\{"[^"]+":.*\}', html_content)
        if json_matches:
            fallback = " ".join(json_matches)
            text += " " + re.sub(r"\s+", " ", fallback).strip()
    return text


def process_company(target: dict) -> dict:
    """Reads every saved HTML snapshot for one company, strips it to visible
    text, hashes the cleaned text, and keeps only the first snapshot for each
    distinct content hash. This turns repeated re-crawls of an unchanged page
    into a handful of genuine pricing-page CHANGE events."""
    company = target["company"]
    folder_name = company.lower()
    company_dir = RAW_HTML_DIR / folder_name

    if not company_dir.exists():
        logger.warning(f"No HTML folder found for {company} at {company_dir}")
        return {"total_html_files_processed": 0, "unique_content_events": 0, "events": []}

    html_files = sorted(company_dir.glob("*.html"))
    total_files = len(html_files)

    seen_hashes = set()
    events = []

    for html_file in html_files:
        timestamp = html_file.stem
        try:
            html_content = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Could not read {html_file}: {e}")
            continue

        clean_text = clean_html_to_text(html_content)
        if not clean_text:
            continue

        text_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        if text_hash in seen_hashes:
            continue
        seen_hashes.add(text_hash)

        try:
            date_str = datetime.strptime(timestamp[:8], "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            continue

        snapshot_url = f"https://web.archive.org/web/{timestamp}/{target['domain']}/{target['pricing_path']}"

        events.append({
            "date": date_str,
            "timestamp": timestamp,
            "text_hash": text_hash,
            "snapshot_url": snapshot_url,
        })

    events.sort(key=lambda e: e["timestamp"])
    logger.info(f"{company}: {total_files} HTML files -> {len(events)} unique content events")

    return {
        "total_html_files_processed": total_files,
        "unique_content_events": len(events),
        "events": events,
    }


def parse_all_companies() -> dict:
    """Phase 2a: builds clean_pricing_events.json for every seed company,
    from real HTML already saved under data/raw_html/."""
    targets = load_targets()
    result = {}
    for target in targets:
        result[target["company"]] = process_company(target)

    with open(CLEAN_EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved clean pricing events to '{CLEAN_EVENTS_PATH}'")
    return result


def calculate_repricing_metrics() -> None:
    """Phase 2b: aggregates clean_pricing_events.json into two computed
    outputs -- repricing_metrics.csv (per-company summary) and
    annual_repricing_trends.csv (per-company, per-year event counts)."""
    if not CLEAN_EVENTS_PATH.exists():
        logger.info("clean_pricing_events.json not found -- running parser first.")
        events_by_company = parse_all_companies()
    else:
        with open(CLEAN_EVENTS_PATH, "r", encoding="utf-8") as f:
            events_by_company = json.load(f)

    metrics_rows = []
    trend_rows = []

    for company, data in events_by_company.items():
        events = data.get("events", [])
        total_snapshots = len(events)

        if total_snapshots == 0:
            metrics_rows.append({
                "company": company,
                "total_snapshots": 0,
                "archived_lifespan_days": 0,
                "annual_snapshot_frequency": 0,
                "median_days_between_changes": "NONE",
            })
            continue

        dates = sorted(datetime.strptime(e["date"], "%Y-%m-%d") for e in events)
        lifespan_days = (dates[-1] - dates[0]).days
        lifespan_years = lifespan_days / 365.25 if lifespan_days > 0 else (1 / 365.25)
        annual_frequency = round(total_snapshots / lifespan_years, 2)

        if len(dates) >= 2:
            gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            median_gap = round(statistics.median(gaps), 2)
        else:
            median_gap = "NONE"

        metrics_rows.append({
            "company": company,
            "total_snapshots": total_snapshots,
            "archived_lifespan_days": lifespan_days,
            "annual_snapshot_frequency": annual_frequency,
            "median_days_between_changes": median_gap,
        })

        year_counts = defaultdict(int)
        for d in dates:
            year_counts[d.year] += 1
        for year in sorted(year_counts):
            trend_rows.append({"year": year, "company": company, "snapshot_count": year_counts[year]})

    with open(METRICS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "total_snapshots", "archived_lifespan_days",
            "annual_snapshot_frequency", "median_days_between_changes"
        ])
        writer.writeheader()
        writer.writerows(metrics_rows)
    logger.info(f"Saved repricing metrics to '{METRICS_CSV_PATH}'")

    with open(TRENDS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "company", "snapshot_count"])
        writer.writeheader()
        writer.writerows(trend_rows)
    logger.info(f"Saved annual repricing trends to '{TRENDS_CSV_PATH}'")


def main():
    parse_all_companies()
    calculate_repricing_metrics()


if __name__ == "__main__":
    main()