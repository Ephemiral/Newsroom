"""
Accountability stage CLI + attach_accountability() (STAGE_9).

Usage:
    python3 -m pipeline.accountability.run --thread-id thr_...     # audit one thread
    python3 -m pipeline.accountability.run --all                    # audit every thread
    python3 -m pipeline.accountability.run --list-pending           # show auto flags awaiting review
    python3 -m pipeline.accountability.run --approve thr_... acc_003
    python3 -m pipeline.accountability.run --suppress thr_... acc_003

Review-gated (G's decision, 2026-07-08): detection writes flags with
review_status="auto"; the frontend renders ONLY "approved" flags. A human
approves each with --approve. Detection is autonomous; DISPLAY is gated.

Receipts (text/source_id/url) are reconstructed from the real event data, never
from the model's echo — the model only returns claim_id references + a note.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import anthropic

from pipeline.accountability.detect import detect_self_reversals
from pipeline.threading.store import ThreadStore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("accountability.run")

EVENTS_DIR = ROOT / "data" / "events"
THREADS_DIR = ROOT / "data" / "threads"
ENTITIES_DIR = ROOT / "data" / "entities"


def _event_path(cluster_id: str) -> Path | None:
    m = list(EVENTS_DIR.glob(f"*/{cluster_id}_analyzed.json"))
    return m[0] if m else None


def _claim_index(thread: dict) -> dict[str, dict]:
    """claim_id -> {cluster_id, date, text, by_outlet: {outlet: {source_id, url, stance}}}
    across all of the thread's events. The single source of truth for receipts —
    a flag's claims must be found here, attributed to the queried outlet."""
    index: dict[str, dict] = {}
    for ev in thread["events"]:
        path = _event_path(ev["cluster_id"])
        if not path:
            continue
        data = json.loads(path.read_text())
        src = {s["source_id"]: s for s in data.get("sources", [])}
        for claim in data.get("claims", []):
            by_outlet: dict[str, dict] = {}
            for stance, ids in (("supported", claim.get("supported_by", [])),
                                ("contested", claim.get("contested_by", []))):
                for sid in ids:
                    s = src.get(sid)
                    if not s:
                        continue
                    by_outlet.setdefault(s["outlet"], {
                        "source_id": sid, "url": s.get("url"), "stance": stance})
            index[claim["claim_id"]] = {
                "cluster_id": ev["cluster_id"], "date": ev["date"],
                "text": claim.get("text", ""), "by_outlet": by_outlet,
            }
    return index


def _outlet_timelines(thread: dict, index: dict) -> dict[str, list[dict]]:
    """{outlet: [{date, cluster_id, claims:[{claim_id, stance, text}]}]} chronological."""
    per_event: dict[str, dict[str, dict]] = {}  # outlet -> cluster_id -> chapter
    for cid, info in index.items():
        for outlet, ref in info["by_outlet"].items():
            chapters = per_event.setdefault(outlet, {})
            ch = chapters.setdefault(info["cluster_id"],
                                     {"date": info["date"], "cluster_id": info["cluster_id"], "claims": []})
            ch["claims"].append({"claim_id": cid, "stance": ref["stance"], "text": info["text"]})
    timelines = {}
    for outlet, chapters in per_event.items():
        timelines[outlet] = sorted(chapters.values(), key=lambda c: c["date"])
    return timelines


def _reconstruct(flag: dict, outlet: str, index: dict) -> dict | None:
    """Validate a raw flag against real data and build the full stored entry, or
    None if it fails (both claims must exist AND be attributed to `outlet`)."""
    e_id, l_id = flag.get("earlier_claim_id"), flag.get("later_claim_id")
    e, l = index.get(e_id), index.get(l_id)
    if not e or not l:
        log.warning("[%s] flag dropped: claim_id not found (%s / %s)", outlet, e_id, l_id)
        return None
    if outlet not in e["by_outlet"] or outlet not in l["by_outlet"]:
        log.warning("[%s] flag dropped: a claim is not attributable to this outlet", outlet)
        return None
    if e["date"] > l["date"]:  # ensure earlier is actually earlier
        e, l, e_id, l_id = l, e, l_id, e_id
    er, lr = e["by_outlet"][outlet], l["by_outlet"][outlet]
    if not (er.get("url") and lr.get("url")):
        log.warning("[%s] flag dropped: missing source link on a receipt", outlet)
        return None
    ftype = flag.get("type")
    if ftype not in ("contradiction", "correction", "retraction"):
        log.warning("[%s] flag dropped: invalid type %r", outlet, ftype)
        return None
    return {
        "outlet": outlet, "type": ftype,
        "subject": flag.get("subject", ""), "note": flag.get("note", ""),
        "earlier": {"cluster_id": e["cluster_id"], "date": e["date"], "claim_id": e_id,
                    "source_id": er["source_id"], "text": e["text"], "url": er["url"]},
        "later": {"cluster_id": l["cluster_id"], "date": l["date"], "claim_id": l_id,
                  "source_id": lr["source_id"], "text": l["text"], "url": lr["url"]},
        "review_status": "auto",
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def attach_accountability(thread_id: str, client: anthropic.Anthropic,
                          store: ThreadStore) -> dict:
    """Audit one thread for outlet self-contradictions. Appends new auto flags."""
    thread = store.load(thread_id)
    if not thread or len(thread.get("events", [])) < 2:
        return {"flags_added": 0}
    thread.setdefault("accountability", [])

    index = _claim_index(thread)
    timelines = _outlet_timelines(thread, index)
    existing = {(f["outlet"], f["earlier"]["claim_id"], f["later"]["claim_id"])
                for f in thread["accountability"]}
    usage: list = []
    added = 0

    for outlet, timeline in timelines.items():
        if sum(1 for c in timeline if c["claims"]) < 2:
            continue  # outlet must appear in ≥2 chapters to self-contradict
        for raw in detect_self_reversals(outlet, timeline, client, usage):
            entry = _reconstruct(raw, outlet, index)
            if not entry:
                continue
            key = (entry["outlet"], entry["earlier"]["claim_id"], entry["later"]["claim_id"])
            if key in existing:
                continue
            existing.add(key)
            entry["id"] = f"acc_{len(thread['accountability']) + 1:03d}"
            thread["accountability"].append(entry)
            store.log_review({"kind": "accountability_flag_pending", "thread_id": thread_id,
                              "flag_id": entry["id"], "outlet": outlet, "type": entry["type"],
                              "subject": entry["subject"]})
            added += 1
            log.info("[%s] flagged %s (%s) — PENDING REVIEW", thread_id, entry["id"], entry["type"])

    if added:
        thread["change_log"].append({
            "date": datetime.now(timezone.utc).date().isoformat(),
            "summary_of_change": f"{added} accountability flag(s) detected (pending review)"})
        store.save(thread)
    ti = sum(u["in"] for u in usage); to = sum(u["out"] for u in usage)
    log.info("%s: %d outlet(s) audited, %d flag(s) added | tokens %d in / %d out",
             thread_id, len(timelines), added, ti, to)
    return {"flags_added": added}


def _set_status(store: ThreadStore, thread_id: str, flag_id: str, status: str) -> None:
    thread = store.load(thread_id)
    if not thread:
        log.error("No thread %s", thread_id); return
    for f in thread.get("accountability", []):
        if f.get("id") == flag_id:
            f["review_status"] = status
            store.save(thread)
            log.info("%s / %s -> %s", thread_id, flag_id, status)
            return
    log.error("No flag %s in %s", flag_id, thread_id)


def main() -> None:
    ap = argparse.ArgumentParser(description="Accountability tracking")
    ap.add_argument("--thread-id")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list-pending", action="store_true")
    ap.add_argument("--approve", nargs=2, metavar=("THREAD_ID", "FLAG_ID"))
    ap.add_argument("--suppress", nargs=2, metavar=("THREAD_ID", "FLAG_ID"))
    args = ap.parse_args()

    store = ThreadStore(THREADS_DIR, EVENTS_DIR, ENTITIES_DIR)

    if args.list_pending:
        for t in store.all_threads():
            for f in t.get("accountability", []):
                if f.get("review_status") == "auto":
                    print(f"[PENDING] {t['thread_id']} / {f['id']}  {f['type']}  {f['outlet']}: {f['subject']}")
                    print(f"          earlier ({f['earlier']['date']}): {f['earlier']['text'][:110]}")
                    print(f"          later   ({f['later']['date']}): {f['later']['text'][:110]}")
        return
    if args.approve:
        _set_status(store, args.approve[0], args.approve[1], "approved"); return
    if args.suppress:
        _set_status(store, args.suppress[0], args.suppress[1], "suppressed"); return

    client = anthropic.Anthropic()
    if args.all:
        total = 0
        for t in store.all_threads():
            total += attach_accountability(t["thread_id"], client, store)["flags_added"]
        log.info("Audited %d threads, %d flag(s) added (all pending review)", len(store.all_threads()), total)
    elif args.thread_id:
        attach_accountability(args.thread_id, client, store)
    else:
        ap.error("give --thread-id, --all, --list-pending, --approve, or --suppress")


if __name__ == "__main__":
    main()
