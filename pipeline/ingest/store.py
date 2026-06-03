"""
Deduplication and storage for ingested articles.

Writes articles as art_<hash>.json under data/ingested/<beat>/.
The layout mirrors data/golden/ so downstream stages treat both identically.

Dedup strategy:
  Primary:   normalised URL (scheme+host+path, lowercase, no fragment/tracking)
  Secondary: near-duplicate title within the same outlet (optional, off by default)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, urlunparse

from pipeline.schema import Article

log = logging.getLogger(__name__)


def _normalise_url(url: str) -> str:
    p = urlparse(url.strip())
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, "", "", ""))


class ArticleStore:
    """
    Manages storage and deduplication for one beat's ingested articles.

    Usage:
        store = ArticleStore("data/ingested", beat="israel_middle_east")
        for article in rss.ingest_beat(config):
            saved = store.save(article)
            if saved:
                print(f"Saved: {article.title}")
    """

    def __init__(self, base_dir: str, beat: str):
        self.beat = beat
        self.beat_dir = Path(base_dir) / beat
        self.beat_dir.mkdir(parents=True, exist_ok=True)
        self._seen_urls: set[str] = self._load_seen_urls()

    def _load_seen_urls(self) -> set[str]:
        """Read all existing article files to build the dedup index."""
        seen = set()
        for path in self.beat_dir.glob("art_*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                url = data.get("url", "")
                if url:
                    seen.add(_normalise_url(url))
            except Exception as e:
                log.warning("Could not read %s for dedup index: %s", path, e)
        log.info("Dedup index loaded: %d existing articles for beat '%s'", len(seen), self.beat)
        return seen

    def is_duplicate(self, article: Article) -> bool:
        return _normalise_url(article.url) in self._seen_urls

    def save(self, article: Article) -> bool:
        """
        Write article to disk if not already stored.
        Returns True if saved, False if duplicate.
        """
        norm = _normalise_url(article.url)
        if norm in self._seen_urls:
            log.debug("Duplicate skipped: %s", article.url)
            return False

        path = self.beat_dir / f"{article.article_id}.json"
        # Handle rare hash collision: append suffix
        if path.exists():
            path = self.beat_dir / f"{article.article_id}_b.json"

        article.save(str(path))
        self._seen_urls.add(norm)
        log.info("Saved: [%s] %s", article.outlet, article.title[:80])
        return True

    def load_all(self) -> list[Article]:
        """Return all stored articles for this beat."""
        articles = []
        for path in sorted(self.beat_dir.glob("art_*.json")):
            try:
                articles.append(Article.from_json_file(str(path)))
            except Exception as e:
                log.warning("Could not load %s: %s", path, e)
        return articles


def load_golden(golden_dir: str, event_id: Optional[str] = None) -> list[Article]:
    """
    Load articles from the golden dataset.
    If event_id is given, loads only that event's articles; otherwise loads all.
    """
    base = Path(golden_dir)
    articles = []

    events = [base / event_id] if event_id else sorted(base.iterdir())

    for event_path in events:
        articles_dir = event_path / "articles"
        if not articles_dir.exists():
            continue
        for path in sorted(articles_dir.glob("art_*.json")):
            try:
                articles.append(Article.from_json_file(str(path)))
            except Exception as e:
                log.warning("Could not load golden article %s: %s", path, e)

    log.info("Loaded %d golden articles%s", len(articles),
             f" for event '{event_id}'" if event_id else "")
    return articles
