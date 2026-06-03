# HANDOVER — Session 3
## News Synthesis & Credibility Engine
**Handover date:** 31 May 2026
**Prepared by:** Claude (Cowork), Session 2
**For:** Claude (Cowork), Session 3
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
| M5 — Phase-1 page | ✅ Done | Next.js app in `web/`; UI polish applied (see §4) |
| M6 — Validate Phase 1 | 🔲 Not started | **← CURRENT TASK** — see §5 |
| M7–M9 | 🔲 Not started | |

**TRACKSHEET.xlsx** is the live record. Updated locally and uploaded to Drive (folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`). Use the most recently modified version in Drive.

---

## 3. File inventory (what was built)

```
/Users/gidon/Documents/Claude/Projects/Newsroom/
│
├── docs/
│   ├── 00_MASTER_DOCUMENT.md      ← architecture + UI design decisions (§12)
│   ├── STAGE_3_4_ANALYZE_ANNOTATE.md  ← per-event JSON schema (the contract)
│   └── STAGE_6_FRONTEND.md
│
├── data/
│   ├── golden/event_001/          ← 10 articles, Netanyahu 70% Gaza announcement
│   ├── events/israel_middle_east/
│   │   └── evt_2026_05_31_001_analyzed.json  ← COMPLETE per-event JSON (M3+M4)
│   └── sources/
│       ├── outlet_provenance.json  ← curated ownership facts for 10 outlets
│       └── author_cache.json       ← Haiku author background cache
│
├── pipeline/
│   ├── schema.py
│   ├── ingest/        (M1)
│   ├── cluster/       (M2)
│   └── analyze/       (M3 — extract.py, reconcile.py, run.py)
│   └── annotate/      (M4 — provenance.py, run.py)
│
└── web/               (M5 — Next.js App Router)
    ├── app/
    │   ├── page.tsx               ← event index
    │   └── event/[id]/page.tsx    ← event detail page
    ├── components/
    │   ├── BiasLegend.tsx         ← spectrum bar + outlet placement
    │   ├── ClaimSection.tsx       ← collapsible group (closed by default)
    │   ├── ClaimCard.tsx          ← expandable claim + framing variants
    │   └── SourceCard.tsx         ← provenance card
    └── lib/
        ├── types.ts               ← TypeScript types for the JSON schema
        └── data.ts                ← reads analyzed JSON from disk
```

---

## 4. What the front end looks like now (M5 state)

Run with:
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom/web
npm install   # if node_modules missing
npm run dev   # → http://localhost:3000
```

**Page structure at `/event/evt_2026_05_31_001`:**
- Event header: title, neutral summary, date, source/claim counts
- "What the coverage shows" section:
  - Three collapsible groups, **closed by default**: Agreed (21), Contested (2), Single-source (9)
  - Group headers show the numeric count in the accent colour instead of a dot
  - Clicking a group expands it; clicking a claim within it shows rationale + framing variants
  - Bias spectrum legend at the bottom of this section (blends with page background, left-aligned outlet names)
- Source provenance cards (2-column grid)
- Light mode locked (no dark mode); typography floor documented in `00_MASTER_DOCUMENT.md §12`

---

## 5. Next task — M6: Validate Phase 1

**Definition of done:** Spectrum-spanning readers say the analysis is fair and useful.

**What to do:**
1. Run `npm run dev` in `web/`, open the event page, and do a personal read-through
2. Share the running page with 2–3 people holding different views on the Israel-Gaza topic (one who'd read Al Jazeera, one who'd read Times of Israel, one centrist). Ask: "Does this feel like it's playing it straight?" and "Do the agreed/contested distinctions seem accurate?"
3. If validation surfaces issues, fixes feed back into M3/M4 (adjust prompts, re-run pipeline) or M5 UI
4. If satisfied, mark M6 Done in tracksheet and proceed to M7 (Generate)

**The two contested claims to audit specifically:**
- `clm_015`: "Palestinians view Israel's expanding buffer zone as part of a strategy to permanently displace them" — left/center vs. center-right split
- `clm_023`: "Voluntary emigration vs. ethnic cleansing framing split" — left labels it ethnic cleansing, center/center-right uses Israeli framing

---

## 6. Working conventions (carry these forward)

1. **Tracksheet first and last.** Mark milestone In Progress when starting, Done when finishing. Add change log rows. Upload to Drive via Google Drive MCP.
2. **Drive upload.** Local folder does NOT auto-sync. After updating `TRACKSHEET.xlsx`, always upload via the MCP tools. Parent folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Golden dataset first.** Test pipeline changes against `data/golden/event_001/` before touching live feeds.
4. **Schema is the contract.** Bump `schema_version` if the per-event JSON structure changes; log in tracksheet.
5. **Ask before:** heavy new dependencies, structural repo changes, anything in `00_MASTER_DOCUMENT.md §8` (fixed decisions).
6. **Sandbox can't call Anthropic API.** The Cowork sandbox is behind an SSL-intercepting proxy. Any `run.py` that calls the API must be run locally by G in a terminal. Code can be written and syntax-checked in the sandbox.
7. **UI design decisions** are in `00_MASTER_DOCUMENT.md §12` — consult before changing colors, fonts, or dark mode.
