"""
Ingest runner — CLI entry point for Stage 1.

Usage:
    # Pull live articles for a beat via RSS
    python -m pipeline.ingest.run --beat israel_middle_east

    # Use the golden dataset as input (for testing downstream stages)
    python -m pipeline.ingest.run --source golden --event event_001

    # Limit articles per source (useful during dev)
    python -m pipeline.ingest.run --beat israel_middle_east --max-per-source 5

    # Skip full-text fetch (fast, uses RSS summary only)
    python -m pipeline.ingest.run --beat israel_middle_east --no-body
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Resolve repo root so we can run from any working directory
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.ingest.rss import ingest_beat
from pipeline.ingest.gdelt import ingest_gdelt
from pipeline.ingest.store import ArticleStore, load_golden

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest.run")


def load_beat_config(beat_name: str) -> dict:
    config_path = REPO_ROOT / "config" / "beats" / f"{beat_name}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Beat config not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def run_live(args) -> None:
    config = load_beat_config(args.beat)
    store = ArticleStore(
        base_dir=str(REPO_ROOT / "data" / "ingested"),
        beat=args.beat,
    )

    saved = skipped = 0

    # --- RSS ingest ---
    for article in ingest_beat(
        config,
        fetch_body=not args.no_body,
        max_per_source=args.max_per_source,
    ):
        if store.save(article):
            saved += 1
        else:
            skipped += 1

    log.info("RSS done — saved: %d, duplicates skipped: %d", saved, skipped)

    # --- GDELT ingest (if enabled in beat config) ---
    if config.get("gdelt", {}).get("enabled") and not args.no_gdelt:
        log.info("Running GDELT ingest...")
        gdelt_articles = ingest_gdelt(config, fetch_body=not args.no_body)
        gdelt_saved = gdelt_skipped = 0
        for article in gdelt_articles:
            if store.save(article):
                gdelt_saved += 1
            else:
                gdelt_skipped += 1
        log.info("GDELT done — saved: %d, duplicates skipped: %d", gdelt_saved, gdelt_skipped)
        saved += gdelt_saved
        skipped += gdelt_skipped

    log.info("Total — saved: %d, duplicates skipped: %d", saved, skipped)


def run_golden(args) -> None:
    golden_dir = str(REPO_ROOT / "data" / "golden")
    articles = load_golden(golden_dir, event_id=args.event)
    log.info("Golden dataset loaded — %d articles available for downstream stages.", len(articles))
    for a in articles:
        log.info("  [%s] %s", a.outlet, a.title[:80])


def main() -> None:
    parser = argparse.ArgumentParser(description="News Synthesis & Credibility Engine — Ingest (Stage 1)")

    parser.add_argument(
        "--source",
        choices=["live", "golden"],
        default="live",
        help="'live' pulls from RSS; 'golden' loads the hand-built fixture (default: live)",
    )
    parser.add_argument(
        "--beat",
        default="israel_middle_east",
        help="Beat name matching a file in config/beats/ (default: israel_middle_east)",
    )
    parser.add_argument(
        "--event",
        default=None,
        help="Golden event ID to load, e.g. event_001 (golden source only; omit for all events)",
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=None,
        metavar="N",
        help="Cap articles fetched per RSS source (useful for fast dev runs)",
    )
    parser.add_argument(
        "--no-body",
        action="store_true",
        help="Skip full-text fetch; store RSS summary only (fast, no trafilatura calls)",
    )
    parser.add_argument(
        "--no-gdelt",
        action="store_true",
        help="Skip GDELT ingest even if enabled in beat config",
    )

    args = parser.parse_args()

    if args.source == "golden":
        run_golden(args)
    else:
        run_live(args)


if __name__ == "__main__":
    main()
