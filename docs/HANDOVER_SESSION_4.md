# HANDOVER — Session 4
## News Synthesis & Credibility Engine
**Handover date:** 31 May 2026
**Prepared by:** Claude (Cowork), Session 3
**For:** Claude (Cowork), Session 4
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
| M2 — Cluster | ✅ Done | Embeddings + threshold clustering; 10/10 golden → 1 cluster |
| M3 — Analyze | ✅ Done | Claim extraction (Haiku) + reconciliation (Sonnet); 32 claims |
| M4 — Annotate | ✅ Done | Ownership + author background filled; source cache at `data/sources/` |
| M5 — Phase-1 page | ✅ Done | Next.js app in `web/`; significant UI improvements this session (see §4) |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending — see §5 |
| M7 — Generate | 🔲 Not started | **← NEXT TASK after M6** — see §6 |
| M8–M9 | 🔲 Not started | |

**TRACKSHEET.xlsx** is the live record. Updated locally and uploaded to Drive (folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`). Use the most recently modified version in Drive.

---

## 3. What changed this session

### Pipeline changes
- **`pipeline/analyze/reconcile.py`** — major update:
  - New `RECONCILE_SYSTEM` prompt adds `corroborated` as a 4th classification (same-side sources only), `claim_group` in the output schema, the stated-rationale extraction rule (B-05), and the parallel framing rule for contested claims (B-06).
  - New `validate_reconciled_output()` function runs after every reconcile call and prints labelled warnings for: sources appearing in both supported_by and contested_by (B-02), and "agreed" claims lacking genuine cross-spectrum support (B-01).
- **`pipeline/analyze/extract.py`** — extraction prompt now instructs Haiku to extract an actor's stated justification as a separate claim whenever a directive or policy is present (B-05).

### Schema & types
- **`web/lib/types.ts`** — `Classification` type now includes `'corroborated'`; `Claim` interface gains optional `claim_group?: string | null`; version comment updated to v0.2.

### UI changes (`web/`)
- **`ClaimCard.tsx`** — contested source chips redesigned: supporting outlets and contesting outlets are now separated by a `↔` divider, both sides using their standard bias color. The old thunderbolt + red styling is gone.
- **`ClaimSection.tsx`** — claims now group by `claim_group` within each section, rendered under snake_case-derived sub-headers. Falls back to flat rendering if no groups present (backward-compatible).
- **`page.tsx`** — added `corroborated` classification section (teal accent) between Agreed and Contested.

### Data
- **`data/events/israel_middle_east/evt_2026_05_31_001_analyzed.json`** — schema bumped to v0.2; all 32 claims backfilled with `claim_group` values for UI demo purposes. Groups: `territorial_control`, `ceasefire_details`, `displacement_policy`, `military_operations`, `humanitarian_situation`, `international_response`, `background_context`.

### Documentation
- **`docs/STAGE_3_4_ANALYZE_ANNOTATE.md`** — schema updated to v0.2; four-tier classification system documented with rules table; `claim_group` documented; all new prompt rules captured.
- **`docs/STAGE_6_FRONTEND.md`** — Pass A section updated to reflect current UI: four classification sections, claim_group sub-headers, `↔` chip layout.
- **`docs/00_MASTER_DOCUMENT.md §12`** — two new design decision entries: contested chip redesign (with rationale against thunderbolt), and claim grouping (rationale, display-only nature of the label).
- **`docs/00_MASTER_DOCUMENT.md §13`** — backlog items B-01 through B-06 logged (pipeline rules extrapolated from M6 content audit).

---

## 4. What the front end looks like now

Run with:
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom/web
npm install   # if node_modules missing
npm run dev   # → http://localhost:3000
```

**Page structure at `/event/evt_2026_05_31_001`:**
- Event header: title, neutral summary, date, source/claim counts
- "What the coverage shows" section:
  - Four collapsible groups, **closed by default**: Agreed, Corroborated (teal), Contested (amber), Single-source (gray)
  - Within each group, claims are sub-grouped by theme (Territorial Control, Ceasefire Details, etc.) under small headers
  - Claim chips: on contested claims, supporting outlets `↔` contesting outlets, both in bias colors
  - Bias spectrum legend at the bottom of this section
- Source provenance cards (2-column grid)
- Light mode locked; typography floor in `00_MASTER_DOCUMENT.md §12`

---

## 5. M6 — What's left

**Definition of done:** Spectrum-spanning readers say the analysis is fair and useful.

**Done this session:**
- Full internal content audit of the analyzed JSON (see findings below)
- Validator questionnaire drafted

**Remaining (G to do):**
1. **Personal read-through** — run `npm run dev`, open the event page, read as a first-time user.
2. **External validators** — share with 2–3 people holding different views on the Israel-Gaza topic:
   - Someone who reads Al Jazeera / follows pro-Palestinian coverage
   - Someone who reads Times of Israel / JNS or follows pro-Israel coverage
   - A centrist who reads Reuters/Bloomberg
3. Use the questionnaire from Session 3 (reproduced below).
4. If feedback surfaces issues → fixes feed back into M3/M4 (prompts, re-run pipeline) or UI.
5. When satisfied → mark M6 Done in TRACKSHEET and proceed to M7.

**Validator questionnaire:**
1. After reading the event page, did it feel like the analysis was playing it straight, or did it seem to favor one side?
2. Look at the "Agreed" section. Do any of these feel like they shouldn't be there — a framing you'd push back on?
3. There are two contested claims. Do the two sides represented feel like a fair characterization of the actual disagreement? Is anything missing?
4. The ownership/funding information is shown for each outlet. Does knowing who owns these outlets change how you read the analysis? Does any ownership description seem inaccurate?
5. Is there a political viewpoint or set of facts you expected to see but didn't?
6. Would you use this? Would it change how you read news on this topic?

**Two contested claims to audit specifically with validators:**
- `clm_015`: "Palestinians view Israel's expanding buffer zone as part of a strategy to permanently displace them" — left/center vs. center-right split
- `clm_023`: "Voluntary emigration vs. ethnic cleansing framing split" — note: clm_023 text was flagged for asymmetric language; if M6 feedback confirms this is an issue, reword and re-run reconcile for this claim.

**Known data issues in current JSON (not fixed — G decided to leave for pipeline re-run):**
- `clm_015`: `src_004` (Reuters) appears in both `supported_by` and `contested_by` — data bug, fixed by B-02 validation in future runs
- `clm_016` and `clm_024`: classified `agreed` but only supported by left-leaning sources — fixed by B-01 classification threshold in future runs

---

## 6. M7 — Generate (next milestone after M6)

**Goal:** Populate the `report` field in the per-event JSON with a structured, reader-facing synthesis grounded in and linked to the claims and provenance already built.

**What the report object looks like** (from `STAGE_5_GENERATE.md` — read that doc before starting M7):
- A set of paragraphs, each tagged with the claim IDs and source IDs it draws from.
- Paragraph `kind`: `agreed` / `contested` / `framing` / `background`.
- Written by Sonnet, strictly source-grounded (no hallucination), with citations woven in.

**Why this matters:** The report is the top layer of the transparency stack. Casual readers get a clean narrative; skeptical readers expand any paragraph to see the underlying claims and provenance. It is the realization of the core product idea.

**Readiness:** M7 can start as soon as M6 is marked Done. The per-event JSON contract (`STAGE_3_4_ANALYZE_ANNOTATE.md v0.2`) is stable. Read `STAGE_5_GENERATE.md` (if it exists) or draft it before implementing.

**Reminder:** The Cowork sandbox cannot call the Anthropic API (SSL-intercepting proxy). Pipeline code can be written and syntax-checked in the sandbox, but `run.py` must be executed locally by G in a terminal.

---

## 7. Working conventions (carry forward)

1. **Tracksheet first and last.** Mark milestone In Progress when starting, Done when finishing. Add change log rows. Upload to Drive via Google Drive MCP.
2. **Drive upload.** Local folder does NOT auto-sync. After updating `TRACKSHEET.xlsx`, always upload via the MCP tools. Parent folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Golden dataset first.** Test pipeline changes against `data/golden/event_001/` before touching live feeds.
4. **Schema is the contract.** Bump `schema_version` if the per-event JSON structure changes; log in tracksheet. Currently at v0.2.
5. **Ask before:** heavy new dependencies, structural repo changes, anything in `00_MASTER_DOCUMENT.md §8` (fixed decisions).
6. **Sandbox can't call Anthropic API.** Any `run.py` must be run locally by G. Code can be written and syntax-checked in the sandbox.
7. **UI design decisions** are in `00_MASTER_DOCUMENT.md §12` — consult before changing colors, fonts, layout, or interaction patterns.
8. **Backlog** is in `00_MASTER_DOCUMENT.md §13` (B-01 through B-06) — pipeline rules to implement on the next full pipeline run.
