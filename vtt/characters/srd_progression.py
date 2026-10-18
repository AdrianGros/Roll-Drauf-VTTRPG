"""Experience, milestones and level-up of SRD characters.

Everything that changes a character here goes through `creator_rules.evaluate`: a level-up builds a
candidate state from the stored one, the engine judges it, and only a complete, valid result is stored.
"""

import copy

from sqlalchemy.orm.attributes import flag_modified

from vtt.rules_content.creator_drafts import class_label, finalize_blockers, sanitize_state
from vtt.rules_content.creator_rules import evaluate, level_for_xp
from vtt.utils.time import utcnow

MODES = ("xp", "milestone")
MAX_XP = 10_000_000
MAX_HISTORY = 300
ADVANCEMENT_FIELDS = ("kind", "featId", "increaseAbility", "increases")


class ProgressionError(Exception):
    def __init__(self, code, message, status=422, **extra):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra


def _block(char):
    block = (char.character_data or {}).get("srd")
    if not isinstance(block, dict):
        raise ProgressionError("not_srd", "Kein SRD-Charakter.")
    return block


def _threshold(data, level):
    return next(row["xp"] for row in data["levels"] if row["level"] == level)


def progression(char):
    stored = _block(char).get("progression")
    stored = stored if isinstance(stored, dict) else {}
    mode = stored.get("mode") if stored.get("mode") in MODES else "xp"
    target = stored.get("milestoneTarget")
    return {"mode": mode, "milestoneTarget": target if isinstance(target, int) else None}


def status(char, data):
    """Where the character stands: level, XP, the level it may reach now and the next XP threshold."""
    prog = progression(char)
    level = char.level or 1
    xp = char.xp or 0
    cap = data["maxLevel"]
    if prog["mode"] == "xp":
        target = level_for_xp(data, xp)
    else:
        target = prog["milestoneTarget"] or level
    target = max(level, min(cap, target))
    return {
        "mode": prog["mode"],
        "level": level,
        "xp": xp,
        "maxLevel": cap,
        "targetLevel": target,
        "canLevelUp": level < cap and target > level,
        "currentLevelXp": _threshold(data, level),
        "nextLevelXp": _threshold(data, level + 1) if level < cap else None,
        "milestoneTarget": prog["milestoneTarget"],
    }


def history(char):
    entries = _block(char).get("history")
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def _log(block, entry):
    entries = block.get("history") if isinstance(block.get("history"), list) else []
    entries.append({"at": utcnow().isoformat() + "Z", **entry})
    block["history"] = entries[-MAX_HISTORY:]


def _int(value):
    return value if type(value) is int else None


# --------------------------------------------------------------------------- XP and milestones

def set_progression(char, data, body, *, user_id):
    """XP award / set, switch between XP and milestone, milestone target (caller checks who may do it, commits)."""
    if not isinstance(body, dict):
        raise ProgressionError("invalid_body", "JSON-Objekt erwartet.", 400)
    note = body.get("note")
    note = note.strip()[:200] if isinstance(note, str) else ""
    changes = []
    block_data = copy.deepcopy(char.character_data)
    block = block_data["srd"]
    prog = dict(progression(char))
    xp = char.xp or 0
    if "mode" in body:
        if body["mode"] not in MODES:
            raise ProgressionError("invalid_mode", "Der Modus muss „xp“ oder „milestone“ sein.")
        if body["mode"] != prog["mode"]:
            prog["mode"] = body["mode"]
            changes.append({"type": "mode", "mode": body["mode"]})
    if "addXp" in body or "setXp" in body:
        if "addXp" in body and "setXp" in body:
            raise ProgressionError("invalid_xp", "Entweder addXp oder setXp.")
        if "addXp" in body:
            amount = _int(body["addXp"])
            if amount is None or abs(amount) > MAX_XP:
                raise ProgressionError("invalid_xp", "Erfahrungspunkte müssen eine ganze Zahl sein.")
            new_xp = xp + amount
        else:
            amount = _int(body["setXp"])
            if amount is None or not 0 <= amount <= MAX_XP:
                raise ProgressionError("invalid_xp", "Erfahrungspunkte müssen zwischen 0 und 10 000 000 liegen.")
            new_xp = amount
        new_xp = max(0, min(MAX_XP, new_xp))
        if new_xp != xp:
            changes.append({"type": "xp", "from": xp, "to": new_xp})
            xp = new_xp
    if "milestoneTarget" in body:
        target = body["milestoneTarget"]
        if target is not None and (_int(target) is None or not 1 <= target <= data["maxLevel"]):
            raise ProgressionError("invalid_target", f"Die Zielstufe muss zwischen 1 und {data['maxLevel']} liegen.")
        if target != prog["milestoneTarget"]:
            prog["milestoneTarget"] = target
            changes.append({"type": "milestone", "target": target})
    if not changes:
        return {"changed": False}
    block["progression"] = prog
    for change in changes:
        _log(block, {**change, "by": user_id, **({"note": note} if note else {})})
    char.xp = xp
    char.character_data = block_data
    flag_modified(char, "character_data")
    return {"changed": True}


# --------------------------------------------------------------------------- level-up

def _lookup(data):
    return {c["classKey"]: c for c in data["classes"]}


def _levels_by_class(state):
    counts = {}
    for entry in state.get("levels") or []:
        if isinstance(entry, dict):
            counts[entry.get("classKey")] = counts.get(entry.get("classKey"), 0) + 1
    return counts


def _need_count(choice, class_level):
    return choice.get("count") or (choice.get("countByLevel") or {}).get(str(class_level), 0)


def needs(data, state, evaluation, class_key):
    """What the next level of `class_key` asks the player to decide (structured for the wizard UI)."""
    classes = _lookup(data)
    entry = classes[class_key]
    counts = _levels_by_class(state)
    new_level = counts.get(class_key, 0) + 1
    new_total = (evaluation["level"] or 0) + 1
    row = entry["levels"][new_level - 1]
    con = evaluation["abilities"]["con"]["modifier"]
    chosen = (state.get("featureChoices") or {}).get(class_key) or {}
    subclasses = state.get("subclasses") or {}
    out = {
        "classKey": class_key,
        "className": entry["name"],
        "newClassLevel": new_level,
        "newTotalLevel": new_total,
        "proficiencyBonus": data["levels"][new_total - 1]["proficiencyBonus"],
        "hp": {"die": entry["hitDie"], "fixed": entry["hitDie"] // 2 + 1, "conModifier": con},
        "features": [{"id": f["id"], "name": f["name"]} for f in row.get("features") or []],
        "subclass": None,
        "advancement": None,
        "featureChoices": [],
        "expertise": None,
        "spells": None,
    }
    if new_level >= entry["subclassLevels"][0] and not subclasses.get(class_key):
        out["subclass"] = {"options": entry["subclasses"]}
    if new_level in entry["asiLevels"] or new_level == entry["epicBoonLevel"]:
        out["advancement"] = {"classLevel": new_level, "epicBoon": new_level == entry["epicBoonLevel"]}
    for choice in entry["featureChoices"]:
        if choice["level"] > new_level:
            continue
        if choice["kind"] == "expertise":
            continue
        current = chosen.get(choice["id"])
        if choice["kind"] in ("option", "feat-category"):
            if current is None:
                out["featureChoices"].append({"id": choice["id"], "kind": choice["kind"], "current": None, "need": 1})
        else:
            need = _need_count(choice, new_level)
            have = len(current) if isinstance(current, list) else 0
            if need > have:
                out["featureChoices"].append({"id": choice["id"], "kind": choice["kind"], "current": current or [], "need": need})
    def expertise_total(level):
        return sum(c.get("count", 0) for c in entry["featureChoices"] if c["kind"] == "expertise" and c["level"] <= level)

    if expertise_total(new_level) > expertise_total(new_level - 1):
        out["expertise"] = {"add": expertise_total(new_level) - expertise_total(new_level - 1), "current": (state.get("skills") or {}).get("expertise") or []}
    casting = entry["spellcasting"]
    if casting:
        crow = next(r for r in casting["levels"] if r["level"] == new_level)
        selection = (state.get("spells") or {}).get(class_key) or {}
        book = casting["spellbook"] if casting["preparation"]["mode"] == "spellbook" else None
        out["spells"] = {
            "cantrips": {"count": crow["cantrips"], "current": selection.get("cantrips") or []},
            "prepared": {"count": crow["prepared"], "current": selection.get("prepared") or []},
            "spellbook": {
                "count": book["startingSpells"] + book["perLevel"] * (new_level - 1),
                "current": selection.get("spellbook") or [],
            } if book else None,
            "maxGrade": max([g + 1 for g, n in enumerate(crow["slots"]) if n] or [0]) if casting["kind"] != "pact" else crow["slotGrade"],
        }
    return out


def _string_list(value, name):
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ProgressionError("invalid_payload", f"„{name}“ muss eine Liste von Kennungen sein.")
    return list(dict.fromkeys(value))


def build_state(data, state, payload):
    """Candidate state for one more level of `payload['classKey']`; raises ProgressionError on malformed input."""
    if not isinstance(payload, dict):
        raise ProgressionError("invalid_body", "JSON-Objekt erwartet.", 400)
    classes = _lookup(data)
    class_key = payload.get("classKey")
    counts = _levels_by_class(state)
    if class_key not in classes or class_key not in counts:
        raise ProgressionError("invalid_class", "Die Klasse gehört nicht zu diesem Charakter.")
    entry = classes[class_key]
    new = copy.deepcopy(state)
    new_level = counts[class_key] + 1
    hp = payload.get("hp", "fixed")
    if hp != "fixed" and (_int(hp) is None):
        raise ProgressionError("invalid_hp", "Trefferpunkte: „fixed“ oder der gewürfelte Wert.")
    new.setdefault("levels", []).append({"classKey": class_key, "hp": hp})

    subclass = payload.get("subclass")
    if subclass is not None:
        subclasses = new.setdefault("subclasses", {})
        if subclasses.get(class_key) and subclasses[class_key] != subclass:
            raise ProgressionError("subclass_locked", "Die Unterklasse ist bereits gewählt und kann nicht geändert werden.", 409)
        if not isinstance(subclass, str):
            raise ProgressionError("invalid_payload", "Unterklasse: Kennung erwartet.")
        subclasses[class_key] = subclass

    advancement = payload.get("advancement")
    if advancement is not None:
        if not isinstance(advancement, dict) or set(advancement) - set(ADVANCEMENT_FIELDS):
            raise ProgressionError("invalid_payload", "Ungültige Verbesserung.")
        new.setdefault("advancements", []).append({"classKey": class_key, "classLevel": new_level, **advancement})

    choices = payload.get("featureChoices")
    if choices is not None:
        if not isinstance(choices, dict):
            raise ProgressionError("invalid_payload", "Merkmalswahlen: Objekt erwartet.")
        defined = {c["id"]: c for c in entry["featureChoices"]}
        bucket = new.setdefault("featureChoices", {}).setdefault(class_key, {})
        for choice_id, value in choices.items():
            choice = defined.get(choice_id)
            if choice is None or choice["kind"] == "expertise":
                raise ProgressionError("invalid_choice", f"Unbekannte Wahl „{choice_id}“.")
            if choice["kind"] in ("option", "feat-category"):
                if bucket.get(choice_id) not in (None, value):
                    raise ProgressionError("choice_locked", f"„{choice_id}“ ist bereits gewählt und kann beim Stufenaufstieg nicht geändert werden.", 409)
                if not isinstance(value, str):
                    raise ProgressionError("invalid_payload", f"„{choice_id}“: Kennung erwartet.")
            else:
                value = _string_list(value, choice_id)
            bucket[choice_id] = value

    expertise = payload.get("expertise")
    if expertise is not None:
        expertise = _string_list(expertise, "expertise")
        skills = new.setdefault("skills", {})
        old = skills.get("expertise") or []
        if not set(old) <= set(expertise):
            raise ProgressionError("expertise_locked", "Bestehende Expertise kann beim Stufenaufstieg nicht entfernt werden.", 409)
        skills["expertise"] = expertise

    spells = payload.get("spells")
    if spells is not None:
        if not isinstance(spells, dict) or set(spells) - {"cantrips", "prepared", "spellbook"}:
            raise ProgressionError("invalid_payload", "Zauber: cantrips, prepared, spellbook erwartet.")
        bucket = new.setdefault("spells", {}).setdefault(class_key, {})
        for field, value in spells.items():
            value = _string_list(value, field)
            if field == "spellbook" and not set(bucket.get("spellbook") or []) <= set(value):
                raise ProgressionError("spellbook_locked", "Zauber im Zauberbuch bleiben beim Stufenaufstieg erhalten.", 409)
            bucket[field] = value
    return new


def preview(char, data, payload):
    """Judge a level-up without storing it. `payload` may be just {classKey} to learn what is needed."""
    block = _block(char)
    state = block.get("state") or {}
    st = status(char, data)
    if st["level"] >= st["maxLevel"]:
        raise ProgressionError("max_level", "Stufe 20 ist bereits erreicht.", 409)
    if not st["canLevelUp"]:
        raise ProgressionError("not_ready", "Für den nächsten Stufenaufstieg fehlen Erfahrungspunkte oder die Freigabe der Spielleitung.", 409, progress=st)
    old_eval = evaluate(data, state)
    candidate = build_state(data, state, payload)
    clean, problems = sanitize_state(candidate, data)
    if problems:
        raise ProgressionError("invalid_state", "Der Zustand ist ungültig.", 422, problems=problems)
    evaluation = evaluate(data, clean)
    blockers = finalize_blockers(evaluation, clean)
    return {
        "state": clean,
        "evaluation": evaluation,
        "blockers": blockers,
        "needs": needs(data, state, old_eval, payload["classKey"]),
        "hpGain": evaluation["hitPoints"]["max"] - old_eval["hitPoints"]["max"],
        "status": st,
    }


def level_up(char, data, payload, *, user_id):
    """Store one level-up (caller commits). Returns the judged result."""
    expected = payload.get("expectedLevel") if isinstance(payload, dict) else None
    if type(expected) is not int:
        raise ProgressionError("expected_level_required", "expectedLevel (die aktuelle Stufe) ist erforderlich.", 400)
    if expected != (char.level or 1):
        raise ProgressionError("level_conflict", "Die Stufe hat sich zwischenzeitlich geändert. Lade den Bogen neu.", 409)
    result = preview(char, data, payload)
    if result["blockers"]:
        raise ProgressionError("level_up_incomplete", "Der Stufenaufstieg ist noch nicht vollständig oder verstößt gegen Regeln.", 422, blockers=result["blockers"])
    evaluation = result["evaluation"]
    state = result["state"]
    old_level, old_hp_max = char.level or 1, char.hp_max or 0
    new_data = copy.deepcopy(char.character_data)
    block = new_data["srd"]
    block["state"] = state
    block["derived"] = evaluation
    _log(block, {
        "type": "level-up", "by": user_id, "classKey": payload["classKey"],
        "fromLevel": old_level, "toLevel": evaluation["level"], "hpGain": result["hpGain"],
    })
    char.level = evaluation["level"]
    char.class_name = class_label(evaluation)[:50]
    char.ac = evaluation["armorClass"]["value"]
    char.hp_max = evaluation["hitPoints"]["max"]
    char.hp_current = max(0, min(char.hp_max, (char.hp_current or 0) + (char.hp_max - old_hp_max)))
    for ability in ("str", "dex", "con", "int", "wis", "cha"):
        setattr(char, f"{ability}_score", evaluation["abilities"][ability]["score"])
    char.proficiency_bonus = evaluation["proficiencyBonus"]
    char.xp = max(char.xp or 0, _threshold(data, evaluation["level"]))
    char.character_data = new_data
    flag_modified(char, "character_data")
    return result
