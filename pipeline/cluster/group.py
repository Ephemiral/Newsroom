"""
Event-clustering logic.

Strategy: threshold-based average-linkage grouping with optional time window.
- Compute pairwise cosine similarity (= dot product on L2-normalised vectors).
- Build an edge mask: two articles are eligible to share a cluster only if their
  similarity exceeds THRESHOLD AND their publication dates are within
  TIME_WINDOW_HOURS of each other.
- Greedily assign each article to the existing cluster it has the highest mean
  similarity to (only among clusters it has at least one eligible edge into),
  provided that mean similarity also clears THRESHOLD; otherwise it starts a
  new cluster. Average-linkage (rather than connected-components/single-linkage)
  avoids transitive chaining, where two genuinely unrelated articles end up in
  the same cluster purely because each is similar to some article in between
  (see B-12 in the master doc backlog).
- Clusters with low mean pairwise similarity are logged as a cohesion warning
  post-hoc — a heuristic flag for grab-bag clusters, not a hard filter.

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


def _average_linkage_cluster(
    sim: np.ndarray,
    adj: np.ndarray,
    threshold: float,
) -> list[list[int]]:
    """
    Average-linkage clustering over a precomputed similarity matrix.
    An article joins an existing cluster only if its average cosine similarity
    to ALL current cluster members meets `threshold`. Prevents the transitive
    chaining that plain connected-components grouping is prone to (B-12).
    """
    n = sim.shape[0]
    clusters: list[list[int]] = []

    for i in range(n):
        best_cluster = None
        best_avg = -1.0

        for ci, members in enumerate(clusters):
            if not any(adj[i, m] for m in members):
                continue
            avg_sim = float(np.mean(sim[i, members]))
            if avg_sim >= threshold and avg_sim > best_avg:
                best_avg = avg_sim
                best_cluster = ci

        if best_cluster is not None:
            clusters[best_cluster].append(i)
        else:
            clusters.append([i])

    return clusters


COHESION_FLOOR = 0.65


def _check_cohesion(clusters: list[dict], sim: np.ndarray, article_ids: list[str]) -> None:
    """Warn about clusters with low mean pairwise similarity (potential grab-bags)."""
    id_to_idx = {aid: i for i, aid in enumerate(article_ids)}
    for c in clusters:
        idxs = [id_to_idx[aid] for aid in c["article_ids"] if aid in id_to_idx]
        if len(idxs) < 2:
            continue
        sims = [sim[i, j] for idx_i, i in enumerate(idxs) for j in idxs[idx_i + 1:]]
        if not sims:
            continue
        mean_sim = float(np.mean(sims))
        if mean_sim < COHESION_FLOOR:
            log.warning(
                "Low-cohesion cluster %s: %d articles, mean_sim=%.3f — possible grab-bag",
                c["cluster_id"], c["size"], mean_sim,
            )


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
    Group articles into event clusters using threshold-based average-linkage grouping.

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

    components = _average_linkage_cluster(sim, adj, threshold)
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

    _check_cohesion(clusters, sim, article_ids)
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
