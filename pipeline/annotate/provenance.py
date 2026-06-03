"""
M4 — Annotate: Provenance lookup
- Outlet ownership: loaded from data/sources/outlet_provenance.json (curated, cached)
- Author background: looked up via Haiku if author is a named journalist (not "Staff")
"""

import json
import re
from pathlib import Path
import anthropic

ROOT = Path(__file__).resolve().parents[2]
OUTLET_CACHE = ROOT / "data" / "sources" / "outlet_provenance.json"
AUTHOR_CACHE = ROOT / "data" / "sources" / "author_cache.json"


def load_outlet_cache() -> dict:
    if OUTLET_CACHE.exists():
        return json.loads(OUTLET_CACHE.read_text())
    return {}


def load_author_cache() -> dict:
    if AUTHOR_CACHE.exists():
        return json.loads(AUTHOR_CACHE.read_text())
    return {}


def save_author_cache(cache: dict):
    AUTHOR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    AUTHOR_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def _is_named_author(author) -> bool:
    """Return True if this looks like a real byline rather than a staff/generic credit."""
    if not author:
        return False
    generic = {"staff", "editorial", "wire", "reuters", "ap", "afp", "editors",
               "al jazeera staff", "bloomberg news", "reuters staff"}
    return author.strip().lower() not in generic


AUTHOR_SYSTEM = """You know the backgrounds of journalists and media personalities.
Given a journalist's name and their outlet, write a one-sentence factual background note:
their beat, career highlights, or relevant expertise. If you have no reliable information
about this specific person, return exactly: null
Return either the one-sentence string or the word null (no quotes, no JSON wrapping)."""


def get_author_background(author, outlet, client, cache):
    """Look up author background. Uses cache to avoid redundant API calls."""
    if not _is_named_author(author):
        return None

    cache_key = f"{author}|{outlet}"
    if cache_key in cache:
        return cache[cache_key]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=AUTHOR_SYSTEM,
        messages=[{"role": "user", "content": f"Journalist: {author}\nOutlet: {outlet}"}]
    )
    text = response.content[0].text.strip()
    result = None if text.lower() == "null" else text

    cache[cache_key] = result
    save_author_cache(cache)
    return result


def get_outlet_ownership(outlet, outlet_cache):
    """Return the ownership one-liner for a known outlet."""
    # Exact match first
    if outlet in outlet_cache:
        return outlet_cache[outlet]["ownership"]
    # Fuzzy: check if any key is a substring of the outlet name or vice versa
    outlet_lower = outlet.lower()
    for key, val in outlet_cache.items():
        if key.lower() in outlet_lower or outlet_lower in key.lower():
            return val["ownership"]
    return None
