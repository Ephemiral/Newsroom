"""
M3 — Analyze: Step 1 — Per-article claim extraction (Haiku)
Reads a single article JSON and returns a list of raw claims with source attribution.
"""

import json
import sys
import anthropic

EXTRACT_SYSTEM = """You are an analyst extracting factual claims from a news article.
Your job: identify every discrete, verifiable factual claim in the article.

Rules:
- Each claim must be grounded in the article text — never invent or infer beyond what is stated.
- Rephrase each claim neutrally (remove loaded language, but preserve meaning).
- Include the outlet's framing as a separate "characterization" field — how does this outlet actually describe this claim?
- Claims should be atomic (one fact per claim, not compound sentences).
- Exclude opinions, predictions, or rhetorical questions.
- If the article has only key facts (no full body text), extract only what is explicitly stated.
- For any claim describing a directive, decision, or policy announcement: if the article provides
  the actor's stated justification or reasoning, extract that reasoning as a SEPARATE claim.
  Do not merge a decision with its stated rationale into a single claim.

CRITICAL: Output a valid JSON array only. No prose before or after. No trailing commas. Each element:
{"raw_claim": "...", "characterization": "...", "quote": "..." or null}"""


def _parse_json_response(text: str, stop_reason: str, label: str):
    """Parse JSON from model output, with truncation repair and fallback."""
    # Strip markdown fences
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    # Repair truncated output (stop_reason == "max_tokens")
    if stop_reason == "max_tokens":
        last_brace = text.rfind("}")
        if last_brace != -1:
            text = text[:last_brace + 1]
            open_brackets = text.count("[") - text.count("]")
            open_braces = text.count("{") - text.count("}")
            text += "]" * open_brackets + "}" * open_braces

    # First attempt: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second attempt: json_repair library (pip install json-repair)
    try:
        from json_repair import repair_json
        return json.loads(repair_json(text))
    except (ImportError, Exception):
        pass

    # Give up: print context and raise
    print(f"\n--- RAW RESPONSE [{label}] (first 600 chars) ---\n{text[:600]}\n---", file=sys.stderr)
    raise ValueError(f"Could not parse JSON response for {label}")


def extract_claims(article: dict, client: anthropic.Anthropic) -> list[dict]:
    """Extract claims from a single article using Haiku."""
    body = article.get("body_text", "")
    has_full_text = body and not body.startswith("[Full article")
    content_block = f"Full article text:\n\n{body}" if has_full_text else f"Article summary/key facts:\n\n{body}"

    prompt = f"""Article metadata:
- Outlet: {article['outlet']}
- Bias rating: {article['bias_rating']} (source: {article['bias_rating_source']})
- Published: {article.get('published_at', 'unknown')}
- Title: {article.get('title', '')}

{content_block}

Extract all discrete factual claims. Return a JSON array only — no other text."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    claims = _parse_json_response(text, response.stop_reason, article["article_id"])

    # Attach source metadata to each claim
    for claim in claims:
        claim["source_article_id"] = article["article_id"]
        claim["source_outlet"] = article["outlet"]
        claim["source_bias"] = article["bias_rating"]

    return claims
