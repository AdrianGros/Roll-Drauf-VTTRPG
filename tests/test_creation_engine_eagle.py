"""Creation Engine = Eagle Homebrew: the Flight Control request contract, worlds, rights and the page."""

import copy

import pytest
from flask_jwt_extended import create_access_token

from vtt import create_app
from vtt.creation_engine import documents as rules
from vtt.creation_engine.models import CeEagleDocument
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Role, User

WEAPON = {"name": "Flammenklinge", "type": "weapon",
          "system": {"type": {"value": "martialM"}, "source": {"rules": "2024"},
                     "activities": {"a1": {"type": "attack", "activation": {"type": "action"}},
                                    "foreign": {"type": "utility"}}},
          "flags": {"other-module": {"keep": True}}}


@pytest.fixture
def ce_app():
    app = create_app(config_name="testing")
    app.config["CE_AUTHORING"] = True
    with app.app_context():
        db.create_all()
        role = Role.query.filter_by(name="DM").first() or Role(name="DM")
        db.session.add(role)
        db.session.flush()
        users = {}
        for name in ("gm", "codm", "player", "stranger"):
            users[name] = User(username=f"ce-{name}", email=f"{name}@example.test", password_hash="x",
                               role_id=role.id, is_active=True, is_suspended=False, account_state="active")
            db.session.add(users[name])
        db.session.flush()
        campaign = Campaign(name="Eagle Kampagne", owner_id=users["gm"].id)
        db.session.add(campaign)
        db.session.flush()
        db.session.add(CampaignMember(campaign_id=campaign.id, user_id=users["codm"].id, campaign_role="CO_DM", status="active"))
        db.session.add(CampaignMember(campaign_id=campaign.id, user_id=users["player"].id, campaign_role="PLAYER", status="active"))
        db.session.commit()
        ids = {name: user.id for name, user in users.items()}
        tokens = {name: create_access_token(identity=str(user_id)) for name, user_id in ids.items()}
        world = f"campaign:{campaign.id}"
    yield app, ids, tokens, world
    with app.app_context():
        db.session.remove()
        db.drop_all()


def client_for(app, tokens, name):
    client = app.test_client()
    client.set_cookie("access_token_cookie", tokens[name])
    return client


def send(client, world, type_, payload):
    response = client.post("/api/ce/authoring/request", json={"world": world, "type": type_, "payload": payload})
    assert response.status_code == 200
    return response.json


def create_pair(client, world, document_id="Abc123", data=WEAPON, pack="world.eagle-weapons-2024"):
    library = send(client, world, "document.create", {"target": {"pack": pack}, "id": document_id,
                                                      "data": {**data, "flags": {**data["flags"], "eagle-homebrew": {"pair": {"world": "Item"}}}}})
    world_side = send(client, world, "document.create", {"target": {"world": "Item"}, "id": document_id,
                                                         "data": {**data, "flags": {**data["flags"], "eagle-homebrew": {"pair": {"pack": pack}}}}})
    return library, world_side


def test_create_pair_is_idempotent_and_foundry_shaped(ce_app):
    app, _, tokens, world = ce_app
    gm = client_for(app, tokens, "gm")
    library, world_side = create_pair(gm, world)
    assert library == {"ok": True, "value": {"created": True, "uuid": "Compendium.world.eagle-weapons-2024.Item.Abc123"}}
    assert world_side == {"ok": True, "value": {"created": True, "uuid": "Item.Abc123"}}
    again, _ = create_pair(gm, world)
    assert again["value"] == {"created": False, "uuid": "Compendium.world.eagle-weapons-2024.Item.Abc123"}
    document = gm.get("/api/ce/authoring/document", query_string={"world": world, "uuid": "Item.Abc123"}).json["document"]
    assert document["source"]["_id"] == "Abc123"
    assert document["source"]["flags"]["eagle-homebrew"]["pair"] == {"pack": "world.eagle-weapons-2024"}
    index = gm.get("/api/ce/authoring/index", query_string={"pack": "world.eagle-weapons-2024"}).json["index"]
    assert index == [{"_id": "Abc123", "name": "Flammenklinge", "type": "weapon", "requirements": None}]


def test_update_replaces_each_path_value_and_keeps_everything_else(ce_app):
    app, _, tokens, world = ce_app
    gm = client_for(app, tokens, "gm")
    create_pair(gm, world)
    # Matt's editor sends the complete projected mapping: removing an Activity means it is absent.
    result = send(gm, world, "document.update", {"uuid": "Item.Abc123", "changes": {
        "system.activities": {"foreign": {"type": "utility"}, "a2": {"type": "save"}},
        "name": "Frostklinge", "flags.eagle-homebrew.pair": {"pack": "world.eagle-weapons-2024"},
        "system.-=source": None}})
    assert result["ok"] is True
    assert sorted(result["value"]["changed"]) == ["flags.eagle-homebrew.pair", "name", "system.-=source", "system.activities"]
    source = gm.get("/api/ce/authoring/document", query_string={"world": world, "uuid": "Item.Abc123"}).json["document"]["source"]
    assert source["system"]["activities"] == {"foreign": {"type": "utility"}, "a2": {"type": "save"}}
    assert "source" not in source["system"]
    assert source["system"]["type"] == {"value": "martialM"}
    assert source["flags"]["other-module"] == {"keep": True}
    assert source["name"] == "Frostklinge"


@pytest.mark.parametrize("changes, detail", [
    ({f"system.p{i}": i for i in range(51)}, "at most 50 paths"),
    ({"_id": "other"}, "cannot be changed"),
    ({"type": "spell"}, "cannot be changed"),
    ({"system.__proto__.x": 1}, "invalid path"),
    ({"name": ""}, "name must be"),
    ({}, "non-empty"),
])
def test_update_limits_answer_like_flight_control(ce_app, changes, detail):
    app, _, tokens, world = ce_app
    gm = client_for(app, tokens, "gm")
    create_pair(gm, world)
    result = send(gm, world, "document.update", {"uuid": "Item.Abc123", "changes": changes})
    assert result["ok"] is False and result["reason"] == "invalid-payload" and detail in result["detail"]
    with app.app_context():
        assert db.session.query(CeEagleDocument).filter_by(document_id="Abc123", pack="").one().revision == 1


@pytest.mark.parametrize("payload, reason", [
    ({"target": {"pack": "world.eagle-weapons"}, "id": "X1", "data": WEAPON}, "invalid-payload"),  # versioned kind needs a version
    ({"target": {"pack": "world.eagle-groups-2024"}, "id": "X1", "data": WEAPON}, "invalid-payload"),  # unversioned kind has none
    ({"target": {"pack": "world.eagle-spells-2024"}, "id": "X1", "data": WEAPON}, "invalid-payload"),  # wrong subtype
    ({"target": {"world": "Item"}, "id": "X1", "data": {**WEAPON, "type": "character"}}, "invalid-payload"),
    ({"target": {"world": "JournalEntry"}, "id": "X1", "data": WEAPON}, "invalid-payload"),
    ({"target": {"world": "Item"}, "id": "bad id!", "data": WEAPON}, "invalid-payload"),
    ({"target": {"world": "Item"}, "id": "X1"}, "invalid-payload"),
])
def test_create_rejects_what_does_not_fit_the_catalog(ce_app, payload, reason):
    app, _, tokens, world = ce_app
    result = send(client_for(app, tokens, "gm"), world, "document.create", payload)
    assert result["ok"] is False and result["reason"] == reason


def test_unknown_request_type(ce_app):
    app, _, tokens, world = ce_app
    assert send(client_for(app, tokens, "gm"), world, "document.delete", {})["reason"] == "unknown-request"


def test_compendium_import_retrofits_a_world_document_under_its_own_id(ce_app):
    app, _, tokens, world = ce_app
    gm = client_for(app, tokens, "gm")
    send(gm, world, "document.create", {"target": {"world": "Item"}, "id": "Old1", "data": WEAPON})
    payload = {"pack": "world.eagle-weapons-2024", "sources": [
        {"source": "Item.Old1", "id": "Old1", "changes": {"flags.eagle-homebrew.pair": {"world": "Item"}}}]}
    first = send(gm, world, "compendium.import", payload)
    assert first == {"ok": True, "value": {"created": [{"uuid": "Compendium.world.eagle-weapons-2024.Item.Old1"}], "existed": []}}
    second = send(gm, world, "compendium.import", payload)
    assert second["value"] == {"created": [], "existed": [{"uuid": "Compendium.world.eagle-weapons-2024.Item.Old1"}]}
    library = gm.get("/api/ce/authoring/document", query_string={
        "world": world, "uuid": "Compendium.world.eagle-weapons-2024.Item.Old1"}).json["document"]["source"]
    assert library["flags"]["eagle-homebrew"]["pair"] == {"world": "Item"}
    assert library["flags"]["other-module"] == {"keep": True}
    mismatch = send(gm, world, "compendium.import", {"pack": "world.eagle-weapons-2024", "sources": [
        {"source": "Item.Old1", "id": "Other"}]})
    assert mismatch["ok"] is False


def test_world_rights_follow_campaign_leadership(ce_app):
    app, _, tokens, world = ce_app
    create_pair(client_for(app, tokens, "gm"), world)
    codm = client_for(app, tokens, "codm")
    assert send(codm, world, "document.update", {"uuid": "Item.Abc123", "changes": {"name": "Co"}})["ok"] is True
    for name in ("player", "stranger"):
        other = client_for(app, tokens, name)
        assert send(other, world, "document.update", {"uuid": "Item.Abc123", "changes": {"name": "Nope"}})["reason"] == "not-permitted"
        assert other.get("/api/ce/authoring/documents", query_string={"world": world}).status_code == 403
    worlds = client_for(app, tokens, "player").get("/api/ce/authoring/worlds").json["worlds"]
    assert [entry["id"] for entry in worlds] == ["personal"]
    assert [entry["id"] for entry in codm.get("/api/ce/authoring/worlds").json["worlds"]] == ["personal", world]


def test_library_and_personal_world_are_private(ce_app):
    app, ids, tokens, world = ce_app
    gm = client_for(app, tokens, "gm")
    create_pair(gm, "personal")
    stranger = client_for(app, tokens, "stranger")
    assert stranger.get("/api/ce/authoring/index", query_string={"pack": "world.eagle-weapons-2024"}).json["index"] == []
    assert stranger.get("/api/ce/authoring/document", query_string={"uuid": "Item.Abc123"}).json["document"] is None
    assert send(stranger, "personal", "document.update", {"uuid": "Item.Abc123", "changes": {"name": "x"}})["ok"] is False
    listing = gm.get("/api/ce/authoring/documents", query_string={"world": "personal"}).json
    assert [entry["uuid"] for entry in listing["world"]] == ["Item.Abc123"]
    assert [entry["uuid"] for entry in listing["library"]] == ["Compendium.world.eagle-weapons-2024.Item.Abc123"]
    # The same Library is reachable from a campaign world; campaign documents are separate.
    from_campaign = gm.get("/api/ce/authoring/documents", query_string={"world": world}).json
    assert from_campaign["world"] == [] and len(from_campaign["library"]) == 1


def test_delete_removes_one_side_only(ce_app):
    app, _, tokens, world = ce_app
    gm = client_for(app, tokens, "gm")
    create_pair(gm, world)
    assert gm.delete("/api/ce/authoring/document", query_string={"world": world, "uuid": "Item.Abc123"}).status_code == 200
    assert gm.get("/api/ce/authoring/document", query_string={"world": world, "uuid": "Item.Abc123"}).json["document"] is None
    assert gm.get("/api/ce/authoring/document", query_string={
        "world": world, "uuid": "Compendium.world.eagle-weapons-2024.Item.Abc123"}).json["document"] is not None
    assert gm.delete("/api/ce/authoring/document", query_string={"world": world, "uuid": "Item.Abc123"}).status_code == 404


def test_endpoints_need_a_usable_account(ce_app):
    app, ids, tokens, world = ce_app
    anonymous = app.test_client()
    assert anonymous.get("/api/ce/authoring/worlds").status_code == 401
    assert anonymous.post("/api/ce/authoring/request", json={}).status_code == 401
    page = anonymous.get("/api/ce/authoring")
    assert page.status_code == 302 and page.headers["Location"].startswith("/login.html")
    with app.app_context():
        db.session.get(User, ids["gm"]).is_suspended = True
        db.session.commit()
    assert client_for(app, tokens, "gm").get("/api/ce/authoring/worlds").status_code == 401


def test_page_hosts_eagle_homebrew(ce_app):
    app, _, tokens, _ = ce_app
    response = client_for(app, tokens, "gm").get("/api/ce/authoring")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "eagle-homebrew/creation-engine.js" in html and 'id="ce-eagle-mount"' in html
    assert response.headers["Cache-Control"] == "private, no-store"


def test_flag_off_hides_the_engine(ce_app):
    app, _, tokens, world = ce_app
    app.config["CE_AUTHORING"] = False
    gm = client_for(app, tokens, "gm")
    assert gm.get("/api/ce/authoring").status_code == 404
    assert gm.post("/api/ce/authoring/request", json={"world": world, "type": "document.create", "payload": {}}).status_code == 404
    assert gm.get("/api/dashboard/capabilities").json == {"authoring_available": False}


def test_capability_matches_the_page(ce_app):
    app, ids, tokens, _ = ce_app
    response = client_for(app, tokens, "gm").get("/api/dashboard/capabilities")
    assert response.json == {"authoring_available": True}


def test_apply_update_is_pure():
    source = {"name": "A", "system": {"x": {"y": 1}}}
    before = copy.deepcopy(source)
    with pytest.raises(rules.RequestFailure):
        rules.apply_update(source, {"system.x.y": float("nan")})
    assert source == before
    assert rules.apply_update(source, {"system.x.-=y": None, "system.z.w": [1]}) == ["system.x.-=y", "system.z.w"]
    assert source == {"name": "A", "system": {"x": {}, "z": {"w": [1]}}}
