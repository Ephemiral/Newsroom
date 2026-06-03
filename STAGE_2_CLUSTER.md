# STAGE 2 — Cluster (Milestone 2)

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`, `STAGE_1_INGEST.md`.
**Milestone:** M2. **Phase:** 1.

## Goal

Group ingested articles so that all articles describing the **same event** land in one cluster. Each cluster becomes the unit of work for Analyze.

## Definition of done

- Given the golden dataset, the clusterer reconstructs the known event (all golden articles for `event_001` land together) — this is your correctness check.
- Given live-ingested articles, it produces sensible event clusters.
- Each cluster is written as a structured object referencing its member article ids.

## Approach (keep it simple for the MVP)

1. **Embed** each article (title + lead/body) using a sentence-embedding model.
2. **Group** by similarity — start with a straightforward method (e.g. threshold-based grouping or a standard clustering algorithm). Do not over-engineer; the golden dataset tells you immediately if it works.
3. **Allow a manual override** for the MVP: a way to hand-assign articles to a cluster. This guarantees you can always produce a correct cluster to develop later stages against, even if auto-clustering is imperfect early.

## Cluster object

```json
{
  "cluster_id": "evt_2026_05_xx_001",
  "beat": "israel_middle_east",
  "article_ids": ["art_001", "art_002", "..."],
  "created_at": "...",
  "method": "auto|manual"
}
```

## Notes

- GDELT already clusters events; you can use its grouping as a prior/seed and refine, rather than clustering from scratch.
- Clustering quality is a known hard problem. For the MVP, "good enough to produce one solid cluster for the golden event" is the bar. Comprehensive auto-clustering is a later concern.

## Handoff

Update the TRACKSHEET (M2 status + change log: method used, how well it reconstructed the golden event). Proceed to `STAGE_3_4_ANALYZE_ANNOTATE.md`.
