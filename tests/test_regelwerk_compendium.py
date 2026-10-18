"""Queryable compendium derived from the published Regelwerk package."""

from __future__ import annotations

import json

import pytest

from vtt import create_app
from vtt.rules_content.validator import CONTENT_ROOT

PACKAGE = CONTENT_ROOT / "srd-5.2.1-de"
API = "/api/rulesets/srd-5.2.1-de/compendium"


@pytest.fixture
def client():
    return create_app(config_name="testing").test_client()


@pytest.fixture(scope="module")
def data():
    return json.loads((PACKAGE / "generated" / "compendium.json").read_text(encoding="utf-8"))


def test_entity_counts_match_the_source_inventory(data):
    assert data["counts"] == {
        "armor": 13,
        "creature": 330,
        "feat": 17,
        "magic-item": 258,
        "spell": 339,
        "weapon": 38,
    }
    ids = [entity["id"] for entity in data["entities"]]
    assert len(ids) == len(set(ids))


def test_every_entity_links_to_an_existing_rule_block(data):
    documents = {}
    for entity in data["entities"]:
        document = documents.setdefault(
            entity["documentId"],
            json.loads((PACKAGE / "documents" / f"{entity['documentId']}.json").read_text(encoding="utf-8")),
        )
        rule_ids = {block["ruleId"] for block in document["blocks"]}
        assert entity["id"] in rule_ids or entity["id"].rsplit(".", 1)[0] in rule_ids, entity["id"]
        assert entity["url"].endswith("#" + entity["id"])


def test_spell_facets_are_complete_and_consistent(data):
    spells = [e for e in data["entities"] if e["type"] == "spell"]
    assert {e["level"] for e in spells} == set(range(10))
    assert len({e["school"] for e in spells}) == 8
    assert all(e["classes"] and e["castingTime"] and e["range"] for e in spells)
    fireball = next(e for e in spells if e["name"] == "Feuerball")
    assert fireball["level"] == 3 and fireball["school"] == "Hervorrufung"
    assert not fireball["concentration"] and "Zauberer" in fireball["classes"]


def test_creature_and_item_parsing_has_no_gaps(data):
    creatures = [e for e in data["entities"] if e["type"] == "creature"]
    assert all(e["size"] and e["creatureType"] and e["armorClass"] and e["hitPoints"] for e in creatures)
    assert {e["challenge"] for e in creatures} >= {"0", "1/8", "1/4", "1/2", "1", "30"}
    items = [e for e in data["entities"] if e["type"] == "magic-item"]
    assert all(e["rarity"] and e["category"] for e in items)


def test_api_filters_spells(client):
    body = client.get(f"{API}?type=spell&level=3&class=Zauberer&school=Hervorrufung").get_json()
    assert body["total"] >= 1
    assert all(i["level"] == 3 and i["school"] == "Hervorrufung" and "Zauberer" in i["classes"] for i in body["items"])
    assert "Feuerball" in [i["name"] for i in body["items"]]
    conc = client.get(f"{API}?type=spell&concentration=true&limit=200").get_json()
    assert conc["total"] > 0 and all(i["concentration"] for i in conc["items"])
    component = client.get(f"{API}?type=spell&component=M&limit=200").get_json()
    assert all("M" in i["components"] for i in component["items"])


def test_api_filters_creatures_by_challenge_rating(client):
    body = client.get(f"{API}?type=creature&cr_min=1/4&cr_max=1&sort=cr&limit=200").get_json()
    values = [i["challengeValue"] for i in body["items"]]
    assert values and values == sorted(values) and 0.25 <= min(values) and max(values) <= 1
    assert client.get(f"{API}?type=creature&legendary=true").get_json()["total"] == 30


def test_api_text_query_ignores_case_and_umlauts(client):
    body = client.get(f"{API}?type=magic-item&q=ADAMANTRUESTUNG").get_json()
    assert [i["name"] for i in body["items"]] == ["Adamantrüstung"]


def test_api_pagination_and_facets(client):
    first = client.get(f"{API}?type=weapon&limit=10").get_json()
    second = client.get(f"{API}?type=weapon&limit=10&offset=10").get_json()
    assert first["total"] == 38 and len(first["items"]) == 10
    assert not {i["id"] for i in first["items"]} & {i["id"] for i in second["items"]}
    assert "Plagen" in first["facets"]["mastery"]


@pytest.mark.parametrize(
    "query",
    ["type=bogus", "type=spell&level=x", "type=spell&level=12", "type=creature&cr_min=abc",
     "type=spell&limit=0", "type=spell&limit=5000", "type=spell&sort=zzz", "type=spell&ritual=maybe",
     "type=spell&component=Q"],
)
def test_api_rejects_invalid_queries(client, query):
    assert client.get(f"{API}?{query}").status_code == 400


def test_compendium_page_and_summary(client):
    assert client.get("/regelwerk/compendium").status_code == 200
    assert client.get(f"{API}/summary").get_json()["counts"]["spell"] == 339
