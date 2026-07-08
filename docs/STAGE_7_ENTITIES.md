# STAGE 7 — Entity Cards (Milestone M10)

> **Status: APPROVED by G (2026-07-08) with modifications. Ready to implement once Anthropic credits are confirmed topped up.**
> Extends the "receipts for everything" model from the outlets covering a story (Stage 4 provenance cards) down to the actors inside it. Same discipline, different layer: provenance cards describe the *source*; entity cards describe the *subject*.
>
> **G's approval modifications (2026-07-08):**
> 1. Each card carries an **openly-licensed image** of the entity (portrait / logo / place photo), reusing the Stage-15b image discipline (attribution mandatory).
> 2. **`location` is a first-class entity type in v1** (not deferred) — a place is extracted when its strategic/geographic significance helps the reader understand the story (e.g. why an attack on *Bushehr* or a closure of the *Strait of Hormuz* matters).
> 3. **No human-review bottleneck.** Person cards publish automatically like the rest of the pipeline (§15a autonomy preserved). The safety net is machine-enforced instead: a fact/allegation about a person **cannot publish unless it has both a source link AND a tier label**.
> 4. **`allegation` tier is allowed for people** — but only when attributed to a named outlet/source **with a link** and labeled as an allegation. The system reports *"Outlet X alleged Y"* (attributed meta-coverage), never asserts it in its own voice.

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_3_4_ANALYZE_ANNOTATE.md` (the JSON contract), `STAGE_6_FRONTEND.md`.
**Milestone:** M10. **Phase:** 3.
**Schema impact:** per-event JSON v0.4 → v0.5 (additive); new entity-store schema v0.1 (its own version line).

---

## Goal

When transparency mode is on, key entities mentioned in the report (people, organizations, parties, technologies such as weapon systems, and **strategically significant locations**) become clickable. Clicking one opens a card with grounded, cited background on that entity — including **an image of it** — and an event-specific note on why it matters to this story. Entities **persist and accumulate**: the same person appearing in a second event resolves to the existing record and enriches it — the entity graph gets deeper with every event processed, never reset.

**Locations (per G, 2026-07-08):** a place earns a card when knowing *why the place matters* changes how the reader understands the event — a nuclear/industrial site (Bushehr), a shipping chokepoint (Strait of Hormuz), a contested border town, a capital under attack. Ordinary dateline locations with no bearing on the story's significance are not extracted. The card answers "why here?" — strategic, economic, or symbolic significance — sourced like any other fact.

## Definition of done

- A shared entity store at `data/entities/` (git-tracked, deploys with the site) with one JSON per entity plus an alias index.
- A new pipeline stage (`pipeline/entities/`) that runs **after Generate** (it needs the final report text): extract mentions → resolve against the store → ground *new* entities → write `event.entities[]` into the per-event JSON.
- Entity resolution with defined matching logic; low-confidence merges logged for review, never merged silently.
- Every entity fact carries its own citation, timestamps, and confidence tier. No uncited biographical or motive claims — ever.
- Each entity has an **openly-licensed image** where one exists (Wikidata `P18` → Commons), with stored, rendered attribution; `null` otherwise.
- **`location` extracted as a first-class type** when a place's significance bears on the story ("why here?").
- Machine-enforced person-content safety (source link + tier label required to publish; attributed allegations only) — no human review step.
- Frontend: clickable entity mentions in transparency mode opening a card panel with image, facts grouped by tier, and an "updated" marker for returning readers.
- Degrades gracefully when B-10 leaves `claim_ids` empty (see B-10 clause).
- `EVENT_SCHEMA_VERSION` bumped to 0.5; tracksheet updated.

## Non-goals (v1)

- A standalone `/entity/[id]` browse page or "follow this entity" — the schema must not block them; do not build them.
- A human review queue / approval workflow — per G, person cards publish automatically (the source-link + tier-label enforcement is the safeguard).

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
   - Primary: **Wikidata + Wikipedia REST APIs** — free, keyless, structured, and citable (every fact cites the article/revision URL and its retrieval date). Wikidata supplies typed connections (`family_of`, `member_of`, `employed_by`…) with the claim's own reference where present. For locations, Wikidata also yields coordinates and instance-of type (military base, nuclear facility, strait…) that seed the "why here?" significance note.
   - **Image (per G):** take Wikidata's image property (`P18`) → the file on Wikimedia Commons, and record its license + credit from the Commons API. Reuses the exact license discipline of Stage 15b (`pipeline/images/`): only CC0/CC BY/CC BY-SA/public-domain accepted, attribution stored and mandatory to render. If there is no openly-licensed image, `image` is `null` (the card renders fine without one). **Person portraits are the entity's own identifying photo** — the Stage-15b "identifiable person disqualifies" rule is an *event-image* rule and does not apply here (the person is the subject).
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
  "image": {
    "url": "https://upload.wikimedia.org/...",
    "source_page": "https://commons.wikimedia.org/wiki/File:...",
    "credit": "Photographer / uploader",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "provider": "Wikimedia Commons",
    "fetched_at": "2026-07-08T12:00:00Z"
  },
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
| `allegation` | Explicitly unproven | Always labeled "allegation" in the rendered text; **never blended into settled facts. Allowed for people (per G) only when attributed to a named source with a link** — the card shows *"Alleged by [outlet] →"*, never the system's own assertion |

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
- Clicking opens a **side panel** (desktop) / bottom sheet (narrow): **image** (when present, with its credit line — a license requirement, same as event images) → summary → roles/affiliations → connections (linking to other entities' cards) → facts **grouped by confidence tier, tier always visible** → relevance-to-this-event → "Updated <date>" marker.
- **Returning-reader indicator:** `localStorage` records `{entity_id: last_seen_iso}`; entities whose `change_log` has newer entries show an "updated" dot on their span and card. Session-based by design (no accounts, no DB — an account system is a different product decision; this schema doesn't block it).
- Schema-driven only: no hardcoded entity content, unknown `type` values render as `other`, absent `event.entities` renders today's page unchanged.

---

## Safety gate — machine-enforced (per G's 2026-07-08 decision: no human bottleneck; the enforcement below is the safeguard)

Rigor ≥ Stage 3/4 — these are reader-facing statements about identifiable real people. A post-stage validator runs on every entity before the event publishes; a `person` fact failing any check is **dropped** (not published), and if that leaves the card empty of facts the entity still renders as plain text, never a broken card.

1. **Every fact carries a source link.** Any fact (any tier) without a `source_url` is dropped with a warning — never published. This is the load-bearing rule; it is what makes automatic publishing of person content acceptable.
2. **Every fact carries a tier label**, and **tiers never blend** in the rendered card — the label is always adjacent to the fact text.
3. **`allegation` about a person = attributed meta-coverage only.** An `allegation`-tier fact on a `person` must have `source_type` naming an outlet/external source and a working link; the card renders it as *"Alleged by [source] →"*. The system never states an allegation about a person in its own voice, and never promotes `allegation` → `verified`/`reported` without logging the transition (change_log).
4. **No motive/characterization without a direct source.** Fields inferring a person's motive, hidden interest, or ideological lean must cite the person's own public record or statements; otherwise the field stays empty. Enforced in the grounding prompt and re-checked by the validator.

`review_status` stays in the schema (defaults to `auto`) as a forward hook: if G later wants a human glance at a specific category, flipping cards to `pending_review` + gating the frontend on `approved` is a config change, not a redesign. Not used in v1.

---

## Cost estimate (working rule 8 — flagged before any implementation)

Haiku-only stage; Wikipedia/Wikidata grounding is free. At current Haiku pricing (~$1/MTok in, $5/MTok out):

| Call | When | Rough tokens (in/out) | Cost |
|---|---|---|---|
| Extract | every event | ~6k / 1k | ~$0.011 |
| Disambiguation | ambiguous matches only (~0–2/event) | ~1k / 0.2k each | ~$0.002 |
| Ground + summarize | **new** entities only (~3–6/event cold, →0–1 warm) | ~3k / 0.5k each | ~$0.006 each |
| Relevance | every event | ~5k / 0.8k | ~$0.009 |

**≈ $0.02–0.05/event while the store is cold, settling to ≈ $0.01–0.02/event warm** — roughly 3–10% on top of the ~$0.30–0.70 the Sonnet reconcile+generate stages already cost. Anthropic web-search fallback adds ~$0.01/search only for non-Wikipedia entities. **Entity images add $0** — Wikidata `P18` + the Commons license API are free, same as the existing image engine. Locations add no new call type (extracted in the same pass as other entities). Numbers are estimates; the implementation must log `usage` per call (B-14 pattern) so real figures replace them within a week of running. **Do not implement while the credit-balance situation (§ handover 16) is unresolved.**

---

## Handoff

**APPROVED by G 2026-07-08** with the four modifications recorded at the top (image, first-class locations, no human bottleneck, attributed allegations allowed). The semantic-dedup prerequisite for later threading work has **merged** to main (`task_4517860d`), so M11 is unblocked.

**Implementation is gated only on Anthropic credits being confirmed topped up** (§ handover 16). Once confirmed, build order:
1. `pipeline/entities/` — extract → resolve → ground (Wikidata/Wikipedia + `P18` image) → relevance → write; the machine-enforced safety validator; the entity store + alias index.
2. Bump `EVENT_SCHEMA_VERSION` to 0.5 (`pipeline/schema.py`) + log it.
3. Web app — `types.ts` for `event.entities[]` and the entity store; clickable spans in `ReportView`; the side-panel/bottom-sheet card with image + tier-grouped facts + "updated" marker.
4. Wire the stage into `scripts/auto_run.py` after Generate, before Image.
5. Update TRACKSHEET (M10 → In progress/Done + change log + schema version).

Then proceed to `STAGE_8_THREADING.md` design — threading extends the now-merged `related_events`/`getEventGroups` grouping into a persistent `thread_id`, not a second linkage system.
