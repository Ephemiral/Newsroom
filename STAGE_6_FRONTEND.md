# STAGE 6 — Front End (Milestones 5 & 8)

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_3_4_ANALYZE_ANNOTATE.md` (the JSON contract).
**Milestones:** M5 (Phase-1 annotated-analysis page), M8 (Phase-2 report + toggle UI). **Phase:** 1 then 2.

## Goal

A Next.js (React) app that reads the per-event JSON and renders it. Built in two passes matching the two phases.

## Why Next.js (recap from Master Doc §4)
Runs locally with one command now; deploys to production with no rewrite; what high-end news UIs are actually built on; React makes the per-paragraph expandable UI natural. This satisfies the requirement: localhost first, no rewrite later.

## Setup
- Scaffold a Next.js app (App Router).
- Read per-event JSON from disk (MVP) — e.g. a `data/events/*.json` folder the app reads at build/runtime. No database.
- The app must treat the JSON schema (`STAGE_3_4` v0.x) as its contract. If the schema version changes, update the reader.

---

## PASS A — Phase 1 page (M5): annotated analysis, no generated report yet

Render directly from `claims`, `sources`, `background`:
- Event title + neutral summary.
- **Claims grouped by classification:** Agreed / Contested / Single-source. For each claim: its text, the sources supporting (and contesting) it, and its `rationale`.
- **Source panel:** one provenance card per source (outlet, link, bias rating + *rating source*, ownership one-liner, author background).
- **Background** section.

This page alone is the Phase-1 deliverable used to validate trust (M6). It is useful and shippable without any generated report.

---

## PASS B — Phase 2 UI (M8): report-by-default with the toggle

Once `report` is populated:
- **Default view:** the synthesized report reads cleanly, paragraph by paragraph (`report.paragraphs[].text`).
- **Toggle at the top of the page:** switches on transparency mode.
- **Transparency mode on:** each paragraph becomes an expandable dropdown. Expanding it reveals — pulled live from the JSON via the paragraph's `supports.claim_ids` / `source_ids` — the underlying claims, their classification and rationale, and the source provenance cards behind that paragraph.
- Visually distinguish paragraph `kind` (agreed / contested / framing / background) subtly, so a reader can see the texture of the synthesis.

This is the realization of the core product idea: clean report on top, full receipts one tap beneath, all driven by the linkage Stage 5 wrote into the JSON.

## Design notes
- Keep components schema-driven; no hardcoded event content.
- Treat the "in vs beside the report" question as a layout decision you can iterate — the toggle/dropdown is the current leading direction (Master Doc §6).
- Accessibility and clean typography matter for a credibility product; this is a reason Next.js over a thrown-together static page.

## Handoff
Update the TRACKSHEET (M5, then M8). M5 unblocks validation (M6); M8 completes the Phase-2 reader experience ahead of validation (M9).
