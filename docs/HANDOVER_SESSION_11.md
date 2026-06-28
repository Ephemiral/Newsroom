# HANDOVER — Session 11
## News Synthesis & Credibility Engine
**Handover date:** 4 June 2026
**Prepared by:** Claude (Cowork), Session 11
**For:** Claude (Cowork), Session 12
**Owner:** G (GitHub: Ephemiral)

---

## 1. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0–M5 | ✅ Done | |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending |
| M7 — Generate | ✅ Done | |
| M8 — Toggle UI | ✅ Done | |
| M9 — Validate Phase 2 | 🔄 **In progress** | 9 events processed; external validation underway via Vercel |

**Live event pages** (Vercel: `https://newsroom-sand-seven.vercel.app`):
- `/event/evt_2026_05_31_001` — golden event (Netanyahu 70% Gaza)
- `/event/evt_2026_06_01_009` — scale test 1 (24 art)
- `/event/evt_2026_06_01_068` — scale test 2 (6 art)
- `/event/evt_2026_06_01_065` — scale test 3 (4 art)
- `/event/evt_2026_06_02_044` — scale test 4 (18 art, full spectrum) — primary validation candidate
- `/event/evt_2026_06_02_014` — scale test 5 (12 art, left→right)
- `/event/evt_2026_06_02_063` — scale test 6 (5 art, Al Jazeera vs Israel Hayom)
- `/event/evt_2026_06_04_014` — Israel Day Parade / Smotrich controversy (17 art)
- `/event/evt_2026_06_04_062` — US-Iran ceasefire negotiations (23 art)
- `/event/evt_2026_06_04_066` — Iranian drone strike on Kuwait airport (12 art)

Also accessible at localhost: `cd web && npm run build && npm run start`

---

## 2. What changed this session

### Infrastructure — Vercel deployment

The app is now deployed at `https://newsroom-sand-seven.vercel.app` — a permanent public URL that does not require a running laptop. Setup involved:
- `git init` + push to GitHub (`Ephemiral/Newsroom`)
- Added `outputFileTracingIncludes` to `web/next.config.ts` so Vercel bundles `data/events/**/*` in the serverless function
- Connected repo to Vercel; free tier, auto-deploys on `git push`

**To publish new events to Vercel:** run the pipeline locally, then `git add data/events/ && git commit -m "..." && git push`. Vercel redeploys automatically in ~1 min.

---

### Generate — JSON parse robustness fix

`_parse_response()` in `pipeline/generate/generate.py` now matches `extract.py`: strips markdown fences, repairs truncated output (`stop_reason == max_tokens`), falls back to `json_repair`. Previously used bare `json.loads()` which crashed on minor model output malformation (hit during scale test on `evt_014`).

---

### B-10 / B-11 — Generate stage kind enforcement

**Root problem identified:** The generate model was labelling paragraphs as `kind=contested` based on whether the *topic* sounds like a dispute between parties (e.g., Iran vs US in negotiations), rather than whether *outlets* actually reported conflicting facts. In `evt_062`, zero claims had `contested_by` populated, yet 4 paragraphs were labelled `contested`. This is the same class of error as B-09 (reconciler mislabelling claims), one layer up.

**Two fixes in `pipeline/generate/generate.py`:**

1. **Prompt signal** — `_build_claims_block()` now emits a prominent `⚠ CONTESTED_BY STATUS` warning at the top of the claims block when no claim has `contested_by` populated, explicitly instructing the model not to write any `contested` paragraphs.

2. **Post-generation enforcement** — `_enforce_paragraph_kinds()` is called after generation and reclassifies `contested` → `framing` when:
   - `claim_ids` is empty (model ignored citation rule — treat as no evidence)
   - `claim_ids` is populated but none of the cited claims have `contested_by` non-empty

Logged as B-10 (claim_ids empty) and B-11 (wrong contested labelling) in `docs/00_MASTER_DOCUMENT.md §13`.

---

### Scale test — 3 new events

Ran `evt_014`, `evt_062`, `evt_066` through the full pipeline. Total events now: 9. Events viewable on Vercel.

---

## 3. What's next

### M9 completion path

**Primary:** Await external validator feedback on `evt_2026_06_02_044` and the new events. Questionnaire sent.

**Run more events:** Target is 20–30 events. After receiving feedback, run another batch:
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 scripts/scale_test.py --discover --beat israel_middle_east
python3 scripts/scale_test.py --run-events evt_A,evt_B,evt_C --beat israel_middle_east
```
After running, push to Vercel: `git add data/events/ && git commit -m "add events" && git push`

Pick events with 10–25 articles spanning left→right. Skip single-source clusters and mega-clusters (>50 articles).

**Regenerate existing events with B-11 fix:** The 3 events run this session (`evt_014`, `evt_062`, `evt_066`) were processed before the B-11 fix. Regenerate them with `--force`:
```bash
python3 -m pipeline.generate.run --event-id evt_2026_06_04_014
python3 -m pipeline.generate.run --event-id evt_2026_06_04_062
python3 -m pipeline.generate.run --event-id evt_2026_06_04_066
```
Then push to Vercel.

### Pending backlog

| ID | Item | Priority |
|----|------|----------|
| B-10 remaining gap | claim_ids still often empty — consider a second-pass citation prompt | Medium |
| B-01 re-run on golden event | clm_016/024 auto-fix | Low |
| Al Jazeera direct RSS diagnostic | proxy works, low urgency | Low |
| B-03–B-07 | In Master Doc §13 | Post-M9 |
| Hebrew sources (Rotter.net) | Post-M9 | Post-M9 |

---

## 4. Infrastructure notes

### Running the pipeline
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate

# Full discover + pick events
python3 scripts/scale_test.py --discover --beat israel_middle_east
python3 scripts/scale_test.py --run-events evt_A,evt_B --beat israel_middle_east

# Regenerate report only (skip analyze/annotate)
python3 -m pipeline.generate.run --event-id evt_XXX

# Front end (local)
cd web && npm run build && npm run start  # production mode — use for sharing
cd web && npm run dev                     # dev mode — localhost only, not for sharing
```

### Publishing to Vercel
```bash
git add data/events/
git commit -m "add events: evt_XXX, evt_YYY"
git push
```
Vercel auto-deploys in ~1 min. New events appear at `https://newsroom-sand-seven.vercel.app`.

### Scheduled tasks
| Task ID | Schedule | Purpose |
|---------|----------|---------|
| `newsroom-source-review` | Monday 9am | Enrich & review newly discovered domains |
| `newsroom-registry-review` | Thursday 9am | Check outlet registry for ownership changes |

---

## 5. Working conventions

1. **Sandbox can't call Anthropic API.** Write pipeline code here; G runs locally with `.venv` activated.
2. **Tracksheet first and last.** Push to GitHub after updating (Vercel doesn't use Drive). Parent Drive folder: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Schema v0.2** is current (event JSON and report sub-object).
4. **Ask before** heavy new dependencies, structural repo changes, fixed decisions (`docs/00_MASTER_DOCUMENT.md §8`).
5. **Golden dataset** is the regression fixture — test pipeline changes against it first.
6. **UI design decisions** in `docs/00_MASTER_DOCUMENT.md §12`.
7. **New sources:** add to both `sources` and `domain_map` in the beat config. Both are required.
8. **Outlet registry:** `data/sources/outlet_provenance.json`. Add new outlets here when adding to beat config. Set `last_reviewed` to today's date.
9. **Vercel auto-deploys on push.** Always commit + push after running new events if you want them live.
