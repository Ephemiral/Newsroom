# HANDOVER — Session 17
## News Synthesis & Credibility Engine ("Critiqal")
**Handover date:** 8 July 2026
**Prepared by:** Claude Code, Session 17
**Owner:** G (GitHub: Ephemiral)

---

## 0. Read this first

The product is **live and fully autonomous** (GitHub Actions cron every 12h, 4 beats, auto-publish to Vercel). This was a **big session**: a frontend design pass, a long-overdue branch merge, and **all of Phase 3** (three new reader-facing features) shipped and live.

- **Live site:** https://newsroom-sand-seven.vercel.app
- **Repo:** https://github.com/Ephemiral/Newsroom
- **Source of truth:** `docs/00_MASTER_DOCUMENT.md` (updated this session — §15c/d/e are the new features; header + §9 + §10 refreshed).
- **Also read** `docs/HANDOVER_SESSION_16.md` for the credit/cron history and `docs/HANDOVER_SESSION_15.md` for the Actions migration + file map.
- **Schema:** events **v0.6** (`pipeline/schema.py`), entity store **v0.1**, thread schema **v0.2**.

At session start: `git log --oneline | grep auto:` for cron activity, and **run `python3 -m pipeline.accountability.run --list-pending`** — the accountability review queue is the one standing human task (see §4).

---

## 1. What changed this session (17)

Four distinct workstreams, all committed and pushed to `main` (Vercel auto-deploys):

### A. Frontend design pass (G's Claude-design revisions) — `c1a0e60`
- Homepage: tagline → *"Think critically. Read Critiqal."* (italic 18px semibold); beat nav centered (`space-between`); **About tab** added; content max-width 760→960 (`padding 0 48px`); removed agreed/contested counts from feed meta rows.
- Event page: max-width 720→960; top padding 44→24; header margin 32→20.
- Report: raised cap on the lede's first letter (`.report-lede::first-letter`, Spectral 3.6em, baseline-aligned).

### B. Merged the semantic-dedup branch (B-13) — `44d5869`
`task_4517860d` (session 15) was **complete but never merged** — so the duplicate-story fix wasn't actually live. Merged `claude/ecstatic-dubinsky-bd166c` into main, hand-reconciling a `page.tsx` conflict with pass (A). Now live: publish-time **semantic dedup** in `auto_run.py` (centroid vs. recent events' title+summary; ≥0.93 reject, ≥0.85 fold into `related_events`) + homepage **`getEventGroups()`** collapsing `related_events` chains into one "Developing story" card.

### C. Phase 3 — three new features (the bulk of the session)
Design-first throughout (stage doc → G review/approval → build), per G's Phase 3 command.

- **M10 — Entity Cards** (`STAGE_7`, `pipeline/entities/`, schema v0.5) — `6c30f67`, fixes `9ffe0ea`. See §3.1.
- **M11 — Story Threading** (`STAGE_8`, `pipeline/threading/`, schema v0.6) — `2361930`. See §3.2.
- **M12 — Accountability Tracking** (`STAGE_9`, `pipeline/accountability/`, thread schema v0.2) — `17bfb04`. See §3.3.

### D. Entity + thread backfill
Entitized all 30 existing events (they predated M10), then threaded the last 45 days → **3 threads** seeded. The accountability audit of those threads produced **0 flags** (correct — no false positives).

---

## 2. Current live state

- **Events:** Middle East 20, Europe 4, Asia 6, Americas 0 = **30**. (Cron published several mid-session — origin ran ahead of local; `git pull` if you see this.)
- **Entity records:** **157** in `data/entities/` (every event now has entities).
- **Threads:** **3** in `data/threads/` — "Death and funeral of Ali Khamenei" (folds the old duplicate funeral cards into one arc), "NATO Ankara Summit and Ukraine Air Defense Requests", "US–Iran Strait of Hormuz negotiations and shipping dispute".
- **Accountability flags:** 0 live (queue empty).
- Scheduler unchanged: GitHub Actions only, every 12h. launchd stays disabled.

---

## 3. Phase 3 features — how each works

### 3.1 Entity Cards (M10) — `pipeline/entities/`
Clickable people/orgs/parties/tech/locations in the report (transparency mode) open a side-panel card. **Persistent + accumulating**: `data/entities/{id}.json`, resolved by alias index; the same entity enriches across events instead of duplicating.
- **Grounded, never invented:** Wikidata/Wikipedia (free, cited on every field) + P18 image (Commons, license-gated). The LLM never asserts biographical facts from training knowledge.
- **Confidence tiers** `verified|reported|disputed|allegation`, never blended in the UI.
- **Safety is machine-enforced** (no human bottleneck): a fact without a source link AND tier label is dropped; **person allegations excluded in v1** (G's decision) and require `attributed_to`; person grounding passes an **LLM namesake guard** (added after a real mis-ground of "Ali Shaath"), audit-logged in `data/entities/review_log.jsonl`.
- CLI: `python3 -m pipeline.entities.run --event-id X | --all-missing [--force]`. Cost ~$0.01/event.

### 3.2 Story Threading (M11) — `pipeline/threading/`
Developing stories linked into a persistent, named **thread** on a cross-beat **"Threads"** tab (`/threads` list, `/thread/[id]` arc newest-chapter-first with "what's new" summaries). `event.thread_id` (schema 0.6) + `data/threads/`.
- **Matching** (`match.py`): IDF-weighted major-entity overlap (0.6) + `claim_group` theme (0.15) + title/summary embedding (0.25), 30-day rolling window; **requires ≥1 shared *specific* (non-ubiquitous) entity** so events don't thread on "Israel"/"US" alone (the guard against a B-12-style blob). Matching is free (reuses stored data); only titles/chapters cost Haiku (~$0.005–0.01/threaded event).
- **A thread only exists at ≥2 events** (G's rule): a lone report is never shown as "developing".
- **Titles** are AI-generated, **neutral, human-overridable** (`title_source: auto|manual`). Prefers under-merging; never auto-merges two established threads (logged).

### 3.3 Accountability Tracking (M12) — `pipeline/accountability/`
Across a thread, flags where an outlet's **own** reporting contradicted/corrected/retracted itself on the same fact — shown side by side in parallel language ("How the reporting changed" on the thread page). Never "biased".
- **The load-bearing guard:** a developing story *changing* is NOT self-contradiction. Detection (**Sonnet**, `claude-sonnet-4-6`) flags only same-fact self-reversal and returns nothing when unsure.
- **Receipts reconstructed from real data**, not the model's echo; flags dropped unless both claims resolve to the same outlet with links.
- **Review-gated (G's decision):** flags written `review_status: "auto"`; the frontend renders **only `"approved"`**. Approve/suppress via CLI (see §5). Generation autonomous, **display human-gated**.

---

## 4. Open items / next work

| Item | Priority | Notes |
|---|---|---|
| **Accountability review queue** | **Standing task** | `python3 -m pipeline.accountability.run --list-pending`; `--approve`/`--suppress <thread> <flag>`. Nothing shows on the site until approved. Empty now; will populate as threads grow. |
| **Threshold calibration** | Medium | Threading `THREAD_MATCH_FLOOR` (0.45) and the entity ubiquity cap were set on ~30 events; recalibrate from logged scores once more data accrues. Same for accountability's behavior at volume. |
| **Unify homepage grouping with threads** | Medium | `getEventGroups()` (related_events collapse) and threads now coexist. STAGE_8 §Migration says thread_id should become the single homepage grouping. Deferred to keep the build low-risk — a clean follow-up. |
| **Person cards ship-dark** | Low/context | The person-card review gate was *offered* but G chose machine-enforced safety instead; if a person card ever looks wrong, `review_status` + the audit log make it traceable. |
| **Anthropic credits / spend limit** | Medium | Credits were topped up this session. Still no monthly limit set — recommend one (S16 item). |
| **Americas beat empty** | Low/expected | Unchanged; nothing has cleared the gates. |
| **Stale root-level doc copies** | Low | `/00_MASTER_DOCUMENT.md`, `/HANDOVER*.md`, `/STAGE_*.md` at repo root are **old duplicates**; the live docs are in `docs/`. Worth deleting the root copies to avoid confusion. |

---

## 5. Operating reference (new CLIs this session)

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom && source .venv/bin/activate

# Entities
python3 -m pipeline.entities.run --event-id EVT [--force]      # one event
python3 -m pipeline.entities.run --all-missing                  # backfill

# Threading
python3 -m pipeline.threading.run --event-id EVT               # thread one event
python3 -m pipeline.threading.run --backfill-days 45 [--reset] # seed threads
python3 -m pipeline.threading.run --list                        # list threads

# Accountability (review queue)
python3 -m pipeline.accountability.run --all                    # audit all threads
python3 -m pipeline.accountability.run --list-pending           # review queue
python3 -m pipeline.accountability.run --approve THREAD FLAG    # publish a flag
python3 -m pipeline.accountability.run --suppress THREAD FLAG   # hide a flag

# Unchanged
python3 scripts/auto_run.py --beats israel_middle_east,europe,americas,asia
cd web && npm run dev     # G usually has :3000 up — note the preview tool can't attach while it is
```

The full autonomous cycle now runs: ingest → cluster → qualify → analyze/annotate/generate → **entities → threading → accountability** → image → commit/push. Each new stage is additive and **non-blocking** (a failure never stops the event publishing).

---

## 6. Conventions (carry forward)

Carry everything from S15 §6 / S16, plus new this session:
- **Grounding, never invention.** Entity/accountability claims about real people cite a checkable source or don't ship. The model never asserts biography or self-contradiction from its own knowledge.
- **Neutral, parallel, overridable.** Thread titles and accountability notes use parallel language, no side's framing, no motive/characterization; AI titles are human-overridable.
- **Prefer under-merging.** Entities, threads, and accountability all bias toward the safe failure — a duplicate/missed link/missed flag over a wrong merge or a false accusation.
- **Review-gated display for the riskiest output.** Accountability flags generate autonomously but only show once a human approves.
- **A thread is ≥2 events; entities are the threading signal** — a new event must be entitized before it can thread.
- **Schema discipline:** bump `EVENT_SCHEMA_VERSION` / `THREAD_SCHEMA_VERSION` / `ENTITY_SCHEMA_VERSION` + log every change; all Phase 3 changes were additive (old files still render).
- **Verification reality:** G's dev server holds `:3000`, so the preview/screenshot tool can't attach — this session verified via curl + data inspection + `tsc`. Mention this limitation honestly rather than claiming a screenshot.
