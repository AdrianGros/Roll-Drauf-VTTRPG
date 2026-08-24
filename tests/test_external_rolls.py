"""M-Beyond20 tests: the source-agnostic external-roll ingest socket.

The first client adapter is the Beyond20 browser extension (D&D Beyond
rolls), but the server contract under test here is deliberately
system-neutral: one normalized envelope in, sanitized broadcast +
persisted chat-history line out.
"""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, ChatMessage, GameSession, Role, User


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _create_campaign(owner_user, name):
    campaign = Campaign(
        name=name,
        description="external roll test campaign",
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


def _add_session(campaign, creator_user, status="in_progress"):
    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name="Roll Map",
        width=20,
        height=20,
        created_by=creator_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Roll Session",
        status=status,
    )
    db.session.add(session)
    db.session.commit()
    return session


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
    user = User(username="ext_dm", email="ext_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="ext_player", email="ext_player@test.com", role_id=1)
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


BEYOND20_STYLE_ROLL = {
    "source": "beyond20",
    "system": "dnd5e",
    "character": "Rilbo Steinfaust",
    "title": "Langschwert: Angriff",
    "roll_type": "attack",
    "formula": "1d20+7",
    "total": 23,
    "rolls": [{"formula": "1d20+7", "total": 23, "dice": [16]}],
    "advantage": "adv",
}


class TestExternalRollIngest:
    def test_member_roll_is_broadcast_and_persisted(self, app, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user, "Beyond Campaign")
        _add_member(campaign, player_user)
        session = _add_session(campaign, dm_user)

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        for sock in (dm_socket, player_socket):
            sock.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
            sock.get_received()

        player_socket.emit("external:roll", {
            "campaign_id": campaign.id,
            "session_id": session.id,
            "roll": BEYOND20_STYLE_ROLL,
        })

        stored = ChatMessage.query.filter_by(
            game_session_id=session.id, content_type="external_roll").all()
        assert len(stored) == 1
        assert stored[0].author_user_id == player_user.id
        assert "Rilbo Steinfaust" in stored[0].content
        assert "= 23" in stored[0].content
        assert "(adv)" in stored[0].content

        for sock in (dm_socket, player_socket):
            events = [e for e in sock.get_received() if e["name"] == "external:roll"]
            assert len(events) == 1, "external roll must broadcast to every room member"
            body = events[0]["args"][0]
            assert body["roll"]["source"] == "beyond20"
            assert body["roll"]["system"] == "dnd5e"
            assert body["roll"]["total"] == 23
            assert body["roll"]["rolls"][0]["dice"] == [16]
            # Relay identity always comes from the authenticated account.
            assert body["sender_name"] == player_user.username

    def test_envelope_is_sanitized(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "Sanitize Campaign")
        session = _add_session(campaign, dm_user)
        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        dm_socket.emit("external:roll", {
            "campaign_id": campaign.id,
            "session_id": session.id,
            "roll": {
                "source": "x" * 500,
                "character": "y" * 500,
                "title": "Wurf",
                "total": float("inf"),
                "rolls": [{"formula": "z" * 500, "total": "not-a-number",
                           "dice": ["a", 3, 4.5],
                           "label": "L" * 200, "kind": "K" * 200,
                           "surprise": "dropped"}] * 40,
                "info": ["I" * 500] * 20,
                "unexpected_key": {"nested": "junk"},
            },
        })

        events = [e for e in dm_socket.get_received() if e["name"] == "external:roll"]
        assert len(events) == 1
        roll = events[0]["args"][0]["roll"]
        assert len(roll["source"]) == 40
        assert len(roll["character"]) == 120
        assert roll["total"] is None
        assert len(roll["rolls"]) == 20
        assert len(roll["rolls"][0]["formula"]) == 200
        assert roll["rolls"][0]["total"] is None
        assert roll["rolls"][0]["dice"] == [3, 4.5]
        assert len(roll["rolls"][0]["label"]) == 60
        assert len(roll["rolls"][0]["kind"]) == 20
        assert "surprise" not in roll["rolls"][0]
        assert len(roll["info"]) == 6
        assert len(roll["info"][0]) == 120
        assert "unexpected_key" not in roll

    def test_needs_title_or_formula(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "Empty Campaign")
        session = _add_session(campaign, dm_user)
        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        dm_socket.emit("external:roll", {
            "campaign_id": campaign.id,
            "session_id": session.id,
            "roll": {"source": "beyond20", "total": 12},
        })
        errors = [e for e in dm_socket.get_received() if e["name"] == "state:error"]
        assert errors and errors[0]["args"][0]["code"] == "bad_request"
        assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 0

    def test_non_member_rejected(self, app, dm_user, player_user, player_client):
        campaign = _create_campaign(dm_user, "Foreign Campaign")
        session = _add_session(campaign, dm_user)

        outsider_socket = socketio.test_client(app, flask_test_client=player_client)
        outsider_socket.get_received()
        outsider_socket.emit("external:roll", {
            "campaign_id": campaign.id,
            "session_id": session.id,
            "roll": BEYOND20_STYLE_ROLL,
        })
        errors = [e for e in outsider_socket.get_received() if e["name"] == "state:error"]
        assert errors and errors[0]["args"][0]["code"] == "forbidden"
        assert ChatMessage.query.filter_by(game_session_id=session.id).count() == 0

    def test_read_only_player_rejected(self, app, dm_user, player_user, player_client):
        """A player in a scheduled session (waiting mode) is read-only --
        same gate as native dice/token actions."""
        campaign = _create_campaign(dm_user, "Waiting Campaign")
        _add_member(campaign, player_user)
        session = _add_session(campaign, dm_user, status="scheduled")

        player_socket = socketio.test_client(app, flask_test_client=player_client)
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.get_received()
        player_socket.emit("external:roll", {
            "campaign_id": campaign.id,
            "session_id": session.id,
            "roll": BEYOND20_STYLE_ROLL,
        })
        errors = [e for e in player_socket.get_received() if e["name"] == "state:error"]
        assert errors and errors[0]["args"][0]["code"] == "forbidden"

    def test_roll_lands_in_bootstrap_chat_history(self, app, dm_user, dm_client):
        campaign = _create_campaign(dm_user, "History Campaign")
        session = _add_session(campaign, dm_user)
        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()
        dm_socket.emit("external:roll", {
            "campaign_id": campaign.id,
            "session_id": session.id,
            "roll": BEYOND20_STYLE_ROLL,
        })

        response = dm_client.get(
            f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
        assert response.status_code == 200
        history = response.get_json()["chat_history"]
        assert any("Rilbo Steinfaust" in (entry.get("message") or "") for entry in history)
