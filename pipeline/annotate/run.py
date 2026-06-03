"""
M4 — Annotate: CLI runner
Usage:
    python3 pipeline/annotate/run.py --source golden
    python3 pipeline/annotate/run.py --analyzed-file data/events/israel_middle_east/evt_2026_05_31_001_analyzed.json

Reads:  per-event analyzed JSON (output of M3)
        data/sources/outlet_provenance.json  (curated outlet cache)
Writes: same file, updated in-place (sources[].ownership + author_background filled)
        data/sources/author_cache.json  (author background cache)
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

from pipeline.annotate.provenance import (
    load_outlet_cache, load_author_cache,
    get_outlet_ownership, get_author_background
)

load_dotenv(ROOT / ".env")


def main():
    parser = argparse.ArgumentParser(description="M4 Annotate — fill source provenance cards")
    parser.add_argument("--source", choices=["golden", "file"], default="golden")
    parser.add_argument("--analyzed-file", default=None,
                        help="Path to analyzed JSON (used with --source file)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Locate the analyzed JSON
    if args.source == "golden" or args.analyzed_file is None:
        analyzed_path = ROOT / "data" / "events" / "israel_middle_east" / "evt_2026_05_31_001_analyzed.json"
    else:
        analyzed_path = Path(args.analyzed_file)

    if not analyzed_path.exists():
        print(f"ERROR: {analyzed_path} not found. Run M3 first.", file=sys.stderr)
        sys.exit(1)

    event_json = json.loads(analyzed_path.read_text())

    outlet_cache = load_outlet_cache()
    author_cache = load_author_cache()

    print(f"Annotating {len(event_json['sources'])} sources...")

    filled_ownership = 0
    filled_author = 0
    skipped_author = 0

    for src in event_json["sources"]:
        src_id = src["source_id"]
        outlet = src["outlet"]
        author = src.get("author")

        # --- Ownership ---
        ownership = get_outlet_ownership(outlet, outlet_cache)
        if ownership:
            src["ownership"] = ownership
            filled_ownership += 1
        else:
            src["ownership"] = None
            print(f"  WARNING: no ownership data for '{outlet}'", file=sys.stderr)

        # --- Author background ---
        print(f"  [{src_id}] {outlet} — author: {author or '(none)'}", end=" ", flush=True)
        bg = get_author_background(author, outlet, client, author_cache)
        src["author_background"] = bg
        if bg:
            filled_author += 1
            print(f"→ got background")
        else:
            skipped_author += 1
            print(f"→ no background (generic/staff byline)")

    # Write updated JSON back
    analyzed_path.write_text(json.dumps(event_json, indent=2, ensure_ascii=False))
    print(f"\nWrote: {analyzed_path.relative_to(ROOT)}")
    print(f"Ownership filled: {filled_ownership}/{len(event_json['sources'])}")
    print(f"Author backgrounds filled: {filled_author} | skipped (generic): {skipped_author}")


if __name__ == "__main__":
    main()
