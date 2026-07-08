"""
Entity extraction + disambiguation + per-event relevance (Haiku) — STAGE_7.

Three small Haiku calls per event (extraction and relevance always; one
disambiguation call only when a mention fuzzily matches an existing store
entity). Token usage is logged per call (B-14 pattern).
"""

from __future__ import annotations

import json
import logging

import anthropic

from pipeline.analyze.extract import _parse_json_response

log = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

EXTRACT_SYSTEM = """You identify the key entities in a news report for a reader-facing "entity card" feature.

Entity types:
- person: named individuals central to the story
- organization: agencies, militaries, militant groups, companies, ministries
- political_party
- technology: weapon systems, platforms, defense systems, notable equipment
- location: ONLY places whose strategic, economic, or symbolic significance matters to understanding the story (a nuclear site, a shipping chokepoint, a contested city). NOT ordinary datelines.

Rules:
- Select at most 8 entities — the ones a reader would actually want background on. Key actors, not every proper noun.
- NEVER include news outlets or journalists reporting the story (they are covered by a separate provenance layer).
- surfaces: the EXACT strings as they appear in the report text (all variants used, e.g. "Benjamin Netanyahu" and "Netanyahu").
- canonical_name: the full formal name.
- context: one line on who/what this is IN THIS STORY (used for disambiguation, not shown to readers).

CRITICAL: Output a valid JSON array only. No prose. Each element:
{"canonical_name": "...", "type": "person|organization|political_party|technology|location|other", "surfaces": ["..."], "context": "..."}"""

DISAMBIG_SYSTEM = """You decide whether a mention in a news story refers to the same real-world entity as an existing record.

Answer with valid JSON only: {"same": true/false, "confidence": "high"|"low", "reason": "..."}
- "same": true only if they are clearly the same person/organization/thing.
- If you cannot be confident (different roles, plausible namesakes, insufficient information), answer same=false or confidence="low". A wrong merge is far worse than a duplicate."""

RELEVANCE_SYSTEM = """For each entity below, write a 1-2 sentence "relevance_to_event" note: why this entity matters to THIS specific story. Neutral, factual, grounded ONLY in the report/claims provided — never your own knowledge or speculation about motives.

CRITICAL: Output valid JSON only: {"<canonical_name>": "relevance text", ...}"""

IDENTITY_SYSTEM = """You check whether a Wikidata search hit refers to the same real-world entity as a mention in a news story.

Answer with valid JSON only: {"same": true/false, "confidence": "high"|"low", "reason": "..."}
- Compare the mention's role/context in the story against the Wikidata label and description.
- Namesakes are common. If the description suggests a different occupation, era, or domain than the story context, answer same=false.
- If you cannot be confident, answer same=false or confidence="low". Grounding a person to the WRONG identity is far worse than leaving the card thin."""


def _call(client: anthropic.Anthropic, system: str, user: str, label: str,
          max_tokens: int = 1500, usage_log: list | None = None):
    resp = client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    if usage_log is not None:
        usage_log.append({"call": label, "model": MODEL,
                          "in": resp.usage.input_tokens, "out": resp.usage.output_tokens})
    log.info("entities/%s: %d in / %d out tokens", label,
             resp.usage.input_tokens, resp.usage.output_tokens)
    return _parse_json_response(resp.content[0].text, resp.stop_reason, f"entities/{label}")


def _event_text(event_data: dict, max_chars: int = 9000) -> str:
    """Report paragraphs + summary + background — what the reader actually sees."""
    parts = [event_data.get("event", {}).get("title", ""),
             event_data.get("event", {}).get("summary", "")]
    report = event_data.get("report") or {}
    for p in report.get("paragraphs", []):
        parts.append(p.get("text", ""))
    for b in event_data.get("background", []):
        parts.append(b.get("point", ""))
    return "\n\n".join(x for x in parts if x)[:max_chars]


def extract_entities(event_data: dict, client: anthropic.Anthropic,
                     usage_log: list | None = None) -> list[dict]:
    """Candidate entities from one event's reader-facing text."""
    text = _event_text(event_data)
    if not text.strip():
        return []
    raw = _call(client, EXTRACT_SYSTEM, f"News report:\n\n{text}",
                "extract", usage_log=usage_log)
    out = []
    for c in raw if isinstance(raw, list) else []:
        if not isinstance(c, dict) or not c.get("canonical_name"):
            continue
        c.setdefault("type", "other")
        c.setdefault("surfaces", [c["canonical_name"]])
        c.setdefault("context", "")
        out.append(c)
    return out[:8]


def disambiguate(candidate: dict, existing_record: dict, client: anthropic.Anthropic,
                 usage_log: list | None = None) -> bool:
    """True only when Haiku is HIGH-confidence the mention == the stored entity."""
    user = json.dumps({
        "mention": {"name": candidate["canonical_name"], "type": candidate["type"],
                    "context_in_story": candidate["context"]},
        "existing_record": {"canonical_name": existing_record["canonical_name"],
                            "type": existing_record["type"],
                            "aliases": existing_record.get("aliases", []),
                            "summary": existing_record.get("summary"),
                            "roles": [r["role"] for r in existing_record.get("roles_affiliations", [])]},
    }, ensure_ascii=False)
    try:
        verdict = _call(client, DISAMBIG_SYSTEM, user, "disambiguate",
                        max_tokens=200, usage_log=usage_log)
        return bool(verdict.get("same")) and verdict.get("confidence") == "high"
    except Exception:
        log.warning("Disambiguation failed for %s — treating as NOT the same (safe default)",
                    candidate["canonical_name"])
        return False


def confirm_identity(name: str, context: str, hit: dict, client: anthropic.Anthropic,
                     usage_log: list | None = None) -> bool:
    """True only when Haiku is HIGH-confidence a Wikidata hit is the mentioned
    entity (namesake guard for person grounding)."""
    user = json.dumps({
        "mention": {"name": name, "context_in_story": context},
        "wikidata_candidate": {"label": hit.get("label"), "description": hit.get("description")},
    }, ensure_ascii=False)
    try:
        verdict = _call(client, IDENTITY_SYSTEM, user, "identity",
                        max_tokens=200, usage_log=usage_log)
        return bool(verdict.get("same")) and verdict.get("confidence") == "high"
    except Exception:
        log.warning("Identity check failed for %s — NOT grounding (safe default)", name)
        return False


def relevance_notes(event_data: dict, entities: list[dict], client: anthropic.Anthropic,
                    usage_log: list | None = None) -> dict[str, str]:
    """{canonical_name: relevance_to_event} for all entities in one call."""
    if not entities:
        return {}
    text = _event_text(event_data, max_chars=7000)
    names = [e["canonical_name"] for e in entities]
    user = f"News report:\n\n{text}\n\nEntities: {json.dumps(names, ensure_ascii=False)}"
    try:
        result = _call(client, RELEVANCE_SYSTEM, user, "relevance", usage_log=usage_log)
        return {k: v for k, v in result.items() if isinstance(v, str) and v.strip()}
    except Exception:
        log.warning("Relevance call failed — entities publish without event notes")
        return {}
