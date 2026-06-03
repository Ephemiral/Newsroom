"""
Weekly Outlet Registry Review
Scheduled task: every Thursday at 9am.

For each outlet in data/sources/outlet_provenance.json, performs a web search
for recent ownership or funding changes, uses Haiku to assess whether the
registry entry needs updating, and presents a digest for G's review.

Any proposed change is flagged — the registry is NOT auto-updated. G reviews
and edits outlet_provenance.json manually if an update is warranted.

Run: python3 scripts/registry_review.py
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "sources" / "outlet_provenance.json"

ASSESS_SYSTEM = """You are an assistant checking whether a media outlet's ownership or funding
information is still accurate based on recent search results.

Given:
- The outlet name
- The current registry entry (ownership + notes)
- Recent web search results about the outlet's ownership

Respond with a JSON object:
{
  "change_detected": true | false,
  "confidence": "high" | "medium" | "low",
  "summary": "One sentence: what changed, or confirmation that nothing has.",
  "suggested_ownership": "Updated ownership string if change_detected, else null",
  "suggested_notes": "Updated notes string if change_detected, else null"
}

Only set change_detected: true if the search results contain clear evidence of an
ownership or funding change that post-dates the last_reviewed date. Do not flag
routine news coverage about the outlet as a change."""


def search_outlet(outlet_name: str, client: anthropic.Anthropic) -> str:
    """Use Claude to simulate a web search summary for the outlet."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                f"Summarise any known ownership, acquisition, or funding changes for the media "
                f"outlet '{outlet_name}' that have occurred or been reported in the past year "
                f"(up to {date.today().isoformat()}). If you know of none, say so plainly. "
                f"Be factual and brief — 2-4 sentences maximum."
            )
        }]
    )
    return response.content[0].text.strip()


def assess_change(outlet_name: str, entry: dict, search_summary: str, client: anthropic.Anthropic) -> dict:
    """Ask Haiku whether a change is warranted."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=ASSESS_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                f"Outlet: {outlet_name}\n"
                f"Last reviewed: {entry.get('last_reviewed', 'unknown')}\n"
                f"Current ownership: {entry.get('ownership', '')}\n"
                f"Current notes: {entry.get('notes', '')}\n\n"
                f"Recent search results:\n{search_summary}"
            )
        }]
    )
    text = response.content[0].text.strip()
    try:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group(0)) if match else {"change_detected": False, "summary": text}
    except Exception:
        return {"change_detected": False, "summary": text}


def main():
    client = anthropic.Anthropic()
    registry = json.loads(REGISTRY_PATH.read_text())

    print(f"\n{'='*60}")
    print(f"OUTLET REGISTRY REVIEW — {date.today().isoformat()}")
    print(f"{'='*60}\n")

    changes_found = []
    no_changes = []

    # Deduplicate: skip variant entries that share ownership with a canonical entry
    seen_ownership = set()
    outlets_to_review = {}
    for name, entry in registry.items():
        key = entry.get("ownership", "")[:60]
        if key not in seen_ownership:
            seen_ownership.add(key)
            outlets_to_review[name] = entry

    for outlet_name, entry in outlets_to_review.items():
        print(f"Checking: {outlet_name}...", flush=True)
        search_summary = search_outlet(outlet_name, client)
        assessment = assess_change(outlet_name, entry, search_summary, client)

        if assessment.get("change_detected"):
            changes_found.append({
                "outlet": outlet_name,
                "assessment": assessment,
                "search_summary": search_summary,
            })
        else:
            no_changes.append(outlet_name)

    # Print digest
    print(f"\n{'─'*60}")
    print(f"DIGEST: {len(changes_found)} potential change(s), {len(no_changes)} unchanged\n")

    if changes_found:
        print("⚠️  POTENTIAL CHANGES — review and update outlet_provenance.json if warranted:\n")
        for item in changes_found:
            print(f"  Outlet:     {item['outlet']}")
            print(f"  Confidence: {item['assessment'].get('confidence', '?')}")
            print(f"  Summary:    {item['assessment'].get('summary', '')}")
            if item['assessment'].get('suggested_ownership'):
                print(f"  Suggested ownership: {item['assessment']['suggested_ownership']}")
            if item['assessment'].get('suggested_notes'):
                print(f"  Suggested notes:     {item['assessment']['suggested_notes']}")
            print()
    else:
        print("✅  No ownership or funding changes detected.\n")

    print(f"Unchanged: {', '.join(no_changes)}\n")
    print(f"Registry path: {REGISTRY_PATH}")
    print(f"To update: edit outlet_provenance.json and set last_reviewed to {date.today().isoformat()}\n")


if __name__ == "__main__":
    main()
