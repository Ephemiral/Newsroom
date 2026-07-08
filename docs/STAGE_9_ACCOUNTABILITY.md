# STAGE 9 — Accountability Tracking (Milestone M12)

> **Status: DESIGN — pending G's review. No implementation until approved.**
> Across a thread, surface where an outlet's *own* reporting changed — it asserted A in an earlier chapter and not-A (or corrected/retracted it) in a later one. Show **both, side by side, in parallel language, and let the reader judge**. This is *"Outlet X said A on day 1 and not-A on day 3, here's both"* — **never** *"Outlet X is biased."*

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_3_4_ANALYZE_ANNOTATE.md` (claims/sources), `STAGE_8_THREADING.md` (this runs across a thread), `STAGE_6_FRONTEND.md`.
**Milestone:** M12. **Phase:** 3 (final feature).
**Schema impact:** thread schema v0.1 → v0.2 (additive `thread.accountability[]`); no per-event schema change. Reuses `claim_id`/`source_id` — **no parallel IDs**.
**Depends on:** Threading (M11) — you cannot track how a claim evolved without a linked sequence of events.

---

## Goal

Inside the product's existing "what the coverage shows" framing, track how an individual outlet's claims on a story evolve or get walked back **over the thread** (not within a single event). Render it in the transparency layer as an evidentiary record — the reporting itself, with dates and links — with zero editorializing about *why* it changed.

## Definition of done

- A stage that, when a thread gains a chapter, compares each returning outlet's new claims against its own earlier claims **in the same thread** and flags genuine self-**contradiction / correction / retraction**.
- Flags stored on the thread object, each citing the two `claim_id`/`source_id`/`cluster_id` instances with both verbatim texts and dates.
- A **"How the reporting changed"** section on the thread page (transparency layer), parallel-language, both quotes shown, links to both events.
- **The world-changed vs. outlet-flip-flopped distinction is enforced** (see Safety) — the single hardest and most important rule here.
- High flagging bar + audit log; the human-review posture is G's decision (below).

## Non-goals (v1)

- **No cross-outlet accountability** ("Outlet A contradicted Outlet B") — that's just the existing contested-claims view; this feature is strictly an outlet **against its own** prior reporting.
- **No motive/characterization** — never "flip-flopped", "walked back under pressure", "backtracked". Only the neutral record.
- **No scoring/leaderboards** of outlet reliability. Out of scope, and a different (dangerous) product.

---

## The core hazard (read this first)

Over a developing story, **most changes are the story developing, not the outlet erring.** "Reuters reported a ceasefire held (day 1), then reported it collapsed (day 4)" is **not** a contradiction — the world changed, and Reuters reported both accurately. Flagging that as an outlet contradicting itself would be false, unfair, and defamation-adjacent — the exact opposite of a trust product's purpose.

So the detection must fire **only** when an outlet's later reporting contradicts, corrects, or retracts its **own earlier account of the same fact at the same point in time** — not when the underlying situation legitimately moved on. This distinction is the whole feature. Everything below is built around getting it right and failing safe (flag nothing rather than flag wrongly).

Three legitimate flag types:
| Type | Meaning | Example |
|---|---|---|
| `contradiction` | Outlet asserted A about a fixed fact, later asserted not-A about that same fixed fact | Reported the strike hit a hospital; later reported (as its own account, not attributed to a new source) it hit a military site |
| `correction` | Outlet explicitly revised an earlier figure/claim | "An earlier report said 40 killed; officials now put the toll at 12" |
| `retraction` | Outlet withdrew an earlier claim | "We can no longer confirm the earlier report that…" |

A change that is the outlet *reporting a new development* is **none of these** and must not be flagged.

---

## Detection rule (explicit)

Runs when a thread gains a chapter (incremental — bounded cost). For each outlet present in the new event **and** in ≥1 earlier chapter of the thread:

1. **Assemble that outlet's claim timeline in the thread** — from each event, the claims where this outlet appears in `supported_by`/`contested_by`, with `claim_id`, `source_id`, `cluster_id`, date, text, and `framing_variants`.
2. **LLM comparison (the high-stakes call — Sonnet, for quality).** Prompt the model with that single outlet's own timeline and ask it to identify *only* cases where the outlet's **later reporting contradicts/corrects/retracts its own earlier reporting about the same fixed fact** — explicitly instructing it that a changed situation, a new development, or reporting a new party's claim is **NOT** a flag. Require it to return, for each genuine flag: the two instances (by `claim_id`), the type, a neutral one-line subject, and a parallel-language note — or an empty list.
3. **Validate every flag** (machine-enforced, mirrors the entity safety gate): both `claim_id`s must exist and resolve to the **same outlet**; both must have real `source_id`s and links; drop any flag missing a citation on either side. A flag that can't cite both receipts is never shown.
4. **Deduplicate** against existing `thread.accountability[]` so a re-run doesn't double-report.

Fail-safe posture: on any ambiguity the model is told to return nothing. A missed contradiction is a non-event; a false one is a serious harm.

---

## Thread schema change (v0.1 → v0.2, additive)

Add `accountability[]` to the thread object:

```json
"accountability": [
  {
    "id": "acc_001",
    "outlet": "Example Outlet",
    "type": "contradiction | correction | retraction",
    "subject": "Neutral one-line description of the fact at issue.",
    "earlier": {
      "cluster_id": "evt_…", "date": "2026-06-20",
      "claim_id": "clm_…", "source_id": "src_…", "text": "verbatim earlier claim", "url": "https://…"
    },
    "later": {
      "cluster_id": "evt_…", "date": "2026-06-27",
      "claim_id": "clm_…", "source_id": "src_…", "text": "verbatim later claim", "url": "https://…"
    },
    "note": "Neutral, parallel statement of what changed — no speculation on why.",
    "review_status": "auto | approved | suppressed",
    "detected_at": "…"
  }
]
```

Everything reuses existing `claim_id`/`source_id`/`cluster_id`. `thread_schema_version` → `"0.2"`.

---

## Frontend contract

On the **thread page** (`/thread/[id]`), when `accountability[]` is non-empty, a transparency-layer section **"How the reporting changed"** (collapsed by default, consistent with the per-paragraph receipts pattern):

- One entry per flag, grouped by outlet. Header states the type plainly: *"Correction"* / *"Contradiction"* / *"Retraction"*.
- The two instances shown **side by side / stacked with equal weight**, each with its date, verbatim text, and a link to that event's full report — the same even-handed, parallel treatment contested claims already get (no side gets a warning color or a credibility label).
- The neutral `note` above them. **No adjectives, no "why."**
- A standing one-line disclaimer: *"This shows an outlet's own reporting at two points in the story. A developing story changes; this section flags only where an outlet's account of the same fact changed."*

Only `review_status != "suppressed"` entries render (and, if G chooses the review gate, only `approved`).

---

## Safety gate (the highest bar of the three features)

Publicly stating that a **named outlet contradicted itself** is the most defamation-adjacent thing the product does. Controls:

1. **The world-changed guard** (above) is the primary defense — enforced in the prompt and reinforced by the fail-safe "return nothing on doubt."
2. **Both receipts mandatory** — a flag with a missing/unresolvable `claim_id` or `source_id` on either side is dropped by the validator, never shown.
3. **Same-outlet check** — both instances must resolve to the same outlet (guards against the model conflating two outlets).
4. **Parallel, motive-free language** — enforced in the prompt; both instances shown with equal weight.
5. **Audit + suppression** — every flag is written to `data/threads/review_log.jsonl`; `review_status: "suppressed"` hides one instantly without deleting the record.
6. **⚠ DECISION FOR G — human review gate.** Master Doc §15a made the pipeline autonomous (no human-in-the-loop), and the entity stage kept that by machine-enforcing safety. Accountability is a notch riskier. Two options:
   - **(a) Autonomous, high-bar + audit + suppression** (consistent with the rest of the pipeline): flags display automatically; you spot-check and suppress any bad one. Keeps the product fully hands-off.
   - **(b) Review-gated**: flags are created with `review_status: "auto"` and **only render once a human sets `"approved"`** (like the person-card option). Safest; costs you a small review step per flag. Given how rarely genuine self-contradictions occur, the review burden would be light.
   My recommendation: **(b)** for this feature specifically — the downside of one wrong public "contradiction" flag outweighs the small manual step, and flags will be infrequent. But it's your call.

---

## Cost estimate (per command working rule 8)

Only runs when a thread gains a chapter, and only for outlets present in both the new and an earlier chapter — a small set. One **Sonnet** call per such thread-update (Sonnet, not Haiku, because a false accusation is far costlier than the tokens):

- ~3–6k input / ~0.5k output per thread-update → **~$0.02–0.04 per thread-update**, incurred only on the (uncommon) event that extends an existing thread. $0 for the many events that don't. Negligible against the ~$0.30–0.70/event the pipeline already spends. Usage logged per call (B-14).

## Rollout

- Ship the stage; it evaluates threads as they gain chapters going forward.
- One-time backfill over the existing threads (there are 3) to seed any historical flags.

## Handoff

G reviews. Decisions to confirm: (1) approve the detection rule + the world-changed guard, (2) **the human-review gate — option (a) autonomous or (b) review-gated (recommended)**, (3) Sonnet for detection, (4) thread-page placement. On approval: implement the stage (extend `pipeline/threading/` or a sibling `pipeline/accountability/`), bump `thread_schema_version` to 0.2, add the thread-page section, update TRACKSHEET (M12). **This completes Phase 3.**
