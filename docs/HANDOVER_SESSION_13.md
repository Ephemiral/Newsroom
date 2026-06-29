# HANDOVER — Session 13
## News Synthesis & Credibility Engine
**Handover date:** 29 June 2026
**Prepared by:** Claude Code, Session 13
**For:** Next session (Claude Code or Cowork)
**Owner:** G (GitHub: Ephemiral)

---

## 0. Read this first

1. Read `docs/00_MASTER_DOCUMENT.md` in full if you haven't — single source of truth for architecture, decisions, schema, backlog rules. Backlog item **B-12** (new this session) is the most actionable open item.
2. `TRACKSHEET.xlsx` is the live status record — both the Milestones tab and Change Log were updated at the end of this session.
3. This session also cleaned up a month of uncommitted session-11 work that was sitting in the working tree — see §2.

---

## 1. What this project is

A media product that aggregates news coverage from many outlets for a single event, surfaces what they agree on vs. dispute, and provides provenance/bias context for each source. Pipeline: `INGEST → CLUSTER → ANALYZE → ANNOTATE → GENERATE`. Front end: Next.js. Contract: per-event JSON artifact on disk (schema v0.2). Full architecture: `docs/00_MASTER_DOCUMENT.md`.

---

## 2. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0–M5 | ✅ Done | |
| M6 — Validate Phase 1 | ✅ Done | |
| M7 — Generate | ✅ Done | |
| M8 — Toggle UI | ✅ Done | |
| M9 — Validate Phase 2 | 🔄 **In progress** | **15 of 20–30 target events processed.** No external validator feedback yet (questionnaire sent June 4). |

**Live Vercel URL:** `https://newsroom-sand-seven.vercel.app` (auto-deploys on `git push`)
**GitHub:** `https://github.com/Ephemiral/Newsroom`

**Processed events (full pipeline, live on Vercel) — 15 total:**
- `evt_2026_05_31_001` — golden event (Netanyahu 70% Gaza)
- `evt_2026_06_01_009`, `evt_2026_06_01_065`, `evt_2026_06_01_068` — scale tests 1–3
- `evt_2026_06_02_044`, `evt_2026_06_02_014`, `evt_2026_06_02_063` — scale tests 4–6
- `evt_2026_06_04_014` — Israel Day Parade / Smotrich (regenerated with B-11 fix)
- `evt_2026_06_04_062` — US-Iran ceasefire negotiations (regenerated with B-11 fix)
- `evt_2026_06_04_066` — Iranian drone strike on Kuwait airport (regenerated with B-11 fix)
- `evt_2026_06_04_017` — UN adds Israel/Russia to conflict sexual-violence blacklist
- `evt_2026_06_01_023` — US-Iran ceasefire extension framework
- `evt_2026_06_01_117` — Israel strikes on Beirut/south Lebanon
- `evt_2026_06_04_023` — Knesset dissolution bill / AG reform
- `evt_2026_06_28_040` — US strikes Iran after cargo ship attack (Strait of Hormuz)

There are now **~3,500 raw clustered event files** in `data/events/israel_middle_east/` (the original ~2,000 plus a fresh discover run from this session) — but see §4 for why most of them aren't usable as-is.

---

## 3. What was done in this session (29 June 2026)

### 3a. Recovered a month of uncommitted work
The working tree had **972 uncommitted files** from session 11 (28 June per file timestamps, but never committed): `TRACKSHEET.xlsx`, `docs/00_MASTER_DOCUMENT.md`, `pipeline/generate/generate.py` (B-10/B-11 fixes), and ~950 raw clustered event JSONs. Also found a stale `.git/index.lock` blocking all git operations (no process actually held it — removed safely). Committed as `7621656`.

### 3b. Regenerated the 3 B-11-affected events
Per the session-12 handover's Step 1: regenerated `evt_2026_06_04_014/062/066`.
- `evt_062`: the B-11 enforcement guard correctly fired and reclassified 2 paragraphs `contested → framing` — working as designed.
- `evt_066`: **crashed** with `AttributeError: 'list' object has no attribute 'get'`. The model returned a bare JSON array of paragraphs instead of the expected `{"paragraphs": [...]}` envelope. Fixed in `generate_report()` (`pipeline/generate/generate.py`) — now normalizes a list response by wrapping it. Committed as `a900b7c`.

### 3c. GitHub auth was broken
`git push` failed with "Invalid username or token." The stored credential was stale/invalid. Walked G through generating a new GitHub PAT (classic, `repo` scope) since `gh` CLI and Homebrew were both unavailable on this machine. Once G ran `git push` manually with the new token, the credential helper cached it and subsequent pushes from Claude Code worked normally.

### 3d. Ran 2 batches of new events (4 + 1 = 5 events)
**Batch A (4 events)** from the existing raw cluster pool, picked by scanning for clusters with 8–25 articles and ≥4 distinct outlets/bias tiers among the ones with cached article bodies:
- `evt_2026_06_04_017`, `evt_2026_06_01_023`, `evt_2026_06_01_117`, `evt_2026_06_04_023`

**Batch B (1 event)** after running a fresh `--discover` for current (June 28) news:
- `evt_2026_06_28_040` — US strikes Iran after cargo ship attack

Both batches committed (`a3d9bed`, `ceaae97`) and pushed.

### 3e. Diagnosed why fresh discover runs yield few usable candidates — logged as B-12
See `docs/00_MASTER_DOCUMENT.md §13, B-12`. Short version: `auto_cluster()` in `pipeline/cluster/group.py` uses connected-components clustering over a cosine-similarity threshold, which is transitive — unrelated articles get chained together into mega-clusters if they're linked by intermediate similar articles. Observed directly: a fresh discover run produced a 24-article "cluster" that was actually three or more distinct Gaza stories (UN genocide inquiry, a World Cup piece, a journalist's death) glued together by shared vocabulary. This buries genuinely good multi-outlet, diverse-spectrum candidates inside junk mega-clusters, shrinking the effective usable pool per discover run far below what the raw cluster count suggests. **Not yet fixed** — see backlog.

---

## 4. What to do next — in order

### Step 1: Address B-12 (clustering chaining) — recommended before further batches
This is the most leveraged fix available. Without it, every future `--discover` run will keep producing the same problem: a handful of mega-clusters eating most of the diverse coverage, leaving only 1–2 clean candidates per run. Options noted in the master doc:
- Switch to average-linkage or enforce a minimum *mean* pairwise similarity across the whole cluster (not just adjacent pairs).
- Add a post-cluster validation/split pass for oversized clusters.
- Cheaper stopgap: raise the similarity threshold (`DEFAULT_THRESHOLD = 0.70` in `pipeline/cluster/group.py`) and/or tighten the 48-hour time window.

### Step 2: Check for validator feedback
Still none as of this session (asked G directly, confirmed no responses yet). Keep checking each session.

### Step 3: Continue running batches toward the 20–30 target
At 15/20–30 now. Once B-12 is addressed, re-run `--discover` and expect a much larger pool of usable candidates. Until then, expect thin pickings (~1 good candidate per discover run) — RSS/Google News feeds only return a *current* snapshot, not a backfill, so don't expect a month-long gap to produce a backlog of fresh material either way.

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 scripts/scale_test.py --discover --beat israel_middle_east
python3 scripts/scale_test.py --run-events evt_A,evt_B,evt_C --beat israel_middle_east
git add data/events/ && git commit -m "add events: ..." && git push
```

**Picking good events (until B-12 is fixed):** manually check article counts/outlet diversity before committing to a run — the printed `--discover` cluster list is unreliable for size/cohesion. A quick Python scan of `data/ingested/israel_middle_east/*.json` cross-referenced against cluster `article_ids` (outlet + bias_rating fields) is more reliable than trusting cluster size alone. Watch for: (a) clusters that are actually 2–3 unrelated stories chained together, (b) re-clusters of stories you've already processed under a different cluster ID — check titles before running.

### Step 4: Complete M9
M9 is done when: 20–30 events are live, validators have given feedback, no new systematic bugs have emerged.

---

## 5. Pending backlog

| ID | Item | Priority |
|----|------|----------|
| **B-12** (new) | Cluster step chains unrelated articles into mega-clusters via transitive connected-components grouping | **Medium-high — recommended next** |
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

### GitHub auth (if push fails again)
Check for a stale `.git/index.lock` first (`rm` it if no git process is actually running — verify with `ps aux | grep git`). If push fails with "Invalid username or token," the stored credential has expired — G needs to generate a new PAT at `github.com/settings/tokens` (classic, `repo` scope) and re-authenticate via one manual `git push` in their own terminal (Claude Code's Bash tool can't handle the interactive credential prompt).

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
| `pipeline/generate/generate.py` | Generate stage — bare-array response fix is here (this session) |
| `pipeline/cluster/group.py` | Clustering — B-12 chaining issue lives here (`auto_cluster`, `DEFAULT_THRESHOLD`) |
| `scripts/scale_test.py` | Discover + run batches of events |
| `data/events/israel_middle_east/` | All clustered event JSONs (raw and processed) |
| `data/sources/outlet_provenance.json` | Outlet registry — update when adding new sources |
| `web/` | Next.js front end |
| `config/` | Beat configs (sources, domain_map) |
| `.env` | API keys — never commit |

---

## 8. Working conventions

1. **Sandbox/API limitation.** Cowork sandbox cannot call the Anthropic API (SSL proxy). All pipeline runs happen on G's machine via Claude Code with `.venv` activated.
2. **Schema v0.2 is current.** Bump and log in the Change Log if you change it.
3. **Golden dataset is the regression fixture.** `data/golden/event_001/`.
4. **Ask before:** heavy new dependencies, structural repo changes, anything in `00_MASTER_DOCUMENT.md §8`.
5. **New sources:** add to `sources` + `domain_map` in beat config, and `data/sources/outlet_provenance.json` with `last_reviewed` set to today.
6. **Tracksheet last.** Update before ending any session.
7. **Vercel auto-deploys on push.** Always commit + push after running new events.
8. **Commit discipline.** Don't let uncommitted work pile up across sessions — this session had to recover 972 files from a month-old uncommitted state. Commit at natural checkpoints within a session, not just at the very end.
9. **Outlet diversity rule of thumb (no hard numeric minimum codified):** the real enforced gate is *ideological spread*, not article count. B-01 requires `supported_by` to span ≥2 bias tiers on opposite sides of center for a claim to count as `agreed`; same-outlet duplicates don't count as independent corroboration (B-07). Golden dataset baseline is 8–12 articles/event; scale-test convention favors 10–25 articles/event, skipping single-source and >50-article (likely mega-) clusters.
