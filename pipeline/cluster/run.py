"""
Cluster runner — CLI entry point for Stage 2.

Usage:
    # Auto-cluster the golden dataset (correctness check)
    python -m pipeline.cluster.run --source golden --event event_001

    # Auto-cluster live-ingested articles for a beat
    python -m pipeline.cluster.run --beat israel_middle_east

    # Manual override: assign specific article IDs to one cluster
    python -m pipeline.cluster.run --manual art_001,art_002,art_003 \\
        --cluster-id evt_2026_05_28_001 --beat israel_middle_east

    # Tune threshold
    python -m pipeline.cluster.run --source golden --threshold 0.45

Outputs JSON cluster files to data/events/<beat>/.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from pipeline.cluster.embed import embed_articles
from pipeline.cluster.group import auto_cluster, manual_cluster, DEFAULT_THRESHOLD
from pipeline.ingest.store import ArticleStore, load_golden
from pipeline.schema import Article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cluster.run")


def save_clusters(clusters: list[dict], beat: str) -> None:
    out_dir = REPO_ROOT / "data" / "events" / beat
    out_dir.mkdir(parents=True, exist_ok=True)
    for cluster in clusters:
        path = out_dir / f"{cluster['cluster_id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cluster, f, indent=2, ensure_ascii=False)
        log.info("Saved cluster: %s (%d articles)", path.name, cluster["size"])


def load_articles(args) -> tuple[list[Article], str]:
    """Load articles and return (articles, beat_name)."""
    if args.source == "golden":
        articles = load_golden(str(REPO_ROOT / "data" / "golden"), event_id=args.event)
        beat = articles[0].beat or "israel_middle_east" if articles else "israel_middle_east"
        # Golden articles don't have beat set — use the config name
        beat = args.beat or "israel_middle_east"
    else:
        store = ArticleStore(str(REPO_ROOT / "data" / "ingested"), beat=args.beat)
        articles = store.load_all()
        beat = args.beat
    return articles, beat


def run_auto(args) -> None:
    articles, beat = load_articles(args)
    if not articles:
        log.error("No articles found. Run ingest first.")
        return

    log.info("Loaded %d articles for clustering", len(articles))
    embeddings, ids = embed_articles(articles, model_name=args.model)
    pub_dates = [getattr(a, "published_at", "") or "" for a in articles]
    time_window = args.time_window if args.time_window > 0 else None
    clusters = auto_cluster(
        embeddings, ids, beat=beat,
        threshold=args.threshold,
        time_window_hours=time_window,
        pub_dates=pub_dates,
    )

    if not clusters:
        log.warning("No clusters produced.")
        return

    save_clusters(clusters, beat)
    log.info(
        "Done — %d clusters from %d articles. Check data/events/%s/",
        len(clusters), len(articles), beat,
    )


def run_manual(args) -> None:
    ids = [a.strip() for a in args.manual.split(",") if a.strip()]
    beat = args.beat or "israel_middle_east"
    cluster = manual_cluster(ids, beat=beat, cluster_id=args.cluster_id)
    save_clusters([cluster], beat)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="News Synthesis & Credibility Engine — Cluster (Stage 2)"
    )
    parser.add_argument(
        "--source", choices=["live", "golden"], default="live",
        help="Article source: 'live' (ingested) or 'golden' (default: live)",
    )
    parser.add_argument(
        "--beat", default="israel_middle_east",
        help="Beat name (default: israel_middle_east)",
    )
    parser.add_argument(
        "--event", default=None,
        help="Golden event ID to load (e.g. event_001); golden source only",
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help=f"Cosine similarity threshold for same-event grouping (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--model", default="all-MiniLM-L6-v2",
        help="Sentence-transformers model name (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--time-window", type=int, default=48, metavar="HOURS",
        help="Max hours between article pub dates for same-cluster eligibility (default: 48; 0 = disable)",
    )
    parser.add_argument(
        "--manual", default=None, metavar="ID1,ID2,...",
        help="Comma-separated article IDs to assign manually to one cluster",
    )
    parser.add_argument(
        "--cluster-id", default=None,
        help="Cluster ID to use with --manual (auto-generated if omitted)",
    )

    args = parser.parse_args()

    if args.manual:
        run_manual(args)
    else:
        run_auto(args)


if __name__ == "__main__":
    main()
