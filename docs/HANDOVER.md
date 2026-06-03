# HANDOVER & ONBOARDING
## News Synthesis & Credibility Engine — read this before doing anything

> **You are a fresh Claude Code / Cowork session being handed an existing project.** This document tells you what the project is, what has and hasn't been done, how the files relate, and exactly how to work. Read it fully before writing any code. The human owner is **G** (GitHub: Ephemiral).

**Handover date:** 31 May 2026
**Project status at handover:** Planning complete. All design and instruction docs written. **No code written yet.** First build task is Milestone 0 (golden dataset).

---

## 1. What this project is (30-second version)

A media product that fights bias and misinformation not by being "neutral" but by being **transparent and multi-perspectival**. For a single news event, it ingests coverage from many outlets across the political spectrum, extracts what they agree on vs. dispute, attaches each source's provenance and bias profile, and generates a synthesized report — while **preserving and surfacing the underlying analysis** so a reader can verify the synthesis instead of trusting it blindly.

The pipeline: `INGEST → CLUSTER → ANALYZE → ANNOTATE → GENERATE`.

The full rationale is in `00_MASTER_DOCUMENT.md`. **Read that next, in full, before this document's section 5.**

---

## 2. The files you have, and the order to read them

1. **`00_MASTER_DOCUMENT.md`** — the complete overview. Architecture, tech decisions, beats, UI design, barriers, build sequence. **Read first and in full.**
2. **`TRACKSHEET.xlsx`** — live project status. Two tabs: *Milestones* (M0–M9 with status) and *Change Log*. **Read the Milestones tab to find the current task. Update both tabs as you work.**
3. **This file** (`HANDOVER.md`) — how to work. Read after the master doc.
4. **The stage docs** — open only the one for the milestone you're currently on:
   - `STAGE_0_GOLDEN_DATASET.md`
   - `STAGE_1_INGEST.md`
   - `STAGE_2_CLUSTER.md`
   - `STAGE_3_4_ANALYZE_ANNOTATE.md` ← also defines the canonical per-event JSON schema
   - `STAGE_5_GENERATE.md`
   - `STAGE_6_FRONTEND.md`
5. **`Project_Charter.docx`** — the original strategy/charter. Background and "why" context; not needed for implementation but useful if you need to understand a decision's origin.

---

## 3. Where things stand (read the tracksheet for the authoritative version)

- **Done:** all planning and documentation. Architecture, tech stack, beats, and the per-event JSON schema (v0.1) are decided and recorded in the Change Log.
- **Not done:** everything in code. No repo scaffolding, no pipeline, no front end yet.
- **Current task:** **Milestone 0 — build the golden dataset** (`STAGE_0_GOLDEN_DATASET.md`). Do this before any pipeline code.

If the tracksheet and this document ever disagree about status, **the tracksheet wins** — it's the living record.

---

## 4. Decisions already made — do NOT relitigate these unless G asks

These were settled deliberately. Treat them as fixed inputs. If you think one is wrong, *raise it with G* rather than quietly building something different.

- **Positioning:** transparent & multi-perspectival, NOT "apolitical." (Never claim objective neutrality.)
- **Architecture:** the five-stage hybrid, with analysis/annotation artifacts preserved and surfaced — not discarded after the report is written.
- **Pipeline language:** Python. (Reuses G's existing "Deep Research Reporter" project.)
- **Front end:** Next.js (React). Chosen so it runs on localhost now and deploys to production later with no rewrite. Do not substitute plain static HTML.
- **Contract between halves:** a single per-event JSON artifact on disk (schema in `STAGE_3_4`). No database in the MVP.
- **Beats:** primary = Israel/Middle East, secondary = general world news. Beats are **configuration, not code** — never hardcode a source in pipeline logic.
- **Build order:** annotation-first. Phase 1 (ingest→cluster→analyze→annotate→render→validate) before Phase 2 (generate→toggle UI→validate).
- **LLM usage:** Anthropic API, model-mixed (Haiku for bulk extraction, Sonnet for synthesis). Every claim must trace to a source (anti-hallucination rule).

---

## 5. How to work — the loop to follow every session

1. **Orient:** read `00_MASTER_DOCUMENT.md`, then open `TRACKSHEET.xlsx` and find the current milestone (lowest one not "Done").
2. **Scope:** open only that milestone's stage doc. Build **only that stage.** Do not run ahead into later stages even if it seems efficient — the build order exists to prove trust before generating.
3. **Build against the golden dataset**, not a live feed, wherever possible. It is the stable fixture for development and testing.
4. **Respect the contract:** if your stage reads or writes the per-event JSON, conform exactly to the schema in `STAGE_3_4`. If you must change the schema, bump `schema_version` and log it.
5. **Confirm before irreversible or scope-expanding actions:** installing heavy new dependencies, changing a decision from section 4, restructuring the repo, or anything touching credentials. Ask G.
6. **Update the tracksheet before you finish:** set the milestone's Status, and append a Change Log row (date, area, what changed, why, by). This is how the next session stays oriented. **Treat updating the tracksheet as part of "done," not optional.**
7. **Hand off cleanly:** end your session by stating what you completed, the tracksheet rows you updated, and what the next milestone is.

---

## 6. Guardrails specific to this project

- **Copyright:** full article text is a local dev fixture only — never served to users, never redistributed. The product links out and works from facts, not reproduced expression. Don't build anything that republishes source article bodies.
- **Bias ratings:** always cite the rating's source (AllSides / Ground News / MBFC). Never present a bias rating as the system's own objective verdict.
- **No invented facts:** the report (Stage 5) may only use claims already in the analyzed JSON. No new facts introduced at generation time. Flag empty-support paragraphs for human review.
- **Secrets:** API keys live in `.env`, never committed. Same pattern as the Deep Research Reporter project.
- **Don't over-engineer the MVP:** clustering "good enough for the golden event" beats a perfect general clusterer. Shipping the core loop and validating trust is the goal, not completeness.

---

## 7. Repo structure to create (suggested, at M0/M1)

```
/ (repo root)
  docs/                      # all the .md docs + charter live here
  config/beats/              # israel_middle_east.json, world_news.json
  data/
    golden/                  # the golden dataset fixture (gitignore if repo is public)
    ingested/<beat>/         # live-ingested articles
    events/                  # per-event JSON artifacts (the contract)
  pipeline/                  # Python: ingest, cluster, analyze, annotate, generate
  web/                       # Next.js front end
  .env                       # secrets, never committed
```

Confirm this layout with G before creating it if anything conflicts with an existing setup.

---

## 8. First action for this session

If nothing has been built yet: scaffold the repo (section 7), then execute `STAGE_0_GOLDEN_DATASET.md` to produce the golden dataset. Then update the tracksheet (M0 → In progress / Done) and the Change Log. Stop and check in with G after M0 before starting M1.

If code already exists: ignore the above, read the tracksheet, and resume from the current milestone.
