"""
Scale test runner — M9

Two-phase script for running 2–3 fresh events through the full pipeline
(ingest → cluster → analyze → annotate → generate) to verify nothing is brittle.

Usage
-----
# Phase 1: pull fresh articles and show discovered event clusters
python3 scripts/scale_test.py --discover [--beat israel_middle_east] [--max-per-source N]

# Phase 2: run the full pipeline on specific event IDs
python3 scripts/scale_test.py --run-events evt_A,evt_B [--beat israel_middle_east] [--force-generate]

Typical workflow
----------------
1. Run --discover. Review the printed cluster list. Pick 2–3 clusters with ≥4 articles
   and good outlet diversity (ideally spanning left–center–right).
2. Run --run-events with the chosen IDs. Each event gets analyzed, annotated, and
   a report generated. Event page URLs are printed at the end.
3. Open each URL in the running Next.js dev server (npm run dev in web/).
4. Check the UI for rendering issues, classification quality, and report coherence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

import anthropic
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scale_test")


# ── Phase 1: Ingest + Cluster ─────────────────────────────────────────────────

def run_discover(beat: str, max_per_source: int | None) -> None:
    """Pull fresh articles and cluster them; print the event list."""
    from pipeline.ingest.rss import ingest_beat
    from pipeline.ingest.gdelt import ingest_gdelt
    from pipeline.ingest.store import ArticleStore
    from pipeline.cluster.embed import embed_articles
    from pipeline.cluster.group import auto_cluster

    config_path = ROOT / "config" / "beats" / f"{beat}.json"
    if not config_path.exists():
        print(f"ERROR: Beat config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    config = json.loads(config_path.read_text())

    store = ArticleStore(base_dir=str(ROOT / "data" / "ingested"), beat=beat)

    print(f"\n── Ingest RSS ({beat}) ──────────────────────────────────────────")
    saved = skipped = 0
    for article in ingest_beat(config, fetch_body=True, max_per_source=max_per_source):
        if store.save(article):
            saved += 1
        else:
            skipped += 1
    print(f"RSS  — saved: {saved} | skipped: {skipped}")

    if config.get("gdelt", {}).get("enabled"):
        print(f"\n── Ingest GDELT ({beat}) ─────────────────────────────────────")
        gdelt_saved = gdelt_skipped = 0
        for article in ingest_gdelt(config, fetch_body=True):
            if store.save(article):
                gdelt_saved += 1
            else:
                gdelt_skipped += 1
        print(f"GDELT — saved: {gdelt_saved} | skipped: {gdelt_skipped}")
        saved += gdelt_saved

    print(f"Total new articles: {saved}")

    articles = store.load_all(max_age_days=3)
    if not articles:
        print("ERROR: No articles found after ingest.", file=sys.stderr)
        sys.exit(1)

    print(f"\n── Cluster ({len(articles)} articles) ──────────────────────────────")
    embeddings, ids = embed_articles(articles)
    pub_dates = [getattr(a, "published_at", "") or "" for a in articles]
    clusters = auto_cluster(embeddings, ids, beat=beat, pub_dates=pub_dates)

    if not clusters:
        print("No clusters produced. Try lowering --threshold in cluster/run.py.")
        return

    # Save cluster JSONs
    out_dir = ROOT / "data" / "events" / beat
    out_dir.mkdir(parents=True, exist_ok=True)
    for cluster in clusters:
        path = out_dir / f"{cluster['cluster_id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cluster, f, indent=2, ensure_ascii=False)

    MIN_DISTINCT_OUTLETS = 3

    print(f"\nDiscovered {len(clusters)} event cluster(s):\n")
    article_map = {a.article_id: a for a in articles}

    shown = 0
    hidden = 0
    for c in sorted(clusters, key=lambda x: -x["size"]):
        outlet_entries = []
        distinct_outlets: set[str] = set()
        for aid in c["article_ids"]:
            art = article_map.get(aid)
            if art:
                outlet_entries.append(f"{art.outlet} ({art.bias_rating})")
                distinct_outlets.add(art.outlet)

        if len(distinct_outlets) < MIN_DISTINCT_OUTLETS:
            hidden += 1
            continue

        print(f"  {c['cluster_id']}  [{c['size']} articles]")
        for o in outlet_entries:
            print(f"    • {o}")
        print()
        shown += 1

    print(f"(Showing {shown} clusters with ≥{MIN_DISTINCT_OUTLETS} distinct outlets. "
          f"{hidden} single/dual-outlet clusters hidden.)")
    print("──────────────────────────────────────────────────────────────────")
    print("Next step: pick 2–3 clusters spanning left–center–right.")
    print("Then run:")
    print(f"  python3 scripts/scale_test.py --run-events <id1,id2,...> --beat {beat}")


# ── Phase 2: Analyze → Annotate → Generate ───────────────────────────────────

def run_pipeline_for_event(event_id: str, beat: str, client: anthropic.Anthropic,
                            force_generate: bool) -> bool:
    """Run stages 3–5 for a single event. Returns True on success."""
    from pipeline.analyze.extract import extract_claims
    from pipeline.analyze.reconcile import reconcile_claims
    from pipeline.analyze.run import (
        load_articles_cluster, build_sources_list,
        remap_article_ids_to_source_ids,
    )
    from pipeline.annotate.provenance import (
        load_outlet_cache, load_author_cache,
        get_outlet_ownership, get_author_background,
    )
    from pipeline.generate.generate import generate_report, validate_report
    from datetime import datetime, timezone
    from collections import Counter

    cluster_path = ROOT / "data" / "events" / beat / f"{event_id}.json"
    if not cluster_path.exists():
        print(f"  ERROR: cluster file not found: {cluster_path}", file=sys.stderr)
        return False

    out_path = ROOT / "data" / "events" / beat / f"{event_id}_analyzed.json"

    # ── Analyze (M3) ──────────────────────────────────────────────────────────
    print(f"\n  [Analyze] Loading articles...")
    articles, meta = load_articles_cluster(cluster_path)
    if not articles:
        print(f"  ERROR: no articles loaded for {event_id}", file=sys.stderr)
        return False

    print(f"  [Analyze] {len(articles)} articles. Extracting claims (Haiku)...")
    all_raw_claims = []
    for art in articles:
        claims = extract_claims(art, client)
        all_raw_claims.extend(claims)
        print(f"    [{art['article_id']}] {art['outlet']} → {len(claims)} claims")

    print(f"  [Analyze] Reconciling {len(all_raw_claims)} raw claims (Sonnet)...")
    reconciled = reconcile_claims(all_raw_claims, articles, client)
    claim_counts = Counter(c["classification"] for c in reconciled.get("claims", []))
    print(f"  [Analyze] Done — {sum(claim_counts.values())} reconciled claims: "
          + ", ".join(f"{k}:{v}" for k, v in sorted(claim_counts.items())))

    # Build per-event JSON
    sources = build_sources_list(articles)
    art_to_src = {s["article_id"]: s["source_id"] for s in sources}
    for s in sources:
        del s["article_id"]
    reconciled = remap_article_ids_to_source_ids(reconciled, art_to_src)

    event_data = {
        "schema_version": "0.2",
        "event": {
            "cluster_id": event_id,
            "beat": beat,
            "title": reconciled.get("event_title", meta.get("title", event_id)),
            "summary": reconciled.get("event_summary", ""),
            "date": reconciled.get("event_date", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "sources": sources,
        "claims": reconciled.get("claims", []),
        "background": reconciled.get("background", []),
        "report": None,
    }
    out_path.write_text(json.dumps(event_data, indent=2, ensure_ascii=False))
    print(f"  [Analyze] Written: {out_path.relative_to(ROOT)}")

    # ── Annotate (M4) ─────────────────────────────────────────────────────────
    print(f"  [Annotate] Filling provenance cards...")
    outlet_cache = load_outlet_cache()
    author_cache = load_author_cache()

    event_data = json.loads(out_path.read_text())
    for src in event_data["sources"]:
        ownership = get_outlet_ownership(src["outlet"], outlet_cache)
        src["ownership"] = ownership
        bg = get_author_background(src.get("author"), src["outlet"], client, author_cache)
        src["author_background"] = bg
    out_path.write_text(json.dumps(event_data, indent=2, ensure_ascii=False))
    print(f"  [Annotate] Done.")

    # ── Generate (M7) ─────────────────────────────────────────────────────────
    event_data = json.loads(out_path.read_text())
    if event_data.get("report") is not None and not force_generate:
        print(f"  [Generate] Report already exists — skipping (use --force-generate to overwrite).")
    else:
        print(f"  [Generate] Writing report (Sonnet)...")
        report = generate_report(event_data, client)
        warnings = validate_report(report, event_data)
        errors = [w for w in warnings if "[ERROR]" in w]
        if errors:
            for e in errors:
                print(f"  [Generate] {e}", file=sys.stderr)
            print(f"  [Generate] ERROR: ID validation failed — report not written.", file=sys.stderr)
            return False
        if warnings:
            for w in warnings:
                print(f"  [Generate] ⚠  {w}")
        event_data["report"] = report
        out_path.write_text(json.dumps(event_data, indent=2, ensure_ascii=False))
        kind_counts = Counter(p["kind"] for p in report["paragraphs"])
        print(f"  [Generate] {len(report['paragraphs'])} paragraphs — "
              + ", ".join(f"{k}:{v}" for k, v in sorted(kind_counts.items())))

    return True


def run_events(event_ids: list[str], beat: str, force_generate: bool) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    results = {}
    for eid in event_ids:
        print(f"\n══════════════════════════════════════════════════════════════")
        print(f"  Event: {eid}")
        print(f"══════════════════════════════════════════════════════════════")
        ok = run_pipeline_for_event(eid, beat, client, force_generate)
        results[eid] = "✅" if ok else "❌"

    print(f"\n══════════════════════════════════════════════════════════════")
    print(f"Scale test complete")
    print(f"══════════════════════════════════════════════════════════════\n")
    for eid, status in results.items():
        print(f"  {status}  {eid}   → http://localhost:3000/event/{eid}")
    print()
    if all(v == "✅" for v in results.values()):
        print("All events processed successfully. Open the URLs above in the running")
        print("Next.js server (cd web && npm run dev) to check rendering.")
    else:
        failed = [e for e, s in results.items() if s == "❌"]
        print(f"⚠  {len(failed)} event(s) failed: {failed}")
        print("Check stderr output above for details.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scale test runner — M9 pipeline end-to-end",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Phase 1: ingest + cluster, print event list",
    )
    parser.add_argument(
        "--run-events", metavar="ID1,ID2,...",
        help="Phase 2: run full pipeline for these cluster IDs",
    )
    parser.add_argument("--beat", default="israel_middle_east")
    parser.add_argument(
        "--max-per-source", type=int, default=None, metavar="N",
        help="Cap RSS articles per source (Phase 1 only; omit for all)",
    )
    parser.add_argument(
        "--force-generate", action="store_true",
        help="Regenerate report even if it already exists",
    )

    args = parser.parse_args()

    if args.discover:
        run_discover(args.beat, args.max_per_source)
    elif args.run_events:
        ids = [e.strip() for e in args.run_events.split(",") if e.strip()]
        if not ids:
            print("ERROR: --run-events requires at least one event ID.", file=sys.stderr)
            sys.exit(1)
        run_events(ids, args.beat, args.force_generate)
    else:
        parser.print_help()
        print("\nERROR: pass --discover or --run-events.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
