# HANDOVER — Session 6
## News Synthesis & Credibility Engine
**Handover date:** 1 June 2026
**Prepared by:** Claude (Cowork), Session 5
**For:** Claude (Cowork), Session 6
**Owner:** G (GitHub: Ephemiral)

---

## 1. What is this project (30-second version)

A media product that aggregates news coverage of a single event from many outlets, extracts what they agree on vs. dispute, surfaces source provenance, and presents a transparent multi-perspectival report. Pipeline: `INGEST → CLUSTER → ANALYZE → ANNOTATE → GENERATE`. Front end: Next.js. Contract: per-event JSON on disk. Full architecture: `docs/00_MASTER_DOCUMENT.md`.

---

## 2. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 — Golden dataset | ✅ Done | 10 articles, `data/golden/event_001/` |
| M1 — Ingest | ✅ Done | RSS + dedup + storage |
| M2 — Cluster | ✅ Done | Embeddings + threshold clustering |
| M3 — Analyze | ✅ Done | 32 claims; B-01/B-02 now enforced |
| M4 — Annotate | ✅ Done | Ownership + author background |
| M5 — Phase-1 page | ✅ Done | Next.js app in `web/` |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending |
| M7 — Generate | ✅ Done | 11 paragraphs; prompt improvements applied |
| M8 — Toggle UI | ✅ Done | ReportView with sidebar bar + transparency toggle |
| M9 — Validate Phase 2 | 🔄 **In progress** | **← CURRENT TASK** — scale test ready to run |

---

## 3. What changed this session

### B-01 + B-02: enforcement in `pipeline/analyze/reconcile.py`

**Before:** B-01 and B-02 were warnings only — they printed to stderr but never touched the data.

**After:** A new `enforce_classification_rules()` function runs *before* the warning pass and mutates the result in place:

- **B-01:** Any claim classified `"agreed"` whose `supported_by_articles` sources don't span left+center or left+right or center+right is **auto-reclassified to `"corroborated"`**. Logged to stderr with `✔ Classification corrections applied`.
- **B-02:** If a source appears in both `supported_by_articles` and `contested_by_articles`, it is **removed from `contested_by_articles`**. Logged the same way.

The B-03 rationale check remains a warning (heuristic, not auto-fixable).

**Effect when golden event is re-run:** clm_015, clm_016, clm_024 will all be correctly classified without manual intervention. B-07 is resolved automatically.

### `pipeline/analyze/run.py`: live article lookup fix

`load_articles_cluster()` now searches in this order for each article ID:
1. `data/golden/event_001/articles/<id>.json` (golden)
2. `data/ingested/<beat>/<id>.json` ← **new** (live runs)
3. `data/events/<beat>/articles/<id>.json` (legacy path)

Without this fix, the scale test would silently skip all articles for any live-ingested event.

### `scripts/scale_test.py`: full scale test runner

New two-phase script at `scripts/scale_test.py`:

```bash
# Phase 1 — discover events
python3 scripts/scale_test.py --discover --beat israel_middle_east [--max-per-source N]

# Phase 2 — run pipeline for chosen events
python3 scripts/scale_test.py --run-events evt_A,evt_B,evt_C --beat israel_middle_east
```

**Phase 1** runs ingest + cluster and prints a formatted list of discovered events with outlet names and bias ratings, so G can assess diversity before committing API budget to the full pipeline.

**Phase 2** runs analyze → annotate → generate for each listed event in sequence. Prints `localhost:3000/event/<id>` URLs at the end for immediate front-end review.

---

## 4. M9 — next steps (what G needs to do)

### Step 1: Run the scale test locally

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate

# Discover events
python3 scripts/scale_test.py --discover --beat israel_middle_east

# Review the list. Pick 2–3 clusters with:
#   - ≥4 articles
#   - outlets spanning left + center + right (or close to it)
#   - different topics from the golden event (proves generalization)

# Run the pipeline on chosen events
python3 scripts/scale_test.py --run-events evt_XXXX,evt_YYYY --beat israel_middle_east
```

### Step 2: Check each event in the UI

```bash
cd web && npm run dev   # → http://localhost:3000
```
Open each URL printed by the scale test. Check:
- Claims section renders without errors (all 4 groups: Agreed/Corroborated/Contested/Single-source)
- Report section renders with sidebar bar and toggle
- No broken source IDs or empty sections that look wrong

### Step 3: Re-run the golden event with B-01 fixes (optional but recommended)

```bash
python3 -m pipeline.analyze.run --source golden
python3 -m pipeline.annotate.run --source golden
python3 -m pipeline.generate.run --force
```

Verify clm_016 and clm_024 are now `corroborated` in the UI (not `agreed`).

### Step 4: External validation (when ready)

Same three-profile test as M6 — pro-Palestinian / pro-Israel / centrist — focused on the *report* specifically:
- Does the narrative feel balanced?
- Are contested paragraphs presented fairly?
- Did expanding sources change how you read any paragraph?

---

## 5. Working conventions (carry forward)

1. **Tracksheet first and last.** Mark milestones, log changes, upload to Drive. Parent folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
2. **Sandbox can't call Anthropic API.** Write pipeline code here; G runs locally with `.venv` activated.
3. **Golden dataset is the fixture.** Test pipeline changes against it before touching live feeds.
4. **Schema v0.2 is current.** Bump version + log in tracksheet if structure changes.
5. **UI design decisions** in `docs/00_MASTER_DOCUMENT.md §12` — consult before changing colors/layout.
6. **Backlog** in `docs/00_MASTER_DOCUMENT.md §13` — B-01 and B-02 are now enforced; B-03 through B-07 remain.
7. **Ask before:** heavy new dependencies, structural repo changes, anything in §8 (fixed decisions).
