"""
Self-contradiction detection (STAGE_9) — the high-stakes call.

Given ONE outlet's own claim timeline across a thread, identify only where its
later reporting contradicts / corrects / retracts its OWN earlier account of the
SAME fixed fact. The dominant failure mode to avoid: flagging a developing story
(the world changed) as an outlet erring. The prompt forbids that explicitly and
the model is told to return NOTHING when unsure — a missed flag is harmless, a
false one is defamation-adjacent.

Uses Sonnet (quality over cost here, per G's decision). The model returns only
claim_id references + type + neutral note; the caller reconstructs the receipts
(text, source_id, url) from the real event data — never from the model's echo.
"""

from __future__ import annotations

import json
import logging

import anthropic

from pipeline.analyze.extract import _parse_json_response

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

DETECT_SYSTEM = """You audit a SINGLE news outlet's own reporting across a developing story for cases where it contradicted, corrected, or retracted ITSELF.

You are given, in date order, the claims this one outlet reported at each stage of the story. Find only cases where the outlet's LATER reporting reverses its OWN EARLIER reporting about the SAME FIXED FACT.

CRITICAL — what is NOT a flag (this is the most important rule):
- A developing story changing is NOT a contradiction. If the situation itself moved on (a ceasefire held, then later collapsed; a toll rose as more became known and was reported AS an update), that is accurate reporting, not self-contradiction. Do NOT flag it.
- Reporting a new party's statement, a new development, or new information is NOT a contradiction.
- Two claims about DIFFERENT facts are NOT a contradiction.
- If you are not sure it is a genuine same-fact self-reversal, DO NOT flag it. A missed case is fine; a wrong accusation is not.

Flag ONLY these, and only when unmistakable:
- "contradiction": the outlet asserted A about a fixed fact, then later asserted not-A about that same fixed fact (not because the situation changed).
- "correction": the outlet explicitly revised its own earlier figure/claim.
- "retraction": the outlet explicitly withdrew its own earlier claim.

Return valid JSON only: a list (possibly empty) of:
{"type": "contradiction|correction|retraction",
 "earlier_claim_id": "clm_...", "later_claim_id": "clm_...",
 "subject": "neutral one-line description of the fact at issue",
 "note": "one neutral sentence stating what changed, in parallel language, with NO speculation about why and NO characterisation (never 'flip-flop', 'backtracked', 'under pressure')"}

Output [] if there is no unmistakable self-reversal. Prefer [] whenever in doubt."""


def detect_self_reversals(outlet: str, timeline: list[dict], client: anthropic.Anthropic,
                          usage_log: list | None = None) -> list[dict]:
    """timeline: [{date, cluster_id, claims:[{claim_id, stance, text}]}] for ONE outlet.
    Returns raw flag dicts (claim_id references only) — the caller validates and
    reconstructs receipts from real data."""
    # Need the same outlet in ≥2 chapters to have anything to compare.
    if sum(1 for c in timeline if c["claims"]) < 2:
        return []

    payload = {"outlet": outlet, "timeline": timeline}
    resp = client.messages.create(
        model=MODEL, max_tokens=1200, system=DETECT_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    if usage_log is not None:
        usage_log.append({"call": "detect", "model": MODEL,
                          "in": resp.usage.input_tokens, "out": resp.usage.output_tokens})
    log.info("accountability/detect [%s]: %d in / %d out tokens",
             outlet, resp.usage.input_tokens, resp.usage.output_tokens)
    try:
        result = _parse_json_response(resp.content[0].text, resp.stop_reason, "accountability/detect")
    except Exception:
        log.warning("Detection parse failed for %s — treating as no flags (safe default)", outlet)
        return []
    return result if isinstance(result, list) else []
