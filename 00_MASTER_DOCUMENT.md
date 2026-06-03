# MASTER DOCUMENT
## News Synthesis & Credibility Engine (working title)

> **Read this first.** This is the single source of truth for the project. Anyone — a human collaborator, Claude Code, or Claude Cowork — should be able to read this document and understand what the project is, why it exists, how it is architected, and what to build next. If you only read one file, read this one. Then consult the per-stage instruction docs (`STAGE_*.md`) for implementation detail, and keep `TRACKSHEET` updated as you go.

**Last updated:** 31 May 2026
**Owner:** G (GitHub: Ephemiral)
**Status:** Pre-build. Architecture and plan defined. No pipeline code written yet.

---

## 1. Mission & Vision

**Mission:** Assist people in critical thought when consuming news and media.

**Vision:** A media product that, instead of adding another voice with its own political lean, aggregates reporting from as many outlets as possible, juxtaposes how each covers an event, and surfaces the *structure of agreement and disagreement* so readers can think for themselves.

**Core insight:** The problem is not only bias and misinformation. It is that readers cannot easily see the *shape* of the disagreement. This product makes that shape visible and transparent.

**Guiding principle — transparent & multi-perspectival, NOT "apolitical":** The product does not promise objective truth. It promises transparency and multiple perspectives. It shows what sources agree on, where they diverge, who is saying what, and each source's track record. This is more honest, more defensible, and more aligned with the mission than any claim of neutrality. (Reasoning: true neutrality is unachievable and invites attack from all sides; bias hides in selection and omission; an LLM inherits its sources' slant; the "hostile media effect" means every reader perceives "neutral" output as biased against them.)

---

## 2. What the Product Does

For a single news event, the system:
1. Ingests coverage from many outlets across the political spectrum.
2. Produces a **synthesized report** separating: facts all sources agree on, disputed points, and differences in framing.
3. Produces a **provenance breakdown**: which outlets, each outlet's bias/credibility profile, ownership/funding, author background.
4. Adds **background/context** to help the reader understand the developing story.
5. Preserves and surfaces the **analysis and annotations** that produced the report, so the reader can verify the synthesis instead of trusting it on faith.

---

## 3. Target Architecture — The Hybrid Model

The product is a single pipeline combining two models (a synthesis outlet and a credibility/annotation layer):

```
INGEST  ->  CLUSTER  ->  ANALYZE  ->  ANNOTATE  ->  GENERATE
```

The final output is a transparent, multi-perspectival report. **Critically, the analysis and annotation artifacts are NOT discarded once the report is written.** They are preserved and surfaced to the reader, in or beside the final report. The annotations are the "proof of work" that lets a skeptical reader verify neutrality. The report is the top layer of a transparent stack: casual readers take the report; skeptical readers expand the receipts and drill down.

### Stage definitions

| Stage | Input | Output | Purpose |
|---|---|---|---|
| **1. Ingest** | Source list (RSS/APIs) | Raw articles (stored) | Pull coverage of events from many outlets |
| **2. Cluster** | Raw articles | Articles grouped per event | Decide which articles describe the same event |
| **3. Analyze** | One event cluster | Claims tagged by source; consensus vs divergence; per-source credibility/bias | Extract the factual structure and the disagreement |
| **4. Annotate** | Analysis output | Provenance cards + rationale objects | Attach the receipts: who said what, source profiles, why something is "agreed" vs "disputed" |
| **5. Generate** | Analysis + annotations | Transparent multi-perspectival report (+ linked annotations) | Write the reader-facing report, grounded in and linked to the receipts |

### System shape (two halves, clean separation)

- **Pipeline (Python):** stages 1–5 produce a single structured **JSON artifact per event**. This is the contract between the two halves.
- **Front end (Next.js / React):** reads the per-event JSON and renders the report plus the expandable annotation layer. Knows nothing about how the JSON was produced.

This separation means the pipeline and the front end can be built and tested independently, and either can be swapped without touching the other.

### The per-event JSON artifact (the contract)

This is the most important interface in the system. Both halves depend on it. A first-draft schema lives in `STAGE_3_4_ANALYZE_ANNOTATE.md` and must be treated as the canonical contract once agreed. Keep it versioned.

---

## 4. Technology Decisions (with rationale; overridable)

- **Pipeline language: Python.** Reuses the existing Deep Research Reporter codebase and patterns (Anthropic Python library, multi-agent sequential/parallel orchestration, Haiku/Sonnet model mixing for cost/rate-limit control). Strongest ecosystem for ingestion, embeddings, clustering.
- **Front end: Next.js (React).** Requirement was: run on localhost now, but don't force a rewrite to look professional later. Next.js runs locally with one command, deploys to production (e.g. Vercel) with no rewrite, is what high-end news/web UIs are actually built on, and makes the toggle/dropdown-per-paragraph UI natural. Tradeoff: marginally more setup than a static HTML file, which is the price of the no-rewrite guarantee.
- **Artifact format between halves: JSON files on disk** (for the MVP). Simple, inspectable, version-controllable. A database is out of scope until after the core loop is proven.
- **LLM: Anthropic API**, model-mixed (Haiku for cheap/bulk extraction, Sonnet for synthesis). Source-grounded generation with citations to control hallucination.

> Any of these can be changed. If you change one, update this section and the TRACKSHEET so the decision and its reason stay recorded.

---

## 5. Beats (Coverage Domains)

Two beats at launch:
- **Primary: Israel / Middle East.** Deepest existing source instincts (see rotter.net CIB work), wide and well-documented bias spread, high coverage volume.
- **Secondary: General world news.** Broader applicability, proves the system generalizes.

**Design requirement:** a beat must be a *configuration* (source list + a few parameters), not code. Adding or swapping a beat should never require touching pipeline logic. See `STAGE_1_INGEST.md` for the beat-config format.

---

## 6. The Reader-Facing UI (current leading design)

The page shows the **final synthesized report by default**. A **toggle at the top of the page** switches on transparency mode: each paragraph of the report becomes an expandable dropdown; opening a paragraph reveals the sources behind it and the rationale for how that part was synthesized. Default reading stays clean; full transparency is one tap away.

(Open design question — kept as the leading direction, not finalized. Alternative considered: inline expandable citations vs. a side-by-side panel.)

---

## 7. Barriers & Mitigations (carry these into every stage)

- **Copyright / licensing.** Aggregating and synthesizing others' reporting carries real exposure (hot-news doctrine, derivative works, scraping ToS). *Mitigation:* lean on facts (not copyrightable) over expression; link out rather than reproduce; never store/serve full article text beyond what's needed internally; pursue licensing later.
- **Cost & latency.** Multi-article LLM synthesis at news velocity is expensive. *Mitigation:* model mixing, aggressive caching, batch cheap extraction.
- **Trust / perceived neutrality.** One viral accusation of slant can sink the brand. *Mitigation:* the annotation layer is the primary defense — make the receipts always available.
- **Contested bias ratings.** Where ratings come from and how they're justified is itself a defensibility question. *Mitigation:* cite the rating source (AllSides/Ground News/MBFC), never present a rating as your own objective verdict.
- **Hallucination.** A synthesis that invents a claim is catastrophic for a truth product. *Mitigation:* source-grounded generation, every claim traceable to a source, human review before publish in the MVP.

---

## 8. Build Sequence (annotation-first)

Build in the order the data flows, and prove trust before generating.

**PHASE 1 — Annotation/analysis layer first.** Lower legal risk (describe + link, not generate prose), leans on existing CIB work, shippable on its own, and is the exact input the generate stage needs.
- Stages: Ingest → Cluster → Analyze → Annotate → render an annotated-analysis page (no generated report yet).
- Validate: do readers across the spectrum trust this layer?

**PHASE 2 — Add Generate on top.** Bolt on the synthesis report once the annotation layer is solid. The receipts are already there to back it. Implement the toggle/dropdown UI.

**Milestone 0 (do this first):** Pick the primary beat's event and build a **golden dataset** — manually collect 8–12 articles across the spectrum covering one real event, saved to disk. Everything downstream is built and tested against this fixture, so you never debug against a live, shifting feed. See `STAGE_0_GOLDEN_DATASET.md`.

---

## 9. Milestones (summary; full detail and live status in the TRACKSHEET)

| # | Milestone | Phase | Definition of done |
|---|---|---|---|
| M0 | Golden dataset | Setup | 8–12 articles for 1 event saved with metadata; beats configured |
| M1 | Ingest | 1 | Pipeline pulls articles for a beat into stored raw form |
| M2 | Cluster | 1 | Articles auto-grouped into event clusters; golden event reconstructed |
| M3 | Analyze | 1 | Per-event JSON: claims-by-source, consensus vs divergence |
| M4 | Annotate | 1 | Provenance cards + rationale added to the JSON |
| M5 | Phase-1 page | 1 | Next.js page renders the annotated analysis for the golden event |
| M6 | Validate Phase 1 | 1 | Spectrum-spanning readers say the analysis is fair/useful |
| M7 | Generate | 2 | Report added to JSON, grounded in + linked to annotations |
| M8 | Toggle UI | 2 | Report-by-default page with per-paragraph expandable receipts |
| M9 | Validate Phase 2 | 2 | Readers find the synthesis fair; 20–30 events processed |

---

## 10. Document Map & Working Rhythm

- **`00_MASTER_DOCUMENT.md`** (this file) — complete overview. Update when a *decision* changes.
- **`TRACKSHEET`** (spreadsheet in Drive) — live status of every milestone, plus a change log. Update **every working session**.
- **`STAGE_0_GOLDEN_DATASET.md`** — Milestone 0 instructions.
- **`STAGE_1_INGEST.md`** — ingestion + beat-config format.
- **`STAGE_2_CLUSTER.md`** — event clustering.
- **`STAGE_3_4_ANALYZE_ANNOTATE.md`** — analysis + annotation; **defines the canonical per-event JSON schema**.
- **`STAGE_5_GENERATE.md`** — report generation (Phase 2).
- **`STAGE_6_FRONTEND.md`** — Next.js front end + toggle UI.

**Working rhythm:** pick the current milestone from the TRACKSHEET → open that stage's instruction doc → build only that stage against the golden dataset → update the TRACKSHEET (status + change log) → move to the next. Work one stage at a time.

---

## 11. Existing Assets to Reuse

- **Deep Research Reporter** — working multi-agent pipeline (Anthropic Python lib, sequential/parallel agents, Haiku/Sonnet mixing). At `/Users/gidon/Documents/deep-research-reporter`, pushed to GitHub (Ephemiral). Reuse its orchestration patterns for stages 3–5.
- **rotter.net CIB detection engine** — separate project; directly relevant to the Analyze stage (coordinated-amplification signals).
