"""
Event-image selection: Haiku proposes Commons search queries from the event
title/summary, then picks the most editorially appropriate candidate.

Two cheap Haiku calls per event. Returns None when nothing suitable clears the
license filter — an event without an image is always acceptable; a wrong or
non-free image is not.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import anthropic
from json_repair import repair_json

from pipeline.images.wikimedia import search_commons

log = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

_QUERY_PROMPT = """You are helping a news product find a *file photo* on Wikimedia Commons to illustrate a news event. Commons has portraits of public figures, photos of specific places, buildings, institutions, vehicles/equipment types, and city skylines — but NOT photos of the specific news event itself.

Event title: {title}
Event summary: {summary}

Propose 2-4 Commons search queries, most promising first. Rules:
- Prefer named public figures central to the event (e.g. "Benjamin Netanyahu"), then specific places/institutions (e.g. "Knesset building", "Strait of Hormuz"), then concrete subjects (e.g. "USS Abraham Lincoln aircraft carrier").
- Each query 1-4 words, a concrete visual subject. No abstract nouns (no "ceasefire", "negotiations", "tensions").
- Avoid queries likely to return maps, flags, logos, or charts.

Respond with JSON only: {{"queries": ["...", "..."]}}"""

_SELECT_PROMPT = """You are choosing a *file photo* to illustrate a news event on a serious, neutral news-analysis site.

Event title: {title}
Event summary: {summary}

Candidate images (from Wikimedia Commons):
{candidates}

Work in two steps.

STEP 1 — Disqualify. A candidate is DISQUALIFIED if:
- Its title or description names or depicts ANY identifiable person who is not named in the event title/summary above. A photo of the right location featuring the wrong person (e.g. a past president or another country's official) is the single worst failure — check every candidate's description for personal names and titles like "President", "Minister", "Secretary" and cross-reference against the event text.
- It is a map, flag alone, logo, chart, diagram, poster, or meme.
- It is a memorial or commemoration of an unrelated event.
- It depicts graphic violence, casualties, or otherwise editorialises the event.

STEP 2 — From the surviving candidates only, pick the best by: (1) relevance to the event's central actor or location; (2) photograph over render/illustration; (3) image quality. People-free photos of relevant places or buildings are a safe, good choice.

Respond with JSON only:
{{"disqualified": [<indices>], "choice": <index of the pick, or -1 if none survive>, "caption": "<short neutral caption for the pick, e.g. 'Benjamin Netanyahu in 2023 (file photo)'>"}}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        return json.loads(repair_json(text))


def find_event_image(event: dict, client: anthropic.Anthropic) -> dict | None:
    """
    Find a permissively-licensed image for a per-event JSON dict.
    `event` is the "event" sub-object (needs title + summary).
    Returns an image dict for embedding at event["image"], or None.
    """
    title = event.get("title", "")
    summary = event.get("summary", "")
    if not title:
        return None

    # ── 1. Haiku: search queries ──────────────────────────────────────────
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": _QUERY_PROMPT.format(title=title, summary=summary)}],
    )
    try:
        queries = _parse_json(resp.content[0].text).get("queries", [])[:4]
    except Exception as e:
        log.warning("Query-generation parse failed: %s", e)
        return None

    # ── 2. Commons search, pooled candidates ─────────────────────────────
    candidates: list[dict] = []
    seen_titles: set[str] = set()
    for q in queries:
        for cand in search_commons(q, limit=6):
            if cand["file_title"] in seen_titles:
                continue
            seen_titles.add(cand["file_title"])
            cand["query"] = q
            candidates.append(cand)
        if len(candidates) >= 18:
            break
    if not candidates:
        log.info("No license-cleared Commons candidates for %r (queries: %s)", title, queries)
        return None

    # ── 3. Haiku: pick the best candidate ─────────────────────────────────
    listing = "\n".join(
        f"[{i}] {c['file_title']} | {c['width']}x{c['height']} | {c['license']} | {c['description'] or '(no description)'}"
        for i, c in enumerate(candidates)
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": _SELECT_PROMPT.format(title=title, summary=summary, candidates=listing)}],
    )
    try:
        decision = _parse_json(resp.content[0].text)
        choice = int(decision.get("choice", -1))
    except Exception as e:
        log.warning("Selection parse failed: %s", e)
        return None

    if choice < 0 or choice >= len(candidates):
        log.info("Model rejected all %d candidates for %r", len(candidates), title)
        return None

    chosen = candidates[choice]
    return {
        "url": chosen["url"],
        "full_url": chosen["full_url"],
        "source_page": chosen["source_page"],
        "width": chosen["width"],
        "height": chosen["height"],
        "caption": (decision.get("caption") or chosen["file_title"].replace("File:", "")).strip(),
        "credit": chosen["credit"],
        "license": chosen["license"],
        "license_url": chosen["license_url"],
        "provider": "wikimedia_commons",
        "file_title": chosen["file_title"],
        "query": chosen["query"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
