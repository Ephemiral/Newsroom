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

_QUERY_PROMPT = """You are helping a news product find a *file photo* from open image libraries (Wikimedia Commons, Openverse) to illustrate a news event. These libraries have portraits of public figures, photos of specific places, buildings, institutions, vehicle/vessel/equipment types, and generic editorial subjects — but NOT photos of the specific news event itself.

Event title: {title}
Event summary: {summary}
{exclusion_note}
First, identify the event's DISTINCTIVE VISUAL ANGLE — what makes this story different from adjacent stories on the same beat. A military escalation story, a shipping/trade story, and a diplomatic-talks story about the same region should each get a different kind of image (e.g. warships / cargo vessels at sea / a negotiating venue).

Then propose 3-5 search queries, most promising first, mixing:
- named public figures central to the event (e.g. "Benjamin Netanyahu"),
- specific places/institutions (e.g. "Knesset building", "Kuwait International Airport"),
- generic-but-evocative subjects expressing the angle (e.g. "cargo ship at sea", "naval warship Persian Gulf", "oil tanker", "press conference podium").

Rules: each query 1-4 words, a concrete visual subject. No abstract nouns (no "ceasefire", "dispute", "tensions"). Avoid queries likely to return maps, flags, logos, or charts.

Respond with JSON only: {{"queries": ["...", "..."]}}"""

_SELECT_PROMPT = """You are choosing a *file photo* to illustrate a news event on a serious, neutral news-analysis site.

Event title: {title}
Event summary: {summary}

Candidate images (from Wikimedia Commons and Openverse):
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


def find_event_image(event: dict, client: anthropic.Anthropic,
                     exclude_titles: set[str] | None = None) -> dict | None:
    """
    Find a permissively-licensed image for a per-event JSON dict.
    `event` is the "event" sub-object (needs title + summary).
    `exclude_titles`: file_titles already used by other events — never reuse an
    image across events, even for similar stories (each event should look distinct).
    Returns an image dict for embedding at event["image"], or None.
    """
    title = event.get("title", "")
    summary = event.get("summary", "")
    if not title:
        return None
    exclude_titles = exclude_titles or set()

    # ── 1. Haiku: search queries ──────────────────────────────────────────
    exclusion_note = ""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": _QUERY_PROMPT.format(
            title=title, summary=summary, exclusion_note=exclusion_note)}],
    )
    try:
        queries = _parse_json(resp.content[0].text).get("queries", [])[:5]
    except Exception as e:
        log.warning("Query-generation parse failed: %s", e)
        return None

    # ── 2. Provider search, pooled candidates ─────────────────────────────
    # Commons first (strongest on public figures/landmarks, best metadata);
    # Openverse widens the pool for generic editorial subjects.
    from pipeline.images.openverse import search_openverse

    candidates: list[dict] = []
    seen_titles: set[str] = set(exclude_titles)
    for q in queries:
        for cand in search_commons(q, limit=6) + search_openverse(q, limit=6):
            if cand["file_title"] in seen_titles:
                continue
            seen_titles.add(cand["file_title"])
            cand["query"] = q
            candidates.append(cand)
        if len(candidates) >= 24:
            break
    if not candidates:
        log.info("No license-cleared candidates for %r (queries: %s)", title, queries)
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
        "provider": chosen.get("provider", "wikimedia_commons"),
        "file_title": chosen["file_title"],
        "query": chosen["query"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
