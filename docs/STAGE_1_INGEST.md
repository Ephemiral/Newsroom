# STAGE 1 — Ingest (Milestone 1)

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_0_GOLDEN_DATASET.md`.
**Milestone:** M1. **Phase:** 1.

## Goal

Pull coverage of events for a configured beat into a stored raw form, using the same article schema as the golden dataset, so live-ingested articles and golden articles are interchangeable downstream.

## Definition of done

- A beat config drives which sources are pulled (no source hardcoded in logic).
- Running the ingester for a beat produces article files in the same schema as `data/golden/`.
- Deduplication: the same article from the same URL is not stored twice.
- The golden dataset remains usable as a drop-in alternative input (a `--source golden` mode or equivalent).

## Source strategy (MVP)

Start with low-legal-risk, structured sources. **Do not scrape yet** (see Master Doc §7).
- **GDELT** — free, global, already clusters events across thousands of outlets; ideal first source. Useful for both discovering events and finding multi-outlet coverage.
- **RSS feeds** — a hand-picked set per beat, spanning the spectrum.
- **News APIs** (e.g. NewsAPI) — optional, if RSS coverage is thin.

## Beat config format

```json
{
  "beat": "israel_middle_east",
  "display_name": "Israel / Middle East",
  "sources": [
    {
      "outlet": "Example Outlet",
      "rss": "https://example.com/feed.xml",
      "bias_rating": "center",
      "bias_rating_source": "AllSides"
    }
  ],
  "gdelt": { "enabled": true, "query": "..." },
  "language_filter": ["en"]
}
```
Adding a beat = adding one such file. Pipeline logic reads the config; it never names a source itself.

## Steps

1. Define the article schema as a single shared module (reused by every stage). Match the golden dataset fields exactly.
2. Implement an RSS reader that walks each source in the beat config and emits articles in that schema.
3. Implement a GDELT client for event discovery + coverage lookup.
4. Implement dedup (by normalized URL, and optionally near-duplicate title).
5. Implement storage (write article files; mirror the `data/golden/` layout under `data/ingested/<beat>/`).
6. Provide a switch so downstream stages can run against `golden` or `ingested` input identically.

## Notes

- Respect each source's robots/ToS; prefer official feeds/APIs over fetching pages.
- Store `collected_at` and the originating beat on every article.
- Keep credentials (API keys) in a `.env` file, never committed — same pattern as Deep Research Reporter.

## Handoff

Update the TRACKSHEET (M1 status + change log: which sources wired, any that failed). Proceed to `STAGE_2_CLUSTER.md`.
