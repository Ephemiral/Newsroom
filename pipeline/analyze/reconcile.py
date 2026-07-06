"""
M3 — Analyze: Step 2 — Cross-article consensus/divergence reasoning (Sonnet)
Takes all per-article raw claims, groups duplicates, classifies each as
agreed / corroborated / contested / single_source, and builds the per-event claims list.
"""

import json
import sys
import anthropic

RECONCILE_SYSTEM = """You are an analyst building a multi-source claim inventory for a news event.
You have been given raw claims extracted from multiple news articles across the political spectrum.

Your task:
1. Group semantically equivalent or overlapping claims (same underlying fact, possibly worded differently).
2. For each unique claim, produce a single neutral statement.
3. Classify each claim using EXACTLY these rules:
   - "agreed": supported by sources from at least two DIFFERENT bias tiers that span the political spectrum
     (e.g., left + center, center + center-right, or left + center-right). Same-side outlets (e.g.,
     left + center-left only, or center-right + right only) do NOT qualify. Ideological breadth is required.
   - "corroborated": supported by multiple sources, but all from the same side of the spectrum
     (e.g., two left-leaning outlets, or two center outlets only). The fact is repeated but not
     cross-spectrum confirmed.
   - "contested": sources explicitly contradict each other on this point, OR the same fact is
     framed in genuinely incompatible ways across bias tiers.
   - "single_source": only one source in the cluster raises this claim.
4. Capture the best framing variants — how different outlets characterize the same fact.
5. Write a reader-facing rationale (1-2 sentences) explaining the classification.
6. Assign each claim to a thematic group (claim_group): a short snake_case label such as
   "territorial_control", "ceasefire_details", "humanitarian_situation", "military_operations",
   "displacement_policy", "international_response". Use 4-8 groups total per event. Claims that
   don't fit any group may be left with claim_group: null.

Critical rules:
- Every claim must cite source_article_ids from the input — never invent support.
- "agreed" requires sources from DIFFERENT sides of the spectrum, not just different outlets.
- A source ID must NOT appear in both supported_by_articles and contested_by_articles for the same claim.
  If a source presents both perspectives, place it in supported_by_articles only.
- If two sources say contradictory things about the same fact, mark it "contested" even if more sources agree.
- ACTOR DISPUTES — merging into contested: When two actors (governments, officials,
  organisations) make directly contradictory claims about the same fact — e.g., Iran denies
  responsibility while the US asserts it; one party claims a deal was reached while the
  other denies it; two sides dispute a figure — you MUST produce ONE contested claim, not
  two separate corroborated claims for each actor's position. Creating separate corroborated
  claims for each side buries the dispute.

  Mark every such claim with "dispute_type": "actor". (All other claims: omit the field
  or use null.) The dispute is between the ACTORS, not between the outlets — it is normal
  for every responsible outlet to report both sides in the same article. Therefore:

  How to assign supported_by / contested_by in actor disputes:
    - supported_by_articles: EVERY outlet that reported the dispute (one side or both) —
      these outlets corroborate that the contradictory accounts exist.
    - contested_by_articles: ONLY outlets whose own reporting asserts one account as fact
      against the other (rare). Usually this list is EMPTY for actor disputes — that is
      correct and expected; the claim stays "contested" because dispute_type is "actor".
    - Use framing_variants to record which account(s) each outlet carried and how it
      presented them (e.g. "Led with the US account; carried Iran's denial in paragraph 8").

  The contested claim's text must use parallel language for both sides
  (per B-06: "Side A characterizes X as Y; Side B characterizes X as Z.").
  Do not use a credibility label for one side that the other does not also receive.

  Example — WRONG (buries dispute):
    [corroborated] Iran's IRGC denied responsibility, claiming damage was caused by a
                   malfunctioning US Patriot missile.
    [corroborated] US Central Command rejected Iran's claim and called it a deliberate strike.

  Example — CORRECT (surfaces dispute):
    [contested]    Iran's IRGC attributed the Kuwait airport damage to a malfunctioning
                   US Patriot missile interceptor; US Central Command and Kuwait's defence
                   ministry attributed the strike directly to an Iranian drone attack.
- STATE-ALIGNED OUTLETS: some sources carry a "state_alignment" value (e.g. "Russian
  state-controlled", "Saudi state-aligned"). These outlets are included precisely because
  they carry a government's own account — but they are perspective, NOT corroboration:
  - They never count toward cross-spectrum agreement. A claim supported only by one
    independent outlet plus state-aligned outlets is "single_source" or "corroborated",
    never "agreed".
  - Whenever a claim text, rationale, or framing variant conveys such an outlet's account,
    name the alignment inline in that text: "Russian state-controlled RT reported that…",
    "Saudi state-aligned Asharq Al-Awsat characterized…". Never cite them bare.
  - For actor disputes they are often the best record of one actor's position — use them,
    with the inline alignment label.
- Keep claims atomic and concrete.
- For any claim describing a directive, decision, or policy: if the source provides the actor's
  stated justification or reasoning, extract it as a SEPARATE linked claim. Do not merge the
  decision and its stated rationale into one claim.
- When writing a contested claim that describes a framing dispute between two sides, use
  grammatically parallel language for both sides. Neither side should receive a credibility label
  (e.g., "observers", "experts", "officials") that the other side does not also receive.
  Prefer: "Side A characterizes X as Y; Side B characterizes X as Z."

Output: A JSON object with this structure:
{
  "event_title": "Short neutral title for the event",
  "event_summary": "1-2 sentence neutral summary of what happened",
  "event_date": "YYYY-MM-DD",
  "claims": [
    {
      "claim_id": "clm_001",
      "text": "Neutral claim statement",
      "classification": "agreed|corroborated|contested|single_source",
      "dispute_type": "actor (only for actor disputes) or null",
      "claim_group": "snake_case_group_name or null",
      "supported_by_articles": ["art_001", "art_004"],
      "contested_by_articles": [],
      "rationale": "Reader-facing explanation of this classification.",
      "framing_variants": [
        {"article_id": "art_001", "characterization": "How this outlet frames it"}
      ]
    }
  ],
  "background": [
    {"point": "Context a reader needs to understand this event", "article_ids": ["art_002"]}
  ]
}"""


def enforce_classification_rules(result: dict, articles: list[dict]) -> list[str]:
    """
    B-01 + B-02 enforcement pass — mutates result in place before validation.
    Returns a list of correction strings that were applied.

    B-01: 'agreed' claims without genuine cross-spectrum support are reclassified
          to 'corroborated'. Cross-spectrum requires sources from ≥2 distinct bias
          tiers that are NOT all on the same side of center.
    B-02: sources that appear in both supported_by_articles and contested_by_articles
          are removed from contested_by_articles (belong in supported_by only).
    """
    corrections = []
    article_bias = {a["article_id"]: a.get("bias_rating", "") for a in articles}
    # B-17: state-aligned outlets add perspective, not corroboration — they never
    # anchor a side of the spectrum for 'agreed' classification.
    article_aligned = {a["article_id"]: bool(a.get("state_alignment")) for a in articles}

    LEFT_SIDE = {"left", "center-left"}
    RIGHT_SIDE = {"center-right", "right"}
    CENTER = {"center"}

    for claim in result.get("claims", []):
        cid = claim.get("claim_id", "?")
        supported = list(claim.get("supported_by_articles", []))
        contested = list(claim.get("contested_by_articles", []))

        # B-02: remove sources from contested_by if they also appear in supported_by
        overlap = set(supported) & set(contested)
        if overlap:
            claim["contested_by_articles"] = [a for a in contested if a not in overlap]
            corrections.append(
                f"B-02 {cid}: moved {overlap} from contested_by to supported_by only."
            )
            contested = claim["contested_by_articles"]

        # B-09: reclassify 'contested' → 'corroborated'/'single_source' when contested_by is empty.
        # A contested classification with no contesting outlets means the model inferred dispute
        # from claim content (e.g., two parties quoted within one claim) rather than from
        # cross-outlet disagreement. That is not an outlet-level contest.
        #
        # B-16 carve-out: actor disputes (dispute_type == "actor") legitimately have an empty
        # contested_by — the contradiction is between the actors, and every outlet that reported
        # the dispute sits in supported_by. They stay "contested" as long as at least two
        # outlets corroborate that the dispute exists; a one-outlet actor dispute is demoted
        # to single_source like any other one-outlet claim.
        if claim.get("classification") == "contested" and not contested:
            if claim.get("dispute_type") == "actor":
                if len(supported) < 2:
                    claim["classification"] = "single_source"
                    corrections.append(
                        f"B-09/B-16 {cid}: actor dispute reported by only "
                        f"{len(supported)} outlet(s) — reclassified to 'single_source'."
                    )
                # else: legitimate actor dispute — keep 'contested'
            else:
                tiers = {article_bias.get(a) for a in supported if article_bias.get(a)}
                new_cls = "corroborated" if len(tiers) >= 2 else "single_source"
                claim["classification"] = new_cls
                corrections.append(
                    f"B-09 {cid}: reclassified 'contested' → '{new_cls}' "
                    f"(contested_by is empty; supported_by tiers: {tiers})."
                )

        # B-01: reclassify 'agreed' → 'corroborated' if cross-spectrum diversity is absent
        # (state-aligned outlets excluded from the tier count — B-17)
        if claim.get("classification") == "agreed":
            tiers = {article_bias.get(a) for a in supported
                     if article_bias.get(a) and not article_aligned.get(a)}
            has_left_side = bool(tiers & LEFT_SIDE)
            has_right_side = bool(tiers & RIGHT_SIDE)
            has_center = bool(tiers & CENTER)
            cross_spectrum = (has_left_side and (has_right_side or has_center)) or \
                             (has_right_side and (has_left_side or has_center))
            if not cross_spectrum:
                claim["classification"] = "corroborated"
                corrections.append(
                    f"B-01 {cid}: reclassified 'agreed' → 'corroborated' "
                    f"(supported_by tiers: {tiers})."
                )

    return corrections


def validate_reconciled_output(result: dict, articles: list[dict]) -> list[str]:
    """
    Post-reconciliation validation checks. Returns a list of warning strings.
    Warnings do not halt the pipeline but are printed so the analyst can review.
    Called AFTER enforce_classification_rules so it reflects corrected data.
    B-03: rationale should not reference outlet names absent from the claim's source lists.
    """
    warnings = []
    article_bias = {a["article_id"]: a.get("bias_rating", "") for a in articles}
    outlet_names = {a["article_id"]: a.get("outlet", "") for a in articles}

    for claim in result.get("claims", []):
        cid = claim.get("claim_id", "?")
        supported = set(claim.get("supported_by_articles", []))
        contested = set(claim.get("contested_by_articles", []))

        # B-03: rationale outlet name check (heuristic)
        rationale = claim.get("rationale", "")
        supported_outlets = {outlet_names.get(a, "") for a in supported}
        contested_outlets = {outlet_names.get(a, "") for a in contested}
        all_cited_outlets = supported_outlets | contested_outlets
        for art_id, outlet in outlet_names.items():
            if outlet and outlet in rationale and outlet not in all_cited_outlets:
                warnings.append(
                    f"{cid}: rationale mentions '{outlet}' but that outlet is not in "
                    f"supported_by or contested_by. Verify the rationale text."
                )

    return warnings


def reconcile_claims(all_raw_claims: list[dict], articles: list[dict],
                     client: anthropic.Anthropic) -> dict:
    """Run cross-article reconciliation using Sonnet."""

    # Build a concise representation of all raw claims for the prompt
    claims_by_article = {}
    for c in all_raw_claims:
        aid = c["source_article_id"]
        if aid not in claims_by_article:
            claims_by_article[aid] = []
        claims_by_article[aid].append({
            "raw_claim": c["raw_claim"],
            "characterization": c["characterization"],
            "quote": c.get("quote")
        })

    # Build article metadata summary
    source_meta = []
    for art in articles:
        source_meta.append({
            "article_id": art["article_id"],
            "outlet": art["outlet"],
            "bias_rating": art["bias_rating"],
            "bias_rating_source": art["bias_rating_source"],
            "state_alignment": art.get("state_alignment"),
            "published_at": art.get("published_at", ""),
            "has_full_text": bool(art.get("body_text") and not art["body_text"].startswith("[Full"))
        })

    prompt = f"""Source articles in this event cluster:
{json.dumps(source_meta, indent=2)}

Raw claims extracted per article:
{json.dumps(claims_by_article, indent=2)}

Reconcile, deduplicate, and classify these claims. Return the JSON object only."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=RECONCILE_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    from pipeline.analyze.extract import _parse_json_response
    result = _parse_json_response(text, response.stop_reason, "reconcile")

    # B-01 + B-02: enforce classification rules (mutates result in place)
    corrections = enforce_classification_rules(result, articles)
    if corrections:
        print(f"\n✔  Classification corrections applied ({len(corrections)}):", file=sys.stderr)
        for c in corrections:
            print(f"   • {c}", file=sys.stderr)

    # B-03: post-reconciliation validation warnings
    warnings = validate_reconciled_output(result, articles)
    if warnings:
        print(f"\n⚠  Reconciliation validation warnings ({len(warnings)}):", file=sys.stderr)
        for w in warnings:
            print(f"   • {w}", file=sys.stderr)

    return result
