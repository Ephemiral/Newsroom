# STAGE 3 & 4 — Analyze + Annotate (Milestones 3 & 4)

> **This document defines the canonical per-event JSON artifact** — the contract between the pipeline and the front end. Treat the schema here as authoritative once agreed, and version it. Both Analyze and Annotate write into this one object, so they are documented together.

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_2_CLUSTER.md`.
**Milestones:** M3 (Analyze), M4 (Annotate). **Phase:** 1.

---

## ANALYZE (M3)

### Goal
Take one event cluster and extract its factual structure and its disagreement: what is claimed, by whom, what's agreed across the spectrum, what's contested.

### Definition of done
- For the golden event, produces a list of discrete claims, each tagged with the sources that assert it.
- Classifies each claim using a four-tier system (see Classification Rules below).
- Captures framing differences (how outlets characterize the same fact).
- Assigns each claim to a thematic group (`claim_group`).
- Writes results into the per-event JSON (schema below).

### Approach
- Use the Anthropic API, model-mixed: cheaper model (Haiku) for bulk per-article claim extraction; stronger model (Sonnet) for cross-article consensus/divergence reasoning. (Same cost pattern as Deep Research Reporter.)
- **Every claim must trace to the article(s) that support it.** No claim without a source. This is the anti-hallucination rule and the basis of the whole trust model.

### Classification Rules

| Label | Meaning | Example |
|-------|---------|---------|
| `agreed` | Supported by sources from ≥2 distinct bias tiers that **span** the spectrum — i.e., sources from different sides (e.g. left + center, center + center-right, left + right). Same-side outlets (left + center-left only) do NOT qualify. | A fact reported by both Reuters (center) and Al Jazeera (left) |
| `corroborated` | Supported by multiple sources, but all from the same side of the spectrum. The fact is repeated but not cross-spectrum confirmed. | A figure cited by two left-leaning outlets only |
| `contested` | Sources explicitly contradict each other, OR frame the same fact in genuinely incompatible ways across bias tiers. | One side calls an action "ethnic cleansing"; the other calls it "voluntary emigration" |
| `single_source` | Only one source in the cluster reports this claim. | A specific satellite figure cited by one outlet |

**Why this matters:** "Agreed" carries an implicit claim of cross-ideological consensus. Labeling same-side corroboration as "agreed" overstates confidence and misleads readers about the actual source distribution.

### Claim Grouping (`claim_group`)

Each claim is assigned to a short snake_case thematic group (e.g. `territorial_control`, `ceasefire_details`, `humanitarian_situation`, `military_operations`, `displacement_policy`, `international_response`). Use 4–8 groups per event. The UI uses this field to render claims under collapsible group headers within each classification section. Claims with `claim_group: null` render ungrouped at the end of their section.

### Per-article extraction rules (Haiku — extract.py)

- Each claim must be atomic (one fact per claim).
- Rephrase neutrally; capture the outlet's framing in a separate `characterization` field.
- **For any directive, decision, or policy announcement:** if the article provides the actor's stated justification or reasoning, extract it as a SEPARATE claim. Do not merge the decision with its rationale.

### Cross-article reconciliation rules (Sonnet — reconcile.py)

- A source ID must NOT appear in both `supported_by` and `contested_by` for the same claim. If a source presents both perspectives, place it in `supported_by` only.
- When writing a contested claim describing a framing dispute, use **grammatically parallel language** for both sides. Neither side gets a credibility label ("observers", "experts", "officials") that the other doesn't also receive. Prefer: *"Side A characterizes X as Y; Side B characterizes X as Z."*
- Post-reconciliation validation (in `reconcile.py`) checks these rules automatically and prints warnings if violated. Warnings do not halt the pipeline.

---

## ANNOTATE (M4)

### Goal
Attach the receipts: per-source provenance profiles, and a rationale for each analytic judgment (why a claim is "agreed" vs "contested").

### Definition of done
- A provenance card per source in the event (outlet, link, bias rating + rating source, ownership/funding one-liner, author background if available).
- A rationale object for each claim's classification, written so a reader could check the reasoning.
- (Later / from CIB work) optional coordinated-amplification signal per source.
- All written into the per-event JSON.

### Approach
- Provenance facts (ownership, funding) can be looked up once per outlet and cached in a `sources/` reference store; don't re-derive per event.
- Bias ratings are always cited to their source, never presented as the system's own verdict (Master Doc §7).

---

## CANONICAL PER-EVENT JSON SCHEMA (v0.2)

**Change from v0.1:**
- `claims[].classification` now has four values: `agreed | corroborated | contested | single_source`
- `claims[].claim_group` field added (string | null)

```json
{
  "schema_version": "0.2",
  "event": {
    "cluster_id": "evt_2026_05_xx_001",
    "beat": "israel_middle_east",
    "title": "Neutral, descriptive event title",
    "summary": "1-2 sentence neutral description",
    "date": "2026-05-xx",
    "generated_at": "..."
  },
  "sources": [
    {
      "source_id": "src_001",
      "outlet": "Example Outlet",
      "url": "https://...",
      "author": "Name or null",
      "published_at": "...",
      "bias_rating": "left|center-left|center|center-right|right",
      "bias_rating_source": "AllSides|GroundNews|MBFC",
      "ownership": "One-line ownership/funding note",
      "author_background": "One-line note or null",
      "amplification_signal": null
    }
  ],
  "claims": [
    {
      "claim_id": "clm_001",
      "text": "A neutrally-worded statement of the claim",
      "classification": "agreed|corroborated|contested|single_source",
      "claim_group": "territorial_control",
      "supported_by": ["src_001", "src_004"],
      "contested_by": [],
      "rationale": "Why this classification: e.g. asserted by left, center, and right sources with consistent detail.",
      "framing_variants": [
        { "source_id": "src_001", "characterization": "how this outlet frames it" }
      ]
    }
  ],
  "background": [
    { "point": "Context a reader needs", "sources": ["src_002"] }
  ],
  "report": null
}
```

### Schema rules
- `report` is `null` until Phase 2 (Generate fills it).
- Every `claim.supported_by` / `contested_by` id must exist in `sources`.
- A source id must not appear in both `supported_by` and `contested_by` for the same claim.
- `agreed` requires cross-spectrum support (sources from different sides). Same-side sources → `corroborated`.
- `rationale` is reader-facing — write it plainly, it is what the transparency UI shows.
- Bump `schema_version` on any breaking change and note it in the TRACKSHEET.

## Handoff
Update the TRACKSHEET (M3 and M4 status + change log; record schema_version). One complete per-event JSON for the golden event is the deliverable that unblocks both the front end (M5) and Generate (M7). Proceed to `STAGE_6_FRONTEND.md` for the Phase-1 page.
