"""
Thread title + chapter summaries (STAGE_8) — the only paid calls in threading.

Titles are neutral and human-overridable (a loaded title on the Threads tab is
a visible trust risk); chapter summaries state what an event ADDED to the story,
grounded strictly in that event's own report — never cross-event speculation.
"""

from __future__ import annotations

import json
import logging

import anthropic

from pipeline.analyze.extract import _parse_json_response

log = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

TITLE_SYSTEM = """You name an ongoing news story that several reports belong to.

Return valid JSON only: {"title": "...", "summary": "..."}
- title: a short, NEUTRAL noun phrase naming the story (e.g. "US–Iran nuclear negotiations", "Gaza governance transition"). No verbs of judgement, no side's framing, no adjectives that characterise ("brutal", "historic"). Parallel and even-handed — a reader from any side should find it fair.
- summary: one neutral sentence on what the ongoing story is about.
Name the STORY, not any single event in it."""

CHAPTER_SYSTEM = """You write a one-sentence note on what a new report ADDED to a developing story the reader is already following.

Return valid JSON only: {"chapter_summary": "..."}
- One sentence, factual, grounded ONLY in the new report provided. Do not restate the whole story; state what is NEW in this development.
- Neutral language; attribute contested points rather than asserting them.
- If this is the first report in the story, summarise what it established."""


def _call(client: anthropic.Anthropic, system: str, user: str, label: str,
          max_tokens: int = 400, usage_log: list | None = None):
    resp = client.messages.create(
        model=MODEL, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}],
    )
    if usage_log is not None:
        usage_log.append({"call": label, "in": resp.usage.input_tokens,
                          "out": resp.usage.output_tokens})
    log.info("threading/%s: %d in / %d out tokens", label,
             resp.usage.input_tokens, resp.usage.output_tokens)
    return _parse_json_response(resp.content[0].text, resp.stop_reason, f"threading/{label}")


def thread_title(event_briefs: list[str], client: anthropic.Anthropic,
                 usage_log: list | None = None) -> tuple[str, str]:
    """(title, summary) for a story from short briefs of its events."""
    user = "Reports in this story:\n\n" + "\n".join(f"- {b}" for b in event_briefs)
    try:
        r = _call(client, TITLE_SYSTEM, user, "title", usage_log=usage_log)
        return r.get("title") or "Developing story", r.get("summary") or ""
    except Exception:
        log.warning("Thread title generation failed — using a placeholder")
        return "Developing story", ""


def chapter_summary(event_brief: str, prior_summary: str | None,
                    client: anthropic.Anthropic, usage_log: list | None = None) -> str:
    """One-sentence 'what's new' for an event joining a thread."""
    prior = f"Story so far: {prior_summary}\n\n" if prior_summary else ""
    user = f"{prior}New report:\n\n{event_brief}"
    try:
        r = _call(client, CHAPTER_SYSTEM, user, "chapter", usage_log=usage_log)
        return r.get("chapter_summary") or ""
    except Exception:
        log.warning("Chapter summary failed — leaving blank")
        return ""


def event_brief(data: dict, max_chars: int = 1200) -> str:
    """Compact title+summary+lede text for the summariser prompts."""
    ev = data.get("event", {})
    parts = [ev.get("title", ""), ev.get("summary", "")]
    report = data.get("report") or {}
    paras = report.get("paragraphs", [])
    if paras:
        parts.append(paras[0].get("text", ""))
    return " ".join(p for p in parts if p)[:max_chars]
