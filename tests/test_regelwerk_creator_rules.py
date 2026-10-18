"""Rules engine for SRD 5.2.1 characters: worked examples per class (hand-computed), all ability methods,
multiclass spell slots, advancement checks and manual overrides."""

from __future__ import annotations

import copy

import pytest

from vtt.rules_content.creator_rules import (
    ABILITY_IDS,
    ability_modifier,
    caster_level,
    evaluate,
    level_for_xp,
    load_creator_data,
    point_buy_cost,
    roll_total,
)

SPECIES = "character-origins.species."
BACKGROUND = "character-origins.backgrounds."
ARMOR = "equipment.armor."


@pytest.fixture(scope="module")
def data():
    return load_creator_data()


@pytest.fixture(scope="module")
def classes(data):
    return {entry["classKey"]: entry for entry in data["classes"]}


def scores(**values):
    base = {"str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10}
    base.update(values)
    return base


def make(class_levels, abilities, background, bonus, species="halfling", **extra):
    """class_levels: list of (classKey, count) in the order the levels were taken."""
    levels = [{"classKey": key} for key, count in class_levels for _ in range(count)]
    state = {
        "abilityMethod": "manual",
        "abilityBase": abilities,
        "levels": levels,
        "background": {"id": BACKGROUND + background, "abilityBonus": bonus},
        "species": {"id": SPECIES + species, "choices": {}},
    }
    state.update(extra)
    return state


def codes(result, severity=None):
    return {f["code"] for f in result["findings"] if severity is None or f["severity"] == severity}


def pick_spells(data, class_key, level, count, exact=False):
    names = [sid for sid in data["spellLists"][class_key] if (data["spells"][sid]["level"] == level if exact else 1 <= data["spells"][sid]["level"] <= level)]
    return names[:count]


# ---------------------------------------------------------------------------- pure helpers

def test_ability_modifier_table():
    assert [ability_modifier(s) for s in (1, 8, 9, 10, 11, 12, 15, 20, 30)] == [-5, -1, -1, 0, 0, 1, 2, 5, 10]


def test_level_for_xp_matches_table(data):
    assert [level_for_xp(data, xp) for xp in (0, 299, 300, 6499, 6500, 355000, 999999)] == [1, 1, 2, 4, 5, 20, 20]


def test_point_buy_costs(data):
    assert point_buy_cost(data, [15, 15, 15, 8, 8, 8]) == 27
    assert point_buy_cost(data, [13, 13, 13, 12, 12, 12]) == 27
    assert point_buy_cost(data, [16, 8, 8, 8, 8, 8]) is None


def test_roll_total_drops_lowest():
    assert roll_total([6, 5, 4, 1]) == 15
    assert roll_total([1, 1, 1, 1]) == 3


def test_caster_level_rule(data):
    assert caster_level(data, {"wizard": 3, "fighter": 3}) == 3
    assert caster_level(data, {"paladin": 3, "ranger": 3}) == 3
    assert caster_level(data, {"paladin": 1}) == 1
    assert caster_level(data, {"paladin": 3, "wizard": 3}) == 5
    assert caster_level(data, {"warlock": 10}) == 0


# ---------------------------------------------------------------------------- worked examples per class

def test_fighter_5_dwarf_soldier_in_plate_and_shield(data):
    state = make(
        [("fighter", 5)], scores(str=15, dex=14, con=13, int=10, wis=12, cha=8), "soldier", {"str": 2, "con": 1}, "dwarf",
        skills={"class": ["akrobatik", "wahrnehmung"]},
        equipment={"armor": ARMOR + "armor-heavy.kettenpanzer", "shield": True},
    )
    result = evaluate(data, state)
    assert result["valid"] and not result["complete"]
    assert {a: result["abilities"][a]["score"] for a in ABILITY_IDS} == {"str": 17, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8}
    assert result["proficiencyBonus"] == 3
    # 10 + 2 (level 1), 4 x (6 + 2) = 32, dwarven toughness +5
    assert result["hitPoints"]["max"] == 12 + 32 + 5
    assert result["hitDice"] == {"d10": 5}
    assert result["armorClass"]["value"] == 16 + 2
    assert result["initiative"] == 2
    assert result["speedMeters"] == 9.0
    assert result["saves"]["str"] == {"proficient": True, "bonus": 3 + 3}
    assert result["saves"]["con"] == {"proficient": True, "bonus": 2 + 3}
    assert result["saves"]["dex"] == {"proficient": False, "bonus": 2}
    assert result["skills"]["athletik"]["bonus"] == 3 + 3
    assert result["skills"]["akrobatik"]["bonus"] == 2 + 3
    assert result["passivePerception"] == 10 + 1 + 3
    assert result["spellcasting"]["classes"] == {} and result["spellcasting"]["slots"] is None
    assert {"advancement-missing", "subclass-missing"} <= codes(result, "incomplete")


def test_wizard_5_halfling_sage_complete_sheet(data, classes):
    cantrips = [sid for sid in data["spellLists"]["wizard"] if data["spells"][sid]["level"] == 0][:4]
    book = pick_spells(data, "wizard", 3, 14)
    state = make(
        [("wizard", 5)], scores(int=15, wis=14, con=13, dex=12, cha=10, str=8), "sage", {"int": 2, "con": 1},
        subclasses={"wizard": "classes.wizard.subclass-evoker"},
        skills={"class": ["heilkunde", "nachforschungen"], "expertise": ["arkane-kunde"]},
        advancements=[{"classKey": "wizard", "classLevel": 4, "kind": "asi", "increases": {"int": 2}}],
        spells={"wizard": {"cantrips": cantrips, "spellbook": book, "prepared": book[:9]}},
    )
    result = evaluate(data, state)
    assert result["findings"] == [] or codes(result, "error") == set(), result["findings"]
    assert result["complete"], [f for f in result["findings"] if f["severity"] in {"error", "incomplete"}]
    assert result["abilities"]["int"] == {"base": 15, "bonus": 4, "score": 19, "modifier": 4}
    assert result["hitPoints"]["max"] == 8 + 4 * (4 + 2)
    assert result["hitDice"] == {"d6": 5}
    assert result["armorClass"]["value"] == 11
    assert result["saves"]["int"]["bonus"] == 4 + 3 and result["saves"]["wis"]["bonus"] == 2 + 3
    assert result["skills"]["arkane-kunde"] == {"name": "Arkane Kunde", "ability": "int", "proficiency": "expertise", "bonus": 4 + 6}
    assert result["skills"]["geschichte"]["proficiency"] == "proficient"
    assert result["passivePerception"] == 12
    wizard = result["spellcasting"]["classes"]["wizard"]
    assert (wizard["saveDc"], wizard["attackBonus"], wizard["cantrips"], wizard["prepared"], wizard["maxGrade"]) == (15, 7, 4, 9, 3)
    assert result["spellcasting"]["slots"] == [4, 3, 2, 0, 0, 0, 0, 0, 0]


def test_barbarian_5_orc_unarmored_defense_and_fast_movement(data):
    state = make([("barbarian", 5)], scores(str=15, con=14, dex=13, wis=12), "soldier", {"str": 2, "con": 1}, "orc")
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == 14 + 4 * (7 + 2)
    assert result["armorClass"]["value"] == 10 + 1 + 2
    assert "barbarian-unarmored-defense" in result["armorClass"]["formula"]
    assert result["speedMeters"] == 9.0 + 3.0
    assert result["saves"]["str"]["bonus"] == 3 + 3 and result["saves"]["con"]["bonus"] == 2 + 3
    with_shield = evaluate(data, {**state, "equipment": {"shield": True}})
    assert with_shield["armorClass"]["value"] == 15


def test_barbarian_fast_movement_lost_in_heavy_armor(data):
    state = make([("barbarian", 5)], scores(str=15, con=14, dex=13), "soldier", {"str": 2, "con": 1}, "orc", equipment={"armor": ARMOR + "armor-heavy.ringpanzer"})
    result = evaluate(data, state)
    assert result["speedMeters"] == 9.0
    assert result["armorClass"]["value"] == 14


def test_monk_5_unarmored_defense_and_movement(data):
    state = make([("monk", 5)], scores(dex=15, wis=14, con=13, str=12), "criminal", {"dex": 2, "con": 1})
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == 10 + 4 * (5 + 2)
    assert result["armorClass"]["value"] == 10 + 3 + 2
    assert result["speedMeters"] == 9.0 + 3.0
    assert result["saves"]["str"]["proficient"] and result["saves"]["dex"]["bonus"] == 3 + 3
    shielded = evaluate(data, {**state, "equipment": {"shield": True}})
    assert shielded["speedMeters"] == 9.0
    assert shielded["armorClass"]["value"] == 10 + 3 + 2
    assert "monk-unarmored-defense" not in shielded["armorClass"]["formula"] and "Schild" in shielded["armorClass"]["formula"]


def test_warlock_5_pact_magic(data):
    state = make([("warlock", 5)], scores(cha=15, dex=14, con=13, int=12, wis=10, str=8), "acolyte", {"cha": 2, "wis": 1})
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == 9 + 4 * (5 + 1)
    warlock = result["spellcasting"]["classes"]["warlock"]
    assert (warlock["saveDc"], warlock["attackBonus"], warlock["cantrips"], warlock["prepared"], warlock["maxGrade"]) == (14, 6, 3, 6, 3)
    assert result["spellcasting"]["pact"] == {"slots": 2, "grade": 3}
    assert result["spellcasting"]["slots"] is None and result["spellcasting"]["casterLevel"] == 0


def test_sorcerer_5_draconic_resilience(data):
    state = make(
        [("sorcerer", 5)], scores(cha=15, con=14, dex=13, int=8, wis=12), "acolyte", {"cha": 2, "wis": 1},
        subclasses={"sorcerer": "classes.sorcerer.subclass-draconic"},
    )
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == 8 + 4 * (4 + 2) + (3 + 2)
    assert result["armorClass"]["value"] == 10 + 1 + 3
    plain = evaluate(data, {**state, "subclasses": {}})
    assert plain["hitPoints"]["max"] == 8 + 4 * (4 + 2)
    assert plain["armorClass"]["value"] == 11


def test_paladin_5_heavy_armor_and_half_caster_slots(data):
    state = make(
        [("paladin", 5)], scores(str=15, cha=14, con=13, wis=12, dex=10, int=8), "soldier", {"str": 2, "con": 1},
        equipment={"armor": ARMOR + "armor-heavy.ritterruestung", "shield": True},
    )
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == 12 + 4 * (6 + 2)
    assert result["armorClass"]["value"] == 18 + 2
    assert "armor-untrained" not in codes(result) and "armor-strength" not in codes(result)
    paladin = result["spellcasting"]["classes"]["paladin"]
    assert (paladin["saveDc"], paladin["attackBonus"], paladin["cantrips"], paladin["prepared"]) == (8 + 3 + 2, 3 + 2, 0, 6)
    assert result["spellcasting"]["slots"] == [4, 2, 0, 0, 0, 0, 0, 0, 0]
    assert result["saves"]["wis"]["bonus"] == 1 + 3 and result["saves"]["cha"]["bonus"] == 2 + 3


def test_rogue_5_expertise_and_light_armor(data):
    state = make(
        [("rogue", 5)], scores(dex=15, int=14, con=13, str=12, wis=10, cha=8), "criminal", {"dex": 2, "con": 1},
        skills={"class": ["akrobatik", "wahrnehmung", "taeuschen", "ueberzeugen"], "expertise": ["heimlichkeit", "fingerfertigkeit"]},
        equipment={"armor": ARMOR + "armor-light.lederruestung"},
    )
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == 10 + 4 * (5 + 2)
    assert result["armorClass"]["value"] == 11 + 3
    # dex +3, plus the Criminal origin feat "Wachsam" (Alert) adds the proficiency bonus
    assert result["initiative"] == 3 + 3
    assert result["skills"]["heimlichkeit"]["bonus"] == 3 + 6
    assert result["skills"]["akrobatik"]["bonus"] == 3 + 3
    assert result["saves"]["dex"]["bonus"] == 3 + 3 and result["saves"]["int"]["bonus"] == 2 + 3
    assert "expertise-missing" not in codes(result) and "expertise-extra" not in codes(result)


@pytest.mark.parametrize("key,die", [
    ("barbarian", 12), ("bard", 8), ("cleric", 8), ("druid", 8), ("fighter", 10), ("monk", 8),
    ("paladin", 10), ("ranger", 10), ("rogue", 8), ("sorcerer", 6), ("warlock", 8), ("wizard", 6),
])
def test_every_class_level_1_and_standard_array(data, classes, key, die):
    entry = classes[key]
    state = {"abilityMethod": "standard-array", "abilityBase": entry["standardAbilityScores"], "levels": [{"classKey": key}]}
    result = evaluate(data, state)
    assert "standard-array" not in codes(result, "error")
    con = ability_modifier(entry["standardAbilityScores"]["con"])
    assert result["hitPoints"]["max"] == die + con
    assert result["hitDice"] == {f"d{die}": 1}
    assert {a for a, row in result["saves"].items() if row["proficient"]} == set(entry["savingThrows"])
    assert result["proficiencyBonus"] == 2


# ---------------------------------------------------------------------------- all classes, all levels

@pytest.mark.parametrize("key", ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"])
def test_every_class_every_level_is_consistent_with_class_table(data, classes, key):
    entry = classes[key]
    con = 14
    for level in range(1, 21):
        state = {"abilityMethod": "manual", "abilityBase": scores(con=con), "levels": [{"classKey": key}] * level}
        result = evaluate(data, state)
        die = entry["hitDie"]
        assert result["hitPoints"]["max"] == (die + 2) + (level - 1) * (die // 2 + 1 + 2), (key, level)
        assert result["proficiencyBonus"] == entry["levels"][level - 1]["proficiencyBonus"]
        assert result["level"] == level
        casting = entry["spellcasting"]
        if casting and casting["kind"] in {"full", "half"}:
            row = casting["levels"][level - 1]
            slots = result["spellcasting"]["slots"]
            assert slots[: len(row["slots"])] == row["slots"], (key, level)
            assert not any(slots[len(row["slots"]):])
            assert result["spellcasting"]["classes"][key]["cantrips"] == row["cantrips"]
            assert result["spellcasting"]["classes"][key]["prepared"] == row["prepared"]
        if casting and casting["kind"] == "pact":
            row = casting["levels"][level - 1]
            assert result["spellcasting"]["pact"] == {"slots": row["slots"], "grade": row["slotGrade"]}


def test_warlock_pact_table_matches_printed_example(data, classes):
    rows = classes["warlock"]["spellcasting"]["levels"]
    assert (rows[4]["slots"], rows[4]["slotGrade"]) == (2, 3)
    assert (rows[10]["slots"], rows[10]["slotGrade"]) == (3, 5)
    assert (rows[16]["slots"], rows[16]["slotGrade"]) == (4, 5)
    assert [r["slotGrade"] for r in rows] == sorted(r["slotGrade"] for r in rows)
    assert classes["warlock"]["spellcasting"]["sourceNotes"][0]["kind"] == "source-defect"


# ---------------------------------------------------------------------------- multiclassing

def test_multiclass_fighter_wizard_slots_and_hit_dice(data):
    state = make([("fighter", 3), ("wizard", 3)], scores(str=15, dex=12, con=14, int=13), "sage", {"int": 2, "con": 1})
    result = evaluate(data, state)
    assert result["level"] == 6 and result["proficiencyBonus"] == 3
    assert result["hitDice"] == {"d10": 3, "d6": 3}
    assert result["spellcasting"]["casterLevel"] == 3
    assert result["spellcasting"]["slots"] == [4, 2, 0, 0, 0, 0, 0, 0, 0]
    # level 1 fighter: 10 + 2, then fighters 2-3: 6 + 2 each, wizard 4-6: 4 + 2 each
    assert result["hitPoints"]["max"] == 12 + 2 * 8 + 3 * 6
    assert [c["classKey"] for c in result["classes"]] == ["fighter", "wizard"]
    assert result["saves"]["str"]["proficient"] and not result["saves"]["int"]["proficient"]


def test_multiclass_combined_half_caster_levels(data):
    state = make([("paladin", 3), ("ranger", 3)], scores(str=14, cha=14, dex=14, wis=14, con=12), "soldier", {"str": 2, "con": 1})
    result = evaluate(data, state)
    assert result["spellcasting"]["casterLevel"] == 3
    assert result["spellcasting"]["slots"][:2] == [4, 2]
    mixed = evaluate(data, make([("paladin", 3), ("wizard", 3)], scores(str=14, cha=14, int=14, con=12), "soldier", {"str": 2, "con": 1}))
    assert mixed["spellcasting"]["casterLevel"] == 5
    assert mixed["spellcasting"]["slots"] == [4, 3, 2, 0, 0, 0, 0, 0, 0]


def test_multiclass_pact_slots_stay_separate(data):
    state = make([("wizard", 3), ("warlock", 2)], scores(int=14, cha=14, con=12), "sage", {"int": 2, "con": 1})
    result = evaluate(data, state)
    assert result["spellcasting"]["slots"] == [4, 2, 0, 0, 0, 0, 0, 0, 0]
    assert result["spellcasting"]["pact"] == {"slots": 2, "grade": 1}
    assert result["hitDice"] == {"d6": 3, "d8": 2}


def test_multiclass_prerequisite_uses_primary_abilities(data):
    ok = evaluate(data, make([("fighter", 1), ("wizard", 1)], scores(str=13, int=13, con=10), "soldier", {"str": 2, "con": 1}))
    assert "multiclass-prerequisite" not in codes(ok)
    low = evaluate(data, make([("fighter", 1), ("wizard", 1)], scores(str=13, int=12, con=10), "soldier", {"str": 2, "con": 1}))
    assert "multiclass-prerequisite" in codes(low, "error")
    paladin = evaluate(data, make([("paladin", 1), ("fighter", 1)], scores(str=15, cha=12, con=10), "soldier", {"str": 2, "con": 1}))
    assert "multiclass-prerequisite" in codes(paladin, "error")
    single = evaluate(data, make([("wizard", 3)], scores(int=8), "sage", {"int": 2, "con": 1}))
    assert "multiclass-prerequisite" not in codes(single)


def test_multiclass_armor_training_grants(data):
    base = make([("wizard", 1), ("fighter", 1)], scores(int=13, str=13, con=10), "sage", {"int": 2, "con": 1}, equipment={"armor": ARMOR + "armor-medium.kettenhemd"})
    assert "armor-untrained" not in codes(evaluate(data, base))
    wizard_only = make([("wizard", 2)], scores(int=13, con=10), "sage", {"int": 2, "con": 1}, equipment={"armor": ARMOR + "armor-medium.kettenhemd"})
    assert "armor-untrained" in codes(evaluate(data, wizard_only), "warning")


def test_multiclass_experience_total_level_sets_proficiency(data):
    state = make([("fighter", 4), ("rogue", 1)], scores(dex=14, str=14, con=10), "criminal", {"dex": 2, "con": 1})
    assert evaluate(data, state)["proficiencyBonus"] == 3


# ---------------------------------------------------------------------------- ability score methods

def test_standard_array_accepts_any_assignment_and_rejects_others(data):
    good = make([("fighter", 1)], dict(zip(ABILITY_IDS, [8, 10, 12, 13, 14, 15])), "soldier", {"str": 2, "con": 1})
    good["abilityMethod"] = "standard-array"
    assert "standard-array" not in codes(evaluate(data, good))
    bad = copy.deepcopy(good)
    bad["abilityBase"]["str"] = 15
    bad["abilityBase"]["dex"] = 15
    assert "standard-array" in codes(evaluate(data, bad), "error")


def test_point_buy(data):
    state = make([("fighter", 1)], dict(zip(ABILITY_IDS, [15, 15, 15, 8, 8, 8])), "soldier", {"str": 2, "con": 1})
    state["abilityMethod"] = "point-buy"
    assert not codes(evaluate(data, state)) & {"point-buy-budget", "point-buy-range", "point-buy-unspent"}
    over = copy.deepcopy(state)
    over["abilityBase"]["int"] = 10
    assert "point-buy-budget" in codes(evaluate(data, over), "error")
    out_of_range = copy.deepcopy(state)
    out_of_range["abilityBase"]["str"] = 16
    assert "point-buy-range" in codes(evaluate(data, out_of_range), "error")
    under = copy.deepcopy(state)
    under["abilityBase"]["str"] = 8
    assert "point-buy-unspent" in codes(evaluate(data, under), "warning")


def test_rolled_scores_must_match_dice(data):
    rolls = [[6, 5, 4, 1], [6, 6, 6, 6], [1, 2, 3, 4], [3, 3, 3, 3], [5, 5, 2, 1], [4, 4, 4, 2]]
    totals = [15, 18, 9, 9, 12, 12]
    state = make([("fighter", 1)], dict(zip(ABILITY_IDS, [12, 18, 9, 15, 12, 9])), "soldier", {"str": 2, "con": 1}, abilityRolls=rolls)
    state["abilityMethod"] = "roll"
    assert sorted(totals) == sorted(state["abilityBase"].values())
    assert not codes(evaluate(data, state)) & {"roll-mismatch", "roll-missing"}
    tampered = copy.deepcopy(state)
    tampered["abilityBase"]["str"] = 17
    assert "roll-mismatch" in codes(evaluate(data, tampered), "error")
    missing = copy.deepcopy(state)
    del missing["abilityRolls"]
    assert "roll-missing" in codes(evaluate(data, missing), "incomplete")


def test_manual_scores(data):
    state = make([("fighter", 1)], scores(str=21), "soldier", {"str": 2, "con": 1})
    result = evaluate(data, state)
    assert "manual-range" in codes(result, "error") and "manual-method" in codes(result, "info")


def test_missing_ability_method_and_scores_are_incomplete(data):
    result = evaluate(data, {"levels": [{"classKey": "fighter"}]})
    assert {"ability-method", "ability-missing", "background-missing", "species-missing"} <= codes(result, "incomplete")
    assert not result["complete"]


def test_background_bonus_patterns(data):
    def run(bonus):
        return evaluate(data, make([("fighter", 1)], scores(), "soldier", bonus))

    assert "background-bonus" not in codes(run({"str": 2, "con": 1}))
    assert "background-bonus" not in codes(run({"str": 1, "dex": 1, "con": 1}))
    assert "background-bonus" in codes(run({"str": 2, "con": 2}), "error")
    assert "background-bonus" in codes(run({"str": 2, "int": 1}), "error")
    assert "background-bonus" in codes(run({"str": 3}), "error")
    assert "background-bonus" in codes(run({}), "incomplete")


def test_score_cap_20_is_enforced_with_warning(data):
    state = make([("fighter", 4)], scores(str=19), "soldier", {"str": 2, "con": 1}, advancements=[{"classKey": "fighter", "classLevel": 4, "kind": "asi", "increases": {"str": 2}}])
    result = evaluate(data, state)
    assert result["abilities"]["str"]["score"] == 20 and result["abilities"]["str"]["modifier"] == 5
    assert "ability-cap" in codes(result, "warning")


# ---------------------------------------------------------------------------- advancements

def test_advancement_slots_and_patterns(data):
    def run(adv, levels=4):
        return evaluate(data, make([("fighter", levels)], scores(str=14), "soldier", {"str": 2, "con": 1}, advancements=adv))

    assert "advancement-missing" in codes(run([]), "incomplete")
    assert "advancement-missing" not in codes(run([{"classKey": "fighter", "classLevel": 4, "kind": "asi", "increases": {"dex": 1, "wis": 1}}]))
    assert "asi-pattern" in codes(run([{"classKey": "fighter", "classLevel": 4, "kind": "asi", "increases": {"dex": 1, "wis": 2}}]), "error")
    assert "asi-pattern" in codes(run([{"classKey": "fighter", "classLevel": 4, "kind": "asi", "increases": {"dex": 3}}]), "error")
    assert "advancement-slot" in codes(run([{"classKey": "fighter", "classLevel": 3, "kind": "asi", "increases": {"dex": 2}}]), "error")
    assert "advancement-slot" in codes(run([{"classKey": "fighter", "classLevel": 8, "kind": "asi", "increases": {"dex": 2}}]), "error")
    dup = [{"classKey": "fighter", "classLevel": 4, "kind": "asi", "increases": {"dex": 2}}] * 2
    assert "advancement-duplicate" in codes(run(dup), "error")


def test_fighter_and_rogue_have_extra_advancement_levels(data):
    fighter = evaluate(data, make([("fighter", 6)], scores(str=14), "soldier", {"str": 2, "con": 1}))
    assert {f["path"] for f in fighter["findings"] if f["code"] == "advancement-missing"} == {"advancements.fighter.4", "advancements.fighter.6"}
    rogue = evaluate(data, make([("rogue", 10)], scores(dex=14), "criminal", {"dex": 2, "con": 1}))
    assert {f["path"] for f in rogue["findings"] if f["code"] == "advancement-missing"} == {"advancements.rogue.4", "advancements.rogue.8", "advancements.rogue.10"}


def test_feat_prerequisites_and_increases(data):
    feat = "feats.descriptions.grappler"
    state = make([("fighter", 4)], scores(str=14), "soldier", {"str": 2, "con": 1}, advancements=[{"classKey": "fighter", "classLevel": 4, "kind": "feat", "featId": feat}])
    assert "feat-increase" in codes(evaluate(data, state), "incomplete")
    state["advancements"][0]["increaseAbility"] = "str"
    result = evaluate(data, state)
    assert "feat-increase" not in codes(result) and result["abilities"]["str"]["score"] == 14 + 2 + 1
    state["advancements"][0]["increaseAbility"] = "wis"
    assert "feat-increase" in codes(evaluate(data, state), "error")
    state["advancements"][0]["featId"] = "feats.descriptions.nope"
    assert "feat-unknown" in codes(evaluate(data, state), "error")


def test_epic_boon_raises_cap_to_30_only_for_its_ability(data):
    levels = [("fighter", 19)]
    adv = [
        {"classKey": "fighter", "classLevel": 4, "kind": "asi", "increases": {"str": 2}},
        {"classKey": "fighter", "classLevel": 6, "kind": "asi", "increases": {"str": 2}},
        {"classKey": "fighter", "classLevel": 8, "kind": "asi", "increases": {"str": 2}},
        {"classKey": "fighter", "classLevel": 12, "kind": "asi", "increases": {"dex": 2}},
        {"classKey": "fighter", "classLevel": 14, "kind": "asi", "increases": {"dex": 2}},
        {"classKey": "fighter", "classLevel": 16, "kind": "asi", "increases": {"dex": 2}},
        {"classKey": "fighter", "classLevel": 19, "kind": "feat", "featId": "feats.descriptions.boon-of-combat-prowess", "increaseAbility": "str"},
    ]
    result = evaluate(data, make(levels, scores(str=15, dex=15), "soldier", {"str": 2, "con": 1}, advancements=adv))
    assert result["abilities"]["str"]["score"] == 15 + 2 + 6 + 1 == 24
    assert result["abilities"]["dex"]["score"] == 20 and "ability-cap" in codes(result, "warning")


def test_feat_repeat_rules(data):
    adv = [
        {"classKey": "fighter", "classLevel": 4, "kind": "feat", "featId": "feats.descriptions.grappler", "increaseAbility": "str"},
        {"classKey": "fighter", "classLevel": 6, "kind": "feat", "featId": "feats.descriptions.grappler", "increaseAbility": "str"},
    ]
    result = evaluate(data, make([("fighter", 6)], scores(str=12), "soldier", {"str": 2, "con": 1}, advancements=adv))
    assert "feat-repeat" in codes(result, "error")


# ---------------------------------------------------------------------------- skills, choices, subclasses

def test_class_skill_choices(data):
    def run(skills):
        return evaluate(data, make([("fighter", 1)], scores(), "soldier", {"str": 2, "con": 1}, skills={"class": skills}))

    assert "class-skills" in codes(run([]), "incomplete")
    assert "class-skills" in codes(run(["akrobatik"]), "incomplete")
    assert "class-skills" in codes(run(["akrobatik", "arkane-kunde"]), "error")
    assert "class-skills" in codes(run(["akrobatik", "akrobatik"]), "error")
    assert "class-skills" not in codes(run(["akrobatik", "geschichte"]))
    overlap = run(["athletik", "geschichte"])
    assert "skill-duplicate" in codes(overlap, "warning")


def test_expertise_requires_proficiency(data):
    state = make(
        [("rogue", 1)], scores(dex=14), "criminal", {"dex": 2, "con": 1},
        skills={"class": ["akrobatik", "wahrnehmung", "taeuschen", "ueberzeugen"], "expertise": ["arkane-kunde", "heimlichkeit"]},
    )
    assert "expertise-without-proficiency" in codes(evaluate(data, state), "error")


def test_subclass_choice(data):
    state = make([("fighter", 3)], scores(), "soldier", {"str": 2, "con": 1}, subclasses={"fighter": "classes.fighter.subclass-champion"})
    assert not codes(evaluate(data, state)) & {"subclass-missing", "subclass-invalid"}
    state["subclasses"] = {"fighter": "classes.wizard.subclass-evoker"}
    assert "subclass-invalid" in codes(evaluate(data, state), "error")
    early = make([("fighter", 2)], scores(), "soldier", {"str": 2, "con": 1}, subclasses={"fighter": "classes.fighter.subclass-champion"})
    assert "subclass-early" in codes(evaluate(data, early), "warning")


def test_species_choices_validate(data):
    def run(choices, species="elf"):
        return evaluate(data, make([("fighter", 1)], scores(), "soldier", {"str": 2, "con": 1}, species=species, skills={"class": ["akrobatik", "geschichte"]}) | {"species": {"id": SPECIES + species, "choices": choices}})

    assert {"species-choice-missing"} <= codes(run({}), "incomplete")
    full = {"lineage": "drow", "spellcasting-ability": "wis", "keen-senses": "wahrnehmung"}
    result = run(full)
    assert not codes(result) & {"species-choice-missing", "species-choice-invalid"}
    assert result["skills"]["wahrnehmung"]["proficiency"] == "proficient"
    assert "species-choice-invalid" in codes(run({**full, "lineage": "mondelf"}), "error")
    assert "species-choice-invalid" in codes(run({**full, "keen-senses": "athletik"}), "error")
    human = run({"skillful": "arkane-kunde", "versatile": "feats.descriptions.alert", "size": "Mittelgroß"}, "human")
    assert human["skills"]["arkane-kunde"]["proficiency"] == "proficient" and "feats.descriptions.alert" in human["feats"]
    assert "species-choice-invalid" in codes(run({"skillful": "arkane-kunde", "versatile": "feats.descriptions.defense", "size": "Klein"}, "human"), "error")


def test_feature_choices_weapon_mastery_and_fighting_style(data):
    def run(choices):
        return evaluate(data, make([("fighter", 1)], scores(str=15), "soldier", {"str": 2, "con": 1}, featureChoices={"fighter": choices}))

    weapons = [w["id"] for w in data["equipment"]["weapons"] if w["category"] in {"simple", "martial"}][:3]
    ok = run({"fighting-style": "feats.descriptions.archery", "weapon-mastery": weapons})
    assert not codes(ok) & {"choice-missing", "choice-invalid", "mastery-proficiency"}
    assert "choice-invalid" in codes(run({"fighting-style": "feats.descriptions.alert", "weapon-mastery": weapons}), "error")
    assert "choice-missing" in codes(run({"fighting-style": "feats.descriptions.archery", "weapon-mastery": weapons[:2]}), "incomplete")
    assert "choice-invalid" in codes(run({"fighting-style": "feats.descriptions.archery", "weapon-mastery": weapons + weapons[:1]}), "error")


def test_metamagic_options_are_class_specific_and_unique(data):
    meta = [o["id"] for o in data["classOptions"] if o["classKey"] == "sorcerer"][:2]
    invocations = [o["id"] for o in data["classOptions"] if o["classKey"] == "warlock"]

    def run(picks, key="sorcerer"):
        return evaluate(data, make([(key, 2)], scores(cha=14), "acolyte", {"cha": 2, "wis": 1}, featureChoices={key: picks}))

    assert "choice-invalid" not in codes(run({"metamagic-1": meta}))
    assert "choice-invalid" in codes(run({"metamagic-1": [meta[0], invocations[0]]}), "error")
    assert "choice-duplicate" in codes(run({"metamagic-1": [meta[0], meta[0]]}), "error")
    assert "choice-missing" in codes(run({"metamagic-1": meta[:1]}), "incomplete")
    assert "choice-invalid" not in codes(run({"eldritch-invocations": invocations[:1]}, "warlock"))


# ---------------------------------------------------------------------------- spells

def test_spell_selection_checks(data):
    cantrips = [sid for sid in data["spellLists"]["wizard"] if data["spells"][sid]["level"] == 0][:3]
    book = pick_spells(data, "wizard", 1, 6, exact=True)
    base = make([("wizard", 1)], scores(int=15), "sage", {"int": 2, "con": 1}, spells={"wizard": {"cantrips": cantrips, "spellbook": book, "prepared": book[:4]}})
    result = evaluate(data, base)
    assert not codes(result) & {"cantrips-missing", "cantrips-extra", "cantrip-invalid", "spellbook-missing", "prepared-missing", "prepared-extra", "spell-invalid", "spell-grade"}

    too_high = copy.deepcopy(base)
    too_high["spells"]["wizard"]["prepared"][0] = pick_spells(data, "wizard", 3, 1, exact=True)[0]
    assert {"spell-grade", "prepared-not-in-book"} <= codes(evaluate(data, too_high), "error")

    cleric_spell = copy.deepcopy(base)
    only_cleric = next(s for s in data["spellLists"]["cleric"] if s not in data["spellLists"]["wizard"] and data["spells"][s]["level"] == 1)
    cleric_spell["spells"]["wizard"]["spellbook"][0] = only_cleric
    assert "spell-invalid" in codes(evaluate(data, cleric_spell), "error")

    extra = copy.deepcopy(base)
    extra["spells"]["wizard"]["cantrips"].append(next(s for s in data["spellLists"]["wizard"] if data["spells"][s]["level"] == 0 and s not in cantrips))
    assert "cantrips-extra" in codes(evaluate(data, extra), "error")

    short = copy.deepcopy(base)
    short["spells"]["wizard"]["prepared"] = []
    assert "prepared-missing" in codes(evaluate(data, short), "incomplete")


def test_spell_lists_cover_every_spell_and_class_lists_are_plausible(data):
    listed = {sid for ids in data["spellLists"].values() for sid in ids}
    assert listed == set(data["spells"])
    for key in ("barbarian", "fighter", "monk", "rogue"):
        assert data["spellLists"][key] == []
    for key in ("bard", "cleric", "druid", "paladin", "ranger", "sorcerer", "warlock", "wizard"):
        assert data["spellLists"][key]
        assert all(sid in data["spells"] for sid in data["spellLists"][key])
    assert not any(data["spells"][s]["level"] == 0 for s in data["spellLists"]["paladin"])


# ---------------------------------------------------------------------------- hit points

def test_rolled_hit_points(data):
    state = make([("fighter", 3)], scores(con=14), "soldier", {"str": 2, "con": 1})
    state["levels"] = [{"classKey": "fighter"}, {"classKey": "fighter", "hp": 4}, {"classKey": "fighter", "hp": 10}]
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == (10 + 2) + (4 + 2) + (10 + 2)
    bad = copy.deepcopy(state)
    bad["levels"][1]["hp"] = 11
    assert "hp-roll" in codes(evaluate(data, bad), "error")


def test_negative_constitution_never_drops_level_gain_below_one(data):
    state = make([("wizard", 3)], scores(con=3), "sage", {"int": 2, "wis": 1})
    result = evaluate(data, state)
    assert [row["gain"] for row in result["hitPoints"]["breakdown"]] == [6 - 4, 1, 1]


def test_fixed_hit_points_match_printed_table(data, classes):
    table = data["hitPoints"]["perLevel"]["fixed"]["byClassName"]
    for entry in classes.values():
        assert table[entry["name"]] == entry["hitDie"] // 2 + 1


# ---------------------------------------------------------------------------- level cap and robustness

def test_level_cap_and_empty_state(data):
    over = evaluate(data, {"levels": [{"classKey": "fighter"}] * 21})
    assert "level-cap" in codes(over, "error") and over["level"] == 20
    empty = evaluate(data, {})
    assert empty["level"] == 0 and "no-class" in codes(empty, "incomplete") and not empty["complete"]


@pytest.mark.parametrize("state", [
    None, [], "x", 5,
    {"levels": "fighter"}, {"levels": [None, 5, "x", {"classKey": 3}]},
    {"abilityBase": "x", "abilityMethod": "roll", "abilityRolls": "x"},
    {"levels": [{"classKey": "wizard"}], "spells": {"wizard": "x"}, "skills": [], "featureChoices": {"wizard": []}},
    {"levels": [{"classKey": "fighter"}], "advancements": [None, {"classKey": "fighter", "classLevel": "x"}], "subclasses": [], "overrides": {"hp.max": 5}},
    {"levels": [{"classKey": "fighter", "hp": "viel"}] * 2, "equipment": {"armor": {"x": 1}}},
])
def test_garbage_input_never_raises(data, state):
    result = evaluate(data, state)
    assert isinstance(result["findings"], list) and "valid" in result


JUNK = [None, 5, "x", [], {}, [None], {"id": {}}, {"id": []}, {"x": [1, {}]}, [{"classKey": []}], True]


def test_junk_in_every_state_field_never_raises(data):
    full = make(
        [("wizard", 4)], scores(int=15), "sage", {"int": 2, "con": 1},
        subclasses={"wizard": "classes.wizard.subclass-evoker"},
        skills={"class": ["heilkunde", "nachforschungen"], "expertise": ["arkane-kunde"], "other": []},
        advancements=[{"classKey": "wizard", "classLevel": 4, "kind": "asi", "increases": {"int": 2}}],
        spells={"wizard": {"cantrips": [], "spellbook": [], "prepared": []}},
        featureChoices={"wizard": {}}, equipment={"armor": None, "shield": False}, overrides={"hp.max": {"add": 1}}, abilityRolls=[],
    )
    for field in list(full):
        for junk in JUNK:
            evaluate(data, {**full, field: junk})
    for field in ("background", "species", "skills", "spells", "equipment", "overrides"):
        for inner in list(full[field]):
            for junk in JUNK:
                evaluate(data, {**full, field: {**full[field], inner: junk}})
    for index in range(4):
        for junk in JUNK:
            levels = copy.deepcopy(full["levels"])
            levels[index] = junk
            evaluate(data, {**full, "levels": levels})
            adv = copy.deepcopy(full["advancements"])
            adv[0] = {**adv[0], **({"kind": junk} if index == 0 else {"classLevel": junk} if index == 1 else {"increases": junk} if index == 2 else {"classKey": junk})}
            evaluate(data, {**full, "advancements": adv})


def test_evaluate_is_deterministic_and_does_not_mutate_input(data):
    state = make([("fighter", 3)], scores(str=15), "soldier", {"str": 2, "con": 1}, overrides={"hp.max": {"add": 3}})
    snapshot = copy.deepcopy(state)
    first = evaluate(data, state)
    assert state == snapshot
    assert evaluate(data, state) == first


# ---------------------------------------------------------------------------- overrides

def test_overrides_are_applied_recorded_and_flagged(data):
    state = make([("fighter", 1)], scores(str=14, dex=12, con=14), "soldier", {"str": 2, "con": 1})
    plain = evaluate(data, state)
    assert plain["overrides"] == []
    state["overrides"] = {
        "hp.max": {"add": 5, "reason": "Heldenhaft"},
        "armorClass": {"set": 17},
        "ability.str": {"set": 18},
        "speed": {"add": 3},
        "initiative": {"add": 2},
        "passivePerception": {"set": 20},
    }
    result = evaluate(data, state)
    assert result["hitPoints"]["max"] == plain["hitPoints"]["max"] + 5
    assert result["armorClass"]["value"] == 17
    assert result["abilities"]["str"]["score"] == 18 and result["abilities"]["str"]["modifier"] == 4
    assert result["speedMeters"] == plain["speedMeters"] + 3
    assert result["initiative"] == plain["initiative"] + 2
    assert result["passivePerception"] == 20
    recorded = {row["key"]: row for row in result["overrides"]}
    assert recorded["hp.max"] == {"key": "hp.max", "computed": plain["hitPoints"]["max"], "value": plain["hitPoints"]["max"] + 5, "reason": "Heldenhaft"}
    assert recorded["armorClass"]["computed"] == plain["armorClass"]["value"]
    assert [f["code"] for f in result["findings"]].count("override-active") == 6


def test_override_errors(data):
    state = make([("fighter", 1)], scores(), "soldier", {"str": 2, "con": 1}, overrides={"bogus": {"set": 1}, "hp.max": {}, "armorClass": {"set": "viel"}})
    result = evaluate(data, state)
    assert {"override-unknown", "override-invalid"} <= codes(result, "error")
    assert result["overrides"] == []


def test_spell_overrides(data):
    state = make([("wizard", 1)], scores(int=16), "sage", {"int": 2, "con": 1}, overrides={"spellSaveDc": {"set": 18}, "spellAttack": {"add": 1}})
    result = evaluate(data, state)
    wizard = result["spellcasting"]["classes"]["wizard"]
    assert wizard["saveDc"] == 18 and wizard["attackBonus"] == 4 + 2 + 1


# ---------------------------------------------------------------------------- findings carry rule references

def test_rule_findings_carry_verbatim_source_refs(data):
    import json
    from tests.test_regelwerk_creator_data import PACKAGE
    from vtt.rules_content.creator_data import Source

    documents = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((PACKAGE / "documents").glob("*.json"))]
    source = Source(documents)
    state = make([("fighter", 1), ("wizard", 1)], dict(zip(ABILITY_IDS, [15, 15, 15, 10, 8, 8])), "soldier", {"str": 2, "dex": 2})
    state["abilityMethod"] = "point-buy"
    result = evaluate(data, state)
    refs = [f["ref"] for f in result["findings"] if f["ref"]]
    assert {"point-buy-budget", "background-bonus", "multiclass-prerequisite"} <= codes(result)
    assert len(refs) >= 3
    for ref in refs:
        assert ref["quote"] in source.text(ref["ruleId"]), ref
