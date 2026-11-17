"""English SRD 5.2.1 rulebook (srd-5.2.1-en): package loading, search and compendium.

The package is produced deterministically by ``tools/build_english_srd.py`` from
the text layer of the official English PDF.  Its official blocks are extracted
source text, never paraphrased; Roll Drauf's own reading notes are
``original-note`` blocks flagged ``editorial``.  This module only reads the
English package.  The German package, its compendium ids and the character pins
that reference them are untouched: English entities live in their own ruleset
and are only resolved through English routes.
"""

from __future__ import annotations

import json
import unicodedata
from fractions import Fraction
from pathlib import Path

from .compendium import MAX_LIMIT, TYPES, CompendiumQueryError, facet_values
from .generator import normalized_search_text
from .validator import CONTENT_ROOT

RULESET_ID = "srd-5.2.1-en"
PACKAGE = CONTENT_ROOT / RULESET_ID
GENERATED = PACKAGE / "generated"
SOURCE_VERSION = "5.2.1"
ROUTE_LOCALE = "en"
HOME_URL = f"/regelwerk/{SOURCE_VERSION}/{ROUTE_LOCALE}"
LICENSE_SLUG = "license"
LICENSE_URL = f"{HOME_URL}/{LICENSE_SLUG}"
PDF_READER_URL = "/regelwerk/en"

_LEVEL_MAX = {"spell": 9, "class-feature": 20}
_RARITY_RANK = {"Common": 0, "Uncommon": 1, "Rare": 2, "Very Rare": 3, "Legendary": 4, "Artifact": 5, "Varies": 6}
_TRUE = {"1", "true", "yes", "ja"}
_FALSE = {"0", "false", "no", "nein"}
_CACHE: dict[str, tuple[int, object]] = {}


def _load(path: Path):
    stamp = path.stat().st_mtime_ns
    cached = _CACHE.get(str(path))
    if cached is None or cached[0] != stamp:
        cached = _CACHE[str(path)] = (stamp, json.loads(path.read_text(encoding="utf-8")))
    return cached[1]


def available() -> bool:
    return all((path).is_file() for path in (
        PACKAGE / "manifest.json", GENERATED / "navigation.json", GENERATED / "compendium.json",
        GENERATED / "search-index.json", GENERATED / "coverage.json"))


def manifest() -> dict:
    return _load(PACKAGE / "manifest.json")


def navigation() -> dict:
    return _load(GENERATED / "navigation.json")


def coverage() -> dict:
    return _load(GENERATED / "coverage.json")


def compendium() -> dict:
    return _load(GENERATED / "compendium.json")


def attribution() -> str:
    license_ = manifest()["license"]
    return (PACKAGE / license_["attributionFile"]).read_text(encoding="utf-8")


def document_entry(document_id: str) -> dict | None:
    return next((item for item in manifest()["documents"] if item["documentId"] == document_id), None)


def document(document_id: str) -> dict | None:
    """A listed document only; ids never become paths unless the manifest names them."""
    if document_entry(document_id) is None:
        return None
    try:
        return _load(PACKAGE / "documents" / f"{document_id}.json")
    except (OSError, ValueError):
        return None


def document_by_slug(slug: str) -> dict | None:
    for section in navigation()["sections"]:
        for entry in section["documents"]:
            if entry["slug"] == slug:
                return entry
    return None


def search(query: str) -> list[dict]:
    normalized = normalized_search_text(query)
    if len(normalized) < 2:
        return []
    tokens = normalized.split()
    matches = []
    for entry in _load(GENERATED / "search-index.json")["entries"]:
        haystack = entry["normalizedText"]
        if not all(token in haystack for token in tokens):
            continue
        heading = normalized_search_text(entry["heading"])
        title = normalized_search_text(entry["title"])
        score = (
            int(normalized == heading) * 8
            + int(heading.startswith(normalized)) * 4
            + int(normalized == title) * 3
            + int(normalized in haystack) * 2
            - int(bool(entry.get("editorial"))) * 1
        )
        matches.append((-score, entry["order"], entry["ruleId"], entry))
    matches.sort(key=lambda item: item[:3])
    results = []
    for _, _, _, entry in matches[:20]:
        text = entry["text"].strip()
        results.append({
            "documentId": entry["documentId"],
            "ruleId": entry["ruleId"],
            "title": entry["title"],
            "heading": entry["heading"],
            "snippet": text if len(text) <= 220 else text[:217].rstrip() + "…",
            "url": entry["url"],
            "editorial": bool(entry.get("editorial")),
        })
    return results


# ---------------------------------------------------------------------------
# Compendium
# ---------------------------------------------------------------------------


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", normalized_search_text(value))
    return "".join(char for char in text if not unicodedata.combining(char)).replace("’", "'")


def _int(params: dict, name: str, *, low: int, high: int, default: int | None = None) -> int | None:
    raw = params.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise CompendiumQueryError(f"{name} must be an integer") from None
    if not low <= value <= high:
        raise CompendiumQueryError(f"{name} out of range")
    return value


def _cr(params: dict, name: str) -> float | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        value = float(Fraction(raw))
    except (ValueError, ZeroDivisionError):
        raise CompendiumQueryError(f"{name} must be a challenge rating") from None
    if not 0 <= value <= 30:
        raise CompendiumQueryError(f"{name} out of range")
    return value


def _bool(params: dict, name: str) -> bool | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    raise CompendiumQueryError(f"{name} must be a boolean")


def query(params: dict) -> dict:
    """List/filter contract of the German compendium API, with English facet values."""
    data = compendium()
    entity_type = params.get("type") or "spell"
    if entity_type not in TYPES:
        raise CompendiumQueryError("unknown type")
    limit = _int(params, "limit", low=1, high=MAX_LIMIT, default=50)
    offset = _int(params, "offset", low=0, high=100000, default=0)
    text = _fold(params.get("q", "")[:100])
    facets = facet_values(data["entities"], entity_type)
    items = [entity for entity in data["entities"] if entity["type"] == entity_type]

    def keep(predicate) -> None:
        nonlocal items
        items = [entity for entity in items if predicate(entity)]

    if text:
        keep(lambda e: text in _fold(e["name"]) or text in _fold(e.get("summary", "")))
    for name in facets:
        if name == "level":
            top = _LEVEL_MAX[entity_type]
            level_min = _int(params, "level_min", low=0, high=top)
            level_max = _int(params, "level_max", low=0, high=top)
            exact = _int(params, "level", low=0, high=top)
            if exact is not None:
                level_min = level_max = exact
            if level_min is not None:
                keep(lambda e: e["level"] >= level_min)
            if level_max is not None:
                keep(lambda e: e["level"] <= level_max)
            continue
        raw = params.get(name) or (params.get("class") if name == "classes" else None)
        if raw:
            wanted = {item.strip().casefold() for item in raw.split(",") if item.strip()}
            keep(lambda e, n=name, w=wanted: (
                bool({str(v).casefold() for v in e[n]} & w) if isinstance(e.get(n), list)
                else str(e.get(n) or "").casefold() in w
            ))
    if entity_type == "spell":
        for flag in ("concentration", "ritual"):
            value = _bool(params, flag)
            if value is not None:
                keep(lambda e, f=flag, v=value: e[f] is v)
        component = params.get("component")
        if component:
            component = "S" if component == "G" else component
            if component not in {"V", "S", "M"}:
                raise CompendiumQueryError("component must be V, S or M")
            keep(lambda e: component in {part.strip()[:1] for part in e["components"].split(",")})
    elif entity_type == "creature":
        cr_min, cr_max = _cr(params, "cr_min"), _cr(params, "cr_max")
        if cr_min is not None:
            keep(lambda e: e["challengeValue"] >= cr_min)
        if cr_max is not None:
            keep(lambda e: e["challengeValue"] <= cr_max)
        legendary = _bool(params, "legendary")
        if legendary is not None:
            keep(lambda e: e["legendary"] is legendary)
    elif entity_type == "magic-item":
        attunement = _bool(params, "attunement")
        if attunement is not None:
            keep(lambda e: e["attunement"] is attunement)
    elif entity_type == "class":
        spellcaster = _bool(params, "spellcaster")
        if spellcaster is not None:
            keep(lambda e: e["spellcaster"] is spellcaster)

    sorts = {
        "name": lambda e: (e["name"].casefold(), e["id"]),
        "level": lambda e: (e.get("level", 0), e["name"].casefold(), e["id"]),
        "cr": lambda e: (e.get("challengeValue", 0), e["name"].casefold(), e["id"]),
        "rarity": lambda e: (_RARITY_RANK.get(e.get("rarity"), 9), e["name"].casefold(), e["id"]),
    }
    sort = params.get("sort") or "name"
    if sort not in sorts:
        raise CompendiumQueryError("unknown sort")
    items.sort(key=sorts[sort])
    return {
        "type": entity_type,
        "total": len(items),
        "limit": limit,
        "offset": offset,
        "items": items[offset: offset + limit],
        "facets": facets,
        "rulesetId": RULESET_ID,
        "rulesetVersion": data["rulesetVersion"],
        "locale": "en-US",
    }


def entity(entity_id: str) -> dict | None:
    return next((item for item in compendium()["entities"] if item["id"] == entity_id), None)


def entry_blocks(document_: dict, entity_: dict) -> list[dict]:
    """The official blocks that make up one compendium entry (editorial notes excluded)."""
    blocks = document_["blocks"]
    index = {block["ruleId"]: position for position, block in enumerate(blocks)}
    table_id = entity_.get("tableId")
    if table_id:
        table = dict(blocks[index[table_id]])
        table["rows"] = [table["rows"][entity_["rowIndex"]]]
        result = [table]
        detail = entity_.get("detailId")
        if detail in index:
            result.append(blocks[index[detail]])
        return result
    start = index[entity_["anchor"]]
    head = blocks[start]
    if head["type"] != "heading":
        return [head]
    stop = entity_.get("excerptEnd")
    end = len(blocks)
    for position in range(start + 1, len(blocks)):
        other = blocks[position]
        if other["ruleId"] == stop or (other["type"] == "heading" and other["level"] <= head["level"]):
            end = position
            break
    result = [block for block in blocks[start:end] if not block.get("editorial")]
    for rule_id in entity_.get("extraBlocks", []):
        if rule_id in index and blocks[index[rule_id]] not in result:
            result.append(blocks[index[rule_id]])
    return result


def entry(entity_id: str) -> tuple[dict, list[dict]] | None:
    found = entity(entity_id)
    if found is None:
        return None
    doc = document(found["documentId"])
    if doc is None:
        return None
    try:
        return found, entry_blocks(doc, found)
    except (KeyError, IndexError):
        return None
