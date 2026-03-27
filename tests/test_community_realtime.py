"""M7 tests: community realtime room and moderation channel behavior."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db, socketio
from vtt_app.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, User


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


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


def _add_member(campaign, user, role="Player"):
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=user.id,
            campaign_role=role,
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=campaign.owner_id,
        )
    )
    db.session.commit()


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
    user = User(username="rt_comm_dm", email="rt_comm_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="rt_comm_player", email="rt_comm_player@test.com", role_id=1)
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


class TestCommunityRealtime:
    def test_chat_event_is_session_room_scoped(self, dm_user, player_user, dm_client, player_client):
        campaign_one, session_one = _create_campaign_with_session(dm_user, "Community One")
        campaign_two, session_two = _create_campaign_with_session(dm_user, "Community Two")
        _add_member(campaign_one, player_user)
        _add_member(campaign_two, player_user)

        dm_socket = socketio.test_client(dm_client.application, flask_test_client=dm_client)
        player_socket = socketio.test_client(player_client.application, flask_test_client=player_client)
        assert dm_socket.is_connected()
        assert player_socket.is_connected()

        dm_socket.emit("session:join", {"campaign_id": campaign_one.id, "session_id": session_one.id})
        player_socket.emit("session:join", {"campaign_id": campaign_two.id, "session_id": session_two.id})
        dm_socket.get_received()
        player_socket.get_received()

        create_response = dm_client.post(
            f"/api/campaigns/{campaign_one.id}/sessions/{session_one.id}/chat/messages",
            json={"content": "room scoped event"},
        )
        assert create_response.status_code == 201

        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(event["name"] == "chat:message_created" for event in dm_events)
        assert not any(event["name"] == "chat:message_created" for event in player_events)

        dm_socket.disconnect()
        player_socket.disconnect()

    def test_report_created_event_reaches_mod_room_only(self, dm_user, player_user, dm_client, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user, "Community Mod")
        _add_member(campaign, player_user)

        dm_socket = socketio.test_client(dm_client.application, flask_test_client=dm_client)
        player_socket = socketio.test_client(player_client.application, flask_test_client=player_client)
        assert dm_socket.is_connected()
        assert player_socket.is_connected()

        dm_socket.emit("mod:join", {"campaign_id": campaign.id})
        player_socket.emit("mod:join", {"campaign_id": campaign.id})
        dm_socket.get_received()
        player_socket.get_received()

        msg_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "please moderate this"},
        )
        message_id = msg_response.get_json()["message"]["id"]

        report_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/reports",
            json={"target_message_id": message_id, "reason_code": "abuse"},
        )
        assert report_response.status_code == 201

        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(event["name"] == "moderation:report_created" for event in dm_events)
        assert not any(event["name"] == "moderation:report_created" for event in player_events)

        dm_socket.disconnect()
        player_socket.disconnect()

    def test_dice_roll_is_not_globally_broadcast(self, dm_user, player_user, dm_client, player_client):
        campaign_one, session_one = _create_campaign_with_session(dm_user, "Dice One")
        campaign_two, session_two = _create_campaign_with_session(dm_user, "Dice Two")
        _add_member(campaign_one, player_user)
        _add_member(campaign_two, player_user)

        dm_socket = socketio.test_client(dm_client.application, flask_test_client=dm_client)
        player_socket = socketio.test_client(player_client.application, flask_test_client=player_client)
        assert dm_socket.is_connected()
        assert player_socket.is_connected()

        dm_socket.emit("session:join", {"campaign_id": campaign_one.id, "session_id": session_one.id})
        player_socket.emit("session:join", {"campaign_id": campaign_two.id, "session_id": session_two.id})
        dm_socket.get_received()
        player_socket.get_received()

        dm_socket.emit(
            "roll_dice",
            {"dice": "1d20", "player": "dm", "campaign_id": campaign_one.id, "session_id": session_one.id},
            callback=True,
        )

        dm_events = dm_socket.get_received()
        player_events = player_socket.get_received()
        assert any(event["name"] == "dice_rolled" for event in dm_events)
        assert not any(event["name"] == "dice_rolled" for event in player_events)

        dm_socket.disconnect()
        player_socket.disconnect()
