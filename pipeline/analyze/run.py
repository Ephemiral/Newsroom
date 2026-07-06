"""
M3 — Analyze: CLI runner
Usage:
    python3 -m pipeline.analyze.run --source golden [--cluster-id evt_2026_05_31_001]
    python3 pipeline/analyze/run.py --source golden

Reads:  data/golden/event_001/articles/*.json  (when --source golden)
        data/events/<beat>/<cluster_id>.json   (for the cluster manifest)
Writes: data/events/<beat>/<cluster_id>_analyzed.json  (per-event JSON v0.1)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import anthropic

# Allow running as script or module
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.analyze.extract import extract_claims
from pipeline.analyze.reconcile import reconcile_claims

load_dotenv(ROOT / ".env")


def load_articles_golden() -> tuple[list[dict], dict]:
    """Load all 10 golden articles + meta."""
    base = ROOT / "data" / "golden" / "event_001"
    meta = json.loads((base / "meta.json").read_text())
    articles = []
    for aid in meta["article_ids"]:
        path = base / "articles" / f"{aid}.json"
        articles.append(json.loads(path.read_text()))
    return articles, meta


def load_articles_cluster(cluster_path: Path) -> tuple[list[dict], dict]:
    """Load articles referenced in a cluster JSON."""
    cluster = json.loads(cluster_path.read_text())
    beat = cluster["beat"]
    articles = []
    for aid in cluster["article_ids"]:
        # Search order: golden → ingested (live runs) → legacy events/articles path
        candidates = [
            ROOT / "data" / "golden" / "event_001" / "articles" / f"{aid}.json",
            ROOT / "data" / "ingested" / beat / f"{aid}.json",
            ROOT / "data" / "events" / beat / "articles" / f"{aid}.json",
        ]
        for c in candidates:
            if c.exists():
                articles.append(json.loads(c.read_text()))
                break
        else:
            print(f"  WARNING: article {aid} not found, skipping", file=sys.stderr)
    return articles, cluster


def build_sources_list(articles: list[dict]) -> list[dict]:
    """Map article IDs to source IDs for the per-event JSON."""
    sources = []
    for i, art in enumerate(articles):
        src_id = f"src_{i+1:03d}"
        sources.append({
            "source_id": src_id,
            "article_id": art["article_id"],   # internal cross-ref, stripped at output
            "outlet": art["outlet"],
            "url": art.get("url", ""),
            "author": art.get("author"),
            "published_at": art.get("published_at", ""),
            "bias_rating": art["bias_rating"],
            "bias_rating_source": art["bias_rating_source"],
            "state_alignment": art.get("state_alignment"),
            "ownership": None,        # M4 (Annotate) will fill this
            "author_background": None,
            "amplification_signal": None,
        })
    return sources


def remap_article_ids_to_source_ids(reconciled: dict, art_to_src: dict) -> dict:
    """Replace article_id references with src_xxx ids throughout the reconciled output."""
    for claim in reconciled.get("claims", []):
        claim["supported_by"] = [art_to_src.get(a, a) for a in claim.pop("supported_by_articles", [])]
        claim["contested_by"] = [art_to_src.get(a, a) for a in claim.pop("contested_by_articles", [])]
        for fv in claim.get("framing_variants", []):
            fv["source_id"] = art_to_src.get(fv.pop("article_id", ""), "")

    for bg in reconciled.get("background", []):
        bg["sources"] = [art_to_src.get(a, a) for a in bg.pop("article_ids", [])]

    return reconciled


def main():
    parser = argparse.ArgumentParser(description="M3 Analyze — extract and reconcile claims")
    parser.add_argument("--source", choices=["golden", "cluster"], default="golden")
    parser.add_argument("--cluster-id", default="evt_2026_05_31_001",
                        help="Cluster ID to load (used with --source cluster)")
    parser.add_argument("--beat", default="israel_middle_east")
    parser.add_argument("--dry-run", action="store_true",
                        help="Extract only, skip reconciliation, print raw claims")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # --- Load articles ---
    if args.source == "golden":
        articles, meta = load_articles_golden()
        cluster_id = "evt_2026_05_31_001"
        beat = meta["beat"]
    else:
        cluster_path = ROOT / "data" / "events" / args.beat / f"{args.cluster_id}.json"
        articles, meta = load_articles_cluster(cluster_path)
        cluster_id = args.cluster_id
        beat = args.beat

    print(f"Loaded {len(articles)} articles for cluster {cluster_id}")

    # --- Step 1: Per-article extraction (Haiku) ---
    print("\nStep 1: Extracting claims per article (Haiku)...")
    all_raw_claims = []
    for art in articles:
        print(f"  [{art['article_id']}] {art['outlet']} ({art['bias_rating']})", end=" ", flush=True)
        claims = extract_claims(art, client)
        all_raw_claims.extend(claims)
        print(f"→ {len(claims)} claims")

    print(f"\nTotal raw claims extracted: {len(all_raw_claims)}")

    if args.dry_run:
        print("\n--- DRY RUN: raw claims ---")
        print(json.dumps(all_raw_claims, indent=2))
        return

    # --- Step 2: Cross-article reconciliation (Sonnet) ---
    print("\nStep 2: Reconciling claims across sources (Sonnet)...")
    reconciled = reconcile_claims(all_raw_claims, articles, client)
    print(f"  → {len(reconciled.get('claims', []))} reconciled claims")
    print(f"  → {len(reconciled.get('background', []))} background points")

    # --- Build sources list + remap IDs ---
    sources = build_sources_list(articles)
    art_to_src = {s["article_id"]: s["source_id"] for s in sources}
    # Remove internal cross-ref field before writing
    for s in sources:
        del s["article_id"]

    reconciled = remap_article_ids_to_source_ids(reconciled, art_to_src)

    # --- Assemble per-event JSON ---
    output = {
        "schema_version": "0.1",
        "event": {
            "cluster_id": cluster_id,
            "beat": beat,
            "title": reconciled.get("event_title", meta.get("title", "")),
            "summary": reconciled.get("event_summary", meta.get("description", "")),
            "date": reconciled.get("event_date", meta.get("date", "")),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "sources": sources,
        "claims": reconciled.get("claims", []),
        "background": reconciled.get("background", []),
        "report": None,
    }

    # --- Write output ---
    out_dir = ROOT / "data" / "events" / beat
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{cluster_id}_analyzed.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\nWrote: {out_path.relative_to(ROOT)}")
    print("\nClaim breakdown:")
    from collections import Counter
    counts = Counter(c["classification"] for c in output["claims"])
    for cls, n in sorted(counts.items()):
        print(f"  {cls}: {n}")


if __name__ == "__main__":
    main()
