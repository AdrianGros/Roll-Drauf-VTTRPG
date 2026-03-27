"""M5 tests: token persistence and realtime room isolation."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db, socketio
from vtt_app.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, User


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
        description="campaign for realtime tests",
        owner_id=owner_user.id,
        status="active",
        max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()

    dm_member = CampaignMember(
        campaign_id=campaign.id,
        user_id=owner_user.id,
        campaign_role="DM",
        status="active",
        joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(),
        invited_by=owner_user.id,
    )
    db.session.add(dm_member)
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


def _add_map_and_session(campaign, creator_user, map_name, session_name):
    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name=map_name,
        width=20,
        height=20,
        created_by=creator_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()

    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name=session_name,
        status="scheduled",
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
    user = User(username="rt_dm", email="rt_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="rt_player", email="rt_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def outsider_user(app):
    user = User(username="rt_out", email="rt_out@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "rt_dm")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "rt_player")
    return client


@pytest.fixture
def outsider_client(app, outsider_user):
    client = app.test_client()
    _login(client, "rt_out")
    return client


class TestTokenRealtime:
    def test_socket_connect_requires_auth(self, app):
        unauth_socket = socketio.test_client(app)
        assert not unauth_socket.is_connected()

    def test_room_isolation_prevents_cross_session_token_events(self, app, dm_client, player_client, dm_user, player_user):
        campaign_one = _create_campaign(dm_user, "Realtime One")
        campaign_two = _create_campaign(dm_user, "Realtime Two")
        _add_member(campaign_one, player_user)
        _add_member(campaign_two, player_user)

        _, session_one = _add_map_and_session(campaign_one, dm_user, "Map One", "Session One")
        _, session_two = _add_map_and_session(campaign_two, dm_user, "Map Two", "Session Two")

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        player_socket = socketio.test_client(app, flask_test_client=player_client)
        assert dm_socket.is_connected()
        assert player_socket.is_connected()

        dm_socket.emit("session:join", {"campaign_id": campaign_one.id, "session_id": session_one.id})
        player_socket.emit("session:join", {"campaign_id": campaign_two.id, "session_id": session_two.id})
        dm_socket.get_received()
        player_socket.get_received()

        dm_socket.emit(
            "token:create",
            {
                "campaign_id": campaign_one.id,
                "session_id": session_one.id,
                "client_event_id": "room-isolation-create-1",
                "token": {"name": "Orc", "x": 2, "y": 3, "token_type": "npc"},
            },
        )

        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(event["name"] == "token:created" for event in dm_events)
        assert not any(event["name"] == "token:created" for event in player_events)

        dm_socket.disconnect()
        player_socket.disconnect()

    def test_non_member_join_gets_forbidden_error(self, app, dm_user, outsider_client):
        campaign = _create_campaign(dm_user, "Protected Realtime")
        _add_map_and_session(campaign, dm_user, "Protected Map", "Protected Session")
        session = GameSession.query.filter_by(campaign_id=campaign.id).first()

        outsider_socket = socketio.test_client(app, flask_test_client=outsider_client)
        assert outsider_socket.is_connected()
        outsider_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        events = outsider_socket.get_received()
        assert any(event["name"] == "state:error" for event in events)
        outsider_socket.disconnect()

    def test_token_update_conflict_emits_state_conflict(self, app, dm_client, dm_user):
        campaign = _create_campaign(dm_user, "Conflict Campaign")
        _, session = _add_map_and_session(campaign, dm_user, "Conflict Map", "Conflict Session")

        create_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens",
            json={"name": "Hero", "x": 1, "y": 1, "token_type": "player"},
        )
        assert create_response.status_code == 201
        token_id = create_response.get_json()["token"]["id"]

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        assert dm_socket.is_connected()
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        dm_socket.emit(
            "token:update",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "token_id": token_id,
                "client_event_id": "conflict-update-1",
                "base_version": 999,
                "patch": {"x": 5},
            },
        )
        events = dm_socket.get_received()
        assert any(event["name"] == "state:conflict" for event in events)
        dm_socket.disconnect()

    def test_token_update_requires_base_version(self, app, dm_client, dm_user):
        campaign = _create_campaign(dm_user, "Base Version Required Campaign")
        _, session = _add_map_and_session(campaign, dm_user, "Base Version Map", "Base Version Session")

        create_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens",
            json={"name": "Mage", "x": 1, "y": 1, "token_type": "player"},
        )
        assert create_response.status_code == 201
        token_id = create_response.get_json()["token"]["id"]

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        assert dm_socket.is_connected()
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        dm_socket.emit(
            "token:update",
            {
                "campaign_id": campaign.id,
                "session_id": session.id,
                "token_id": token_id,
                "client_event_id": "missing-base-version-1",
                "patch": {"x": 7},
            },
        )
        events = dm_socket.get_received()
        errors = [event for event in events if event["name"] == "state:error"]
        assert errors
        assert "base_version required" in errors[-1]["args"][0]["message"]
        dm_socket.disconnect()

    def test_duplicate_client_event_id_is_deduped(self, app, dm_client, dm_user):
        campaign = _create_campaign(dm_user, "Dedup Campaign")
        _, session = _add_map_and_session(campaign, dm_user, "Dedup Map", "Dedup Session")

        create_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens",
            json={"name": "Rogue", "x": 2, "y": 2, "token_type": "player"},
        )
        assert create_response.status_code == 201
        token_payload = create_response.get_json()["token"]
        token_id = token_payload["id"]
        base_version = token_payload["version"]

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        assert dm_socket.is_connected()
        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id})
        dm_socket.get_received()

        update_payload = {
            "campaign_id": campaign.id,
            "session_id": session.id,
            "token_id": token_id,
            "client_event_id": "dedupe-update-1",
            "base_version": base_version,
            "patch": {"x": 9},
        }
        dm_socket.emit("token:update", update_payload)
        first_events = dm_socket.get_received()
        assert any(event["name"] == "token:updated" for event in first_events)

        dm_socket.emit("token:update", update_payload)
        second_events = dm_socket.get_received()
        assert any(event["name"] == "state:duplicate" for event in second_events)
        assert not any(event["name"] == "token:updated" for event in second_events)

        state_response = dm_client.get(f"/api/campaigns/{campaign.id}/sessions/{session.id}/state")
        assert state_response.status_code == 200
        tokens = state_response.get_json()["tokens"]
        updated_token = next(token for token in tokens if token["id"] == token_id)
        assert updated_token["x"] == 9
        dm_socket.disconnect()

    def test_session_join_switches_active_room_for_same_socket(self, app, dm_client, dm_user):
        campaign_one = _create_campaign(dm_user, "Switch Campaign One")
        campaign_two = _create_campaign(dm_user, "Switch Campaign Two")
        _, session_one = _add_map_and_session(campaign_one, dm_user, "Switch Map One", "Switch Session One")
        _, session_two = _add_map_and_session(campaign_two, dm_user, "Switch Map Two", "Switch Session Two")

        dm_socket = socketio.test_client(app, flask_test_client=dm_client)
        assert dm_socket.is_connected()

        dm_socket.emit("session:join", {"campaign_id": campaign_one.id, "session_id": session_one.id})
        dm_socket.get_received()
        dm_socket.emit("session:join", {"campaign_id": campaign_two.id, "session_id": session_two.id})
        dm_socket.get_received()

        dm_socket.emit(
            "token:create",
            {
                "campaign_id": campaign_one.id,
                "session_id": session_one.id,
                "client_event_id": "switch-room-create-1",
                "token": {"name": "Old Room Token", "x": 1, "y": 1, "token_type": "player"},
            },
        )
        old_room_events = dm_socket.get_received()
        assert not any(event["name"] == "token:created" for event in old_room_events)

        dm_socket.emit(
            "token:create",
            {
                "campaign_id": campaign_two.id,
                "session_id": session_two.id,
                "client_event_id": "switch-room-create-2",
                "token": {"name": "New Room Token", "x": 2, "y": 2, "token_type": "player"},
            },
        )
        new_room_events = dm_socket.get_received()
        assert any(event["name"] == "token:created" for event in new_room_events)
        dm_socket.disconnect()

    def test_api_token_update_requires_owner_or_dm(self, dm_user, player_user, outsider_user, dm_client, player_client, outsider_client):
        campaign = _create_campaign(dm_user, "Ownership Campaign")
        _add_member(campaign, player_user)
        _add_member(campaign, outsider_user)
        _, session = _add_map_and_session(campaign, dm_user, "Owner Map", "Owner Session")

        create_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens",
            json={"name": "Player Token", "x": 1, "y": 1, "token_type": "player"},
        )
        assert create_response.status_code == 201
        token_id = create_response.get_json()["token"]["id"]

        forbidden = outsider_client.put(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens/{token_id}",
            json={"patch": {"x": 4}},
        )
        assert forbidden.status_code == 403

        allowed = dm_client.put(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/tokens/{token_id}",
            json={"patch": {"x": 6}},
        )
        assert allowed.status_code == 200
