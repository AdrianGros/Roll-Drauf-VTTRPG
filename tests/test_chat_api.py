"""M7 tests: community chat API."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, User


def _login(client, username, password="Password123!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


def _create_campaign_with_session(owner_user):
    campaign = Campaign(
        name="Community Campaign",
        description="community test campaign",
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
        name="Community Map",
        width=30,
        height=30,
        created_by=owner_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()

    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Community Session",
        status="in_progress",
    )
    db.session.add(session)
    db.session.commit()
    return campaign, session


def _add_member(campaign, user):
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=user.id,
            campaign_role="Player",
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
    user = User(username="chat_dm", email="chat_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="chat_player", email="chat_player@test.com", role_id=1)
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


class TestChatApi:
    def test_member_can_post_and_list_messages(self, dm_user, player_user, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        post_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "Hello table!"},
        )
        assert post_response.status_code == 201
        message_payload = post_response.get_json()["message"]
        assert message_payload["content"] == "Hello table!"

        list_response = player_client.get(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages"
        )
        assert list_response.status_code == 200
        messages = list_response.get_json()["messages"]
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello table!"

    def test_chat_post_is_idempotent_with_client_event_id(self, dm_user, player_user, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        first = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "idempotent", "client_event_id": "evt-fixed-123"},
        )
        second = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "idempotent", "client_event_id": "evt-fixed-123"},
        )

        assert first.status_code == 201
        assert second.status_code == 200
        assert first.get_json()["message"]["id"] == second.get_json()["message"]["id"]

    def test_muted_user_cannot_post_chat(self, dm_user, player_user, dm_client, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        mute_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions",
            json={"action_type": "mute", "subject_user_id": player_user.id, "duration_minutes": 15},
        )
        assert mute_response.status_code == 201

        blocked = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "am I muted?"},
        )
        assert blocked.status_code == 403

    def test_non_member_cannot_read_chat(self, dm_user, player_user, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user)

        response = player_client.get(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages"
        )
        assert response.status_code == 403
