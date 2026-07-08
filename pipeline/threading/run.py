"""
Threading stage CLI + attach_thread() (STAGE_8).

Usage:
    python3 -m pipeline.threading.run --event-id evt_...           # thread one event
    python3 -m pipeline.threading.run --backfill-days 45 [--reset] # seed threads from recent events
    python3 -m pipeline.threading.run --list                        # print current threads

Runs after Generate + Entities (needs entities to match on) and writes
event["event"]["thread_id"] (schema 0.6, additive) + the thread manifest in
data/threads/. A thread is only created from a matched PAIR, so a lone report
is never surfaced as "developing".
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
import numpy as np

from pipeline.cluster.embed import embed_texts
from pipeline.threading import match as M
from pipeline.threading.store import ThreadStore
from pipeline.threading.summarize import thread_title, chapter_summary, event_brief
from pipeline.schema import EVENT_SCHEMA_VERSION as SCHEMA_VERSION

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("threading.run")

EVENTS_DIR = ROOT / "data" / "events"
THREADS_DIR = ROOT / "data" / "threads"
ENTITIES_DIR = ROOT / "data" / "entities"


def _event_path(cluster_id: str) -> Path | None:
    m = list(EVENTS_DIR.glob(f"*/{cluster_id}_analyzed.json"))
    return m[0] if m else None


def _embed(sigs: list[M.Signature], emb_cache: dict[str, np.ndarray]) -> None:
    """Attach embeddings to signatures, computing any missing in one batch call."""
    todo = [s for s in sigs if s.cluster_id not in emb_cache and s.text]
    if todo:
        vecs = embed_texts([s.text for s in todo])
        for s, v in zip(todo, vecs):
            emb_cache[s.cluster_id] = v
    for s in sigs:
        s.embedding = emb_cache.get(s.cluster_id)


def attach_thread(analyzed_path: Path, client: anthropic.Anthropic, store: ThreadStore,
                  idf: dict | None = None, spec: float | None = None,
                  all_sigs: dict | None = None, emb_cache: dict | None = None,
                  usage: list | None = None) -> dict:
    """Assign one event to a thread (joining, creating a pair, or leaving it
    unthreaded). Returns {"thread_id": id|None, "modified": [paths]}."""
    data = json.loads(analyzed_path.read_text())
    e_sig = M.signature_from_event(data)
    if not e_sig.cluster_id:
        return {"thread_id": None, "modified": []}

    idf = idf if idf is not None else store.build_idf()
    all_sigs = all_sigs if all_sigs is not None else store.load_signatures()
    spec = spec if spec is not None else M.specific_threshold(idf, len(all_sigs))
    emb_cache = emb_cache if emb_cache is not None else {}
    usage = usage if usage is not None else []

    # Candidate past events inside the window.
    candidates = [s for cid, s in all_sigs.items()
                  if cid != e_sig.cluster_id and M.within_window(e_sig, s)]
    if not candidates:
        return {"thread_id": None, "modified": []}

    _embed([e_sig, *candidates], emb_cache)

    qualifying = []
    for p in candidates:
        ok, s = M.qualifies(e_sig, p, idf, spec)
        if ok:
            qualifying.append((s, p))
    if not qualifying:
        log.info("%s: no qualifying story link — stays unthreaded", e_sig.cluster_id)
        return {"thread_id": None, "modified": []}

    qualifying.sort(key=lambda x: -x[0])
    best_score, best_p = qualifying[0]

    # Cross-thread guard: if matches span ≥2 existing threads, assign to the best
    # and log the rest for a human to consider merging (never auto-merge threads).
    matched_threads = {store.thread_of(p.cluster_id) for _, p in qualifying}
    matched_threads.discard(None)
    if len(matched_threads) > 1:
        store.log_review({"kind": "cross_thread_match", "event": e_sig.cluster_id,
                          "threads": sorted(matched_threads), "chosen": store.thread_of(best_p.cluster_id)})

    modified: list[Path] = []
    existing_tid = store.thread_of(best_p.cluster_id)

    if existing_tid:
        thread = store.load(existing_tid)
        cs = chapter_summary(event_brief(data), thread.get("summary"), client, usage)
        store.add_event(thread, e_sig, cs, best_score)
    else:
        # New thread from the matched pair {best_p, e}. best_p is the opener.
        p_path = _event_path(best_p.cluster_id)
        if not p_path:
            log.warning("Matched event %s has no file — skipping thread creation", best_p.cluster_id)
            return {"thread_id": None, "modified": []}
        p_data = json.loads(p_path.read_text())
        title, summary = thread_title([event_brief(p_data), event_brief(data)], client, usage)
        tid = store.mint_id(title)
        thread = store.create(tid, title, summary)
        store.add_event(thread, best_p, chapter_summary(event_brief(p_data), None, client, usage), 1.0)
        store.add_event(thread, e_sig, chapter_summary(event_brief(data), summary, client, usage), best_score)
        # Backfill the opener's thread_id.
        p_data["event"]["thread_id"] = tid
        p_data["schema_version"] = SCHEMA_VERSION
        p_path.write_text(json.dumps(p_data, indent=2, ensure_ascii=False))
        modified.append(p_path)

    store.refresh_status(thread)
    store.save(thread)

    data["event"]["thread_id"] = thread["thread_id"]
    data["schema_version"] = SCHEMA_VERSION
    analyzed_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    modified.append(analyzed_path)

    log.info("%s → thread %s (score %.2f, %d chapters)",
             e_sig.cluster_id, thread["thread_id"], best_score, len(thread["events"]))
    return {"thread_id": thread["thread_id"], "modified": modified}


def backfill(days: int, client: anthropic.Anthropic, store: ThreadStore, reset: bool = False) -> None:
    """Seed threads from events published in the last `days`, oldest→newest."""
    if reset:
        for p in list(THREADS_DIR.glob("thr_*.json")) + list(THREADS_DIR.glob("*.jsonl")):
            p.unlink()
        store.__init__(THREADS_DIR, EVENTS_DIR, ENTITIES_DIR)  # reload empty

    sigs = store.load_signatures()
    idf = store.build_idf()
    spec = M.specific_threshold(idf, len(sigs))
    import time
    cutoff = time.time() - days * 86400
    window = sorted((s for s in sigs.values() if s.ts >= cutoff), key=lambda s: s.ts)
    log.info("Backfill: %d events in the last %d days", len(window), days)

    emb_cache: dict = {}
    _embed(list(sigs.values()), emb_cache)  # embed everything once

    usage: list = []
    threaded = 0
    for s in window:
        path = _event_path(s.cluster_id)
        if not path:
            continue
        r = attach_thread(path, client, store, idf=idf, spec=spec,
                          all_sigs=sigs, emb_cache=emb_cache, usage=usage)
        if r["thread_id"]:
            threaded += 1
    ti = sum(u["in"] for u in usage); to = sum(u["out"] for u in usage)
    log.info("Backfill done: %d events threaded into %d threads | tokens %d in / %d out",
             threaded, len(store.all_threads()), ti, to)


def main() -> None:
    ap = argparse.ArgumentParser(description="Story threading")
    ap.add_argument("--event-id")
    ap.add_argument("--backfill-days", type=int)
    ap.add_argument("--reset", action="store_true", help="clear data/threads before backfill")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    store = ThreadStore(THREADS_DIR, EVENTS_DIR, ENTITIES_DIR)

    if args.list:
        for t in sorted(store.all_threads(), key=lambda x: x["last_updated"], reverse=True):
            print(f"{t['thread_id']:40s} [{t['status']:10s}] {len(t['events'])}ch  {t['title']}")
        return

    client = anthropic.Anthropic()
    if args.backfill_days:
        backfill(args.backfill_days, client, store, reset=args.reset)
    elif args.event_id:
        path = _event_path(args.event_id)
        if not path:
            log.error("No analyzed file for %s", args.event_id); sys.exit(1)
        attach_thread(path, client, store)
    else:
        ap.error("give --event-id, --backfill-days, or --list")


if __name__ == "__main__":
    main()
