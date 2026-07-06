"""
Openverse image search — second provider for the event image stage.

Openverse (openverse.org, a WordPress/WP-Engine project) indexes ~800M
openly-licensed images from Flickr, museums, and other sources, with
machine-readable license metadata and a keyless public API. Used to widen the
candidate pool when Wikimedia Commons comes up short — Commons is strong on
public figures and landmarks but thin on generic editorial subjects
("cargo ship at sea", "naval convoy").

Same license policy as wikimedia.py: CC0 / CC BY / CC BY-SA / public domain
only. Attribution fields are preserved and must be rendered by the front end.

Note: anonymous API access is rate-limited; at pipeline volume (a handful of
queries per publish cycle) this is fine, but failures are treated as
non-fatal — the caller just gets fewer candidates.
"""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

API_URL = "https://api.openverse.org/v1/images/"
ACCEPTED_LICENSES = "cc0,by,by-sa,pdm"
MIN_SOURCE_WIDTH = 500

_HEADERS = {
    "User-Agent": "CritiqalNewsroom/0.1 (news synthesis research; kafri.sg@gmail.com)"
}

_LICENSE_LABEL = {
    "cc0": "CC0",
    "by": "CC BY",
    "by-sa": "CC BY-SA",
    "pdm": "Public domain",
}


def search_openverse(query: str, limit: int = 8, timeout: int = 20) -> list[dict]:
    """Search Openverse; return candidates in the same shape as search_commons()."""
    params = {
        "q": query,
        "license": ACCEPTED_LICENSES,
        "per_page": limit,
        "filter_dead": "true",
    }
    try:
        resp = requests.get(API_URL, params=params, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except Exception as e:
        log.warning("Openverse search failed for %r: %s", query, e)
        return []

    candidates = []
    for r in results[:limit]:  # API sometimes ignores per_page
        if (r.get("width") or 0) < MIN_SOURCE_WIDTH:
            continue
        lic = (r.get("license") or "").lower()
        if lic not in _LICENSE_LABEL:
            continue
        version = r.get("license_version") or ""
        license_name = f"{_LICENSE_LABEL[lic]} {version}".strip()
        candidates.append({
            "file_title": f"openverse:{r.get('id', '')}|{(r.get('title') or 'Untitled')[:120]}",
            "description": (r.get("title") or "")[:300],
            "url": r.get("url"),
            "full_url": r.get("url"),
            "source_page": r.get("foreign_landing_url") or r.get("url"),
            "width": r.get("width"),
            "height": r.get("height"),
            "credit": r.get("creator") or "Unknown author",
            "license": license_name,
            "license_url": r.get("license_url"),
            "date_taken": "",
            "provider": "openverse",
        })
    return candidates
