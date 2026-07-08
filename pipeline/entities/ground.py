"""
Entity grounding — look a NEW entity up in citable reference sources (STAGE_7).

Primary: Wikidata (structured, typed, has the P18 image property) + the
Wikipedia REST summary (neutral prose, a citable URL). Free, keyless APIs.

Hard rule (mirrors the bias-rating rule): the model never asserts biographical
facts from training knowledge. Everything grounded here carries the URL it was
retrieved from and the retrieval date. If no citable source is found, fields
stay empty — an entity card can legitimately be thin.

Entity images reuse the Stage-15b license discipline via
pipeline.images.wikimedia.license_acceptable: CC0 / CC BY / CC BY-SA / public
domain only, attribution stored and mandatory to render. The Stage-15b
"identifiable person disqualifies" rule is an *event-image* rule and does not
apply here — the person IS the subject (portraits are the point).
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import requests

from pipeline.images.wikimedia import license_acceptable

log = logging.getLogger(__name__)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

_HEADERS = {
    "User-Agent": "CritiqalNewsroom/0.1 (news synthesis research; kafri.sg@gmail.com)"
}
_TAG_RE = re.compile(r"<[^>]+>")

# Wikidata property ids used for typed connections / roles.
_CONNECTION_PROPS = {
    "P22": "family_of",        # father
    "P25": "family_of",        # mother
    "P26": "family_of",        # spouse
    "P40": "family_of",        # child
    "P3373": "family_of",      # sibling
    "P102": "member_of",       # political party
    "P463": "member_of",       # member of
    "P108": "employed_by",     # employer
    "P169": "leads",           # chief executive officer (org side)
    "P488": "leads",           # chairperson (org side)
}
_ROLE_PROP = "P39"             # position held
_IMAGE_PROP = "P18"
_INSTANCE_PROP = "P31"

# Type sanity keywords: a Wikidata hit whose description matches the wrong
# family is rejected (e.g. resolving a person mention to a warship). Kept
# deliberately broad — the point is family-level sanity, not precision; person
# identity is separately confirmed by an LLM check (namesake guard).
_TYPE_HINTS = {
    "person": ("politician", "official", "minister", "president", "diplomat", "general",
               "leader", "journalist", "businessperson", "commander", "activist",
               "cleric", "scientist", "human", "figure", "chief", "head of", "chairman",
               "spokesperson", "technocrat", "economist", "lawyer", "academic", "engineer"),
    "organization": ("organization", "organisation", "agency", "company", "militant",
                     "armed", "military", "ministry", "union", "committee", "group",
                     "force", "media", "network", "government", "authority",
                     "administration", "council", "movement", "coalition", "body",
                     "institution", "parliament", "party",
                     # States acting as political actors are legitimately typed
                     # "organization" by the extractor; the QID is the country.
                     "country", "state", "nation", "republic", "kingdom"),
    "political_party": ("political party", "party", "movement", "coalition", "alliance"),
    "technology": ("missile", "aircraft", "system", "weapon", "drone", "vehicle",
                   "ship", "radar", "satellite", "platform", "rifle", "tank",
                   "helicopter", "submarine", "rocket", "bomb", "interceptor"),
    "location": ("city", "town", "port", "strait", "province", "region", "country",
                 "facility", "plant", "base", "airport", "border", "river", "island",
                 "capital", "district", "site", "territory", "enclave", "settlement",
                 "area", "peninsula", "gulf", "sea", "valley", "zone", "state",
                 "crossing", "checkpoint", "corridor", "village", "municipality",
                 "building", "hotel", "structure", "complex", "compound", "camp"),
}


def _strip(value: str) -> str:
    return html.unescape(_TAG_RE.sub("", value or "")).strip()


def _get(url: str, params: dict, timeout: int = 20) -> Optional[dict]:
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.warning("Lookup failed (%s): %s", url.split("/")[2], e)
        return None


# ── Wikidata ──────────────────────────────────────────────────────────────────

def wikidata_candidates(name: str, etype: str, limit: int = 5) -> list[dict]:
    """Search Wikidata for `name`; return ranked candidates {qid, label,
    description, type_plausible}. Type-plausible hits are ranked first (the
    keyword match is a soft *ranking* hint only — never a hard reject, since it
    wrongly dropped e.g. "United States Secretary of Defense" as a non-person).
    Final identity is decided by the LLM confirmation guard in ground_entity."""
    data = _get(WIKIDATA_API, {
        "action": "wbsearchentities", "search": name, "language": "en",
        "limit": limit, "format": "json",
    })
    if not data or not data.get("search"):
        return []
    hints = _TYPE_HINTS.get(etype, ())
    entries = []
    for hit in data["search"]:
        desc = hit.get("description") or ""
        entries.append({
            "qid": hit["id"], "label": hit.get("label", name), "description": desc,
            "type_plausible": any(h in desc.lower() for h in hints) if hints else True,
        })
    # Stable sort keeps Wikidata's own relevance order within each group.
    entries.sort(key=lambda e: 0 if e["type_plausible"] else 1)
    return entries


def wikidata_entity(qid: str) -> Optional[dict]:
    data = _get(WIKIDATA_API, {
        "action": "wbgetentities", "ids": qid,
        "props": "claims|labels|descriptions|sitelinks", "languages": "en", "format": "json",
    })
    try:
        return data["entities"][qid]
    except Exception:
        return None


def _claim_values(entity: dict, prop: str) -> list:
    out = []
    for claim in entity.get("claims", {}).get(prop, []):
        try:
            out.append(claim["mainsnak"]["datavalue"]["value"])
        except Exception:
            continue
    return out


def _qid_labels(qids: list[str]) -> dict[str, str]:
    """Batch-resolve QIDs to English labels."""
    if not qids:
        return {}
    data = _get(WIKIDATA_API, {
        "action": "wbgetentities", "ids": "|".join(qids[:50]),
        "props": "labels", "languages": "en", "format": "json",
    })
    labels = {}
    for qid, ent in (data or {}).get("entities", {}).items():
        try:
            labels[qid] = ent["labels"]["en"]["value"]
        except Exception:
            continue
    return labels


# ── Wikipedia summary ─────────────────────────────────────────────────────────

def wikipedia_summary(entity: dict) -> Optional[dict]:
    """{text, url} from the English Wikipedia summary for a Wikidata entity."""
    title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
    if not title:
        return None
    data = _get(WIKIPEDIA_SUMMARY.format(title=requests.utils.quote(title, safe="")), {})
    if not data or not data.get("extract"):
        return None
    url = (data.get("content_urls", {}).get("desktop", {}) or {}).get(
        "page", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")
    return {"text": data["extract"], "url": url}


# ── Entity image (P18 → Commons, license-gated) ──────────────────────────────

def commons_file_image(file_name: str, thumb_width: int = 640) -> Optional[dict]:
    """License-cleared image dict for a specific Commons file, or None."""
    data = _get(COMMONS_API, {
        "action": "query", "titles": f"File:{file_name}",
        "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": thumb_width, "format": "json",
    })
    try:
        page = next(iter(data["query"]["pages"].values()))
        info = page["imageinfo"][0]
    except Exception:
        return None
    if info.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
        return None
    meta = info.get("extmetadata", {})
    license_name = _strip(meta.get("LicenseShortName", {}).get("value", ""))
    if not license_acceptable(license_name):
        log.info("Entity image rejected (license %r): %s", license_name, file_name)
        return None
    return {
        "url": info.get("thumburl") or info["url"],
        "source_page": info.get("descriptionurl", ""),
        "credit": _strip(meta.get("Artist", {}).get("value", "")) or "Wikimedia Commons",
        "license": license_name,
        "license_url": meta.get("LicenseUrl", {}).get("value") or None,
        "provider": "Wikimedia Commons",
        "file_title": f"File:{file_name}",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Orchestration ─────────────────────────────────────────────────────────────

def ground_entity(record: dict, store, confirm=None) -> dict:
    """Fill a new entity record from Wikidata/Wikipedia. Mutates and returns it.
    Every populated field carries its citation; absent sources leave fields empty.

    `confirm` (optional): callable(hit) -> bool. Passed for person entities —
    an LLM namesake guard that must approve the hit before grounding proceeds.
    A wrong identity poisons the record; a thin card is always the safer failure."""
    name, etype = record["canonical_name"], record["type"]
    candidates = wikidata_candidates(name, etype)
    if not candidates:
        log.info("No Wikidata hit for %s (%s) — card stays thin", name, etype)
        return record

    # Try candidates in rank order; the LLM guard picks the real identity and
    # skips namesakes/disambiguation. Trying more than the top hit recovers the
    # case where a namesake outranks the correct entity in search relevance.
    hit = None
    for cand in candidates[:3]:
        if "disambiguation" in (cand["description"] or "").lower():
            continue
        if confirm is not None and not confirm(cand):
            continue
        hit = cand
        break
    if hit is None:
        store.log_review({"kind": "identity_not_confirmed", "entity_id": record["entity_id"],
                          "name": name, "type": etype,
                          "candidates": [{"qid": c["qid"], "description": c["description"]}
                                         for c in candidates[:3]]})
        log.info("No confirmed Wikidata identity for %s — card stays thin, logged", name)
        return record

    record["wikidata_qid"] = hit["qid"]
    if hit["label"] and hit["label"] != record["canonical_name"]:
        store.add_alias(record, hit["label"])

    entity = wikidata_entity(hit["qid"])
    if not entity:
        return record

    wd_url = f"https://www.wikidata.org/wiki/{hit['qid']}"

    # Summary: Wikipedia extract (preferred) or Wikidata description.
    wiki = wikipedia_summary(entity)
    if wiki:
        # First 2 sentences keep the card tight; the URL cites the full page.
        sentences = re.split(r"(?<=[.!?]) +", wiki["text"])
        record["summary"] = " ".join(sentences[:2]).strip()
        record["summary_sources"] = [wiki["url"]]
    elif hit["description"]:
        desc = hit["description"]
        record["summary"] = desc[0].upper() + desc[1:]
        record["summary_sources"] = [wd_url]

    # Image (P18) — license-gated via Commons.
    images = _claim_values(entity, _IMAGE_PROP)
    if images and isinstance(images[0], str):
        record["image"] = commons_file_image(images[0])

    # Roles (P39 position held) — cited to Wikidata. Wikidata stores one P39
    # statement per term (e.g. a legislator gets one per parliament), so dedupe
    # by label — "Knesset member" should appear once, not five times.
    role_qids = [v["id"] for v in _claim_values(entity, _ROLE_PROP)
                 if isinstance(v, dict) and "id" in v]
    labels = _qid_labels(role_qids)
    seen_roles: set[str] = set()
    for qid in role_qids:
        label = labels.get(qid)
        if not label or label.lower() in seen_roles:
            continue
        seen_roles.add(label.lower())
        record["roles_affiliations"].append({
            "role": label, "org_entity_id": None,
            "start": None, "end": None,
            "source_url": wd_url, "source_type": "reference_work",
        })
        if len(seen_roles) >= 6:
            break

    # Typed connections — only to entities ALREADY in the store (matched by QID),
    # so every edge points at a real card. Unmatched relations are simply skipped;
    # they'll link up when/if the other entity enters the store.
    rel_qids: list[tuple[str, str]] = []  # (relation_type, qid)
    for prop, rel_type in _CONNECTION_PROPS.items():
        for v in _claim_values(entity, prop):
            if isinstance(v, dict) and "id" in v:
                rel_qids.append((rel_type, v["id"]))
    for rel_type, qid in rel_qids:
        other_id = store.lookup_qid(qid)
        if other_id and other_id != record["entity_id"]:
            if not any(c["entity_id"] == other_id and c["type"] == rel_type
                       for c in record["connections"]):
                record["connections"].append({
                    "type": rel_type, "entity_id": other_id,
                    "note": None, "source_url": wd_url,
                })

    # A couple of atomic facts from the Wikipedia summary tail (beyond the card
    # summary), tiered `reported` (reference work, not independently verified by us).
    if wiki:
        tail = re.split(r"(?<=[.!?]) +", wiki["text"])[2:5]
        for sentence in tail:
            s = sentence.strip()
            if len(s) > 40:
                store.add_fact(record, {
                    "text": s,
                    "source_url": wiki["url"],
                    "source_type": "reference_work",
                    "confidence_tier": "reported",
                }, change_note="Grounded from Wikipedia")

    record["change_log"].append({
        "date": datetime.now(timezone.utc).date().isoformat(),
        "summary_of_change": f"Grounded from Wikidata {hit['qid']}"
                             + (" + Wikipedia" if wiki else ""),
        "source": wd_url,
    })
    return record
