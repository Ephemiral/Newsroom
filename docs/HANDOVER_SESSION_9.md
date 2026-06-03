# HANDOVER — Session 9
## News Synthesis & Credibility Engine
**Handover date:** 2 June 2026
**Prepared by:** Claude (Cowork), Session 9
**For:** Claude (Cowork), Session 10
**Owner:** G (GitHub: Ephemiral)

---

## 1. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0–M5 | ✅ Done | |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending |
| M7 — Generate | ✅ Done | |
| M8 — Toggle UI | ✅ Done | |
| M9 — Validate Phase 2 | 🔄 **In progress** | Pre-validation UI/pipeline fixes applied this session; ready to validate |

**Live event pages** (`cd web && npm run dev` → http://localhost:3000):
- `/event/evt_2026_05_31_001` — golden event (Netanyahu 70% Gaza)
- `/event/evt_2026_06_01_009` — scale test 1 (24 art)
- `/event/evt_2026_06_01_068` — scale test 2 (6 art)
- `/event/evt_2026_06_01_065` — scale test 3 (4 art) — **needs regeneration after B-08 fix**
- `/event/evt_2026_06_02_044` — scale test 4 (18 art, full spectrum)
- `/event/evt_2026_06_02_014` — scale test 5 (12 art, left→right)
- `/event/evt_2026_06_02_063` — scale test 6 (5 art, Al Jazeera vs Israel Hayom)

---

## 2. What changed this session

### B-08 — New paragraph kind: `one_sided`; strict kind taxonomy

**Problem identified:** The generate stage was labeling paragraphs as `contested` when they were
actually reported by only one ideological lane. `contested` was doing two jobs — active factual
dispute AND one-sided coverage — which conflated different signals and produced misleading labels.

**Fix:**
- Added `one_sided` as a fifth paragraph kind alongside `agreed`, `contested`, `framing`, `background`.
- Rewrote `## Paragraph kinds` in `GENERATE_SYSTEM` (`pipeline/generate/generate.py`) with
  strict, claim-data-driven rules: each kind must be derivable from the claim classification
  and `contested_by` fields. `contested` now requires at least one cited claim with
  `contested_by` non-empty.
- Added post-generation validation in `validate_report()`: warns if a `contested` paragraph
  cites no claim with `contested_by` populated.
- Bumped report `schema_version` from `"0.1"` to `"0.2"`.
- Added `one_sided` to `ReportParagraph['kind']` union in `web/lib/types.ts`.
- Added `one_sided` to `KIND` config in `web/components/ReportView.tsx`: pink sidebar bar
  (`#f9a8d4` / `#db2777`), "One-sided" badge, tooltip explaining the asymmetry signal.

**B-08 written up in:** `docs/00_MASTER_DOCUMENT.md §13`

### B-08 (cont.) — Kind-based ordering replaces Gaza-specific ordering

**Problem:** `## Ordering` in the generate prompt was hardcoded for Gaza (Hamas attacks, ceasefire,
territorial expansion, etc.), making it irrelevant and potentially confusing for non-Gaza events.

**Fix:** Replaced topic-specific ordering with a kind-based sequence:
1. `agreed` → 2. `background` → 3. `framing` / `one_sided` → 4. `contested`

Added explicit safeguard: if a kind group has no supporting claims, omit it entirely — never
invent paragraphs to fill a structural slot.

### Outlet metadata registry — populated and scheduled

**Problem:** `data/sources/outlet_provenance.json` was missing ownership data for most beat
outlets (BBC, The Guardian, Israel Hayom, Ynet, Arutz Sheva, Middle East Eye, Jerusalem Post,
i24 News), causing empty description boxes in the Sources section.

**Fix:**
- Populated `outlet_provenance.json` with all 13 current beat outlets plus name variants
  (e.g. both `"Haaretz"` and `"Haaretz (English)"`). Each entry now has `ownership`, `notes`,
  and `last_reviewed`.
- Created `scripts/registry_review.py`: weekly script that checks each outlet for
  ownership/funding changes using Haiku, presents a digest, and flags updates for G's review.
  Does NOT auto-edit the registry — G approves changes manually.
- Created scheduled task `newsroom-registry-review`: runs every **Thursday at 9am**
  (separate from the Monday source-discovery review). Run "Run now" once in the Scheduled
  sidebar to pre-approve tool permissions.

### Sources section — grouped by outlet (`OutletCard`)

**Problem:** The Sources section showed one card per article, causing the same outlet to appear
multiple times (4 Israel Hayom cards, 2 Guardian cards with different authors).

**Fix:**
- Created `web/components/OutletCard.tsx`: groups all articles from the same outlet into one card.
  Shows ownership and bias badge once per outlet. Individual articles (date, author, link)
  are listed within the card — collapsed behind a "▸ N articles" toggle when there are multiple.
- Updated `web/app/event/[id]/page.tsx`: sources section now groups by outlet and renders
  `OutletCard` instead of `SourceCard`. Header now reads "X outlets, Y articles".
- `SourceCard.tsx` is retained (still used by ReportView receipts).

---

## 3. What's next

### Immediate — regenerate evt_2026_06_01_065
The 065 event was generated before the B-08 fix. Re-run to confirm `one_sided` paragraphs
appear correctly and no B-08 validation warnings are emitted:
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 -m pipeline.generate.run --event-id evt_2026_06_01_065 --force
```

### M9 completion — external validation
Still the primary open milestone. Best candidate events:
- `evt_2026_06_02_044` — 18 articles, full left→right spectrum
- `evt_2026_06_02_014` — 12 articles, left→right

Three reader profiles needed: pro-Palestinian, pro-Israeli, centrist.
Validation questions are in `docs/HANDOVER_SESSION_8.md §3`.

### Registry scheduled task — run once manually
Click "Run now" on `newsroom-registry-review` in the Scheduled sidebar to pre-approve
tool permissions before the first automatic Thursday run.

### Future considerations (not action items)
FC-01 added to `docs/00_MASTER_DOCUMENT.md §14`: whether official government statements should eventually be sourced directly (press releases / official channels) rather than through news outlet reporting. Conclusion: not a current requirement; the right future move is a `source_type` field on the claim schema. No action needed before M9.

### Pending backlog items
| ID | Item | Priority |
|----|------|----------|
| B-01 re-run on golden event | clm_016/024 auto-fix | Low |
| Al Jazeera direct RSS diagnostic | proxy works, low urgency | Low |
| B-03–B-07 | Backlog in `docs/00_MASTER_DOCUMENT.md §13` | Post-M9 |
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

# Or run stages individually
python3 -m pipeline.ingest.run --beat israel_middle_east
python3 -m pipeline.cluster.run --beat israel_middle_east
python3 -m pipeline.analyze.run --source cluster --cluster-id evt_XXX
python3 -m pipeline.annotate.run --source file --analyzed-file data/events/israel_middle_east/evt_XXX_analyzed.json
python3 -m pipeline.generate.run --event-id evt_XXX

# Front end
cd web && npm run dev   # → http://localhost:3000
```

### Scheduled tasks
| Task ID | Schedule | Purpose |
|---------|----------|---------|
| `newsroom-source-review` | Monday 9am | Enrich & review newly discovered domains |
| `newsroom-registry-review` | Thursday 9am | Check outlet registry for ownership changes |

---

## 5. Working conventions

1. **Sandbox can't call Anthropic API.** Write pipeline code here; G runs locally with `.venv` activated.
2. **Tracksheet first and last.** Upload to Drive after updating. Parent folder: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Schema v0.2** is current (event JSON). Report sub-object now also at `"0.2"` (added `one_sided` kind).
4. **Ask before** heavy new dependencies, structural repo changes, fixed decisions (`docs/00_MASTER_DOCUMENT.md §8`).
5. **Golden dataset** is the regression fixture — test pipeline changes against it first.
6. **UI design decisions** in `docs/00_MASTER_DOCUMENT.md §12`.
7. **New sources:** add to both `sources` and `domain_map` in the beat config. Both are required.
8. **Outlet registry:** `data/sources/outlet_provenance.json`. Add new outlets here when adding to the beat config. Set `last_reviewed` to today's date.
