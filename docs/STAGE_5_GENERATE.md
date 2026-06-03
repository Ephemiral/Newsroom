# STAGE 5 — Generate (Milestone 7, Phase 2)

> **Do not start this until Phase 1 is validated (M6).** The generated report sits on top of the annotation layer and must be grounded in it.

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_3_4_ANALYZE_ANNOTATE.md`.
**Milestone:** M7. **Phase:** 2.

## Goal

Produce the reader-facing, transparent, multi-perspectival report from the per-event JSON, and write it back into the same JSON's `report` field — with every part of the report linked to the claims/sources that back it.

## Definition of done

- `report` field populated for the golden event.
- The report explicitly distinguishes **agreed facts**, **disputed points**, and **framing differences**.
- **Every report paragraph links to the claim_ids / source_ids it draws from** — this linkage is what powers the toggle/dropdown UI (Stage 6).
- No claim appears in the report that isn't in `claims` (no new facts introduced at generation time).

## Approach

- Use Sonnet for synthesis. Feed it the structured `claims`, `sources`, and `background` — **not** raw article text — so it synthesizes from the analyzed structure, keeping it grounded and reducing copyright surface.
- Require structured output: each report paragraph as an object with its text and the `claim_ids`/`source_ids` it references.
- Explicit instruction to the model: separate what is agreed from what is contested; attribute contested points to who holds them; surface framing differences rather than resolving them.

## Report sub-schema (extends the per-event JSON `report` field)

```json
"report": {
  "schema_version": "0.1",
  "generated_at": "...",
  "paragraphs": [
    {
      "paragraph_id": "p1",
      "text": "Neutral synthesized prose for this paragraph.",
      "supports": { "claim_ids": ["clm_001"], "source_ids": ["src_001","src_004"] },
      "kind": "agreed|contested|framing|background"
    }
  ]
}
```

## Anti-hallucination checks (build these in)

- Validate that every `claim_id`/`source_id` referenced by a paragraph exists.
- Flag any paragraph whose `supports` is empty for human review.
- Human review before publish remains in the loop for the MVP.

## Handoff
Update the TRACKSHEET (M7 status + change log; report schema_version). Proceed to `STAGE_6_FRONTEND.md` to add the toggle UI (M8).
