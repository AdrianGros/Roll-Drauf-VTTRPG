"""WP6 authenticated REST/Socket.IO conformance on the real PostgreSQL gateway."""

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, decode_token
from flask_socketio import SocketIO

from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.transports import register
from vtt.creation_engine.transports.sockets import NAMESPACE
from vtt.models import CampaignMember
from sqlalchemy import select

from test_ce_content_store import postgres_engine
from test_ce_kernel import kernel_engine
from test_ce_public import public_engine, public_world, pending

pytestmark = pytest.mark.postgres


@pytest.fixture
def transport(public_world):
    world, gateway = public_world
    app = Flask("creation-engine-transport-test")
    app.config.update(TESTING=True, SECRET_KEY="ce-test-secret", JWT_SECRET_KEY="ce-test-jwt-secret-" * 3,
                      JWT_TOKEN_LOCATION=["cookies"], JWT_COOKIE_CSRF_PROTECT=True, CE_RUNTIME=True)
    jwt = JWTManager(app)
    revoked = set()
    @jwt.token_in_blocklist_loader
    def blocklist(header, claims):
        return claims["jti"] in revoked
    socketio = SocketIO(app, async_mode="threading")
    app.extensions["ce_gateway"] = gateway
    register(app, socketio)
    clients = {}
    with app.app_context():
        for user in (1, 2, 3):
            token = create_access_token(identity=str(user))
            claims = decode_token(token)
            client = app.test_client()
            client.set_cookie("access_token_cookie", token)
            clients[user] = (client, claims)
    return app, socketio, clients, world, gateway, revoked


def post(client_info, path, body, **headers):
    client, claims = client_info
    return client.post(path, data=canonical_bytes(body), content_type="application/json",
                       headers={"X-CSRF-TOKEN": claims["csrf"], **headers})


def socket_client(transport, user=2, *, csrf=True):
    app, socketio, clients, *_ = transport
    client, claims = clients[user]
    return socketio.test_client(app, namespace=NAMESPACE, flask_test_client=client,
                                auth={"csrf": claims["csrf"]} if csrf else {})


def test_rest_and_socket_share_command_identity_and_public_receipt(transport):
    app, sio, clients, world, g, _ = transport
    response = post(clients[2], "/api/ce/commands", world["wire"])
    assert response.status_code == 200
    receipt = response.get_json()
    assert "outcomeDigest" not in receipt
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "ETag" not in response.headers
    client = socket_client(transport)
    try:
        wire = {**world["wire"], "commandId": "cmd:socket-retry"}
        socket_receipt = client.emit("ce:command", {"command": canonical_bytes(wire).decode()}, namespace=NAMESPACE, callback=True)
        assert socket_receipt == receipt
    finally:
        client.disconnect(namespace=NAMESPACE)


@pytest.mark.parametrize("operation", ["read", "explain", "export"])
def test_rest_curse_gm_warm_cache_never_changes_player_projection(transport, operation):
    _, _, clients, world, _, _ = transport
    url = f'/api/ce/scopes/{world["scope"]}/objects/sheet:hero?operation={operation}'
    gm = clients[1][0].get(url)
    assert gm.status_code == 200 and "sourceName" in gm.get_json()["fields"]
    player = clients[2][0].get(url)
    assert player.status_code == 200
    assert player.get_json()["fields"]["defense"]["value"]["numerator"] == 12
    for secret in (b"Secret curse", b"effect:secret", b"private.invalid", b"outcomeDigest", b"omitted"):
        assert secret not in player.data


def test_unknown_and_forbidden_objects_have_identical_public_errors(transport):
    _, _, clients, world, _, _ = transport
    prefix = f'/api/ce/scopes/{world["scope"]}/objects/'
    unknown = clients[2][0].get(prefix + "unknown")
    private = clients[2][0].get(prefix + "curse:secret")
    assert unknown.status_code == private.status_code == 404
    assert unknown.get_json() == private.get_json() == {"error": {"code": "NOT_FOUND"}}


def test_http_authentication_csrf_and_flag_gates(transport):
    app, _, clients, world, g, _ = transport
    assert app.test_client().post("/api/ce/commands", json=world["wire"]).status_code == 401
    assert clients[2][0].post("/api/ce/commands", json=world["wire"]).status_code == 401
    app.config["CE_RUNTIME"] = False
    assert post(clients[2], "/api/ce/commands", world["wire"]).status_code == 404
    app.config["CE_RUNTIME"] = True
    del app.extensions["ce_gateway"]
    response = post(clients[2], "/api/ce/commands", world["wire"])
    assert response.status_code == 503 and response.get_json() == {"error": {"code": "ENGINE_UNAVAILABLE"}}


def test_transport_size_and_spoofing_rejected_before_persistence(transport):
    _, _, clients, world, g, _ = transport
    forged = {**world["wire"], "principalId": 1}
    assert post(clients[2], "/api/ce/commands", forged).status_code == 400
    g.kernel.max_request_bytes = 100
    response = post(clients[2], "/api/ce/commands", world["wire"])
    assert response.status_code == 413
    with g.store.transaction(world["scope"]) as tx:
        assert tx.receipt(2, world["wire"]["idempotencyKey"]) is None


def test_rest_view_as_stays_read_only_and_hides_owner_private_fields(transport):
    _, _, clients, world, g, _ = transport
    base = f'/api/ce/scopes/{world["scope"]}'
    response = post(clients[1], base + "/view-as", {"memberId": 2})
    assert response.status_code == 201
    view_id = response.get_json()["viewAsId"]
    viewed = clients[1][0].get(base + "/objects/sheet:hero", headers={"X-CE-View-As": view_id}).get_json()
    assert "privateNote" not in viewed["fields"] and "sourceName" not in viewed["fields"]
    response = post(clients[1], "/api/ce/commands", world["wire"], **{"X-CE-View-As": view_id})
    assert response.status_code == 403
    closed = clients[1][0].delete(base + "/view-as/" + view_id, headers={"X-CSRF-TOKEN": clients[1][1]["csrf"]})
    assert closed.status_code == 200 and closed.get_json() == {"closed": True}


def test_socket_requires_csrf_handshake_and_rechecks_token_revocation(transport):
    *_, revoked = transport
    invalid = socket_client(transport, csrf=False)
    assert not invalid.is_connected(namespace=NAMESPACE)
    client = socket_client(transport)
    try:
        revoked.add(transport[2][2][1]["jti"])
        response = client.emit("ce:subscribe", {"scopeId": transport[3]["scope"],
            "contractVersion": "1.1.3", "authorityEpoch": 1}, namespace=NAMESPACE, callback=True)
        assert response["status"] == 403
    finally:
        client.disconnect(namespace=NAMESPACE)


@pytest.mark.parametrize("body", [None, [], "invalid", {"scopeId": {}}, {"scopeId": {}, "contractVersion": "1.1.3", "authorityEpoch": 1},
                                   {"scopeId": "scope:x", "contractVersion": "1.1.3", "authorityEpoch": True}])
def test_socket_rejects_malformed_subscriptions(transport, body):
    client = socket_client(transport)
    try:
        response = client.emit("ce:subscribe", body, namespace=NAMESPACE, callback=True)
        assert response["status"] == 400
    finally:
        client.disconnect(namespace=NAMESPACE)


def test_socket_private_snapshot_cursor_connection_binding_and_revocation(transport):
    _, _, _, world, g, _ = transport
    client, second = socket_client(transport), socket_client(transport)
    try:
        sub = client.emit("ce:subscribe", {"scopeId": world["scope"], "contractVersion": "1.1.3", "authorityEpoch": 1},
                          namespace=NAMESPACE, callback=True)
        assert len(sub["snapshot"]["objects"]) == 1
        assert b"Secret curse" not in canonical_bytes(sub)
        body = {"scopeId": world["scope"], "subscriptionId": sub["subscriptionId"], "cursor": sub["cursor"]}
        assert second.emit("ce:poll", body, namespace=NAMESPACE, callback=True)["status"] == 404
        page = client.emit("ce:poll", body, namespace=NAMESPACE, callback=True)
        assert page["events"] == []
        emitted = client.get_received(namespace=NAMESPACE)
        assert [e["name"] for e in emitted] == ["ce:events"]
        with g.store.transaction(world["scope"]) as tx:
            member = tx.session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == world["campaign"],
                                                                    CampaignMember.user_id == 2))
            member.status = "kicked"
            g.policy.changed(tx, g.kernel, 1, reason="transport revocation")
        assert client.emit("ce:poll", body, namespace=NAMESPACE, callback=True)["status"] == 404
        assert client.get_received(namespace=NAMESPACE) == []
    finally:
        client.disconnect(namespace=NAMESPACE)
        second.disconnect(namespace=NAMESPACE)


def test_decision_token_and_receipt_cannot_be_read_by_another_member(transport):
    _, _, clients, world, g, _ = transport
    first, d = pending(world, g)
    prefix = f'/api/ce/scopes/{world["scope"]}'
    assert clients[2][0].get(prefix + "/decisions/" + d.id).status_code == 200
    assert clients[3][0].get(prefix + "/decisions/" + d.id).status_code == 403
    assert clients[3][0].get(prefix + "/receipts/" + world["wire"]["idempotencyKey"]).status_code == 404


@pytest.mark.parametrize("payload", ['{"operation":"InvokeActivity","operation":"AdjustResource"}',
                                     '{"value":NaN}', '{"value":1,"value":2}', {}])
def test_socket_preserves_strict_json_validation(transport, payload):
    client = socket_client(transport)
    try:
        response = client.emit("ce:command", {"command": payload}, namespace=NAMESPACE, callback=True)
        assert response == {"error": {"code": "SCHEMA_INVALID"}, "status": 400}
    finally:
        client.disconnect(namespace=NAMESPACE)
