"""Structured creator data (creator-data.json): shape, source quotes and cross-checks against the rule tables."""

from __future__ import annotations

import json

import pytest

from vtt.rules_content.creator_data import SCHEMA_VERSION, Source, _core
from vtt.rules_content.validator import CONTENT_ROOT

PACKAGE = CONTENT_ROOT / "srd-5.2.1-de"
CLASS_KEYS = {"barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"}


@pytest.fixture(scope="module")
def data():
    return json.loads((PACKAGE / "generated" / "creator-data.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def compendium():
    return json.loads((PACKAGE / "generated" / "compendium.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source():
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((PACKAGE / "documents").glob("*.json"))]
    return Source(documents)


def _refs(node):
    if isinstance(node, dict):
        if set(node) == {"ruleId", "quote"}:
            yield node
        for value in node.values():
            yield from _refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _refs(value)


def _walk(node):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def test_header_and_digest_match_compendium(data, compendium):
    assert data["schemaVersion"] == SCHEMA_VERSION
    assert data["rulesetId"] == "srd-5.2.1-de"
    assert data["packageDigest"] == compendium["packageDigest"]


def test_every_curated_quote_is_verbatim_in_its_rule_block(data, source):
    refs = list(_refs(data))
    assert len(refs) > 150
    for ref in refs:
        assert ref["quote"] in source.text(ref["ruleId"]), ref


def test_no_unresolved_equipment_references(data, compendium):
    gear = {e["id"] for e in compendium["entities"]}
    count = 0
    for node in _walk(data):
        if isinstance(node, dict) and node.get("kind") in {"item", "unresolved"}:
            assert node["kind"] == "item", node
            assert node["itemId"] in gear, node
            count += 1
    assert count > 40


def test_all_content_is_covered(data):
    assert {c["classKey"] for c in data["classes"]} == CLASS_KEYS
    assert len(data["species"]) == 9
    assert len(data["backgrounds"]) == 4
    assert len(data["feats"]) == 17
    assert len(data["skills"]) == 18
    assert len(data["alignments"]) == 9
    assert len(data["trinkets"]) == 100
    assert len(data["equipment"]["packs"]) == 7
    assert len(data["classOptions"]) == 38


def test_ability_modifier_matches_printed_table(source):
    core = _core(source)
    assert core["abilityModifier"]["formula"] == "floor((score - 10) / 2)"


def test_levels_cover_one_to_twenty_with_expected_bonus(data):
    levels = data["levels"]
    assert [row["level"] for row in levels] == list(range(1, 21))
    assert [row["proficiencyBonus"] for row in levels if row["level"] in {1, 5, 9, 13, 17}] == [2, 3, 4, 5, 6]
    assert levels[0]["xp"] == 0 and levels[-1]["xp"] == 355000


def test_ability_score_methods(data):
    methods = data["abilityScoreMethods"]
    assert methods["standardArray"]["values"] == [15, 14, 13, 12, 10, 8]
    point_buy = methods["pointBuy"]
    assert point_buy["budget"] == 27
    assert point_buy["costs"] == {"8": 0, "9": 1, "10": 2, "11": 3, "12": 4, "13": 5, "14": 7, "15": 9}
    assert methods["backgroundBonus"]["options"] == [[2, 1], [1, 1, 1]]


def test_standard_scores_per_class_are_the_standard_array(data):
    for entry in data["classes"]:
        scores = entry["standardAbilityScores"]
        assert sorted(scores.values(), reverse=True) == [15, 14, 13, 12, 10, 8]
        for ability in entry["primaryAbilities"]["abilities"]:
            assert scores[ability] >= 13


def test_hit_points_use_constitution_and_flag_source_defect(data):
    by_key = {c["classKey"]: c["hitDie"] for c in data["classes"]}
    assert by_key == {
        "barbarian": 12, "bard": 8, "cleric": 8, "druid": 8, "fighter": 10, "monk": 8,
        "paladin": 10, "ranger": 10, "rogue": 8, "sorcerer": 6, "warlock": 8, "wizard": 6,
    }
    hp = data["hitPoints"]
    assert hp["level1"]["formula"] == "hitDie + conModifier"
    notes = hp["level1"]["sourceNotes"]
    assert len(notes) == 1 and notes[0]["kind"] == "source-defect"
    assert sorted(notes[0]["classes"]) == ["Kämpfer", "Paladin", "Waldläufer"]
    assert hp["perLevel"]["fixed"]["byClassName"]["Barbar"] == 7
    assert hp["perLevel"]["fixed"]["byClassName"]["Magier"] == 4


def test_class_progression_levels_and_slots(data):
    for entry in data["classes"]:
        assert [row["level"] for row in entry["levels"]] == list(range(1, 21))
        assert entry["subclassLevels"] == [3]
        assert entry["epicBoonLevel"] == 19
        assert {4, 8, 12, 16}.issubset(entry["asiLevels"])
        assert entry["primaryAbilities"]["abilities"]
        assert len(entry["savingThrows"]) == 2


def test_full_caster_slots_match_multiclass_table(data):
    table = data["multiclass"]["spellSlotsByCasterLevel"]
    for entry in data["classes"]:
        spell = entry["spellcasting"]
        if not spell or spell["kind"] != "full":
            continue
        for row in spell["levels"]:
            assert row["slots"] == table[str(row["level"])], (entry["classKey"], row["level"])


def test_half_caster_slots_match_multiclass_table(data):
    table = data["multiclass"]["spellSlotsByCasterLevel"]
    for entry in data["classes"]:
        spell = entry["spellcasting"]
        if not spell or spell["kind"] != "half":
            continue
        for row in spell["levels"]:
            caster_level = (row["level"] + 1) // 2
            assert row["slots"] == table[str(caster_level)][:5], (entry["classKey"], row["level"])


def test_spellcasting_kinds(data):
    kinds = {c["classKey"]: (c["spellcasting"] or {}).get("kind") for c in data["classes"]}
    assert kinds == {
        "barbarian": None, "bard": "full", "cleric": "full", "druid": "full", "fighter": None, "monk": None,
        "paladin": "half", "ranger": "half", "rogue": None, "sorcerer": "full", "warlock": "pact", "wizard": "full",
    }
    wizard = next(c for c in data["classes"] if c["classKey"] == "wizard")
    assert wizard["spellcasting"]["preparation"]["mode"] == "spellbook"
    assert wizard["spellcasting"]["spellbook"]["startingSpells"] == 6


def test_resources_declare_recovery_with_quote(data):
    sorcerer = next(c for c in data["classes"] if c["classKey"] == "sorcerer")
    points = next(r for r in sorcerer["resources"] if r["id"] == "sorcery-points")
    assert points["recover"] == {"long": "all"}
    assert points["usesByLevel"]["2"] == 2
    warlock = next(c for c in data["classes"] if c["classKey"] == "warlock")
    assert warlock["resources"][0]["recover"] == {"short": "all", "long": "all"}
    fighter = next(c for c in data["classes"] if c["classKey"] == "fighter")
    assert {r["id"] for r in fighter["resources"]} == {"second-wind", "action-surge", "indomitable"}
    for entry in data["classes"]:
        for resource in entry["resources"]:
            assert resource["recover"] and resource["source"]["quote"]


def test_multiclass_rules(data):
    multiclass = data["multiclass"]
    assert multiclass["prerequisite"]["minimumScore"] == 13
    assert multiclass["casterLevel"]["half"] == ["paladin", "ranger"]
    assert sorted(multiclass["spellSlotsByCasterLevel"], key=int) == [str(n) for n in range(1, 21)]
    assert multiclass["spellSlotsByCasterLevel"]["20"] == [4, 3, 3, 3, 3, 2, 2, 1, 1]
    for entry in data["classes"]:
        assert entry["multiclassGrants"]["source"]["quote"]


def test_starting_equipment_has_two_options_and_gold(data):
    for entry in data["classes"]:
        options = entry["startingEquipment"]
        assert {"A", "B"}.issubset(options), entry["classKey"]
        assert any(all(part["kind"] == "coins" for part in option) for option in options.values()), entry["classKey"]
    levels = data["startingEquipmentByLevel"]
    assert [(row["fromLevel"], row["toLevel"]) for row in levels] == [(2, 4), (5, 10), (11, 16), (17, 20)]


def test_species_choices(data):
    species = {entry["id"].rsplit(".", 1)[-1]: entry for entry in data["species"]}
    assert {c["id"] for c in species["elf"]["choices"]} >= {"lineage", "spellcasting-ability", "keen-senses"}
    assert [o["id"] for o in species["elf"]["choices"][0]["options"]] == ["drow", "hochelf", "waldelf"]
    assert len(species["dragonborn"]["choices"][0]["options"]) == 10
    assert len(species["goliath"]["choices"][0]["options"]) == 6
    assert len(species["tiefling"]["choices"][0]["options"]) == 3
    assert {o["id"] for o in species["gnome"]["choices"][0]["options"]} == {"rock-gnome", "forest-gnome"}
    assert {c["id"] for c in species["human"]["choices"]} >= {"skillful", "versatile"}


def test_backgrounds_grant_origin_package(data):
    for background in data["backgrounds"]:
        assert len(background["abilities"]) == 3
        assert len(background["skills"]) == 2
        assert background["feat"]
        assert set(background["startingEquipment"]) == {"A", "B"}


def test_feat_prerequisites_and_increases(data):
    feats = {f["id"].rsplit(".", 1)[-1]: f for f in data["feats"]}
    assert feats["ability-score-improvement"]["category"] == "Allgemeines Talent"
    assert feats["magic-initiate"]["repeatable"] is True
    epics = [f for f in data["feats"] if f["category"] == "Epische-Gabe-Talent"]
    assert epics and all(f["prerequisite"]["minLevel"] == 19 for f in epics)
    assert all(f["abilityIncrease"]["max"] == 30 for f in epics)


def test_languages_alignments_equipment(data):
    standard = [lang for lang in data["languages"] if lang["kind"] == "standard"]
    rolled = sorted(n for lang in standard if lang["roll"] for n in range(lang["roll"][0], lang["roll"][1] + 1))
    assert rolled == list(range(1, 13))
    assert sorted(a["abbreviation"] for a in data["alignments"]) == sorted(["RG", "NG", "CG", "RN", "N", "CN", "RB", "NB", "CB"])
    assert data["equipment"]["coins"]["GM"]["valueInCp"] == 100
    shield = next(a for a in data["equipment"]["armor"] if a["category"] == "shield")
    assert shield["shield"] is True and shield["base"] == 2
    plate = next(a for a in data["equipment"]["armor"] if a["name"] == "Ritterrüstung")
    assert plate["base"] == 18 and plate["dex"] == "none" and plate["strengthRequirement"] == 15 and plate["stealthDisadvantage"]
    longsword = next(w for w in data["equipment"]["weapons"] if w["name"] == "Langschwert")
    assert longsword["damage"] == {"dice": 1, "sides": 8, "flat": 0, "type": "slashing"}
    assert any(p.get("versatile") == {"dice": 1, "sides": 10} for p in longsword["properties"])
