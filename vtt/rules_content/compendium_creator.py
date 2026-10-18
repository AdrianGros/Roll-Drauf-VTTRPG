"""Creator-facing compendium entities: classes, species, backgrounds, gear, tools, glossary."""

from __future__ import annotations

import re
import unicodedata

from .generator import document_url
from .compendium import SIZES, _base, _slug, _split_top_level, _summary

_COUNT_WORDS = {"einen": 1, "eine": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5}
_FEATURE_HEADING = re.compile(r"^(?P<level>\d+)\. Stufe: (?P<name>.+)$")
_PRICE_SUFFIX = re.compile(r"^(?P<name>.+?) \((?P<cost>[^()]*(?:\([^()]*\))?[^()]*)\)$")
_TAG_SUFFIX = re.compile(r"^(?P<name>.+?) \((?P<tag>[^()]+)\)$")
# The official German source names these four spells differently in its class spell lists than in the
# spell descriptions (e.g. list "Licht" vs. description heading "Leicht"). The package keeps both
# spellings verbatim; this map only links them.
_SPELL_LIST_ALIASES = {
    "Licht": "Leicht",
    "Fliegen": "Flug",
    "Springen": "Sprung",
    "Verwünschen": "Verwünschung",
}
_OPTION_GROUPS = {
    "Metamagie-Optionen": "Metamagie",
    "Schauerliche-Anrufung-Optionen": "Schauerliche Anrufung",
}


def _first_paragraph(blocks: list[dict]) -> str:
    for block in blocks:
        if block["type"] == "paragraph":
            return _summary(block["text"])
    return ""


def _following(blocks: list[dict], index: int, stop_level: int) -> list[dict]:
    """Blocks after blocks[index] up to the next heading of level <= stop_level."""
    result = []
    for block in blocks[index + 1:]:
        if block["type"] == "heading" and block["level"] <= stop_level:
            break
        result.append(block)
    return result


def _definitions(block: dict | None) -> dict[str, str]:
    return {entry["term"]: entry["definition"] for entry in block["entries"]} if block else {}


def _equipment_options(text: str) -> dict[str, str]:
    options = {}
    for match in re.finditer(r"\((?P<key>[A-C])\) (?P<value>.+?)(?= oder \([A-C]\) |$)", text):
        options[match["key"]] = match["value"].strip()
    return options


def _skill_choice(text: str) -> dict:
    match = re.match(r"^Wähle (?P<count>\w+) aus: (?P<list>.+)$", text)
    if match and match["count"] in _COUNT_WORDS:
        options = [item.strip() for item in re.split(r",| oder ", match["list"]) if item.strip()]
        return {"count": _COUNT_WORDS[match["count"]], "options": options}
    free = re.match(r"^(?P<count>\w+) Fertigkeiten deiner Wahl", text)
    if free and free["count"].lower() in _COUNT_WORDS:
        return {"count": _COUNT_WORDS[free["count"].lower()], "options": None}
    raise ValueError(f"unparsed skill choice: {text!r}")


def _split_and(text: str) -> list[str]:
    return [item.strip() for item in re.split(r",| und ", text) if item.strip()]


def _progression(table: dict) -> list[dict]:
    columns = table["columns"]
    if columns[:3] != ["Stufe", "Übungsbonus", "Klassenmerkmale"]:
        raise ValueError(f"unexpected progression columns: {columns}")
    rows = []
    for row in table["rows"]:
        features = [] if row[2] == "–" else _split_top_level(row[2])
        extras = {column: value for column, value in zip(columns[3:], row[3:]) if value != "–"}
        rows.append({"level": int(row[0]), "proficiencyBonus": row[1], "features": features, "extras": extras})
    return rows


def _spell_lists(blocks: list[dict], spells: list[dict], spell_ids: dict[str, str], class_name: str) -> dict[str, list[str]]:
    """Class spell list per grade, taken from each spell's own class line.

    The printed list tables in the source are incomplete or misplace rows
    (Druid, Bard, Wizard, Sorcerer), so they are only checked for unknown names.
    """
    for block in blocks:
        if block["type"] != "table" or not re.match(r"^spell-list-(?:cantrips|level\d)$", block["ruleId"].rsplit(".", 1)[-1]):
            continue
        for row in block["rows"]:
            name = re.sub(r"\s*\*+$", "", row[0]).strip()
            if _SPELL_LIST_ALIASES.get(name, name) not in spell_ids:
                raise ValueError(f"{class_name}: spell list entry without spell: {name!r}")
    lists: dict[str, list[str]] = {}
    for spell in sorted(spells, key=lambda item: item["name"].casefold()):
        if class_name in spell["classes"]:
            lists.setdefault(str(spell["level"]), []).append(spell["id"])
    return dict(sorted(lists.items()))


def _classes(manifest: dict, document: dict, spells: list[dict], spell_ids: dict[str, str]) -> list[dict]:
    blocks = document["blocks"]
    key = document["documentId"].split(".")[1]
    head = blocks[0]
    traits = _definitions(next(b for b in blocks if b["ruleId"].endswith(".key-traits")))
    hit_die = re.match(r"^1W(\d+) pro ", traits["Trefferpunktewürfel"])
    if not hit_die:
        raise ValueError(f"unparsed hit die: {traits['Trefferpunktewürfel']!r}")
    progression_table = next(b for b in blocks if b["ruleId"].endswith(".progression-table"))
    spell_lists = _spell_lists(blocks, spells, spell_ids, head["text"])
    entities: list[dict] = []
    feature_ids: list[str] = []
    subclass_ids: list[str] = []
    current_h3: dict | None = None
    current_subclass: str | None = None
    subclass_features: dict[str, list[str]] = {}
    option_kind: str | None = None

    for index, block in enumerate(blocks):
        if block["type"] != "heading":
            continue
        if block["level"] == 3:
            current_h3 = block
            subclass_match = re.match(r"^(?P<cls>.+?)-Unterklasse: (?P<name>.+)$", block["text"])
            option_kind = _OPTION_GROUPS.get(block["text"])
            current_subclass = subclass_match["name"] if subclass_match else None
            if subclass_match:
                body = _following(blocks, index, 3)
                motto = next((b["text"] for b in body if b["type"] == "paragraph" and b["ruleId"].endswith("-motto")), None)
                intro = next((b for b in body if b["type"] == "paragraph" and b["ruleId"].endswith("-introduction")), None)
                subclass = _base(manifest, document, "subclass", subclass_match["name"], block["ruleId"])
                subclass.update(
                    {
                        "className": head["text"],
                        "classKey": key,
                        "motto": motto,
                        "summary": _summary(intro["text"]) if intro else "",
                        "features": [],
                    }
                )
                entities.append(subclass)
                subclass_ids.append(block["ruleId"])
                subclass_features[block["ruleId"]] = subclass["features"]
            continue
        if block["level"] != 4 or current_h3 is None:
            continue
        body = _following(blocks, index, 4)
        feature = _FEATURE_HEADING.match(block["text"])
        if feature:
            entity = _base(manifest, document, "class-feature", feature["name"], block["ruleId"])
            entity.update(
                {
                    "className": head["text"],
                    "classKey": key,
                    "level": int(feature["level"]),
                    "subclass": current_subclass,
                    "summary": _first_paragraph(body),
                }
            )
            entities.append(entity)
            if current_subclass:
                subclass_features[current_h3["ruleId"]].append(block["ruleId"])
            else:
                feature_ids.append(block["ruleId"])
        elif option_kind:
            prerequisite = next((b["text"] for b in body if b["ruleId"].endswith("-prerequisite")), None)
            cost = next((b["text"] for b in body if b["ruleId"].endswith("-cost")), None)
            description = next((b for b in body if b["ruleId"].endswith("-description") or b["ruleId"].endswith("-introduction")), None)
            entity = _base(manifest, document, "class-option", block["text"], block["ruleId"])
            entity.update(
                {
                    "className": head["text"],
                    "classKey": key,
                    "optionKind": option_kind,
                    "prerequisite": prerequisite.removeprefix("Voraussetzung: ") if prerequisite else None,
                    "cost": cost.removeprefix("Kosten: ") if cost else None,
                    "summary": _summary(description["text"]) if description else "",
                }
            )
            entities.append(entity)

    skills = _skill_choice(traits["Fertigkeiten, in denen du geübt bist"])
    class_entity = _base(manifest, document, "class", head["text"], head["ruleId"])
    class_entity.update(
        {
            "classKey": key,
            "primaryAbility": traits["Hauptattribut"],
            "hitDie": int(hit_die[1]),
            "savingThrows": _split_and(traits["Rettungswürfe, in denen du geübt bist"]),
            "skillChoices": skills,
            "weaponTraining": traits["Übung im Umgang mit Waffen"],
            "toolTraining": traits.get("Übung im Umgang mit Werkzeug"),
            "armorTraining": traits["Rüstungsvertrautheit"],
            "startingEquipment": traits["Anfangsausrüstung"],
            "startingEquipmentOptions": _equipment_options(traits["Anfangsausrüstung"]),
            "spellcaster": bool(spell_lists),
            "subclasses": subclass_ids,
            "features": feature_ids,
            "progression": _progression(progression_table),
            "spellList": spell_lists,
            "summary": f"W{hit_die[1]} · Hauptattribut {traits['Hauptattribut']} · Rettungswürfe {traits['Rettungswürfe, in denen du geübt bist']}",
        }
    )
    for subclass_id, features in subclass_features.items():
        if not features:
            raise ValueError(f"subclass without features: {subclass_id}")
    return [class_entity, *entities]


def _species(manifest: dict, document: dict) -> list[dict]:
    blocks = document["blocks"]
    start = next(i for i, b in enumerate(blocks) if b["ruleId"].endswith(".species-descriptions"))
    result = []
    for index in range(start + 1, len(blocks)):
        block = blocks[index]
        if block["type"] != "heading" or block["level"] != 4:
            continue
        body = _following(blocks, index, 4)
        details = _definitions(next(b for b in body if b["ruleId"].endswith("-traits")))
        size_text = details["Größe"]
        sizes = [s for s in SIZES if re.search(rf"(?<!\w){s}(?!\w)", size_text, re.IGNORECASE)]
        speed = re.match(r"^(\d+(?:,\d+)?) m$", details["Bewegungsrate"])
        if not speed:
            raise ValueError(f"unparsed species speed: {details['Bewegungsrate']!r}")
        trait_names = []
        darkvision = None
        for item in body:
            if item["type"] != "paragraph" or item["ruleId"].endswith("-introduction"):
                continue
            match = re.match(r"^(?P<name>[^:.]{2,60}): (?P<text>.+)$", item["text"])
            if not match or item["ruleId"].endswith("-traits-introduction"):
                continue
            trait_names.append(match["name"])
            sight = re.search(r"Dunkelsicht mit einer Reichweite von (\d+) Metern", item["text"])
            if match["name"] == "Dunkelsicht" and sight:
                darkvision = int(sight[1])
        entity = _base(manifest, document, "species", block["text"], block["ruleId"])
        entity.update(
            {
                "creatureType": details["Kreaturentyp"],
                "sizeText": size_text,
                "sizes": sizes,
                "speed": details["Bewegungsrate"],
                "speedMeters": float(speed[1].replace(",", ".")),
                "darkvision": darkvision,
                "traits": trait_names,
                "tables": [b["caption"] for b in body if b["type"] == "table"],
                "summary": f"{details['Kreaturentyp']} · {size_text.split(' –')[0]} · Bewegungsrate {details['Bewegungsrate']}",
            }
        )
        result.append(entity)
    return result


def _backgrounds(manifest: dict, document: dict, feat_names: set[str]) -> list[dict]:
    blocks = document["blocks"]
    start = next(i for i, b in enumerate(blocks) if b["ruleId"].endswith(".background-descriptions"))
    result = []
    for index in range(start + 1, len(blocks)):
        block = blocks[index]
        if block["type"] != "heading" or block["level"] != 4:
            continue
        body = _following(blocks, index, 4)
        details = _definitions(next(b for b in body if b["ruleId"].endswith("-traits")))
        feat_text = re.sub(r"\s*\(siehe „Talente“\)$", "", details["Talent"])
        feat_match = re.match(r"^(?P<feat>.+?)(?: \((?P<choice>[^)]+)\))?$", feat_text)
        feat = feat_match["feat"]
        if feat not in feat_names:
            raise ValueError(f"{block['text']}: feat not in compendium: {feat!r}")
        entity = _base(manifest, document, "background", block["text"], block["ruleId"])
        entity.update(
            {
                "abilities": [item.strip() for item in details["Attributswerte"].split(",")],
                "feat": feat,
                "featChoice": feat_match["choice"],
                "skills": [item.strip() for item in details["Fertigkeiten, in denen du geübt bist"].split(" und ")],
                "tool": details["Übung im Umgang mit Werkzeug"],
                "equipment": details["Ausrüstung"],
                "equipmentOptions": _equipment_options(details["Ausrüstung"]),
                "summary": f"Talent {feat_text} · Fertigkeiten {details['Fertigkeiten, in denen du geübt bist']}",
            }
        )
        result.append(entity)
    return result


def _fold_key(value: str) -> frozenset[str]:
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
    text = unicodedata.normalize("NFC", value).lower().translate(table)
    return frozenset(re.sub(r"[(),:]", " ", text).split())


_GEAR_ALIASES = {
    "Abdeckbare Laterne": "Laterne, abdeckbar",
    "Behälter (Karte oder Schriftrolle)": "Behälter, Karten oder Schriftrollen",
}
_GEAR_SUBTABLES = {
    "arcane-foci": "Arkaner Fokus",
    "druidic-foci": "Druidischer Fokus",
    "holy-symbols": "Heiliges Symbol",
    "ammunition": "Geschosse",
}


def _gear(manifest: dict, document: dict) -> list[dict]:
    blocks = document["blocks"]
    descriptions: dict[frozenset[str], tuple[dict, list[dict]]] = {}
    for index, block in enumerate(blocks):
        if block["type"] == "heading" and block["level"] == 3:
            match = _PRICE_SUFFIX.match(block["text"])
            name = match["name"] if match else block["text"]
            descriptions[_fold_key(name)] = (block, _following(blocks, index, 3))
    result = []
    for block in blocks:
        if block["type"] != "table":
            continue
        key = block["ruleId"].rsplit(".", 1)[-1]
        if key == "gear-table":
            category = "Abenteurerausrüstung"
        elif key in _GEAR_SUBTABLES:
            category = _GEAR_SUBTABLES[key]
        else:
            continue
        for row_index, row in enumerate(block["rows"]):
            name = row[0]
            if key == "ammunition":
                weight, cost, extra = row[3], row[4], f"{row[1]} {row[2]}"
            else:
                weight, cost, extra = row[1], row[2], ""
            looked_up = _GEAR_ALIASES.get(name, name)
            heading, body = descriptions.get(_fold_key(looked_up), (None, []))
            if heading is None and key == "gear-table":
                base = re.sub(r"\s*\(.*\)$", "", name)
                heading, body = descriptions.get(_fold_key(base), (None, []))
            rule_id = f"{block['ruleId']}.{_slug(name)}"
            entity = _base(manifest, document, "gear", name, rule_id)
            entity["url"] = document_url(manifest, document, block["ruleId"])
            if heading is not None and key == "gear-table":
                entity["url"] = document_url(manifest, document, heading["ruleId"])
                entity["detailId"] = heading["ruleId"]
            entity.update(
                {
                    "category": category,
                    "weight": weight,
                    "cost": cost,
                    "tableId": block["ruleId"],
                    "rowIndex": row_index,
                    "summary": _first_paragraph(body) or (f"{extra} · {cost}" if extra else cost),
                }
            )
            result.append(entity)
    return result


def _tools(manifest: dict, document: dict) -> list[dict]:
    blocks = document["blocks"]
    group = None
    result = []
    for index, block in enumerate(blocks):
        if block["type"] != "heading":
            continue
        if block["level"] == 3:
            group = block["text"]
            continue
        if block["level"] != 4 or group not in {"Handwerkszeug", "Anderes Werkzeug"}:
            continue
        match = _PRICE_SUFFIX.match(block["text"])
        if not match:
            raise ValueError(f"unparsed tool heading: {block['text']!r}")
        details = _definitions(next(b for b in _following(blocks, index, 4) if b["type"] == "definition-list"))
        entity = _base(manifest, document, "tool", match["name"], block["ruleId"])
        entity.update(
            {
                "category": group,
                "ability": details["Attribut"],
                "cost": match["cost"],
                "weight": details.get("Gewicht"),
                "use": details.get("Verwenden"),
                "crafts": details.get("Herstellen"),
                "summary": f"{details['Attribut']} · {match['cost']}" + (f" · {details['Gewicht']}" if details.get("Gewicht") else ""),
            }
        )
        result.append(entity)
    return result


def _mounts_and_vehicles(manifest: dict, document: dict) -> list[dict]:
    result = []
    for block in document["blocks"]:
        if block["type"] != "table":
            continue
        key = block["ruleId"].rsplit(".", 1)[-1]
        for row_index, row in enumerate(block["rows"]):
            common = {"tableId": block["ruleId"], "rowIndex": row_index}
            rule_id = f"{block['ruleId']}.{_slug(row[0])}"
            if key == "mounts-and-animals-table":
                entity = _base(manifest, document, "mount", row[0], rule_id)
                entity.update(common | {"carryingCapacity": row[1], "cost": row[2], "summary": f"Traglast {row[1]} · {row[2]}"})
            elif key in {"tack-and-vehicles-table", "saddles-table"}:
                entity = _base(manifest, document, "gear", row[0], rule_id)
                entity.update(
                    common
                    | {"category": "Sattel, Zaumzeug und Fuhrwerke", "weight": row[1], "cost": row[2], "summary": f"{row[1]} · {row[2]}"}
                )
            elif key == "air-and-water-vehicles-table":
                entity = _base(manifest, document, "vehicle", row[0], rule_id)
                entity.update(
                    common
                    | {
                        "speed": row[1],
                        "crew": row[2],
                        "passengers": row[3],
                        "cargoTons": row[4],
                        "armorClass": row[5],
                        "hitPoints": row[6],
                        "damageThreshold": row[7],
                        "cost": row[8],
                        "summary": f"Bewegungsrate {row[1]} · RK {row[5]} · TP {row[6]} · {row[8]}",
                    }
                )
            else:
                continue
            entity["url"] = document_url(manifest, document, block["ruleId"])
            result.append(entity)
    return result


def _services(manifest: dict, document: dict) -> list[dict]:
    blocks = document["blocks"]
    result = []
    for index, block in enumerate(blocks):
        if block["type"] == "heading" and block["level"] == 3 and block["ruleId"].split(".")[-1].startswith("lifestyle-"):
            match = _PRICE_SUFFIX.match(block["text"])
            if not match:
                raise ValueError(f"unparsed lifestyle heading: {block['text']!r}")
            entity = _base(manifest, document, "service", match["name"], block["ruleId"])
            entity.update(
                {
                    "category": "Lebenshaltungskosten",
                    "cost": match["cost"],
                    "summary": _first_paragraph(_following(blocks, index, 3)) or match["cost"],
                }
            )
            result.append(entity)
        elif block["type"] == "table":
            key = block["ruleId"].rsplit(".", 1)[-1]
            category = {
                "food-drink-lodging-table": "Essen, Trinken und Unterkunft",
                "hirelings-table": "Mietlinge",
                "spellcasting-services-table": "Zauberwirken",
            }.get(key)
            if not category:
                continue
            for row_index, row in enumerate(block["rows"]):
                spellcasting = key == "spellcasting-services-table"
                name = f"Zauberwirken: {'Zaubertrick' if row[0] == 'Zaubertrick' else 'Grad ' + row[0]}" if spellcasting else row[0]
                cost = row[-1]
                entity = _base(manifest, document, "service", name, f"{block['ruleId']}.{_slug(name)}")
                entity["url"] = document_url(manifest, document, block["ruleId"])
                entity.update(
                    {
                        "category": category,
                        "cost": cost,
                        "tableId": block["ruleId"],
                        "rowIndex": row_index,
                        "summary": f"{cost} · {row[1]}" if spellcasting else cost,
                    }
                )
                result.append(entity)
    return result


def _glossary(manifest: dict, document: dict) -> list[dict]:
    blocks = document["blocks"]
    result = []
    for index, block in enumerate(blocks):
        if block["type"] != "heading" or block["level"] != 3:
            continue
        match = _TAG_SUFFIX.match(block["text"])
        name, category = (match["name"], match["tag"]) if match else (block["text"], "Regelbegriff")
        entity = _base(manifest, document, "glossary", name, block["ruleId"])
        entity.update({"category": category, "summary": _first_paragraph(_following(blocks, index, 3))})
        result.append(entity)
    return result


def build_creator_entities(manifest: dict, documents: list[dict], spells: list[dict], feats: list[dict]) -> list[dict]:
    spell_ids: dict[str, str] = {}
    for spell in spells:
        if spell["name"] in spell_ids:
            raise ValueError(f"ambiguous spell name: {spell['name']}")
        spell_ids[spell["name"]] = spell["id"]
    feat_names = {feat["name"] for feat in feats}
    entities: list[dict] = []
    for document in documents:
        document_id = document["documentId"]
        if document_id.startswith("classes."):
            entities.extend(_classes(manifest, document, spells, spell_ids))
        elif document_id == "character-origins.species":
            entities.extend(_species(manifest, document))
        elif document_id == "character-origins.backgrounds":
            entities.extend(_backgrounds(manifest, document, feat_names))
        elif document_id == "equipment.adventuring-gear":
            entities.extend(_gear(manifest, document))
        elif document_id == "equipment.tools":
            entities.extend(_tools(manifest, document))
        elif document_id == "equipment.mounts-and-vehicles":
            entities.extend(_mounts_and_vehicles(manifest, document))
        elif document_id == "equipment.expenses-and-services":
            entities.extend(_services(manifest, document))
        elif document_id.startswith("glossary.") and document_id != "glossary.conventions":
            entities.extend(_glossary(manifest, document))
    return entities
