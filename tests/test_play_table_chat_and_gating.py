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
