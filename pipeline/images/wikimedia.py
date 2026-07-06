"""
Wikimedia Commons image search for the event image stage.

Why Wikimedia Commons: every file is under a free license (or public domain),
the API returns machine-readable license + attribution metadata, and Wikimedia
explicitly permits hotlinking from upload.wikimedia.org. This keeps the product
clear of the copyright exposure documented in 00_MASTER_DOCUMENT.md §7 — we
never touch publisher photography.

Only permissive licenses are accepted (CC0, CC BY, CC BY-SA, public domain).
NC (non-commercial) and ND (no-derivatives) variants are rejected outright.
Attribution fields are preserved in the returned candidate and must be
rendered by the front end wherever the image is shown.
"""

from __future__ import annotations

import html
import logging
import re

import requests

log = logging.getLogger(__name__)

API_URL = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 1200
MIN_SOURCE_WIDTH = 500
ACCEPTED_MIME = {"image/jpeg", "image/png", "image/webp"}

# Accepted license short-names (case-insensitive prefix match after normalisation).
_LICENSE_OK = re.compile(r"^(cc0|cc[ -]by(-sa)?([ -][0-9.]+.*)?|public domain|pdm|no restrictions)", re.I)
_LICENSE_BAD = re.compile(r"\b(nc|nd)\b", re.I)

_TAG_RE = re.compile(r"<[^>]+>")

_HEADERS = {
    # Commons asks API clients to identify themselves.
    "User-Agent": "CritiqalNewsroom/0.1 (news synthesis research; kafri.sg@gmail.com)"
}


def _strip_html(value: str) -> str:
    """Commons metadata fields (Artist, ImageDescription) arrive as HTML."""
    return html.unescape(_TAG_RE.sub("", value or "")).strip()


def license_acceptable(short_name: str) -> bool:
    if not short_name:
        return False
    name = short_name.strip()
    if _LICENSE_BAD.search(name.replace("BY", "")):  # don't let "BY" trip the ND/NC check
        return False
    return bool(_LICENSE_OK.match(name))


def search_commons(query: str, limit: int = 8, timeout: int = 20) -> list[dict]:
    """
    Search Commons file namespace for `query`; return license-cleared candidates.

    Each candidate dict carries everything needed to embed AND attribute:
        file_title, description, url (thumb), full_url, source_page,
        width, height, credit, license, license_url
    """
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,  # File:
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": THUMB_WIDTH,
        "format": "json",
    }
    try:
        resp = requests.get(API_URL, params=params, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning("Commons search failed for %r: %s", query, e)
        return []

    candidates = []
    for page in data.get("query", {}).get("pages", {}).values():
        infos = page.get("imageinfo")
        if not infos:
            continue
        ii = infos[0]
        em = ii.get("extmetadata", {})

        def meta(key: str) -> str:
            return (em.get(key) or {}).get("value") or ""

        license_name = meta("LicenseShortName")
        if not license_acceptable(license_name):
            continue
        if ii.get("mime") not in ACCEPTED_MIME:
            continue
        if (ii.get("width") or 0) < MIN_SOURCE_WIDTH:
            continue

        candidates.append({
            "file_title": page.get("title", ""),
            "description": _strip_html(meta("ImageDescription"))[:300],
            "url": ii.get("thumburl") or ii.get("url"),
            "full_url": ii.get("url"),
            "source_page": ii.get("descriptionurl"),
            "width": ii.get("thumbwidth") or ii.get("width"),
            "height": ii.get("thumbheight") or ii.get("height"),
            "credit": _strip_html(meta("Artist")) or "Unknown author",
            "license": license_name,
            "license_url": meta("LicenseUrl") or None,
            "date_taken": _strip_html(meta("DateTimeOriginal"))[:40],
        })
    return candidates
