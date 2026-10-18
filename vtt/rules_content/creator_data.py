"""Structured, machine-readable creator data derived from the published Regelwerk package.

Everything is computed from the package documents and the generated compendium. Where the source only
states a rule in prose, a small curated entry names the rule block and quotes the sentence verbatim;
the build fails if a quote is not found, so the data cannot drift away from the published text.
"""

from __future__ import annotations

import re
import unicodedata

from .compendium import _slug

SCHEMA_VERSION = "regelwerk.creator-data.v1"

ABILITIES = (
    ("str", "Stärke", "Stä."),
    ("dex", "Geschicklichkeit", "Ges."),
    ("con", "Konstitution", "Kon."),
    ("int", "Intelligenz", "Int."),
    ("wis", "Weisheit", "Wei."),
    ("cha", "Charisma", "Cha."),
)
_ABILITY_BY_NAME = {name: key for key, name, _abbr in ABILITIES}
_COIN_CP = {"KM": 1, "SM": 10, "EM": 50, "GM": 100, "PM": 1000}
_NUMBER_WORDS = {
    "ein": 1, "eine": 1, "einen": 1, "einem": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6,
    "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12,
}
_MINUS = "−"
_SPELL_ALIASES = {"leicht": "licht", "flug": "fliegen"}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.replace("ß", "ss")).strip()


def _int(value: str) -> int:
    return int(value.replace(".", "").replace(_MINUS, "-").replace("+", "").strip())


def _num(value) -> int:
    if value is None or value in {"–", ""}:
        return 0
    return int(value)


class Source:
    """Rule-block index with verbatim-quote verification."""

    def __init__(self, documents: list[dict], errors: list[str] | None = None):
        self.blocks: dict[str, dict] = {}
        self.documents = {document["documentId"]: document for document in documents}
        self.errors = errors
        for document in documents:
            for block in document["blocks"]:
                self.blocks[block["ruleId"]] = block

    def _fail(self, message: str):
        if self.errors is None:
            raise ValueError(message)
        self.errors.append(message)

    def block(self, rule_id: str) -> dict:
        if rule_id not in self.blocks:
            self._fail(f"unknown rule block {rule_id!r}")
            return {"type": "paragraph", "text": "", "ruleId": rule_id}
        return self.blocks[rule_id]

    def text(self, rule_id: str) -> str:
        block = self.block(rule_id)
        kind = block["type"]
        if kind in {"paragraph", "heading", "rule-callout", "page-note", "original-note"}:
            return block["text"]
        if kind in {"unordered-list", "ordered-list"}:
            return "\n".join(block["items"])
        if kind == "definition-list":
            return "\n".join(f"{entry['term']}: {entry['definition']}" for entry in block["entries"])
        if kind == "table":
            return "\n".join(" | ".join(row) for row in block["rows"])
        raise ValueError(f"cannot quote block type {kind}")

    def ref(self, rule_id: str, quote: str) -> dict:
        if quote not in self.text(rule_id):
            self._fail(f"quote not found in {rule_id}: {quote!r}")
        return {"ruleId": rule_id, "quote": quote}

    def table(self, rule_id: str) -> dict:
        block = self.block(rule_id)
        if block["type"] != "table":
            self._fail(f"{rule_id} is not a table")
            return {"columns": [], "rows": [], "ruleId": rule_id}
        return block


def _ability_id(name: str) -> str:
    key = _ABILITY_BY_NAME.get(name.strip())
    if not key:
        raise ValueError(f"unknown ability {name!r}")
    return key


def _ability_list(text: str) -> tuple[str, list[str]]:
    if " oder " in text:
        return "any", [_ability_id(part) for part in text.split(" oder ")]
    if " und " in text:
        return "all", [_ability_id(part) for part in text.split(" und ")]
    return "all", [_ability_id(text)]


def _cost_cp(text: str | None) -> int | None:
    match = re.fullmatch(r"([\d.]+) (KM|SM|EM|GM|PM)", (text or "").strip())
    if not match:
        return None
    return int(match.group(1).replace(".", "")) * _COIN_CP[match.group(2)]


def _weight_kg(text: str | None) -> float | None:
    match = re.fullmatch(r"([\d,.]+) (kg|g)(?: \(voll\))?", (text or "").strip())
    if not match:
        return None
    value = float(match.group(1).replace(".", "").replace(",", "."))
    return round(value / 1000, 4) if match.group(2) == "g" else value


class Spells:
    def __init__(self, entities: list[dict]):
        self.by_fold = {_fold(e["name"]): e["id"] for e in entities if e["type"] == "spell"}

    def get(self, name: str) -> str:
        key = _fold(name)
        key = _SPELL_ALIASES.get(key, key)
        if key not in self.by_fold:
            raise ValueError(f"unknown spell {name!r}")
        return self.by_fold[key]


# --------------------------------------------------------------------------- core rule tables

def _core(src: Source) -> dict:
    prefix = "character-creation.abilities-alignment-and-details."
    modifier_table = src.table(prefix + "scores-and-modifiers-table")
    printed: dict[int, int] = {}
    for row in modifier_table["rows"]:
        for score_cell, mod_cell in ((row[0], row[1]), (row[2], row[3])):
            low, _, high = score_cell.replace("–", "-").partition("-")
            for score in range(int(low), int(high or low) + 1):
                printed[score] = _int(mod_cell)
    for score, modifier in printed.items():
        if modifier != (score - 10) // 2:
            raise ValueError(f"printed modifier {modifier} for score {score} contradicts floor((score-10)/2)")
    if modifier_table["rows"] and sorted(printed) != list(range(min(printed), max(printed) + 1)):
        raise ValueError("modifier table has gaps")

    skill_table = src.table("core.proficiency.skill-list-table")
    skills = [{"id": _slug(row[0]), "name": row[0], "ability": _ability_id(row[1])} for row in skill_table["rows"]]
    if len(skills) != 18:
        raise ValueError("expected 18 skills")

    advancement = src.table("character-creation.advancement-and-multiclassing.character-advancement-table")
    levels = [
        {"level": int(row[0]), "xp": _int(row[1]), "proficiencyBonus": _int(row[2])} for row in advancement["rows"]
    ]
    if [row["level"] for row in levels] != list(range(1, 21)):
        raise ValueError("advancement table must cover levels 1-20")

    methods_id = prefix + "generating-scores-methods"
    methods = {entry["term"]: entry["definition"] for entry in src.block(methods_id)["entries"]}
    array = [int(n) for n in re.findall(r"\d+", methods["Standardsatz"].split(":", 1)[1])]
    if array != [15, 14, 13, 12, 10, 8]:
        raise ValueError(f"unexpected standard array {array}")
    cost_table = src.table(prefix + "point-cost-table")
    costs = {}
    for row in cost_table["rows"]:
        costs[int(row[0])] = int(row[1])
        costs[int(row[2])] = int(row[3])
    if sorted(costs) != list(range(8, 16)):
        raise ValueError("point-cost table must cover 8-15")
    budget = int(re.search(r"Du hast (\d+) Punkte", methods["Punktkosten"]).group(1))

    standard_set = src.table(prefix + "standard-set-by-class-table")
    if standard_set["columns"] != ["Klasse"] + [abbr for _k, _n, abbr in ABILITIES]:
        raise ValueError(f"unexpected standard-set columns {standard_set['columns']}")

    return {
        "abilities": [{"id": key, "name": name, "abbreviation": abbr} for key, name, abbr in ABILITIES],
        "abilityModifier": {
            "formula": "floor((score - 10) / 2)",
            "verifiedAgainst": prefix + "scores-and-modifiers-table",
        },
        "skills": skills,
        "levels": levels,
        "maxLevel": 20,
        "abilityScoreMethods": {
            "standardArray": {"values": array, "source": src.ref(methods_id, "15, 14, 13, 12, 10, 8")},
            "pointBuy": {
                "budget": budget,
                "minScore": 8,
                "maxScore": 15,
                "costs": {str(score): costs[score] for score in sorted(costs)},
                "source": src.ref(methods_id, "27 Punkte"),
            },
            "roll": {"dice": "4W6", "dropLowest": 1, "count": 6, "source": src.ref(methods_id, "4W6")},
            "backgroundBonus": {
                "options": [[2, 1], [1, 1, 1]],
                "maxScore": 20,
                "source": src.ref(
                    prefix + "adjusting-scores-description",
                    "Erhöhe einen dieser Werte um 2 Punkte und einen anderen um 1 Punkt, oder alle drei um je 1 Punkt",
                ),
            },
        },
        "formulas": {
            "passivePerception": src.ref(prefix + "passive-perception-formula", "10 + Weisheitswurf-Modifikator (Wahrnehmung)"),
            "armorClassUnarmored": src.ref(prefix + "armor-class-entry", "10 plus deinem Geschicklichkeitsmodifikator"),
            "spellSaveDc": src.ref(prefix + "spellcasting-formulas", "Zauberrettungswurf-SG = 8 + Zauberwirken-Attributsmodifikator + Übungsbonus"),
            "spellAttack": src.ref(prefix + "spellcasting-formulas", "Zauberangriffsbonus = Zauberwirken-Attributsmodifikator + Übungsbonus"),
            "meleeAttack": src.ref(prefix + "attack-bonus-formulas", "Nahkampfangriffsbonus = Stärkemodifikator + Übungsbonus"),
            "rangedAttack": src.ref(prefix + "attack-bonus-formulas", "Fernkampfangriffsbonus = Geschicklichkeitsmodifikator + Übungsbonus"),
        },
        "_standardSetRows": standard_set["rows"],
    }


def _hit_points(src: Source, class_dice: dict[str, int]) -> dict:
    level1 = src.table("character-creation.abilities-alignment-and-details.hit-points-at-level-1-table")
    fixed = src.table("character-creation.advancement-and-multiclassing.fixed-hit-points-table")
    notes = []
    covered: set[str] = set()
    fixed_by_class: dict[str, int] = {}
    for row in fixed["rows"]:
        value = int(re.match(r"(\d+) \+ KON-Modifikator", row[1]).group(1))
        for name in re.split(r", | oder ", row[0]):
            fixed_by_class[name] = value
    for row in level1["rows"]:
        names = re.split(r", | oder ", row[0])
        match = re.match(r"(\d+) \+ (KON|GES)-Modifikator", row[1])
        base, printed_ability = int(match.group(1)), match.group(2)
        for name in names:
            covered.add(name)
            if class_dice[name] != base:
                raise ValueError(f"level-1 HP table disagrees with hit die for {name}")
            if fixed_by_class[name] != base // 2 + 1:
                raise ValueError(f"fixed HP table disagrees with hit die for {name}")
        if printed_ability != "KON":
            notes.append(
                {
                    "kind": "source-defect",
                    "classes": names,
                    "printedText": src.ref(level1["ruleId"], row[1]),
                    "resolution": (
                        "Das Trefferpunktemaximum der 1. Stufe nutzt für alle Klassen den Konstitutionsmodifikator "
                        "(siehe Tabelle „Feste Trefferpunkte“ und alle übrigen Klassenzeilen); die gedruckte Angabe "
                        "„GES“ ist ein Quellfehler und wird nicht übernommen."
                    ),
                    "evidence": src.ref(fixed["ruleId"], "6 + KON-Modifikator"),
                }
            )
    if covered != set(class_dice):
        raise ValueError("level-1 HP table does not cover all classes")
    return {
        "level1": {"formula": "hitDie + conModifier", "sourceNotes": notes, "source": level1["ruleId"]},
        "perLevel": {
            "rolled": {"formula": "1d(hitDie) + conModifier", "minimum": 1},
            "fixed": {
                "byClassName": dict(sorted(fixed_by_class.items())),
                "formula": "floor(hitDie / 2) + 1 + conModifier",
            },
            "source": fixed["ruleId"],
        },
    }


def _multiclass(src: Source) -> dict:
    prefix = "character-creation.advancement-and-multiclassing."
    table = src.table(prefix + "multiclass-spell-slots-table")
    if table["columns"] != ["Stufe", *map(str, range(1, 10))]:
        raise ValueError("unexpected multiclass slot table columns")
    slots = {row[0]: [_num(cell) for cell in row[1:]] for row in table["rows"]}
    if sorted(map(int, slots)) != list(range(1, 21)):
        raise ValueError("multiclass slot table must cover levels 1-20")
    return {
        "prerequisite": {
            "minimumScore": 13,
            "rule": "primaryAbilitiesOfNewAndAllCurrentClasses",
            "source": src.ref(prefix + "prerequisites-description", "von mindestens 13"),
        },
        "experience": src.ref(prefix + "multiclass-experience-points-description", "gesamten Charakterstufe"),
        "hitPoints": src.ref(prefix + "multiclass-hit-points-gain", "nur dann, wenn deine gesamte Charakterstufe 1 ist"),
        "hitDice": src.ref(prefix + "multiclass-hit-dice-combining", "notiere sie separat"),
        "proficiencyBonus": src.ref(prefix + "multiclass-proficiency-bonus-description", "gesamten Charakterstufe"),
        "armorClass": src.ref(prefix + "multiclass-armor-class-description", "nur jeweils eine nutzen"),
        "extraAttack": {
            "stacks": False,
            "maxAttacks": 2,
            "source": src.ref(prefix + "multiclass-extra-attack-no-stacking", "addieren sich die Merkmale nicht"),
        },
        "casterLevel": {
            "full": ["bard", "cleric", "druid", "sorcerer", "wizard"],
            "half": ["paladin", "ranger"],
            "halfRounding": "up",
            "separate": ["warlock"],
            "fullSource": src.ref(prefix + "multiclass-spell-slots-addends", "All deine Stufen in den Klassen Barde, Druide, Kleriker, Magier und Zauberer"),
            "halfSource": src.ref(prefix + "multiclass-spell-slots-addends", "die Hälfte deiner Stufen (aufgerundet) in den Klassen Paladin und Waldläufer"),
        },
        "spellSlotsByCasterLevel": {level: slots[level] for level in sorted(slots, key=int)},
        "preparedSpells": src.ref(prefix + "multiclass-prepared-spells", "für jede Klasse einzeln"),
        "cantripScaling": src.ref(prefix + "multiclass-cantrips", "gesamten Charakterstufe"),
        "pactMagic": src.ref(prefix + "multiclass-pact-magic", "auch zum Wirken von Zaubern verwenden"),
    }


def _starting_levels(src: Source) -> list[dict]:
    table = src.table("character-creation.advancement-and-multiclassing.starting-equipment-by-level-table")
    result = []
    for row in table["rows"]:
        low, _, high = row[0].replace("–", "-").partition("-")
        match = re.match(r"(?:([\d.]+) GM plus (\d+)W(\d+) × ([\d.]+) GM plus )?normale Anfangsausrüstung", row[1], re.I)
        if not match:
            raise ValueError(f"unparsed starting-equipment row {row}")
        result.append(
            {
                "fromLevel": int(low),
                "toLevel": int(high or low),
                "baseGold": _int(match.group(1)) if match.group(1) else 0,
                "rolledGold": (
                    {"dice": int(match.group(2)), "sides": int(match.group(3)), "multiplier": _int(match.group(4))}
                    if match.group(2) else None
                ),
                "standardEquipment": True,
                "magicItems": row[2],
            }
        )
    return result


# --------------------------------------------------------------------------- equipment

_ITEM_ALIASES = {
    "flaschen ol": "Öl", "flasche ol": "Öl",
    "bogen papier": "Papier", "bogen pergament": "Pergament", "pergament": "Pergament",
    "tagesrationen": "Rationen", "tagesration": "Rationen",
    "reisekleidung": "Kleidung, Reise", "feine kleidung": "Kleidung, fein",
    "karten oder schriftrollenbehalter": "Behälter (Karte oder Schriftrolle)",
    "kostume": "Kostüm", "fackeln": "Fackel", "kerzen": "Kerze", "pfeile": "Pfeile", "bolzen": "Bolzen",
}
_CHOICE_ITEMS = {
    "musikinstrument deiner wahl": "musical-instrument",
    "musikinstrument": "musical-instrument",
    "spielset": "gaming-set",
    "spielset wie oben": "gaming-set",
    "arkaner fokus": "arcane-focus",
    "druidischer fokus": "druidic-focus",
    "heiliges symbol": "holy-symbol",
    "handwerkszeug oder musikinstrument im rahmen von ubung im umgang mit werkzeug oben ausgewahlt": "tool-choice",
}


class _Items:
    def __init__(self, entities: list[dict]):
        self.by_fold: dict[str, dict] = {}
        for entity in entities:
            if entity["type"] in {"gear", "weapon", "armor", "tool", "mount", "vehicle"}:
                self.by_fold.setdefault(_fold(entity["name"]), entity)

    def find(self, name: str) -> dict | None:
        key = _fold(name)
        if key in self.by_fold:
            return self.by_fold[key]
        alias = _ITEM_ALIASES.get(key)
        if alias and _fold(alias) in self.by_fold:
            return self.by_fold[_fold(alias)]
        return None


def _split_items(text: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if depth == 0 and char == ",":
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    out: list[str] = []
    for part in parts:
        out.extend(piece.strip() for piece in re.split(r" und (?![^()]*\))", part) if piece.strip())
    return out


_QUANTITY = re.compile(r"^(\d+|" + "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True)) + r") (.+)$", re.I)


def _parse_entry(text: str, items: _Items) -> dict:
    coin = re.fullmatch(r"([\d.]+) (KM|SM|EM|GM|PM)", text)
    if coin:
        return {"kind": "coins", "amount": _int(coin.group(1)), "coin": coin.group(2)}
    if _fold(text) in _CHOICE_ITEMS:
        return {"kind": "choice", "category": _CHOICE_ITEMS[_fold(text)], "quantity": 1}
    quantity, rest = 1, text
    match = _QUANTITY.match(text)
    if match:
        quantity = int(match.group(1)) if match.group(1).isdigit() else _NUMBER_WORDS[match.group(1).casefold()]
        rest = match.group(2)
    if _fold(rest) in _CHOICE_ITEMS:
        return {"kind": "choice", "category": _CHOICE_ITEMS[_fold(rest)], "quantity": quantity}
    if _fold(rest) == "zauberbuch":
        return {"kind": "special", "special": "spellbook", "quantity": quantity}
    entity = items.find(rest)
    qualifier = None
    if entity is None:
        paren = re.fullmatch(r"(.+?) \((.+)\)", rest)
        if paren:
            base, qualifier = paren.group(1), paren.group(2)
            sheets = re.fullmatch(r"(\d+) Blätter", qualifier)
            if sheets and _fold(base) == "pergament":
                found = items.find("Pergament")
                if found:
                    return {"kind": "item", "itemId": found["id"], "quantity": int(sheets.group(1)), "unit": "sheet"}
            if _fold(base) in _CHOICE_ITEMS:
                return {"kind": "choice", "category": _CHOICE_ITEMS[_fold(base)], "quantity": quantity, "variant": qualifier}
            entity = items.find(base)
    if entity is None:
        for candidate in (rest[:-1], rest[:-2], rest.rstrip("n"), rest.rstrip("e")):
            entity = items.find(candidate)
            if entity:
                break
    if entity is None:
        return {"kind": "unresolved", "text": text}
    result = {"kind": "item", "itemId": entity["id"], "quantity": quantity}
    if qualifier:
        result["variant"] = qualifier
    return result


def _entries(text: str, items: _Items) -> list[dict]:
    return [_parse_entry(part, items) for part in _split_items(text)]


def _packs(src: Source, items: _Items) -> dict:
    packs = {}
    for rule_id, block in src.blocks.items():
        if not rule_id.startswith("equipment.adventuring-gear.item-") or block["type"] != "paragraph":
            continue
        match = re.match(r"^Eine (?P<name>[\wäöüÄÖÜß-]+) enthält folgende Gegenstände: (?P<list>.+)\.$", block["text"])
        if not match:
            continue
        entity = items.find(match["name"])
        if entity is None:
            raise ValueError(f"pack without gear entry: {match['name']}")
        packs[entity["id"]] = {
            "name": entity["name"],
            "contents": _entries(match["list"], items),
            "source": src.ref(rule_id, "enthält folgende Gegenstände"),
        }
    return dict(sorted(packs.items()))


def _armor(entity: dict) -> dict:
    formula = entity["armorClass"]
    shield = re.fullmatch(r"\+(\d+)", formula)
    if shield:
        entry = {"base": int(shield.group(1)), "dex": "none", "dexCap": None, "shield": True}
    else:
        match = re.fullmatch(r"(\d+)(?: \+ GES-Modifikator(?: \(max\. (\d+)\))?)?", formula)
        if not match:
            raise ValueError(f"unparsed armor class {formula!r}")
        if " + GES" not in formula:
            dex, cap = "none", 0
        elif match.group(2):
            dex, cap = "capped", int(match.group(2))
        else:
            dex, cap = "full", None
        entry = {"base": int(match.group(1)), "dex": dex, "dexCap": cap, "shield": False}
    strength = re.fullmatch(r"Stä\. (\d+)", entity["strength"])
    category = {"Leicht": "light", "Mittelschwer": "medium", "Schwer": "heavy", "Schild": "shield"}[entity["armorCategory"]]
    return {
        "id": entity["id"], "name": entity["name"], "category": category, **entry,
        "strengthRequirement": int(strength.group(1)) if strength else None,
        "stealthDisadvantage": entity["stealth"] == "Nachteil",
        "costCp": _cost_cp(entity.get("cost")), "weightKg": _weight_kg(entity.get("weight")),
    }


_DAMAGE_TYPES = {"Hieb": "slashing", "Stich": "piercing", "Wucht": "bludgeoning"}


def _weapon(entity: dict) -> dict:
    damage = re.fullmatch(r"(?:(\d+)W(\d+)|(\d+)) (Hieb|Stich|Wucht)", entity["damage"])
    if not damage:
        raise ValueError(f"unparsed damage {entity['damage']!r}")
    if damage.group(1):
        dmg = {"dice": int(damage.group(1)), "sides": int(damage.group(2)), "flat": 0}
    else:
        dmg = {"dice": 0, "sides": 0, "flat": int(damage.group(3))}
    dmg["type"] = _DAMAGE_TYPES[damage.group(4)]
    properties: list[dict] = []
    text = entity["properties"]
    if text != "–":
        for part in re.split(r",\s*(?![^()]*\))", text):
            prop = re.fullmatch(r"([^()]+?)(?: \((.+)\))?", part.strip())
            name, detail = prop.group(1).strip(), prop.group(2)
            item: dict = {"name": name}
            if detail:
                versatile = re.fullmatch(r"(\d+)W(\d+)", detail)
                reach = re.match(r"Reichweite ([\d,]+)/([\d,]+)", detail)
                if name == "Vielseitig" and versatile:
                    item["versatile"] = {"dice": int(versatile.group(1)), "sides": int(versatile.group(2))}
                elif reach:
                    item["range"] = {"normal": float(reach.group(1).replace(",", ".")), "long": float(reach.group(2).replace(",", "."))}
                    tail = detail[reach.end():].lstrip(",; ")
                    if tail:
                        item["detail"] = tail
                else:
                    item["detail"] = detail
            properties.append(item)
    return {
        "id": entity["id"], "name": entity["name"],
        "category": "simple" if entity["weaponClass"] == "Einfach" else "martial",
        "kind": "melee" if entity["weaponKind"] == "Nahkampf" else "ranged",
        "damage": dmg, "properties": properties, "mastery": entity["mastery"],
        "costCp": _cost_cp(entity.get("cost")), "weightKg": _weight_kg(entity.get("weight")),
    }


def _equipment(src: Source, entities: list[dict], items: _Items) -> dict:
    coin_table = src.table("equipment.coins-and-weapons.coin-values")
    coins = {}
    for row in coin_table["rows"]:
        abbr = re.search(r"\((\w+)\)", row[0]).group(1)
        numerator, _, denominator = row[1].partition("/")
        coins[abbr] = {"name": row[0].split(" (")[0], "valueInCp": int(round(float(numerator) / float(denominator or 1) * 100))}
    if {abbr: data["valueInCp"] for abbr, data in coins.items()} != _COIN_CP:
        raise ValueError("coin values changed")
    general = [
        {
            "id": e["id"], "name": e["name"], "kind": e["type"], "category": e.get("category"),
            "costCp": _cost_cp(e.get("cost")), "weightKg": _weight_kg(e.get("weight")),
        }
        for e in entities if e["type"] in {"gear", "tool"}
    ]
    return {
        "coins": coins,
        "armor": [_armor(e) for e in entities if e["type"] == "armor"],
        "weapons": [_weapon(e) for e in entities if e["type"] == "weapon"],
        "items": sorted(general, key=lambda item: item["id"]),
        "packs": _packs(src, items),
        "armorClass": {
            "unarmored": "10 + dexModifier",
            "source": src.ref("equipment.armor.armor-details", "Basis-RK"),
        },
    }


# --------------------------------------------------------------------------- classes

def _armor_proficiency(text: str) -> list[str]:
    folded = text.casefold()
    if folded == "keine":
        return []
    found = []
    if "leicht" in folded:
        found.append("light")
    if "mittelschwer" in folded:
        found.append("medium")
    if "schwer" in folded.replace("mittelschwer", ""):
        found.append("heavy")
    if "schild" in folded:
        found.append("shield")
    if not found:
        raise ValueError(f"unparsed armor training {text!r}")
    return found


def _weapon_proficiency(text: str) -> list[dict]:
    folded = text.casefold()
    table = {
        "einfache waffen": [{"category": "simple"}],
        "einfache waffen und kriegswaffen": [{"category": "simple"}, {"category": "martial"}],
        "einfache waffen und kriegswaffen mit der eigenschaft leicht": [{"category": "simple"}, {"category": "martial", "requiresProperty": ["Leicht"]}],
        "einfache waffen und kriegswaffen mit der eigenschaft finesse oder leicht": [{"category": "simple"}, {"category": "martial", "requiresProperty": ["Finesse", "Leicht"]}],
    }
    if folded not in table:
        raise ValueError(f"unparsed weapon training {text!r}")
    return table[folded]


def _tool_training(text: str | None, items: _Items) -> dict | None:
    if not text:
        return None
    if text.startswith("Drei Musikinstrumente"):
        return {"choose": {"count": 3, "category": "musical-instrument"}}
    if text.startswith("Wähle eine Art von Handwerkszeug oder ein Musikinstrument"):
        return {"choose": {"count": 1, "category": ["artisan-tools", "musical-instrument"]}}
    entity = items.find(text)
    if entity is None:
        raise ValueError(f"unmapped tool training {text!r}")
    return {"fixed": [entity["id"]]}


_MULTICLASS_GRANTS = {
    "barbarian": ({"weapons": [{"category": "martial"}], "armor": ["shield"]}, "Übung im Umgang mit Kriegswaffen, Vertrautheit mit Schilden"),
    "bard": ({"skillChoices": {"count": 1, "from": "any"}, "toolChoices": [{"count": 1, "category": "musical-instrument"}], "armor": ["light"]}, "Übung in einer Fertigkeit deiner Wahl, Übung im Umgang mit einem Musikinstrument deiner Wahl, Vertrautheit mit leichter Rüstung"),
    "cleric": ({"armor": ["light", "medium", "shield"]}, "Vertrautheit mit leichter und mittelschwerer Rüstung sowie mit Schilden"),
    "druid": ({"armor": ["light", "shield"]}, "Vertrautheit mit leichter Rüstung sowie mit Schilden"),
    "fighter": ({"weapons": [{"category": "martial"}], "armor": ["light", "medium", "shield"]}, "Übung im Umgang mit Kriegswaffen, Vertrautheit mit leichter und mittelschwerer Rüstung sowie mit Schilden"),
    "monk": ({}, "Du erhältst das Merkmal Trefferpunktewürfel aus der Tabelle „Hauptmerkmale des Mönchs“."),
    "paladin": ({"weapons": [{"category": "martial"}], "armor": ["light", "medium", "shield"]}, "Übung im Umgang mit Kriegswaffen, Vertrautheit mit leichter und mittelschwerer Rüstung sowie mit Schilden"),
    "ranger": ({"weapons": [{"category": "martial"}], "skillChoices": {"count": 1, "from": "class"}, "armor": ["light", "medium", "shield"]}, "Übung im Umgang mit Kriegswaffen, Übung in einer Fertigkeit deiner Wahl von der Fertigkeitenliste des Waldläufers, Vertrautheit mit leichter und mittelschwerer Rüstung sowie mit Schilden"),
    "rogue": ({"skillChoices": {"count": 1, "from": "class"}, "tools": ["Diebeswerkzeug"], "armor": ["light"]}, "Übung in einer Fertigkeit deiner Wahl von der Fertigkeitenliste des Schurken, Übung im Umgang mit Diebeswerkzeug, Vertrautheit mit leichter Rüstung"),
    "sorcerer": ({}, "Du erhältst die Trefferpunktewürfel, die in der Tabelle „Hauptmerkmale des Zauberers“ aufgeführt sind."),
    "warlock": ({"armor": ["light"]}, "Vertrautheit mit leichter Rüstung"),
    "wizard": ({}, "Du erhältst die Trefferpunktewürfel, die in der Tabelle „Hauptmerkmale des Magiers“ aufgeführt sind."),
}

# Choices the source states in prose: (id, kind, level, rule suffix, quote, extras)
_FEATURE_CHOICES = {
    "barbarian": [
        ("weapon-mastery", "weapon-mastery", 1, "level1-weapon-mastery-description", "zweier Arten von einfachen Nahkampfwaffen oder Nahkampf-Kriegswaffen", {"countColumn": "Waffenbeherrschung", "weapons": "simple-or-martial-melee"}),
    ],
    "bard": [
        ("expertise-1", "expertise", 2, "level2-expertise-description", "Expertise (siehe „Regelglossar“) in zwei Fertigkeiten deiner Wahl, in denen du geübt bist", {"count": 2}),
        ("expertise-2", "expertise", 9, "level2-expertise-growth", "Auf der 9. Stufe erhältst du Expertise in zwei weiteren Fertigkeiten", {"count": 2}),
    ],
    "cleric": [
        ("divine-order", "option", 1, "level1-divine-order-introduction", "einer der folgenden heiligen Rollen verschrieben", {"options": {"protector": "level1-divine-order-protector", "thaumaturge": "level1-divine-order-thaumaturge"}}),
    ],
    "druid": [
        ("primal-order", "option", 1, "level1-primal-order-introduction", "einer der folgenden heiligen Rollen verschrieben", {"options": {"magician": "level1-primal-order-magician", "warden": "level1-primal-order-warden"}}),
    ],
    "fighter": [
        ("fighting-style", "feat-category", 1, "level1-fighting-style-description", "ein Kampfstil-Talent deiner Wahl", {"category": "Kampfstil-Talent"}),
        ("weapon-mastery", "weapon-mastery", 1, "level1-weapon-mastery-description", "dreier Arten von einfachen Waffen oder Kriegswaffen", {"countColumn": "Waffenbeherrschung", "weapons": "simple-or-martial"}),
    ],
    "paladin": [
        ("weapon-mastery", "weapon-mastery", 1, "level1-weapon-mastery-description", "zweier Waffenarten deiner Wahl", {"count": 2, "weapons": "proficient"}),
        ("fighting-style", "feat-category", 2, "level2-fighting-style-description", "ein Kampfstil-Talent deiner Wahl", {"category": "Kampfstil-Talent", "alternative": "level2-fighting-style-blessed-warrior"}),
    ],
    "ranger": [
        ("weapon-mastery", "weapon-mastery", 1, "level1-weapon-mastery-description", "zweier Waffenarten deiner Wahl", {"count": 2, "weapons": "proficient"}),
        ("deft-explorer-expertise", "expertise", 2, "level2-deft-explorer-expertise", "Wähle eine deiner Fertigkeiten aus, in denen du geübt bist, aber keine Expertise hast", {"count": 1}),
        ("deft-explorer-languages", "language", 2, "level2-deft-explorer-languages", "zwei Sprachen deiner Wahl", {"count": 2}),
        ("fighting-style", "feat-category", 2, "level2-fighting-style-description", "ein Kampfstil-Talent deiner Wahl", {"category": "Kampfstil-Talent", "alternative": "level2-fighting-style-druidic-warrior"}),
        ("expertise", "expertise", 9, "level9-expertise-description", "Wähle zwei deiner Fertigkeiten aus, in denen du geübt bist, aber keine Expertise hast", {"count": 2}),
    ],
    "rogue": [
        ("weapon-mastery", "weapon-mastery", 1, "level1-weapon-mastery-description", "zweier Waffenarten deiner Wahl", {"count": 2, "weapons": "proficient"}),
        ("expertise-1", "expertise", 1, "level1-expertise-description", "Expertise in zwei Fertigkeiten deiner Wahl, in denen du geübt bist", {"count": 2}),
        ("expertise-2", "expertise", 6, "level1-expertise-level6", "Auf der 6. Schurkenstufe erhältst du Expertise in zwei weiteren Fertigkeiten", {"count": 2}),
        ("thieves-cant-language", "language", 1, "level1-thieves-cant-description", "eine andere Sprache deiner Wahl", {"count": 1}),
    ],
    "sorcerer": [
        ("metamagic-1", "class-option", 2, "level2-metamagic-description", "zwei Metamagie-Optionen deiner Wahl", {"optionKind": "Metamagie", "count": 2}),
        ("metamagic-2", "class-option", 10, "level2-metamagic-swap", "Auf der 10. und 17. Zaubererstufe erhältst du jeweils zwei wei", {"optionKind": "Metamagie", "count": 2}),
        ("metamagic-3", "class-option", 17, "level2-metamagic-swap", "Auf der 10. und 17. Zaubererstufe erhältst du jeweils zwei wei", {"optionKind": "Metamagie", "count": 2}),
    ],
    "warlock": [
        ("eldritch-invocations", "class-option", 1, "level1-eldritch-invocations-growth", "„Bekannte Anrufungen“", {"optionKind": "Schauerliche Anrufung", "countColumn": "Bekannte Anrufungen"}),
    ],
    "wizard": [
        ("scholar", "expertise", 2, "level2-scholar-description", "Wähle eine der folgenden Fertigkeiten aus, sofern du Übung darin hast", {"count": 1, "restrictToSkills": ["Arkane Kunde", "Geschichte", "Heilkunde", "Nachforschungen", "Naturkunde", "Religion"]}),
    ],
}

# Limited-use resources: (id, name, level, rule suffix, quote, recover, extras)
_ONE_SHORT_ALL_LONG = {"short": "one", "long": "all"}
_RESOURCES = {
    "barbarian": [
        ("rage", "Kampfrausch", 1, "level1-rage-uses", "Nach einer kurzen Rast erhältst du eine verbrauchte Anwendung zurück.", _ONE_SHORT_ALL_LONG, {"usesColumn": "Kampfrausch-Anzahl"}),
    ],
    "bard": [
        ("bardic-inspiration", "Bardische Inspiration", 1, "level1-bardic-inspiration-uses", "entspricht deinem Charismamodifikator (mindestens einmal)", {"long": "all"}, {"uses": {"formula": "max(1, chaModifier)"}}),
        ("bardic-inspiration-font", "Bardische Inspiration (Quelle der Inspiration)", 5, "level5-font-of-inspiration-rest", "nach einer kurzen oder langen Rast zurück", {"short": "all", "long": "all"}, {"replaces": "bardic-inspiration"}),
    ],
    "cleric": [
        ("channel-divinity", "Göttliche Macht fokussieren", 2, "level2-channel-divinity-uses", "Wenn du eine kurze Rast beendest, erhältst du eine verbrauchte Anwendung zurück.", _ONE_SHORT_ALL_LONG, {"usesColumn": "Göttliche Macht fokussieren"}),
    ],
    "druid": [
        ("wild-shape", "Tiergestalt", 2, "level2-wild-shape-uses", "Nach einer kurzen Rast erhältst du eine verbrauchte Anwendung zurück.", _ONE_SHORT_ALL_LONG, {"usesColumn": "Tiergestalt"}),
    ],
    "fighter": [
        ("second-wind", "Durchschnaufen", 1, "level1-second-wind-uses", "Nach einer kurzen Rast erhältst du eine verbrauchte Anwendung zurück.", _ONE_SHORT_ALL_LONG, {"usesColumn": "Durchschnaufen"}),
        ("action-surge", "Tatendrang", 2, "level2-action-surge-rest", "Du kannst dieses Merkmal erst nach einer kurzen oder langen Rast erneut verwenden.", {"short": "all", "long": "all"}, {"uses": {"byLevel": {"2": 1, "17": 2}}}),
        ("indomitable", "Unbeugsam", 9, "level9-indomitable-growth", "ab der 13. Stufe zweimal vor einer langen Rast und ab der 17. Stufe dreimal vor einer langen Rast", {"long": "all"}, {"uses": {"byLevel": {"9": 1, "13": 2, "17": 3}}}),
    ],
    "monk": [
        ("focus-points", "Fokuspunkte", 2, "level2-monks-focus-regain", "Du erhältst verbrauchte Fokuspunkte nach einer kurzen oder langen Rast zurück.", {"short": "all", "long": "all"}, {"usesColumn": "Fokuspunkte"}),
    ],
    "paladin": [
        ("lay-on-hands", "Handauflegen", 1, "level1-lay-on-hands-description", "das Fünffache deiner Paladinstufe an Trefferpunkten", {"long": "all"}, {"uses": {"formula": "5 * paladinLevel", "kind": "pool"}}),
        ("channel-divinity", "Göttliche Macht fokussieren", 3, "level3-channel-divinity-uses", "Wenn du eine kurze Rast beendest, erhältst du eine verbrauchte Anwendung zurück.", _ONE_SHORT_ALL_LONG, {"usesColumn": "Göttliche Macht fokussieren"}),
    ],
    "ranger": [
        ("favored-enemy", "Erzfeind", 1, "level1-favored-enemy-description", "Du erhältst alle verbrauchten Anwendungen dieser Fähigkeit nach einer langen Rast zurück.", {"long": "all"}, {"usesColumn": "Erzfeind"}),
    ],
    "sorcerer": [
        ("innate-sorcery", "Intuitive Zauberei", 1, "level1-innate-sorcery-uses", "erhältst alle verbrauchten Anwendungen nach einer langen Rast zurück", {"long": "all"}, {"uses": {"fixed": 2}}),
        ("sorcery-points", "Zaubereipunkte", 2, "level2-font-of-magic-points", "Du erhältst alle verbrauchten Zaubereipunkte nach einer langen Rast zurück.", {"long": "all"}, {"usesColumn": "Zaubereipunkte"}),
    ],
    "warlock": [
        ("pact-magic-slots", "Paktmagie-Zauberplätze", 1, "level1-pact-magic-slots", "Du erhältst alle verbrauchten Paktmagie-Zauberplätze nach einer kurzen oder langen Rast zurück.", {"short": "all", "long": "all"}, {"kind": "spell-slots"}),
    ],
    "wizard": [
        ("arcane-recovery", "Arkane Erholung", 1, "level1-arcane-recovery-rest", "Du kannst dieses Merkmal erst nach einer langen Rast erneut verwenden.", {"long": "all"}, {"uses": {"fixed": 1}}),
    ],
}


def _rule(src: Source, class_key: str, suffix: str) -> str:
    rule_id = f"classes.{class_key}.{suffix}"
    src.block(rule_id)
    return rule_id


def _column(progression: list[dict], column: str, from_level: int = 1) -> dict:
    return {str(row["level"]): _num(row["extras"].get(column)) for row in progression if row["level"] >= from_level}


def _spellcasting(src: Source, class_key: str, progression: list[dict]) -> dict | None:
    base = f"classes.{class_key}."
    pact = class_key == "warlock"
    prefix = base + ("level1-pact-magic-" if pact else "level1-spellcasting-")
    if prefix + "ability" not in src.blocks:
        return None
    ability_name = re.search(r"ist (\w+)\.$", src.text(prefix + "ability")).group(1)
    kind = "pact" if pact else ("half" if class_key in {"paladin", "ranger"} else "full")
    swap_text = src.text(prefix + "prepared-swap")
    cantrip_text = " ".join(src.text(prefix + suffix) for suffix in ("cantrips", "cantrips-swap") if prefix + suffix in src.blocks)
    levels = []
    for row in progression:
        extras = row["extras"]
        entry = {"level": row["level"], "cantrips": _num(extras.get("Zaubertricks")), "prepared": _num(extras.get("Vorbereitete Zauber"))}
        if pact:
            entry["slots"] = _num(extras.get("Grad der Zauberplätze"))
            entry["slotGrade"] = _num(extras.get("Zauberplätze"))
        else:
            entry["slots"] = [_num(extras.get(f"Grad {grade}")) for grade in range(1, 10 if kind == "full" else 6)]
        levels.append(entry)
    result = {
        "kind": kind,
        "ability": _ability_id(ability_name),
        "abilitySource": src.ref(prefix + "ability", f"ist {ability_name}"),
        "preparation": {
            "mode": "spellbook" if class_key == "wizard" else "prepared",
            "swapWhen": "long-rest" if "lange Rast" in swap_text else "level-up",
            "swapAmount": "any" if "beliebige" in swap_text else "one",
            "source": src.ref(prefix + "prepared-swap", "Deine vorbereiteten Zauber ändern"),
        },
        "cantripSwapWhen": ("long-rest" if "lange Rast" in cantrip_text else "level-up") if cantrip_text else None,
        "levels": levels,
        "ritualCasting": class_key in {"bard", "cleric", "druid", "wizard"},
        "focus": prefix + "focus" in src.blocks,
    }
    if pact:
        fifth = next(row for row in levels if row["level"] == 5)
        if (fifth["slots"], fifth["slotGrade"]) != (2, 3):
            raise ValueError("warlock pact slots do not match the printed example (level 5: two slots of grade 3)")
        result["sourceNotes"] = [{
            "kind": "source-defect",
            "printedText": src.ref(prefix + "slots", "zeigt, wie viele Zauberplätze dir"),
            "evidence": src.ref(prefix + "slots-example", "hast du zwei Zauberplätze des 3. Grades"),
            "resolution": "Die Spaltenköpfe „Grad der Zauberplätze“ und „Zauberplätze“ der Tabelle „Hexenmeistermerkmale“ sind vertauscht: Die Werte unter „Grad der Zauberplätze“ sind die Anzahl der Plätze, die Werte unter „Zauberplätze“ der Grad. Maßgeblich ist das gedruckte Beispiel (Stufe 5: zwei Plätze des 3. Grades).",
        }]
    if class_key == "wizard":
        result["spellbook"] = {
            "startingSpells": 6,
            "perLevel": 2,
            "startingSource": src.ref(prefix + "spellbook-starting", "sechs Magierzaubern des 1. Grades"),
            "growthSource": src.ref(prefix + "spellbook-growth", "zwei neue Magierzauber"),
        }
    return result


def _classes(src: Source, entities: list[dict], items: _Items) -> list[dict]:
    result = []
    features = {}
    for entity in entities:
        if entity["type"] == "class-feature" and not entity.get("subclass"):
            features.setdefault(entity["classKey"], {})[(entity["level"], entity["name"])] = entity["id"]
    for entity in sorted((e for e in entities if e["type"] == "class"), key=lambda e: e["name"].casefold()):
        key = entity["classKey"]
        progression = entity["progression"]
        mode, primary = _ability_list(entity["primaryAbility"])
        asi = [row["level"] for row in progression if "Attributswerterhöhung" in row["features"]]
        subclass = [row["level"] for row in progression if any(name.endswith("Unterklasse") for name in row["features"])]
        epic = [row["level"] for row in progression if "Epische Gabe" in row["features"]]
        if not (asi and subclass and epic):
            raise ValueError(f"{key}: progression lacks ASI/subclass/epic boon rows")
        skills = entity["skillChoices"]
        resources = []
        for rid, name, level, suffix, quote, recover, extras in _RESOURCES.get(key, []):
            spec = {"id": rid, "name": name, "level": level, "recover": recover, **extras}
            spec["source"] = src.ref(_rule(src, key, suffix), quote)
            if "usesColumn" in spec:
                column = spec["usesColumn"]
                if not any(column in row["extras"] for row in progression):
                    raise ValueError(f"{key}: resource {rid} references unknown column {column!r}")
                spec["usesByLevel"] = _column(progression, column, level)
            resources.append(spec)
        choices = []
        for cid, kind, level, suffix, quote, extras in _FEATURE_CHOICES.get(key, []):
            spec = {"id": cid, "kind": kind, "level": level, **extras}
            spec["source"] = src.ref(_rule(src, key, suffix), quote)
            if "options" in spec:
                spec["options"] = {option: _rule(src, key, rule) for option, rule in spec["options"].items()}
            if "alternative" in spec:
                spec["alternative"] = _rule(src, key, spec["alternative"])
            if "countColumn" in spec:
                column = spec["countColumn"]
                if not any(column in row["extras"] for row in progression):
                    raise ValueError(f"{key}: choice {cid} references unknown column {column!r}")
                spec["countByLevel"] = _column(progression, column)
            choices.append(spec)
        grants, grant_quote = _MULTICLASS_GRANTS[key]
        multiclass = dict(grants)
        multiclass["source"] = src.ref(f"classes.{key}.as-a-multiclass-character-list", grant_quote)
        result.append(
            {
                "id": entity["id"],
                "classKey": key,
                "name": entity["name"],
                "hitDie": entity["hitDie"],
                "primaryAbilities": {
                    "mode": mode, "abilities": primary,
                    "source": src.ref(f"classes.{key}.key-traits", "Hauptattribut: " + entity["primaryAbility"]),
                },
                "savingThrows": [_ability_id(name) for name in entity["savingThrows"]],
                "skillChoices": {"count": skills["count"], "options": [_slug(n) for n in skills.get("options") or []] or None},
                "weaponProficiencies": _weapon_proficiency(entity["weaponTraining"]),
                "armorProficiencies": _armor_proficiency(entity["armorTraining"]),
                "toolProficiencies": _tool_training(entity.get("toolTraining"), items),
                "startingEquipment": {k: _entries(v, items) for k, v in entity["startingEquipmentOptions"].items()},
                "asiLevels": asi,
                "subclassLevels": subclass,
                "epicBoonLevel": epic[0],
                "levels": [
                    {
                        "level": row["level"],
                        "proficiencyBonus": _int(row["proficiencyBonus"]),
                        "features": [{"name": name, "id": features.get(key, {}).get((row["level"], name))} for name in row["features"]],
                        "columns": {name: (int(value) if re.fullmatch(r"\d+", value) else value) for name, value in row["extras"].items()},
                    }
                    for row in progression
                ],
                "spellcasting": _spellcasting(src, key, progression),
                "resources": resources,
                "featureChoices": choices,
                "multiclassGrants": multiclass,
                "subclasses": entity["subclasses"],
            }
        )
    return result


# --------------------------------------------------------------------------- origins, feats, misc

def _species(src: Source, entities: list[dict], spells: Spells) -> list[dict]:
    prefix = "character-origins.species."
    result = []
    for entity in sorted((e for e in entities if e["type"] == "species"), key=lambda e: e["name"].casefold()):
        key = entity["id"].rsplit(".", 1)[-1]
        entry = {
            "id": entity["id"], "name": entity["name"], "sizes": list(entity["sizes"]),
            "speedMeters": entity["speedMeters"], "darkvisionMeters": entity.get("darkvision"),
            "creatureType": entity["creatureType"], "traits": entity["traits"], "choices": [], "grants": None,
        }
        if key == "dragonborn":
            table = src.table(prefix + "dragonborn-draconic-ancestry-table")
            options = []
            for row in table["rows"]:
                options.append({"id": _slug(row[0]), "name": row[0], "damageType": row[1]})
                options.append({"id": _slug(row[2]), "name": row[2], "damageType": row[3]})
            entry["choices"].append({
                "id": "draconic-ancestry", "kind": "option", "options": sorted(options, key=lambda o: o["name"]),
                "source": src.ref(prefix + "dragonborn-draconic-ancestry", "Wähle die Art des Drachen"),
            })
        elif key in {"elf", "tiefling"}:
            stem = "elf-elven-lineage" if key == "elf" else "tiefling-fiendish-legacy"
            table = src.table(prefix + stem + "-table")
            options = []
            for row in table["rows"]:
                cantrips = re.findall(r"kennst du den Zaubertrick ([^.]+?)\.", row[1])
                resist = re.search(r"gegen (\w+?) ?[sS]chaden resistent", row[1])
                options.append({
                    "id": _slug(row[0]), "name": row[0],
                    "cantrips": [spells.get(name) for name in cantrips],
                    "resistance": resist.group(1) if resist else None,
                    "spellsByLevel": {"3": spells.get(row[2]), "5": spells.get(row[3])},
                    "description": row[1],
                })
            entry["choices"].append({"id": "lineage", "kind": "option", "options": options, "source": src.ref(table["ruleId"], row[0])})
            quote = "Intelligenz, Weisheit oder Charisma" if key == "elf" else "Charisma, Intelligenz oder Weisheit"
            entry["choices"].append({
                "id": "spellcasting-ability", "kind": "ability", "options": ["int", "wis", "cha"],
                "source": src.ref(prefix + stem + "-ability", quote),
            })
            if key == "elf":
                entry["choices"].append({
                    "id": "keen-senses", "kind": "skill", "options": [_slug(n) for n in ("Motiv erkennen", "Überlebenskunst", "Wahrnehmung")],
                    "source": src.ref(prefix + "elf-keen-senses", "Motiv erkennen, Überlebenskunst oder Wahrnehmung"),
                })
            else:
                entry["grants"] = {
                    "cantrips": [spells.get("Thaumaturgie")],
                    "source": src.ref(prefix + "tiefling-otherworldly-presence", "Thaumaturgie"),
                }
        elif key == "gnome":
            entry["choices"].append({
                "id": "lineage", "kind": "option",
                "options": [
                    {"id": "rock-gnome", "name": "Felsengnom", "cantrips": [spells.get("Ausbessern"), spells.get("Taschenspielerei")], "alwaysPrepared": [], "source": src.ref(prefix + "gnome-rock-gnome", "Ausbessern und Taschenspielerei")},
                    {"id": "forest-gnome", "name": "Waldgnom", "cantrips": [spells.get("Einfache Illusion")], "alwaysPrepared": [spells.get("Mit Tieren sprechen")], "source": src.ref(prefix + "gnome-forest-gnome", "Einfache Illusion")},
                ],
                "source": src.ref(prefix + "gnome-gnomish-lineage", "Wähle eine der folgenden Optionen aus"),
            })
            entry["choices"].append({
                "id": "spellcasting-ability", "kind": "ability", "options": ["int", "wis", "cha"],
                "source": src.ref(prefix + "gnome-gnomish-lineage", "Charisma, Intelligenz oder Weisheit"),
            })
        elif key == "goliath":
            giants = [("frost", "Frostriese"), ("stone", "Steinriese"), ("fire", "Feuerriese"), ("hill", "Hügelriese"), ("storm", "Sturmriese"), ("cloud", "Wolkenriese")]
            entry["choices"].append({
                "id": "giant-ancestry", "kind": "option",
                "options": [{"id": slug, "name": giant, "source": src.ref(prefix + f"goliath-giant-ancestry-{slug}", f"({giant})")} for slug, giant in giants],
                "source": src.ref(prefix + "goliath-giant-ancestry", "Wähle einen der folgenden Vorzüge"),
            })
        elif key == "human":
            entry["choices"].append({"id": "skillful", "kind": "skill", "count": 1, "options": None, "source": src.ref(prefix + "human-skillful", "in einer Fertigkeit deiner Wahl geübt")})
            entry["choices"].append({"id": "versatile", "kind": "feat-category", "category": "Herkunftstalent", "recommended": "Begabt", "source": src.ref(prefix + "human-versatile", "ein Herkunftstalent deiner Wahl")})
        if len(entry["sizes"]) > 1:
            entry["choices"].append({"id": "size", "kind": "size", "options": entry["sizes"]})
        result.append(entry)
    return result


def _backgrounds(entities: list[dict], items: _Items) -> list[dict]:
    result = []
    for entity in sorted((e for e in entities if e["type"] == "background"), key=lambda e: e["name"].casefold()):
        tool = entity.get("tool")
        tool_entity = items.find(tool) if tool else None
        tool_choice = None
        if tool and tool_entity is None:
            if "Spielset" not in tool:
                raise ValueError(f"{entity['id']}: unmapped tool {tool!r}")
            tool_choice = {"count": 1, "category": "gaming-set"}
        result.append({
            "id": entity["id"], "name": entity["name"],
            "abilities": [_ability_id(name) for name in entity["abilities"]],
            "feat": entity["feat"], "featChoice": entity.get("featChoice"),
            "skills": [_slug(name) for name in entity["skills"]],
            "tool": tool_entity["id"] if tool_entity else None, "toolChoice": tool_choice,
            "startingEquipment": {k: _entries(v, items) for k, v in entity["equipmentOptions"].items()},
        })
    return result


_FEAT_CHOICES = {
    "feats.descriptions.skilled": [
        ("proficiencies", "skill-or-tool", {"count": 3}, "description", "drei Fertigkeiten oder Werkzeugen deiner Wahl in beliebiger Kombination"),
    ],
    "feats.descriptions.magic-initiate": [
        ("spell-list", "option", {"options": ["Druide", "Kleriker", "Magier"]}, "two-cantrips", "aus der Zauberliste des Druiden, des Klerikers oder des Magiers"),
        ("cantrips", "spells", {"count": 2, "level": 0}, "two-cantrips", "zwei Zaubertricks deiner Wahl"),
        ("level-1-spell", "spells", {"count": 1, "level": 1}, "level1-spell", "Wähle einen Zauber des 1. Grades"),
        ("spellcasting-ability", "ability", {"options": ["int", "wis", "cha"]}, "two-cantrips", "Intelligenz, Weisheit oder Charisma"),
    ],
    "feats.descriptions.ability-score-improvement": [
        ("increase", "ability-increase", {"patterns": [[2], [1, 1]], "max": 20}, "description", "um 2 Punkte oder zwei Attributswerte deiner Wahl um je 1 Punkt"),
    ],
}


def _feats(src: Source, entities: list[dict]) -> list[dict]:
    result = []
    for entity in sorted((e for e in entities if e["type"] == "feat"), key=lambda e: e["name"].casefold()):
        base = entity["id"]
        prerequisite = {"minLevel": None, "abilities": None, "requiresFeature": None, "raw": entity["prerequisite"]}
        for part in (entity["prerequisite"] or "").split(", "):
            if not part:
                continue
            level = re.fullmatch(r"min\. (\d+)\. Stufe", part)
            ability = re.fullmatch(r"min\. (.+?) (\d+)", part)
            if level:
                prerequisite["minLevel"] = int(level.group(1))
            elif ability:
                mode, abilities = _ability_list(ability.group(1))
                prerequisite["abilities"] = {"mode": mode, "abilities": abilities, "min": int(ability.group(2))}
            elif part == "Kampfstil-Merkmal":
                prerequisite["requiresFeature"] = "fighting-style"
            elif part == "Merkmal Zauberwirken":
                prerequisite["requiresFeature"] = "spellcasting"
            else:
                raise ValueError(f"{base}: unparsed feat prerequisite {part!r}")
        increase = None
        if base + "-ability-score-increase" in src.blocks:
            text = src.text(base + "-ability-score-increase")
            names = [name for name in _ABILITY_BY_NAME if name in text] or [name for name, _k in ()]
            cap = int(re.search(r"auf (?:höchstens|maximal) (\d+)", text).group(1))
            increase = {
                "abilities": [_ability_id(n) for n in names] or "any", "amount": 1, "max": cap,
                "source": src.ref(base + "-ability-score-increase", "Attributswerterhöhung"),
            }
        choices = []
        for cid, kind, extras, suffix, quote in _FEAT_CHOICES.get(base, []):
            choices.append({"id": cid, "kind": kind, **extras, "source": src.ref(f"{base}-{suffix}", quote)})
        result.append({
            "id": base, "name": entity["name"], "category": entity["category"], "prerequisite": prerequisite,
            "repeatable": (base + "-repeatable") in src.blocks,
            "abilityIncrease": increase, "choices": choices,
            "source": src.ref(base + "-category", entity["category"]),
        })
    return result


def _class_options(entities: list[dict]) -> list[dict]:
    result = []
    for entity in sorted((e for e in entities if e["type"] == "class-option"), key=lambda e: e["id"]):
        prerequisite = entity.get("prerequisite")
        level = re.match(r"Ab (\d+)\. ", prerequisite) if prerequisite else None
        result.append({
            "id": entity["id"], "name": entity["name"], "classKey": entity["classKey"], "kind": entity["optionKind"],
            "minClassLevel": int(level.group(1)) if level else None, "prerequisite": prerequisite, "cost": entity.get("cost"),
        })
    return result


def _languages_alignments_trinkets(src: Source) -> dict:
    prefix = "character-creation.overview-and-steps."
    languages = []
    for row in src.table(prefix + "standard-languages-table")["rows"]:
        entry = {"id": _slug(row[1]), "name": row[1], "kind": "standard", "roll": None}
        if row[0] != "–":
            low, _, high = row[0].replace("–", "-").partition("-")
            entry["roll"] = [int(low), int(high or low)]
        else:
            entry["automatic"] = True
        languages.append(entry)
    for row in src.table(prefix + "rare-languages-table")["rows"]:
        name = row[0].rstrip("*").strip()
        languages.append({"id": _slug(name), "name": name, "kind": "rare", "roll": None})
    covered = sorted(n for entry in languages if entry["roll"] for n in range(entry["roll"][0], entry["roll"][1] + 1))
    if covered != list(range(1, 13)):
        raise ValueError("standard language 1W12 ranges must cover 1-12 exactly once")

    ethics = {"Rechtschaffen": "lawful", "Neutral": "neutral", "Chaotisch": "chaotic"}
    morals = {"gut": "good", "neutral": "neutral", "böse": "evil"}
    alignments = []
    for entry in src.block("character-creation.abilities-alignment-and-details.nine-alignments-list")["entries"]:
        match = re.fullmatch(r"(.+) \((\w+)\)", entry["term"])
        name, abbr = match.group(1), match.group(2)
        if name == "Neutral":
            ethic, moral = "neutral", "neutral"
        else:
            first, _, second = name.partition(" ")
            ethic, moral = ethics[first], morals[second]
        alignments.append({"id": _slug(name), "name": name, "abbreviation": abbr, "ethic": ethic, "moral": moral})
    if len(alignments) != 9:
        raise ValueError("expected nine alignments")

    trinkets = [row[1] for row in src.table("character-creation.trinkets.trinkets-table")["rows"]]
    if len(trinkets) != 100:
        raise ValueError("expected 100 trinkets")
    return {"languages": languages, "alignments": alignments, "trinkets": trinkets}


def _modifiers(src: Source, classes: list[dict]) -> dict:
    barbarian = next(c for c in classes if c["classKey"] == "barbarian")
    monk = next(c for c in classes if c["classKey"] == "monk")
    sorcerer = next(c for c in classes if c["classKey"] == "sorcerer")
    if not any("Ungerüstete Bewegung" in row["columns"] for row in monk["levels"]):
        raise ValueError("monk table lacks the unarmored movement column")
    return {
        "armorClassFormulas": [
            {
                "id": "barbarian-unarmored-defense", "classKey": "barbarian", "minClassLevel": 1, "subclass": None,
                "base": 10, "abilities": ["dex", "con"], "armor": "none", "shield": "allowed",
                "source": src.ref("classes.barbarian.level1-unarmored-defense-description", "10 plus deinem Geschicklichkeitsmodifikator plus deinem Konstitutionsmodifikator"),
            },
            {
                "id": "monk-unarmored-defense", "classKey": "monk", "minClassLevel": 1, "subclass": None,
                "base": 10, "abilities": ["dex", "wis"], "armor": "none", "shield": "forbidden",
                "source": src.ref("classes.monk.level1-unarmored-defense-description", "weder Rüstung noch Schild"),
            },
            {
                "id": "draconic-resilience-scales", "classKey": "sorcerer", "minClassLevel": 3, "subclass": sorcerer["subclasses"][0],
                "base": 10, "abilities": ["dex", "cha"], "armor": "none", "shield": "allowed",
                "source": src.ref("classes.sorcerer.subclass-level3-draconic-resilience-scales", "10 plus deinem Geschicklichkeits- plus deinem Charismamodifikator"),
            },
        ],
        "armorClassBonuses": [
            {
                "id": "defense-fighting-style", "featId": "feats.descriptions.defense", "bonus": 1, "requiresArmor": True,
                "source": src.ref("feats.descriptions.defense-description", "Bonus von +1 auf die Rüstungsklasse"),
            }
        ],
        "hitPointBonuses": [
            {
                "id": "dwarven-toughness", "origin": "species", "speciesId": "character-origins.species.dwarf",
                "perCharacterLevel": 1,
                "source": src.ref("character-origins.species.dwarf-dwarven-toughness", "um 1 und bei jedem Stufenaufstieg um 1 weiteren Punkt"),
            },
            {
                "id": "draconic-resilience-hp", "origin": "subclass", "subclass": sorcerer["subclasses"][0], "classKey": "sorcerer",
                "minClassLevel": 3, "flat": 3, "perClassLevelAbove": 1,
                "source": src.ref("classes.sorcerer.subclass-level3-draconic-resilience-description", "um 3 Punkte und auf jeder höheren Zaubererstufe um 1 weiteren Punkt"),
            },
        ],
        "speedBonuses": [
            {
                "id": "barbarian-fast-movement", "classKey": "barbarian", "minClassLevel": 5, "meters": 3, "unless": ["heavy"],
                "source": src.ref("classes.barbarian.level5-fast-movement-description", "Bewegungsrate erhöht sich um drei Meter, sofern du keine schwere Rüstung trägst"),
            },
            {
                "id": "monk-unarmored-movement", "classKey": "monk", "minClassLevel": 2, "column": "Ungerüstete Bewegung",
                "armor": "none", "shield": "forbidden",
                "source": src.ref("classes.monk.level2-unarmored-movement-description", "sofern du weder Rüstung noch Schild trägst"),
            },
        ],
        "initiativeBonuses": [
            {
                "id": "alert-initiative", "featId": "feats.descriptions.alert", "bonus": "proficiencyBonus",
                "source": src.ref("feats.descriptions.alert-initiative-proficiency", "kannst du dem Ergebnis deinen Übungsbonus hinzufügen"),
            }
        ],
    }


def _spell_lists(entities: list[dict], classes: list[dict]) -> dict:
    key_by_name = {entry["name"]: entry["classKey"] for entry in classes}
    spells = [e for e in entities if e["type"] == "spell"]
    lists: dict[str, list[str]] = {key: [] for key in key_by_name.values()}
    for spell in sorted(spells, key=lambda e: e["id"]):
        for name in spell["classes"]:
            lists[key_by_name[name]].append(spell["id"])
    return {
        "spells": {s["id"]: {"level": s["level"], "ritual": bool(s["ritual"]), "name": s["name"]} for s in sorted(spells, key=lambda e: e["id"])},
        "spellLists": lists,
    }


def build_creator_data(manifest: dict, documents: list[dict], compendium: dict, errors: list[str] | None = None) -> dict:
    src = Source(documents, errors)
    entities = compendium["entities"]
    items = _Items(entities)
    spells = Spells(entities)
    core = _core(src)
    standard_rows = core.pop("_standardSetRows")
    classes = _classes(src, entities, items)
    by_name = {entry["name"]: entry for entry in classes}
    standard_set = {
        by_name[row[0]]["classKey"]: {key: int(value) for (key, _n, _a), value in zip(ABILITIES, row[1:])}
        for row in standard_rows
    }
    if sorted(standard_set) != sorted(entry["classKey"] for entry in classes):
        raise ValueError("standard set table does not cover all classes")
    for entry in classes:
        entry["standardAbilityScores"] = standard_set[entry["classKey"]]
        if sorted(entry["standardAbilityScores"].values(), reverse=True) != [15, 14, 13, 12, 10, 8]:
            raise ValueError(f"standard set for {entry['classKey']} is not the standard array")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "rulesetId": manifest["rulesetId"],
        "rulesetVersion": manifest["rulesetVersion"],
        **core,
        "hitPoints": _hit_points(src, {entry["name"]: entry["hitDie"] for entry in classes}),
        "multiclass": _multiclass(src),
        "startingEquipmentByLevel": _starting_levels(src),
        "classes": classes,
        **_modifiers(src, classes),
        **_spell_lists(entities, classes),
        "classOptions": _class_options(entities),
        "species": _species(src, entities, spells),
        "backgrounds": _backgrounds(entities, items),
        "feats": _feats(src, entities),
        "equipment": _equipment(src, entities, items),
        **_languages_alignments_trinkets(src),
    }
