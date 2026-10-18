"""Structured, queryable compendium derived deterministically from Regelwerk documents."""

from __future__ import annotations

import re
import unicodedata
from fractions import Fraction

from .generator import document_url

SCHEMA_VERSION = "regelwerk.compendium.v1"
SCHOOLS = {
    "Erkenntnis": "Erkenntnis",
    "Verzauberung": "Verzauberung",
    "Hervorrufung": "Hervorrufung",
    "Illusion": "Illusion",
    "Beschwörung": "Beschwörung",
    "Verwandlung": "Verwandlung",
    "Nekromantie": "Nekromantie",
    "Bann": "Bann",
}
SIZES = ("Winzig", "Klein", "Mittelgroß", "Groß", "Riesig", "Gigantisch")
RARITIES = ("sehr selten", "ungewöhnlich", "gewöhnlich", "selten", "legendär", "Artefakt")


def _summary(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _sections(blocks: list[dict]) -> list[tuple[dict, list[dict]]]:
    """Split a document into (level-3 heading, following blocks) groups."""
    groups: list[tuple[dict, list[dict]]] = []
    for block in blocks:
        if block["type"] == "heading" and block["level"] == 3:
            groups.append((block, []))
        elif groups:
            groups[-1][1].append(block)
    return groups


def _base(manifest: dict, document: dict, entity_type: str, name: str, rule_id: str) -> dict:
    return {
        "id": rule_id,
        "type": entity_type,
        "name": name,
        "documentId": document["documentId"],
        "sourcePages": document["sourcePages"],
        "url": document_url(manifest, document, rule_id),
    }


def _split_top_level(text: str, sep: str = ",") -> list[str]:
    parts, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == sep and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def _spells(manifest: dict, document: dict) -> list[dict]:
    result = []
    for heading, blocks in _sections(document["blocks"]):
        school_block = next((b for b in blocks if b["type"] == "paragraph" and b["ruleId"].endswith(".schule")), None)
        props = next((b for b in blocks if b["type"] == "definition-list" and b["ruleId"].endswith(".eigenschaften")), None)
        if not school_block or not props:
            continue
        match = re.match(r"^(?P<kind>.+?) \((?P<classes>[^)]*)\)$", school_block["text"])
        if not match:
            raise ValueError(f"unparsed spell header: {school_block['text']!r}")
        kind = match["kind"]
        level_match = re.match(r"^(?P<school>\S+?)zauber (?P<level>\d)\. Grades$", kind)
        if level_match:
            school, level = level_match["school"], int(level_match["level"])
        else:
            cantrip = re.match(r"^Zaubertrick (?:der|des) (?P<school>\S+)$", kind)
            if not cantrip:
                raise ValueError(f"unparsed spell kind: {kind!r}")
            school, level = cantrip["school"], 0
        school = school if school in SCHOOLS else school.removesuffix("s")
        if school not in SCHOOLS:
            raise ValueError(f"unknown spell school: {school!r}")
        values = {entry["term"]: entry["definition"] for entry in props["entries"]}
        text_blocks = [b for b in blocks if b["type"] == "paragraph" and ".text-" in b["ruleId"]]
        entity = _base(manifest, document, "spell", heading["text"], heading["ruleId"])
        entity.update(
            {
                "level": level,
                "school": SCHOOLS[school],
                "classes": sorted(item.strip() for item in match["classes"].split(",") if item.strip()),
                "castingTime": values["Zeitaufwand"],
                "range": values["Reichweite"],
                "components": values["Komponenten"],
                "duration": values["Wirkungsdauer"],
                "concentration": "Konzentration" in values["Wirkungsdauer"],
                "ritual": "Ritual" in values["Zeitaufwand"],
                "summary": _summary(text_blocks[0]["text"]) if text_blocks else "",
            }
        )
        result.append(entity)
    return result


def _hg(value: str) -> tuple[str, float, int | None]:
    match = re.match(r"^(?P<cr>\d+(?:/\d+)?) \((?:EP (?P<xp>[\d.]+)|(?P<xp2>[\d.]+) EP)", value)
    if not match:
        raise ValueError(f"unparsed challenge rating: {value!r}")
    xp = (match["xp"] or match["xp2"]).replace(".", "")
    return match["cr"], float(Fraction(match["cr"])), int(xp)


def _creature_type(value: str) -> tuple[str | None, str, str]:
    head, _, alignment = value.partition(", ")
    size = next((s for s in SIZES if head.startswith(s)), None)
    kind = head
    if size:
        kind = re.sub(r"^\S+(?: oder \S+)? ", "", head, count=1)
    return size, kind.strip(), alignment.strip()


def _first_int(value: str) -> int | None:
    match = re.match(r"^\d+", value)
    return int(match.group()) if match else None


def _creatures(manifest: dict, document: dict) -> list[dict]:
    result = []
    for heading in (b for b in document["blocks"] if b["type"] == "stat-block"):
        entries = {entry["label"]: entry["value"] for entry in heading["entries"]}
        size, kind, alignment = _creature_type(entries["Typ"])
        challenge, challenge_value, xp = _hg(entries["HG"])
        sections = {section["title"] for section in heading.get("sections", [])}
        entity = _base(manifest, document, "creature", heading["name"], heading["ruleId"])
        entity.update(
            {
                "origin": "animal" if document["documentId"].startswith("animals.") else "monster",
                "size": size,
                "creatureType": re.sub(r"\s*\(.*\)$", "", kind),
                "subtype": (re.search(r"\((.*)\)$", kind) or [None, None])[1],
                "alignment": alignment,
                "armorClass": _first_int(entries["RK"]),
                "hitPoints": _first_int(entries["TP"]),
                "speed": entries["Bewegungsrate"],
                "challenge": challenge,
                "challengeValue": challenge_value,
                "xp": xp,
                "legendary": "Legendäre Aktionen" in sections,
                "summary": f"{entries['Typ']} · RK {entries['RK']} · TP {entries['TP']} · HG {challenge}",
            }
        )
        result.append(entity)
    return result


def _magic_items(manifest: dict, document: dict) -> list[dict]:
    result = []
    for heading, blocks in _sections(document["blocks"]):
        subtitle = next((b for b in blocks if b["type"] == "paragraph" and b["ruleId"].endswith(".untertitel")), None)
        if not subtitle:
            continue
        text = subtitle["text"]
        parts = _split_top_level(text)
        category = parts[0]
        rest = ", ".join(parts[1:])
        rarity = next((r for r in RARITIES if re.search(rf"(?<![\w]){re.escape(r)}(?![\w])", re.sub(r"\([^)]*\)", "", rest))), None)
        if rarity is None:
            rarity = "variabel" if "variiert" in rest or "oder" in rest else None
        if rarity is None:
            raise ValueError(f"unparsed magic item subtitle: {text!r}")
        body = [b for b in blocks if b is not subtitle and b["type"] == "paragraph"]
        entity = _base(manifest, document, "magic-item", heading["text"], heading["ruleId"])
        entity.update(
            {
                "category": re.sub(r"\s*\(.*\)$", "", category),
                "detail": subtitle["text"],
                "rarity": rarity,
                "attunement": "Einstimmung" in text,
                "summary": _summary(body[0]["text"]) if body else "",
            }
        )
        result.append(entity)
    return result


def _feats(manifest: dict, document: dict) -> list[dict]:
    result = []
    blocks = document["blocks"]
    for index, block in enumerate(blocks):
        if block["type"] != "heading" or block["level"] != 4:
            continue
        following = []
        for item in blocks[index + 1:]:
            if item["type"] == "heading":
                break
            following.append(item)
        category_block = next((b for b in following if b["ruleId"].endswith("-category")), None)
        if not category_block:
            continue
        match = re.match(r"^(?P<category>[^(]+?)(?: \(Voraussetzung: (?P<pre>.+)\))?$", category_block["text"])
        if not match:
            raise ValueError(f"unparsed feat category: {category_block['text']!r}")
        description = next((b for b in following if b["ruleId"].endswith("-description")), None)
        entity = _base(manifest, document, "feat", block["text"], block["ruleId"])
        entity.update(
            {
                "category": match["category"],
                "prerequisite": match["pre"],
                "summary": _summary(description["text"]) if description else "",
            }
        )
        result.append(entity)
    return result


_WEAPON_GROUPS = {
    "weapons-simple-melee": ("Einfach", "Nahkampf"),
    "weapons-simple-ranged": ("Einfach", "Fernkampf"),
    "weapons-martial-melee": ("Kriegswaffe", "Nahkampf"),
    "weapons-martial-ranged": ("Kriegswaffe", "Fernkampf"),
}
_ARMOR_GROUPS = {
    "armor-light": "Leicht",
    "armor-medium": "Mittelschwer",
    "armor-heavy": "Schwer",
    "armor-shield-table": "Schild",
}


def _slug(value: str) -> str:
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})
    text = unicodedata.normalize("NFC", value).translate(table).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _equipment(manifest: dict, document: dict) -> list[dict]:
    result = []
    for block in document["blocks"]:
        if block["type"] != "table":
            continue
        key = block["ruleId"].rsplit(".", 1)[-1]
        if key in _WEAPON_GROUPS:
            weapon_class, weapon_kind = _WEAPON_GROUPS[key]
            for row_index, row in enumerate(block["rows"]):
                name, damage, properties, mastery, weight, cost = row
                entity = _base(manifest, document, "weapon", name, f"{block['ruleId']}.{_slug(name)}")
                entity["url"] = document_url(manifest, document, block["ruleId"])
                entity.update(
                    {
                        "tableId": block["ruleId"],
                        "rowIndex": row_index,
                        "weaponClass": weapon_class,
                        "weaponKind": weapon_kind,
                        "damage": damage,
                        "properties": properties,
                        "mastery": mastery,
                        "weight": weight,
                        "cost": cost,
                        "summary": f"{damage} · {properties}",
                    }
                )
                result.append(entity)
        elif key in _ARMOR_GROUPS:
            for row_index, row in enumerate(block["rows"]):
                name, armor_class, strength, stealth, weight, cost = row
                entity = _base(manifest, document, "armor", name, f"{block['ruleId']}.{_slug(name)}")
                entity["url"] = document_url(manifest, document, block["ruleId"])
                entity.update(
                    {
                        "tableId": block["ruleId"],
                        "rowIndex": row_index,
                        "armorCategory": _ARMOR_GROUPS[key],
                        "armorClass": armor_class,
                        "strength": strength,
                        "stealth": stealth,
                        "weight": weight,
                        "cost": cost,
                        "summary": f"RK {armor_class} · {cost}",
                    }
                )
                result.append(entity)
    return result


def build_compendium(manifest: dict, documents: list[dict]) -> dict:
    from .compendium_creator import build_creator_entities

    entities: list[dict] = []
    for document in documents:
        prefix = document["documentId"].split(".", 1)[0]
        if prefix == "spells":
            entities.extend(_spells(manifest, document))
        elif prefix in {"monsters", "animals"}:
            entities.extend(_creatures(manifest, document))
        elif prefix == "magic-items":
            entities.extend(_magic_items(manifest, document))
        elif document["documentId"] == "feats.descriptions":
            entities.extend(_feats(manifest, document))
        elif document["documentId"] in {"equipment.coins-and-weapons", "equipment.armor"}:
            entities.extend(_equipment(manifest, document))
    entities.extend(
        build_creator_entities(
            manifest,
            documents,
            [e for e in entities if e["type"] == "spell"],
            [e for e in entities if e["type"] == "feat"],
        )
    )
    seen: set[str] = set()
    for entity in entities:
        if entity["id"] in seen:
            raise ValueError(f"duplicate compendium id: {entity['id']}")
        seen.add(entity["id"])
    entities.sort(key=lambda item: (item["type"], item["name"].casefold(), item["id"]))
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity["type"]] = counts.get(entity["type"], 0) + 1
    return {
        "schemaVersion": SCHEMA_VERSION,
        "rulesetId": manifest["rulesetId"],
        "rulesetVersion": manifest["rulesetVersion"],
        "counts": dict(sorted(counts.items())),
        "entities": entities,
    }


_LIST_FACETS = {
    "spell": ("level", "school", "classes"),
    "creature": ("size", "creatureType", "origin"),
    "magic-item": ("category", "rarity"),
    "feat": ("category",),
    "weapon": ("weaponClass", "weaponKind", "mastery"),
    "armor": ("armorCategory",),
    "class": ("primaryAbility", "hitDie"),
    "subclass": ("className",),
    "class-feature": ("level", "className", "subclass"),
    "class-option": ("className", "optionKind"),
    "species": ("creatureType", "sizes"),
    "background": ("feat",),
    "gear": ("category",),
    "tool": ("category", "ability"),
    "mount": (),
    "vehicle": (),
    "service": ("category",),
    "glossary": ("category",),
}
_LEVEL_MAX = {"spell": 9, "class-feature": 20}
TYPES = tuple(_LIST_FACETS)
MAX_LIMIT = 200


_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


class CompendiumQueryError(ValueError):
    pass


def _fold(value: object) -> str:
    from .generator import normalized_search_text

    return normalized_search_text(value).translate(_UMLAUTS)


def _parse_int(params: dict, name: str, *, low: int, high: int, default: int | None = None) -> int | None:
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


def _parse_cr(params: dict, name: str) -> float | None:
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


def _parse_bool(params: dict, name: str) -> bool | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    if raw in {"1", "true", "ja"}:
        return True
    if raw in {"0", "false", "nein"}:
        return False
    raise CompendiumQueryError(f"{name} must be a boolean")


def facet_values(entities: list[dict], entity_type: str) -> dict[str, list]:
    facets: dict[str, set] = {name: set() for name in _LIST_FACETS[entity_type]}
    for entity in entities:
        if entity["type"] != entity_type:
            continue
        for name in facets:
            value = entity.get(name)
            if isinstance(value, list):
                facets[name].update(value)
            elif value not in (None, ""):
                facets[name].add(value)
    return {
        name: sorted(values, key=lambda item: (0, item, "") if isinstance(item, int) else (1, 0, str(item).casefold()))
        for name, values in facets.items()
    }


def query_compendium(data: dict, params: dict) -> dict:
    entity_type = params.get("type") or "spell"
    if entity_type not in TYPES:
        raise CompendiumQueryError("unknown type")
    limit = _parse_int(params, "limit", low=1, high=MAX_LIMIT, default=50)
    offset = _parse_int(params, "offset", low=0, high=100000, default=0)
    query = _fold(params.get("q", "")[:100])
    items = [entity for entity in data["entities"] if entity["type"] == entity_type]

    def keep(predicate):
        nonlocal items
        items = [entity for entity in items if predicate(entity)]

    if query:
        keep(lambda e: query in _fold(e["name"]) or query in _fold(e.get("summary", "")))

    for name in _LIST_FACETS[entity_type]:
        if name == "level":
            top = _LEVEL_MAX[entity_type]
            level_min = _parse_int(params, "level_min", low=0, high=top)
            level_max = _parse_int(params, "level_max", low=0, high=top)
            exact = _parse_int(params, "level", low=0, high=top)
            if exact is not None:
                level_min = level_max = exact
            if level_min is not None:
                keep(lambda e: e["level"] >= level_min)
            if level_max is not None:
                keep(lambda e: e["level"] <= level_max)
            continue
        raw = params.get(name) or (params.get("class") if name == "classes" else None)
        if raw:
            wanted = {item.casefold() for item in raw.split(",") if item.strip()}
            keep(lambda e, n=name, w=wanted: (
                bool({v.casefold() for v in e[n]} & w) if isinstance(e.get(n), list)
                else str(e.get(n) or "").casefold() in w
            ))

    if entity_type == "spell":
        for flag in ("concentration", "ritual"):
            value = _parse_bool(params, flag)
            if value is not None:
                keep(lambda e, f=flag, v=value: e[f] is v)
        component = params.get("component")
        if component:
            if component not in {"V", "G", "M"}:
                raise CompendiumQueryError("component must be V, G or M")
            keep(lambda e: component in {part.strip()[:1] for part in e["components"].split(",")})
    elif entity_type == "creature":
        cr_min, cr_max = _parse_cr(params, "cr_min"), _parse_cr(params, "cr_max")
        if cr_min is not None:
            keep(lambda e: e["challengeValue"] >= cr_min)
        if cr_max is not None:
            keep(lambda e: e["challengeValue"] <= cr_max)
        legendary = _parse_bool(params, "legendary")
        if legendary is not None:
            keep(lambda e: e["legendary"] is legendary)
    elif entity_type == "magic-item":
        attunement = _parse_bool(params, "attunement")
        if attunement is not None:
            keep(lambda e: e["attunement"] is attunement)
    elif entity_type == "class":
        spellcaster = _parse_bool(params, "spellcaster")
        if spellcaster is not None:
            keep(lambda e: e["spellcaster"] is spellcaster)

    sort = params.get("sort") or "name"
    rarity_rank = {"gewöhnlich": 0, "ungewöhnlich": 1, "selten": 2, "sehr selten": 3, "legendär": 4, "Artefakt": 5}
    sorts = {
        "name": lambda e: e["name"].casefold(),
        "level": lambda e: (e.get("level", 0), e["name"].casefold()),
        "cr": lambda e: (e.get("challengeValue", 0), e["name"].casefold()),
        "rarity": lambda e: (rarity_rank.get(e.get("rarity"), 9), e["name"].casefold()),
    }
    if sort not in sorts:
        raise CompendiumQueryError("unknown sort")
    items.sort(key=sorts[sort])
    total = len(items)
    return {
        "type": entity_type,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items[offset: offset + limit],
        "facets": facet_values(data["entities"], entity_type),
    }


def entry_excerpt(document: dict, entity: dict) -> list[dict]:
    """Verbatim package blocks that make up one compendium entry."""
    blocks = document["blocks"]
    by_id = {block.get("ruleId"): index for index, block in enumerate(blocks)}

    def section(rule_id: str) -> list[dict]:
        start = by_id[rule_id]
        head = blocks[start]
        if head["type"] != "heading":
            return [head]
        end = len(blocks)
        for index in range(start + 1, len(blocks)):
            other = blocks[index]
            if other["type"] == "heading" and other["level"] <= head["level"]:
                end = index
                break
        return blocks[start:end]

    result: list[dict] = []
    table_id = entity.get("tableId")
    if table_id:
        table = dict(blocks[by_id[table_id]])
        table["rows"] = [table["rows"][entity["rowIndex"]]]
        result.append(table)
        if entity.get("detailId"):
            result.extend(section(entity["detailId"]))
        return result
    anchor = entity["url"].split("#", 1)[1]
    if entity["type"] == "class":
        prefix = anchor.rsplit(".", 1)[0]
        start = by_id[anchor]
        features = by_id[f"{prefix}.class-features"]
        end = next((i for i in range(features + 1, len(blocks)) if blocks[i]["type"] == "heading" and blocks[i]["level"] == 4), len(blocks))
        overview = blocks[start:end]
        progression = blocks[by_id[f"{prefix}.progression-table"]]
        return overview if progression in overview else overview + [progression]
    return section(anchor)
