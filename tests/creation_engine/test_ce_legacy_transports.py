"""WP7 compatibility through the actual character/combat/socket routes."""

import os

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, decode_token
from flask_socketio import SocketIO
from sqlalchemy import select
from sqlalchemy.orm import Session

from vtt.creation_engine.transports.legacy_host import install
from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.content import new_id
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.transports import register
from vtt.extensions import db, limiter
from vtt.models.character import Character
from vtt.models.equipment import Equipment
from vtt.models.token_state import TokenState

from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine, world, add_tokens, cutover, context, command

pytestmark = pytest.mark.postgres


@pytest.fixture
def legacy_transport(migration_engine):
    w = world(migration_engine, count=1)
    w["tokens"] = add_tokens(migration_engine, w)
    cutover(w)
    app = Flask("legacy-engine-test")
    app.config.update(TESTING=True, SECRET_KEY="ce-legacy-test-secret", JWT_SECRET_KEY="ce-legacy-jwt-secret-" * 3,
        SQLALCHEMY_DATABASE_URI=os.environ["CE_TEST_DATABASE_URL"], SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_TOKEN_LOCATION=["cookies"], JWT_COOKIE_CSRF_PROTECT=True, RATELIMIT_ENABLED=False, CE_RUNTIME=True)
    db.init_app(app)
    limiter.init_app(app)
    JWTManager(app)
    sio = SocketIO(app, async_mode="threading")
    from vtt.characters import characters_bp
    from vtt.campaigns import campaigns_bp
    from vtt.socket_handlers import register_socket_handlers
    app.register_blueprint(characters_bp, url_prefix="/api")
    app.register_blueprint(campaigns_bp, url_prefix="/api")
    register_socket_handlers(sio)
    register(app, sio)
    install(app, gateway=w["gateway"])
    clients = {}
    with app.app_context():
        host_engine = db.engine
        for user in (1, w["user"]):
            token = create_access_token(identity=str(user))
            client = app.test_client(); client.set_cookie("access_token_cookie", token)
            clients[user] = (client, decode_token(token))
    yield app, sio, clients, w
    with app.app_context():
        db.session.remove()
        host_engine._ce_legacy_guards()
        host_engine.dispose()


def headers(client_info, command_context):
    return {"X-CSRF-TOKEN": client_info[1]["csrf"], "X-CE-Authority-Epoch": str(command_context["authorityEpoch"]),
            "X-CE-Scope-Version": str(command_context["expectedScopeVersion"]), "Idempotency-Key": command_context["idempotencyKey"]}


def test_real_sheet_put_translates_once_and_all_representations_agree(legacy_transport):
    app, sio, clients, w = legacy_transport
    client_info = clients[w["user"]]
    client = client_info[0]
    h = headers(client_info, context(w))
    path = f"/api/characters/{w['characters'][0]}"
    first = client.put(path, json={"hp_current": 5}, headers=h)
    assert first.status_code == 200, first.json
    retry = client.put(path, json={"hp_current": 5}, headers=h)
    assert retry.json["receipt"] == first.json["receipt"]
    sheet = client.get(path + "/sheet")
    assert sheet.json["character"]["hp_current"] == 5
    assert sheet.headers["Cache-Control"] == "private, no-store"
    for token in w["tokens"]:
        response = client.get(f"/api/ce/migration/tokens/{token}/projection")
        assert response.status_code == 200 and response.json["hp_current"] == 5
    with app.app_context():
        assert db.session.get(Character, w["characters"][0]).hp_current == 8
        payload = db.session.get(TokenState, w["tokens"][0]).serialize()
        assert payload["hp_current"] is None and "engine" in payload


def test_sheet_export_and_collection_reads_use_current_policy(legacy_transport):
    app, sio, clients, w = legacy_transport
    path = f"/api/characters/{w['characters'][0]}"
    owner = clients[w["user"]][0].get(path + "/export")
    assert owner.json["export_kind"] == "creation_engine_legacy_compat"
    assert owner.json["character"]["character_data"]["secret"] == "kept private"
    for suffix in ("", "/sheet", "/export", "/equipment"):
        gm = clients[1][0].get(path + suffix)
        assert gm.status_code == 200
        assert "kept private" not in gm.get_data(as_text=True)
        assert "script" not in gm.get_data(as_text=True)


@pytest.mark.parametrize("method,suffix,body,code", [
    ("put", "", {"level": 4}, "LEGACY_FIELD_READ_ONLY"),
    ("put", "", {"hp_current": 5, "name": "Partial write"}, "LEGACY_FIELD_READ_ONLY"),
    ("put", "", {"campaign_id": 99}, "SCOPE_TRANSFER_UNSUPPORTED"),
    ("post", "/level-up", {}, "LEGACY_FIELD_READ_ONLY"),
    ("post", "/inventory", {"name": "New item"}, "LEGACY_FIELD_READ_ONLY"),
])
def test_unsupported_legacy_writers_are_rejected_before_writing(legacy_transport, method, suffix, body, code):
    app, sio, clients, w = legacy_transport
    info = clients[w["user"]]
    result = getattr(info[0], method)(f"/api/characters/{w['characters'][0]}" + suffix,
        json=body, headers=headers(info, context(w)))
    assert result.status_code == 409 and result.json["error"]["code"] == code


def test_old_client_without_authority_epoch_gets_conflict(legacy_transport):
    app, sio, clients, w = legacy_transport
    info = clients[w["user"]]
    response = info[0].put(f"/api/characters/{w['characters'][0]}", json={"hp_current": 5},
                          headers={"X-CSRF-TOKEN": info[1]["csrf"]})
    assert response.status_code == 409 and response.json["error"]["code"] == "AUTHORITY_EPOCH_MISMATCH"
    assert "authorized scope projection" in response.json["refresh"]


def test_equipment_toggle_is_an_engine_checkpoint(legacy_transport):
    app, sio, clients, w = legacy_transport
    with app.app_context():
        item_id = db.session.scalar(select(Equipment.id).where(Equipment.character_id == w["characters"][0]))
    info = clients[w["user"]]
    response = info[0].put(f"/api/characters/{w['characters'][0]}/equipment/{item_id}",
                           json={"is_equipped": False}, headers=headers(info, context(w)))
    assert response.status_code == 200, response.json
    assert response.json["receipt"]["checkpointId"]
    with app.app_context():
        assert db.session.get(Equipment, item_id).is_equipped is True


def test_legacy_socket_hp_uses_durable_receipt_and_requires_csrf(legacy_transport):
    app, sio, clients, w = legacy_transport
    info = clients[w["user"]]
    client = sio.test_client(app, flask_test_client=info[0])
    assert client.is_connected()
    with app.app_context():
        token = db.session.get(TokenState, w["tokens"][0])
        payload = {"campaign_id": w["campaign"], "session_id": token.game_session_id, "token_id": token.id,
                   "patch": {"hp_current": 4}, "ce": context(w)}
    try:
        denied = client.emit("token:update", payload, callback=True)
        assert denied["error"]["code"] == "OPERATION_FORBIDDEN"
        payload["ce"]["csrf"] = info[1]["csrf"]
        result = client.emit("token:update", payload, callback=True)
        assert result["status"] == "committed", result
        assert client.emit("token:update", payload, callback=True) == result
        assert app.extensions["ce_legacy"].read(w["user"], "vtt.token", w["tokens"][1])["hp_current"] == 4
        assert not any(event["name"] == "token:updated" for event in client.get_received())
    finally:
        client.disconnect()


def test_open_legacy_scope_uses_workspace_identity_and_cannot_mark_fixture(migration_engine):
    w = world(migration_engine, fixture=False, count=1)
    g = w["gateway"]
    with Session(migration_engine) as session, session.begin():
        workspace = ContentStore(session).workspace_for(1, now=g.store.now(session))
    wire = {"contractVersion": "1.1.3", "commandId": new_id("cmd"), "idempotencyKey": new_id("key"),
            "workspaceId": workspace.id, "authorityEpoch": 1, "operation": "OpenLegacyCampaignScope",
            "payload": {"legacyCampaignId": w["campaign"]}}
    result = g.submit(1, canonical_bytes(wire))
    assert result["scopeId"] == w["scope"]
    assert g.submit(1, canonical_bytes({**wire, "commandId": new_id("cmd")})) == result
    from vtt.creation_engine.errors import ContractViolation
    with pytest.raises(ContractViolation):
        g.submit(w["user"], canonical_bytes(wire))
    with pytest.raises(ContractViolation):
        g.submit(1, canonical_bytes({**wire, "payload": {**wire["payload"], "fixture": True}}))
    # A workspace key is independent of the new runtime scope's key namespace.
    assert command(w, "MapLegacyCharacter", {"source": {"sourceType": "vtt.character", "sourceId": w["characters"][0]},
        "migrationVersion": 1}, idempotencyKey=wire["idempotencyKey"])["status"] == "committed"


def test_combat_hp_requires_resource_grant_then_uses_the_same_ledger(legacy_transport):
    from dataclasses import replace
    from vtt.models.combat_encounter import CombatEncounter
    from vtt.creation_engine.policy import Grant
    app, sio, clients, w = legacy_transport
    g = w["gateway"]
    with app.app_context():
        token = db.session.get(TokenState, w["tokens"][0])
        session_id = token.game_session_id
        encounter = CombatEncounter(campaign_id=w["campaign"], game_session_id=session_id,
                                    session_state_id=token.session_state_id, started_by=1, status="active")
        db.session.add(encounter); db.session.commit()
    path = f"/api/campaigns/{w['campaign']}/sessions/{session_id}/combat/hp-adjust"
    body = {"base_version": 1, "target_token_id": w["tokens"][0], "delta": -2, "reason": "manual damage"}
    denied = clients[1][0].post(path, json=body, headers=headers(clients[1], context(w)))
    assert denied.status_code == 403
    target = app.extensions["ce_legacy"].representation("vtt.token", w["tokens"][0])["instanceId"]
    with g.store.transaction(w["scope"]) as tx:
        old = g.policy.policies(tx).policies[target]
        changed = replace(old, grants=old.grants + (Grant("controls", principals=(1,)), Grant("adjust", principals=(1,))))
        g.policy.replace(tx, g.kernel, 1, changed, expected_version=tx.scope.policy_version, reason="explicit fixture control")
    response = clients[1][0].post(path, json=body, headers=headers(clients[1], context(w)))
    assert response.status_code == 200, response.json
    assert response.json["token"]["hp_current"] == 6
    assert app.extensions["ce_legacy"].read(w["user"], "vtt.token", w["tokens"][1])["hp_current"] == 6


def test_token_projection_respects_representation_visibility_and_view_as(legacy_transport):
    app, sio, clients, w = legacy_transport
    with app.app_context():
        token = db.session.get(TokenState, w["tokens"][0])
        token.visibility = "dm_only"
        db.session.commit()
    path = f"/api/ce/migration/tokens/{w['tokens'][0]}/projection"
    assert clients[w["user"]][0].get(path).status_code == 404
    assert clients[1][0].get(path).status_code == 200
    view = w["gateway"].enter_view(1, w["scope"], w["user"])
    assert clients[1][0].get(path, headers={"X-CE-View-As": view["viewAsId"]}).status_code == 404


def test_legacy_resource_body_still_requires_strict_json(legacy_transport):
    app, sio, clients, w = legacy_transport
    info = clients[w["user"]]
    response = info[0].put(f"/api/characters/{w['characters'][0]}", data='{"hp_current":1,"hp_current":2}',
                          content_type="application/json", headers=headers(info, context(w)))
    assert response.status_code == 400 and response.json["error"]["code"] == "SCHEMA_INVALID"
