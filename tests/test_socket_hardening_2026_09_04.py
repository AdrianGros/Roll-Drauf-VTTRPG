"""Adversarial audit fixes (2026-09-04), all in vtt/socket_handlers.py:

1. Kicking/banning a member never force-disconnected their live socket --
   they kept silently receiving broadcasts after the DB said they no
   longer belonged.
2. _room_name has no delimiter after the trailing session id, so a plain
   str.startswith() prefix match on room names (session 2 vs 22/234...)
   could leave/rejoin the wrong rooms.
3. No throttle existed on any Socket.IO event -- a flood vector.
4. `data or {}` only substitutes {} for FALSY data; a truthy non-dict
   payload (a list, a bare string) crashed the first .get() call
   uncaught.
"""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, User
from vtt.socket_handlers import _RATE_LIMITS, _room_matches_base


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name):
    campaign = Campaign(
        name=name, description="socket hardening test campaign",
        owner_id=owner_user.id, status="active", max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()
    db.session.add(CampaignMember(
        campaign_id=campaign.id, user_id=owner_user.id, campaign_role="DM",
        status="active", joined_at=datetime.utcnow(), invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(), invited_by=owner_user.id,
    ))
    db.session.commit()
    return campaign


def _add_member(campaign, user, campaign_role="Player"):
    db.session.add(CampaignMember(
        campaign_id=campaign.id, user_id=user.id, campaign_role=campaign_role,
        status="active", joined_at=datetime.utcnow(), invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(), invited_by=campaign.owner_id,
    ))
    db.session.commit()


def _add_map_and_session(campaign, creator_user):
    campaign_map = CampaignMap(
        campaign_id=campaign.id, name="Hardening Map", width=20, height=20,
        created_by=creator_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()
    session = GameSession(
        campaign_id=campaign.id, map_id=campaign_map.id, name="Hardening Session",
        status="in_progress",
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
    user = User(username="sh_dm", email="sh_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="sh_player", email="sh_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "sh_dm")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "sh_player")
    return client


class TestRoomNameCollision:
    """Direct function-level test -- deterministic and doesn't depend on
    the DB happening to assign colliding auto-increment session ids."""

    def test_exact_base_room_matches(self):
        assert _room_matches_base("campaign:1:session:2", "campaign:1:session:2") is True

    def test_a_real_subroom_matches(self):
        assert _room_matches_base("campaign:1:session:2:dm", "campaign:1:session:2") is True
        assert _room_matches_base("campaign:1:session:2:players", "campaign:1:session:2") is True
        assert _room_matches_base("campaign:1:session:2:user:9", "campaign:1:session:2") is True

    def test_a_different_session_that_shares_a_numeric_prefix_does_not_match(self):
        """The actual bug: session 22's own base room used to look like
        it "started with" session 2's base room under plain startswith."""
        assert _room_matches_base("campaign:1:session:22", "campaign:1:session:2") is False
        assert _room_matches_base("campaign:1:session:234:dm", "campaign:1:session:2") is False

    def test_a_different_campaign_does_not_match(self):
        assert _room_matches_base("campaign:12:session:2", "campaign:1:session:2") is False


class TestSocketRateLimiting:
    def test_flooding_token_update_gets_rate_limited(self, app, dm_client, dm_user):
        campaign = _create_campaign(dm_user, "Rate Limit Campaign")
        _, session = _add_map_and_session(campaign, dm_user)

        socket = socketio.test_client(app, flask_test_client=dm_client)
        assert socket.is_connected()
        socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        socket.get_received()

        limit = _RATE_LIMITS["token:update"]
        payload = {
            "campaign_id": campaign.id, "session_id": session.id, "token_id": 999999,
            "patch": {"x": 1, "y": 1},
        }
        rate_limited_seen = False
        for _ in range(limit + 5):
            socket.emit("token:update", payload)
            events = socket.get_received()
            if any(
                event["name"] == "state:error" and event["args"][0].get("code") == "rate_limited"
                for event in events
            ):
                rate_limited_seen = True
                break
        assert rate_limited_seen, "flooding past the limit must eventually trigger rate_limited"
        socket.disconnect()

    def test_a_normal_session_stays_well_under_the_limit(self, app, dm_client, dm_user):
        """A sanity check on the limit's own generosity, not just the
        mechanism: a handful of real updates must never trip it."""
        campaign = _create_campaign(dm_user, "Normal Use Campaign")
        _, session = _add_map_and_session(campaign, dm_user)

        socket = socketio.test_client(app, flask_test_client=dm_client)
        socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        socket.get_received()

        for _ in range(5):
            socket.emit("token:update", {
                "campaign_id": campaign.id, "session_id": session.id, "token_id": 999999,
                "patch": {"x": 1, "y": 1},
            })
            events = socket.get_received()
            assert not any(
                event["name"] == "state:error" and event["args"][0].get("code") == "rate_limited"
                for event in events
            )
        socket.disconnect()


class TestNonDictPayloadDoesNotCrash:
    def test_a_list_payload_does_not_raise(self, app, dm_client, dm_user):
        campaign = _create_campaign(dm_user, "Malformed Payload Campaign")
        _, session = _add_map_and_session(campaign, dm_user)

        socket = socketio.test_client(app, flask_test_client=dm_client)
        assert socket.is_connected()
        # Before the fix this crashed the handler with an uncaught
        # AttributeError the moment it called .get() on a list.
        socket.emit("session:join", ["not", "a", "dict"])
        assert socket.is_connected(), "a malformed payload must not kill the connection"
        socket.disconnect()

    def test_a_bare_string_payload_does_not_raise(self, app, dm_client, dm_user):
        socket = socketio.test_client(app, flask_test_client=dm_client)
        assert socket.is_connected()
        socket.emit("chat:message_sent", "not a dict either")
        assert socket.is_connected()
        socket.disconnect()


class TestKickForceDisconnects:
    def test_kicked_player_socket_is_disconnected(self, app, dm_client, player_client, dm_user, player_user):
        campaign = _create_campaign(dm_user, "Kick Campaign")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user)

        player_socket = socketio.test_client(app, flask_test_client=player_client)
        assert player_socket.is_connected()
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.get_received()

        response = dm_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions",
            json={"action_type": "kick", "subject_user_id": player_user.id, "reason": "test"},
        )
        assert response.status_code == 201

        assert not player_socket.is_connected(), "a kicked member's live socket must be force-disconnected"

    def test_warn_does_not_disconnect(self, app, dm_client, player_client, dm_user, player_user):
        """Only kick/ban disconnect -- a lesser action like warn must
        not knock a still-legitimate member off the table."""
        campaign = _create_campaign(dm_user, "Warn Campaign")
        _add_member(campaign, player_user)
        _, session = _add_map_and_session(campaign, dm_user)

        player_socket = socketio.test_client(app, flask_test_client=player_client)
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        player_socket.get_received()

        response = dm_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions",
            json={"action_type": "warn", "subject_user_id": player_user.id, "reason": "test"},
        )
        assert response.status_code == 201
        assert player_socket.is_connected()
        player_socket.disconnect()
