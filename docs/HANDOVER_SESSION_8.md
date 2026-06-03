# HANDOVER — Session 8
## News Synthesis & Credibility Engine
**Handover date:** 2 June 2026
**Prepared by:** Claude (Cowork), Session 7
**For:** Claude (Cowork), Session 8
**Owner:** G (GitHub: Ephemiral)

---

## 1. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0–M5 | ✅ Done | |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending |
| M7 — Generate | ✅ Done | |
| M8 — Toggle UI | ✅ Done | |
| M9 — Validate Phase 2 | 🔄 **In progress** | 6 events processed; external validation is the remaining step |

**Live event pages** (`cd web && npm run dev` → http://localhost:3000):
- `/event/evt_2026_05_31_001` — golden event (Netanyahu 70% Gaza)
- `/event/evt_2026_06_01_009` — scale test 1 (24 art)
- `/event/evt_2026_06_01_068` — scale test 2 (6 art)
- `/event/evt_2026_06_01_065` — scale test 3 (4 art)
- `/event/evt_2026_06_02_044` — scale test 4 (18 art, full spectrum)
- `/event/evt_2026_06_02_014` — scale test 5 (12 art, left→right)
- `/event/evt_2026_06_02_063` — scale test 6 (5 art, Al Jazeera vs Israel Hayom)

---

## 2. What changed this session

### Full spectrum source coverage achieved
The beat now covers left → right for the first time:

| Bias | Outlets |
|------|---------|
| left | Al Jazeera English, Middle East Eye |
| center-left | Haaretz, The Guardian |
| center | Reuters, BBC News, Euronews |
| center-right | Ynet News *(new)*, Times of Israel, Jerusalem Post, i24 News |
| right | Arutz Sheva *(new)*, Israel Hayom *(new)* |

All three new outlets use Google News RSS proxy (direct RSS unavailable/blocked). `domain` field added to all sources in beat config for GDELT matching.

### GDELT ingest (`pipeline/ingest/gdelt.py`)
New ingest path alongside RSS. Queries GDELT DOC 2.0 API with beat keywords, maps article domains to outlet metadata via `domain_map` in the beat config. Unknown domains are logged to `data/suggested_sources.json` rather than silently dropped.

Run with: `python3 -m pipeline.ingest.run --beat israel_middle_east` (GDELT runs automatically after RSS if `gdelt.enabled: true` in config). Skip GDELT with `--no-gdelt`.

**Install requirement:** `pip install gdeltdoc pandas`

### Source discovery (`data/suggested_sources.json`)
Every GDELT run logs previously unseen domains with: `seen_count`, `sample_titles`, `first_seen`, `enriched` (bool), `reviewed` (bool). The weekly scheduled task enriches and presents these for G's review.

### Weekly scheduled task (`newsroom-source-review`)
Runs every Monday at 9am. Reads `suggested_sources.json`, uses web search to research un-enriched domains (bias, ownership, funding, country, editorial stance, flags), writes enrichment back to file, and presents a formatted review digest. G then decides whether to add the source to the beat config.

**To add a reviewed source:** add to both `sources` and `domain_map` in `config/beats/israel_middle_east.json`.

### Frontend — force-dynamic rendering (`web/app/page.tsx`, `web/app/event/[id]/page.tsx`)
Added `export const dynamic = 'force-dynamic'` and removed `generateStaticParams()`. New event JSON files now appear in the UI and at their URLs without restarting the dev server.

---

## 3. What's next

### M9 completion — external validation
The scale test is done. The remaining M9 requirement is external validation: three reader profiles (pro-Palestinian, pro-Israeli, centrist) evaluating the Phase-2 report on at least one event with full spectrum coverage. **evt_2026_06_02_044** or **evt_2026_06_02_014** are the best candidates — both have left through right coverage.

Questions to ask validators:
- Does the narrative feel balanced given the source mix?
- Are contested paragraphs presented fairly (neither side given implicit credibility)?
- Did expanding sources change how you read any paragraph?
- Is the right-wing Israeli framing (Arutz Sheva, Israel Hayom) represented without being dismissed?
- Is the Hezbollah/Lebanon context and Hamas-run health ministry attribution clear enough?

### Al Jazeera diagnostic (still pending)
Al Jazeera is now working via Google News proxy (articles appear in evt_007 cluster), but worth running the diagnostic to understand whether their direct feed can ever be used, or if the proxy is permanent.

### B-01 re-run on golden event
The golden event (evt_2026_05_31_001) was analyzed before B-01 enforcement. Re-running analyze → annotate → generate would correct clm_016 and clm_024 misclassifications. Low priority but worth doing before M9 closes.

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 -m pipeline.analyze.run --source golden
python3 -m pipeline.annotate.run --source golden
python3 -m pipeline.generate.run --force
```

### Rotter.net / Hebrew sources
The user has an existing CIB detection engine for Rotter.net. Hebrew-language sources are currently out of scope (pipeline assumes English), but this is worth revisiting after M9. Candidate: add Hebrew→English translation as an optional ingest step (trafilatura + Google Translate API or Argos Translate).

---

## 4. Infrastructure notes

### Running the pipeline
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate

# Full discover + pick events
python3 scripts/scale_test.py --discover --beat israel_middle_east
python3 scripts/scale_test.py --run-events evt_A,evt_B --beat israel_middle_east

# Or run stages individually
python3 -m pipeline.ingest.run --beat israel_middle_east
python3 -m pipeline.cluster.run --beat israel_middle_east
python3 -m pipeline.analyze.run --source cluster --cluster-id evt_XXX
python3 -m pipeline.annotate.run --source file --analyzed-file data/events/israel_middle_east/evt_XXX_analyzed.json
python3 -m pipeline.generate.run --event-id evt_XXX

# Front end
cd web && npm run dev   # → http://localhost:3000
```

### Key cluster parameters
- Threshold: `0.70` (raised from 0.50 — required for beat-specific data)
- Time window: `48h` (articles >48h apart won't cluster together)
- Override: `--threshold 0.80` for tighter clusters, `--time-window 72` for slower stories

### GDELT config (in beat JSON)
```json
"gdelt": {
  "enabled": true,
  "keywords": ["Israel", "Gaza", ...],
  "timespan": "24h",
  "max_records": 250,
  "language": "English"
}
```
Tune `max_records` down (e.g. 100) if ingest is too slow.

---

## 5. Known issues / backlog

| ID | Issue | Status |
|----|-------|--------|
| Al Jazeera direct RSS | 301→403, using Google News proxy | Low — proxy works fine |
| B-03 | Rationale mentions outlet not in source list (warning only) | Low |
| B-05/B-06 | Prompt improvements for policy rationale + parallel framing | In reconcile prompt |
| Golden event re-run | clm_016/024 will auto-fix with B-01 enforcement | Low priority |
| Hebrew sources | Rotter.net sources are Hebrew-only | Post-M9 |
| Suggested sources task | Run "Run now" in Scheduled sidebar to pre-approve tool permissions | Do once |

Full backlog: `docs/00_MASTER_DOCUMENT.md §13`

---

## 6. Working conventions

1. **Sandbox can't call Anthropic API.** Write pipeline code here; G runs locally with `.venv` activated.
2. **Tracksheet first and last.** Upload to Drive after updating. Parent folder: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Schema v0.2** is current. Bump + log if structure changes.
4. **Ask before** heavy new dependencies, structural repo changes, fixed decisions (§8).
5. **Golden dataset** is the regression fixture — test pipeline changes against it first.
6. **UI design decisions** in `docs/00_MASTER_DOCUMENT.md §12`.
7. **New sources:** add to both `sources` and `domain_map` in the beat config. Both are required.
