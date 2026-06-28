# HANDOVER — Session 12
## News Synthesis & Credibility Engine
**Handover date:** 28 June 2026
**Prepared by:** Claude (Cowork), Session 12
**For:** Claude Code
**Owner:** G (GitHub: Ephemiral)

---

## 0. Read this first

You are picking up an active project mid-flight. This document tells you exactly where things stand and what to do next. Before writing any code:

1. Read `docs/00_MASTER_DOCUMENT.md` in full — it is the single source of truth for architecture, decisions, schema, and backlog rules.
2. Skim the latest stage doc for your current milestone: `STAGE_5_GENERATE.md` is the relevant one for pending regeneration tasks.
3. Treat `TRACKSHEET.xlsx` as the live status record — update it at the end of every session.

---

## 1. What this project is

A media product that aggregates news coverage from many outlets for a single event, surfaces what they agree on vs. dispute, and provides provenance/bias context for each source. Pipeline: `INGEST → CLUSTER → ANALYZE → ANNOTATE → GENERATE`. Front end: Next.js. Contract: per-event JSON artifact on disk (schema v0.2). Full architecture: `docs/00_MASTER_DOCUMENT.md`.

---

## 2. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0–M5 | ✅ Done | |
| M6 — Validate Phase 1 | ✅ Done | Internal audit done; external validation complete |
| M7 — Generate | ✅ Done | |
| M8 — Toggle UI | ✅ Done | |
| M9 — Validate Phase 2 | 🔄 **In progress** | 9 events processed; external validators sent questionnaire (June 4); target is 20–30 events |

**Live Vercel URL:** `https://newsroom-sand-seven.vercel.app` (auto-deploys on `git push`)
**GitHub:** `https://github.com/Ephemiral/Newsroom`

**Processed events (full pipeline, live on Vercel):**
- `evt_2026_05_31_001` — golden event (Netanyahu 70% Gaza)
- `evt_2026_06_01_009` — scale test 1 (24 articles)
- `evt_2026_06_01_068` — scale test 2 (6 articles)
- `evt_2026_06_01_065` — scale test 3 (4 articles)
- `evt_2026_06_02_044` — scale test 4 (18 articles, full spectrum) — primary validation candidate
- `evt_2026_06_02_014` — scale test 5 (12 articles, left→right)
- `evt_2026_06_02_063` — scale test 6 (5 articles, Al Jazeera vs Israel Hayom)
- `evt_2026_06_04_014` — Israel Day Parade / Smotrich controversy (17 articles)
- `evt_2026_06_04_062` — US-Iran ceasefire negotiations (23 articles)
- `evt_2026_06_04_066` — Iranian drone strike on Kuwait airport (12 articles)

There are ~2,000 raw clustered event files in `data/events/israel_middle_east/` that have not been run through the full pipeline — plenty of material for the next batch.

---

## 3. What was done in session 11 (June 4, 2026)

### Vercel deployment
- `git init` + push to GitHub (`Ephemiral/Newsroom`)
- Added `outputFileTracingIncludes` to `web/next.config.ts` so Vercel bundles `data/events/**/*`
- Connected repo to Vercel; auto-deploys on `git push`

### Generate — JSON parse robustness fix
`_parse_response()` in `pipeline/generate/generate.py` now strips markdown fences, repairs truncated output (`stop_reason == max_tokens`), and falls back to `json_repair`. Previously used bare `json.loads()` which crashed on minor model output malformation.

### B-10 / B-11 — Generate stage kind enforcement
Root problem: the generate model was labelling paragraphs `kind=contested` based on whether the *topic* sounded like a dispute, not whether *outlets* actually reported conflicting facts.

Two fixes in `pipeline/generate/generate.py`:
1. **Prompt signal:** `_build_claims_block()` now emits a `⚠ CONTESTED_BY STATUS` warning when no claim has `contested_by` populated, instructing the model not to write `contested` paragraphs.
2. **Post-generation enforcement:** `_enforce_paragraph_kinds()` reclassifies `contested` → `framing` when `claim_ids` is empty or none of the cited claims have `contested_by` populated.

### Scale test
Ran `evt_014`, `evt_062`, `evt_066` (June 4 date prefix) through the full pipeline. These were processed *before* the B-11 fix was finalized, so they need regeneration (see §4).

---

## 4. What to do next — in order

### Step 1: Regenerate the 3 events affected by B-11

These were run before the B-11 fix was fully applied:

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 -m pipeline.generate.run --event-id evt_2026_06_04_014 --force
python3 -m pipeline.generate.run --event-id evt_2026_06_04_062 --force
python3 -m pipeline.generate.run --event-id evt_2026_06_04_066 --force
```

Then push to Vercel:
```bash
git add data/events/
git commit -m "regenerate evt_014/062/066 with B-11 fix"
git push
```

### Step 2: Check for validator feedback

Validators were sent a questionnaire on June 4 with a link to `evt_2026_06_02_044` (and the others). G needs to check whether responses have arrived. If they have, review and note any issues before running more events.

### Step 3: Run more events to reach the M9 target (20–30)

There are ~2,000 raw clustered events in `data/events/israel_middle_east/`. Use the scale test script to pick and run a batch:

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate

# (Optional) Re-discover if you want fresher clusters
python3 scripts/scale_test.py --discover --beat israel_middle_east

# Run a batch of events
python3 scripts/scale_test.py --run-events evt_A,evt_B,evt_C --beat israel_middle_east
```

**Picking good events:** aim for 10–25 articles per event, spanning left→right on the source spectrum. Skip single-source clusters and mega-clusters (>50 articles). Check `data/events/israel_middle_east/` for candidates — use the clustered JSON files to see article counts before committing.

After each batch:
```bash
git add data/events/
git commit -m "add events: evt_XXX, evt_YYY, ..."
git push
```

### Step 4: Complete M9

M9 is done when:
- 20–30 events are processed and live on Vercel
- External validators have provided feedback
- No new systematic pipeline bugs have emerged

After M9, update TRACKSHEET.xlsx and determine next steps with G.

---

## 5. Pending backlog (post-M9 or lower priority)

| ID | Item | Priority |
|----|------|----------|
| B-10 remaining | `claim_ids` still often empty — consider a second-pass citation prompt | Medium |
| B-01 re-run | clm_016/024 on golden event auto-fix on next re-run | Low |
| Al Jazeera direct RSS | Proxy works; low urgency | Low |
| B-03–B-07 | See `docs/00_MASTER_DOCUMENT.md §13` | Post-M9 |
| Hebrew sources (Rotter.net) | Post-M9 | Post-M9 |

---

## 6. Infrastructure reference

### Running the pipeline
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate

# Full discover + pick events
python3 scripts/scale_test.py --discover --beat israel_middle_east
python3 scripts/scale_test.py --run-events evt_A,evt_B --beat israel_middle_east

# Regenerate report only (skip analyze/annotate)
python3 -m pipeline.generate.run --event-id evt_XXX [--force]

# Front end (local, production mode)
cd web && npm run build && npm run start
```

### Publishing to Vercel
```bash
git add data/events/
git commit -m "add events: ..."
git push
# Auto-deploys in ~1 min
```

### Scheduled tasks (already set up, no action needed)
| Task ID | Schedule | Purpose |
|---------|----------|---------|
| `newsroom-source-review` | Monday 9am | Enrich & review newly discovered domains |
| `newsroom-registry-review` | Thursday 9am | Check outlet registry for ownership changes |

---

## 7. Key file map

| Path | Purpose |
|------|---------|
| `docs/00_MASTER_DOCUMENT.md` | Full architecture, decisions, schema, backlog rules — read this |
| `TRACKSHEET.xlsx` | Live milestone status and change log — update every session |
| `pipeline/generate/generate.py` | Generate stage — B-10/B-11 fixes are here |
| `scripts/scale_test.py` | Discover + run batches of events |
| `data/events/israel_middle_east/` | All clustered event JSONs (raw and processed) |
| `data/sources/outlet_provenance.json` | Outlet registry — update when adding new sources |
| `data/suggested_sources.json` | Unknown domains from GDELT ingest |
| `web/` | Next.js front end |
| `config/` | Beat configs (sources, domain_map) — beats are config, not code |
| `.env` | API keys — never commit |

---

## 8. Working conventions

1. **Sandbox/API limitation.** Claude Code can run pipeline code locally; the Cowork sandbox cannot call the Anthropic API (SSL proxy). All pipeline runs happen on G's machine with `.venv` activated.
2. **Schema v0.2 is current.** Event JSON and report sub-object are both v0.2. If you must change the schema, bump `schema_version` and log it in the Change Log.
3. **Golden dataset is the regression fixture.** Test pipeline changes against `data/golden/event_001/` first.
4. **Ask before:** heavy new dependencies, structural repo changes, anything in `docs/00_MASTER_DOCUMENT.md §8` (fixed decisions).
5. **New sources:** add to both `sources` and `domain_map` in the beat config, and add to `data/sources/outlet_provenance.json` with `last_reviewed` set to today.
6. **Tracksheet last.** Update TRACKSHEET.xlsx (Status + Change Log row) before ending any session. Drive parentId: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX` — manual upload required (no auto-sync).
7. **Vercel auto-deploys on push.** Always commit + push after running new events.
