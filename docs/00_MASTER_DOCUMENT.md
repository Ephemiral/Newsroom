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

## 12. UI Design Decisions (Front End)

Living record of choices made during M5 build and validation. Update when a decision changes.

### Color & bias spectrum

**Decision:** Bias ratings map to a fixed five-color spectrum: Left=blue, Center-left=sky, Center=gray, Center-right=orange, Right=red. Colors are used consistently across source chips, framing variants, and the legend bar.

**Rationale:** Color gives readers instant orientation to the ideological provenance of a claim without requiring them to read every outlet name. The gradient (cool→warm) mirrors the conventional left-right political axis.

**Legend:** A visual spectrum bar (gradient + outlet placement) appears above the claims section on every event page. It doubles as the source overview for the event.

**Alternatives for future consideration:**
- Replace color with icon/shape encoding for accessibility (colorblind-safe)
- Add a Ground News-style "coverage" indicator showing how many sources from each side covered the event
- Source credibility tier (separate from bias) as a second visual dimension

---

### Typography & contrast floor

**Decision (2026-05-31):** Page is locked to light mode. Dark mode is disabled via `color-scheme: light` on the root `<html>` element and by removing the `@media (prefers-color-scheme: dark)` block from `globals.css`.

**Rationale:** Dark mode support requires deliberate per-element contrast decisions. Half-implemented dark mode (inheriting system setting without explicit dark-mode color overrides) produces text that falls below the WCAG AA contrast ratio of 4.5:1 on dark backgrounds. For a credibility product where readability is load-bearing, it's better to ship a well-considered light theme than a broken dark one.

**Typography floor (defined in CSS variables):**
- `--text-secondary` (#4b5563, Tailwind gray-600): body copy, descriptions — minimum for paragraph text
- `--text-tertiary` (#6b7280, Tailwind gray-500): secondary body copy — absolute floor for running text
- `--text-meta` (#9ca3af, Tailwind gray-400): dates, labels, metadata only — never used for content

**Alternatives for future consideration:**
- Proper dark mode pass: define a `[data-theme="dark"]` variant with explicit overrides for every text role, tested against WCAG AA
- System-preference-aware theming with a manual toggle (sun/moon icon in nav)
- Variable font weight to preserve contrast at smaller sizes without lightening color

---

### Source attribution display

**Decision:** Internal source IDs (`src_001`, `src_002`, etc.) are never shown to readers. All source references render as "Outlet Name · DD Mon YYYY" (e.g. "Al Jazeera · 28 May 2026"). Date format uses `toLocaleDateString(undefined, ...)` so it follows the reader's device locale automatically (metric countries get day-first, US gets month-first).

**Rationale:** Internal IDs are implementation artifacts. Readers need outlet name and publication date to evaluate a claim's provenance; they don't need file identifiers.

---

### Contested source chip layout

**Decision (2026-05-31):** On claim cards for contested claims, source chips are split into two groups by a `↔` divider: supporting outlets on the left, contesting outlets on the right. All chips use the outlet's standard bias color — no special color, icon, or border distinguishes contested chips from non-contested ones within each group.

**Rationale:** The original design used a `↯` (thunderbolt) prefix and red styling on contesting chips. This was misleading: in a genuinely contested claim, both sides are presenting their framing — neither side is "more contested" than the other. Marking one side with a warning symbol implied asymmetric credibility. The `↔` divider communicates the tension between positions without privileging either side.

**Alternatives for future consideration:**
- Labeling the two groups ("Reported by" / "Framed differently by") for accessibility clarity.
- Showing the divider only when both groups are non-empty; otherwise rendering all chips flat.

---

### Claim grouping within classification sections

**Decision (2026-05-31):** Within each classification section (Agreed, Corroborated, Contested, Single-source), claims are rendered under thematic sub-headers derived from the `claim_group` field (e.g. "Territorial Control", "Ceasefire Details"). Groups are sorted alphabetically; ungrouped claims (`claim_group: null`) render at the end. If no claims in a section have a group, the section renders flat (backward-compatible with schema v0.1 data).

**Rationale:** A flat list of 20+ claims in a single section is hard to scan. Grouping by theme lets readers find the claims relevant to what they already know, and makes the density of coverage on each sub-topic visible at a glance.

**Group labels are display-only:** the `claim_group` value in the JSON is snake_case (e.g. `territorial_control`); the UI converts it to title case for rendering. The label is never shown to the reader as a classification — it is purely a navigational aid.

**Alternatives for future consideration:**
- Making groups collapsible independently of the parent section.
- Surfacing group-level claim counts alongside the group header.

---

### Report transparency UI (M8)

**Decision (2026-06-01):** The Phase-2 reader experience uses a continuous 2px sidebar bar and a per-paragraph transparency toggle.

**Sidebar bar:** A single unbroken vertical bar runs down the left edge of all Analysis paragraphs. Each segment is colored by the paragraph's `kind` field: agreed=green (#86efac active #16a34a), contested=amber (#fcd34d active #d97706), framing=indigo (#a5b4fc active #4f46e5), background=slate (#cbd5e1 active #64748b). The bar never breaks or gains gaps — expansion does not affect its continuity.

**Transparency toggle:** An indigo pill button ("Show sources" / "Transparency on") in the Analysis section header. When OFF, paragraph text only is shown. When ON: (a) a kind legend row appears beneath the header with tooltips explaining each classification; (b) each paragraph shows its kind badge and a per-paragraph "Show sources" / "Hide sources" button. Each paragraph expands and collapses independently.

**Receipt format (when expanded):** "Supporting claims" rendered as gray bullet points (no colored badges — reduces saturation). "Sources" rendered as pale tinted chips (e.g., left=bg-blue-100 text-blue-700) rather than saturated solid colors. Outlet deduplication: multiple articles from the same outlet show the outlet name only once.

**Rationale:** The original saturated colored badges in both claims and source chips created visual noise when multiple receipts were open simultaneously. Pale tints preserve the bias-spectrum signal without overwhelming the paragraph text. Bullet points for claims reduce badge clutter since classification context is already provided by the kind badge at the paragraph level.

**Alternatives for future consideration:**
- Animate bar segment thickness on expand/collapse to give tactile feedback.
- Allow the transparency toggle to persist across sessions via localStorage.
- Add a "jump to paragraph" index using kind legend as anchor links.

---

## 13. Backlog — Pipeline & Schema Improvements

Logged during M6 validation (2026-05-31). These are not blocking for the current demo; they are targeted fixes for future pipeline runs.

---

### B-01 — Classification threshold: require cross-spectrum diversity

**Problem:** The M3 reconcile step classifies a claim as "agreed" if ≥2 sources support it, regardless of whether those sources all have the same bias rating. This produces claims labeled "agreed" that are actually only corroborated within a single ideological lane (e.g., clm_016, clm_024 — both supported only by left-leaning outlets).

**Rule to implement in `reconcile.py`:**
- `"agreed"` (or future equivalent label) requires sources from **≥2 distinct bias tiers**, where those tiers are not all on the same side of center (i.e., not all left + center-left, not all center-right + right).
- Claims that meet the count threshold but not the diversity threshold should be classified `"corroborated"` instead.
- Within each classification group in the UI, sort claims by number of distinct bias tiers represented (descending) so thin claims sink naturally.

**Note on labeling:** "agreed" vs. "corroborated" may be revisited — the label matters less once each claim card shows a coverage indicator (see B-04). For now, the classification field is the signal.

---

### B-02 — Validation rule: supported_by ∩ contested_by must be empty

**Problem:** In clm_015, Reuters (`src_004`) appeared in both `supported_by` and `contested_by`. A source that presents both perspectives belongs in `supported_by` only; the contested status is established by the *absence* of a view among certain outlet groups.

**Rule to implement as a post-reconciliation validation check:**
```python
for claim in claims:
    assert set(claim["supported_by"]).isdisjoint(set(claim["contested_by"])), \
        f"{claim['claim_id']}: source appears in both supported_by and contested_by"
```
Run this check before writing the JSON artifact. Raise a warning (not a hard failure) so the analyst can decide whether to fix or annotate.

---

### B-03 — Validation rule: rationale must not cite unsupported sources

**Problem:** The clm_016 rationale mentioned Haaretz as providing "implicit support," but Haaretz did not appear in `supported_by`. Rationale text should only reference sources that are formally in `supported_by` or `contested_by`.

**Rule:** Add a post-reconciliation check that parses rationale text for outlet names and flags any that don't appear in the claim's source lists. This is heuristic (outlet names can vary), so implement as a warning, not a hard block.

---

### B-04 — Schema: add `claim_group` field for UI hierarchy

**Problem:** The current schema produces a flat list of claims per classification. Many claims are logically related (e.g., clm_001/clm_002/clm_007/clm_008/clm_009 all concern territorial control figures; clm_006/clm_007/clm_009 all concern the October 2025 ceasefire). Presenting them as a flat list creates noise and repetition.

**Schema change:** Add an optional `claim_group` string field to each claim object:
```json
{ "claim_id": "clm_001", "claim_group": "territorial_control", ... }
```

**Groups observed in event_001 (suggested values):**
- `"territorial_control"` — clm_001, clm_002, clm_007, clm_008, clm_009, clm_010, clm_012
- `"ceasefire_details"` — clm_006, clm_007, clm_009
- `"displacement_policy"` — clm_015, clm_022, clm_023
- `"humanitarian_situation"` — clm_016, clm_027, clm_028
- `"military_operations"` — clm_019, clm_021
- `"international_response"` — clm_026, clm_027, clm_030

**Pipeline change:** Add a grouping pass to `reconcile.py` (or as a separate step) that asks the model to assign each claim to a group. Prompt: *"Group the following claims into 4–8 thematic clusters. Return a JSON object mapping claim_id to a snake_case group name."*

**UI change:** Within each classification section (agreed/contested/single-source), render claims grouped under their `claim_group` header, collapsed by default. Claims without a group render ungrouped at the bottom.

**Schema version:** Bump `schema_version` to `"0.2"` when this field is added.

---

### B-05 — Prompt improvement: extract stated rationale for policy decisions

**Problem:** The M3 extract prompt captures *what* was announced but not *why* — the actor's stated justification. For Netanyahu's 70% directive, the only rationale captured was the audience exchange ("step by step"). The broader strategic reasoning (security rationale, buffer zone doctrine, deterrence framing) was present in sources but not extracted as a distinct claim.

**Rule to add to the M3 extraction prompt:**
> "For any claim describing a directive, policy, or decision, also extract the actor's stated justification or reasoning if present in the source. Treat the stated rationale as a separate claim linked to the decision claim."

---

### B-06 — Contested claim text must use parallel framing

**Problem:** clm_023 used asymmetric language ("observers characterize X as ethnic cleansing; Israeli officials present it as voluntary"), giving one side the credibility signal of "observers" and the other the credibility signal of official attribution.

**Rule to add to the M3 reconcile prompt:**
> "When writing a contested claim that describes a framing dispute between two sides, use grammatically parallel language for both sides. Neither side should receive a label (e.g., 'observers', 'experts', 'officials') that the other side does not also receive. Prefer: 'Side A characterizes X as Y; Side B characterizes X as Z.'"

---

### B-07 — clm_024 misclassified as `agreed` (confirmed single-outlet)

**Problem:** `clm_024` (total death toll >72,000 Palestinians since October 2023) is classified `agreed` but both supporting sources (`src_001`, `src_002`) are Al Jazeera English articles — two pieces from the same outlet. This is effectively a `single_source` claim by outlet. The figure itself originates from the Hamas-run Gaza Health Ministry and has not been independently corroborated by a non-Hamas authority. Presenting it in the "Agreed across the spectrum" section is misleading.

**Fix:** B-01 enforcement in `reconcile.py` will automatically reclassify this on the next pipeline re-run (cross-spectrum diversity check will fail; it will become `single_source` or at most `corroborated`). No manual JSON edit required — leave for the pipeline.

**Note for generate prompt:** The `GENERATE_SYSTEM` prompt already instructs Sonnet to attribute casualty figures to the Gaza Health Ministry (Hamas-run) and note they are unverified by independent sources. This attribution will be present in the regenerated report once the claim is correctly classified.

---

### B-08 — Add `one_sided` paragraph kind; tighten generate stage kind semantics

**Problem:** The generate stage uses four paragraph kinds (`agreed`, `contested`, `framing`, `background`), but "contested" is being applied to two genuinely different situations:
1. Active factual dispute — sources on different sides make opposing claims about the same fact.
2. One-sided coverage — only one ideological lane reported something; the other side's silence is itself informative.

These are distinct signals. Collapsing them into "contested" is misleading: it implies active disagreement where there may be none, and it makes "contested" appear when no claim in the paragraph has a non-empty `contested_by` list. It also means one-sided coverage — one of the product's most valuable signals — has no dedicated label.

**Observed in:** `evt_2026_06_01_065` — paragraphs p4–p9 were labeled `contested` but sourced exclusively from one ideological lane, with no claim having `contested_by` populated.

**Fix:** Add a fifth kind `one_sided` and enforce strict rules for all kinds in the generate prompt. The kind must be derivable from the claim classification data passed to the model.

**Revised kind taxonomy:**

| Kind | When to use | Required evidence |
|------|-------------|-----------------|
| `agreed` | Cross-spectrum factual agreement | `supported_by` spans ≥2 bias tiers on opposite sides of center |
| `contested` | Active factual dispute | At least one cited claim has non-empty `contested_by` |
| `framing` | Same underlying fact, meaningfully different characterization across the spectrum | Claims are `agreed`/`corroborated` but `framing_variants` differ across ideological lines |
| `one_sided` | Only one part of the spectrum reported this; other outlets' silence is informative | All cited claims are `single_source` or `corroborated` within a single ideological lane |
| `background` | Historical/contextual information not tied to breaking facts | N/A |

**Changes required:**
- `pipeline/generate/generate.py` — rewrite `## Paragraph kinds` block in `GENERATE_SYSTEM` with the above table and enforcement rules. Add post-generation validation: warn if any `contested` paragraph cites no claim with `contested_by` non-empty.
- `web/lib/types.ts` — add `'one_sided'` to the `ReportParagraph['kind']` union.
- `web/components/ReportView.tsx` — add `one_sided` to the `KIND` config (color, label, tooltip).
- Report `schema_version` inside the `report` object: bump to `"0.2"` once this change is live.

**UI note:** `one_sided` paragraphs should display a label like "One-sided" with a tooltip explaining that this content was reported by only one part of the political spectrum, and that the other side's choice not to cover it is itself meaningful.

---

### B-09 — Reconciler must not classify a claim as `contested` when `contested_by` is empty

**Problem:** `clm_020` in `evt_2026_06_02_044` is classified `contested` at the claim level, but `contested_by` is empty. The reconciler identified a factual dispute *within the claim text* (Iran said X; US Central Command denied it) rather than between two reporting outlets. Both outlets that cited this claim (BBC News, Euronews) agreed on the facts — they each reported both sides of the Iran/US dispute. There is no outlet-level contradiction, so `contested_by` is correctly empty.

**Impact:** The generate stage then writes a `contested` paragraph backed by a claim with empty `contested_by`. The B-08 validation warns about this, but it slips through. In the UI, the contested receipt shows no `↔` separator — the reader sees a "Contested" badge with no visible contention.

**Fix to implement in `reconcile.py`:**
After classification is complete, add a post-reconciliation guard:
```python
for claim in claims:
    if claim["classification"] == "contested" and not claim["contested_by"]:
        # Reclassify based on source diversity
        if len(set(s.bias_tier for s in claim.sources)) >= 2:
            claim["classification"] = "corroborated"
        else:
            claim["classification"] = "single_source"
```
A `contested` claim with no `contested_by` is a contradiction in terms — it means the model inferred dispute from the claim content rather than from cross-outlet disagreement. These should be `corroborated` (multiple outlets, same fact) or `single_source`.

**Note:** B-08's post-generation validation already warns when a `contested` paragraph cites no claim with `contested_by` populated. B-09 fixes the upstream cause so the warning is never needed.

---

### B-10 — Generate stage: `claim_ids` not populated in report paragraphs

**Problem:** The generate stage returns paragraphs with empty `claim_ids: []`. The model ignores the prompt rule requiring every paragraph to cite at least one `claim_id`. This has two downstream effects: (1) the B-08/B-11 validation cannot check kind consistency because there are no claims to evaluate; (2) the receipt UI cannot show which specific claims back a paragraph.

**Root cause:** The system prompt states the rule, but the model consistently drops citation IDs in the JSON output. The rule was not reinforced strongly enough in the prompt.

**Fix implemented (2026-06-04) in `pipeline/generate/generate.py`:**
- Added a `⚠ CONTESTED_BY STATUS` header in `_build_claims_block()` that explicitly states when no claims have `contested_by` populated, with a bolded instruction not to write any `contested` paragraphs.
- The B-11 enforcement pass (see below) treats empty `claim_ids` as "no evidence" and reclassifies accordingly.

**Remaining gap:** `claim_ids` are still often empty — the prompt fix reduces but may not eliminate this. A future improvement would be to add a second-pass prompt that fills in missing citation IDs after the initial generation.

---

### B-11 — Generate stage: `contested` paragraph kind based on topic, not outlet disagreement

**Problem:** The generate model labels report paragraphs as `kind=contested` because the *subject matter* sounds politically contested (e.g., ceasefire negotiations involve two parties with opposing interests), not because any outlet actually reported a different version of the facts. In `evt_2026_06_04_062` (US-Iran ceasefire), zero claims had `contested_by` populated, yet 4 of 11 paragraphs were labelled `contested`. This misleads the reader into thinking outlets disagreed when they all reported the same facts.

**Root cause:** The model conflates "this topic involves a dispute between actors" with "outlets reported conflicting facts." These are fundamentally different signals. The former is narrative context; the latter is what `contested` is supposed to surface.

**Fix implemented (2026-06-04) in `pipeline/generate/generate.py`:**
- Added `_enforce_paragraph_kinds()` — a post-generation guard that reclassifies `contested` paragraphs as `framing` when: (a) `claim_ids` is empty (no evidence at all), or (b) no cited claim has `contested_by` non-empty. Mirrors B-09 in `reconcile.py`, one layer up.
- Added `⚠ CONTESTED_BY STATUS` warning in `_build_claims_block()` to make the absence of outlet-level disagreement explicit in the prompt context.

**Note:** B-09 fixes this at the claim classification layer. B-11 fixes it at the report paragraph layer. Both guards are needed because the generate model creates paragraph labels independently of claim labels.

---

### B-12 — Cluster step chains unrelated articles into mega-clusters

**Problem:** `auto_cluster()` (`pipeline/cluster/group.py`) uses connected-components grouping over a pairwise cosine-similarity threshold (0.70). This is transitive: if article A is similar enough to B, and B to C, then A/B/C land in one cluster even when A and C are unrelated. Observed on 2026-06-28: a fresh discover run produced a 217-article cluster chaining together dozens of distinct Gaza-related stories purely because they shared beat vocabulary. This pollutes the candidate pool and makes manual candidate selection much harder.

**Root cause:** Single-linkage/connected-components has no mechanism to enforce intra-cluster cohesion. It only requires that each pair of *adjacent* articles in the chain exceeds the threshold — not that the cluster as a whole is coherent.

**Agreed fix — two-part implementation:**

**Part 1 — Replace connected-components with average-linkage** in `pipeline/cluster/group.py`. Rewrite `_connected_components()` so that an article can only join an existing cluster if its *average* cosine similarity to *all current cluster members* meets the threshold (not just one member). The full n×n similarity matrix is already computed by `embeddings @ embeddings.T`, so no additional dot-product cost — the change is only in how that matrix is traversed during grouping. Expected wall-clock impact: modest (a few extra seconds for n=3,000). Expected outcome: eliminates transitive chains; clusters stay topically coherent.

**Part 2 — Add cohesion check post-processing** after clustering. For each produced cluster, compute the mean pairwise cosine similarity across all article pairs. Log a warning (and optionally filter from the candidate display) for any cluster whose mean falls below a floor (e.g., 0.65). This acts as a validation layer to catch any outliers that slip through Part 1.

**Implementation files:**
- `pipeline/cluster/group.py` — rewrite `_connected_components()` with average-linkage logic; add `_check_cohesion()` post-processing.
- No schema changes. No changes to ingest, analyze, annotate, or generate stages.

**Status: ✅ Implemented (2026-06-30, Claude Code session 13).** Unit-tested with a synthetic bridge-article case confirming the old algorithm chained unrelated topics together while the new one correctly keeps them separate. Pending live-data confirmation from G's next discover run.

---

### B-15 — Article store accumulates indefinitely, bloating clustering pool

**Problem:** `ArticleStore.load_all()` in `pipeline/ingest/store.py` returns every article ever ingested — no age filter, no staleness pruning. Each `--discover` run therefore re-clusters the entire historical store alongside today's news. After multiple discover runs (June 1, 4, 28, 29…), the pool grew to thousands of articles spanning weeks. This compounds B-12: the more articles in the pool, the more bridges exist for transitive chaining to exploit.

**Root cause:** `load_all()` is a simple glob over `data/ingested/<beat>/` with no date awareness.

**Agreed fix:** Add `max_age_days: int | None = None` parameter to `ArticleStore.load_all()`. When set, skip any article whose `published_at` is older than `max_age_days` days from the current time. Files remain on disk (dedup integrity is preserved — `_seen_urls` still indexes everything), only the clustering pool is filtered.

Call site in `scripts/scale_test.py` (`run_discover()`) passes `max_age_days=3`. This means each discover run clusters only articles published in the last 3 days — enough to capture fast-developing stories (most stories in this beat ignite and evolve within 24–72h) while keeping the pool lean and coherent.

**Implementation files:**
- `pipeline/ingest/store.py` — add `max_age_days` param to `load_all()`, filter by `article.published_at`.
- `scripts/scale_test.py` — update `store.load_all()` call in `run_discover()` to pass `max_age_days=3`.

**No schema changes. No changes to ingest, analyze, annotate, generate, or frontend.**

**Status: ✅ Implemented (2026-06-30, Claude Code session 13).** `max_age_days=3` wired into `scale_test.py --discover`. Dedup index untouched. Pending live-data confirmation from G's next discover run.

---

### B-13 — Duplicate event clusters polluting the homepage

**Problem:** Multiple discover runs can produce overlapping clusters covering the same news event (e.g. the Smotrich/NY parade appeared three times; the Kuwait airport strike appeared twice). Each cluster becomes a separate event card on the homepage. The result is a noisy feed that undermines credibility — readers see what looks like redundant coverage rather than a curated synthesis.

**Root cause:** There is no deduplication step between cluster creation and the event pipeline. Each discover run creates new cluster IDs even when the underlying stories overlap substantially with clusters from prior runs.

**Fix options to evaluate:**
1. **Pre-run dedup:** Before running a cluster through the full pipeline, check for semantic similarity against existing processed event JSONs and skip if cosine similarity > threshold (e.g. 0.85) on the headline/summary.
2. **Post-run merge:** Allow a human or automated step to mark two event IDs as "same event" and hide one from the frontend (keep the richer one).
3. **Frontend dedup:** Add a `superseded_by` field to the event JSON; the frontend skips cards where this field is set.
4. **Cluster-step dedup:** At discover time, check new cluster article_ids against existing cluster article_ids and discard clusters with high overlap (e.g. >50% shared articles).

**Priority:** Medium — visually noisy but not functionally broken. Fix before public launch. Option 4 (cluster-step dedup) is probably cleanest.

---

### B-14 — Token cost analysis per article/event

**Problem:** We have no visibility into API spend per event — total tokens consumed across analyze, annotate, and generate stages; cost per article; or cost at scale (e.g. 100 events/month). Without this we cannot estimate operating costs, set batch limits, or make informed decisions about model mixing (Haiku vs Sonnet).

**What to measure:**
- Tokens in/out per stage (analyze, annotate, generate) per event
- Cost per event at current Haiku/Sonnet pricing
- Breakdowns: cost per article ingested vs. cost per claim extracted vs. cost per paragraph generated
- Projection: cost at 20 events/week, 50 events/week

**Implementation:** Add token logging to each stage's API calls (the Anthropic client returns `usage` in every response). Aggregate into a `token_log` sub-object in the analyzed JSON or a separate `data/costs/` ledger. Build a simple summary script.

**Priority:** Medium — not blocking M9, but needed before any public launch or cost projection conversation.

---

## 14. Future Considerations (Notes for Review)

These are not backlog items — no action required now. They are questions worth revisiting once the core product is more mature.

---

### B-16 — Reconcile prompt atomizes disputes into separate corroborated claims, hiding contested findings

**Problem:** The reconcile stage (`pipeline/analyze/reconcile.py`) is dramatically under-classifying claims as `contested`. Across 21 processed events, only 5 contested claims exist. This is not because the beat lacks genuine disputes — it is because the model is splitting competing accounts of the same fact into *separate* claims rather than grouping them as one `contested` claim.

**Concrete example (evt_2026_06_04_066 — Kuwait airport):**
- Iran's IRGC: damage was caused by a malfunctioning US Patriot missile interceptor
- US Central Command: Iran deliberately struck the airport with drones

The model produced two separate `corroborated` claims — one for each side's position — each corroborated by the outlets that reported that position. This is factually correct but analytically wrong: it buries the dispute. A reader seeing two separate corroborated facts has no idea they are contradictory. This should be one `contested` claim: "Iran's IRGC claimed the damage was caused by a malfunctioning US Patriot missile; US Central Command and Kuwait attributed the strike directly to an Iranian drone attack."

Same pattern appears across nearly every event involving US-Iran, Israel-UN, or any two-government dispute — the adversarial positions get filed as separate corroborated claims, not as a contested pair.

**Root cause:** The reconcile prompt instruction ("If two sources say contradictory things about the same fact, mark it contested") is correct in principle, but the model interprets it per-claim rather than across-claims. It evaluates each extracted claim in isolation and finds that multiple outlets *do* report each position (making it `corroborated`) — without recognizing that the two positions together constitute a dispute about a single fact.

**Fix — prompt change in `pipeline/analyze/reconcile.py`:**

Add an explicit instruction to the `RECONCILE_SYSTEM` prompt:

> **Disputed facts:** When different sources provide contradictory accounts of the SAME underlying fact (e.g., who caused an event, whether an agreement was reached, what the official figures are, what was said in a meeting), you MUST group all accounts into a SINGLE claim classified as `contested`. Do NOT create separate `corroborated` claims for each side's position — this hides the dispute entirely. The contested claim's `text` should neutrally frame the disagreement as a dispute (e.g., "Iran and the US gave contradictory accounts of responsibility for the Kuwait airport strike"). `supported_by_articles` should list sources holding the majority/initiating account; `contested_by_articles` should list sources holding the minority/contesting account. The rationale should explain both positions in parallel language.

**Expected impact:** Estimated 15–25 currently-`corroborated` claims across the existing 21 events would correctly reclassify as `contested`. The event cards on the homepage would surface the genuine disputes the product is designed to highlight. The generate stage already has B-11 guards to handle `contested` claims properly, so no downstream changes are needed.

**Testing:** Re-run reconcile on evt_2026_06_04_066 (Kuwait airport) and evt_2026_06_28_040 (Strait of Hormuz) with the updated prompt. Both should produce at least 3–5 contested claims each on Iran vs. US responsibility disputes.

**Priority:** High — this is a product-level correctness issue. The site currently looks like nearly everything is "agreed," which is the opposite of the product's value proposition. Fix before external validation or public launch.

**Status update (2026-06-30):** Prompt fix implemented in `RECONCILE_SYSTEM` (the "ACTOR DISPUTES" block). Validated on the 3 test events specified above — and confirmed the model *is* now correctly merging actor disputes into single claims with parallel framing. But the fix is currently being neutralized downstream: `evt_066` and `evt_040` produced **0** contested claims (expected 3–5 each); `evt_062` produced only 1 (expected 2–3). Root cause identified, not yet fixed — see below.

**New finding — conflict with B-02:** B-02 ("a source can't appear in both `supported_by` and `contested_by`; if it presents both perspectives, keep it in `supported_by` only") was written for a different notion of "contested" than B-16 introduces. B-02's model assumes contested = *outlets* diverge in what they report (one outlet's own reporting embodies one side). B-16's actor disputes are different: it's normal and expected for the *same* outlet to responsibly report both sides of a government-vs-government dispute in one article. When that happens, B-02 strips the outlet down to `supported_by` only — and if every outlet covering the dispute reported it that evenhandedly (the journalistically *good* outcome), `contested_by` ends up completely empty. B-09 then (correctly, by its own pre-B-16 logic) demotes the claim away from `contested`, undoing B-16's fix. Confirmed via log trace: 8 of 8 observed B-09 firings across the 3 test events were directly preceded by a B-02 strip that emptied `contested_by`.

**Options under consideration (not yet decided):**
1. Make B-02's strip evidence-preserving — only remove an overlapping source from `contested_by` if doing so leaves `contested_by` non-empty. Cheapest, code-only, no prompt/schema changes. Risk: heuristic patch, doesn't resolve the underlying conceptual conflict.
2. Explicit actor-dispute carve-out in both B-02 and B-16 prompt text, telling the model a source may legitimately appear in both lists for an actor dispute; matching code change to skip the B-02 strip for these claims specifically.
3. Schema-level: introduce a `dispute_type` distinction (coverage-divergence vs. actor-dispute) with different evidence-rendering semantics — actor disputes would show as "Position A (reported by: ...) vs. Position B (reported by: ...)" rather than the existing bias-colored supporting/contesting chip split. Most correct long-term, biggest lift (new schema fields + new UI card layout for this claim subtype).

Leaning toward option 1 as the immediate fix, with 2/3 as later refinements if 1 proves too blunt in practice. **Not yet implemented — decision pending.**

---

### B-17 — Source list has no state-aligned/regional outlets; actor-dispute claims are entirely Western-mediated

**Problem:** All 13 outlets configured for the `israel_middle_east` beat (`config/beats/israel_middle_east.json`) are Western or Israeli: Al Jazeera English, Middle East Eye, Haaretz, The Guardian, BBC, Reuters, Euronews, Ynet, Times of Israel, Jerusalem Post, i24, Arutz Sheva, Israel Hayom. There is no Iranian, Gulf Arab, or other regional-state-aligned outlet in the source list.

**Concrete example (`evt_2026_06_04_062`, clm_005 — "was a deal reached" dispute):** the claim text names "Iran's Tasnim news agency" and named Iranian officials as the source of the Iranian position — but Tasnim itself is not one of our ingested sources. All 7 supporting articles behind this claim are BBC, Reuters, Euronews, and The Guardian. The "Iranian side" of every actor-dispute claim in the dataset is, without exception, a Western outlet's paraphrase of what Iran said — never Iran's own reporting.

**Why this matters beyond B-16:** Even a perfectly working contested-claim pipeline (see B-16) can only be as good as what's in `supported_by`/`contested_by`. Right now those lists can never contain a source that reports the Iranian (or other regional-state) position as its own assertion of fact — only ones that report it as an attributed, hedged claim ("Iran says..."). This is a distinct axis of bias from the existing left/center/right spectrum tracked by `bias_rating` — it's a *geographic/state-alignment* gap baked into the beat config from the start.

**Tension to resolve before fixing:** the obvious candidates (PressTV, Tasnim News, IRNA, Mehr News) are state-controlled mouthpieces, not independent press. For most news products that's disqualifying. For *this* product, transparently labeled state-controlled sourcing might be a feature rather than a bug — "this is verbatim what the Iranian government's own outlet said" is arguably more transparent than a Western outlet's third-hand summary, provided the reader is shown unambiguously what kind of source it is (e.g. an `ownership: "Iranian state-controlled"` provenance card rather than treating it as just another point on the left-right bias spectrum). Practical concerns to weigh: RSS/access reliability (sanctions-adjacent hosting), English-language availability, and whether `bias_rating` (currently a left-right scale) is even the right field to represent "state mouthpiece" — it may need its own categorical flag separate from the political spectrum.

**Not yet scoped or implemented — flagged for G's decision** on whether/how to proceed, given the credibility tradeoffs above.

**Priority:** Medium — doesn't block B-16's resolution (the evidence-model conflict needs fixing regardless, on the existing source list), but caps how much B-16's fix can actually achieve until addressed.

---

### FC-02 — Single-outlet clusters as a "Breaking / Developing" signal

**Background:** During M9 scale testing (2026-06-30), discover runs frequently produced large clusters made up entirely of articles from a single outlet (e.g. 60 articles from Israel Hayom, 11 from Euronews). These are currently filtered out of the candidate pool (minimum 3 distinct outlets required to be shown). However, they represent two meaningfully different phenomena worth distinguishing and potentially surfacing:

**Case 1 — Timing artifact (genuine breaking news):** One outlet breaks a story and others haven't caught up yet. If you re-run discover 6–12 hours later, the cluster would have multiple outlets. The single-outlet cluster is a lag signal, not a real editorial gap. A "Check back later" or "Developing" label would be appropriate here.

**Case 2 — Lane-specific coverage:** A story resonates strongly within one ideological lane but is genuinely ignored by others. For example, a domestic Israeli political story saturating Israel Hayom, Ynet, and Arutz Sheva but absent from Al Jazeera and The Guardian. This is not a timing artifact — it's a substantive editorial divergence. The `one_sided` paragraph kind in our schema is designed to surface this *after* a story is processed, but these single-outlet clusters surface it *before* — as a raw signal that something is being covered in one lane and not others.

**Why this matters for Critiqal:** The product's purpose is to surface not just what outlets agree/disagree on, but *what they choose to cover at all*. Lane-specific saturation (Case 2) is exactly the kind of signal a transparency-first news product should surface. It's a different product feature than the main synthesis pipeline — more of an editorial dashboard or alert layer.

**Potential implementation directions (not yet scoped):**
- At discover time, flag single-dominant-outlet clusters with a `signal_type: "developing"` or `"lane_specific"` field rather than discarding them.
- Build a lightweight pre-pipeline alert surface: "X is covering [topic] heavily; no other outlets reporting yet."
- Use outlet recurrence over time (same outlet cluster appearing across multiple discover runs) to distinguish Case 1 (disappears when others catch up) from Case 2 (persists as lane-specific).

**Connection to existing features:** Case 2 maps directly to the `one_sided` paragraph kind (§5, schema v0.2). The `one_sided` kind flags paragraphs where only one ideological lane reported a fact. Single-outlet discover clusters are the same signal one step earlier in the pipeline. A future version could automatically flag discovered clusters as `one_sided_candidate` before running them through analyze/annotate/generate.

**This is not a current backlog item** — no action required during M9. Revisit when scoping post-M9 product features.

---

### FC-01 — Official statement sourcing and claim provenance types

**The question:** When a paragraph contains an official statement by a government entity (e.g. "The Israeli Defence Ministry condemned the move as a 'disgraceful decision'"), should the pipeline attempt to source that statement directly — linking to a press release or official channel — rather than relying solely on news outlet reporting?

**Why this is worth thinking about:** A primary source (the actual press release or official channel) is more authoritative than a news outlet's paraphrase. For a credibility product, primary sourcing is the gold standard. The concern is legitimate.

**Why it is not a current requirement:** Many official statements in this beat are made at press conferences, in Hebrew or Arabic, or are released to Israeli press only — there is often no English-language press release URL to link to. More fundamentally, the pipeline's model is meta-coverage: it shows readers what outlets reported and how their coverage differs. Adding a primary source verification layer would be a different product with significantly higher infrastructure cost.

**The existing mechanism handles accountability adequately for now:** Claims are attributed to the outlets that reported them; readers can click through to the original article. The generate prompt already requires verbatim quotes where available (from `framing_variants`), which reduces the risk of unattributed paraphrase.

**The right future enhancement, if revisited:** Add a `source_type` field to the claim schema distinguishing between "journalist-reported fact," "attributed official statement," "primary document cited," and "statistics from official body." This would let the UI flag paragraphs containing attributed official statements without requiring primary source links. It preserves the existing pipeline model while surfacing the indirect sourcing as a signal readers can assess. Worth considering as a schema addition (alongside a schema version bump) once external validation has run and the core loop is proven.

---

## 11. Existing Assets to Reuse

- **Deep Research Reporter** — working multi-agent pipeline (Anthropic Python lib, sequential/parallel agents, Haiku/Sonnet mixing). At `/Users/gidon/Documents/deep-research-reporter`, pushed to GitHub (Ephemiral). Reuse its orchestration patterns for stages 3–5.
- **rotter.net CIB detection engine** — separate project; directly relevant to the Analyze stage (coordinated-amplification signals).
