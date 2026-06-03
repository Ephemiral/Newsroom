"""
Shared article schema for the News Synthesis & Credibility Engine pipeline.

Every stage (ingest, cluster, analyze, annotate, generate) reads and writes
articles using this structure. It matches the golden dataset field names exactly
so that golden and live-ingested articles are interchangeable downstream.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import os


@dataclass
class Article:
    # Identity
    article_id: str                      # e.g. "art_001"
    event_id: Optional[str]             # e.g. "event_001"; None for freshly ingested articles

    # Provenance
    outlet: str                          # e.g. "Al Jazeera English"
    url: str                             # canonical URL
    author: Optional[str]               # byline, or None
    published_at: str                    # ISO 8601 string, e.g. "2026-05-28T19:03:50Z"
    title: str

    # Content
    body_text: str                       # full article text (local dev fixture only)

    # Bias
    bias_rating: Optional[str]          # "left" | "center-left" | "center" | "center-right" | "right"
    bias_rating_source: Optional[str]   # "AllSides" | "GroundNews" | "MBFC"

    # Collection metadata
    collected_at: str                    # ISO 8601 date string, e.g. "2026-05-31"
    beat: Optional[str] = None          # beat name this article was ingested for

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> "Article":
        return cls(
            article_id=d["article_id"],
            event_id=d.get("event_id"),
            outlet=d["outlet"],
            url=d["url"],
            author=d.get("author"),
            published_at=d.get("published_at", ""),
            title=d["title"],
            body_text=d.get("body_text", ""),
            bias_rating=d.get("bias_rating"),
            bias_rating_source=d.get("bias_rating_source"),
            collected_at=d.get("collected_at", ""),
            beat=d.get("beat"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "Article":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
