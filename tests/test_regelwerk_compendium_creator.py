"""Creator-oriented compendium entities: classes, species, backgrounds, gear and rules vocabulary."""

from __future__ import annotations

import json
import re

import pytest

from vtt import create_app
from vtt.rules_content.compendium import entry_excerpt
from vtt.rules_content.validator import CONTENT_ROOT

PACKAGE = CONTENT_ROOT / "srd-5.2.1-de"
API = "/api/rulesets/srd-5.2.1-de/compendium"
SPELL_LIST_ALIASES = {"Licht": "Leicht", "Fliegen": "Flug", "Springen": "Sprung", "Verwünschen": "Verwünschung"}


@pytest.fixture
def client():
    return create_app(config_name="testing").test_client()


@pytest.fixture(scope="module")
def entities():
    return json.loads((PACKAGE / "generated" / "compendium.json").read_text(encoding="utf-8"))["entities"]


def _of(entities, entity_type):
    return [e for e in entities if e["type"] == entity_type]


def _document(document_id):
    return json.loads((PACKAGE / "documents" / f"{document_id}.json").read_text(encoding="utf-8"))


def test_twelve_classes_with_complete_progression(entities):
    classes = _of(entities, "class")
    assert len(classes) == 12
    for entity in classes:
        assert [row["level"] for row in entity["progression"]] == list(range(1, 21)), entity["name"]
        assert entity["hitDie"] in {6, 8, 10, 12}
        assert entity["savingThrows"] and entity["primaryAbility"] and entity["startingEquipmentOptions"]
        assert len(entity["subclasses"]) == 1
    assert {e["name"] for e in classes if e["spellcaster"]} == {
        "Barde", "Druide", "Hexenmeister", "Kleriker", "Magier", "Paladin", "Waldläufer", "Zauberer"
    }


def test_every_progression_feature_has_a_feature_entity(entities):
    features = _of(entities, "class-feature")
    names = {(e["classKey"], e["name"]) for e in features}
    assert {e["id"] for e in features} >= {f for c in _of(entities, "class") for f in c["features"]}
    for entity in _of(entities, "class"):
        level_one = {e["name"] for e in features if e["classKey"] == entity["classKey"] and e["level"] == 1}
        assert level_one, entity["name"]
        for row in entity["progression"]:
            for feature in row["features"]:
                if feature in {"Unterklassenmerkmal", "Attributswerterhöhung", "Epische Gabe"} or "Talent" in feature:
                    continue
                base = re.sub(r"\s*\(.*\)$", "", feature)
                assert (entity["classKey"], base) in names or any(base in n for _, n in names), (entity["name"], feature)


def test_class_spell_lists_resolve_to_spells_and_match_spell_class_lines(entities):
    spells = {e["id"]: e for e in _of(entities, "spell")}
    for entity in _of(entities, "class"):
        listed = [i for ids in entity["spellList"].values() for i in ids]
        assert len(listed) == len(set(listed))
        for level, ids in entity["spellList"].items():
            for spell_id in ids:
                assert entity["name"] in spells[spell_id]["classes"]
                assert spells[spell_id]["level"] == int(level)
        assert entity["spellcaster"] == bool(listed)
    wizard = next(e for e in _of(entities, "class") if e["classKey"] == "wizard")
    assert "spells.c-f.feuerball" in wizard["spellList"]["3"] or any(
        spells[i]["name"] == "Feuerball" for i in wizard["spellList"]["3"]
    )


def test_printed_class_spell_tables_are_only_incomplete_never_unknown(entities):
    """The source's printed class lists omit or misplace rows; the entity lists follow the spell class lines."""
    spells = {e["name"]: e["id"] for e in _of(entities, "spell")}
    expected_missing = {"bard": 1, "druid": 33, "wizard": 1, "sorcerer": 2}
    expected_misplaced = {"druid": 16}
    for entity in _of(entities, "class"):
        if not entity["spellcaster"]:
            continue
        printed = {}
        for block in _document(entity["documentId"])["blocks"]:
            match = block["type"] == "table" and re.search(r"spell-list-(?:cantrips|level(\d))$", block["ruleId"])
            if match:
                printed[match.group(1) or "0"] = {
                    spells[SPELL_LIST_ALIASES.get(n, n)]
                    for n in (re.sub(r"\s*\*+$", "", row[0]).strip() for row in block["rows"])
                }
        derived = {level: set(ids) for level, ids in entity["spellList"].items()}
        missing = sum(len(derived[l] - printed.get(l, set())) for l in derived)
        misplaced = sum(len(printed[l] - derived.get(l, set())) for l in printed)
        assert missing == expected_missing.get(entity["classKey"], 0), entity["classKey"]
        assert misplaced == expected_misplaced.get(entity["classKey"], 0), entity["classKey"]


def test_subclasses_options_species_and_backgrounds(entities):
    subclasses = _of(entities, "subclass")
    assert len(subclasses) == 12 and all(e["features"] for e in subclasses)
    options = _of(entities, "class-option")
    assert {e["optionKind"] for e in options} == {"Metamagie", "Schauerliche Anrufung"}
    species = _of(entities, "species")
    assert {e["name"] for e in species} >= {"Elf", "Zwerg", "Mensch", "Halbling"}
    assert all(e["speed"] and e["sizes"] and e["traits"] for e in species)
    backgrounds = _of(entities, "background")
    feats = {e["name"] for e in _of(entities, "feat")}
    assert len(backgrounds) == 4
    for background in backgrounds:
        assert background["feat"] in feats
        assert len(background["abilities"]) == 3 and len(background["skills"]) == 2
        assert set(background["equipmentOptions"]) == {"A", "B"}


def test_gear_tools_services_and_vocabulary(entities):
    gear = {e["name"]: e for e in _of(entities, "gear")}
    scholar = next(e for n, e in gear.items() if n.startswith("Gelehrtenausr"))
    assert scholar["detailId"] and "Tintenfüller" in scholar["summary"]
    assert gear["Abdeckbare Laterne"]["detailId"].endswith("laterne-abdeckbar")
    assert len(_of(entities, "tool")) == 25
    spellcasting = [e for e in _of(entities, "service") if e["category"] == "Zauberwirken"]
    assert {e["name"] for e in spellcasting} >= {"Zauberwirken: Zaubertrick", "Zauberwirken: Grad 1", "Zauberwirken: Grad 9"}
    glossary = {e["name"]: e for e in _of(entities, "glossary")}
    assert "Zustand" in {e["category"] for e in glossary.values()}
    assert len(_of(entities, "mount")) == 8 and len(_of(entities, "vehicle")) == 7


def test_api_filters_for_creator_types(client):
    features = client.get(f"{API}?type=class-feature&className=Mönch&level_max=2&limit=200").get_json()
    assert features["total"] > 0 and all(i["className"] == "Mönch" and i["level"] <= 2 for i in features["items"])
    top = client.get(f"{API}?type=class-feature&level=20&limit=200").get_json()
    assert top["total"] >= 12 and 20 in top["facets"]["level"]
    casters = client.get(f"{API}?type=class&spellcaster=true").get_json()
    assert casters["total"] == 8
    assert client.get(f"{API}?type=class&hitDie=12").get_json()["total"] == 1
    assert client.get(f"{API}?type=gear&category=Heiliges Symbol").get_json()["total"] >= 3
    assert client.get(f"{API}?type=glossary&category=Zustand").get_json()["total"] >= 10
    assert client.get(f"{API}?type=class-feature&level=21").status_code == 400
    assert client.get(f"{API}?type=spell&level=10").status_code == 400
    levels = client.get(f"{API}?type=class-feature&limit=1").get_json()["facets"]["level"]
    assert levels == sorted(levels) and levels[0] == 1


def test_every_entity_has_a_detail_excerpt(entities):
    documents = {}
    for entity in entities:
        document = documents.setdefault(entity["documentId"], _document(entity["documentId"]))
        blocks = entry_excerpt(document, entity)
        assert blocks, entity["id"]
        if entity.get("tableId"):
            assert blocks[0]["type"] == "table" and len(blocks[0]["rows"]) == 1
            assert blocks[0]["rows"][0] == _document(entity["documentId"])["blocks"][
                [b.get("ruleId") for b in _document(entity["documentId"])["blocks"]].index(entity["tableId"])
            ]["rows"][entity["rowIndex"]]


def test_detail_endpoint(client):
    body = client.get(f"{API}/entry/classes.wizard.wizard").get_json()
    assert body["entity"]["name"] == "Magier"
    types = {b["type"] for b in body["blocks"]}
    assert "table" in types and body["blocks"][0]["type"] == "heading"
    assert body["blocks"][-1]["type"] != "heading"
    assert not any(b["type"] == "heading" and ".level1-" in b["ruleId"] for b in body["blocks"])
    assert any(b["type"] == "table" and b["ruleId"].endswith("progression-table") for b in body["blocks"])
    row = client.get(f"{API}/entry/equipment.coins-and-weapons.weapons-simple-melee.beil").get_json()
    assert row["blocks"][0]["rows"][0][0] == "Beil"
    response = client.get(f"{API}/entry/does.not.exist")
    assert response.status_code == 404
    assert client.get(f"{API}/entry/spells.a-b.ablenkung").get_json()["blocks"][0]["text"] == "Ablenkung"
