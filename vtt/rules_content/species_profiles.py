"""Published homebrew Species as the SRD rules engine sees them (pure, no Flask, no database).

A published Species revision carries an immutable *profile* (built by `vtt.creation_engine.species`). A character
pins that profile in its SRD block (`srd.speciesPin`); every evaluation of the character reads the Species from
the pin through `rules_data_for_block`, never from the mutable Eagle document or the catalog. A draft refers to
the revision by its Species id (`homebrew.species.<revision id>`); the server resolves it after checking access.
"""

from __future__ import annotations

import math
import re

from .creator_rules import load_creator_data

PROFILE_SCHEMA = "roll-drauf.species-profile.v1"
PIN_SCHEMA = "roll-drauf.species-pin.v1"
SPECIES_PREFIX = "homebrew.species."
FEET_TO_METERS = 0.3  # the German SRD writes 30 ft as 9 m
_SPECIES_ID = re.compile(r"^homebrew\.species\.([1-9][0-9]{0,9})$")

ACTION_KINDS = {"object-telekinesis"}
ACTIVATIONS = {"action": "Aktion", "bonus-action": "Bonusaktion"}
MAX_OBJECT_TEXT = 160


def meters(feet) -> float:
    return round(feet * FEET_TO_METERS, 1)


def species_id(revision_id: int) -> str:
    return f"{SPECIES_PREFIX}{revision_id}"


def revision_id_of(value) -> int | None:
    """Revision id of a homebrew Species id, else None (SRD ids and garbage alike)."""
    match = _SPECIES_ID.match(value) if isinstance(value, str) else None
    return int(match.group(1)) if match else None


def is_homebrew_species(value) -> bool:
    return isinstance(value, str) and value.startswith(SPECIES_PREFIX)


def species_entry(profile: dict, sid: str) -> dict:
    """The profile in the shape of a creator-data Species, so `creator_rules.evaluate` needs no special case."""
    sizes = [size["label"] for size in profile["sizes"]]
    walk = next((m["meters"] for m in profile["movement"] if m["mode"] == "walk"), 0.0)
    darkvision = next((s["meters"] for s in profile["senses"] if s["sense"] == "darkvision"), None)
    choices = [
        {"id": choice["id"], "kind": "skill", "label": choice["label"], "options": list(choice["options"]),
         "grants": "proficiency", "source": None}
        for choice in profile["skillChoices"]
    ]
    if len(sizes) > 1:
        choices.append({"id": "size", "kind": "size", "label": "Größe", "options": sizes, "source": None})
    return {
        "id": sid,
        "name": profile["name"],
        "creatureType": profile["creatureType"]["label"],
        "sizes": sizes,
        "speedMeters": walk,
        "darkvisionMeters": darkvision,
        "traits": [trait["name"] for trait in profile["traits"]] + [action["name"] for action in profile["actions"]],
        "choices": choices,
        "grants": None,
        "homebrew": True,
        "description": profile.get("description") or "",
    }


def with_species(data: dict, entry: dict) -> dict:
    """Creator data plus one Species; the cached creator data itself is never modified."""
    return {**data, "species": [*data["species"], entry]}


def pinned(block) -> dict | None:
    """The Species pin of a character's SRD block, or None for SRD-only characters."""
    pin = block.get("speciesPin") if isinstance(block, dict) else None
    if not isinstance(pin, dict) or pin.get("schema") != PIN_SCHEMA:
        return None
    if type(pin.get("revisionId")) is not int or not isinstance(pin.get("profile"), dict):
        return None
    return pin


def rules_data_for_block(block, data: dict | None = None) -> dict:
    """The rules data one character is evaluated with: the SRD package plus its pinned Species, if any."""
    data = data or load_creator_data()
    pin = pinned(block)
    if pin is not None:
        data = with_species(data, species_entry(pin["profile"], species_id(pin["revisionId"])))
    from .origin_profiles import pinned as rule_pins, with_pins
    return with_pins(data, rule_pins(block))


def action_summary(action: dict) -> str:
    activation = ACTIVATIONS.get(action.get("activation"), action.get("activation"))
    return (f"{activation} · beliebig oft · bewegt einen unbeaufsichtigten Gegenstand (höchstens {action['maxWeightLb']} lb) "
            f"in bis zu {action['rangeFeet']} ft Entfernung um bis zu {action['maxMoveFeet']} ft. Kein Angriff, kein Schaden, "
            "keine Kreaturen, nichts Getragenes oder Gehaltenes. Die Spielleitung entscheidet, ob der Gegenstand infrage kommt.")


def origin_view(pin: dict | None) -> dict | None:
    """What sheet, party and table show about a pinned Species (provenance included, no Eagle source)."""
    if pin is None:
        return None
    profile = pin["profile"]
    return {
        "speciesId": species_id(pin["revisionId"]),
        "revisionId": pin["revisionId"],
        "revision": pin.get("revision"),
        "digest": pin.get("digest"),
        "scope": pin.get("scope"),
        "author": pin.get("author"),
        "name": profile["name"],
        "edition": profile["edition"],
        "description": profile.get("description") or "",
        "creatureType": profile["creatureType"],
        "sizes": profile["sizes"],
        "movement": profile["movement"],
        "senses": profile["senses"],
        "sensesNote": profile.get("sensesNote") or "",
        "traits": profile["traits"],
        "skillChoices": profile["skillChoices"],
        "actions": [{**action, "summary": action_summary(action)} for action in profile["actions"]],
    }


def find_action(pin: dict | None, action_id) -> dict | None:
    if pin is None or not isinstance(action_id, str):
        return None
    return next((a for a in pin["profile"]["actions"] if a.get("id") == action_id), None)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def check_declaration(action: dict, body) -> tuple[dict, list[dict]]:
    """(declaration, problems) for one use of a race action; the declaration is what the table log records."""
    problems = []
    body = body if isinstance(body, dict) else {}
    if action.get("kind") not in ACTION_KINDS:
        return {}, [{"path": "", "message": "Diese Aktion wird vom VTT nicht unterstützt."}]
    text = body.get("object")
    text = " ".join(text.split()) if isinstance(text, str) else ""
    if not 3 <= len(text) <= MAX_OBJECT_TEXT:
        problems.append({"path": "object", "message": f"Beschreibe den Gegenstand in 3 bis {MAX_OBJECT_TEXT} Zeichen."})
    limits = (("weightLb", "Gewicht", action["maxWeightLb"], "lb", False),
              ("distanceFeet", "Entfernung", action["rangeFeet"], "ft", True),
              ("moveFeet", "Bewegung", action["maxMoveFeet"], "ft", False))
    declaration = {"object": text}
    for field, label, limit, unit, zero_ok in limits:
        value = _number(body.get(field))
        if value is None or value < 0 or (value == 0 and not zero_ok) or value > limit:
            problems.append({"path": field, "message": f"{label}: höchstens {limit} {unit}" + (" und mehr als 0." if not zero_ok else ".")})
        else:
            declaration[field] = int(value) if float(value).is_integer() else round(value, 1)
    if body.get("unattended") is not True:
        problems.append({"path": "unattended", "message": "Bestätige, dass niemand den Gegenstand trägt oder hält."})
    for forbidden in ("targetCreature", "damage", "attack"):
        if body.get(forbidden):
            problems.append({"path": forbidden, "message": "Telekinese greift nicht an, macht keinen Schaden und bewegt keine Kreaturen."})
    return declaration, problems


def declaration_text(char_name: str, action: dict, declaration: dict) -> str:
    activation = ACTIVATIONS.get(action.get("activation"), action.get("activation"))
    return (f"{char_name} · {action['name']} ({activation}, Spielleitung entscheidet): bewegt „{declaration['object']}“ "
            f"(≈ {declaration['weightLb']} lb, {declaration['distanceFeet']} ft entfernt) um bis zu {declaration['moveFeet']} ft. "
            "Kein Angriff, kein Schaden, keine Kreaturen, nichts Getragenes.")
