"""
Event-clustering logic.

Strategy (MVP): threshold-based agglomerative grouping with optional time window.
- Compute pairwise cosine similarity (= dot product on L2-normalised vectors).
- Build a graph: connect any two articles whose similarity exceeds THRESHOLD
  AND whose publication dates are within TIME_WINDOW_HOURS of each other.
- Extract connected components — each component is an event cluster.

Threshold guidance:
  0.50 — original MVP value, tuned for golden dataset where "unrelated" articles
          were from completely different topics. Too loose for a beat-specific feed
          where all articles share topic vocabulary (Israel, Gaza, Hamas, etc.).
  0.70 — recommended for live beat feeds. Requires articles to share specific
          event language (same operation name, location, actor combination).
  0.80 — strict; use when clusters are still too large at 0.70.

Time window guidance:
  None  — no time constraint (original behavior)
  48    — most news events play out over 24–48h; 48h is a good default
  72    — looser, allows slow-developing stories to cluster together
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# Similarity threshold for "same event" (0–1, cosine similarity).
DEFAULT_THRESHOLD = 0.70

# Maximum hours between article publication dates for same-cluster eligibility.
# None disables the constraint (original behavior).
DEFAULT_TIME_WINDOW_HOURS: Optional[int] = 48


def _connected_components(adj: np.ndarray) -> list[list[int]]:
    """Union-find over a boolean adjacency matrix."""
    n = adj.shape[0]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for i in range(n):
        for j in range(i + 1, n):
            if adj[i, j]:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)
    return list(groups.values())


def _parse_pub_date(date_str: str) -> Optional[datetime]:
    """Parse ISO 8601 date string to datetime. Returns None on failure."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def auto_cluster(
    embeddings: np.ndarray,
    article_ids: list[str],
    beat: str,
    threshold: float = DEFAULT_THRESHOLD,
    time_window_hours: Optional[int] = DEFAULT_TIME_WINDOW_HOURS,
    pub_dates: Optional[list[str]] = None,
) -> list[dict]:
    """
    Group articles into event clusters using threshold-based connected components.

    Args:
        embeddings: L2-normalised article embedding matrix (n × d).
        article_ids: list of article ID strings, same order as embeddings.
        beat: beat name for cluster metadata.
        threshold: cosine similarity threshold (0–1). Higher = more discriminating.
        time_window_hours: if set, two articles can only cluster together if their
            publication dates are within this many hours. None disables the constraint.
        pub_dates: list of ISO 8601 publication date strings, same order as embeddings.
            Required for time_window_hours to have effect.

    Returns a list of cluster dicts (per the STAGE_2 schema).
    """
    n = len(article_ids)
    if n == 0:
        return []

    # Cosine similarity matrix (dot product of L2-normalised vectors)
    sim = embeddings @ embeddings.T
    adj = sim >= threshold
    np.fill_diagonal(adj, False)  # no self-loops

    # Time-window constraint: zero out edges between articles too far apart in time
    if time_window_hours is not None and pub_dates:
        parsed_dates = [_parse_pub_date(d) for d in pub_dates]
        max_delta = timedelta(hours=time_window_hours)
        skipped = 0
        for i in range(n):
            for j in range(i + 1, n):
                if adj[i, j] and parsed_dates[i] and parsed_dates[j]:
                    if abs(parsed_dates[i] - parsed_dates[j]) > max_delta:
                        adj[i, j] = adj[j, i] = False
                        skipped += 1
        if skipped:
            log.info("Time-window filter: removed %d cross-time edges (>%dh apart)", skipped, time_window_hours)

    components = _connected_components(adj)
    now = datetime.now(timezone.utc).isoformat()
    clusters = []

    for idx, component in enumerate(components):
        ids = [article_ids[i] for i in component]
        cluster_id = f"evt_{now[:10].replace('-', '_')}_{idx + 1:03d}"
        clusters.append({
            "cluster_id": cluster_id,
            "beat": beat,
            "article_ids": ids,
            "created_at": now,
            "method": "auto",
            "threshold": threshold,
            "size": len(ids),
        })
        log.info(
            "Cluster %s: %d articles — %s",
            cluster_id,
            len(ids),
            ", ".join(ids[:4]) + ("…" if len(ids) > 4 else ""),
        )

    tw = f", time_window={time_window_hours}h" if time_window_hours else ""
    log.info(
        "Auto-clustering: %d articles → %d clusters (threshold=%.2f%s)",
        n, len(clusters), threshold, tw,
    )
    return clusters


def manual_cluster(article_ids: list[str], beat: str, cluster_id: str | None = None) -> dict:
    """
    Create a manually assigned cluster from a list of article IDs.
    Use this when auto-clustering fails to group correctly.
    """
    now = datetime.now(timezone.utc).isoformat()
    cid = cluster_id or f"evt_{now[:10].replace('-', '_')}_manual_001"
    cluster = {
        "cluster_id": cid,
        "beat": beat,
        "article_ids": article_ids,
        "created_at": now,
        "method": "manual",
        "size": len(article_ids),
    }
    log.info("Manual cluster %s: %d articles", cid, len(article_ids))
    return cluster
