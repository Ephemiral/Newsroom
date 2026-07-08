"""
Machine-enforced entity safety validator (STAGE_7 safety gate).

Per G's 2026-07-08 decision there is no human review step; THIS is the
safeguard that makes automatic publishing of person content acceptable:

1. Every fact must carry a source link — a fact without source_url is DROPPED.
2. Every fact must carry a valid tier label — unlabeled facts are DROPPED.
3. An `allegation` about a person must be attributed meta-coverage: it needs a
   source link AND an `attributed_to` naming the outlet/source; the frontend
   renders it as "Alleged by [source] →", never the system's own assertion.
4. Summary/roles/connections without citations are stripped the same way.

Dropped items are logged loudly, never published. If validation leaves a card
with no content, the entity still resolves — the frontend renders its mention
as plain text, not a broken card.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

VALID_TIERS = {"verified", "reported", "disputed", "allegation"}


def validate_entity(record: dict) -> dict:
    """Enforce the safety rules on one entity record. Mutates and returns it.
    Records what was dropped in the change_log is deliberately NOT done —
    dropped content was never published, so there is nothing to disclose."""
    eid = record.get("entity_id", "?")
    is_person = record.get("type") == "person"

    # Rule 4 first: uncited summary is cleared (thin card beats uncited card).
    if record.get("summary") and not record.get("summary_sources"):
        log.warning("[%s] summary dropped: no citation", eid)
        record["summary"] = None

    kept_facts = []
    for fact in record.get("facts", []):
        text = (fact.get("text") or "")[:60]
        if not fact.get("source_url"):
            log.warning("[%s] fact dropped (no source link): %s…", eid, text)
            continue
        tier = fact.get("confidence_tier")
        if tier not in VALID_TIERS:
            log.warning("[%s] fact dropped (missing/invalid tier %r): %s…", eid, tier, text)
            continue
        if is_person and tier == "allegation" and not fact.get("attributed_to"):
            log.warning("[%s] person allegation dropped (no attributed_to): %s…", eid, text)
            continue
        kept_facts.append(fact)
    record["facts"] = kept_facts

    kept_roles = []
    for r in record.get("roles_affiliations", []):
        if r.get("source_url"):
            kept_roles.append(r)
        else:
            log.warning("[%s] role dropped (no source): %s", eid, r.get("role"))
    record["roles_affiliations"] = kept_roles

    kept_connections = []
    for c in record.get("connections", []):
        if c.get("source_url"):
            kept_connections.append(c)
        else:
            log.warning("[%s] connection dropped (no source): %s", eid, c.get("type"))
    record["connections"] = kept_connections

    # Image must carry its attribution fields (license requirement).
    img = record.get("image")
    if img and not (img.get("credit") and img.get("license") and img.get("source_page")):
        log.warning("[%s] image dropped: incomplete attribution", eid)
        record["image"] = None

    return record
