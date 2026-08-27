"""Play-table refactor tests (robot audit 2026-08-23).

Covers the two backend changes shipped with the table refactor:

1. The ``chat:message_sent`` socket handler. The client has emitted this
   event since the chat UI was built, but no server handler existed --
   every table chat message silently vanished. Now it must persist a
   ChatMessage row, broadcast to the session room, and surface in the
   play bootstrap payload as ``chat_history``.

2. Read-only gating on the token socket handlers (audit finding D10):
   membership+ownership alone used to let players mutate tokens over the
   socket in session states where the whole UI and every REST play route
   treated them as read-only (e.g. a scheduled session's waiting mode).
"""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, ChatMessage, GameSession, Role, TokenState, User


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
        description="campaign for play table tests",
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


def _add_map_and_session(campaign, creator_user, session_status="in_progress"):
    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name="Table Map",
        width=20,
        height=20,
        created_by=creator_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Table Session",
        status=session_status,
    )
    db.session.add(session)
    db.session.commit()
    return campaign_map, session


@pytest.fixture
def app():
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
    user = User(username="table_dm", email="table_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="table_player", email="table_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, dm_user.username)
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, player_user.username)
    return client


class TestTableChat:
    def test_chat_message_is_persisted_and_broadcast(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Chat Campaign")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()
        player_socket.get_received()

        player_socket.emit(
            "chat:message_sent",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "message": "Hallo Tisch!",
                # Client-supplied identity must be ignored in favor of the
                # authenticated socket user.
                "sender_id": 99999,
                "sender_name": "spoofed-name",
            },
        )

        stored = ChatMessage.query.filter_by(game_session_id=session.id).all()
        assert len(stored) == 1
        assert stored[0].content == "Hallo Tisch!"
        assert stored[0].author_user_id == player_user.id

        # Both room members (including the sender) receive the broadcast --
        # the sender's own chat log only appends on receipt.
        for socket_client in (dm_socket, player_socket):
            events = [e for e in socket_client.get_received() if e["name"] == "chat:message_sent"]
            assert len(events) == 1, "every room member must receive the chat broadcast"
            payload = events[0]["args"][0]
            assert payload["message"] == "Hallo Tisch!"
            assert payload["sender_id"] == player_user.id
            assert payload["sender_name"] == player_user.username

    def test_chat_rejects_non_member_and_empty_message(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Chat Guard Campaign")
        # player_user is deliberately NOT a member here.
        _, session = _add_map_and_session(campaign, dm_user)

        outsider_socket = socketio.test_client(app, flask_test_client=player_client)
        outsider_socket.get_received()
        outsider_socket.emit(
            "chat:message_sent",
            {"campaign_id": campaign.id, "session_id": session.id, "message": "sollte nicht ankommen"},
        )
        assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 0
        errors = [e for e in outsider_socket.get_received() if e["name"] == "state:error"]
        assert errors, "non-member chat must be rejected with state:error"

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()
        dm_socket.emit(
            "chat:message_sent",
            {"campaign_id": campaign.id, "session_id": session.id, "message": "   "},
        )
        assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 0

    def test_bootstrap_exposes_chat_history(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "History Campaign")
        _, session = _add_map_and_session(campaign, dm_user)
        db.session.add(
            ChatMessage(
                campaign_id=campaign.id,
                game_session_id=session.id,
                author_user_id=dm_user.id,
                content="Alte Nachricht",
            )
        )
        db.session.commit()

        response = dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        history = response.get_json()["chat_history"]
        assert len(history) == 1
        assert history[0]["message"] == "Alte Nachricht"
        assert history[0]["sender_name"] == dm_user.username


class TestSocketReadOnlyGating:
    def test_player_cannot_create_token_in_scheduled_session(self, app, dm_user, player_user, dm_client, player_client):
        """Waiting mode (scheduled session) is read-only for players --
        REST and the UI both enforce that; the socket path must too."""
        campaign = _create_campaign(dm_user, "Gate Campaign")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user, session_status="scheduled")

        player_socket = socketio.test_client(app, flask_test_client=player_client)
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.get_received()

        player_socket.emit(
            "token:create",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "client_event_id": "gate-create-1",
                "token": {"name": "Blocked", "token_type": "player", "x": 0, "y": 0},
            },
        )
        assert TokenState.query.filter_by(game_session_id=session.id).count() == 0
        errors = [e for e in player_socket.get_received() if e["name"] == "state:error"]
        assert errors and errors[0]["args"][0]["code"] == "forbidden"

    def test_dm_can_still_prepare_tokens_in_scheduled_session(self, app, dm_user, dm_client):
        """The gate must NOT break DM prep: operators are never read-only
        outside ended sessions."""
        campaign = _create_campaign(dm_user, "Prep Campaign")
        _, session = _add_map_and_session(campaign, dm_user, session_status="scheduled")

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        dm_socket.emit(
            "token:create",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "client_event_id": "prep-create-1",
                "token": {"name": "Goblin", "token_type": "monster", "x": 70, "y": 140},
            },
        )
        assert TokenState.query.filter_by(game_session_id=session.id).count() == 1

    def test_player_can_move_own_token_in_live_session(self, app, dm_user, player_user, dm_client, player_client):
        """Live mode stays interactive for players on their own tokens."""
        campaign = _create_campaign(dm_user, "Live Campaign")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user, session_status="in_progress")

        player_socket = socketio.test_client(app, flask_test_client=player_client)
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.get_received()

        player_socket.emit(
            "token:create",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "client_event_id": "live-create-1",
                "token": {"name": "Held", "token_type": "player", "x": 0, "y": 0},
            },
        )
        token = TokenState.query.filter_by(game_session_id=session.id).first()
        assert token is not None
        player_socket.get_received()

        player_socket.emit(
            "token:update",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "token_id": token.id,
                "base_version": token.version,
                "client_event_id": "live-move-1",
                "patch": {"x": 140, "y": 210},
            },
        )
        db.session.refresh(token)
        assert (token.x, token.y) == (140, 210)


class TestRollVisibility:
    """S08: roll visibility (public/gm_only/blind/self) is the CRITICAL
    risk the research doc flagged for this slice -- the server must be the
    sole source of truth, never a client-supplied claim. These tests hit
    the real socket handler and real room-scoped broadcast (_emit_scoped_roll),
    not just the persisted row, since the visibility bug that matters most
    is "an unauthorized client received the real event over the socket".
    """

    def test_non_dm_blind_request_is_silently_downgraded_to_public(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Sichtbarkeits-Kampagne")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()
        player_socket.get_received()

        player_socket.emit(
            "roll_dice",
            {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d20",
             "player": "player", "visibility": "blind"},
        )

        stored = ChatMessage.query.filter_by(game_session_id=session.id, content_type="dice_roll").first()
        assert stored is not None
        assert stored.visibility == "public", "a non-DM blind request must be downgraded, not honored"

        events = [e for e in player_socket.get_received() if e["name"] == "dice_rolled"]
        assert len(events) == 1
        assert events[0]["args"][0].get("result", {}).get("total") is not None, \
            "downgraded-to-public roll must reach the player with a real result, not a placeholder"

    def test_dm_blind_roll_reaches_dm_in_full_and_players_only_as_a_placeholder(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Verdeckte Wuerfe")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()
        player_socket.get_received()

        dm_socket.emit(
            "roll_dice",
            {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d20+3",
             "player": dm_user.username, "visibility": "blind"},
        )

        stored = ChatMessage.query.filter_by(game_session_id=session.id, content_type="dice_roll").first()
        assert stored is not None
        assert stored.visibility == "blind"

        dm_events = [e for e in dm_socket.get_received() if e["name"] == "dice_rolled"]
        assert len(dm_events) == 1
        dm_payload = dm_events[0]["args"][0]
        assert dm_payload.get("result", {}).get("total") is not None, "DM must always see the real roll"
        assert dm_payload.get("dice") == "1d20+3"

        player_events = [e for e in player_socket.get_received() if e["name"] == "dice_rolled"]
        assert len(player_events) == 1, "the player must still learn SOMETHING happened (a placeholder), not silence"
        player_payload = player_events[0]["args"][0]
        assert player_payload.get("hidden") is True
        assert player_payload.get("result") is None, "a blind roll must never leak the total to a non-DM client"
        assert player_payload.get("dice") is None, "a blind roll must never leak the formula to a non-DM client"
        assert player_payload.get("player") is None, "a blind roll must never leak who rolled to a non-DM client"

    def test_gm_only_roll_reaches_only_the_dm_room(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        campaign = _create_campaign(dm_user, "Nur-SL Wuerfe")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()
        player_socket.get_received()

        dm_socket.emit(
            "roll_dice",
            {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d20",
             "player": dm_user.username, "visibility": "gm_only"},
        )

        dm_events = [e for e in dm_socket.get_received() if e["name"] == "dice_rolled"]
        assert len(dm_events) == 1

        player_events = [e for e in player_socket.get_received() if e["name"] == "dice_rolled"]
        assert not player_events, "gm_only must not reach players as a dice_rolled event at all, not even a placeholder"

    def test_public_roll_still_reaches_everyone_in_full(
        self, app, dm_user, player_user, dm_client, player_client
    ):
        """Regression check: the new scoped-broadcast path must not have
        narrowed the existing, previously-working public-roll behavior."""
        campaign = _create_campaign(dm_user, "Oeffentliche Wuerfe")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()
        player_socket.get_received()

        player_socket.emit(
            "roll_dice",
            {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d6",
             "player": player_user.username, "visibility": "public"},
        )

        for socket_client in (dm_socket, player_socket):
            events = [e for e in socket_client.get_received() if e["name"] == "dice_rolled"]
            assert len(events) == 1
            assert events[0]["args"][0].get("result", {}).get("total") is not None

    def test_advantage_rolls_a_single_d20_twice_and_keeps_the_higher(
        self, app, dm_user, dm_client
    ):
        campaign = _create_campaign(dm_user, "Vorteil-Kampagne")
        _, session = _add_map_and_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        acks = []
        for _ in range(20):  # enough tries that a coin-flip discard bug would show up
            ack = dm_socket.emit(
                "roll_dice",
                {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d20",
                 "player": dm_user.username, "mode": "advantage"},
                callback=True,
            )
            acks.append(ack)
        dm_socket.get_received()

        assert len(acks) == 20
        for result in acks:
            assert result["mode"] == "advantage"
            assert len(result["rolls"]) == 1
            assert len(result["discarded_rolls"]) == 1
            # the kept roll must never be lower than the discarded one
            assert result["rolls"][0] >= result["discarded_rolls"][0]

    def test_advantage_mode_is_ignored_for_multi_die_formulas(self, app, dm_user, dm_client):
        """ADV/DIS has no well-defined meaning for "advantage on 3d6" --
        must fall back to a normal roll rather than error or silently
        misapply the mechanic."""
        campaign = _create_campaign(dm_user, "Mehrwuerfel-Kampagne")
        _, session = _add_map_and_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        ack = dm_socket.emit(
            "roll_dice",
            {"campaign_id": campaign.id, "session_id": session.id, "dice": "3d6",
             "player": dm_user.username, "mode": "advantage"},
            callback=True,
        )
        dm_socket.get_received()

        assert ack["mode"] == "normal"
        assert len(ack["rolls"]) == 3
        assert "discarded_rolls" not in ack
