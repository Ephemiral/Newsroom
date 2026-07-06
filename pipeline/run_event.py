"""
Single-event pipeline orchestration: Analyze (M3) → Annotate (M4) → Generate (M7).

Extracted from scripts/scale_test.py so both the manual scale-test flow and the
autonomous runner (scripts/auto_run.py) share one implementation. Behavior is
identical to the original scale_test version.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]


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
        "schema_version": "0.3",
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
