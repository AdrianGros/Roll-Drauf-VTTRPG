"""Explicit fictional author choices used by backend end-to-end fixtures."""

from copy import deepcopy

from vtt.creation_engine.compiler import homebrew as h


def grants(**values):
    return {"modifiers": {}, "proficiencies": [], "resistances": [], "resources": [], "spells": [], **values}


def feature(key, **values):
    return {"id": key, "name": key.title(), "description": "An explicitly authored test feature.",
            "grants": grants(**values), "choices": []}


def examples():
    choice = {"id": "training", "name": "Training", "count": 1, "options": [
        {"id": "mind", "name": "Mind", "grants": grants(modifiers={"int": 2}, proficiencies=["arcana"])},
        {"id": "body", "name": "Body", "grants": grants(modifiers={"con": 2})}]}
    race_feature = feature("echo", modifiers={"dex": 1}, proficiencies=["arcana"], resistances=["cold"])
    race_feature["choices"] = [choice]
    clazz = {"name": "Lantern keeper", "class": {"edition": "dnd5e_2024", "hitDie": 8, "levels": [
        {"level": 1, "hpGain": 8, "features": [feature("spark", proficiencies=["arcana", "save.con"],
            resources=[{"id": "mana", "maximum": 10, "recovery": "long_rest"}], spells=["ember", "mend", "ward"])]},
        {"level": 2, "hpGain": 5, "features": [feature("reservoir", modifiers={"ac": 1},
            resources=[{"id": "mana", "maximum": 5, "recovery": "long_rest"}])]}]}}
    race = {"name": "Echo folk", "race": {"edition": "dnd5e_2024", "creatureType": "Humanoid", "size": "medium",
        "speed": 30, "features": [race_feature]}}
    spell = {"name": "Ember thread", "spell": {"edition": "dnd5e_2024", "key": "ember", "level": 1,
        "school": "Evocation", "castingTime": "action", "components": "V, S", "target": "single", "rangeFeet": 60,
        "cost": {"resource": "mana", "amount": 2}, "resolution": {"kind": "automatic"},
        "effect": {"kind": "damage", "dice": {"count": 2, "sides": 6, "bonus": 1}, "damageType": "fire"},
        "durationRounds": 0, "concentration": False, "upcast": {"dicePerLevel": 1, "costPerLevel": 1}}}
    healing = deepcopy(spell)
    healing["name"] = "Mending light"
    healing["spell"].update(key="mend", effect={"kind": "healing", "dice": {"count": 1, "sides": 6, "bonus": 2}})
    ward = deepcopy(spell)
    ward["name"] = "Lantern ward"
    ward["spell"].update(key="ward", target="self", rangeFeet=0, effect={"kind": "modifier", "stat": "ac", "amount": 3},
        concentration=True, durationRounds=2, upcast={"dicePerLevel": 0, "costPerLevel": 0})
    return [(h.CLASS, clazz), (h.RACE, race), (h.SPELL, spell), (h.SPELL, healing), (h.SPELL, ward)]


def build(class_id="class:fixture", race_id="race:fixture", **values):
    return {"name": "Test hero", "classRevision": class_id, "raceRevision": race_id, "level": 1,
            "baseScores": {"str": 10, "dex": 12, "con": 12, "int": 14, "wis": 10, "cha": 10},
            "baseAc": 12, "baseHp": 10, "choices": {"race/echo/training": ["mind"]}, **values}


def documents():
    keys = ["class:fixture", "race:fixture", "spell:ember", "spell:mend", "spell:ward"]
    return {key: {"kind": h.KINDS[kind], "content": value} for key, (kind, value) in zip(keys, examples())}
