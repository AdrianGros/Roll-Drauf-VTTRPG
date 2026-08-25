"""Playtable audit 2026-08-25 (docs/PLAYTABLE_AUDIT_2026-08-25.md), rule
§10 (Ticket→Szenario vor Fix): these scenarios reproduce the audit
findings BEFORE the fixes land.

P0 — DM secrets must be filtered server-side: `dm_only` tokens,
foreign `owner_only` tokens and non-player-visible scene layers were
serialized into every player's bootstrap, socket snapshot and room
broadcast; only play-ui.js hid them client-side.

P2 — internal dice rolls vanished on reload: `roll_dice` broadcast but
never persisted, unlike Beyond20 external rolls.
"""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db, socketio
from vtt.models import (
    Campaign,
    CampaignMap,
    CampaignMember,
    ChatMessage,
    GameSession,
    Role,
    SceneLayer,
    SceneStack,
    TokenState,
    User,
)
from vtt.play.service import ensure_session_state


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name):
    campaign = Campaign(
        name=name,
        description="campaign for secret-filtering tests",
        owner_id=owner_user.id,
        status="active",
        max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=owner_user.id,
            campaign_role="DM",
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=owner_user.id,
        )
    )
    db.session.commit()
    return campaign


def _add_member(campaign, user, campaign_role="Player"):
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=user.id,
            campaign_role=campaign_role,
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=campaign.owner_id,
        )
    )
    db.session.commit()


def _add_map_and_session(campaign, creator_user):
    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name="Secrets Map",
        width=20,
        height=20,
        created_by=creator_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Secrets Session",
        status="in_progress",
    )
    db.session.add(session)
    db.session.commit()
    return campaign_map, session


def _add_token(state, campaign, session, campaign_map, name, visibility,
               owner_user_id=None):
    token = TokenState(
        session_state_id=state.id,
        campaign_id=campaign.id,
        game_session_id=session.id,
        map_id=campaign_map.id,
        owner_user_id=owner_user_id,
        name=name,
        token_type="npc",
        x=1,
        y=1,
        visibility=visibility,
    )
    db.session.add(token)
    db.session.commit()
    return token


def _arrange_secrets(dm_user, player_user):
    """Campaign with one hidden layer and the four token visibility cases."""
    campaign = _create_campaign(dm_user, "Secrets Campaign")
    _add_member(campaign, player_user)
    campaign_map, session = _add_map_and_session(campaign, dm_user)
    state = ensure_session_state(campaign, session)

    secret_map = CampaignMap(campaign_id=campaign.id, name="DM-Notizen",
                             width=10, height=10, created_by=dm_user.id)
    db.session.add(secret_map)
    stack = SceneStack(campaign_id=campaign.id, game_session_id=session.id,
                       created_by=dm_user.id)
    db.session.add(stack)
    db.session.flush()
    visible_layer = SceneLayer(scene_stack_id=stack.id,
                               campaign_map_id=campaign_map.id,
                               label="Sichtbar", order_index=0,
                               is_player_visible=True)
    hidden_layer = SceneLayer(scene_stack_id=stack.id,
                              campaign_map_id=secret_map.id,
                              label="DM-Notizkarte", order_index=1,
                              is_player_visible=False)
    db.session.add_all([visible_layer, hidden_layer])
    db.session.commit()

    tokens = {
        "public": _add_token(state, campaign, session, campaign_map,
                             "Wirt", "public"),
        "dm_only": _add_token(state, campaign, session, campaign_map,
                              "Versteckter Drache", "dm_only"),
        "own": _add_token(state, campaign, session, campaign_map,
                          "Eigener Marker", "owner_only",
                          owner_user_id=player_user.id),
        "foreign": _add_token(state, campaign, session, campaign_map,
                              "Fremder Marker", "owner_only",
                              owner_user_id=dm_user.id),
    }
    return campaign, session, state, tokens, visible_layer, hidden_layer


@pytest.fixture
def app():
    # Socket-handler module globals (presence, room tracking) survive app
    # instances; without clearing them, a test whose socket never
    # disconnected leaks its roster into the next test's identical room ids.
    from vtt import socket_handlers as socket_handler_state
    socket_handler_state._room_presence.clear()
    socket_handler_state._connected_rooms.clear()

    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def dm_user(app):
    user = User(username="secrets_dm", email="secrets_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="secrets_player", email="secrets_player@test.com",
                role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "secrets_dm")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "secrets_player")
    return client


def _token_names(payload):
    return {token["name"] for token in payload["tokens"]}


def _layer_labels(scene_stack_payload):
    return {layer["label"] for layer in scene_stack_payload["layers"]}


class TestSecretFilteringRest:
    def test_player_bootstrap_hides_dm_secrets(self, app, dm_user, player_user,
                                               player_client):
        campaign, session, *_ = _arrange_secrets(dm_user, player_user)
        response = player_client.get(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        payload = response.get_json()
        assert _token_names(payload["state_payload"]) == {"Wirt", "Eigener Marker"}
        assert _layer_labels(payload["scene_stack"]) == {"Sichtbar"}

    def test_dm_bootstrap_keeps_everything(self, app, dm_user, player_user,
                                           dm_client):
        campaign, session, *_ = _arrange_secrets(dm_user, player_user)
        response = dm_client.get(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        payload = response.get_json()
        assert _token_names(payload["state_payload"]) == {
            "Wirt", "Versteckter Drache", "Eigener Marker", "Fremder Marker"}
        assert _layer_labels(payload["scene_stack"]) == {"Sichtbar", "DM-Notizkarte"}


class TestSecretFilteringSocket:
    def _join(self, app, flask_client, campaign, session):
        socket = socketio.test_client(app, flask_test_client=flask_client)
        assert socket.is_connected()
        socket.emit("session:join",
                    {"campaign_id": campaign.id, "session_id": session.id})
        return socket

    def _snapshot(self, events):
        return next(event["args"][0] for event in events
                    if event["name"] == "state:snapshot")

    def test_join_snapshot_filters_by_role(self, app, dm_user, player_user,
                                           dm_client, player_client):
        campaign, session, *_ = _arrange_secrets(dm_user, player_user)
        player_socket = self._join(app, player_client, campaign, session)
        snapshot = self._snapshot(player_socket.get_received())
        assert {t["name"] for t in snapshot["tokens"]} == {"Wirt", "Eigener Marker"}

        dm_socket = self._join(app, dm_client, campaign, session)
        snapshot = self._snapshot(dm_socket.get_received())
        assert {t["name"] for t in snapshot["tokens"]} == {
            "Wirt", "Versteckter Drache", "Eigener Marker", "Fremder Marker"}
        player_socket.disconnect()
        dm_socket.disconnect()

    def test_dm_only_token_events_are_scoped_and_translated(
            self, app, dm_user, player_user, dm_client, player_client):
        campaign, session, *_ = _arrange_secrets(dm_user, player_user)
        dm_socket = self._join(app, dm_client, campaign, session)
        player_socket = self._join(app, player_client, campaign, session)
        dm_socket.get_received()
        player_socket.get_received()

        # 1. Hidden creation: DM sees token:created, player must not.
        dm_socket.emit("token:create", {
            "campaign_id": campaign.id, "session_id": session.id,
            "client_event_id": "secret-create-1",
            "token": {"name": "Hinterhalt-Ork", "x": 5, "y": 5,
                      "token_type": "npc", "visibility": "dm_only"},
        })
        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        created = next(e for e in dm_events if e["name"] == "token:created")
        token_id = created["args"][0]["token"]["id"]
        base_version = created["args"][0]["token"]["version"]
        assert not any(e["name"].startswith("token:") for e in player_events)

        # 2. Reveal (dm_only -> public): the player learns about it as a
        # token:created, never having seen the token before.
        dm_socket.emit("token:update", {
            "campaign_id": campaign.id, "session_id": session.id,
            "token_id": token_id, "base_version": base_version,
            "client_event_id": "secret-reveal-1",
            "patch": {"visibility": "public"},
        })
        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(e["name"] == "token:updated" for e in dm_events)
        reveal = next(e for e in player_events if e["name"] == "token:created")
        assert reveal["args"][0]["token"]["name"] == "Hinterhalt-Ork"
        base_version = reveal["args"][0]["token"]["version"]

        # 3. Hide again (public -> dm_only): the player sees a deletion.
        dm_socket.emit("token:update", {
            "campaign_id": campaign.id, "session_id": session.id,
            "token_id": token_id, "base_version": base_version,
            "client_event_id": "secret-hide-1",
            "patch": {"visibility": "dm_only"},
        })
        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(e["name"] == "token:updated" for e in dm_events)
        hidden = next(e for e in player_events if e["name"] == "token:deleted")
        assert hidden["args"][0]["token_id"] == token_id
        assert not any(e["name"] == "token:updated" for e in player_events)

        dm_socket.disconnect()
        player_socket.disconnect()


class TestCombatSecretFiltering:
    """Playtable-Vordermann 2026-08-25: wiring the combat backend to the
    table must not reopen the P0 leak — combat payloads carry full token
    serializations, so state/event participants need the same role filter
    as snapshots (hidden participants also vanish from initiative_order,
    and active_token_id of a hidden actor is masked for players)."""

    def _start_combat(self, dm_client, campaign, session, state):
        state.active_map_id = state.active_map_id or GameSession.query.get(
            session.id).map_id
        db.session.commit()
        response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/combat/start",
            json={"mode": "auto"})
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    def test_combat_state_hides_dm_secrets_from_player(
            self, app, dm_user, player_user, dm_client, player_client):
        campaign, session, state, tokens, *_ = _arrange_secrets(
            dm_user, player_user)
        started = self._start_combat(dm_client, campaign, session, state)
        assert {t["name"] for t in started["participants"]} >= {
            "Versteckter Drache"}

        response = player_client.get(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/combat/state")
        assert response.status_code == 200
        payload = response.get_json()
        names = {t["name"] for t in payload["participants"]}
        assert names == {"Wirt", "Eigener Marker"}
        hidden_ids = {tokens["dm_only"].id, tokens["foreign"].id}
        assert not hidden_ids & set(payload["encounter"]["initiative_order"])

        dm_response = dm_client.get(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/combat/state")
        assert {t["name"] for t in dm_response.get_json()["participants"]} == {
            "Wirt", "Versteckter Drache", "Eigener Marker", "Fremder Marker"}

    def test_combat_events_are_role_scoped(
            self, app, dm_user, player_user, dm_client, player_client):
        campaign, session, state, tokens, *_ = _arrange_secrets(
            dm_user, player_user)
        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        for sock in (dm_socket, player_socket):
            assert sock.is_connected()
            sock.emit("session:join",
                      {"campaign_id": campaign.id, "session_id": session.id})
            sock.get_received()

        self._start_combat(dm_client, campaign, session, state)
        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        dm_started = next(e for e in dm_events if e["name"] == "combat:started")
        # The client drops repeated event_seq values as stale, so the FIRST
        # received variant wins — the server therefore emits the personal
        # owner variant before the public players-room variant.
        player_started = next(
            e for e in player_events if e["name"] == "combat:started")
        assert {t["name"] for t in dm_started["args"][0]["participants"]} == {
            "Wirt", "Versteckter Drache", "Eigener Marker", "Fremder Marker"}
        assert {t["name"] for t in player_started["args"][0]["participants"]} == {
            "Wirt", "Eigener Marker"}
        assert dm_started["args"][0]["event_seq"] == \
            player_started["args"][0]["event_seq"]
        dm_socket.disconnect()
        player_socket.disconnect()


class TestPresence:
    """Playtable-Vordermann 2026-08-25 (P2): nobody at the table could see
    who else is connected — join/leave now broadcast a roster."""

    def test_join_and_leave_update_roster(self, app, dm_user, player_user,
                                          dm_client, player_client):
        campaign, session, *_ = _arrange_secrets(dm_user, player_user)
        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        assert dm_socket.is_connected()
        dm_socket.emit("session:join",
                       {"campaign_id": campaign.id, "session_id": session.id})
        events = dm_socket.get_received()
        roster = [e for e in events if e["name"] == "presence:update"]
        assert roster, "join must broadcast a presence roster"
        assert {u["username"] for u in roster[-1]["args"][0]["users"]} == {
            "secrets_dm"}

        player_socket = socketio.test_client(app, flask_test_client=player_client)
        assert player_socket.is_connected()
        player_socket.emit("session:join",
                           {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.get_received()
        dm_events = dm_socket.get_received()
        roster = [e for e in dm_events if e["name"] == "presence:update"]
        assert {u["username"] for u in roster[-1]["args"][0]["users"]} == {
            "secrets_dm", "secrets_player"}

        player_socket.emit("session:leave",
                           {"campaign_id": campaign.id, "session_id": session.id})
        dm_events = dm_socket.get_received()
        roster = [e for e in dm_events if e["name"] == "presence:update"]
        assert {u["username"] for u in roster[-1]["args"][0]["users"]} == {
            "secrets_dm"}
        dm_socket.disconnect()
        player_socket.disconnect()


class TestDicePersistence:
    def test_internal_rolls_persist_to_chat(self, app, dm_user, player_user,
                                            dm_client):
        campaign, session, *_ = _arrange_secrets(dm_user, player_user)
        socket = socketio.test_client(app, flask_test_client=dm_client)
        assert socket.is_connected()
        socket.emit("session:join",
                    {"campaign_id": campaign.id, "session_id": session.id})
        socket.get_received()

        socket.emit("roll_dice", {
            "campaign_id": campaign.id, "session_id": session.id,
            "dice": "2d6+1", "player": "secrets_dm",
        })
        events = socket.get_received()
        assert any(e["name"] == "dice_rolled" for e in events)

        message = ChatMessage.query.filter_by(
            game_session_id=session.id, content_type="dice_roll").first()
        assert message is not None, "internal rolls must persist like Beyond20 rolls"
        assert message.author_user_id == dm_user.id
        assert "2d6+1" in message.content
        socket.disconnect()
