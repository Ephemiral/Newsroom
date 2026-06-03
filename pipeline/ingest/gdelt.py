"""
GDELT DOC 2.0 ingest for the News Synthesis & Credibility Engine.

Uses the GDELT DOC API (via the gdeltdoc Python library) to discover articles
about a beat's keywords across the entire English-language web — regardless of
whether the outlet has a working RSS feed or not.

Key advantages over RSS-only:
- Surfaces articles from outlets not in the configured source list
- Works for bot-blocked outlets (fetches from GDELT's index, not the outlet directly)
- Updates every 15 minutes; no feed management required
- Free, no API key

Workflow:
1. Query GDELT with beat keywords → article list (url, domain, title, date)
2. Match each domain against beat's domain_map → outlet name + bias rating
3. Unknown domains → logged to data/suggested_sources.json for G's review
4. Return Article objects for known domains; skip unknowns (or optionally include)

Install: pip install gdeltdoc pandas
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from pipeline.schema import Article
from pipeline.ingest.rss import _fetch_body_rate_limited, _article_id_from_url

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SUGGESTED_SOURCES_PATH = REPO_ROOT / "data" / "suggested_sources.json"


def _extract_domain(url: str) -> str:
    """Return the registered domain from a URL (strips subdomains like www.)."""
    host = urlparse(url).netloc.lower()
    # Strip common subdomains
    for prefix in ("www.", "m.", "en.", "english."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    return host


def _load_suggested_sources() -> dict:
    if SUGGESTED_SOURCES_PATH.exists():
        return json.loads(SUGGESTED_SOURCES_PATH.read_text())
    return {}


def _save_suggested_sources(data: dict) -> None:
    SUGGESTED_SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUGGESTED_SOURCES_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _update_suggested_sources(unknown_domains: dict[str, list[str]]) -> None:
    """
    Merge newly seen unknown domains into the suggested sources log.

    unknown_domains: {domain: [sample_title, ...]}

    Each entry tracks:
      seen_count    — total articles seen from this domain across all runs
      sample_titles — up to 5 representative article titles
      first_seen    — ISO date of first appearance
      enriched      — False until the weekly task researches this domain
      reviewed      — False until G accepts or declines the source
    """
    from datetime import date
    existing = _load_suggested_sources()
    today = date.today().isoformat()
    new_count = 0
    for domain, titles in unknown_domains.items():
        if domain not in existing:
            existing[domain] = {
                "seen_count": 0,
                "sample_titles": [],
                "first_seen": today,
                "enriched": False,
                "reviewed": False,
            }
            new_count += 1
        existing[domain]["seen_count"] += len(titles)
        existing[domain]["sample_titles"] = (
            existing[domain]["sample_titles"] + titles
        )[:5]
    _save_suggested_sources(existing)
    log.info(
        "Source discovery: %d new domain(s), %d total unknown — %s",
        new_count, len(existing), SUGGESTED_SOURCES_PATH.relative_to(REPO_ROOT),
    )


def ingest_gdelt(
    beat_config: dict,
    fetch_body: bool = True,
    include_unknown_domains: bool = False,
) -> list[Article]:
    """
    Query GDELT DOC API and return Article objects for the beat.

    Args:
        beat_config: parsed beat JSON dict.
        fetch_body: if True, fetch full article text via trafilatura.
        include_unknown_domains: if True, also return articles from domains
            not in domain_map (with outlet='Unknown', bias_rating=None).
            Default False — unknown domains are logged only.

    Returns:
        List of Article objects (dedup handled by ArticleStore in run.py).
    """
    try:
        from gdeltdoc import GdeltDoc, Filters
    except ImportError:
        log.error(
            "gdeltdoc not installed. Run: pip install gdeltdoc pandas"
        )
        return []

    gdelt_config = beat_config.get("gdelt", {})
    if not gdelt_config.get("enabled", False):
        log.info("GDELT ingest disabled in beat config.")
        return []

    domain_map: dict[str, dict] = beat_config.get("domain_map", {})
    beat_name = beat_config.get("beat", "unknown")
    today = datetime.now(timezone.utc).date().isoformat()

    keywords = gdelt_config.get("keywords", [])
    if not keywords:
        log.warning("GDELT: no keywords configured.")
        return []

    # GDELT OR-joins a list of keywords
    keyword_query = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords)
    timespan = gdelt_config.get("timespan", "24h")
    max_records = min(gdelt_config.get("max_records", 250), 250)
    language = gdelt_config.get("language", "English")

    log.info(
        "GDELT query: keywords=%r timespan=%s max=%d lang=%s",
        keyword_query, timespan, max_records, language,
    )

    try:
        gd = GdeltDoc()
        f = Filters(
            keyword=keyword_query,
            timespan=timespan,
            num_records=max_records,
            language=language,
        )
        df = gd.article_search(f)
    except Exception as e:
        log.error("GDELT query failed: %s", e)
        return []

    if df is None or df.empty:
        log.info("GDELT returned no articles.")
        return []

    log.info("GDELT returned %d articles.", len(df))

    # Match domains → outlet metadata
    articles: list[Article] = []
    unknown_domains: dict[str, list[str]] = defaultdict(list)

    for _, row in df.iterrows():
        url = row.get("url", "")
        title = str(row.get("title", "")).strip()
        seen_date = str(row.get("seendate", ""))
        raw_domain = str(row.get("domain", ""))

        if not url or not title:
            continue

        # Normalize domain
        domain = _extract_domain(url) or raw_domain.lower()

        outlet_meta = domain_map.get(domain)
        if outlet_meta is None:
            # Try stripping one more subdomain level
            parts = domain.split(".")
            if len(parts) > 2:
                shorter = ".".join(parts[-2:])
                outlet_meta = domain_map.get(shorter)

        if outlet_meta is None:
            unknown_domains[domain].append(title)
            if not include_unknown_domains:
                continue
            outlet_meta = {"outlet": domain, "bias_rating": None, "bias_rating_source": None}

        # Parse GDELT date (format: 20240510T123456Z)
        published_at = ""
        try:
            dt = datetime.strptime(seen_date[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            published_at = dt.isoformat()
        except Exception:
            pass

        # Fetch body text
        body_text = ""
        if fetch_body:
            body_text = _fetch_body_rate_limited(url)

        articles.append(Article(
            article_id=_article_id_from_url(url),
            event_id=None,
            outlet=outlet_meta["outlet"],
            url=url,
            author=None,
            published_at=published_at,
            title=title,
            body_text=body_text,
            bias_rating=outlet_meta.get("bias_rating"),
            bias_rating_source=outlet_meta.get("bias_rating_source"),
            collected_at=today,
            beat=beat_name,
        ))

    log.info(
        "GDELT: %d articles matched known domains, %d from unknown domains%s.",
        len(articles),
        sum(len(v) for v in unknown_domains.values()),
        " (logged)" if unknown_domains else "",
    )

    if unknown_domains:
        _update_suggested_sources(dict(unknown_domains))

    return articles
