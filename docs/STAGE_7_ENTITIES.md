# STAGE 7 — Entity Cards (Milestone M10)

> **Status: DESIGN — pending G's review. No implementation until approved.**
> Extends the "receipts for everything" model from the outlets covering a story (Stage 4 provenance cards) down to the actors inside it. Same discipline, different layer: provenance cards describe the *source*; entity cards describe the *subject*.

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_3_4_ANALYZE_ANNOTATE.md` (the JSON contract), `STAGE_6_FRONTEND.md`.
**Milestone:** M10. **Phase:** 3.
**Schema impact:** per-event JSON v0.4 → v0.5 (additive); new entity-store schema v0.1 (its own version line).

---

## Goal

When transparency mode is on, key entities mentioned in the report (people, organizations, parties, technologies such as weapon systems) become clickable. Clicking one opens a card with grounded, cited background on that entity and an event-specific note on why it matters to this story. Entities **persist and accumulate**: the same person appearing in a second event resolves to the existing record and enriches it — the entity graph gets deeper with every event processed, never reset.

## Definition of done

- A shared entity store at `data/entities/` (git-tracked, deploys with the site) with one JSON per entity plus an alias index.
- A new pipeline stage (`pipeline/entities/`) that runs **after Generate** (it needs the final report text): extract mentions → resolve against the store → ground *new* entities → write `event.entities[]` into the per-event JSON.
- Entity resolution with defined matching logic; low-confidence merges logged for review, never merged silently.
- Every entity fact carries its own citation, timestamps, and confidence tier. No uncited biographical or motive claims — ever.
- Frontend: clickable entity mentions in transparency mode opening a card panel; facts grouped by tier; "updated" marker for returning readers.
- Person-card publish gate decided by G and implemented (see Safety, below).
- Degrades gracefully when B-10 leaves `claim_ids` empty (see B-10 clause).
- `EVENT_SCHEMA_VERSION` bumped to 0.5; tracksheet updated.

## Non-goals (v1)

- `location` entities (allowed by the enum; not extracted in v1 — earn their place later).
- A standalone `/entity/[id]` browse page or "follow this entity" — the schema must not block them; do not build them.
- The `allegation` tier for `person` entities (see Safety). The schema defines it; the pipeline does not mint it in v1.

---

## Approach

### Pipeline placement

```
INGEST → CLUSTER → ANALYZE → ANNOTATE → GENERATE → **ENTITIES** → IMAGE → publish
```

The stage reads the finished per-event JSON (report text, claims, sources, background) and the entity store; it writes `event.entities[]` into the event JSON and creates/updates files in `data/entities/`. Single writer (one scheduler, per §15a) — no concurrency handling needed.

### Steps

1. **Extract (Haiku, 1 call/event).** From report paragraphs + claims + background, list candidate entities: `{surface_forms[], proposed_type, one_line_context}`. Cap at ~8 per event — key actors, not every proper noun. Skip outlets (they are Stage-4's layer).
2. **Resolve (no LLM in the common case).** For each candidate, look up `data/entities/index.json` (normalized alias → `entity_id`):
   - **Exact canonical/alias match + same `type`** → resolve to existing entity.
   - **Partial/fuzzy match** (surname-only, initials, transliteration variants) → one Haiku disambiguation call comparing the candidate's event context against the stored entity's `summary`/`roles_affiliations`. Confidence ≥ high → merge; otherwise **create a new entity and append the pair to `data/entities/review_log.jsonl`** for manual reconciliation. A wrong merge poisons two records; a missed merge is just a duplicate awaiting cleanup — always prefer the second failure.
   - **No match** → new entity.
3. **Ground (new entities only; cached forever after).**
   - Primary: **Wikidata + Wikipedia REST APIs** — free, keyless, structured, and citable (every fact cites the article/revision URL and its retrieval date). Wikidata supplies typed connections (`family_of`, `member_of`, `employed_by`…) with the claim's own reference where present.
   - Fallback (entity absent from Wikipedia): Anthropic web-search tool, restricted to establishing `summary` + `roles_affiliations` from primary/public-record pages; each fact cites the fetched URL.
   - **Hard rule, mirroring the bias-rating rule:** the model never asserts biographical, affiliation, or motive facts from its own training knowledge. If no citable source is found, the field stays empty. Politically sensitive fields (party affiliation, ideological lean, interests in the story) are sourced to the entity's own public record or statements, never inferred.
4. **Relevance (Haiku, 1 call/event).** For each resolved entity, a 1–2 sentence `relevance_to_event`, citing the event's `claim_ids`/`source_ids` it derives from (B-10 clause below when those are empty).
5. **Write.** Update entity files (append-only, see Change discipline), rebuild the alias index, write `event.entities[]`, bump nothing silently — schema versions and the tracksheet record every shape change.

### Entity IDs

`ent_<type>_<slug>` (e.g. `ent_person_benjamin_netanyahu`, `ent_technology_patriot_missile_system`). Slug from the canonical name; numeric suffix on collision. **IDs are immutable once minted** — events reference them the way claims reference `source_id`s.

---

## Entity store schema (v0.1)

`data/entities/{entity_id}.json`:

```json
{
  "entity_schema_version": "0.1",
  "entity_id": "ent_person_example_name",
  "type": "person | organization | political_party | technology | location | other",
  "canonical_name": "Example Name",
  "aliases": ["E. Name", "Example N."],
  "summary": "Neutral, factual, 1–2 sentences. Cited like any fact (summary_sources).",
  "summary_sources": ["https://en.wikipedia.org/wiki/..."],
  "roles_affiliations": [
    {
      "role": "Senior Advisor to the President",
      "org_entity_id": "ent_organization_white_house",
      "start": "2017", "end": "2021",
      "source_url": "https://...", "source_type": "public_record"
    }
  ],
  "connections": [
    {
      "type": "family_of | business_partner_of | employed_by | member_of | ...",
      "entity_id": "ent_person_other_person",
      "note": "optional one-liner",
      "source_url": "https://..."
    }
  ],
  "facts": [
    {
      "fact_id": "fct_001",
      "text": "Atomic, sourced statement.",
      "source_url": "https://...",
      "source_type": "public_record | wire_reporting | own_statement | reference_work",
      "first_reported": "2026-07-08",
      "last_updated": "2026-07-08",
      "confidence_tier": "verified | reported | disputed | allegation",
      "supersedes": null,
      "contradicted_by": null
    }
  ],
  "review_status": "auto | pending_review | approved",
  "first_seen_event": "evt_2026_07_08_israel_middle_east_001",
  "appears_in_events": ["evt_..."],
  "created_at": "2026-07-08T12:00:00Z",
  "last_updated": "2026-07-08T12:00:00Z",
  "change_log": [
    { "date": "2026-07-08", "summary_of_change": "Entity created from evt_...", "source": "https://..." }
  ]
}
```

`data/entities/index.json`: `{ normalized_alias: entity_id }` — the resolution lookup, rebuilt on every write.
`data/entities/review_log.jsonl`: one line per low-confidence resolution or person-card pending review.

### Confidence tiers (mirrors the claims classification discipline)

| Tier | Meaning | Rendering rule |
|---|---|---|
| `verified` | Established across independent sources over time | Plain statement + citation |
| `reported` | Credibly reported, limited corroboration | "Reported by …" attribution visible |
| `disputed` | Subject denies, or credible contradicting reporting exists | Both positions shown, parallel language (B-06 applies here too) |
| `allegation` | Explicitly unproven | Always labeled "allegation" in the rendered text; **never blended into settled facts; not minted for `person` entities in v1** |

Tier transitions (allegation → verified, etc.) are never silent: the old entry stays, the new state links to it (`supersedes`), and the `change_log` records the transition.

### Change discipline (hard requirement)

- **Append-only.** Never overwrite or delete a fact. New information appends; supersession/contradiction links the entries (`supersedes` / `contradicted_by`) and notes it in `change_log`.
- Every fact keeps `first_reported` + `last_updated`.
- `change_log` = `{date, summary_of_change, source}` — powers the reader-facing "updated" indicator.
- The extensible `type` enum: unknown types render as `other` in the frontend — a new type is a non-breaking addition.

---

## Per-event JSON change (v0.4 → v0.5, additive)

New optional `event.entities[]` in the per-event JSON. Old files without it render exactly as today.

```json
"entities": [
  {
    "entity_id": "ent_person_example_name",
    "surfaces": ["Example Name", "Name"],
    "relevance_to_event": "1–2 sentences on why this entity matters to THIS story.",
    "relevance_supports": { "claim_ids": ["clm_003"], "source_ids": ["src_001"] },
    "relevance_grounding": "claims | sources_fallback"
  }
]
```

- `surfaces` are the exact strings that appear in this event's report text. The frontend makes mentions clickable by **surface-string matching within paragraphs** — deliberately not character offsets, which break the moment a report is regenerated.
- The full entity card is read from `data/entities/{entity_id}.json` at render time (the web app already reads `data/` from disk; same pattern).

### B-10 degradation clause (dependency, not assumption)

`claim_ids` on report paragraphs are often empty (open bug B-10). Therefore:
- Relevance grounding tries claims first; when the linkage is missing it falls back to matching the entity's surfaces against `sources[].title`-adjacent fields, `background[]` and the event summary, sets `relevance_grounding: "sources_fallback"`, and the rendered card says *"relevance derived from this event's summary and sources"* instead of listing claim receipts.
- An empty `relevance_supports` never yields an empty or broken card — the entity's store-backed content (summary, roles, facts) does not depend on B-10 at all.

---

## Frontend contract

- **Transparency mode ON:** entity surfaces in report paragraphs render as clickable spans (dotted underline; visually distinct from claim receipts). Mode OFF: plain text, zero visual noise — same philosophy as the existing toggle.
- Clicking opens a **side panel** (desktop) / bottom sheet (narrow): summary → roles/affiliations → connections (linking to other entities' cards) → facts **grouped by confidence tier, tier always visible** → relevance-to-this-event → "Updated <date>" marker.
- **Returning-reader indicator:** `localStorage` records `{entity_id: last_seen_iso}`; entities whose `change_log` has newer entries show an "updated" dot on their span and card. Session-based by design (no accounts, no DB — an account system is a different product decision; this schema doesn't block it).
- Schema-driven only: no hardcoded entity content, unknown `type` values render as `other`, absent `event.entities` renders today's page unchanged.

---

## Safety gate (rigor ≥ Stage 3/4 — these are reader-facing statements about identifiable real people)

1. **No claim about motive, hidden interest, or characterization that isn't directly sourced.** Enforced in the grounding prompt AND by a post-stage validator: any fact without `source_url` is dropped with a warning, never published.
2. **Tiers never blend in the rendered card.** The tier label is always adjacent to the fact text.
3. **`allegation` tier is not minted for `person` entities in v1** (defamation exposure — flagged to G per working rule 6). Revisit with a track record.
4. **Person-card publish gate — ⚠ requires G's decision (conflicts with §15a autonomy):** Master Doc §15a superseded human review by owner decision; this stage recommends restoring it for `person` cards only. Proposed resolution: person entities are created with `review_status: "pending_review"` — the pipeline writes them and events reference them, but the frontend renders a person card **only when `review_status: "approved"`** (an unapproved reference renders as plain text, not a broken card). Review = a human edits the field after reading the card (listed in `review_log.jsonl`). Non-person types default to `auto`. **Autonomy is preserved; person cards ship dark until approved.**

---

## Cost estimate (working rule 8 — flagged before any implementation)

Haiku-only stage; Wikipedia/Wikidata grounding is free. At current Haiku pricing (~$1/MTok in, $5/MTok out):

| Call | When | Rough tokens (in/out) | Cost |
|---|---|---|---|
| Extract | every event | ~6k / 1k | ~$0.011 |
| Disambiguation | ambiguous matches only (~0–2/event) | ~1k / 0.2k each | ~$0.002 |
| Ground + summarize | **new** entities only (~3–6/event cold, →0–1 warm) | ~3k / 0.5k each | ~$0.006 each |
| Relevance | every event | ~5k / 0.8k | ~$0.009 |

**≈ $0.02–0.05/event while the store is cold, settling to ≈ $0.01–0.02/event warm** — roughly 3–10% on top of the ~$0.30–0.70 the Sonnet reconcile+generate stages already cost. Anthropic web-search fallback adds ~$0.01/search only for non-Wikipedia entities. Numbers are estimates; the implementation must log `usage` per call (B-14 pattern) so real figures replace them within a week of running. **Do not implement while the credit-balance situation (§ handover 16) is unresolved.**

---

## Handoff

G reviews this doc → decisions needed: (1) approve/modify the design, (2) the person-card publish gate (§ Safety 4), (3) confirm the no-allegations-for-persons v1 restriction, (4) cost sign-off. On approval: implement `pipeline/entities/`, bump `EVENT_SCHEMA_VERSION` to 0.5, add types + panel to the web app, update TRACKSHEET (M10 status + change log + schema version), then proceed to `STAGE_8_THREADING.md` design — which is **sequenced behind the merge of the semantic-dedup branch** (`claude/ecstatic-dubinsky-bd166c`, task_4517860d): threading extends its `related_events` grouping into a persistent `thread_id`, not a second linkage system.
