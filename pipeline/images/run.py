"""
Image stage CLI — attach a permissively-licensed file photo to analyzed events.

Usage:
    python3 -m pipeline.images.run --event-id evt_2026_06_28_040 [--beat israel_middle_east] [--force]
    python3 -m pipeline.images.run --all-missing [--beat israel_middle_east]

Writes event["event"]["image"] into the per-event *_analyzed.json and bumps
schema_version to 0.3 (additive change: optional image object with attribution).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import anthropic

from pipeline.images.select import find_event_image
from pipeline.schema import EVENT_SCHEMA_VERSION as SCHEMA_VERSION

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("images.run")


def _used_image_titles(beat_dir: Path, exclude_event: str) -> set[str]:
    """file_titles of images already used by OTHER events in this beat — never reuse."""
    used = set()
    for p in beat_dir.glob("*_analyzed.json"):
        if p.name == exclude_event:
            continue
        try:
            img = json.loads(p.read_text()).get("event", {}).get("image")
            if img and img.get("file_title"):
                used.add(img["file_title"])
        except Exception:
            continue
    return used


def attach_image(path: Path, client: anthropic.Anthropic, force: bool = False) -> bool:
    """Attach an image to one analyzed event file. Returns True if an image was attached."""
    data = json.loads(path.read_text())
    event = data.get("event", {})
    if event.get("image") and not force:
        log.info("%s already has an image — skipping (use --force to replace)", path.name)
        return False

    image = find_event_image(event, client, exclude_titles=_used_image_titles(path.parent, path.name))
    # Record the attempt either way so automated re-runs don't retry every cycle
    event["image_attempted_at"] = datetime.now(timezone.utc).isoformat()
    if image is None:
        log.info("%s: no suitable image found — leaving imageless", path.name)
        event["image"] = None
    else:
        event["image"] = image
        log.info("%s: attached %s (%s)", path.name, image["file_title"], image["license"])

    data["event"] = event
    data["schema_version"] = SCHEMA_VERSION
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return image is not None


def main():
    parser = argparse.ArgumentParser(description="Attach Commons file photos to analyzed events")
    parser.add_argument("--event-id")
    parser.add_argument("--all-missing", action="store_true", help="Process every analyzed event without an image")
    parser.add_argument("--beat", default="israel_middle_east")
    parser.add_argument("--force", action="store_true", help="Replace an existing image")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    beat_dir = ROOT / "data" / "events" / args.beat

    if args.event_id:
        path = beat_dir / f"{args.event_id}_analyzed.json"
        if not path.exists():
            print(f"ERROR: {path} not found", file=sys.stderr)
            sys.exit(1)
        attach_image(path, client, force=args.force)
    elif args.all_missing:
        paths = sorted(beat_dir.glob("*_analyzed.json"))
        attached = skipped = 0
        for path in paths:
            ev = json.loads(path.read_text()).get("event", {})
            # Skip events with an image, and past no-result attempts (unless --force)
            if (ev.get("image") or "image_attempted_at" in ev) and not args.force:
                skipped += 1
                continue
            if attach_image(path, client, force=args.force):
                attached += 1
        log.info("Done — %d images attached, %d already had images, %d total events", attached, skipped, len(paths))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
