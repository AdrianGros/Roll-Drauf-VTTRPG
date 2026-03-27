"""M7 tests: moderation action policy matrix."""

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
        name="Moderation Campaign",
        description="moderation test campaign",
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
        name="Moderation Map",
        width=15,
        height=15,
        created_by=owner_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()

    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Moderation Session",
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
    user = User(username="mod_dm", email="mod_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="mod_player", email="mod_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(app):
    user = User(username="mod_admin", email="mod_admin@test.com", role_id=3)
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


@pytest.fixture
def admin_client(app, admin_user):
    client = app.test_client()
    _login(client, admin_user.username)
    return client


class TestModerationActions:
    def test_player_cannot_apply_moderation_action(self, dm_user, player_user, player_client):
        campaign, _ = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        response = player_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions",
            json={"action_type": "mute", "subject_user_id": player_user.id, "duration_minutes": 10},
        )
        assert response.status_code == 403

    def test_dm_cannot_apply_ban(self, dm_user, player_user, dm_client):
        campaign, _ = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        response = dm_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions",
            json={"action_type": "ban", "subject_user_id": player_user.id},
        )
        assert response.status_code == 400

    def test_admin_can_ban_and_revoke(self, dm_user, player_user, admin_client):
        campaign, _ = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        create_response = admin_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions",
            json={"action_type": "ban", "subject_user_id": player_user.id, "reason": "escalated"},
        )
        assert create_response.status_code == 201
        action = create_response.get_json()["action"]
        assert action["action_type"] == "ban"
        assert action["is_active"] is True

        revoke_response = admin_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions/{action['id']}/revoke"
        )
        assert revoke_response.status_code == 200
        revoked = revoke_response.get_json()["action"]
        assert revoked["is_active"] is False

    def test_delete_message_action_soft_deletes_chat_message(self, dm_user, player_user, dm_client, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        message_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "moderate me"},
        )
        message_id = message_response.get_json()["message"]["id"]

        action_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/moderation/actions",
            json={"action_type": "delete_message", "subject_message_id": message_id, "reason": "cleanup"},
        )
        assert action_response.status_code == 201

        list_response = player_client.get(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages"
        )
        assert list_response.status_code == 200
        message_payload = list_response.get_json()["messages"][0]
        assert message_payload["content"] == "[message removed]"
