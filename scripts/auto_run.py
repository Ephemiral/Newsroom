"""
Autonomous pipeline runner — discover, qualify, publish. No human in the loop.

One invocation = one cycle:
  1. Ingest fresh articles (RSS + GDELT) for the beat.
  2. Cluster the last 3 days of articles.
  3. Apply qualification gates to every cluster (see QUALIFICATION GATES below).
  4. Run analyze → annotate → generate on the top qualifying clusters
     (report validation failures abort that event — nothing broken is published).
  5. Attach an openly-licensed file photo (Wikimedia Commons).
  6. git commit + push the new event files → Vercel auto-deploys.

Designed to be run every few hours by launchd (see docs). Safe to run manually.

QUALIFICATION GATES (a cluster must pass ALL to publish):
  - size:          MIN_ARTICLES–MAX_ARTICLES articles (default 4–40)
  - outlets:       ≥3 distinct outlets
  - spectrum:      ≥1 outlet left-of-center AND ≥1 right-of-center, counting
                   independent outlets only (state-aligned outlets add
                   perspective, not corroboration — B-17)
  - bodies:        ≥3 articles with a usable body text (≥400 chars)
  - cohesion:      mean pairwise cosine similarity ≥ 0.65 (no grab-bag clusters)
  - novelty:       ≥50% of the cluster's articles must be previously unpublished.
                   This blocks re-publishing the SAME articles while leaving room
                   for developing stories: new coverage of an ongoing story
                   publishes as a new event, linked to the earlier one via
                   event.related_events ("Earlier coverage" in the UI).
  - not retried:   the same article set (URL fingerprint) is attempted only once

Usage:
    python3 scripts/auto_run.py [--beat israel_middle_east] [--max-events 2]
                                [--dry-run] [--no-push]

State + logs live in data/logs/autorun/ (gitignored is fine; state is local).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("auto_run")

# ── Tunables ──────────────────────────────────────────────────────────────────
MIN_ARTICLES = 4
MAX_ARTICLES = 40
MIN_OUTLETS = 3
MIN_BODY_CHARS = 400
MIN_BODIES = 3
COHESION_FLOOR = 0.65
MIN_NEW_COVERAGE = 0.50     # ≥ this fraction of a cluster's URLs must be previously unpublished
INGEST_MAX_AGE_DAYS = 3
DEFAULT_MAX_EVENTS = 2      # per cycle — cost control

LEFT_TIERS = {"left", "center-left"}
RIGHT_TIERS = {"right", "center-right"}


class SystemicError(RuntimeError):
    """A whole-cycle failure (bad API key, etc.) — abort and alert loudly.
    Distinct from a routine single-event validation rejection, which is silent."""


def _is_systemic_api_error(e: Exception) -> bool:
    """True for account-level failures that will hit EVERY beat identically —
    a bad/blocked key, or an exhausted credit balance. These abort the whole
    cycle immediately instead of erroring once per beat."""
    s = str(e).lower()
    return ("authentication_error" in s or "invalid x-api-key" in s
            or "401" in s or "permission_error" in s
            or "credit balance" in s or "billing" in s)

LOG_DIR = ROOT / "data" / "logs" / "autorun"
# State is git-tracked (and committed by publish cycles) so that stateless
# environments — the GitHub Actions runner — share the attempt ledger and never
# re-burn tokens on an article set that already failed.
STATE_PATH = ROOT / "data" / "autorun" / "state.json"
LOCK_PATH = LOG_DIR / "autorun.lock"
LOCK_STALE_SECONDS = 3 * 3600


# ── Lock ──────────────────────────────────────────────────────────────────────

def acquire_lock() -> bool:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        age = time.time() - LOCK_PATH.stat().st_mtime
        if age < LOCK_STALE_SECONDS:
            log.warning("Another auto_run appears active (lock age %.0fs) — exiting.", age)
            return False
        log.warning("Stale lock (%.0fs old) — overriding.", age)
    LOCK_PATH.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


# ── State (article-set fingerprints already attempted) ───────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            log.warning("Could not parse state file — starting fresh.")
    return {"attempted": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def fingerprint(urls: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(urls)).encode()).hexdigest()[:16]


# ── Published-event index (for novelty gate) ──────────────────────────────────

def published_events(events_root: Path) -> list[dict]:
    """id/title/URL-set of every already-published (analyzed) event, across ALL
    beats — the same story must not re-publish, in any theatre."""
    events = []
    for path in events_root.glob("*/*_analyzed.json"):
        try:
            data = json.loads(path.read_text())
            urls = {s.get("url", "") for s in data.get("sources", []) if s.get("url")}
            if urls:
                events.append({
                    "event_id": data.get("event", {}).get("cluster_id", path.stem.replace("_analyzed", "")),
                    "title": data.get("event", {}).get("title", ""),
                    "urls": urls,
                })
        except Exception:
            continue
    return events


# ── Cluster qualification ─────────────────────────────────────────────────────

def evaluate_cluster(cluster: dict, article_map: dict, sim, id_to_idx: dict,
                     published: list[set[str]], state: dict) -> tuple[bool, str, dict]:
    """Apply all gates. Returns (qualified, reason_if_not, stats)."""
    import numpy as np

    arts = [article_map[a] for a in cluster["article_ids"] if a in article_map]
    urls = [a.url for a in arts]
    outlets = {a.outlet for a in arts}
    tiers = {a.bias_rating for a in arts if a.bias_rating}
    # B-17: state-aligned outlets add perspective, not corroboration — the
    # cross-spectrum gate must be satisfied by independent outlets alone.
    indep_tiers = {a.bias_rating for a in arts
                   if a.bias_rating and not getattr(a, "state_alignment", None)}
    bodies = sum(1 for a in arts if len(a.body_text or "") >= MIN_BODY_CHARS)

    stats = {
        "size": len(arts),
        "outlets": sorted(outlets),
        "bias_tiers": sorted(tiers),
        "usable_bodies": bodies,
        "fingerprint": fingerprint(urls),
    }

    if not (MIN_ARTICLES <= len(arts) <= MAX_ARTICLES):
        return False, f"size {len(arts)} outside [{MIN_ARTICLES},{MAX_ARTICLES}]", stats
    if len(outlets) < MIN_OUTLETS:
        return False, f"only {len(outlets)} distinct outlets", stats
    if not (indep_tiers & LEFT_TIERS and indep_tiers & RIGHT_TIERS):
        return False, f"no cross-spectrum spread among independent outlets (tiers: {sorted(indep_tiers)})", stats
    if bodies < MIN_BODIES:
        return False, f"only {bodies} articles with usable body text", stats

    # Cohesion (mean pairwise similarity)
    idxs = [id_to_idx[a.article_id] for a in arts if a.article_id in id_to_idx]
    if len(idxs) >= 2:
        pair_sims = [sim[i, j] for k, i in enumerate(idxs) for j in idxs[k + 1:]]
        mean_sim = float(np.mean(pair_sims))
        stats["cohesion"] = round(mean_sim, 3)
        if mean_sim < COHESION_FLOOR:
            return False, f"low cohesion {mean_sim:.3f} (grab-bag)", stats

    # Novelty vs. already-published events. Developing stories are welcome:
    # what's blocked is re-publishing the SAME articles, not new coverage of an
    # ongoing story. A cluster qualifies if ≥50% of its articles are new
    # (unseen URLs); prior events sharing articles are recorded as related —
    # published as a development, not rejected as a duplicate.
    url_set = set(urls)
    all_published_urls = set().union(*(p["urls"] for p in published)) if published else set()
    new_frac = len(url_set - all_published_urls) / max(len(url_set), 1)
    stats["new_coverage"] = round(new_frac, 2)
    related = [
        {"cluster_id": p["event_id"], "title": p["title"]}
        for p in published
        if len(url_set & p["urls"]) >= 2 or len(url_set & p["urls"]) / max(len(url_set), 1) > 0.15
    ]
    if related:
        stats["related_events"] = related
    if new_frac < MIN_NEW_COVERAGE:
        return False, f"only {new_frac:.0%} new coverage — same articles already published", stats

    # Already attempted this exact article set?
    if stats["fingerprint"] in state["attempted"]:
        prev = state["attempted"][stats["fingerprint"]]
        return False, f"already attempted on {prev.get('at', '?')} ({prev.get('outcome')})", stats

    return True, "", stats


def unique_event_id(out_dir: Path, beat: str) -> str:
    """
    Beat-namespaced, globally-unique event ID: evt_<date>_<beat>_<NNN>.

    The beat is part of the ID and uniqueness is checked across ALL beat
    directories, not just this one — otherwise two beats independently mint
    evt_<date>_auto_001 and the frontend's getEvent(id) can only resolve one of
    them, shadowing the rest (the cross-beat collision bug).
    """
    date_part = datetime.now(timezone.utc).strftime("%Y_%m_%d")
    events_root = out_dir.parent  # data/events/
    existing = {p.stem.replace("_analyzed", "") for p in events_root.glob(f"*/evt_{date_part}_*.json")}
    n = 1
    while f"evt_{date_part}_{beat}_{n:03d}" in existing:
        n += 1
    return f"evt_{date_part}_{beat}_{n:03d}"


# ── Git publish ───────────────────────────────────────────────────────────────

def git_publish(paths: list[Path], titles: list[str], no_push: bool) -> str:
    rel = [str(p.relative_to(ROOT)) for p in paths]
    subprocess.run(["git", "add", *rel], cwd=ROOT, check=True)
    if titles:
        title_line = "; ".join(t[:60] for t in titles)
        msg = f"auto: publish {len(titles)} event(s) — {title_line}\n\nAutomated publish by scripts/auto_run.py."
    else:
        msg = "auto: record failed publish attempt(s) in state ledger\n\nAutomated commit by scripts/auto_run.py."
    subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
    if no_push:
        return "committed (push skipped)"
    push = subprocess.run(["git", "push"], cwd=ROOT, capture_output=True, text=True)
    if push.returncode != 0:
        log.error("git push failed: %s", push.stderr.strip()[:500])
        return "committed, PUSH FAILED (will deploy on next successful push)"
    return "pushed"


# ── Main cycle ────────────────────────────────────────────────────────────────

def run_cycle(beat: str, max_events: int, dry_run: bool, no_push: bool) -> dict:
    from pipeline.ingest.rss import ingest_beat
    from pipeline.ingest.gdelt import ingest_gdelt
    from pipeline.ingest.store import ArticleStore
    from pipeline.cluster.embed import embed_articles
    from pipeline.cluster.group import auto_cluster

    run_log: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "beat": beat,
        "dry_run": dry_run,
        "published": [],
        "rejected": [],            # clusters rejected by the qualification gates
        "rejected_pipeline": [],   # selected but failed report validation (routine)
        "errors": [],              # systemic/transient failures (API, crash) — alert-worthy
    }

    config_path = ROOT / "config" / "beats" / f"{beat}.json"
    config = json.loads(config_path.read_text())
    store = ArticleStore(base_dir=str(ROOT / "data" / "ingested"), beat=beat)
    out_dir = ROOT / "data" / "events" / beat
    out_dir.mkdir(parents=True, exist_ok=True)  # first run of a new beat has no dir yet

    # ── 1. Ingest ─────────────────────────────────────────────────────────
    log.info("Ingesting RSS for beat %s…", beat)
    saved = sum(1 for a in ingest_beat(config, fetch_body=True) if store.save(a))
    if config.get("gdelt", {}).get("enabled"):
        log.info("Ingesting GDELT…")
        saved += sum(1 for a in ingest_gdelt(config, fetch_body=True) if store.save(a))
    run_log["new_articles"] = saved
    log.info("Ingest done — %d new articles.", saved)

    # ── 2. Cluster ────────────────────────────────────────────────────────
    articles = store.load_all(max_age_days=INGEST_MAX_AGE_DAYS)
    if len(articles) < MIN_ARTICLES:
        run_log["outcome"] = f"only {len(articles)} recent articles — nothing to do"
        return run_log
    log.info("Clustering %d recent articles…", len(articles))
    embeddings, ids = embed_articles(articles)
    sim = embeddings @ embeddings.T
    id_to_idx = {aid: i for i, aid in enumerate(ids)}
    pub_dates = [getattr(a, "published_at", "") or "" for a in articles]
    clusters = auto_cluster(embeddings, ids, beat=beat, pub_dates=pub_dates)
    run_log["clusters"] = len(clusters)

    # ── 3. Qualify ────────────────────────────────────────────────────────
    article_map = {a.article_id: a for a in articles}
    published = published_events(ROOT / "data" / "events")
    state = load_state()

    qualified = []
    for c in sorted(clusters, key=lambda x: -x["size"]):
        ok, reason, stats = evaluate_cluster(c, article_map, sim, id_to_idx, published, state)
        if ok:
            qualified.append((c, stats))
        elif stats["size"] >= MIN_ARTICLES:
            # Log only non-trivial rejections to keep the run log readable
            run_log["rejected"].append({"size": stats["size"], "reason": reason})

    # Rank: widest spectrum spread first, then size
    qualified.sort(key=lambda cs: (-len(cs[1]["bias_tiers"]), -cs[1]["size"]))
    selected = qualified[:max_events]
    log.info("%d cluster(s) qualified; selecting %d.", len(qualified), len(selected))

    if dry_run:
        for c, stats in selected:
            log.info("[dry-run] would publish: %s", json.dumps(stats))
        run_log["outcome"] = f"dry-run — {len(qualified)} qualified"
        return run_log

    if not selected:
        run_log["outcome"] = "no qualifying clusters this cycle"
        return run_log

    # ── 4–6. Publish each selected cluster ────────────────────────────────
    import anthropic
    from pipeline.run_event import run_pipeline_for_event
    from pipeline.images.run import attach_image

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        run_log["outcome"] = "ERROR: ANTHROPIC_API_KEY not set"
        return run_log
    client = anthropic.Anthropic(api_key=api_key)

    to_commit: list[Path] = []
    titles: list[str] = []

    for cluster, stats in selected:
        event_id = unique_event_id(out_dir, beat)
        cluster["cluster_id"] = event_id
        cluster_path = out_dir / f"{event_id}.json"
        cluster_path.write_text(json.dumps(cluster, indent=2, ensure_ascii=False))

        log.info("Running pipeline for %s (%d articles, tiers %s)…",
                 event_id, stats["size"], stats["bias_tiers"])
        attempt = {"at": datetime.now(timezone.utc).isoformat(), "event_id": event_id}
        error_exc = None
        try:
            ok = run_pipeline_for_event(event_id, beat, client, force_generate=False)
        except Exception as e:
            log.exception("Pipeline crashed for %s", event_id)
            ok = False
            error_exc = e

        analyzed_path = out_dir / f"{event_id}_analyzed.json"
        if ok:
            # Link developments of an ongoing story to their earlier events
            if stats.get("related_events"):
                data = json.loads(analyzed_path.read_text())
                data["event"]["related_events"] = stats["related_events"]
                analyzed_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            try:
                attach_image(analyzed_path, client)
            except Exception:
                log.exception("Image stage failed for %s (publishing without image)", event_id)
            data = json.loads(analyzed_path.read_text())
            titles.append(data["event"].get("title", event_id))
            to_commit += [cluster_path, analyzed_path]
            attempt["outcome"] = "published"
            run_log["published"].append({"event_id": event_id, "title": titles[-1], **stats})
            state["attempted"][stats["fingerprint"]] = attempt
            save_state(state)
        else:
            # Never leave half-processed artifacts for the site to pick up
            for p in (analyzed_path, cluster_path):
                if p.exists():
                    p.unlink()

            if error_exc is not None:
                # A raised exception is a SYSTEMIC/transient problem (API auth, rate
                # limit, network, a code bug) — NOT the article set's fault. Do NOT
                # record it in the ledger, so it's retried next cycle once fixed.
                run_log.setdefault("errors", []).append(
                    {"event_id": event_id, "error": str(error_exc)[:300]})
                if _is_systemic_api_error(error_exc):
                    # Every beat will hit the same wall (bad key or no credits) —
                    # abort now instead of burning an hour ingesting the rest.
                    msg = str(error_exc)
                    if "credit balance" in msg.lower() or "billing" in msg.lower():
                        raise SystemicError(
                            "Anthropic API balance exhausted — top up at "
                            "console.anthropic.com → Plans & Billing. " + msg[:120])
                    raise SystemicError(
                        "Anthropic API authentication failed — check the "
                        "ANTHROPIC_API_KEY secret. " + msg[:120])
                # Non-auth exception: skip this event, keep going.
            else:
                # A clean False is a routine validation rejection (e.g. the report
                # failed ID validation). The article set genuinely didn't qualify —
                # record it so we don't reprocess the same junk every cycle. This
                # is normal operation, NOT a workflow failure.
                attempt["outcome"] = "rejected"
                run_log["rejected_pipeline"].append({"event_id": event_id, **stats})
                state["attempted"][stats["fingerprint"]] = attempt
                save_state(state)

    # ── Git ───────────────────────────────────────────────────────────────
    # The attempt ledger travels with the repo (see STATE_PATH comment); commit
    # it even on publish-free cycles that recorded failed attempts.
    if STATE_PATH.exists():
        to_commit.append(STATE_PATH)
    if titles or run_log["rejected_pipeline"]:
        try:
            run_log["git"] = git_publish(to_commit, titles, no_push)
        except Exception as e:
            log.exception("git publish failed")
            run_log["git"] = f"ERROR: {e}"
    run_log["outcome"] = (
        f"published {len(titles)}, rejected {len(run_log['rejected_pipeline'])}, "
        f"errors {len(run_log['errors'])}")
    return run_log


def notify_failure(summary: str) -> None:
    """Local alerting: macOS notification when a cycle goes wrong (launchd mode).
    In GitHub Actions the workflow's failure-issue step covers this instead."""
    if sys.platform != "darwin" or os.environ.get("GITHUB_ACTIONS"):
        return
    try:
        safe = summary.replace('"', "'")[:200]
        subprocess.run([
            "osascript", "-e",
            f'display notification "{safe}" with title "Newsroom autorun failed" sound name "Basso"',
        ], check=False, timeout=10)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Autonomous discover→qualify→publish cycle")
    parser.add_argument("--beats", "--beat", dest="beats", default="israel_middle_east",
                        help="Comma-separated beat names, processed in order")
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS,
                        help="Max events published per beat per cycle")
    parser.add_argument("--dry-run", action="store_true", help="Qualify only; no LLM calls, no publishing")
    parser.add_argument("--no-push", action="store_true", help="Commit but do not push")
    args = parser.parse_args()
    beats = [b.strip() for b in args.beats.split(",") if b.strip()]

    if not acquire_lock():
        sys.exit(0)

    # Only SYSTEMIC problems escalate to a workflow failure + alert. A cluster
    # that fails the qualification gates or report validation is normal operation
    # and must NOT turn the run red or open an issue (that would cry wolf every
    # cycle). Systemic = a crash, an API/auth error, or a git push failure.
    failures = []
    systemic_abort = False
    try:
        for beat in beats:
            if systemic_abort:
                break  # a bad key affects every beat — don't ingest the rest
            run_log = {}
            try:
                run_log = run_cycle(beat, args.max_events, args.dry_run, args.no_push)
            except SystemicError as e:
                log.error("[%s] systemic abort: %s", beat, e)
                run_log = {"beat": beat, "outcome": f"SYSTEMIC: {e}",
                           "started_at": datetime.now(timezone.utc).isoformat()}
                systemic_abort = True
            except Exception as e:
                log.exception("auto_run cycle crashed for beat %s", beat)
                run_log = {"beat": beat, "outcome": f"CRASH: {e}",
                           "started_at": datetime.now(timezone.utc).isoformat()}
            run_log["finished_at"] = datetime.now(timezone.utc).isoformat()
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            (LOG_DIR / f"run_{stamp}_{beat}.json").write_text(
                json.dumps(run_log, indent=2, ensure_ascii=False))
            log.info("[%s] Cycle finished: %s", beat, run_log.get("outcome"))
            outcome = str(run_log.get("outcome", ""))
            git_status = str(run_log.get("git", ""))
            if ("CRASH" in outcome or "SYSTEMIC" in outcome or run_log.get("errors")
                    or "FAILED" in git_status or "ERROR" in git_status):
                failures.append(f"{beat}: {outcome} | git: {git_status or 'n/a'}")
    finally:
        if failures:
            notify_failure("; ".join(failures))
        release_lock()

    if failures:
        sys.exit(1)  # non-zero exit → CI failure step fires


if __name__ == "__main__":
    main()
