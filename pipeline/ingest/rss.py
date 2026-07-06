"""
RSS ingester for the News Synthesis & Credibility Engine.

Reads a beat config, walks each source's RSS feed, fetches full article body
text via trafilatura, and yields Article objects in the pipeline schema.

Body fetching is concurrent (ThreadPoolExecutor) with per-domain rate limiting:
each domain gets at most one request per DOMAIN_REQUEST_DELAY seconds, but
multiple domains are fetched simultaneously. On a 10-source beat this typically
reduces ingest time from ~10 minutes to ~1 minute.

Usage (from run.py — not called directly):
    articles = list(ingest_beat(beat_config))
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Generator, Optional
from urllib.parse import urlparse, urlunparse

import feedparser
import trafilatura
import trafilatura.settings

from pipeline.schema import Article

log = logging.getLogger(__name__)

# Seconds between requests to the same domain (per-domain, not global)
DOMAIN_REQUEST_DELAY = 1.0

# Max simultaneous fetches across all domains
MAX_CONCURRENT_FETCHES = 8

# Realistic browser User-Agent — many outlets block the default feedparser UA
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Trafilatura config: favour quality, include comments=False
_TRAF_CONFIG = trafilatura.settings.use_config()
_TRAF_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "15")

# Per-domain rate-limiting state (thread-safe)
_domain_registry_lock = threading.Lock()
_domain_locks: dict[str, threading.Lock] = {}
_domain_last_fetch: dict[str, float] = {}


def _get_domain_lock(domain: str) -> threading.Lock:
    """Return (and lazily create) the per-domain lock + last-fetch timestamp."""
    with _domain_registry_lock:
        if domain not in _domain_locks:
            _domain_locks[domain] = threading.Lock()
            _domain_last_fetch[domain] = 0.0
        return _domain_locks[domain]


def _normalise_url(url: str) -> str:
    """Lowercase scheme+host, strip fragment and common tracking params."""
    p = urlparse(url.strip())
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, "", "", ""))


def _article_id_from_url(url: str) -> str:
    """Stable short ID derived from the normalised URL."""
    h = hashlib.sha256(_normalise_url(url).encode()).hexdigest()[:10]
    return f"art_{h}"


def _parse_date(entry) -> str:
    """Return ISO 8601 string from a feedparser entry, or empty string."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    return ""


def _fetch_body(url: str) -> str:
    """Download page and extract main body text via trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        text = trafilatura.extract(
            downloaded,
            config=_TRAF_CONFIG,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
        )
        return text or ""
    except Exception as e:
        log.warning("Body fetch failed for %s: %s", url, e)
        return ""


def _fetch_body_rate_limited(url: str) -> str:
    """
    Fetch body with per-domain rate limiting (thread-safe).
    Acquires a per-domain lock, waits if needed, then fetches.
    Multiple domains proceed in parallel; same-domain requests are serialised.
    """
    domain = urlparse(url).netloc
    lock = _get_domain_lock(domain)
    with lock:
        elapsed = time.monotonic() - _domain_last_fetch[domain]
        wait = DOMAIN_REQUEST_DELAY - elapsed
        if wait > 0:
            time.sleep(wait)
        _domain_last_fetch[domain] = time.monotonic()
    return _fetch_body(url)


def _author_from_entry(entry) -> Optional[str]:
    if hasattr(entry, "author") and entry.author:
        return entry.author
    if hasattr(entry, "authors") and entry.authors:
        names = [a.get("name", "") for a in entry.authors if a.get("name")]
        return ", ".join(names) if names else None
    return None


def ingest_beat(
    beat_config: dict,
    fetch_body: bool = True,
    max_per_source: Optional[int] = None,
) -> Generator[Article, None, None]:
    """
    Yield Article objects for every item found in the beat's RSS sources.

    RSS feeds are parsed sequentially (fast). Body fetching is concurrent:
    up to MAX_CONCURRENT_FETCHES simultaneous requests, with per-domain
    rate limiting so no single outlet is hammered.

    Args:
        beat_config: parsed beat JSON dict (from config/beats/*.json).
        fetch_body: if True, fetch full article text concurrently.
                    Set False for fast testing (uses RSS summary instead).
        max_per_source: cap articles per source (useful during development).
    """
    beat_name = beat_config.get("beat", "unknown")
    today = datetime.now(timezone.utc).date().isoformat()

    # ── Phase 1: parse all RSS feeds and collect candidate entries ─────────
    # This is fast (one HTTP request per source, no body fetching yet).
    pending: list[dict] = []   # list of article metadata dicts, body_text=None

    for source in beat_config.get("sources", []):
        rss_url = source.get("rss")
        outlet = source.get("outlet", "Unknown")
        bias_rating = source.get("bias_rating")
        bias_rating_source = source.get("bias_rating_source")
        topic_filter = source.get("topic_filter", [])
        fallback_url = source.get("rss_fallback")

        if not rss_url:
            log.warning("Source '%s' has no RSS URL — skipping.", outlet)
            continue

        log.info("Fetching RSS: %s (%s)", outlet, rss_url)

        try:
            feed = feedparser.parse(rss_url, agent=_USER_AGENT)
        except Exception as e:
            log.error("Failed to parse RSS for %s: %s", outlet, e)
            continue

        if feed.bozo and not feed.entries:
            log.warning("RSS parse warning for %s: %s", outlet, feed.bozo_exception)

        # Fallback URL if primary returned nothing
        if not feed.entries and fallback_url:
            log.warning("Primary RSS empty for %s — trying fallback: %s", outlet, fallback_url)
            try:
                feed = feedparser.parse(fallback_url, agent=_USER_AGENT)
            except Exception as e:
                log.error("Fallback RSS also failed for %s: %s", outlet, e)
                continue

        entries = feed.entries
        if max_per_source:
            entries = entries[:max_per_source]

        filtered_out = 0
        for entry in entries:
            url = getattr(entry, "link", None)
            if not url:
                continue

            title = getattr(entry, "title", "").strip()

            # topic_filter: skip if none of the keywords match title or summary
            if topic_filter:
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                haystack = (title + " " + summary).lower()
                if not any(kw.lower() in haystack for kw in topic_filter):
                    filtered_out += 1
                    continue

            pending.append({
                "url": url,
                "title": title,
                "author": _author_from_entry(entry),
                "published_at": _parse_date(entry),
                "outlet": outlet,
                "bias_rating": bias_rating,
                "bias_rating_source": bias_rating_source,
                "state_alignment": source.get("state_alignment"),
                "summary": getattr(entry, "summary", "") or getattr(entry, "description", "") or "",
            })

        if filtered_out:
            log.info("  %s: filtered out %d off-topic entries (topic_filter active)", outlet, filtered_out)

    log.info("RSS phase complete — %d candidate articles to fetch", len(pending))

    # ── Phase 2: fetch bodies concurrently ─────────────────────────────────
    if not fetch_body:
        # Fast path: use RSS summaries, no HTTP fetching
        for meta in pending:
            yield Article(
                article_id=_article_id_from_url(meta["url"]),
                event_id=None,
                outlet=meta["outlet"],
                url=meta["url"],
                author=meta["author"],
                published_at=meta["published_at"],
                title=meta["title"],
                body_text=meta["summary"],
                bias_rating=meta["bias_rating"],
                bias_rating_source=meta["bias_rating_source"],
                collected_at=today,
                beat=beat_name,
                state_alignment=meta.get("state_alignment"),
            )
        return

    # Concurrent fetch with per-domain rate limiting
    log.info(
        "Fetching %d article bodies (max %d concurrent, %.1fs per-domain delay)…",
        len(pending), MAX_CONCURRENT_FETCHES, DOMAIN_REQUEST_DELAY,
    )

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_FETCHES) as pool:
        future_to_meta = {
            pool.submit(_fetch_body_rate_limited, meta["url"]): meta
            for meta in pending
        }
        done = 0
        for future in as_completed(future_to_meta):
            meta = future_to_meta[future]
            try:
                body_text = future.result()
            except Exception as e:
                log.warning("Body fetch error for %s: %s", meta["url"], e)
                body_text = ""

            done += 1
            if done % 20 == 0 or done == len(pending):
                log.info("  fetched %d / %d", done, len(pending))

            yield Article(
                article_id=_article_id_from_url(meta["url"]),
                event_id=None,
                outlet=meta["outlet"],
                url=meta["url"],
                author=meta["author"],
                published_at=meta["published_at"],
                title=meta["title"],
                body_text=body_text,
                bias_rating=meta["bias_rating"],
                bias_rating_source=meta["bias_rating_source"],
                collected_at=today,
                beat=beat_name,
                state_alignment=meta.get("state_alignment"),
            )
