"""
Entity store — the persistent, accumulating library of entities (STAGE_7).

One JSON per entity at data/entities/{entity_id}.json plus an alias index
(index.json) for resolution. Entities are append-only: facts are never
overwritten or deleted; new information appends and every change lands in
the entity's change_log (this powers the reader-facing "updated" marker).

Resolution discipline (STAGE_7): a wrong merge poisons two records; a missed
merge is just a duplicate awaiting cleanup. Always prefer the second failure —
low-confidence matches are logged to review_log.jsonl, never merged silently.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

ENTITY_SCHEMA_VERSION = "0.1"

ENTITY_TYPES = {"person", "organization", "political_party", "technology", "location", "other"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def normalize(name: str) -> str:
    """Case/diacritic/punctuation-insensitive key for alias lookup."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize(name)).strip("_") or "unnamed"


class EntityStore:
    """Load/create/update entity records under a directory (default data/entities/)."""

    def __init__(self, store_dir: Path):
        self.dir = Path(store_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, str] = {}       # normalized alias -> entity_id
        self._qids: dict[str, str] = {}        # wikidata QID -> entity_id
        self._load_index()

    # ── index ────────────────────────────────────────────────────────────

    def _load_index(self) -> None:
        self._index, self._qids = {}, {}
        for p in self.dir.glob("ent_*.json"):
            try:
                rec = json.loads(p.read_text())
            except Exception:
                log.warning("Unreadable entity file skipped: %s", p.name)
                continue
            eid = rec.get("entity_id", p.stem)
            for alias in [rec.get("canonical_name", "")] + rec.get("aliases", []):
                key = normalize(alias)
                if key:
                    self._index.setdefault(key, eid)
            if rec.get("wikidata_qid"):
                self._qids[rec["wikidata_qid"]] = eid

    def rebuild_index_file(self) -> None:
        """Persist the alias index (informational; the store is re-scanned on load)."""
        (self.dir / "index.json").write_text(
            json.dumps(dict(sorted(self._index.items())), indent=2, ensure_ascii=False))

    # ── lookup ───────────────────────────────────────────────────────────

    def lookup_exact(self, name: str) -> Optional[str]:
        return self._index.get(normalize(name))

    def lookup_qid(self, qid: str) -> Optional[str]:
        return self._qids.get(qid)

    def candidates_for(self, name: str) -> list[str]:
        """Entity IDs whose alias tokens contain/are contained by `name`'s tokens
        (e.g. 'Netanyahu' vs 'Benjamin Netanyahu') — disambiguation candidates,
        never auto-merged."""
        tokens = set(normalize(name).split())
        if not tokens:
            return []
        out = []
        for alias, eid in self._index.items():
            alias_tokens = set(alias.split())
            if tokens != alias_tokens and (tokens <= alias_tokens or alias_tokens <= tokens):
                if eid not in out:
                    out.append(eid)
        return out

    # ── record IO ────────────────────────────────────────────────────────

    def path(self, entity_id: str) -> Path:
        return self.dir / f"{entity_id}.json"

    def load(self, entity_id: str) -> Optional[dict]:
        p = self.path(entity_id)
        if not p.exists():
            return None
        return json.loads(p.read_text())

    def save(self, record: dict) -> None:
        record["last_updated"] = _now()
        self.path(record["entity_id"]).write_text(
            json.dumps(record, indent=2, ensure_ascii=False))
        # keep in-memory index current
        eid = record["entity_id"]
        for alias in [record.get("canonical_name", "")] + record.get("aliases", []):
            key = normalize(alias)
            if key:
                self._index.setdefault(key, eid)
        if record.get("wikidata_qid"):
            self._qids[record["wikidata_qid"]] = eid

    # ── creation / mutation (append-only) ────────────────────────────────

    def mint_id(self, etype: str, name: str) -> str:
        base = f"ent_{etype}_{slugify(name)}"
        eid, n = base, 2
        while self.path(eid).exists():
            eid = f"{base}_{n}"
            n += 1
        return eid

    def create(self, etype: str, canonical_name: str, event_id: str) -> dict:
        if etype not in ENTITY_TYPES:
            etype = "other"
        eid = self.mint_id(etype, canonical_name)
        record = {
            "entity_schema_version": ENTITY_SCHEMA_VERSION,
            "entity_id": eid,
            "type": etype,
            "canonical_name": canonical_name,
            "aliases": [],
            "wikidata_qid": None,
            "summary": None,
            "summary_sources": [],
            "image": None,
            "roles_affiliations": [],
            "connections": [],
            "facts": [],
            "review_status": "auto",
            "first_seen_event": event_id,
            "appears_in_events": [event_id],
            "created_at": _now(),
            "last_updated": _now(),
            "change_log": [{
                "date": _today(),
                "summary_of_change": f"Entity created from {event_id}",
                "source": None,
            }],
        }
        return record

    def add_alias(self, record: dict, alias: str) -> None:
        if alias and alias != record["canonical_name"] and alias not in record["aliases"]:
            record["aliases"].append(alias)

    def mark_appearance(self, record: dict, event_id: str) -> None:
        if event_id not in record["appears_in_events"]:
            record["appears_in_events"].append(event_id)

    def add_fact(self, record: dict, fact: dict, change_note: Optional[str] = None) -> bool:
        """Append a fact unless an identical text already exists (append-only:
        existing facts are never modified). Returns True if appended."""
        for existing in record["facts"]:
            if normalize(existing.get("text", "")) == normalize(fact.get("text", "")):
                existing["last_updated"] = _today()
                return False
        fact.setdefault("fact_id", f"fct_{len(record['facts']) + 1:03d}")
        fact.setdefault("first_reported", _today())
        fact.setdefault("last_updated", _today())
        fact.setdefault("supersedes", None)
        fact.setdefault("contradicted_by", None)
        record["facts"].append(fact)
        record["change_log"].append({
            "date": _today(),
            "summary_of_change": change_note or f"Fact added: {fact['text'][:80]}",
            "source": fact.get("source_url"),
        })
        return True

    def log_review(self, entry: dict) -> None:
        entry["at"] = _now()
        with open(self.dir / "review_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
