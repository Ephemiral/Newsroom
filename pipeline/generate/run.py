"""
M7 — Generate: CLI runner
Usage:
    python3 -m pipeline.generate.run [--event-id evt_2026_05_31_001] [--beat israel_middle_east]
    python3 pipeline/generate/run.py

Reads:  data/events/<beat>/<event_id>_analyzed.json
Writes: data/events/<beat>/<event_id>_analyzed.json  (report field populated in-place)

The script never overwrites a report that already exists unless --force is passed.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import anthropic

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.generate.generate import generate_report, validate_report

load_dotenv(ROOT / ".env")


def main():
    parser = argparse.ArgumentParser(description="M7 Generate — produce reader-facing report")
    parser.add_argument(
        "--event-id",
        default="evt_2026_05_31_001",
        help="Cluster/event ID (without _analyzed.json suffix)",
    )
    parser.add_argument("--beat", default="israel_middle_east")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing report field if already present",
    )
    args = parser.parse_args()

    # --- Load analyzed JSON ---
    event_path = ROOT / "data" / "events" / args.beat / f"{args.event_id}_analyzed.json"
    if not event_path.exists():
        print(f"ERROR: File not found: {event_path}", file=sys.stderr)
        sys.exit(1)

    event_data = json.loads(event_path.read_text())

    # Guard: don't overwrite unless --force
    if event_data.get("report") is not None and not args.force:
        print(
            f"Report field already populated for {args.event_id}. "
            "Use --force to regenerate.",
            file=sys.stderr,
        )
        sys.exit(0)

    print(f"Event:   {event_data['event']['title']}")
    print(f"Claims:  {len(event_data['claims'])}")
    print(f"Sources: {len(event_data['sources'])}")

    # --- API client ---
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # --- Generate ---
    print("\nGenerating report...")
    report = generate_report(event_data, client)
    print(f"  → {len(report['paragraphs'])} paragraphs generated")

    # --- Validate ---
    print("\nValidating...")
    warnings = validate_report(report, event_data)
    if warnings:
        for w in warnings:
            print(w)
        # Errors are fatal; warnings (empty supports) are not
        errors = [w for w in warnings if "[ERROR]" in w]
        if errors:
            print(f"\n{len(errors)} errors found — aborting write.", file=sys.stderr)
            sys.exit(1)
    else:
        print("  ✓ All claim_ids and source_ids valid")

    # --- Write back in-place ---
    event_data["report"] = report
    event_path.write_text(json.dumps(event_data, indent=2, ensure_ascii=False))
    print(f"\nWrote report to: {event_path.relative_to(ROOT)}")

    # --- Summary ---
    from collections import Counter
    kinds = Counter(p["kind"] for p in report["paragraphs"])
    print("\nParagraph breakdown:")
    for kind, n in sorted(kinds.items()):
        print(f"  {kind}: {n}")

    print("\nDone. Human review recommended before publishing.")


if __name__ == "__main__":
    main()
