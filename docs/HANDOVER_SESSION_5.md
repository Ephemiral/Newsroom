# HANDOVER — Session 5
## News Synthesis & Credibility Engine
**Handover date:** 1 June 2026
**Prepared by:** Claude (Cowork), Session 4
**For:** Claude (Cowork), Session 5
**Owner:** G (GitHub: Ephemiral)

---

## 1. What is this project (30-second version)
A media product that aggregates news coverage of a single event from many outlets across the political spectrum, extracts what they agree on vs. dispute, surfaces source provenance (ownership, bias rating, author background), and presents a transparent multi-perspectival analysis. Pipeline: `INGEST → CLUSTER → ANALYZE → ANNOTATE → GENERATE`. Front end: Next.js. Contract between pipeline and UI: a per-event JSON artifact on disk. Full architecture: `docs/00_MASTER_DOCUMENT.md`.

---

## 2. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0 — Golden dataset | ✅ Done | 10 articles, 1 event (`data/golden/event_001/`) |
| M1 — Ingest | ✅ Done | RSS + dedup + storage + CLI |
| M2 — Cluster | ✅ Done | Embeddings + threshold clustering |
| M3 — Analyze | ✅ Done | Claim extraction (Haiku) + reconciliation (Sonnet); 32 claims |
| M4 — Annotate | ✅ Done | Ownership + author background filled |
| M5 — Phase-1 page | ✅ Done | Next.js app in `web/` |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending — kept open for fine-tuning |
| M7 — Generate | ✅ Done | 11 paragraphs in `report` field; prompt improved this session |
| M8 — Toggle UI | ✅ Done | ReportView with continuous bar + transparency toggle — see §4 |
| M9 — Validate Phase 2 | 🔲 Not started | **← NEXT TASK** — see §5 |

**TRACKSHEET.xlsx** is the live record. Always update and upload to Drive (folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`).

---

## 3. What changed this session

### M7 — Generate pipeline
- **`pipeline/generate/generate.py`** — new module: `GENERATE_SYSTEM` prompt, `generate_report()`, `validate_report()`.
- **`pipeline/generate/run.py`** — CLI runner: loads `_analyzed.json`, calls generate, validates IDs, writes `report` field in-place. Use `--force` to regenerate.
- **Prompt rules added this session** (in `GENERATE_SYSTEM`):
  - **Source balance** — weight by ideological breadth, not source count. Flag single-spectrum claims.
  - **Quotes** — include verbatim first-person quotes from `framing_variants` where available.
  - **Casualty figures** — attribute Gaza death tolls to Hamas-run Gaza Health Ministry; note unverified status.
  - **Regional context** — when Lebanon/Syria operations appear, always explain Hezbollah/Iran proxy background as a separate conflict.

### M8 — Toggle UI
- **`web/components/ReportView.tsx`** — new client component:
  - Thin 2px continuous sidebar bar, colored by paragraph `kind` (never breaks)
  - Indigo pill toggle ("Show sources" / "Transparency on")
  - When toggle ON: kind legend row with hover tooltips + per-paragraph kind badge + per-paragraph "Show/Hide sources" button
  - Each paragraph expands/collapses independently; paragraph text always visible
  - Receipt: claims as gray bullet points, sources as pale tinted chips, outlet deduplication
- **`web/lib/types.ts`** — added `ReportParagraph`, `Report` interfaces; `AnalyzedEvent.report` typed as `Report | null`
- **`web/app/event/[id]/page.tsx`** — `ReportView` wired in above the claims section; `claimsMap` passed through

### Data quality issue identified
- **clm_024** (death toll >72,000) is classified `agreed` but both sources are Al Jazeera English — same outlet. Should be `single_source`. Logged as **B-07** in `docs/00_MASTER_DOCUMENT.md §13`. Will be auto-corrected by B-01 enforcement on next pipeline re-run. No manual fix needed.

### Documentation updated
- `docs/00_MASTER_DOCUMENT.md §12` — Report transparency UI design decisions added
- `docs/00_MASTER_DOCUMENT.md §13` — B-07 added

---

## 4. What the front end looks like now

Run with:
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom/web
npm run dev   # → http://localhost:3000
```

**Page at `/event/evt_2026_05_31_001`:**
- **Analysis section** (new, above claims):
  - 11 paragraphs with a continuous 2px colored sidebar bar
  - Indigo "Show sources" toggle in the header
  - Toggle ON: kind legend (Agreed/Contested/Framing/Background with tooltips), per-paragraph kind badge, per-paragraph "Show/Hide sources" button
  - Expanding a paragraph shows: bullet-point claims + pale outlet chips
- **What the coverage shows** (unchanged from M5):
  - Four collapsible groups: Agreed / Corroborated / Contested / Single-source
  - Claims grouped by `claim_group` theme within each section
  - Bias spectrum legend
- **Source provenance cards**

**To regenerate the report** (e.g., after prompt changes):
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 -m pipeline.generate.run --force
```

---

## 5. M9 — Validate Phase 2 (next milestone)

**Definition of done:** Readers find the synthesized report fair and useful; the transparency mechanism is intuitive; 20–30 events have been processed end-to-end.

**What this involves:**
1. **Personal read-through** of the full Phase-2 page (report + toggle + claims).
2. **External validators** (same three profiles as M6 — pro-Palestinian, pro-Israel, centrist) asked to evaluate the *report* specifically:
   - Does the narrative feel balanced given the source mix?
   - Are the contested paragraphs presented fairly?
   - Did expanding the sources change how you read any paragraph?
   - Is the Hezbollah/Lebanon context sufficient?
3. **Scale test** — process 2–3 more events through the full pipeline (ingest → cluster → analyze → annotate → generate) to verify nothing is brittle.
4. **B-01 fix** — before the scale test, implement the cross-spectrum classification threshold in `reconcile.py` so clm_024 and clm_016 are correctly classified. This also fixes B-07.

**Known backlog items to address before or during M9:**
- B-01 (classification threshold) — highest priority; fixes clm_024 and clm_016
- B-02 (supported_by ∩ contested_by validation) — already in `reconcile.py` as a warning; promote to enforced rule
- B-07 (clm_024 misclassification) — resolved automatically by B-01

---

## 6. Working conventions (carry forward)

1. **Tracksheet first and last.** Mark milestone In Progress when starting, Done when finishing. Add change log rows. Upload to Drive via Google Drive MCP.
2. **Drive upload.** Local folder does NOT auto-sync. After updating `TRACKSHEET.xlsx`, always upload via the MCP tools. Parent folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Golden dataset first.** Test pipeline changes against `data/golden/event_001/` before touching live feeds.
4. **Schema is the contract.** Currently at v0.2. Bump `schema_version` if the per-event JSON structure changes; log in tracksheet.
5. **Ask before:** heavy new dependencies, structural repo changes, anything in `00_MASTER_DOCUMENT.md §8` (fixed decisions).
6. **Sandbox can't call Anthropic API.** Write pipeline code here, but G must run it locally from the Newsroom root with `.venv` activated.
7. **UI design decisions** in `00_MASTER_DOCUMENT.md §12` — consult before changing colors, fonts, layout, or interaction patterns.
8. **Backlog** in `00_MASTER_DOCUMENT.md §13` (B-01 through B-07) — implement on next full pipeline run.
9. **Project instructions:** Ask for permission before any unauthorized or unspecified changes.
