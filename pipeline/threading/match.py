"""
Story-threading match logic (STAGE_8) — pure scoring, no IO.

Decides when two events are chapters of the same developing story, using signals
that already exist: the events' major entities (M10), their thematic claim_groups,
and their title+summary embeddings (reused from the dedup stage).

The central hazard is over-linking on ubiquitous entities ("Israel", "United
States") — that would re-create the B-12 mega-cluster failure at thread level.
The defence is IDF weighting: an entity's contribution is scaled by how rare it
is across the corpus, and a link additionally REQUIRES at least one shared
"specific" (rare) entity. The bias is deliberately toward under-linking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

# ── Tunable constants (approved 2026-07-08). Calibrate THREAD_MATCH_FLOOR from
#    the per-comparison scores logged by run.py, same as the dedup gate's
#    SEMANTIC_* thresholds were. ──────────────────────────────────────────────
THREAD_WINDOW_DAYS = 30       # link only to events within this many days (rolling)
THREAD_MATCH_FLOOR = 0.45     # minimum blended score to link
W_ENT, W_THM, W_EMB = 0.60, 0.15, 0.25  # entity / theme / embedding weights
# An entity is "ubiquitous" (not story-specific) once it appears in more than
# this fraction of events — those are the "Israel"/"US"/"Iran" that must NOT be
# allowed to anchor a thread on their own. A SHARED entity appears in ≥2 events
# by definition, so the bar must be about ubiquity, not uniqueness.
UBIQUITY_FRACTION = 0.25

_MAJOR_PREFIXES = ("ent_person_", "ent_organization_",
                   "ent_political_party_", "ent_technology_")


def is_major_entity(entity_id: str) -> bool:
    """Person/org/party/tech carry story identity; generic locations/other over-link."""
    return entity_id.startswith(_MAJOR_PREFIXES)


@dataclass
class Signature:
    """Everything the matcher needs about one event."""
    cluster_id: str
    beat: str
    date: str                       # 'YYYY-MM-DD'
    entities: frozenset             # major entity_ids
    claim_groups: frozenset
    text: str                       # title + summary (for embedding)
    embedding: np.ndarray | None = field(default=None)

    @property
    def ts(self) -> float:
        try:
            return datetime.fromisoformat(f"{self.date}T00:00:00+00:00").timestamp()
        except Exception:
            return float("-inf")


def signature_from_event(data: dict) -> Signature:
    ev = data.get("event", {})
    entities = frozenset(
        e["entity_id"] for e in ev.get("entities", [])
        if e.get("entity_id") and is_major_entity(e["entity_id"])
    )
    groups = frozenset(
        c["claim_group"] for c in data.get("claims", [])
        if c.get("claim_group")
    )
    text = f"{ev.get('title', '')}. {ev.get('summary', '')}".strip()
    return Signature(
        cluster_id=ev.get("cluster_id", ""), beat=ev.get("beat", ""),
        date=(ev.get("date", "") or "")[:10], entities=entities,
        claim_groups=groups, text=text,
    )


# ── IDF over the entity corpus ────────────────────────────────────────────────

def build_idf(entity_doc_freq: dict[str, int], n_events: int) -> dict[str, float]:
    """Smoothed IDF per entity_id from its document frequency (number of events
    it appears in). Rare entities score high; ubiquitous ones near-zero."""
    idf = {}
    for eid, df in entity_doc_freq.items():
        idf[eid] = math.log((n_events + 1) / (df + 1)) + 1.0
    return idf


def specific_threshold(idf: dict[str, float], n_events: int) -> float:
    """IDF value at the ubiquity cutoff. An entity is 'specific' (can anchor a
    thread link) when its IDF ≥ this — i.e. it appears in at most `ubiq_df`
    events. Rare/story-specific entities clear it; ubiquitous ones don't.

    Because IDF decreases monotonically with document frequency, thresholding on
    IDF ≥ idf(ubiq_df) is exactly `df ≤ ubiq_df`."""
    ubiq_df = max(4, round(UBIQUITY_FRACTION * max(1, n_events)))
    return math.log((n_events + 1) / (ubiq_df + 1)) + 1.0


# ── scoring ───────────────────────────────────────────────────────────────────

def _idf_weighted_overlap(a: frozenset, b: frozenset, idf: dict[str, float]) -> float:
    """Weighted Jaccard of two entity sets, each entity weighted by its IDF."""
    inter = a & b
    union = a | b
    if not union:
        return 0.0
    num = sum(idf.get(e, 1.0) for e in inter)
    den = sum(idf.get(e, 1.0) for e in union)
    return num / den if den else 0.0


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def score(e: Signature, p: Signature, idf: dict[str, float]) -> float:
    ent = _idf_weighted_overlap(e.entities, p.entities, idf)
    thm = _jaccard(e.claim_groups, p.claim_groups)
    emb = 0.0
    if e.embedding is not None and p.embedding is not None:
        emb = max(0.0, float(e.embedding @ p.embedding))
    return W_ENT * ent + W_THM * thm + W_EMB * emb


def shared_specific(e: Signature, p: Signature, idf: dict[str, float],
                    threshold: float) -> list[str]:
    """Shared entities whose IDF clears the 'specific' bar — the anti-over-link guard."""
    return [eid for eid in (e.entities & p.entities) if idf.get(eid, 0.0) >= threshold]


def within_window(e: Signature, p: Signature, window_days: int = THREAD_WINDOW_DAYS) -> bool:
    """p must be at or before e, and no more than window_days earlier."""
    if p.ts == float("-inf") or e.ts == float("-inf"):
        return False
    delta_days = (e.ts - p.ts) / 86400.0
    return 0 <= delta_days <= window_days


def qualifies(e: Signature, p: Signature, idf: dict[str, float],
              threshold: float) -> tuple[bool, float]:
    """(links?, score). E links to P iff within window, score ≥ floor, and they
    share ≥1 specific entity."""
    if e.cluster_id == p.cluster_id or not within_window(e, p):
        return False, 0.0
    s = score(e, p, idf)
    if s < THREAD_MATCH_FLOOR:
        return False, s
    if not shared_specific(e, p, idf, threshold):
        return False, s
    return True, s
