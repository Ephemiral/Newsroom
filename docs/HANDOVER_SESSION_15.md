# HANDOVER — Session 15
## News Synthesis & Credibility Engine ("Critiqal")
**Handover date:** 7 July 2026
**Prepared by:** Claude Code (Fable 5), Session 15
**Owner:** G (GitHub: Ephemiral)

---

## 0. Read this first (30 seconds)

The product is **live and fully autonomous.** A GitHub Actions cron runs the whole pipeline every 6 hours across four theatres (Middle East, Europe, Americas, Asia), publishing openly-licensed-image news events to Vercel with **no human in the loop**. This session took it from "manual, local, Israel-only" to that state, and fixed the bugs that surfaced along the way.

- **Live site:** https://newsroom-sand-seven.vercel.app
- **Repo (now PUBLIC):** https://github.com/Ephemiral/Newsroom
- **Single source of truth:** `docs/00_MASTER_DOCUMENT.md` — §15 covers autonomous operation + images; §13/§14 backlog has B-16/B-17 (both RESOLVED this cycle).
- **Schema is v0.4** (`pipeline/schema.py: EVENT_SCHEMA_VERSION`).

At session start, **always check what the cron has published since**: `git log --oneline` for `auto:` commits, and the GitHub Actions run history. The repo and live site change on their own.

---

## 1. Current status

| Area | State |
|---|---|
| Autonomous pipeline | ✅ Live on GitHub Actions, every 6h, all 4 beats |
| Scheduler | GitHub Actions ONLY. **launchd is disabled + plist removed** — do not re-enable (they'd race) |
| Events live | 24 across beats: Middle East 17, Europe 2, Asia 5, Americas 0 (counts grow each cron run) |
| Images | ✅ Commons + Openverse, permissive licenses only, no cross-event reuse |
| Contested claims (B-16) | ✅ RESOLVED — actor-dispute model (schema v0.4) |
| State-aligned outlets (B-17) | ✅ RESOLVED — RT/Global Times/Asharq Al-Awsat/Saudi Gazette with alignment labels |
| Failure alerting | ✅ CI auto-opens a GitHub issue (`autorun-failure` label) with embedded diagnostics + emails G |

**M9 (validate phase 2)** is effectively met on the "20–30 events" axis; external validator feedback still never arrived (a standing open item since session 6).

---

## 2. What this session built (in order)

### 2a. Event images (schema v0.3 → NOW part of v0.4)
- `pipeline/images/` — `wikimedia.py` (Commons), `openverse.py` (2nd provider), `select.py` (Haiku query-gen + disqualify-then-pick), `run.py` (CLI).
- **Licenses:** CC0 / CC BY / CC BY-SA / public domain only. NC/ND rejected. Keeps clear of §7 copyright exposure. Full attribution stored in `event.image` and **must** be rendered (license requirement).
- **v2 rules:** angle-specific queries (a military-escalation story and a shipping story get different images); **no image reused across events**; any photo showing an identifiable person not central to the event is disqualified.
- CLI: `python3 -m pipeline.images.run --event-id X [--force]` or `--all-missing`.
- Front end: homepage thumbnails; event page shows the image **inside the report body after the lede** (`web/components/EventImageFigure.tsx`, placement logic in `ReportView.tsx`), not as a top hero.

### 2b. Autonomous runner (`scripts/auto_run.py`)
- One cycle per beat: ingest → cluster → **qualification gates** → analyze/annotate/generate → image → git commit + push.
- **Gates:** size 4–40, ≥3 outlets, cross-spectrum among **independent** outlets (state-aligned don't count), ≥3 usable bodies, cohesion ≥0.65, **≥50% new-URL novelty**, one-attempt fingerprinting.
- `--beats a,b,c` runs theatres in sequence; novelty gate is **global across beats** (a story can't publish in two theatres).
- Failure semantics (important): **systemic** errors (bad API key, crash, git failure) fail the workflow + alert and abort remaining beats; **routine** per-event validation rejections are recorded and skipped silently (no false alarms). Transient/systemic errors are NOT written to the ledger, so they retry next cycle.
- `pipeline/run_event.py` holds the shared stage-3–5 orchestration (used by both `auto_run.py` and `scripts/scale_test.py`).

### 2c. B-16 RESOLVED — actor disputes (schema v0.4)
- New optional claim field **`dispute_type: "actor"`**. Actor disputes stay `contested` with an empty `contested_by` by design (every reporting outlet corroborates the dispute exists; the two positions live in the claim text + framing_variants).
- `reconcile.py`: B-09 carve-out keeps validated actor disputes as contested; `generate.py`: `_claim_is_contested_evidence()` counts them as contested evidence.
- UI: a "conflicting accounts" tag on the claim card (`ClaimCard.tsx`).
- Validated: evt_066 0→3, evt_040 0→3, evt_062 1→4 contested claims. See Master Doc §13 B-16 (RESOLVED block).

### 2d. B-17 RESOLVED — state-aligned outlets
- New `state_alignment` field flows beat config → `Article` (schema) → per-event `sources[]` → UI.
- Outlets added: **RT News** (europe), **Global Times** (asia), **Asharq Al-Awsat** + **Saudi Gazette** (middle east). Provenance registry entries state ownership plainly.
- **Perspective, not corroboration:** excluded from the cross-spectrum gate (auto_run) and B-01's agreed tier count; reconcile/generate prompts require inline attribution ("Russian state-controlled RT reported that…").
- UI: ⚑ marker on chips, red badge on outlet cards, About-page section.

### 2e. Multi-theatre expansion
- New beat configs: `config/beats/europe.json`, `americas.json`, `asia.json` (feeds live-verified). `world_news.json` remains an unscheduled stub.
- Homepage theatre tabs (`web/lib/beats.ts` is the single label map; the "Middle East" label maps to internal beat key `israel_middle_east` — key never changed).
- 13 new outlets added to `data/sources/outlet_provenance.json`.

### 2f. Developing-news novelty + related events
- Novelty gate is now "≥50% of a cluster's article URLs are new," not a per-event overlap cap. A developing story (new coverage) publishes as a new event; prior events sharing articles are recorded in `event.related_events` and shown as an "Earlier coverage" box.
- **Known gap (see §4):** this is URL-based, so it does NOT catch *semantically* the same story with a different article set.

### 2g. Go-live polish
- `/about` methodology page; OG/Twitter meta tags (event image in social shares); `sitemap.ts`; `robots.ts`; tagline corrected "Neutral synthesis" → **"Transparent synthesis"** (per the fixed positioning decision — never claim neutrality).

### 2h. GitHub Actions migration (the long saga — see §3)
- `.github/workflows/autorun.yml`: cron `23 */6 * * *` + manual `workflow_dispatch`. Repo made **public** (unlimited Actions minutes; a 4-beat cycle is ~60–75 min, over the private free tier). Security audit before going public was clean (no key in history, no full article text in published JSON, `data/ingested/` gitignored).
- `data/autorun/state.json` is now **git-tracked** so the stateless CI runner shares the attempt ledger and commits it back.
- Fast **~1s auth check** + prefix/length sanity at the start of the workflow, so a bad key fails in seconds not 17 minutes.
- Failure issue body **embeds the run-log diagnostics** (readable via the public issues API without auth).

---

## 3. The GitHub Actions saga — why there are 5+ CI runs, and what each taught us

Do not be alarmed by the failed runs in the Actions history. Root causes, in order:
1. **Run #1 (401):** the `ANTHROPIC_API_KEY` secret value was wrong (paste error).
2. **Run #2 (33 min):** masked the still-wrong key (Israel had nothing to publish that cycle, so no API call) and crashed on a **missing beat directory** — `auto_run` wrote to `data/events/<beat>/` without `mkdir`. Fixed (`b6186d0`).
3. **Runs #3 & #4 (17 min, 401):** the secret was **still wrong** — the earlier re-paste never actually took. Confirmed via the new self-diagnosing issue body.
4. **Root fix:** the secret was set **via the GitHub API** (encrypted with PyNaCl, using G's stored git credential) — the key stayed in memory only, never printed, never written to disk (per G's explicit condition). PyNaCl was `pip install`ed into `.venv` for this (harmless, left installed).
5. **Run #5: SUCCESS** — authenticated, ran all four beats, published 5 events autonomously.
6. **Post-success:** the live site showed duplicates + missing events → traced to the **cross-beat ID collision** bug (§2h context / Master Doc §15a). Fixed in `3995bd5`.

**Takeaway for next session:** if a run fails, read the auto-opened GitHub issue — its body now contains the exact per-beat outcome and error. If the key ever needs re-setting, the API method is in this session's history (or just have G paste it; the fast auth-check confirms in ~1 min either way).

---

## 4. Open items / known gaps

| Item | Priority | Notes |
|---|---|---|
| **Semantic dedup + homepage story-grouping** | **High** | The novelty gate is URL-based, so it published 3 "Khamenei funeral" events (same story, different articles) on 6 July. Those were manually deleted, but the gap remains. **A background task (`task_4517860d`) was spawned this session and is running independently** to add embedding-based dedup at publish time + collapse `related_events` into one homepage card. Check its outcome before doing related work. |
| Funeral-dupe resurrection | Low | The 2 deleted funeral events' fingerprints are NOT in the rebuilt ledger (files were gone), so their article sets *could* re-publish once. Mitigated by the 3-day rolling ingest window aging those articles out. |
| Americas beat empty | Low/expected | 0 events so far — nothing cleared the gates yet, not a bug. Watch that its Fox `topic_filter` isn't too narrow. |
| B-10 (`claim_ids` often empty) | Medium | Unchanged from prior sessions. |
| External validator feedback | Medium | Never received (open since session 6). |
| Title/framing consistency | Medium | The funeral trio had inconsistent framing ("State Funeral" vs "Assassinated"). Reducing dupes masks it; a reconciler-consistency pass could help later. |

---

## 5. Operating reference

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate

# Manual cycle (same as CI runs)
python3 scripts/auto_run.py --beats israel_middle_east,europe,americas,asia

# Dry-run a beat (ingest+cluster+qualify only, no LLM, no publish)
python3 scripts/auto_run.py --dry-run --beats europe

# Image stage
python3 -m pipeline.images.run --event-id evt_X --beat europe [--force]
python3 -m pipeline.images.run --all-missing

# Front end (local)
cd web && npm run dev   # note: G often has this running on :3000 already
```

**CI:** trigger via GitHub UI (Actions → autorun → Run workflow) or API. Every failure opens an issue with diagnostics. The cron fires every 6h automatically.

**If the API key rotates:** re-set the `ANTHROPIC_API_KEY` repo secret (Settings → Secrets and variables → Actions). The workflow's fast auth-check confirms correctness within ~1 minute of the next run.

---

## 6. Working conventions (carry forward)

1. Event IDs are **beat-namespaced and globally unique** — never revert to a beat-agnostic scheme (Master Doc §15a).
2. Run exactly ONE scheduler (GitHub Actions). Do not re-enable launchd.
3. Image attribution lines are a **license requirement** — never remove.
4. Positioning is "transparent & multi-perspectival," **never** "neutral/objective."
5. State-aligned outlets are perspective, not corroboration — keep them out of cross-spectrum counts and always label them.
6. Bump `EVENT_SCHEMA_VERSION` for structural JSON changes; log in the TRACKSHEET Change Log.
7. Watch for stale `.git/index.lock` (recurred several times historically) — remove if no git process is live.
8. Commit at natural checkpoints; keep `data/autorun/state.json` consistent with the committed event files (rebuild it from the events if in doubt — the fingerprint is `sha256("\n".join(sorted(source_urls)))[:16]`).

---

## 7. Key file map (what changed this session)

| Path | Purpose |
|---|---|
| `scripts/auto_run.py` | Autonomous runner: gates, multi-beat, beat-namespaced IDs, systemic-vs-routine failure handling |
| `pipeline/run_event.py` | Shared stage-3–5 orchestration |
| `pipeline/images/` | Image stage (Commons + Openverse) |
| `pipeline/schema.py` | `EVENT_SCHEMA_VERSION="0.4"`, `state_alignment` field |
| `pipeline/analyze/reconcile.py` | B-16 actor disputes, B-17 state-alignment, B-01/B-02/B-09 guards |
| `pipeline/generate/generate.py` | `_claim_is_contested_evidence()`, state-aligned prose attribution |
| `.github/workflows/autorun.yml` | CI: cron, fast auth-check, self-diagnosing failure issues |
| `config/beats/{europe,americas,asia}.json` | New theatre configs |
| `data/sources/outlet_provenance.json` | +13 outlets incl. 4 state-aligned |
| `web/lib/beats.ts` | Beat label map ("Middle East") |
| `web/app/page.tsx` | Theatre tabs, thumbnails |
| `web/components/{EventImageFigure,ReportView,ClaimCard,OutletCard}.tsx` | Image placement, actor-dispute tag, ⚑ alignment markers |
| `web/app/about/page.tsx`, `sitemap.ts`, `robots.ts` | Go-live polish |
| `data/autorun/state.json` | Git-tracked attempt ledger |
