"""
Thread store (STAGE_8) — persistent story arcs at data/threads/{thread_id}.json,
plus the event-signature index and IDF table the matcher runs on.

A thread ALWAYS holds ≥2 events (G's decision, 2026-07-08): threads are only
ever created from a matched pair, so a lone report is never shown as
"developing". Titles are AI-generated but human-overridable — once
title_source == "manual" the pipeline never rewrites the title.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pipeline.threading.match import Signature, signature_from_event, build_idf, is_major_entity

log = logging.getLogger(__name__)

THREAD_SCHEMA_VERSION = "0.1"
DORMANT_AFTER_DAYS = 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "story"


class ThreadStore:
    """Threads + a read-through index of event signatures and entity IDF."""

    def __init__(self, threads_dir: Path, events_dir: Path, entities_dir: Path):
        self.dir = Path(threads_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.events_dir = Path(events_dir)
        self.entities_dir = Path(entities_dir)
        self._threads: dict[str, dict] = {}
        self._event_to_thread: dict[str, str] = {}
        self._load_threads()

    # ── threads ──────────────────────────────────────────────────────────

    def _load_threads(self) -> None:
        for p in self.dir.glob("thr_*.json"):
            try:
                t = json.loads(p.read_text())
            except Exception:
                log.warning("Unreadable thread skipped: %s", p.name)
                continue
            self._threads[t["thread_id"]] = t
            for ev in t.get("events", []):
                self._event_to_thread[ev["cluster_id"]] = t["thread_id"]

    def thread_of(self, cluster_id: str) -> Optional[str]:
        return self._event_to_thread.get(cluster_id)

    def load(self, thread_id: str) -> Optional[dict]:
        return self._threads.get(thread_id)

    def all_threads(self) -> list[dict]:
        return list(self._threads.values())

    def mint_id(self, title: str) -> str:
        base = f"thr_{_slug(title)}"
        tid, n = base, 2
        while (self.dir / f"{tid}.json").exists() or tid in self._threads:
            tid = f"{base}_{n}"; n += 1
        return tid

    def save(self, thread: dict) -> None:
        thread["last_updated"] = _now()
        (self.dir / f"{thread['thread_id']}.json").write_text(
            json.dumps(thread, indent=2, ensure_ascii=False))
        self._threads[thread["thread_id"]] = thread
        for ev in thread.get("events", []):
            self._event_to_thread[ev["cluster_id"]] = thread["thread_id"]

    def create(self, thread_id: str, title: str, summary: str) -> dict:
        return {
            "thread_schema_version": THREAD_SCHEMA_VERSION,
            "thread_id": thread_id,
            "title": title,
            "title_source": "auto",
            "summary": summary,
            "status": "developing",
            "beats": [],
            "key_entities": [],
            "events": [],
            "created_at": _now(),
            "last_updated": _now(),
            "change_log": [{"date": _today(), "summary_of_change": "Thread created"}],
        }

    def add_event(self, thread: dict, sig: Signature, chapter_summary: str,
                  link_score: float) -> None:
        """Append an event chapter (chronological), refresh beats/key_entities/status."""
        if any(e["cluster_id"] == sig.cluster_id for e in thread["events"]):
            return
        thread["events"].append({
            "cluster_id": sig.cluster_id,
            "date": sig.date,
            "chapter_summary": chapter_summary,
            "link_score": round(link_score, 3),
        })
        thread["events"].sort(key=lambda e: e["date"])
        if sig.beat and sig.beat not in thread["beats"]:
            thread["beats"].append(sig.beat)
        key = set(thread["key_entities"]) | {e for e in sig.entities if is_major_entity(e)}
        thread["key_entities"] = sorted(key)
        thread["change_log"].append(
            {"date": _today(), "summary_of_change": f"Added {sig.cluster_id}"})

    def refresh_status(self, thread: dict, now_ts: float | None = None) -> None:
        """developing → dormant when the latest event is older than DORMANT_AFTER_DAYS."""
        if not thread["events"]:
            return
        now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
        latest = max(thread["events"], key=lambda e: e["date"])["date"]
        try:
            latest_ts = datetime.fromisoformat(f"{latest}T00:00:00+00:00").timestamp()
        except Exception:
            return
        thread["status"] = "dormant" if (now_ts - latest_ts) / 86400.0 > DORMANT_AFTER_DAYS else "developing"

    def log_review(self, entry: dict) -> None:
        entry["at"] = _now()
        with open(self.dir / "review_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ── event signatures + IDF (read-through over data/events + data/entities) ──

    def load_signatures(self) -> dict[str, Signature]:
        """cluster_id -> Signature for every analyzed event (no embeddings yet)."""
        sigs = {}
        for p in self.events_dir.glob("*/*_analyzed.json"):
            try:
                sig = signature_from_event(json.loads(p.read_text()))
            except Exception:
                continue
            if sig.cluster_id:
                sigs[sig.cluster_id] = sig
        return sigs

    def build_idf(self) -> dict[str, float]:
        """IDF per entity from the store's appears_in_events counts + event total."""
        n_events = sum(1 for _ in self.events_dir.glob("*/*_analyzed.json"))
        df: dict[str, int] = {}
        for p in self.entities_dir.glob("ent_*.json"):
            try:
                rec = json.loads(p.read_text())
            except Exception:
                continue
            df[rec["entity_id"]] = max(1, len(rec.get("appears_in_events", [])))
        return build_idf(df, max(1, n_events))
