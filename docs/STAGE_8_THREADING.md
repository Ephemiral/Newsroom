# STAGE 8 — Story Threading (Milestone M11)

> **Status: ✅ IMPLEMENTED (2026-07-08, same session as approval).** `pipeline/threading/` live and wired into `auto_run.py`; thread store at `data/threads/`; **"Threads"** tab + `/threads` list + `/thread/[id]` arc + event-page banner shipped. Backfill formed 3 threads (Khamenei funeral, NATO/Ukraine, US–Iran Hormuz) with neutral AI titles. G's approved decisions: tab label **"Threads"**, neutral human-overridable titles, backfill yes. Implementation note: the specific-entity guard was refactored from an IDF *percentile* (which demanded `df=1` and blocked every shared entity) to a **ubiquity cap** (`df ≤ 25% of events`) — see match.py.
> Links event clusters that are chapters of the same ongoing story into a persistent, named, ordered **thread**, so a reader can open "US–Iran negotiations" and follow the whole arc — not just today's snapshot. Threads are a **cross-beat** organizing layer surfaced on their own **"Threads"** tab.

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_3_4_ANALYZE_ANNOTATE.md` (JSON contract), `STAGE_7_ENTITIES.md` (entities power the matching), `STAGE_6_FRONTEND.md`.
**Milestone:** M11. **Phase:** 3.
**Schema impact:** per-event JSON v0.5 → v0.6 (additive `event.thread_id`); new thread schema v0.1 (`data/threads/`).
**Depends on:** the merged semantic-dedup / `related_events` / `getEventGroups` work (task_4517860d) — threading **extends** it, and the entity stage (M10) — threading **matches on** it.

---

## The core distinction (why this isn't the dedup we already shipped)

We already have two things that sound like threading but aren't:

| Layer | Question it answers | Window | Basis |
|---|---|---|---|
| **Semantic dedup** (shipped) | "Is this the *same report* re-clustered?" → don't double-publish | 5 days | near-identical (cosine ≥0.85/0.93) |
| **`getEventGroups`** (shipped) | "Collapse near-duplicate cards on the homepage" | n/a | `related_events` edges |
| **Threading** (this doc) | "Are these *different reports* on the *same ongoing story*?" → group into an arc | **weeks** | **shared entities + theme** |

Dedup stops the *same article set* becoming two cards. Threading links *genuinely distinct developments* — "ceasefire talks begin" (week 1) and "talks collapse" (week 4) share **no articles** and are **not near-duplicates**, so dedup correctly leaves them apart. Threading is the layer that recognizes they're one story. It became tractable only now because M10 gives us the entities to match on.

---

## Goal

A persistent `thread` groups the events of one developing story, chronologically, each event annotated with *what it added*. Threads have human-readable titles, span beats, and live on a dedicated **"Developing"** tab. This is also the required substrate for Accountability Tracking (M12), which traverses a thread's events per-outlet.

## Definition of done

- A threading stage (`pipeline/threading/`) runs after Generate + Entities; it assigns each new event to an existing thread, forms a new thread when it links to a previously-unthreaded event, or leaves it unthreaded.
- Persistent thread objects at `data/threads/{thread_id}.json` (git-tracked, deploy with the site).
- An **explicit, written matching rule** (below) with tunable, logged thresholds — not vibes.
- A **"Developing" tab** listing threads (newest activity first); a **thread page** showing the arc.
- **A thread only ever contains ≥2 events** (G's decision): a single report is never shown as "developing."
- AI-generated, neutral, human-overridable thread titles + per-event "what's new" summaries.
- `EVENT_SCHEMA_VERSION` → 0.6 (`event.thread_id`); tracksheet updated.

## Non-goals (v1)

- **"Follow this story" / notifications** — out of scope per command. The schema must not *block* it (persistent `thread_id` + `last_updated` are enough to add it later); don't build it.
- **Accountability Tracking** — that's M12 (`STAGE_9`), built *on top of* this schema. Not here.
- Retroactive threading of the full back catalogue beyond a bounded backfill window (see Rollout).

---

## Approach

### Pipeline placement

```
… → GENERATE → ENTITIES → **THREADING** → IMAGE → publish
```

Threading needs the event's entities (M10) and its title+summary embedding (already computed). It reads existing threads + recent events, decides membership, and writes `event.thread_id` + updates/creates the thread manifest. Single writer (one scheduler) — no concurrency handling.

### The unit of matching: an event's "story signature"

For each event, the stage builds a signature from data that already exists:

- **Major entities** — the `event.entities[]` of type `person`, `organization`, `political_party`, `technology`. Generic `location` and `other` are excluded from the *primary* signal (they over-link).
- **Themes** — the event's `claim_group` values.
- **Embedding** — the title+summary vector (reused from the dedup stage).

### The over-linking problem (and the fix)

Ubiquitous entities — "Israel", "United States", "Iran", "Gaza Strip" — appear in dozens of unrelated events. Matching on them would re-create the B-12 mega-cluster disaster at thread level (everything glued into one blob). **Fix: weight each entity by its rarity across the corpus (IDF).** A story-specific entity ("Board of Peace", "Ali Shaath", "MIM-104 Patriot", a named operation) is a strong thread signal; a ubiquitous one is nearly weightless. The IDF table is recomputed from the entity store's `appears_in_events` counts (free, no LLM).

---

## Matching rule (explicit — the heart of the design)

A candidate event **E** is compared against every event **P** published within `THREAD_WINDOW_DAYS` before it. The link score:

```
score(E, P) = w_ent · IDF_weighted_overlap(major_entities(E), major_entities(P))
            + w_thm · jaccard(claim_groups(E), claim_groups(P))
            + w_emb · cosine(embed(E), embed(P))
```

**E links to P** iff **all** of:
1. `score(E, P) ≥ THREAD_MATCH_FLOOR`, **and**
2. E and P share **≥1 "specific" entity** — a shared major entity whose IDF weight exceeds `SPECIFIC_ENTITY_IDF` (this is the guard against linking two events purely because both mention "Israel"), **and**
3. `P.date` is within `THREAD_WINDOW_DAYS` of `E.date`.

**Assignment logic** (mirrors the entity-resolution discipline — *prefer under-merging to over-merging*):
- E links to one or more past events → E joins the thread of its **single highest-scoring** match `P*`.
- `P*` has no thread yet → **create a new thread** containing exactly `{P*, E}` (this is why threads are always ≥2 events).
- E matches events across **two different existing threads** → do **not** auto-merge the threads; assign E to the higher-scoring one and **log the cross-thread match** to `data/threads/review_log.jsonl` for manual merge review. Merging two established threads is high-impact and error-prone; a human confirms it.
- No qualifying match → E stays **unthreaded** (`thread_id: null`); it appears only in the normal feeds.

**Window semantics:** `THREAD_WINDOW_DAYS` is measured from the thread's **most recent** event, not its first — an active story keeps extending as long as coverage continues; a story that goes quiet for the whole window naturally stops accreting (and is marked `dormant`, below). This lets a months-long saga stay one thread while it's live.

**Starting thresholds** (tunable constants, calibrated from `score` values logged per comparison — same discipline as the dedup gate's `SEMANTIC_*`):
```
THREAD_WINDOW_DAYS   = 30
THREAD_MATCH_FLOOR   = 0.45      # calibrate from logged scores
SPECIFIC_ENTITY_IDF  = <p60 of the IDF distribution>   # "not one of the ~top ubiquitous entities"
w_ent, w_thm, w_emb  = 0.6, 0.15, 0.25
```
These will be wrong on day one and right after a week of logged real scores — shipped exactly like `SEMANTIC_SAME_STORY` was.

---

## Thread schema (v0.1) — `data/threads/{thread_id}.json`

```json
{
  "thread_schema_version": "0.1",
  "thread_id": "thr_us_iran_nuclear_talks",
  "title": "US–Iran nuclear negotiations",
  "title_source": "auto",
  "summary": "One-line neutral description of the ongoing story.",
  "status": "developing",
  "beats": ["israel_middle_east", "americas"],
  "key_entities": ["ent_organization_iran", "ent_person_...", "..."],
  "events": [
    {
      "cluster_id": "evt_2026_06_20_israel_middle_east_003",
      "date": "2026-06-20",
      "chapter_summary": "What THIS event added to the story vs. the prior chapter.",
      "link_score": 0.71
    }
  ],
  "created_at": "…", "last_updated": "…",
  "change_log": [{ "date": "…", "summary_of_change": "…" }]
}
```

- `events` is chronological (oldest→newest); `key_entities` is the running union of specific entities that define the thread (the matching basis, and what M12 will group outlets by).
- `status`: `developing` while within-window activity continues; `dormant` when no new event for `THREAD_WINDOW_DAYS`. Dormant threads still render (history is permanent) but sort below active ones.
- `title` / `title_source`: AI-generated (`auto`); if a human edits it, `title_source` becomes `manual` and the pipeline never overwrites it.
- **Immutable `thread_id`**, slug-minted like entity ids.

### Per-event change (v0.5 → v0.6, additive)

`event.thread_id: string | null` — the thread this event belongs to, or null (unthreaded). Old events and standalone events stay null and render exactly as today. `related_events` remains for the event-page "Earlier coverage" box; **`thread_id` supersedes `getEventGroups` as the primary grouping** (see Migration).

---

## Frontend contract

**"Developing" tab** (new, in the homepage nav beside All / beats / About — cross-beat, so *not* under a beat):
- Lists every thread (all have ≥2 events by construction), sorted by `last_updated`, `developing` above `dormant`.
- Each row: title, one-line summary, chapter count ("5 developments"), latest date, latest event's image.
- **Single events never appear here** (G's decision) — they're in All / their beat until/unless they thread.

**Thread page** `/thread/[id]`:
- Title + summary, then the arc. Latest chapter first (readers come for the newest development), each chapter a card: date, event title, its `chapter_summary` ("what's new"), link to the full event page. A reader scrolls **down** to travel **back** through the story's history.
- Reuses the existing event-card styling; schema-driven, no hardcoded content.

**Event page:** the current "Earlier coverage" box becomes **"Part of a developing story: [thread title] →"** linking to the thread when `thread_id` is set; unchanged when null.

**Homepage:** a threaded event's card gets a small "Developing story" badge linking to its thread (this replaces the on-the-fly `getEventGroups` collapse with persistent thread membership).

### Migration from `getEventGroups`

`getEventGroups()` currently computes homepage grouping live from `related_events`. Once threads are persistent, the homepage reads `thread_id` instead. `getEventGroups` is either retired or reduced to a thin wrapper over thread membership — no second, competing grouping system (per the command's explicit requirement).

---

## Trust & safety flags (per command working rule 6)

1. **Loaded thread titles are a visible trust risk.** An AI title that editorializes ("Israel's assault on…") undermines the whole product on the most prominent surface. Mitigation: the title prompt inherits the event-title discipline (transparent, parallel language, no side's framing) and titles are **human-overridable** with one edit. Flag for review before launch.
2. **Over-merging misrepresents the news.** Gluing unrelated events into one "story" is the B-12 failure at a reader-facing level. Mitigations baked into the rule: IDF weighting, the required specific-entity guard, conservative thresholds, and *never* auto-merging two established threads (logged for human review instead). The bias is deliberately toward **under-linking** (two short threads) over **over-linking** (one wrong thread).
3. **"What's new" summaries must not invent developments.** Each `chapter_summary` is grounded in that event's own report only — same anti-hallucination discipline as Generate. No cross-event speculation.

---

## Cost estimate (per command working rule 8)

Matching is **near-free**: entity signatures come from stored JSON, IDF from `appears_in_events` counts, and the embedding is reused from the dedup stage — all set/vector math, no LLM. The only paid calls, and only when an event actually threads:

| Call | When | Cost |
|---|---|---|
| `chapter_summary` (what's new) | per event that joins a thread | ~$0.005 |
| Thread title | once when a thread is created; refresh only if still `auto` and materially changed | ~$0.003 |

**≈ $0.005–0.01 per *threaded* event; $0 for the majority that don't thread.** Negligible on top of the ~$0.30–0.70/event the pipeline already spends. Usage logged per call (B-14).

## Rollout

- Ship the stage; it threads events **going forward** automatically.
- One-time **bounded backfill**: run the matcher over the last ~30–45 days of existing events to seed initial threads (the current live stories — Gaza governance, US–Iran, Ukraine/NATO — should form immediately). Older archive left unthreaded.

## Handoff

G reviews this doc. Decisions to confirm: (1) approve/modify the matching rule + starting thresholds, (2) tab label ("Developing" vs "Stories"/"Threads"), (3) the neutral-title constraint + override behavior, (4) backfill window. On approval: implement `pipeline/threading/`, bump `EVENT_SCHEMA_VERSION` to 0.6, add the tab + thread page, update TRACKSHEET (M11), then proceed to `STAGE_9_ACCOUNTABILITY.md` (M12) — which reads this thread object and adds the per-outlet claim-history view, reusing `claim_id`/`source_id` (no parallel IDs).
