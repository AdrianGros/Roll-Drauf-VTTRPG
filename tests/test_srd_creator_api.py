"""P3: SRD character creator drafts, finalizing, persistence and source-package model."""

import copy

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles
from vtt.models.srd_creator_draft import SrdCreatorDraft
from vtt.rules_content.creator_drafts import SYSTEM_ID, character_values, finalize_blockers, sanitize_state
from vtt.rules_content.creator_rules import evaluate, load_creator_data
from vtt.rules_content.creator_sources import SRD_SOURCE_ID, pin_sources, pin_status, validate_source_ids

BASE = "/api/srd-creator"


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        yield app
        db.session.remove()
        db.drop_all()


def _user(app, name):
    with app.app_context():
        role = Role.query.filter_by(name="Player").first()
        user = User(username=name, email=f"{name}@example.com", role_id=role.id)
        user.set_password("Srd-Pass-123!")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "username": name, "password": "Srd-Pass-123!"}


def _client(app, name):
    info = _user(app, name)
    client = app.test_client()
    resp = client.post("/api/auth/login", json={"username": info["username"], "password": info["password"]})
    assert resp.status_code == 200
    client.user_id = info["id"]
    return client


@pytest.fixture
def client(app):
    return _client(app, "srd_owner")


@pytest.fixture
def other(app):
    return _client(app, "srd_other")


@pytest.fixture(scope="module")
def data():
    return load_creator_data()


def wizard_state(data, name="Mira Eulenfeder"):
    cantrips = [sid for sid in data["spellLists"]["wizard"] if data["spells"][sid]["level"] == 0][:4]
    book = [sid for sid in data["spellLists"]["wizard"] if 1 <= data["spells"][sid]["level"] <= 3][:14]
    return {
        "abilityMethod": "manual",
        "abilityBase": {"str": 8, "dex": 12, "con": 13, "int": 15, "wis": 14, "cha": 10},
        "levels": [{"classKey": "wizard"}] * 5,
        "background": {"id": "character-origins.backgrounds.sage", "abilityBonus": {"int": 2, "con": 1}},
        "species": {"id": "character-origins.species.halfling", "choices": {}},
        "subclasses": {"wizard": "classes.wizard.subclass-evoker"},
        "skills": {"class": ["heilkunde", "nachforschungen"], "expertise": ["arkane-kunde"]},
        "advancements": [{"classKey": "wizard", "classLevel": 4, "kind": "asi", "increases": {"int": 2}}],
        "spells": {"wizard": {"cantrips": cantrips, "spellbook": book, "prepared": book[:9]}},
        "identity": {"name": name, "alignment": "neutral-gut", "backstory": "Fand eine Eule."},
    }


def make_draft(client, state=None, **extra):
    resp = client.post(f"{BASE}/drafts", json={"state": state if state is not None else {}, **extra})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ------------------------------------------------------------------ pure modules

def test_sanitize_rejects_unknown_fields_depth_size_and_garbage(data):
    clean, problems = sanitize_state({"levels": [], "derived": {"hp": 999}}, data)
    assert [p["path"] for p in problems] == ["derived"] and "derived" not in clean
    deep = {"overrides": {}}
    node = deep["overrides"]
    for _ in range(12):
        node["x"] = {}
        node = node["x"]
    assert sanitize_state(deep, data)[1]
    assert sanitize_state({"identity": {"backstory": "x" * 9000}}, data)[1]
    assert sanitize_state({"identity": {"name": "x" * 101}}, data)[1]
    assert sanitize_state({"identity": {"alignment": "chaos-boss"}}, data)[1]
    assert sanitize_state({"identity": {"mystery": "x"}}, data)[1]
    assert sanitize_state({"levels": [{"classKey": "wizard"}] * 500}, data)[1]
    assert sanitize_state({"abilityBase": {"str": float("inf")}}, data)[1]
    assert sanitize_state([1, 2], data)[1]
    assert sanitize_state(None, data) == ({}, [])
    assert sanitize_state({"sources": ["gibts-nicht"]}, data)[1]
    assert sanitize_state({"sources": []}, data)[1]
    assert sanitize_state({"sources": [SRD_SOURCE_ID]}, data)[1] == []


def test_source_model_pins_and_detects_drift(data):
    pins = pin_sources(data)
    assert pins == [pin_sources(data, [SRD_SOURCE_ID])[0]]
    assert pins[0]["id"] == SRD_SOURCE_ID and pins[0]["license"] == "CC-BY-4.0"
    assert pins[0]["version"] == data["rulesetVersion"] and pins[0]["digest"] == data["packageDigest"]
    assert pin_status(data, pins) == "current"
    stale = copy.deepcopy(pins)
    stale[0]["digest"] = "sha256:0"
    assert pin_status(data, stale) == "drifted"
    assert pin_status(data, None) == "drifted" and pin_status(data, ["x"]) == "drifted"
    assert validate_source_ids(None) == []
    assert validate_source_ids(["a", "a"])


def test_character_values_are_derived_from_the_evaluation_only(data):
    state = wizard_state(data)
    evaluation = evaluate(data, state)
    assert finalize_blockers(evaluation, state) == []
    values = character_values(data, state, evaluation, draft_id=7, finalized_at="2026-10-18T10:00:00Z")
    assert values["class_name"] == "Magier" and values["race"] == "Halbling" and values["background"] == "Weiser"
    assert (values["level"], values["xp"], values["proficiency_bonus"]) == (5, 6500, 3)
    assert values["int_score"] == 19 and values["hp_max"] == values["hp_current"] == evaluation["hitPoints"]["max"]
    assert values["character_data"]["system_id"] == SYSTEM_ID
    assert values["character_data"]["srd"]["sources"][0]["digest"] == data["packageDigest"]


def test_multiclass_class_name_is_compact_and_capped(data):
    state = wizard_state(data)
    state["levels"] = [{"classKey": "fighter"}] * 3 + [{"classKey": "wizard"}] * 2
    values = character_values(data, state, evaluate(data, state), draft_id=1, finalized_at="x")
    assert values["class_name"] == "Kämpfer 3 / Magier 2" and len(values["class_name"]) <= 50


# ------------------------------------------------------------------ API: access

def test_requires_authentication(app):
    anonymous = app.test_client()
    for method, path in (("get", "/meta"), ("get", "/drafts"), ("post", "/drafts"), ("post", "/evaluate"), ("get", "/creator-data")):
        assert getattr(anonymous, method)(BASE + path).status_code == 401, path


def test_meta_and_creator_data(client, data):
    meta = client.get(f"{BASE}/meta").get_json()
    assert meta["systemId"] == SYSTEM_ID and meta["rulesetId"] == "srd-5.2.1-de" and meta["maxLevel"] == 20
    assert [s["id"] for s in meta["sources"]] == [SRD_SOURCE_ID] and meta["defaultSources"] == [SRD_SOURCE_ID]
    assert client.get(f"{BASE}/creator-data").get_json()["packageDigest"] == data["packageDigest"]


def test_drafts_are_private_to_their_owner(client, other):
    draft = make_draft(client)["draft"]
    url = f"{BASE}/drafts/{draft['id']}"
    assert other.get(url).status_code == 404
    assert other.put(url, json={"version": 1, "state": {}}).status_code == 404
    assert other.delete(url).status_code == 404
    assert other.post(f"{url}/finalize", json={"version": 1}).status_code == 404
    assert other.get(f"{BASE}/drafts").get_json()["drafts"] == []
    assert client.get(url).status_code == 200


# ------------------------------------------------------------------ API: draft lifecycle

def test_create_get_list_and_server_side_evaluation(client):
    created = make_draft(client, step="species")
    draft = created["draft"]
    assert (draft["status"], draft["version"], draft["step"], draft["state"]) == ("draft", 1, "species", {})
    assert created["evaluation"]["complete"] is False and created["blockers"]
    fetched = client.get(f"{BASE}/drafts/{draft['id']}").get_json()
    assert fetched["draft"]["id"] == draft["id"] and fetched["evaluation"] == created["evaluation"]
    assert [d["id"] for d in client.get(f"{BASE}/drafts").get_json()["drafts"]] == [draft["id"]]


def test_update_bumps_version_and_rechecks_rules(client, data):
    draft = make_draft(client)["draft"]
    state = wizard_state(data)
    state["abilityBase"]["str"] = 99
    resp = client.put(f"{BASE}/drafts/{draft['id']}", json={"version": 1, "state": state, "step": "review"})
    body = resp.get_json()
    assert resp.status_code == 200 and body["draft"]["version"] == 2 and body["draft"]["step"] == "review"
    assert body["draft"]["name"] == "Mira Eulenfeder"
    assert "manual-range" in {f["code"] for f in body["evaluation"]["findings"]}
    assert body["evaluation"]["valid"] is False, "invalid rules are stored as a draft but reported"


def test_stale_and_missing_versions_are_refused(client):
    draft = make_draft(client)["draft"]
    url = f"{BASE}/drafts/{draft['id']}"
    assert client.put(url, json={"version": 1, "step": "a"}).status_code == 200
    stale = client.put(url, json={"version": 1, "step": "b"})
    assert stale.status_code == 409 and stale.get_json()["error"] == "version_conflict"
    assert stale.get_json()["draft"]["version"] == 2 and stale.get_json()["draft"]["step"] == "a"
    assert client.put(url, json={"step": "b"}).status_code == 400
    assert client.put(url, json={"version": "2"}).status_code == 400
    assert client.put(url, json={"version": True}).status_code == 400


def test_invalid_input_is_refused_without_storing(client):
    draft = make_draft(client)["draft"]
    url = f"{BASE}/drafts/{draft['id']}"
    for bad in ({"derived": {}}, {"identity": {"name": 5}}, {"levels": "x" * 3000}):
        resp = client.put(url, json={"version": 1, "state": bad})
        assert resp.status_code == 422 and resp.get_json()["problems"], bad
    assert client.put(url, json={"version": 1, "step": "Not Valid!"}).status_code == 400
    assert client.post(f"{BASE}/drafts", json={"state": {"nope": 1}}).status_code == 422
    assert client.post(f"{BASE}/drafts", data="not json", content_type="application/json").status_code == 400
    assert client.get(url).get_json()["draft"]["version"] == 1


def test_discard_hides_the_draft_and_frees_the_slot(client):
    draft = make_draft(client)["draft"]
    url = f"{BASE}/drafts/{draft['id']}"
    assert client.delete(url).get_json() == {"discarded": True}
    assert client.get(url).status_code == 404
    assert client.put(url, json={"version": 2}).status_code == 404
    assert client.get(f"{BASE}/drafts").get_json()["drafts"] == []


def test_open_draft_limit(client):
    for _ in range(25):
        make_draft(client)
    resp = client.post(f"{BASE}/drafts", json={"state": {}})
    assert resp.status_code == 409 and resp.get_json()["error"] == "draft_limit"


def test_stateless_evaluate(client, data):
    resp = client.post(f"{BASE}/evaluate", json={"state": wizard_state(data)})
    body = resp.get_json()
    assert resp.status_code == 200 and body["evaluation"]["complete"] and body["blockers"] == []
    assert body["evaluation"]["abilities"]["int"]["score"] == 19
    assert client.post(f"{BASE}/evaluate", json={"state": {"zzz": 1}}).status_code == 422
    assert client.post(f"{BASE}/evaluate", json=[]).status_code == 400


# ------------------------------------------------------------------ API: finalize

def test_finalize_requires_a_complete_valid_draft(client):
    draft = make_draft(client)["draft"]
    resp = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1})
    body = resp.get_json()
    assert resp.status_code == 422 and body["error"] == "draft_incomplete"
    assert {"no-class", "name-missing"} <= {b["code"] for b in body["blockers"]}
    assert Character.query.count() == 0


def test_finalize_needs_a_name(client, data):
    state = wizard_state(data)
    del state["identity"]["name"]
    draft = make_draft(client, state)["draft"]
    resp = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1})
    assert resp.status_code == 422 and [b["code"] for b in resp.get_json()["blockers"]] == ["name-missing"]


def test_finalize_blocks_rule_errors(client, data):
    state = wizard_state(data)
    state["abilityBase"]["str"] = 99
    draft = make_draft(client, state)["draft"]
    resp = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1})
    assert resp.status_code == 422 and "manual-range" in {b["code"] for b in resp.get_json()["blockers"]}


def test_finalize_creates_exactly_one_character_and_is_idempotent(app, client, data):
    state = wizard_state(data)
    draft = make_draft(client, state)["draft"]
    evaluation = evaluate(data, state)
    url = f"{BASE}/drafts/{draft['id']}/finalize"

    resp = client.post(url, json={"version": 1})
    body = resp.get_json()
    assert resp.status_code == 201 and body["alreadyFinalized"] is False, body
    sheet = body["character"]
    assert sheet["name"] == "Mira Eulenfeder" and sheet["level"] == 5 and sheet["system_id"] == SYSTEM_ID
    assert sheet["class"] == "Magier" and sheet["species"] == "Halbling" and sheet["background"] == "Weiser"

    with app.app_context():
        char = db.session.get(Character, sheet["id"])
        assert char.user_id == client.user_id and char.campaign_id is None
        assert (char.hp_max, char.hp_current, char.ac) == (evaluation["hitPoints"]["max"], evaluation["hitPoints"]["max"], 11)
        assert (char.str_score, char.int_score, char.con_score) == (8, 19, 14)
        assert (char.proficiency_bonus, char.xp, char.mana_max) == (3, 6500, 0)
        block = char.character_data["srd"]
        assert char.character_data["system_id"] == SYSTEM_ID
        assert block["derived"] == evaluation and block["state"] == state and block["draftId"] == draft["id"]
        assert block["sources"][0]["digest"] == data["packageDigest"] and block["sources"][0]["license"] == "CC-BY-4.0"
        row = db.session.get(SrdCreatorDraft, draft["id"])
        assert (row.status, row.character_id, row.version) == ("finalized", char.id, 2)

    again = client.post(url, json={"version": 1})
    assert again.status_code == 200 and again.get_json()["alreadyFinalized"] is True
    assert again.get_json()["character"]["id"] == sheet["id"]
    with app.app_context():
        assert Character.query.count() == 1
    assert client.put(f"{BASE}/drafts/{draft['id']}", json={"version": 2, "step": "x"}).status_code == 409
    assert client.delete(f"{BASE}/drafts/{draft['id']}").status_code == 409
    assert client.get(f"{BASE}/drafts").get_json()["drafts"] == []


def test_finalize_refuses_stale_version_and_unknown_campaign(app, client, data):
    draft = make_draft(client, wizard_state(data))["draft"]
    url = f"{BASE}/drafts/{draft['id']}/finalize"
    assert client.post(url, json={"version": 5}).status_code == 409
    assert client.post(url, json={}).status_code == 400
    assert client.post(url, json={"version": 1, "campaign_id": 987654}).status_code == 404
    with app.app_context():
        assert Character.query.count() == 0
        assert db.session.get(SrdCreatorDraft, draft["id"]).status == "draft"


def test_client_cannot_inject_derived_values(app, client, data):
    state = wizard_state(data)
    draft = make_draft(client, state)["draft"]
    assert client.put(f"{BASE}/drafts/{draft['id']}", json={"version": 1, "state": {**state, "hp_max": 999}}).status_code == 422
    resp = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1, "hp_max": 999, "ac": 30, "level": 20})
    assert resp.status_code == 201
    assert (resp.get_json()["character"]["level"], resp.get_json()["character"]["ac"]) == (5, 11)


def test_overrides_flow_through_to_the_character(client, data, app):
    state = wizard_state(data)
    state["overrides"] = {"armorClass": {"set": 17, "reason": "Magische Robe der Spielleitung"}}
    draft = make_draft(client, state)["draft"]
    resp = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1})
    assert resp.status_code == 201 and resp.get_json()["character"]["ac"] == 17


# ------------------------------------------------------------------ API: character access + generic-API guard

def finalized(client, data, name="Mira Eulenfeder"):
    draft = make_draft(client, wizard_state(data, name))["draft"]
    resp = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={"version": 1})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["character"]


def test_srd_character_endpoint(client, other, data):
    char = finalized(client, data)
    body = client.get(f"{BASE}/characters/{char['id']}").get_json()
    assert body["sourceStatus"] == "current" and body["srd"]["schema"] == "roll-drauf.srd-character.v1"
    assert body["evaluation"] == body["srd"]["derived"]
    assert other.get(f"{BASE}/characters/{char['id']}").status_code == 403
    plain = client.post("/api/characters", json={"name": "Plain", "level": 1})
    assert plain.status_code == 201
    assert client.get(f"{BASE}/characters/{plain.get_json()['id']}").status_code == 422
    assert client.get(f"{BASE}/characters/99999").status_code == 404


def test_pins_report_drift_when_the_package_changes(app, client, data):
    char = finalized(client, data)
    with app.app_context():
        row = db.session.get(Character, char["id"])
        block = copy.deepcopy(row.character_data)
        block["srd"]["sources"][0]["digest"] = "sha256:old"
        row.character_data = block
        db.session.commit()
    assert client.get(f"{BASE}/characters/{char['id']}").get_json()["sourceStatus"] == "drifted"


def test_generic_character_api_cannot_rewrite_derived_srd_fields(app, client, data):
    char = finalized(client, data)
    url = f"/api/characters/{char['id']}"
    for field, value in (("ac", 30), ("hp_max", 999), ("level", 20), ("int", 30), ("race", "Elf"), ("character_data", {})):
        resp = client.put(url, json={field: value})
        assert resp.status_code == 409 and resp.get_json()["error"] == "srd_character_managed", field
    assert client.put(url, json={"name": "Neuer Name", "hp_current": 3}).status_code == 200
    with app.app_context():
        row = db.session.get(Character, char["id"])
        assert (row.name, row.hp_current, row.ac, row.level) == ("Neuer Name", 3, 11, 5)


def test_srd_characters_cannot_be_forged_through_the_generic_api(client, data):
    forged = {"system_id": SYSTEM_ID, "srd": {"derived": {}}}
    assert client.post("/api/characters", json={"name": "Fake", "character_data": forged}).status_code == 400
    assert client.post("/api/characters", json={"name": "Fake", "character_data": {"srd": {}}}).status_code == 400
    plain = client.post("/api/characters", json={"name": "Plain"}).get_json()
    assert client.put(f"/api/characters/{plain['id']}", json={"character_data": forged}).status_code == 400
    assert client.put(f"/api/characters/{plain['id']}", json={"character_data": {"note": "ok"}}).status_code == 200


def test_old_creators_are_unaffected(client):
    rdl = client.post("/api/characters", json={"name": "Held", "species": "mensch", "faction": "rote-rose", "class": "kaempfer", "background": "soldat"})
    assert rdl.status_code == 201 and rdl.get_json()["system_id"] == "roll_drauf_light"
    assert client.put(f"/api/characters/{rdl.get_json()['id']}", json={"ac": 12}).status_code == 200
