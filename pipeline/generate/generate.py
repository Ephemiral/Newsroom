"""
M7 — Generate: Produce the reader-facing report from structured claims + sources.

Calls Sonnet with the per-event claim inventory (not raw article text) and
returns a structured `report` object matching the schema in STAGE_5_GENERATE.md.

Each paragraph is tagged with:
  - paragraph_id: "p1", "p2", ...
  - text: neutral synthesized prose
  - supports: { claim_ids: [...], source_ids: [...] }
  - kind: "agreed" | "contested" | "framing" | "one_sided" | "background"
"""

import json
import re
from datetime import datetime, timezone


GENERATE_SYSTEM = """You are writing the reader-facing report for a multi-source news analysis tool.

Your job is to synthesize a transparent, multi-perspectival narrative from a structured claim inventory.
The claims have already been extracted and classified from articles across the political spectrum.
You must write FROM the claims — do not introduce facts, figures, or characterizations that do not
appear in the provided claim list.

## Output format

Return a JSON object with this exact structure:
{
  "paragraphs": [
    {
      "paragraph_id": "p1",
      "text": "Synthesized prose for this paragraph.",
      "supports": {
        "claim_ids": ["clm_001", "clm_002"],
        "source_ids": ["src_001", "src_004"]
      },
      "kind": "agreed"
    }
  ]
}

## Paragraph kinds

The `kind` field is NOT a subjective editorial judgment — it must be derived directly from
the classification labels and `contested_by` fields of the claims the paragraph synthesizes.
Use the rules below exactly.

- "agreed": The paragraph synthesizes claims whose `supported_by` sources span at least two
  bias tiers on opposite sides of center (e.g. left + center-right, or center-left + right).
  State agreed facts plainly. Do NOT use this kind for claims backed only by sources from
  one side of the spectrum, even if multiple outlets are involved.

- "contested": At least one claim cited in this paragraph has a non-empty `contested_by` list —
  meaning sources actively assert opposing positions on the same fact. Present both sides by
  name. Use grammatically parallel language — do not give one side a credibility label
  (e.g. "observers", "experts") that the other does not also receive.
  Do NOT use this kind merely because a topic is contentious or because only one side covered it.

- "framing": The claims are classified AGREED or CORROBORATED at the factual level (no active
  dispute), but `framing_variants` differ meaningfully across ideological lines — the same
  underlying fact is characterized or emphasized differently by different outlet groups.
  Make clear this is a framing difference, not a factual dispute.

- "one_sided": All claims in this paragraph are classified SINGLE_SOURCE or CORROBORATED
  within a single ideological lane (e.g. only left-leaning outlets, or only right-leaning
  Israeli outlets). The other side of the spectrum did not report this. Surface which part
  of the spectrum reported it. Do not treat one-sided coverage as agreed or contested —
  the asymmetry is itself the signal.

- "background": Contextual information (history, prior events, legal context) that helps
  the reader understand the current event. Not tied to a specific breaking claim.

## Ordering

Write paragraphs in this sequence by kind:
1. agreed — the core facts confirmed across the political spectrum
2. background — context the reader needs to understand what happened
3. framing and one_sided — where the spectrum diverges in emphasis or coverage
4. contested — active factual disputes between sources

Within each group, order by narrative importance. Do not mix kinds out of sequence
unless a background fact is needed to make a specific contested or one_sided claim
intelligible — in that case, place it immediately before that paragraph and mark
it background.

IMPORTANT — missing kinds: Not every event will have claims in every category.
- If there are no CONTESTED claims (no claim has contested_by populated), do not
  write any contested paragraphs. Omit that group entirely.
- If all claims are AGREED, write only agreed and background paragraphs.
- If there are no SINGLE_SOURCE or lane-specific CORROBORATED claims, omit
  one_sided paragraphs.
- Never invent a paragraph kind to fill a structural slot. Only write a paragraph
  if the underlying claims support it. A shorter, accurate report is better than
  a longer report with unsupported kind assignments.

## Rules

- Every paragraph MUST cite at least one claim_id and at least one source_id in `supports`.
- Only cite claim_ids and source_ids that appear in the input. Do not invent IDs.
- `claim_ids` must contain only identifiers from the CLAIMS section, which are formatted `clm_XXX` (e.g. "clm_001", "clm_014").
- `source_ids` must contain only identifiers from the SOURCES section, which are formatted `src_XXX` (e.g. "src_001", "src_007").
- Never place a `clm_XXX` value inside `source_ids`, and never place a `src_XXX` value inside `claim_ids`.
- Do not merge more than ~4 claims into one paragraph — keep paragraphs focused.
- For contested claims: present both sides. Identify who holds each view (e.g., "left-leaning
  outlets", "Israeli officials and center-right sources"). Do not resolve the dispute.
- Tone: neutral, precise, transparent. Assume an intelligent reader who wants to understand
  what different sources say, not be told what to think.
- Write in the past tense (these are recent events being reported).
- Aim for 12–16 paragraphs total.
- Do not include any text outside the JSON object.

## Source balance

The source set for this event may have more outlets from one side of the spectrum than another.
Do NOT let volume dominate framing. A fact supported by three left-leaning outlets and one
center outlet should not read as more authoritative than a fact supported by one outlet from
each side. When synthesizing, weight by ideological breadth of support, not raw count.
If a claim is only backed by sources from one side of the spectrum (even if multiple), note
that explicitly rather than presenting it as broad consensus.

## Quotes

Where the claim's framing_variants contain direct verbatim quotations from named officials,
leaders, or primary sources (text in quotation marks with an identifiable speaker), include
at least one such quote per section where available. Format: "[Quote]" — [Name], [Title/Role].
Prefer first-person quotes from the actor themselves over paraphrased second-hand reporting.

## Casualty figures

When citing death toll figures for Palestinian casualties in Gaza, attribute them to their
originating source: these figures come from the Gaza Health Ministry, which operates under
Hamas administration. Note this attribution explicitly so readers can assess the sourcing.
Do not omit the figures — they are the only available count — but do not present them as
independently verified unless the claim's supporting sources include a non-Hamas authority.

## Regional conflict context

If the claims mention Israeli military presence in Lebanon or Syria, always include a
background paragraph explaining that these operations were directed against Hezbollah —
an Iranian-backed militant group designated as a terrorist organization by the US and EU —
operating along Israel's northern borders. This is a distinct conflict from Gaza, not an
extension of it. Draw only on claims present in the input; do not add facts not in the claims."""


def _claim_is_contested_evidence(c: dict) -> bool:
    """
    True when a claim constitutes evidence of genuine contention (B-11/B-16):
    either outlets directly disagree (contested_by populated), or the claim is a
    validated actor dispute (classification 'contested' with dispute_type 'actor',
    which the B-09/B-16 reconcile guard only lets through with >=2 outlets).
    """
    return bool(c.get("contested_by")) or (
        c.get("classification") == "contested" and c.get("dispute_type") == "actor"
    )


def _build_claims_block(claims: list[dict]) -> str:
    """Format claims into a readable block for the prompt, grouped by classification."""
    groups = {"agreed": [], "corroborated": [], "contested": [], "single_source": []}
    for c in claims:
        cls = c.get("classification", "single_source")
        groups.setdefault(cls, []).append(c)

    # Emit a prominent header when nothing in the event evidences genuine contention
    # (neither outlet-level disagreement nor a validated actor dispute — B-16)
    has_any_contested_evidence = any(_claim_is_contested_evidence(c) for c in claims)
    lines = []
    if not has_any_contested_evidence:
        lines.append(
            "⚠ CONTESTED_BY STATUS: No claim in this event has a non-empty contested_by list "
            "or a validated actor dispute. "
            "This means NO outlets reported genuinely opposing facts and no actors gave "
            "contradictory accounts. "
            "You MUST NOT write any paragraphs with kind=contested. "
            "Use framing or one_sided instead where perspectives differ.\n"
        )

    for cls, label in [
        ("agreed", "AGREED (cross-spectrum consensus)"),
        ("corroborated", "CORROBORATED (same-side confirmation only)"),
        ("contested", "CONTESTED (genuine disagreement between sources)"),
        ("single_source", "SINGLE SOURCE (one outlet only)"),
    ]:
        if not groups.get(cls):
            continue
        lines.append(f"\n### {label}\n")
        for c in groups[cls]:
            lines.append(f"[{c['claim_id']}] ({c.get('claim_group', '')}) {c['text']}")
            lines.append(f"  supported_by: {', '.join(c.get('supported_by', []))}")
            if c.get("contested_by"):
                lines.append(f"  contested_by: {', '.join(c['contested_by'])}")
            if c.get("dispute_type") == "actor":
                lines.append(
                    "  dispute_type: actor — the contradiction is between the actors named in "
                    "the claim; every outlet above corroborates that the dispute exists"
                )
            if c.get("rationale"):
                lines.append(f"  rationale: {c['rationale']}")
            lines.append("")

    return "\n".join(lines)


def _build_sources_block(sources: list[dict]) -> str:
    """Format sources into a readable reference block."""
    lines = ["\n### SOURCES\n"]
    has_aligned = any(s.get("state_alignment") for s in sources)
    if has_aligned:
        lines.append(
            "⚠ STATE-ALIGNED SOURCES PRESENT: sources marked [STATE-ALIGNED: …] below are "
            "government-controlled or government-aligned outlets. Whenever the report text "
            "conveys their account, name the alignment inline — e.g. \"Russian state-controlled "
            "RT reported that…\", \"Saudi state-aligned Asharq Al-Awsat characterized…\". "
            "Never cite them without the label, and never present their account as "
            "independent corroboration.\n"
        )
    for s in sources:
        ownership = s.get("ownership") or "Unknown"
        aligned = f" [STATE-ALIGNED: {s['state_alignment']}]" if s.get("state_alignment") else ""
        lines.append(
            f"[{s['source_id']}] {s['outlet']}{aligned} — bias: {s.get('bias_rating', '?')} "
            f"({s.get('bias_rating_source', '')}) — {ownership}"
        )
    return "\n".join(lines)


def _parse_response(text: str, stop_reason: str = "end_turn") -> dict:
    """Extract JSON from model response, handling markdown fences and minor malformation."""
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    # Repair truncated output
    if stop_reason == "max_tokens":
        last_brace = text.rfind("}")
        if last_brace != -1:
            text = text[:last_brace + 1]
            text += "]" * (text.count("[") - text.count("]"))
            text += "}" * (text.count("{") - text.count("}"))

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        from json_repair import repair_json
        return json.loads(repair_json(text))
    except (ImportError, Exception):
        pass

    raise ValueError(f"Could not parse generate response. First 600 chars:\n{text[:600]}")


def generate_report(event_data: dict, client) -> dict:
    """
    Generate the report field for a per-event JSON.

    Args:
        event_data: Full parsed per-event JSON (schema v0.2)
        client: anthropic.Anthropic client

    Returns:
        report dict matching the schema in STAGE_5_GENERATE.md
    """
    event = event_data["event"]
    claims = event_data["claims"]
    sources = event_data["sources"]

    claims_block = _build_claims_block(claims)
    sources_block = _build_sources_block(sources)

    user_prompt = f"""## Event

Title: {event['title']}
Summary: {event['summary']}
Date: {event['date']}

{sources_block}

{claims_block}

Write the reader-facing report as a JSON object following the format and rules in your instructions.
"""

    print("  Calling Sonnet for report generation...", flush=True)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=GENERATE_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text
    parsed = _parse_response(raw, response.stop_reason)

    # Model occasionally returns a bare JSON array of paragraphs instead of
    # the {"paragraphs": [...]} envelope.
    if isinstance(parsed, list):
        parsed = {"paragraphs": parsed}

    # Wrap in the full report envelope
    report = {
        "schema_version": "0.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paragraphs": parsed.get("paragraphs", []),
    }

    # B-11: enforce paragraph kind consistency before returning
    _enforce_paragraph_kinds(report, event_data)

    return report


def validate_report(report: dict, event_data: dict) -> list[str]:
    """
    Validate report paragraph IDs against the claim and source inventories.
    Auto-corrects transposed IDs (clm_XXX in source_ids, src_XXX in claim_ids).
    Checks that kind assignments are consistent with the underlying claim data (B-08).

    Returns a list of warning strings. Only [ERROR] lines cause the run to abort.
    """
    valid_claim_ids = {c["claim_id"] for c in event_data["claims"]}
    valid_source_ids = {s["source_id"] for s in event_data["sources"]}
    # Build a lookup for claim classification and contested_by
    claim_meta = {
        c["claim_id"]: {
            "classification": c.get("classification", "single_source"),
            "has_contested_by": _claim_is_contested_evidence(c),
        }
        for c in event_data["claims"]
    }
    warnings = []

    for para in report.get("paragraphs", []):
        pid = para.get("paragraph_id", "?")
        supports = para.get("supports", {})
        cited_claims = list(supports.get("claim_ids", []))
        cited_sources = list(supports.get("source_ids", []))

        # Auto-correct: clm_XXX in source_ids → move to claim_ids
        misplaced_claims = [sid for sid in cited_sources if sid.startswith("clm_")]
        if misplaced_claims:
            for bad in misplaced_claims:
                cited_sources.remove(bad)
                if bad not in cited_claims:
                    cited_claims.append(bad)
            supports["claim_ids"] = cited_claims
            supports["source_ids"] = cited_sources
            warnings.append(
                f"  [WARN] {pid}: auto-corrected {misplaced_claims} from source_ids → claim_ids"
            )

        # Auto-correct: src_XXX in claim_ids → move to source_ids
        misplaced_sources = [cid for cid in cited_claims if cid.startswith("src_")]
        if misplaced_sources:
            for bad in misplaced_sources:
                cited_claims.remove(bad)
                if bad not in cited_sources:
                    cited_sources.append(bad)
            supports["claim_ids"] = cited_claims
            supports["source_ids"] = cited_sources
            warnings.append(
                f"  [WARN] {pid}: auto-corrected {misplaced_sources} from claim_ids → source_ids"
            )

        if not cited_claims and not cited_sources:
            warnings.append(f"  [WARN] {pid}: supports is empty — flag for human review")

        # B-08: kind consistency check
        kind = para.get("kind", "")
        if kind == "contested":
            has_any_contested = any(
                claim_meta.get(cid, {}).get("has_contested_by", False)
                for cid in cited_claims
            )
            if not has_any_contested:
                warnings.append(
                    f"  [WARN] {pid}: kind=contested but no cited claim has contested_by "
                    f"populated — consider one_sided or framing"
                )

        for cid in cited_claims:
            if cid not in valid_claim_ids:
                warnings.append(f"  [ERROR] {pid}: unknown claim_id '{cid}'")

        for sid in cited_sources:
            if sid not in valid_source_ids:
                warnings.append(f"  [ERROR] {pid}: unknown source_id '{sid}'")

    return warnings


def _enforce_paragraph_kinds(report: dict, event_data: dict) -> list[str]:
    """
    B-11 enforcement: reclassify `contested` paragraphs that have no outlet-level
    disagreement evidence. Mirrors B-09 in reconcile.py one layer up.

    Two cases both result in reclassification to `framing`:
    1. claim_ids is empty — model ignored the citation rule, so there is no evidence
       to evaluate. Treat absence of evidence as no contested support.
    2. claim_ids is populated but none of the cited claims have contested_by non-empty —
       the model labelled a paragraph contested because the topic sounds disputed, not
       because outlets actually reported opposing facts.

    Mutates report in place. Returns list of corrections applied.
    """
    import sys
    claim_has_contested = {
        c["claim_id"]: _claim_is_contested_evidence(c)
        for c in event_data["claims"]
    }
    corrections = []

    for para in report.get("paragraphs", []):
        if para.get("kind") != "contested":
            continue
        cited = para.get("supports", {}).get("claim_ids", [])
        if not cited:
            para["kind"] = "framing"
            corrections.append(
                f"B-11 {para['paragraph_id']}: contested → framing "
                f"(claim_ids empty; no outlet-level dispute evidence)"
            )
        elif not any(claim_has_contested.get(cid, False) for cid in cited):
            para["kind"] = "framing"
            corrections.append(
                f"B-11 {para['paragraph_id']}: contested → framing "
                f"(cited claims {cited} have no contested_by — topic dispute, not outlet dispute)"
            )

    if corrections:
        print(f"\n✔  Kind enforcement corrections applied ({len(corrections)}):", file=sys.stderr)
        for c in corrections:
            print(f"   • {c}", file=sys.stderr)

    return corrections
