"""Tischplatz: a DM or CO-DM sits at one session's table as a player.

Owner decision 2026-11-01 (docs/decisions/PLAYTABLE_ROLE_SEPARATION_2026-11-01.md):
a DM who enters as a player gets exactly a player's rights and data at that
table, over HTTP, sockets and sheet rolls, until they explicitly take the DM
seat again. Nobody else can create a DM seat.
"""

pytest_plugins = ["tests.play_shared"]

import pytest

from vtt.extensions import db, socketio
from vtt.models import CampaignMap, Character, ChatMessage, SceneLayer, SceneStack, TableSeat, TokenState
from vtt.play.service import ensure_session_state, get_table_role
from tests.play_shared import add_map, add_member, create_campaign, create_session


@pytest.fixture(autouse=True)
def _fresh_socket_state():
    # Socket bookkeeping is module-global; earlier tests leave their sids behind.
    from vtt import socket_handlers

    socket_handlers._room_presence.clear()
    socket_handlers._connected_rooms.clear()
    socket_handlers._connected_users.clear()


def _url(campaign, session, suffix):
    return f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/{suffix}"


def _token(state, campaign, session, name, visibility, owner_user_id=None, token_type="npc"):
    token = TokenState(
        session_state_id=state.id, campaign_id=campaign.id, game_session_id=session.id,
        map_id=state.active_map_id, owner_user_id=owner_user_id, name=name, token_type=token_type,
        x=1, y=1, size=1, rotation=0, visibility=visibility, metadata_json={}, version=1,
    )
    db.session.add(token)
    db.session.commit()
    return token


def _live_table(dm_user, player_user, name="Tischplatz"):
    """Live session with a hidden layer, a dm_only token, the player's token and a gm_only chat row."""
    campaign = create_campaign(dm_user, name)
    add_member(campaign, player_user, "Player")
    campaign_map = add_map(campaign, dm_user, f"{name} Karte")
    session = create_session(campaign, f"{name} Sitzung", status="in_progress", map_id=campaign_map.id)
    state = ensure_session_state(campaign, session)
    state.active_map_id = campaign_map.id
    secret_map = CampaignMap(campaign_id=campaign.id, name="Geheime Karte", width=10, height=10,
                             created_by=dm_user.id)
    db.session.add(secret_map)
    stack = SceneStack(campaign_id=campaign.id, game_session_id=session.id, created_by=dm_user.id)
    db.session.add(stack)
    db.session.flush()
    db.session.add_all([
        SceneLayer(scene_stack_id=stack.id, campaign_map_id=campaign_map.id, label="Sichtbar",
                   order_index=0, is_player_visible=True),
        SceneLayer(scene_stack_id=stack.id, campaign_map_id=secret_map.id, label="DM-Notizkarte",
                   order_index=1, is_player_visible=False),
        ChatMessage(campaign_id=campaign.id, game_session_id=session.id, author_user_id=dm_user.id,
                    content="Nur für die Spielleitung", content_type="dice_roll", visibility="gm_only"),
    ])
    db.session.commit()
    tokens = {
        "dragon": _token(state, campaign, session, "Versteckter Drache", "dm_only"),
        "hero": _token(state, campaign, session, "Heldin", "public", owner_user_id=player_user.id,
                       token_type="player"),
    }
    return campaign, session, state, tokens


def _take_seat(client, campaign, session, seat):
    return client.put(_url(campaign, session, "seat"), json={"seat": seat})


def _bootstrap(client, campaign, session):
    response = client.get(_url(campaign, session, "bootstrap"))
    assert response.status_code == 200, response.get_json()
    return response.get_json()


class TestSeatChoice:
    def test_owner_starts_in_the_dm_seat_and_may_switch(self, play_app, play_dm_user, play_player_user,
                                                        play_dm_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)

        payload = _bootstrap(play_dm_client, campaign, session)

        assert payload["session_role"] == "DM"
        assert payload["seat"] == "dm"
        assert payload["can_switch_seat"] is True

    def test_player_seat_gives_the_owner_the_player_projection(self, play_app, play_dm_user, play_player_user,
                                                               play_dm_client):
        campaign, session, _, tokens = _live_table(play_dm_user, play_player_user)

        response = _take_seat(play_dm_client, campaign, session, "player")
        assert response.status_code == 200
        assert response.get_json() == {"session_role": "PLAYER", "seat": "player", "can_switch_seat": True}

        payload = _bootstrap(play_dm_client, campaign, session)
        token_ids = {token["id"] for token in payload["state_payload"]["tokens"]}
        layer_labels = {layer["label"] for layer in payload["scene_stack"]["layers"]}
        assert payload["session_role"] == "PLAYER"
        assert payload["seat"] == "player"
        assert tokens["dragon"].id not in token_ids
        assert tokens["hero"].id in token_ids
        assert "DM-Notizkarte" not in layer_labels
        assert all(row.get("message") != "Nur für die Spielleitung" for row in payload["chat_history"])

    def test_seat_survives_reload_and_only_an_explicit_switch_restores_dm(self, play_app, play_dm_user,
                                                                         play_player_user, play_dm_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)
        _take_seat(play_dm_client, campaign, session, "player")

        assert _bootstrap(play_dm_client, campaign, session)["session_role"] == "PLAYER"
        assert _bootstrap(play_dm_client, campaign, session)["session_role"] == "PLAYER"

        response = _take_seat(play_dm_client, campaign, session, "dm")
        assert response.get_json()["session_role"] == "DM"
        assert TableSeat.query.count() == 0
        assert _bootstrap(play_dm_client, campaign, session)["session_role"] == "DM"

    def test_seat_is_per_session(self, play_app, play_dm_user, play_player_user, play_dm_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)
        other = create_session(campaign, "Andere Sitzung", status="in_progress")
        _take_seat(play_dm_client, campaign, session, "player")

        assert get_table_role(campaign, play_dm_user.id, session.id) == "PLAYER"
        assert get_table_role(campaign, play_dm_user.id, other.id) == "DM"

    def test_a_player_cannot_take_the_dm_seat(self, play_app, play_dm_user, play_player_user, play_player_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)

        assert _take_seat(play_player_client, campaign, session, "dm").status_code == 403
        response = _take_seat(play_player_client, campaign, session, "player")
        assert response.status_code == 200
        assert response.get_json() == {"session_role": "PLAYER", "seat": "player", "can_switch_seat": False}
        assert TableSeat.query.count() == 0

    def test_an_observer_stays_an_observer(self, play_app, play_dm_user, play_player_user, play_observer_user,
                                           play_observer_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)
        add_member(campaign, play_observer_user, "Observer")

        assert _take_seat(play_observer_client, campaign, session, "dm").status_code == 403
        response = _take_seat(play_observer_client, campaign, session, "player")
        assert response.get_json()["session_role"] == "OBSERVER"
        assert _bootstrap(play_observer_client, campaign, session)["read_only"] is True

    def test_unknown_seat_and_outsiders_are_refused(self, play_app, play_dm_user, play_player_user,
                                                    play_dm_client, play_outsider_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)

        assert _take_seat(play_dm_client, campaign, session, "god").status_code == 400
        assert _take_seat(play_outsider_client, campaign, session, "player").status_code == 403

    def test_a_revoked_co_dm_keeps_no_rights_through_a_seat(self, play_app, play_dm_user, play_player_user,
                                                            play_codm_user, play_codm_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)
        member = add_member(campaign, play_codm_user, "CO_DM")
        _take_seat(play_codm_client, campaign, session, "player")
        member.status = "kicked"
        db.session.commit()

        assert play_codm_client.get(_url(campaign, session, "bootstrap")).status_code == 403
        assert _take_seat(play_codm_client, campaign, session, "dm").status_code == 403


class TestPlayerSeatHasNoDmRights:
    def test_dm_only_play_routes_are_refused(self, play_app, play_dm_user, play_player_user, play_dm_client):
        campaign, session, _, tokens = _live_table(play_dm_user, play_player_user)
        _take_seat(play_dm_client, campaign, session, "player")

        assert play_dm_client.post(_url(campaign, session, "vision/walls"),
                                   json={"x0": 0, "y0": 0, "x1": 100, "y1": 0}).status_code == 403
        assert play_dm_client.get(_url(campaign, session, "vision/walls")).status_code == 403
        assert play_dm_client.post(_url(campaign, session, "scene-stack/init"), json={}).status_code == 403
        assert play_dm_client.post(_url(campaign, session, "transition"),
                                   json={"target_state": "ended"}).status_code == 403
        assert play_dm_client.get(
            _url(campaign, session, f"vision/tokens/{tokens['hero'].id}/visible")).status_code == 403

    def test_legacy_table_routes_are_refused(self, play_app, play_dm_user, play_player_user, play_dm_client):
        campaign, session, _, tokens = _live_table(play_dm_user, play_player_user)
        _take_seat(play_dm_client, campaign, session, "player")
        base = f"/api/campaigns/{campaign.id}/sessions/{session.id}"

        assert play_dm_client.post(f"{base}/combat/start", json={}).status_code == 403
        assert play_dm_client.post(f"{base}/maps/activate", json={"map_id": 1}).status_code == 403
        moved = play_dm_client.put(f"{base}/tokens/{tokens['hero'].id}",
                                   json={"base_version": 1, "patch": {"x": 3}})
        assert moved.status_code == 403
        state = play_dm_client.get(f"{base}/state")
        assert state.status_code == 200
        assert tokens["dragon"].id not in {token["id"] for token in state.get_json()["tokens"]}

    def test_dm_seat_keeps_its_rights(self, play_app, play_dm_user, play_player_user, play_dm_client):
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)
        _take_seat(play_dm_client, campaign, session, "player")
        _take_seat(play_dm_client, campaign, session, "dm")

        response = play_dm_client.post(_url(campaign, session, "vision/walls"),
                                       json={"x0": 0, "y0": 0, "x1": 100, "y1": 0, "sight": "normal"})
        assert response.status_code == 201, response.get_json()


class TestSocketSeat:
    def _joined(self, play_app, client, campaign, session):
        sock = socketio.test_client(play_app, flask_test_client=client)
        assert sock.is_connected()
        sock.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        events = sock.get_received()
        snapshot = [event for event in events if event["name"] == "state:snapshot"][-1]["args"][0]
        return sock, snapshot

    def test_join_in_the_player_seat_gets_the_player_snapshot_and_room(self, play_app, play_dm_user,
                                                                       play_player_user, play_dm_client):
        from vtt.socket_handlers import _connected_rooms, _room_presence
        from vtt.utils.realtime import dm_room, players_room

        _connected_rooms.clear()
        _room_presence.clear()
        campaign, session, _, tokens = _live_table(play_dm_user, play_player_user)
        _take_seat(play_dm_client, campaign, session, "player")

        sock, snapshot = self._joined(play_app, play_dm_client, campaign, session)
        rooms = set().union(*_connected_rooms.values())

        assert tokens["dragon"].id not in {token["id"] for token in snapshot["tokens"]}
        assert players_room(campaign.id, session.id) in rooms
        assert dm_room(campaign.id, session.id) not in rooms
        sock.disconnect()

    def test_taking_the_player_seat_leaves_the_dm_room_at_once(self, play_app, play_dm_user, play_player_user,
                                                                play_dm_client):
        from vtt.socket_handlers import _connected_rooms, _room_presence
        from vtt.utils.realtime import dm_room, players_room

        _connected_rooms.clear()
        _room_presence.clear()
        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)
        sock, _ = self._joined(play_app, play_dm_client, campaign, session)
        assert dm_room(campaign.id, session.id) in set().union(*_connected_rooms.values())

        _take_seat(play_dm_client, campaign, session, "player")
        events = sock.get_received()
        rooms = set().union(*_connected_rooms.values())

        assert dm_room(campaign.id, session.id) not in rooms
        assert players_room(campaign.id, session.id) in rooms
        changed = [event for event in events if event["name"] == "table:seat_changed"]
        assert changed and changed[-1]["args"][0]["session_role"] == "PLAYER"
        presence = [event for event in events if event["name"] == "presence:update"][-1]["args"][0]
        assert presence["users"][0]["role"] == "PLAYER"

        # A DM-room broadcast no longer reaches the downgraded tab.
        socketio.emit("token:created", {"secret": True}, room=dm_room(campaign.id, session.id))
        assert not [event for event in sock.get_received() if event["name"] == "token:created"]
        sock.disconnect()

    def test_player_seat_cannot_move_a_foreign_token_or_roll_blind(self, play_app, play_dm_user, play_player_user,
                                                                   play_dm_client):
        from vtt.socket_handlers import _connected_rooms, _room_presence

        _connected_rooms.clear()
        _room_presence.clear()
        campaign, session, _, tokens = _live_table(play_dm_user, play_player_user)
        _take_seat(play_dm_client, campaign, session, "player")
        sock, _ = self._joined(play_app, play_dm_client, campaign, session)

        sock.emit("token:update", {"campaign_id": campaign.id, "session_id": session.id,
                                   "client_event_id": "seat-move-1", "token_id": tokens["hero"].id,
                                   "base_version": 1, "patch": {"x": 4}})
        errors = [event for event in sock.get_received() if event["name"] == "state:error"]
        assert errors
        db.session.expire_all()
        assert db.session.get(TokenState, tokens["hero"].id).x == 1

        sock.emit("roll_dice", {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d20",
                                "player": "DM", "visibility": "blind"})
        row = ChatMessage.query.filter_by(game_session_id=session.id, content_type="dice_roll") \
            .order_by(ChatMessage.id.desc()).first()
        assert row.visibility == "public"
        sock.disconnect()


class TestSheetRollsInThePlayerSeat:
    def _character(self, campaign, owner, name):
        char = Character(user_id=owner.id, campaign_id=campaign.id, name=name, race="Mensch",
                         class_name="Kämpfer", level=1)
        db.session.add(char)
        db.session.commit()
        return char

    def test_player_seat_rolls_only_for_own_characters(self, play_app, play_dm_user, play_player_user,
                                                       play_dm_client):
        from vtt.characters import sheet_link

        campaign, session, _, _ = _live_table(play_dm_user, play_player_user)
        foreign = self._character(campaign, play_player_user, "Heldin")
        own = self._character(campaign, play_dm_user, "Gastheld")

        assert sheet_link.roll_destination(play_dm_user, foreign, session.id)["session"].id == session.id
        _take_seat(play_dm_client, campaign, session, "player")

        try:
            sheet_link.roll_destination(play_dm_user, foreign, session.id)
        except sheet_link.RollTargetError as exc:
            assert exc.code == "session_forbidden"
        else:
            raise AssertionError("a player seat rolled for someone else's character")
        assert sheet_link.roll_destination(play_dm_user, foreign)["session"] is None
        assert sheet_link.roll_destination(play_dm_user, own, session.id)["session"].id == session.id
