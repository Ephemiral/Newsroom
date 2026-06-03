# HANDOVER — Session 2
## News Synthesis & Credibility Engine — Read this before doing anything

**Handover date:** 31 May 2026
**Prepared by:** Claude (Cowork), Session 1
**For:** Claude (Cowork), Session 2
**Owner:** G (GitHub: Ephemiral)

---

## 1. What this project is (60-second version)

A media product that aggregates news coverage of a single event from many outlets across the political spectrum, extracts what they agree on vs. dispute, attaches each source's provenance and bias profile, and generates a transparent, multi-perspectival synthesised report — while preserving the underlying analysis so a reader can verify the synthesis instead of trusting it blindly.

Pipeline: `INGEST → CLUSTER → ANALYZE → ANNOTATE → GENERATE`

Front end: Next.js. Contract between pipeline and UI: a per-event JSON artifact on disk.

**Full architecture is in:** `docs/00_MASTER_DOCUMENT.md` — read it in full if you need background on any decision.

---

## 2. Current status — what is done

| Milestone | Status | Summary |
|-----------|--------|---------|
| M0 — Golden dataset | ✅ Done | 10 articles, 1 event, saved to `data/golden/event_001/` |
| M1 — Ingest | ✅ Done | RSS ingester + dedup + storage + CLI runner |
| M2 — Cluster | ✅ Done | Embedding + threshold clustering; verified 10/10 golden articles → 1 cluster |
| M3 — Analyze | 🔲 Not started | **← CURRENT TASK** |
| M4–M9 | 🔲 Not started | |

**The tracksheet** (`TRACKSHEET.xlsx`) is the live record. It has been updated and uploaded to Google Drive. M0, M1, M2 are marked Done with notes.

---

## 3. What was built — file inventory

```
/Users/gidon/Documents/Claude/Projects/Newsroom/
│
├── docs/                          # All planning docs (copies)
│   ├── 00_MASTER_DOCUMENT.md      ← single source of truth for architecture
│   ├── HANDOVER.md                ← original onboarding doc
│   ├── STAGE_0_GOLDEN_DATASET.md
│   ├── STAGE_1_INGEST.md
│   ├── STAGE_2_CLUSTER.md
│   ├── STAGE_3_4_ANALYZE_ANNOTATE.md  ← defines the per-event JSON schema
│   ├── STAGE_5_GENERATE.md
│   └── STAGE_6_FRONTEND.md
│
├── config/beats/
│   ├── israel_middle_east.json    ← 10 RSS sources + GDELT query
│   └── world_news.json            ← 8 sources (stub, expand at M1)
│
├── data/
│   ├── golden/event_001/
│   │   ├── meta.json              ← event description + article ID list
│   │   └── articles/
│   │       ├── art_001.json  (Al Jazeera — left)
│   │       ├── art_002.json  (Al Jazeera explainer — left)
│   │       ├── art_003.json  (Truthout — left)
│   │       ├── art_004.json  (Reuters/GVWire — center)
│   │       ├── art_005.json  (JNS/Jewish News — center-right)
│   │       ├── art_006.json  (Euronews — center)
│   │       ├── art_007.json  (Bloomberg — center)
│   │       ├── art_008.json  (Times of Israel — center-right)
│   │       ├── art_009.json  (Haaretz — center-left)
│   │       └── art_010.json  (Democracy Now! — left)
│   └── events/
│       └── israel_middle_east/
│           └── evt_2026_05_31_001.json   ← cluster output from M2
│
├── pipeline/
│   ├── schema.py                  ← Article dataclass (shared by all stages)
│   ├── ingest/
│   │   ├── rss.py                 ← feedparser + trafilatura full-text fetch
│   │   ├── store.py               ← URL-normalised dedup + JSON storage
│   │   └── run.py                 ← CLI: --beat / --source golden / --max-per-source
│   └── cluster/
│       ├── embed.py               ← sentence-transformers (all-MiniLM-L6-v2)
│       ├── group.py               ← cosine threshold + connected components
│       └── run.py                 ← CLI: --source golden / --threshold / --manual
│
├── scripts/
│   └── update_tracksheet_m2.py   ← one-off script (already run, can ignore)
│
├── .env.example                   ← key names; copy to .env and fill in
├── .gitignore
└── TRACKSHEET.xlsx
```

---

## 4. The golden dataset — event_001

**Event:** Netanyahu's announcement on 28 May 2026 that he had directed the IDF to expand territorial control of Gaza from ~60% to 70%, going well beyond the October 2025 ceasefire terms.

**Why this event is ideal for the golden dataset:**
- Single concrete statement, one named actor, one date
- Factually bounded (specific percentage figures to verify)
- Framing diverges sharply across the spectrum — from "security operation" to "unlawful annexation"

**Article breakdown:**
- 5 articles have full `body_text` (Al Jazeera x2, Truthout, Reuters, JNS)
- 5 articles have metadata + key facts only (Bloomberg, Times of Israel, Haaretz, Euronews, Democracy Now — paywalled/blocked at collection time)
- All bias ratings are cited to AllSides or MBFC, never invented

---

## 5. The cluster output

File: `data/events/israel_middle_east/evt_2026_05_31_001.json`

```json
{
  "cluster_id": "evt_2026_05_31_001",
  "beat": "israel_middle_east",
  "article_ids": ["art_001", "art_002", "art_003", "art_004", "art_005",
                  "art_006", "art_007", "art_008", "art_009", "art_010"],
  "created_at": "2026-05-31T12:48:34Z",
  "method": "auto",
  "threshold": 0.5,
  "size": 10
}
```

All 10 articles landed in one cluster at threshold 0.50. ✅

---

## 6. The per-event JSON schema (the contract)

Defined in `docs/STAGE_3_4_ANALYZE_ANNOTATE.md`. This is the most important interface in the system. The pipeline writes into it; the Next.js front end reads from it.

**Key fields the M3/M4 stages will populate:**
```json
{
  "schema_version": "0.1",
  "event": { "cluster_id": "...", "beat": "...", "title": "...", "summary": "...", "date": "..." },
  "sources": [
    {
      "source_id": "src_001",
      "outlet": "Al Jazeera English",
      "url": "...",
      "author": "...",
      "published_at": "...",
      "bias_rating": "left",
      "bias_rating_source": "AllSides",
      "ownership": "...",
      "author_background": "...",
      "amplification_signal": null
    }
  ],
  "claims": [
    {
      "claim_id": "clm_001",
      "text": "Neutrally-worded claim",
      "classification": "agreed|contested|single_source",
      "supported_by": ["src_001", "src_004"],
      "contested_by": [],
      "rationale": "Why this classification — reader-facing plain language.",
      "framing_variants": [
        { "source_id": "src_001", "characterization": "How this outlet frames it" }
      ]
    }
  ],
  "background": [{ "point": "Context a reader needs", "sources": ["src_002"] }],
  "report": null
}
```

`report` stays null until M7 (Generate). **Do not change the schema without bumping `schema_version` and logging it in the tracksheet.**

---

## 7. Next task — M3: Analyze

**Stage doc:** `docs/STAGE_3_4_ANALYZE_ANNOTATE.md`

**Definition of done:**
- For the golden event, produces a list of discrete claims, each tagged with the sources that assert it
- Classifies each claim as **agreed**, **contested**, or **single_source**
- Captures framing differences (how outlets characterize the same fact)
- Writes results into the per-event JSON (schema above)

**Approach (from the stage doc):**
- Use Anthropic API, **model-mixed**: Haiku for per-article claim extraction (cheap/bulk), Sonnet for cross-article consensus/divergence reasoning
- Every claim must trace to the article(s) that support it — no claim without a source (anti-hallucination rule)
- "Agreed" means agreed *across different bias ratings*, not just many same-leaning outlets
- Feed articles by `article_id` — load them from `data/golden/event_001/articles/`

**Suggested file layout for M3:**
```
pipeline/analyze/
    extract.py     ← per-article claim extraction (Haiku)
    reconcile.py   ← cross-article consensus/divergence (Sonnet)
    run.py         ← CLI runner; reads cluster JSON, outputs per-event JSON
```

**Output goes to:** `data/events/israel_middle_east/evt_2026_05_31_001_analyzed.json`
(or overwrites the cluster file — keep consistent with how previous stages worked)

**API key:** must be in `.env` as `ANTHROPIC_API_KEY`. Same pattern as `deep-research-reporter` at `/Users/gidon/Documents/deep-research-reporter`.

---

## 8. Decisions already made — do NOT relitigate

These are fixed. If you think one is wrong, raise it with G rather than quietly building something different.

- **Positioning:** transparent & multi-perspectival, NOT "apolitical." Never claim objective neutrality.
- **Architecture:** five-stage hybrid, analysis/annotation artifacts preserved and surfaced, not discarded after report is written
- **Pipeline language:** Python (reuses G's "Deep Research Reporter" patterns)
- **Front end:** Next.js — runs on localhost now, deploys to production with no rewrite
- **Contract between halves:** per-event JSON on disk. No database in the MVP.
- **Beats:** primary = Israel/Middle East, secondary = general world news. Beats are **configuration, not code**
- **Build order:** annotation-first. Phase 1 (ingest→cluster→analyze→annotate→render→validate) before Phase 2 (generate→toggle UI→validate)
- **LLM:** Anthropic API, model-mixed (Haiku for bulk extraction, Sonnet for synthesis). Every claim must trace to a source.

---

## 9. Working conventions

1. **Tracksheet first and last.** Mark the milestone In Progress when you start, Done when you finish. Add a Change Log row. Upload to Drive via the Google Drive connector (the Drive MCP is connected).
2. **Drive upload note.** The Newsroom folder on G's Mac and Google Drive are **not auto-syncing**. After updating `TRACKSHEET.xlsx` locally, always upload it to Drive using the `mcp__0db98f0c...` Google Drive tools. The Newsroom folder's `parentId` on Drive is `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Golden dataset first.** Always build and test against `data/golden/event_001/` before touching live feeds. Use `--source golden` flags.
4. **Schema is the contract.** If you need to change the per-event JSON schema, bump `schema_version` and log it in the tracksheet.
5. **Ask before:** installing heavy new dependencies, changing any decision from section 8, restructuring the repo, or anything touching credentials.
6. **Copyright guardrail.** Full article text is a local dev fixture only — never served to users, never redistributed. The product links out and works from facts.
7. **Bias ratings** are always cited (AllSides/MBFC/GroundNews). Never present a rating as the system's own verdict.
8. **No invented facts.** The report (Stage 5) may only use claims already in the analyzed JSON. Flag empty-support paragraphs for human review.
9. **Secrets in .env only.** Never committed. Same pattern as Deep Research Reporter.

---

## 10. Existing asset to reuse

**Deep Research Reporter** — G's existing working multi-agent pipeline:
- Location: `/Users/gidon/Documents/deep-research-reporter`
- Uses: Anthropic Python library, sequential/parallel agent orchestration, Haiku/Sonnet mixing
- **Reuse its patterns for M3–M5** (especially the model-mixing and prompt structure)

---

## 11. Instructions for G

1. **Open a new chat** in Cowork and paste or attach this document so the new session reads it first.
2. **Make sure your `.env` file exists** at `/Users/gidon/Documents/Claude/Projects/Newsroom/.env` with `ANTHROPIC_API_KEY=your_key_here` — M3 will need it to call the API.
3. **Installed packages** (`sentence-transformers`, `scikit-learn`, `openpyxl`, `feedparser`, `trafilatura`) are already on your Python 3.9 install from this session. You may need `anthropic` for M3: run `python3 -m pip install anthropic` if it's not already there.
4. **Tracksheet on Drive** — the latest version is uploaded. When you open it in Google Sheets, use the most recently modified `TRACKSHEET.xlsx` in your Newsroom folder.
5. **The cluster output file** is at `data/events/israel_middle_east/evt_2026_05_31_001.json` — M3 reads this as its input.
