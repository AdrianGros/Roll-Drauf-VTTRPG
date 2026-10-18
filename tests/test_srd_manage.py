"""P10: level-down, archive, duplicate, rebuild as draft and companions of SRD characters."""

import pytest

from vtt.characters import srd_progression
from vtt.extensions import db
from vtt.models import Character, InventoryItem
from vtt.rules_content.creator_drafts import character_values, finalize_blockers
from vtt.rules_content.creator_rules import evaluate

from tests.test_srd_creator_api import BASE, _client, app, client, data, finalized, other  # noqa: F401
from tests.test_srd_progression import CLASS_KEYS, award, level_one_state, make_character, payload_from_needs
from tests.test_srd_rolls import table  # noqa: F401


def _levelled(data, key, target):
    """States and evaluations of a class from level 1 up to `target`."""
    state = level_one_state(data, key)
    evaluation = evaluate(data, state)
    history = [(state, evaluation)]
    for _ in range(2, target + 1):
        need = srd_progression.needs(data, state, evaluation, key)
        state = srd_progression.build_state(data, state, payload_from_needs(data, need, evaluation, state))
        evaluation = evaluate(data, state)
        assert finalize_blockers(evaluation, state) == []
        history.append((state, evaluation))
    return history


def _stored(data, state, evaluation):
    values = character_values(data, state, evaluation, draft_id=1, finalized_at="2026-01-01T00:00:00Z")
    return Character(user_id=1, **values)


# ------------------------------------------------------------------ level-down on the engine

@pytest.mark.parametrize("key", CLASS_KEYS)
def test_level_down_walks_every_class_back_to_level_1(app, data, key):
    history = _levelled(data, key, 20)
    top_state, top_eval = history[-1]
    char = _stored(data, top_state, top_eval)
    for target in range(19, 0, -1):
        result = srd_progression.level_down(char, data, {"expectedLevel": target + 1}, user_id=1)
        before_state, before_eval = history[target - 1]
        evaluation = result["evaluation"]
        assert evaluation["level"] == target == char.level
        assert evaluation["hitPoints"]["max"] == before_eval["hitPoints"]["max"] == char.hp_max
        assert evaluation["armorClass"]["value"] == before_eval["armorClass"]["value"]
        assert evaluation["spellcasting"] == before_eval["spellcasting"]
        assert [(c["classKey"], c["level"], c["subclass"]) for c in evaluation["classes"]] == [(c["classKey"], c["level"], c["subclass"]) for c in before_eval["classes"]]
        assert char.hp_current <= char.hp_max
        assert data["levels"][target - 1]["xp"] <= char.xp < data["levels"][target]["xp"]
        assert char.character_data["srd"]["history"][-1]["type"] == "level-down"
    with pytest.raises(srd_progression.ProgressionError) as exc:
        srd_progression.level_down(char, data, {"expectedLevel": 1}, user_id=1)
    assert exc.value.code == "min_level"


def test_level_down_removes_the_last_class_of_a_multiclass(app, data):
    state = level_one_state(data, "fighter")
    state["abilityBase"]["cha"] = 8
    state["levels"].append({"classKey": "wizard", "hp": "fixed"})
    evaluation = evaluate(data, state)
    state["skills"]["multiclass"] = {"wizard": []}
    char = _stored(data, state, evaluation)
    result = srd_progression.level_down(char, data, {"expectedLevel": 2}, user_id=1)
    assert [(c["classKey"], c["level"]) for c in result["evaluation"]["classes"]] == [("fighter", 1)]
    assert "wizard" not in char.character_data["srd"]["state"].get("spells", {})


# ------------------------------------------------------------------ level-down through the API

def test_level_down_api(client, other, data):
    char = finalized(client, data)
    cid = char["id"]
    row = db.session.get(Character, cid)
    row.hp_current = row.hp_max
    db.session.commit()
    before_max = row.hp_max

    info = client.get(f"{BASE}/characters/{cid}/progression").get_json()
    assert info["canLevelDown"] is True and info["lastLevel"]["classKey"] == "wizard" and info["lastLevel"]["classLevel"] == 5
    assert other.post(f"{BASE}/characters/{cid}/level-down", json={"expectedLevel": 5}).status_code == 403
    assert client.post(f"{BASE}/characters/{cid}/level-down", json={}).status_code == 400
    stale = client.post(f"{BASE}/characters/{cid}/level-down", json={"expectedLevel": 4})
    assert stale.status_code == 409 and stale.get_json()["error"] == "level_conflict"

    resp = client.post(f"{BASE}/characters/{cid}/level-down", json={"expectedLevel": 5})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["level"] == 4 and body["removed"]["classLevel"] == 5 and body["status"]["level"] == 4
    assert body["history"][-1]["type"] == "level-down"
    stored = db.session.get(Character, cid)
    assert stored.level == 4 and stored.proficiency_bonus == 2 and stored.hp_max < before_max
    assert stored.hp_current == stored.hp_max
    assert stored.xp == 6499
    assert stored.character_data["srd"]["derived"]["level"] == 4
    assert body["status"]["canLevelUp"] is False
    assert client.get(f"{BASE}/characters/{cid}").get_json()["evaluation"]["level"] == 4
    # the experience was capped, the level can be taken again with a fresh award
    award(client, cid, addXp=1)
    assert client.get(f"{BASE}/characters/{cid}/progression").get_json()["status"]["canLevelUp"] is True


def test_level_down_milestone_mode_and_level_1_floor(client, data):
    char = make_character(client, level_one_state(data, "fighter"))
    cid = char["id"]
    assert client.get(f"{BASE}/characters/{cid}/progression").get_json()["canLevelDown"] is False
    floor = client.post(f"{BASE}/characters/{cid}/level-down", json={"expectedLevel": 1})
    assert floor.status_code == 409 and floor.get_json()["error"] == "min_level"
    award(client, cid, mode="milestone", milestoneTarget=3)
    need = client.post(f"{BASE}/characters/{cid}/level-up/preview", json={"classKey": "fighter"}).get_json()["needs"]
    state = db.session.get(Character, cid).character_data["srd"]["state"]
    payload = payload_from_needs(data, need, evaluate(data, state), state)
    assert client.post(f"{BASE}/characters/{cid}/level-up", json={**payload, "expectedLevel": 1}).status_code == 200
    body = client.post(f"{BASE}/characters/{cid}/level-down", json={"expectedLevel": 2}).get_json()
    assert body["level"] == 1 and body["status"]["milestoneTarget"] == 1


def test_dm_cannot_level_down(app, client, other, data):
    t = table(app, client, other, data)
    assert t["dm"].post(f"{BASE}/characters/{t['char']['id']}/level-down", json={"expectedLevel": 5}).status_code == 403


# ------------------------------------------------------------------ archive

def test_archive_hides_and_restores(client, other, data):
    cid = finalized(client, data)["id"]
    names = lambda url: [c["id"] for c in client.get(url).get_json()]  # noqa: E731
    assert cid in names("/api/characters/mine")
    assert other.post(f"{BASE}/characters/{cid}/archive", json={"archived": True}).status_code == 403
    assert client.post(f"{BASE}/characters/{cid}/archive", json={"archived": "yes"}).status_code == 400
    resp = client.post(f"{BASE}/characters/{cid}/archive", json={"archived": True})
    assert resp.status_code == 200 and resp.get_json()["archived"] is True
    assert cid not in names("/api/characters/mine")
    assert cid in names("/api/characters/mine?archived=only")
    assert client.get(f"{BASE}/characters/{cid}/progression").get_json()["archived"] is True
    assert db.session.get(Character, cid).character_data["srd"]["history"][-1]["type"] == "archive"
    resp = client.post(f"{BASE}/characters/{cid}/archive", json={"archived": False})
    assert resp.get_json()["archived"] is False
    assert cid in names("/api/characters/mine") and cid not in names("/api/characters/mine?archived=only")
    assert "lifecycle" not in db.session.get(Character, cid).character_data


def test_characters_in_a_campaign_cannot_be_archived(app, client, other, data):
    t = table(app, client, other, data)
    resp = client.post(f"{BASE}/characters/{t['char']['id']}/archive", json={"archived": True})
    assert resp.status_code == 409 and resp.get_json()["error"] == "in_campaign"


# ------------------------------------------------------------------ duplicate

def test_duplicate_is_an_independent_copy(client, other, data):
    char = finalized(client, data)
    cid = char["id"]
    db.session.add(InventoryItem(character_id=cid, name="Seil", quantity=2))
    row = db.session.get(Character, cid)
    row.avatar_storage_key = "secret/key"
    db.session.commit()
    assert other.post(f"{BASE}/characters/{cid}/duplicate").status_code == 403

    resp = client.post(f"{BASE}/characters/{cid}/duplicate")
    assert resp.status_code == 201, resp.get_json()
    copy_id = resp.get_json()["character"]["id"]
    assert copy_id != cid
    copy_row, source = db.session.get(Character, copy_id), db.session.get(Character, cid)
    assert copy_row.name == f"{source.name} (Kopie)" and copy_row.campaign_id is None
    assert copy_row.user_id == source.user_id and copy_row.level == source.level and copy_row.hp_max == source.hp_max
    assert copy_row.avatar_storage_key is None
    assert [i.name for i in copy_row.inventory] == ["Seil"] and copy_row.inventory[0].character_id == copy_id
    assert copy_row.character_data["srd"]["state"] == source.character_data["srd"]["state"]
    assert [h["type"] for h in copy_row.character_data["srd"]["history"]] == ["duplicate"]
    # changing one does not change the other
    award(client, copy_id, addXp=1000)
    assert db.session.get(Character, cid).xp == 6500
    assert client.get(f"{BASE}/characters/{copy_id}/progression").get_json()["status"]["xp"] == 7500


def test_duplicate_of_an_archived_character_is_active(client, data):
    cid = finalized(client, data)["id"]
    client.post(f"{BASE}/characters/{cid}/archive", json={"archived": True})
    copy_id = client.post(f"{BASE}/characters/{cid}/duplicate").get_json()["character"]["id"]
    assert copy_id in [c["id"] for c in client.get("/api/characters/mine").get_json()]


# ------------------------------------------------------------------ rebuild as draft

def test_to_draft_creates_an_editable_draft(client, other, data):
    cid = finalized(client, data)["id"]
    assert other.post(f"{BASE}/characters/{cid}/to-draft").status_code == 403
    resp = client.post(f"{BASE}/characters/{cid}/to-draft")
    assert resp.status_code == 201, resp.get_json()
    draft = resp.get_json()["draft"]
    assert draft["status"] == "draft" and draft["name"] == "Mira Eulenfeder" and draft["character_id"] is None
    full = client.get(f"{BASE}/drafts/{draft['id']}").get_json()
    assert full["draft"]["state"] == db.session.get(Character, cid).character_data["srd"]["state"]
    assert full["blockers"] == []
    assert draft["id"] in [d["id"] for d in client.get(f"{BASE}/drafts").get_json()["drafts"]]
    assert db.session.get(Character, cid).level == 5


def test_to_draft_respects_the_draft_limit(client, data, monkeypatch):
    from vtt.characters import srd_creator

    cid = finalized(client, data)["id"]
    monkeypatch.setattr(srd_creator, "MAX_OPEN_DRAFTS", 0)
    assert client.post(f"{BASE}/characters/{cid}/to-draft").status_code == 409


# ------------------------------------------------------------------ companions

def test_companions_roundtrip_and_validation(client, other, data):
    cid = finalized(client, data)["id"]
    url = f"{BASE}/characters/{cid}/companions"
    assert client.get(url).get_json()["companions"] == []
    wolf = {"name": " Wolf ", "kind": "Tier", "hpMax": 11, "hpCurrent": 99, "ac": 13, "speed": "40 ft.", "attacks": "Biss +4, 2d4+2", "notes": "Rudelführer"}
    resp = client.put(url, json={"companions": [wolf, {**wolf, "name": "Rabe", "hpMax": 1, "hpCurrent": 1}]})
    assert resp.status_code == 200, resp.get_json()
    stored = resp.get_json()["companions"]
    assert [c["name"] for c in stored] == ["Wolf", "Rabe"] and stored[0]["hpCurrent"] == 11
    assert stored[0]["id"] and stored[0]["id"] != stored[1]["id"]
    assert client.get(url).get_json()["companions"] == stored
    assert other.get(url).status_code == 403
    assert other.put(url, json={"companions": []}).status_code == 403
    again = client.put(url, json={"companions": stored}).get_json()["companions"]
    assert [c["id"] for c in again] == [c["id"] for c in stored]
    assert client.put(url, json={"companions": []}).get_json()["companions"] == []

    for bad in (
        {"companions": "x"}, {"companions": [1]}, {"companions": [{"name": ""}]}, {"companions": [{"name": "A" * 61}]},
        {"companions": [{"name": "A", "hpMax": -1}]}, {"companions": [{"name": "A", "hpMax": 1.5}]}, {"companions": [{"name": "A", "ac": 51}]},
        {"companions": [{"name": "A", "notes": "n" * 2001}]}, {"companions": [{"name": "A", "id": "../x"}]},
        {"companions": [{"name": "A"}] * 21},
    ):
        resp = client.put(url, json=bad)
        assert resp.status_code in (400, 422), bad
    assert client.get(url).get_json()["companions"] == []


def test_companions_are_part_of_the_copy(client, data):
    cid = finalized(client, data)["id"]
    client.put(f"{BASE}/characters/{cid}/companions", json={"companions": [{"name": "Wolf", "hpMax": 5, "hpCurrent": 5}]})
    copy_id = client.post(f"{BASE}/characters/{cid}/duplicate").get_json()["character"]["id"]
    assert client.get(f"{BASE}/characters/{copy_id}/companions").get_json()["companions"][0]["name"] == "Wolf"


# ------------------------------------------------------------------ non-SRD characters stay untouched

def test_non_srd_characters_have_no_management(client):
    plain = client.post("/api/characters", json={"name": "Alt", "level": 1}).get_json()
    pid = plain["id"]
    for method, path, body in (
        ("post", "archive", {"archived": True}), ("post", "duplicate", None), ("post", "to-draft", None),
        ("post", "level-down", {"expectedLevel": 1}), ("get", "companions", None), ("put", "companions", {"companions": []}),
    ):
        resp = getattr(client, method)(f"{BASE}/characters/{pid}/{path}", **({"json": body} if body is not None else {}))
        assert resp.status_code == 422, path
    assert pid in [c["id"] for c in client.get("/api/characters/mine").get_json()]
