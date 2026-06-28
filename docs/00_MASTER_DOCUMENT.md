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

## 14. Future Considerations (Notes for Review)

These are not backlog items — no action required now. They are questions worth revisiting once the core product is more mature.

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
