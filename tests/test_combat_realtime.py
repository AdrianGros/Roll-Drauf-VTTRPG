"""M6 tests: combat realtime room broadcasts."""

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


def _add_active_member(campaign, user, campaign_role, invited_by):
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=user.id,
            campaign_role=campaign_role,
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=invited_by,
        )
    )
    db.session.commit()


def _create_campaign_with_session(owner_user, name):
    campaign = Campaign(
        name=name,
        description=f"{name} description",
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

    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name=f"{name} map",
        width=20,
        height=20,
        created_by=owner_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()

    game_session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name=f"{name} session",
        status="in_progress",
    )
    db.session.add(game_session)
    db.session.commit()
    return campaign, game_session


def _seed_tokens(dm_client, campaign_id, session_id):
    token_a = dm_client.post(
        f"/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
        json={"name": "Hero", "x": 1, "y": 1, "token_type": "player", "hp_current": 15, "hp_max": 15},
    )
    assert token_a.status_code == 201
    token_b = dm_client.post(
        f"/api/campaigns/{campaign_id}/sessions/{session_id}/tokens",
        json={"name": "Goblin", "x": 3, "y": 3, "token_type": "monster", "hp_current": 7, "hp_max": 7},
    )
    assert token_b.status_code == 201


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
    user = User(username="rt_combat_dm", email="rt_combat_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="rt_combat_player", email="rt_combat_player@test.com", role_id=1)
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


class TestCombatRealtime:
    def test_combat_started_event_is_room_scoped(self, dm_user, player_user, dm_client, player_client):
        campaign_one, session_one = _create_campaign_with_session(dm_user, "Realtime Combat One")
        campaign_two, session_two = _create_campaign_with_session(dm_user, "Realtime Combat Two")
        _add_active_member(campaign_one, player_user, "Player", dm_user.id)
        _add_active_member(campaign_two, player_user, "Player", dm_user.id)

        _seed_tokens(dm_client, campaign_one.id, session_one.id)
        _seed_tokens(dm_client, campaign_two.id, session_two.id)

        dm_socket = socketio.test_client(dm_client.application, flask_test_client=dm_client)
        player_socket = socketio.test_client(player_client.application, flask_test_client=player_client)
        assert dm_socket.is_connected()
        assert player_socket.is_connected()

        dm_socket.emit("session:join", {"campaign_id": campaign_one.id, "session_id": session_one.id})
        player_socket.emit("session:join", {"campaign_id": campaign_two.id, "session_id": session_two.id})
        dm_socket.get_received()
        player_socket.get_received()

        start_response = dm_client.post(
            f"/api/campaigns/{campaign_one.id}/sessions/{session_one.id}/combat/start",
            json={"mode": "auto"},
        )
        assert start_response.status_code == 201

        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(event["name"] == "combat:started" for event in dm_events)
        assert not any(event["name"] == "combat:started" for event in player_events)

        dm_socket.disconnect()
        player_socket.disconnect()

    def test_combat_turn_event_reaches_same_room_members(self, dm_user, player_user, dm_client, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user, "Realtime Turn")
        _add_active_member(campaign, player_user, "Player", dm_user.id)
        _seed_tokens(dm_client, campaign.id, game_session.id)

        dm_socket = socketio.test_client(dm_client.application, flask_test_client=dm_client)
        player_socket = socketio.test_client(player_client.application, flask_test_client=player_client)
        assert dm_socket.is_connected()
        assert player_socket.is_connected()

        dm_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": game_session.id})
        player_socket.emit("session:join", {"campaign_id": campaign.id, "session_id": game_session.id})
        dm_socket.get_received()
        player_socket.get_received()

        start_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/start",
            json={"mode": "manual"},
        )
        assert start_response.status_code == 201
        dm_socket.get_received()
        player_socket.get_received()

        state_response = dm_client.get(f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/state")
        assert state_response.status_code == 200
        encounter_version = state_response.get_json()["encounter"]["version"]

        turn_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/turn/advance",
            json={"base_version": encounter_version},
        )
        assert turn_response.status_code == 200

        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(event["name"] == "combat:turn" for event in dm_events)
        assert any(event["name"] == "combat:turn" for event in player_events)

        dm_socket.disconnect()
        player_socket.disconnect()
