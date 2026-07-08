"""
Entity stage CLI — extract, resolve, ground and attach entities to analyzed events.

Usage:
    python3 -m pipeline.entities.run --event-id evt_2026_07_07_israel_middle_east_001
    python3 -m pipeline.entities.run --all-missing [--beat israel_middle_east]

Per STAGE_7_ENTITIES.md (approved 2026-07-08):
  extract (Haiku) → resolve against data/entities/ → ground NEW entities
  (Wikidata/Wikipedia + P18 image) → relevance (Haiku) → validate (machine-
  enforced safety gate) → write event["event"]["entities"] + entity store.

Writes schema_version 0.5 on the event file (additive: optional entities[]).
Runs after Generate (needs the report text) and before/independently of Image.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import anthropic

from pipeline.entities.extract import (
    extract_entities, disambiguate, relevance_notes, confirm_identity,
)
from pipeline.entities.ground import ground_entity
from pipeline.entities.store import EntityStore
from pipeline.entities.validate import validate_entity
from pipeline.schema import EVENT_SCHEMA_VERSION as SCHEMA_VERSION

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("entities.run")

STORE_DIR = ROOT / "data" / "entities"
EVENTS_DIR = ROOT / "data" / "events"


def _relevance_supports(surfaces: list[str], event_data: dict) -> tuple[dict, str]:
    """Receipts for the relevance note. Claims first; B-10 fallback to sources/
    background text matching when claim linkage is missing (STAGE_7 B-10 clause)."""
    lowered = [s.lower() for s in surfaces if s]
    claim_ids = []
    for claim in event_data.get("claims", []):
        text = (claim.get("text") or "").lower()
        if any(s in text for s in lowered):
            claim_ids.append(claim["claim_id"])
    if claim_ids:
        return {"claim_ids": claim_ids[:6], "source_ids": []}, "claims"

    source_ids = []
    for src in event_data.get("sources", []):
        title = (src.get("url") or "").lower()  # titles aren't stored per-source; URL slug is
        if any(s.replace(" ", "-") in title for s in lowered):
            source_ids.append(src["source_id"])
    return {"claim_ids": [], "source_ids": source_ids[:6]}, "sources_fallback"


def attach_entities(analyzed_path: Path, client: anthropic.Anthropic,
                    store_dir: Path = STORE_DIR, force: bool = False) -> bool:
    """Attach entities to one analyzed event file. Returns True if entities were written."""
    data = json.loads(analyzed_path.read_text())
    event = data.get("event", {})
    event_id = event.get("cluster_id", analyzed_path.stem.replace("_analyzed", ""))

    if event.get("entities") and not force:
        log.info("%s already has entities — skipping (use --force to redo)", analyzed_path.name)
        return False
    if not data.get("report"):
        log.info("%s has no report — entity stage needs the report text, skipping", analyzed_path.name)
        return False

    usage: list[dict] = []
    store = EntityStore(store_dir)

    # 1. Extract candidates from the reader-facing text.
    candidates = extract_entities(data, client, usage_log=usage)
    if not candidates:
        log.info("%s: no entities extracted", event_id)
        return False
    log.info("%s: %d candidate entities", event_id, len(candidates))

    # 2. Resolve each against the store; ground the genuinely new ones.
    resolved: list[tuple[dict, dict]] = []  # (candidate, record)
    for cand in candidates:
        name = cand["canonical_name"]
        record = None

        eid = store.lookup_exact(name)
        if eid is None:
            for surface in cand.get("surfaces", []):
                eid = store.lookup_exact(surface)
                if eid:
                    break
        if eid:
            record = store.load(eid)
            if record and record["type"] != cand["type"] and "other" not in (record["type"], cand["type"]):
                # Same name, different kind (e.g. a place vs. an operation) — not a match.
                store.log_review({"kind": "type_conflict", "name": name,
                                  "existing": eid, "candidate_type": cand["type"]})
                record = None

        if record is None:
            fuzzy = store.candidates_for(name)
            for fuzzy_id in fuzzy[:2]:  # at most 2 disambiguation calls per mention
                existing = store.load(fuzzy_id)
                if existing and disambiguate(cand, existing, client, usage_log=usage):
                    record = existing
                    store.add_alias(record, name)
                    break
            if record is None and fuzzy:
                store.log_review({"kind": "low_confidence_match", "name": name,
                                  "candidates": fuzzy, "event_id": event_id})

        if record is None:
            record = store.create(cand["type"], name, event_id)
            # Namesake guard: person grounding requires an LLM identity
            # confirmation of the Wikidata hit against the story context.
            confirm = None
            if cand["type"] == "person":
                confirm = lambda hit, c=cand: confirm_identity(  # noqa: E731
                    c["canonical_name"], c["context"], hit, client, usage_log=usage)
            ground_entity(record, store, confirm=confirm)
            # Audit trail: every person→identity binding is reviewable later.
            if cand["type"] == "person" and record.get("wikidata_qid"):
                store.log_review({"kind": "person_grounded", "entity_id": record["entity_id"],
                                  "name": name, "qid": record["wikidata_qid"],
                                  "context": cand["context"], "event_id": event_id})
            # QID dedup: grounding may reveal this is an entity we already hold
            # under another name (the strongest identity signal we have).
            if record.get("wikidata_qid"):
                existing_id = store.lookup_qid(record["wikidata_qid"])
                if existing_id and existing_id != record["entity_id"]:
                    log.info("%s resolved to existing %s via QID — merging alias", name, existing_id)
                    merged = store.load(existing_id)
                    store.add_alias(merged, name)
                    record = merged

        for surface in cand.get("surfaces", []):
            store.add_alias(record, surface)  # no-ops on canonical name / duplicates
        store.mark_appearance(record, event_id)
        resolved.append((cand, record))

    # 3. Relevance notes (one call for all entities).
    notes = relevance_notes(data, [c for c, _ in resolved], client, usage_log=usage)

    # 4. Validate (machine-enforced safety gate) + persist the store.
    seen_ids = set()
    event_entities = []
    for cand, record in resolved:
        if record["entity_id"] in seen_ids:  # two mentions resolved to one entity
            continue
        seen_ids.add(record["entity_id"])
        validate_entity(record)
        store.save(record)

        supports, grounding = _relevance_supports(cand["surfaces"], data)
        event_entities.append({
            "entity_id": record["entity_id"],
            "surfaces": cand["surfaces"],
            "relevance_to_event": notes.get(cand["canonical_name"]),
            "relevance_supports": supports,
            "relevance_grounding": grounding,
        })
    store.rebuild_index_file()

    # 5. Write the event file (additive schema 0.5).
    event["entities"] = event_entities
    data["schema_version"] = SCHEMA_VERSION
    analyzed_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    total_in = sum(u["in"] for u in usage)
    total_out = sum(u["out"] for u in usage)
    log.info("%s: %d entities attached | tokens %d in / %d out (%d calls)",
             event_id, len(event_entities), total_in, total_out, len(usage))
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="Attach entity cards to analyzed events")
    ap.add_argument("--event-id")
    ap.add_argument("--all-missing", action="store_true")
    ap.add_argument("--beat")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    client = anthropic.Anthropic()

    paths: list[Path] = []
    if args.event_id:
        matches = list(EVENTS_DIR.glob(f"*/{args.event_id}_analyzed.json"))
        if not matches:
            log.error("No analyzed file found for %s", args.event_id)
            sys.exit(1)
        paths = matches
    elif args.all_missing:
        pattern = f"{args.beat}/*_analyzed.json" if args.beat else "*/*_analyzed.json"
        for p in sorted(EVENTS_DIR.glob(pattern)):
            if not json.loads(p.read_text()).get("event", {}).get("entities"):
                paths.append(p)
    else:
        ap.error("give --event-id or --all-missing")

    done = 0
    for p in paths:
        try:
            if attach_entities(p, client, force=args.force):
                done += 1
        except Exception:
            log.exception("Entity stage failed for %s — continuing", p.name)
    log.info("Entities attached to %d/%d event(s)", done, len(paths))


if __name__ == "__main__":
    main()
