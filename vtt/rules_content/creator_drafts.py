"""Draft state hygiene and finalize mapping of the SRD character creator (pure, no Flask).

`sanitize_state` is the only door for client-supplied creator state: it is
strictly structural (types, sizes, known top-level fields). Rule validation stays in
`creator_rules.evaluate`; this module never decides what is *legal*, only what is
*storable*.
"""

from __future__ import annotations

import json
import math

from vtt.rules_content.creator_sources import SRD_SOURCE_ID, default_source_ids, pin_sources

SYSTEM_ID = "srd_5_2_1_de"
SRD_BLOCK_SCHEMA = "roll-drauf.srd-character.v1"

STATE_FIELDS = (
    "abilityMethod", "abilityBase", "abilityRolls", "levels", "background", "species", "subclasses",
    "advancements", "skills", "featureChoices", "equipment", "spells", "overrides", "identity", "sources",
)
IDENTITY_SHORT = ("name", "pronouns", "age", "height", "weight", "eyes", "hair", "skin", "faith")
IDENTITY_LONG = ("appearance", "traits", "ideals", "bonds", "flaws", "backstory", "notes")
IDENTITY_FIELDS = IDENTITY_SHORT + IDENTITY_LONG + ("alignment",)

MAX_STATE_BYTES = 100_000
MAX_DEPTH = 7
MAX_NODES = 6_000
MAX_KEY = 80
MAX_STRING = 2_000
MAX_LONG_TEXT = 8_000
MAX_SHORT_TEXT = 100


def _walk(value, depth, counter, path, problems):
    counter[0] += 1
    if counter[0] > MAX_NODES:
        problems.append({"path": path, "message": "Der Entwurf ist zu umfangreich."})
        return False
    if depth > MAX_DEPTH:
        problems.append({"path": path, "message": "Die Struktur ist zu tief verschachtelt."})
        return False
    if value is None or isinstance(value, (bool, int)):
        return True
    if isinstance(value, float):
        if not math.isfinite(value):
            problems.append({"path": path, "message": "Zahlen müssen endlich sein."})
            return False
        return True
    if isinstance(value, str):
        limit = MAX_LONG_TEXT if path.startswith("identity.") else MAX_STRING
        if len(value) > limit:
            problems.append({"path": path, "message": f"Text zu lang (höchstens {limit} Zeichen)."})
            return False
        return True
    if isinstance(value, list):
        if len(value) > 400:
            problems.append({"path": path, "message": "Liste zu lang."})
            return False
        return all(_walk(item, depth + 1, counter, f"{path}[{i}]", problems) for i, item in enumerate(value))
    if isinstance(value, dict):
        if len(value) > 400:
            problems.append({"path": path, "message": "Objekt hat zu viele Felder."})
            return False
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_KEY:
                problems.append({"path": path, "message": "Ungültiger Feldname."})
                return False
            if not _walk(item, depth + 1, counter, f"{path}.{key}" if path else key, problems):
                return False
        return True
    problems.append({"path": path, "message": "Nicht unterstützter Werttyp."})
    return False


def sanitize_state(raw, data: dict) -> tuple[dict, list[dict]]:
    """Return (clean state, problems). Problems are `{path, message}`; a non-empty list means: do not store."""
    problems: list[dict] = []
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return {}, [{"path": "", "message": "Der Entwurfszustand muss ein Objekt sein."}]
    unknown = sorted(key for key in raw if key not in STATE_FIELDS)
    for key in unknown[:10]:
        problems.append({"path": str(key)[:MAX_KEY], "message": "Unbekanntes Feld."})
    if not _walk(raw, 0, [0], "", problems):
        return {}, problems
    clean = {key: raw[key] for key in STATE_FIELDS if key in raw}
    if len(json.dumps(clean, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > MAX_STATE_BYTES:
        problems.append({"path": "", "message": "Der Entwurf ist zu groß."})
    problems.extend(_check_identity(clean.get("identity"), data))
    problems.extend(_check_sources(clean.get("sources")))
    return clean, problems


def _check_identity(identity, data: dict) -> list[dict]:
    if identity is None:
        return []
    if not isinstance(identity, dict):
        return [{"path": "identity", "message": "Die Beschreibung muss ein Objekt sein."}]
    problems = []
    for key, value in identity.items():
        path = f"identity.{key}"
        if key not in IDENTITY_FIELDS:
            problems.append({"path": path, "message": "Unbekanntes Feld."})
        elif key == "alignment":
            if value is not None and value not in {entry["id"] for entry in data["alignments"]}:
                problems.append({"path": path, "message": "Unbekannte Gesinnung."})
        elif value is not None and not isinstance(value, str):
            problems.append({"path": path, "message": "Text erwartet."})
        elif isinstance(value, str) and key in IDENTITY_SHORT and len(value) > MAX_SHORT_TEXT:
            problems.append({"path": path, "message": f"Text zu lang (höchstens {MAX_SHORT_TEXT} Zeichen)."})
    return problems


def _check_sources(sources) -> list[dict]:
    from vtt.rules_content.creator_sources import validate_source_ids

    return [{"path": "sources", "message": message} for message in validate_source_ids(sources)]


def identity_name(state: dict) -> str:
    identity = state.get("identity") if isinstance(state.get("identity"), dict) else {}
    name = identity.get("name")
    return name.strip() if isinstance(name, str) else ""


def finalize_blockers(evaluation: dict, state: dict) -> list[dict]:
    """Reasons a draft cannot become a character yet (empty list: ready)."""
    blockers = [
        {"code": item["code"], "severity": item["severity"], "message": item["message"], "path": item.get("path")}
        for item in evaluation["findings"]
        if item["severity"] in {"error", "incomplete"}
    ]
    if not identity_name(state):
        blockers.append({"code": "name-missing", "severity": "incomplete", "message": "Gib deinem Charakter einen Namen.", "path": "identity.name"})
    return blockers


def character_values(data: dict, state: dict, evaluation: dict, *, draft_id: int, finalized_at: str) -> dict:
    """Column values and `character_data` for a finished SRD character, derived on the server only."""
    species = next((entry for entry in data["species"] if entry["id"] == (state.get("species") or {}).get("id")), None)
    background = next((entry for entry in data["backgrounds"] if entry["id"] == (state.get("background") or {}).get("id")), None)
    classes = evaluation["classes"]
    if len(classes) == 1:
        class_name = classes[0]["name"]
    else:
        class_name = " / ".join(f"{entry['name']} {entry['level']}" for entry in classes)
    xp = next((row["xp"] for row in data["levels"] if row["level"] == evaluation["level"]), 0)
    abilities = evaluation["abilities"]
    sources = state.get("sources") or default_source_ids()
    srd_block = {
        "schema": SRD_BLOCK_SCHEMA,
        "sources": pin_sources(data, sources),
        "draftId": draft_id,
        "finalizedAt": finalized_at,
        "state": state,
        "derived": evaluation,
    }
    return {
        "name": identity_name(state)[:100],
        "race": (species["name"] if species else "")[:50],
        "class_name": class_name[:50],
        "background": (background["name"] if background else "")[:100],
        "level": evaluation["level"],
        "xp": xp,
        "ac": evaluation["armorClass"]["value"],
        "hp_max": evaluation["hitPoints"]["max"],
        "hp_current": evaluation["hitPoints"]["max"],
        "str_score": abilities["str"]["score"],
        "dex_score": abilities["dex"]["score"],
        "con_score": abilities["con"]["score"],
        "int_score": abilities["int"]["score"],
        "wis_score": abilities["wis"]["score"],
        "cha_score": abilities["cha"]["score"],
        "proficiency_bonus": evaluation["proficiencyBonus"],
        "character_data": {"system_id": SYSTEM_ID, "system_version": 1, "srd": srd_block},
    }


def is_srd_character_data(character_data) -> bool:
    return isinstance(character_data, dict) and (character_data.get("system_id") == SYSTEM_ID or "srd" in character_data)


__all__ = [
    "SRD_BLOCK_SCHEMA", "SRD_SOURCE_ID", "SYSTEM_ID", "STATE_FIELDS", "character_values", "finalize_blockers",
    "identity_name", "is_srd_character_data", "sanitize_state",
]
