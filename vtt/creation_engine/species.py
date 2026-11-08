"""Playability check: an Eagle Species document plus the VTT supplement -> a 2024 Species profile (pure).

Eagle writes Foundry dnd5e `race` Items. Only the fields listed here are converted; every other mechanic
(advancements other than Size, Active Effects, Activities, enricher references, unknown system fields) blocks
publication with a diagnostic that names the field and what to do. Prose is never mined for rules.

The supplement is the VTT-owned, typed part an Eagle Species cannot express: skill-proficiency choices,
race actions (`object-telekinesis` only) and narrative traits. Its schema is `SUPPLEMENT_FIELDS` below.
"""

from __future__ import annotations

import html
import re

from vtt.rules_content.species_profiles import ACTION_KINDS, ACTIVATIONS, PROFILE_SCHEMA, meters

SUPPLEMENT_SCHEMA = "roll-drauf.species-supplement.v1"
SUPPLEMENT_FIELDS = {"schema", "skillChoices", "actions", "traits"}
CHOICE_FIELDS = {"id", "label", "options"}
ACTION_FIELDS = {"id", "name", "kind", "activation", "uses", "rangeFeet", "maxWeightLb", "maxMoveFeet", "description"}
TRAIT_FIELDS = {"id", "name", "description"}
LIMITS = {"rangeFeet": (5, 120), "maxWeightLb": (1, 500), "maxMoveFeet": (5, 120)}
MAX_CHOICES, MAX_ACTIONS, MAX_TRAITS = 2, 4, 10
MAX_DESCRIPTION = 4000

CREATURE_TYPES = {
    "aberration": "Aberration", "beast": "Tier", "celestial": "Himmlisches Wesen", "construct": "Konstrukt",
    "dragon": "Drache", "elemental": "Elementar", "fey": "Feenwesen", "fiend": "Unhold", "giant": "Riese",
    "humanoid": "Humanoide", "monstrosity": "Monstrosität", "ooze": "Schlick", "plant": "Pflanze", "undead": "Untoter",
}
SIZES = {"tiny": "Winzig", "sm": "Klein", "med": "Mittelgroß", "lg": "Groß", "huge": "Riesig", "grg": "Gigantisch"}
MOVEMENT = {"walk": "Gehen", "swim": "Schwimmen", "fly": "Fliegen", "climb": "Klettern", "burrow": "Graben"}
SENSES = {"darkvision": "Dunkelsicht", "blindsight": "Blindsicht", "tremorsense": "Erschütterungssinn", "truesight": "Wahrsicht"}
SYSTEM_FIELDS = {"description", "source", "identifier", "type", "movement", "senses", "advancement"}
ADVANCEMENT_HINTS = {
    "Trait": "Fertigkeiten, Sprachen, Resistenzen oder Rettungswürfe aus einem Trait-Advancement übernimmt der VTT noch nicht. "
             "Lege eine Fertigkeitswahl im VTT-Zusatz an und entferne das Trait-Advancement in Eagle.",
    "ItemGrant": "Verknüpfte Items werden noch nicht übernommen. Beschreibe das Merkmal im VTT-Zusatz und entferne das Advancement.",
    "ItemChoice": "Item-Auswahlen werden noch nicht übernommen. Entferne das Advancement oder beschreibe das Merkmal im VTT-Zusatz.",
    "ScaleValue": "Skalenwerte werden nicht ausgewertet. Entferne das Advancement.",
    "AbilityScoreImprovement": "Spezies nach 2024 geben keine Attributserhöhung, das macht der Hintergrund. Entferne das Advancement.",
}
_ENRICHER = re.compile(r"@[A-Za-z]+\[|\[\[")
_NUMBER = re.compile(r"^\s*\d{1,4}(?:\.\d+)?\s*$")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


class _Report:
    def __init__(self):
        self.entries: list[dict] = []

    def add(self, path, status, code, message):
        self.entries.append({"path": path, "status": status, "code": code, "message": message})

    @property
    def blocked(self):
        return any(entry["status"] == "blocked" for entry in self.entries)


def _empty(value):
    return value in (None, "", [], {}, False, 0)


def _dict(value):
    return value if isinstance(value, dict) else {}


def plain_text(value) -> str:
    text = re.sub(r"<\s*(br|/p|/li|/h[1-6])\s*/?>", "\n", value if isinstance(value, str) else "", flags=re.I)
    text = html.unescape(re.sub(r"<[^>]*>", "", text))
    text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _distance(value, units, path, report, label):
    """(feet, meters) of a Foundry distance, None when unset; a formula or bad unit blocks."""
    if value in (None, "", 0):
        return None
    if isinstance(value, bool) or not (isinstance(value, (int, float)) or (isinstance(value, str) and _NUMBER.match(value))):
        report.add(path, "blocked", "formula", f"{label}: nur eine feste Zahl ist spielbar, keine Formel ({str(value)[:40]}).")
        return None
    number = float(value)
    if not 0 < number <= 1000:
        report.add(path, "blocked", "out-of-range", f"{label}: zwischen 1 und 1000 erwartet.")
        return None
    if units == "m":
        return round(number / 0.3), round(number, 1)
    return round(number), meters(number)


def _units(value, path, report):
    if value in (None, "", "ft", "m"):
        return value or "ft"
    report.add(path, "blocked", "units", "Nur Fuß (ft) oder Meter (m) sind spielbar.")
    return "ft"


def _edition(system, pack, report):
    rules = _dict(system.get("source")).get("rules")
    if rules == "2024":
        report.add("system.source.rules", "converted", "edition", "Regelwerk 2024.")
        return "2024"
    if rules == "2014" or (not rules and pack.endswith("-2014")):
        report.add("system.source.rules", "blocked", "edition-2014",
                   "2014-Spezies sind noch nicht spielbar: Der Charakter-Ersteller baut 2024-Charaktere (SRD 5.2.1). "
                   "Lege die Spezies als 2024-Fassung an, um sie zu veröffentlichen.")
        return "2014"
    if rules:
        report.add("system.source.rules", "blocked", "edition-unknown", f"Unbekanntes Regelwerk „{str(rules)[:20]}“; erwartet wird 2024.")
        return None
    report.add("system.source.rules", "converted", "edition-assumed", "Kein Regelwerk angegeben; wie im Editor gilt 2024.")
    return "2024"


def _creature_type(system, report):
    kind = _dict(system.get("type"))
    for field, value in kind.items():
        if field not in {"value", "subtype", "custom"} and not _empty(value):
            report.add(f"system.type.{field}", "blocked", "type-unsupported", f"Kreaturentyp-Feld „{field}“ wird nicht übernommen; entferne den Wert.")
    key = kind.get("value")
    detail = " ".join(part for part in (kind.get("subtype"), kind.get("custom")) if isinstance(part, str) and part.strip())[:80]
    if key == "custom" and detail:
        report.add("system.type", "converted", "creature-type", f"Eigener Kreaturentyp „{detail}“.")
        return {"key": "custom", "label": detail, "detail": ""}
    if key not in CREATURE_TYPES:
        report.add("system.type.value", "blocked", "creature-type-missing", "Wähle in Eagle einen Kreaturentyp (zum Beispiel Humanoid).")
        return None
    report.add("system.type.value", "converted", "creature-type", f"Kreaturentyp {CREATURE_TYPES[key]}.")
    return {"key": key, "label": CREATURE_TYPES[key] + (f" ({detail})" if detail else ""), "detail": detail}


def _movement(system, report):
    movement = _dict(system.get("movement"))
    units = _units(movement.get("units"), "system.movement.units", report)
    out = []
    for mode, label in MOVEMENT.items():
        value = _distance(movement.get(mode), units, f"system.movement.{mode}", report, label)
        if value:
            out.append({"mode": mode, "label": label, "feet": value[0], "meters": value[1]})
            report.add(f"system.movement.{mode}", "converted", "movement", f"{label} {value[0]} ft ({str(value[1]).replace('.', ',')} m).")
    for key, value in movement.items():
        if key not in MOVEMENT and key != "units" and not _empty(value):
            report.add(f"system.movement.{key}", "blocked", "movement-unsupported", f"„{key}“ der Bewegung wird nicht unterstützt; entferne den Wert.")
    if not any(entry["mode"] == "walk" for entry in out):
        report.add("system.movement.walk", "blocked", "walk-missing", "Trage eine Gehgeschwindigkeit ein (zum Beispiel 30 ft).")
    return out


def _senses(system, report):
    senses = _dict(system.get("senses"))
    ranges = _dict(senses.get("ranges")) or {k: senses.get(k) for k in SENSES}
    units = _units(senses.get("units"), "system.senses.units", report)
    out = []
    for sense, label in SENSES.items():
        value = _distance(ranges.get(sense), units, f"system.senses.ranges.{sense}", report, label)
        if value:
            out.append({"sense": sense, "label": label, "feet": value[0], "meters": value[1]})
            report.add(f"system.senses.ranges.{sense}", "converted", "sense", f"{label} {value[0]} ft.")
    for sense, value in ranges.items():
        if sense not in SENSES and not _empty(value):
            report.add(f"system.senses.ranges.{sense}", "blocked", "sense-unsupported", f"Sinn „{sense}“ wird nicht übernommen; entferne den Wert.")
    if not any(entry["sense"] == "darkvision" for entry in out):
        report.add("system.senses.ranges.darkvision", "converted", "no-darkvision", "Keine Dunkelsicht.")
    note = plain_text(senses.get("special"))
    if len(note) > 200:
        report.add("system.senses.special", "blocked", "senses-note-too-long", "Besondere Sinne: höchstens 200 Zeichen; kürze den Text.")
        note = note[:200]
    if note:
        report.add("system.senses.special", "narrative", "senses-note", "Besondere Sinne werden als Text angezeigt.")
    for key, value in senses.items():
        if key not in {"ranges", "units", "special", *SENSES} and not _empty(value):
            report.add(f"system.senses.{key}", "blocked", "sense-unsupported", f"Sinn „{key}“ wird nicht unterstützt.")
    return out, note


def _advancements(system, report):
    raw = system.get("advancement")
    items = list(raw.items()) if isinstance(raw, dict) else list(enumerate(raw if isinstance(raw, list) else []))
    sizes = None
    for key, advancement in items:
        advancement = _dict(advancement)
        kind = advancement.get("type")
        path = f"system.advancement.{advancement.get('_id') or key}"
        if kind == "Size" and sizes is None:
            chosen = _dict(advancement.get("configuration")).get("sizes")
            chosen = [s for s in chosen if isinstance(s, str)] if isinstance(chosen, list) else []
            unknown = [s for s in chosen if s not in SIZES]
            if not chosen or unknown:
                report.add(path, "blocked", "size-invalid", "Wähle im Größen-Advancement mindestens eine bekannte Größe.")
                continue
            sizes = [{"key": s, "label": SIZES[s]} for s in SIZES if s in chosen]
            report.add(path, "converted", "size", "Größe " + " oder ".join(s["label"] for s in sizes) + ".")
        else:
            hint = ADVANCEMENT_HINTS.get(kind, "Dieser Advancement-Typ ist dem VTT unbekannt. Entferne ihn.")
            report.add(path, "blocked", "advancement-unsupported", f"{kind or 'Advancement'}: {hint}")
    if sizes is None:
        report.add("system.advancement", "blocked", "size-missing", "Füge in Eagle ein Größen-Advancement hinzu (zum Beispiel Klein).")
    return sizes or []


def _check_text(value, limit, path, label, report, *, required=True):
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        report.add(path, "blocked", "supplement-invalid", f"{label}: Text mit {'1' if required else '0'} bis {limit} Zeichen erwartet.")
        return None
    return " ".join(value.split()) if limit <= 80 else value.strip()


def _check_id(value, path, seen, report):
    if not isinstance(value, str) or not _ID.match(value) or value in seen or value == "size":
        report.add(path, "blocked", "supplement-invalid", "Kennung: eindeutig, Kleinbuchstaben, Ziffern und Bindestriche (höchstens 40).")
        return None
    seen.add(value)
    return value


def _exact(entry, fields, path, report):
    if not isinstance(entry, dict):
        report.add(path, "blocked", "supplement-invalid", "Objekt erwartet.")
        return False
    extra = sorted(set(entry) - fields)
    missing = sorted(fields - set(entry))
    if extra or missing:
        report.add(path, "blocked", "supplement-invalid", "Felder " + ", ".join(
            [*(f"„{k}“ unbekannt" for k in extra[:5]), *(f"„{k}“ fehlt" for k in missing)]) + ".")
        return False
    return True


def _supplement(supplement, skills, report):
    """(skillChoices, actions, traits) from the typed VTT supplement."""
    if supplement is None:
        supplement = {}
    if not isinstance(supplement, dict):
        report.add("supplement", "blocked", "supplement-invalid", "Der VTT-Zusatz muss ein Objekt sein.")
        return [], [], []
    for key in sorted(set(supplement) - SUPPLEMENT_FIELDS):
        report.add(f"supplement.{key}", "blocked", "supplement-invalid", f"Unbekanntes Feld „{str(key)[:40]}“ im VTT-Zusatz.")
    if supplement.get("schema", SUPPLEMENT_SCHEMA) != SUPPLEMENT_SCHEMA:
        report.add("supplement.schema", "blocked", "supplement-invalid", f"Schema muss {SUPPLEMENT_SCHEMA} sein.")
    seen: set[str] = set()
    choices, actions, traits = [], [], []
    for name, limit in (("skillChoices", MAX_CHOICES), ("actions", MAX_ACTIONS), ("traits", MAX_TRAITS)):
        value = supplement.get(name, [])
        if not isinstance(value, list) or len(value) > limit:
            report.add(f"supplement.{name}", "blocked", "supplement-invalid", f"Liste mit höchstens {limit} Einträgen erwartet.")
            supplement = {**supplement, name: []}
    for index, raw in enumerate(supplement.get("skillChoices", [])):
        path = f"supplement.skillChoices[{index}]"
        if not _exact(raw, CHOICE_FIELDS, path, report):
            continue
        choice_id = _check_id(raw["id"], f"{path}.id", seen, report)
        label = _check_text(raw["label"], 60, f"{path}.label", "Bezeichnung", report)
        options = raw["options"]
        if not isinstance(options, list) or not 2 <= len(options) <= len(skills) or len(set(map(str, options))) != len(options) \
                or any(option not in skills for option in options):
            report.add(f"{path}.options", "blocked", "skill-options", "Wähle mindestens zwei verschiedene Fertigkeiten aus dem SRD.")
            continue
        if choice_id and label:
            choices.append({"id": choice_id, "label": label, "options": list(options)})
            report.add(path, "converted", "skill-choice", f"{label}: Übung in " + " oder ".join(skills[o] for o in options) + " (Spielerwahl).")
    for index, raw in enumerate(supplement.get("actions", [])):
        path = f"supplement.actions[{index}]"
        if not _exact(raw, ACTION_FIELDS, path, report):
            continue
        before = len(report.entries)
        action_id = _check_id(raw["id"], f"{path}.id", seen, report)
        name = _check_text(raw["name"], 80, f"{path}.name", "Name", report)
        description = _check_text(raw["description"], 2000, f"{path}.description", "Beschreibung", report, required=False)
        if raw["kind"] not in ACTION_KINDS:
            report.add(f"{path}.kind", "blocked", "action-kind", "Spielbar ist nur „object-telekinesis“ (unbeaufsichtigten Gegenstand bewegen).")
        if raw["activation"] not in ACTIVATIONS:
            report.add(f"{path}.activation", "blocked", "action-activation", "Aktivierung: „action“ oder „bonus-action“.")
        if raw["uses"] != "at-will":
            report.add(f"{path}.uses", "blocked", "action-uses", "Nur „at-will“ ist spielbar; begrenzte Nutzungen mit Rast-Zählern kommen später.")
        numbers = {}
        for field, (low, high) in LIMITS.items():
            value = raw[field]
            if type(value) is not int or not low <= value <= high:
                report.add(f"{path}.{field}", "blocked", "action-limit", f"{field}: ganze Zahl von {low} bis {high}.")
            numbers[field] = value
        if any(entry["status"] == "blocked" for entry in report.entries[before:]):
            continue
        actions.append({
            "id": action_id, "name": name, "kind": raw["kind"], "activation": raw["activation"], "uses": "at-will",
            **numbers, "adjudication": "dm", "description": description or "",
            "restrictions": ["no-attack", "no-damage", "no-creature", "no-worn-or-carried"],
        })
        report.add(path, "converted", "action", f"{name}: Aktion für den Tisch, die Spielleitung entscheidet.")
    for index, raw in enumerate(supplement.get("traits", [])):
        path = f"supplement.traits[{index}]"
        if not _exact(raw, TRAIT_FIELDS, path, report):
            continue
        trait_id = _check_id(raw["id"], f"{path}.id", seen, report)
        name = _check_text(raw["name"], 80, f"{path}.name", "Name", report)
        description = _check_text(raw["description"], 2000, f"{path}.description", "Beschreibung", report)
        if trait_id and name and description:
            traits.append({"id": trait_id, "name": name, "description": description})
            report.add(path, "narrative", "trait", f"{name}: Text für die Spielleitung, ohne Automatik.")
    return choices, actions, traits


def inspect(source: dict, supplement, *, skills: dict, pack: str = "") -> dict:
    """{playable, edition, entries, profile}; `profile` is set only when nothing blocks publication.

    `skills` maps SRD skill ids to names (creator data). `pack` is the Library pack of a Library document.
    """
    report = _Report()
    source = source if isinstance(source, dict) else {}
    system = _dict(source.get("system"))
    if source.get("type") != "race":
        report.add("type", "blocked", "not-species", "Nur Spezies (Eagle: Species) können als Herkunft veröffentlicht werden.")
    name = source.get("name") if isinstance(source.get("name"), str) else ""
    if not 1 <= len(name.strip()) <= 100:
        report.add("name", "blocked", "name-invalid", "Trage einen Speziesnamen mit 1 bis 100 Zeichen ein.")
    else:
        report.add("name", "converted", "name", f"Name „{name[:80]}“.")
    edition = _edition(system, pack, report)
    creature_type = _creature_type(system, report)
    sizes = _advancements(system, report)
    movement = _movement(system, report)
    senses, senses_note = _senses(system, report)
    description_fields = _dict(system.get("description"))
    raw_description = description_fields.get("value")
    for field, value in description_fields.items():
        if field != "value" and not _empty(value):
            report.add(f"system.description.{field}", "blocked", "description-unsupported",
                       f"Beschreibung „{field}“ wird nicht gezeigt; verschiebe den Text in die normale Beschreibung oder den VTT-Zusatz.")
    if isinstance(raw_description, str) and _ENRICHER.search(raw_description):
        report.add("system.description.value", "blocked", "description-reference",
                   "Der Text enthält Foundry-Verweise oder Inline-Würfe (@UUID[…], [[…]]). Schreibe sie als normalen Text.")
    description = plain_text(raw_description)
    if len(description) > MAX_DESCRIPTION:
        report.add("system.description.value", "blocked", "description-too-long", f"Beschreibung: höchstens {MAX_DESCRIPTION} sichtbare Zeichen; kürze den Text.")
        description = description[:MAX_DESCRIPTION]
    if description:
        report.add("system.description.value", "narrative", "description", "Beschreibung wird als Text angezeigt.")
    for key, value in system.items():
        if key not in SYSTEM_FIELDS and not _empty(value):
            report.add(f"system.{key}", "blocked", "field-unsupported", f"„{key}“ ist dem VTT als Spezies-Regel unbekannt; entferne den Wert.")
    if not _empty(source.get("effects")):
        report.add("effects", "blocked", "effects-unsupported", "Active Effects werden nicht ausgeführt. Entferne sie oder beschreibe die Regel im VTT-Zusatz.")
    choices, actions, traits = _supplement(supplement, skills, report)
    playable = edition == "2024" and not report.blocked
    profile = None
    if playable:
        profile = {
            "schema": PROFILE_SCHEMA, "edition": edition, "name": name.strip()[:100], "description": description,
            "creatureType": creature_type, "sizes": sizes, "movement": movement, "senses": senses, "sensesNote": senses_note,
            "skillChoices": choices, "actions": actions, "traits": traits,
        }
    return {"playable": playable, "edition": edition, "entries": report.entries, "profile": profile}
