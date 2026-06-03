# HANDOVER — Session 10
## News Synthesis & Credibility Engine
**Handover date:** 2 June 2026
**Prepared by:** Claude (Cowork), Session 10
**For:** Claude (Cowork), Session 11
**Owner:** G (GitHub: Ephemiral)

---

## 1. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0–M5 | ✅ Done | |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending |
| M7 — Generate | ✅ Done | |
| M8 — Toggle UI | ✅ Done | |
| M9 — Validate Phase 2 | 🔄 **In progress** | Self-review (G, centrist) on evt_044 complete; formal external validation deferred |

**Live event pages** (`cd web && npm run dev` → http://localhost:3000):
- `/event/evt_2026_05_31_001` — golden event (Netanyahu 70% Gaza)
- `/event/evt_2026_06_01_009` — scale test 1 (24 art)
- `/event/evt_2026_06_01_068` — scale test 2 (6 art)
- `/event/evt_2026_06_01_065` — scale test 3 (4 art) — regenerated with B-08 fix ✓
- `/event/evt_2026_06_02_044` — scale test 4 (18 art, full spectrum) — primary validation candidate
- `/event/evt_2026_06_02_014` — scale test 5 (12 art, left→right)
- `/event/evt_2026_06_02_063` — scale test 6 (5 art, Al Jazeera vs Israel Hayom)

---

## 2. What changed this session

### UI — Transparency toggle: receipts now hide correctly

**Problem:** When the transparency toggle was turned off, any paragraph whose "Show sources" had been clicked would still show its receipt.

**Fix:** `{expanded && transparencyMode && <Receipt />}` — receipt only renders when both conditions are true. The `expanded` state persists so re-enabling transparency restores previously-open paragraphs.

**File:** `web/components/ReportView.tsx`

---

### UI — Sidebar bar alignment fixed

**Problem:** The sidebar bar was a separate flex column alongside the paragraph cards column. Each bar segment used `flexGrow: 1`, dividing available height equally — not matching individual paragraph heights. Result: colors were cut off mid-paragraph and misaligned.

**Fix:** Restructured layout. Each paragraph is now a `flex items-stretch` row containing its own 2px bar segment + content div. The bar segment stretches to exactly match its sibling paragraph card's height.

**File:** `web/components/ReportView.tsx`

---

### UI — Contested receipt: ↔ separator and two-sided layout

**Problem:** Contested paragraphs showed source chips flat (no indication of which outlet was on which side of the contention).

**Fix:** Receipt for `contested` paragraphs now:
- Aggregates `supported_by` and `contested_by` from all cited claims
- Deduplicates by outlet name; if same outlet appears on both sides, keeps it on the supporting side and appends an italicised note: *"[Outlet] published articles on both sides of this contention."*
- Renders supporting outlets ↔ contesting outlets with a `↔` separator
- Falls back to plain source list if `contested_by` is empty across all cited claims

**File:** `web/components/ReportView.tsx`

---

### B-09 logged — reconciler must not mark a claim `contested` when `contested_by` is empty

**Problem identified during evt_044 review:** `clm_020` (Iran drone/US denial) is classified `contested` but `contested_by=[]`. The reconciler inferred dispute from the claim text itself (two parties — Iran and CENTCOM — giving contradictory statements), not from two outlets contradicting each other. Both BBC and Euronews agreed on the facts. The claim should be `corroborated`.

**Documented in:** `docs/00_MASTER_DOCUMENT.md §13` as B-09.

**Fix required in:** `pipeline/analyze/reconcile.py` — post-classification guard: if `classification == "contested"` and `contested_by == []`, reclassify as `corroborated` (multiple outlets) or `single_source`.

---

### Self-review — evt_2026_06_02_044

G reviewed evt_044 (18 articles, full left→right spectrum) as a self-proclaimed centrist:
1. Article reads balanced; sources well mixed across the spectrum.
2. Contested paragraph text is well-written. Two data issues noted: Euronews on both sides of the nuclear claim (two different articles, legitimate), and military operations paragraph showing no ↔ (B-09 upstream cause).
3. Transparency toggle creates anticipation to explore sourcing — positive signal.
4. All outlets have room in the coverage; feels balanced.
5. N/A — Hamas health ministry question doesn't apply to this event (Iran/nuclear, not Gaza).

---

### Scheduled tasks — both pre-approved

Both scheduled tasks have been manually triggered to pre-approve tool permissions:
- `newsroom-source-review` — Mondays 9am
- `newsroom-registry-review` — Thursdays 9am

---

## 3. What's next

### M9 completion path
The remaining gap is: (a) event volume (target 20–30; currently 6) and (b) spectrum-spanning external validators. Neither is actionable without G running more pipeline cycles and recruiting reviewers. When ready:

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 scripts/scale_test.py --discover --beat israel_middle_east
python3 scripts/scale_test.py --run-events evt_A,evt_B --beat israel_middle_east
```

Best external candidates: evt_2026_06_02_044 (18 art, full spectrum), evt_2026_06_02_014 (12 art).

Validation questions (event-agnostic):
1. Does the narrative feel balanced given the source mix?
2. Are contested paragraphs presented fairly — neither side given implicit credibility?
3. Did expanding the sources (transparency toggle) change how you read any paragraph?
4. Does every part of the political spectrum represented in the sources feel like it has room?
5. Is any background or contextual claim insufficiently attributed?

### B-09 — fix reconcile.py
Priority backlog item. Add post-classification guard in `pipeline/analyze/reconcile.py` to reclassify `contested` claims with empty `contested_by`. See `docs/00_MASTER_DOCUMENT.md §13 B-09` for the exact fix.

### Pending backlog
| ID | Item | Priority |
|----|------|----------|
| B-09 | contested_by=[] guard in reconcile.py | High — next pipeline session |
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
3. **Schema v0.2** is current (event JSON and report sub-object).
4. **Ask before** heavy new dependencies, structural repo changes, fixed decisions (`docs/00_MASTER_DOCUMENT.md §8`).
5. **Golden dataset** is the regression fixture — test pipeline changes against it first.
6. **UI design decisions** in `docs/00_MASTER_DOCUMENT.md §12`.
7. **New sources:** add to both `sources` and `domain_map` in the beat config. Both are required.
8. **Outlet registry:** `data/sources/outlet_provenance.json`. Add new outlets here when adding to the beat config. Set `last_reviewed` to today's date.
