"""Pure mechanics for the private homebrew test adapter; never writes VTT sheets."""

from copy import deepcopy

from vtt.creation_engine.compiler import homebrew as h
from vtt.creation_engine.compiler.flame import integer, object_schema
from vtt.creation_engine.compiler.interview import StrictValidator
from vtt.creation_engine.kernel.records import refuse

CONTRACT = "homebrew-sandbox:1"
RUNTIME = "dnd5e.homebrew-test:1"
ID = {"type": "string", "pattern": r"^[A-Za-z0-9._:-]{1,128}$"}
REF = object_schema({"kind": {"const": "revision"}, "id": ID, "definitionId": ID,
                     "digest": {"type": "string", "pattern": r"^sha256:[a-f0-9]{64}$"}})
CHOICES = {"type": "object", "maxProperties": 200,
           "propertyNames": {"pattern": r"^(class|race)/[a-z][a-z0-9_.-]{0,63}/[a-z][a-z0-9_.-]{0,63}$"},
           "additionalProperties": h.array(h.IDENTIFIER, 10)}
BUILD = object_schema({"name": h.NAME, "classRevision": ID, "raceRevision": ID, "level": integer(1, 20),
    "baseScores": object_schema({a: integer(1, 30) for a in h.ABILITIES}),
    "baseAc": integer(0, 100), "baseHp": integer(1, 10000), "choices": CHOICES})
PAYLOADS = {
    "CreateSandbox": object_schema({"edition": {"enum": list(h.EDITIONS)}, "revisions": h.array(REF, 64, 3)}),
    "BuildCharacter": BUILD,
    "RebuildCharacter": object_schema({"characterId": ID, "build": BUILD}),
    "CastSpell": object_schema({"casterId": ID, "targetId": ID, "spellKey": h.IDENTIFIER,
        "castLevel": integer(0, 9), "distanceFeet": integer(0, 10000),
        "adjudication": object_schema({"timingSatisfied": {"const": True}, "componentsSatisfied": {"const": True}})}),
    "AdvanceRounds": object_schema({"rounds": integer(1, 10000)}),
    "RecoverResources": object_schema({"characterId": ID, "event": {"enum": ["short_rest", "long_rest", "manual"]},
                                       "reason": h.NAME}),
    "EndConcentration": object_schema({"characterId": ID, "reason": h.NAME}),
    "ResolveConcentration": object_schema({"characterId": ID, "maintained": {"type": "boolean"}, "reason": h.NAME}),
}


def command_schema(operation):
    props = {"contractVersion": {"const": CONTRACT}, "idempotencyKey": ID,
             "operation": {"const": operation}, "payload": PAYLOADS[operation]}
    if operation != "CreateSandbox":
        props.update(sandboxId=ID, expectedVersion=integer(1, 2**53-1))
    return object_schema(props)


def validate_command(value):
    if not isinstance(value, dict) or not isinstance(value.get("operation"), str) or value["operation"] not in PAYLOADS:
        refuse("SCHEMA_INVALID")
    if not StrictValidator(command_schema(value["operation"])).is_valid(value):
        refuse("SCHEMA_INVALID")


def _document(documents, revision_id, kind):
    document = documents.get(revision_id)
    if document is None or document["kind"] != kind:
        refuse("REVISION_NOT_IN_LOCK")
    return document["content"]


def spell_catalog(documents):
    return {d["content"]["spell"]["key"]: {"revisionId": key, **d["content"]}
            for key, d in documents.items() if d["kind"] == "spell"}


def build_character(build, documents, *, previous=None):
    """Recompute contributions from retained bases; keep spent resources spent."""
    clazz = _document(documents, build["classRevision"], "class")
    race = _document(documents, build["raceRevision"], "race")
    levels = clazz["class"]["levels"]
    if build["level"] > len(levels):
        refuse("CLASS_LEVEL_UNSUPPORTED")
    active_levels = levels[:build["level"]]
    features = [("race", feature) for feature in race["race"]["features"]]
    features += [("class", feature) for level in active_levels for feature in level["features"]]
    grants, expected_choices = [], set()
    for kind, feature in features:
        source = f"{kind}/{feature['id']}"
        grants.append({"source": source, "name": feature["name"], "values": feature["grants"]})
        for choice in feature["choices"]:
            key = source + "/" + choice["id"]
            expected_choices.add(key)
            selected = build["choices"].get(key)
            options = {option["id"]: option for option in choice["options"]}
            if (selected is None or len(selected) != choice["count"] or len(set(selected)) != len(selected)
                    or any(option not in options for option in selected)):
                refuse("CHOICE_REQUIRED")
            for option in selected:
                grants.append({"source": key + "/" + option, "name": options[option]["name"], "values": options[option]["grants"]})
    if set(build["choices"]) != expected_choices:
        refuse("CHOICE_INVALID")
    stats = {**build["baseScores"], "ac": build["baseAc"], "hpMax": build["baseHp"] + sum(l["hpGain"] for l in active_levels),
             "speed": race["race"]["speed"]}
    sets = {"proficiencies": {}, "resistances": {}, "spells": {}}
    resources = {}
    for grant in grants:
        values, source = grant["values"], grant["source"]
        for stat, amount in values["modifiers"].items():
            stats[stat] += amount
        for key in sets:
            for value in values[key]:
                sets[key].setdefault(value, []).append(source)
        for resource in values["resources"]:
            row = resources.setdefault(resource["id"], {"maximum": 0, "recovery": resource["recovery"], "sources": []})
            if row["recovery"] != resource["recovery"]:
                refuse("RESOURCE_RECOVERY_CONFLICT")
            row["maximum"] += resource["maximum"]
            row["sources"].append(source)
    if any(not 1 <= stats[a] <= 30 for a in h.ABILITIES) or not 1 <= stats["hpMax"] <= 30000 or not 0 <= stats["ac"] <= 100 or not 0 <= stats["speed"] <= 10000:
        refuse("RESOURCE_BOUND_EXCEEDED")
    if set(sets["spells"]) - spell_catalog(documents).keys():
        refuse("SPELL_NOT_IN_LOCK")
    for key, resource in resources.items():
        if resource["maximum"] > 10000:
            refuse("RESOURCE_BOUND_EXCEEDED")
        current = previous["resources"].get(key, {}).get("current", 0) if previous else resource["maximum"]
        resource["current"] = min(current, resource["maximum"])
    return {"name": build["name"], "build": deepcopy(build), "className": clazz["name"], "raceName": race["name"],
            "creatureType": race["race"]["creatureType"], "size": race["race"]["size"], "level": build["level"],
            "stats": stats, "hp": min(previous["hp"], stats["hpMax"]) if previous else stats["hpMax"],
            "proficiencyBonus": 2 + (build["level"]-1)//4, **sets, "resources": resources, "grants": grants}


def actor(state, identifier):
    value = state["characters"].get(identifier)
    if value is None:
        refuse("NOT_FOUND")
    return value


def current_stat(state, identifier, stat):
    base = actor(state, identifier)["stats"][stat]
    # One exact revision per spell key is pinned in the scope. Multiple casters
    # of that same spell do not multiply its modifier; independent durations stay
    # recorded so another application can remain after one concentration ends.
    active = {e["spellKey"]: e["amount"] for e in state["effects"] if e["targetId"] == identifier and e["stat"] == stat}
    return max(0, base + sum(active.values()))


def end_concentration(state, caster_id):
    removed = [e["id"] for e in state["effects"] if e["casterId"] == caster_id and e["concentration"]]
    state["effects"] = [e for e in state["effects"] if e["id"] not in removed]
    return removed


def execute(state, documents, operation, payload, *, new_id, roll):
    """Caller owns transaction, receipt and RNG recording. Mutates private state."""
    pending = state.get("pendingConcentration")
    if pending:
        if operation != "ResolveConcentration":
            refuse("SCOPE_BUSY")
        if payload["characterId"] != pending["characterId"]:
            refuse("DECISION_STALE")
        removed = [] if payload["maintained"] else end_concentration(state, payload["characterId"])
        state["pendingConcentration"] = None
        return {"maintained": payload["maintained"], "removedEffects": removed, "decision": pending}
    if operation == "ResolveConcentration":
        refuse("DECISION_STALE")
    if operation in {"BuildCharacter", "RebuildCharacter"}:
        if operation == "BuildCharacter":
            if len(state["characters"]) >= 32:
                refuse("BUDGET_EXCEEDED")
            identifier, build, old = new_id("hbactor"), payload, None
        else:
            identifier, build = payload["characterId"], payload["build"]
            old = actor(state, identifier)
        character = build_character(build, documents, previous=old)
        state["characters"][identifier] = character
        # Rebuild cannot rewind cast outcomes. End effects cast using lost grants.
        state["effects"] = [e for e in state["effects"] if e["casterId"] != identifier or e["spellKey"] in character["spells"]]
        return {"characterId": identifier, "character": deepcopy(character)}
    if operation == "AdvanceRounds":
        state["round"] += payload["rounds"]
        expired = [e["id"] for e in state["effects"] if e["expiresAtRound"] <= state["round"]]
        state["effects"] = [e for e in state["effects"] if e["id"] not in expired]
        return {"round": state["round"], "expiredEffects": expired}
    if operation == "EndConcentration":
        actor(state, payload["characterId"])
        return {"removedEffects": end_concentration(state, payload["characterId"])}
    if operation == "RecoverResources":
        character = actor(state, payload["characterId"])
        changed = {}
        for key, resource in character["resources"].items():
            if resource["recovery"] == payload["event"] or payload["event"] == "long_rest" and resource["recovery"] == "short_rest":
                changed[key] = resource["maximum"] - resource["current"]
                resource["current"] = resource["maximum"]
        return {"recovered": changed}
    if operation != "CastSpell":
        refuse("SEMANTIC_INVALID")
    return cast(state, documents, payload, new_id=new_id, roll=roll)


def cast(state, documents, payload, *, new_id, roll):
    caster_id, target_id, key = payload["casterId"], payload["targetId"], payload["spellKey"]
    caster, target = actor(state, caster_id), actor(state, target_id)
    spell = spell_catalog(documents).get(key)
    if spell is None or key not in caster["spells"]:
        refuse("SPELL_NOT_KNOWN")
    s = spell["spell"]
    if caster["hp"] == 0:
        refuse("CASTER_INCAPACITATED")
    if payload["castLevel"] < s["level"] or s["level"] == 0 and payload["castLevel"] != 0:
        refuse("SPELL_LEVEL_INVALID")
    if (s["target"] == "self" and target_id != caster_id or
            caster_id == target_id and payload["distanceFeet"] != 0 or payload["distanceFeet"] > s["rangeFeet"]):
        refuse("SPELL_TARGET_INVALID")
    higher = payload["castLevel"] - s["level"]
    cost = s["cost"]["amount"] + higher * s["upcast"]["costPerLevel"]
    resource = caster["resources"].get(s["cost"]["resource"])
    if cost and (resource is None or resource["current"] < cost):
        refuse("RESOURCE_BOUND_EXCEEDED")
    # Validate before spending or drawing. Committed misses still spend the cost.
    if cost:
        resource["current"] -= cost
    result = {"spellKey": key, "revisionId": spell["revisionId"], "cost": cost,
              "resource": s["cost"]["resource"], "hit": True, "saved": False, "critical": False,
              "hpDelta": 0, "concentrationCheckRequired": None}
    resolution = s["resolution"]
    if resolution["kind"] == "attack":
        die = roll(20)
        bonus = (caster["stats"][resolution["ability"]]-10)//2 + caster["proficiencyBonus"]
        result.update(attackRoll=die, attackTotal=die+bonus, critical=die == 20,
                      hit=die == 20 or die != 1 and die+bonus >= current_stat(state, target_id, "ac"))
    elif resolution["kind"] == "save":
        ability = resolution["saveAbility"]
        dc = 8 + (caster["stats"][resolution["ability"]]-10)//2 + caster["proficiencyBonus"]
        die = roll(20)
        total = die + (target["stats"][ability]-10)//2 + (target["proficiencyBonus"] if "save."+ability in target["proficiencies"] else 0)
        result.update(saveRoll=die, saveTotal=total, saveDC=dc, saved=total >= dc)
    effect = s["effect"]
    if effect["kind"] == "modifier":
        if s["concentration"]:
            result["replacedConcentration"] = end_concentration(state, caster_id)
        state["effects"] = [e for e in state["effects"] if not (e["casterId"] == caster_id and e["spellKey"] == key)]
        entry = {"id": new_id("hbeffect"), "casterId": caster_id, "targetId": target_id, "spellKey": key,
                 "stat": effect["stat"], "amount": effect["amount"], "concentration": s["concentration"],
                 "expiresAtRound": state["round"] + s["durationRounds"]}
        state["effects"].append(entry)
        result["effect"] = entry
    elif result["hit"] and not (result["saved"] and not resolution.get("halfOnSave", False)):
        dice = effect["dice"]
        count = (dice["count"] + higher*s["upcast"]["dicePerLevel"]) * (2 if result["critical"] else 1)
        amount = sum(roll(dice["sides"]) for _ in range(count)) + dice["bonus"]
        if result["saved"]:
            amount //= 2
        before = target["hp"]
        if effect["kind"] == "damage":
            if effect["damageType"] in target["resistances"]:
                amount //= 2
            target["hp"] = max(0, before-amount)
            if target["hp"] == 0:
                result["endedConcentration"] = end_concentration(state, target_id)
            elif amount and any(e["casterId"] == target_id and e["concentration"] for e in state["effects"]):
                result["concentrationCheckRequired"] = {"characterId": target_id, "dc": max(10, amount//2)}
                state["pendingConcentration"] = result["concentrationCheckRequired"]
        else:
            target["hp"] = min(target["stats"]["hpMax"], before+amount)
        result.update(amount=amount, hpDelta=target["hp"]-before, targetHp=target["hp"])
    return result
