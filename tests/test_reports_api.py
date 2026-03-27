"""M7 tests: report workflow API."""

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
        name="Reports Campaign",
        description="reports test campaign",
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
        name="Reports Map",
        width=25,
        height=25,
        created_by=owner_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()

    session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Reports Session",
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
    user = User(username="report_dm", email="report_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="report_player", email="report_player@test.com", role_id=1)
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


class TestReportsApi:
    def test_player_can_create_report_for_message(self, dm_user, player_user, dm_client, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        message_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "A problematic message"},
        )
        assert message_response.status_code == 201
        message_id = message_response.get_json()["message"]["id"]

        report_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/reports",
            json={"target_message_id": message_id, "reason_code": "abuse", "description": "please review"},
        )
        assert report_response.status_code == 201
        report = report_response.get_json()["report"]
        assert report["status"] == "open"
        assert report["target_message_id"] == message_id

    def test_player_cannot_view_report_queue(self, dm_user, player_user, player_client):
        campaign, _ = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        response = player_client.get(f"/api/campaigns/{campaign.id}/reports")
        assert response.status_code == 403

    def test_dm_can_assign_and_resolve_report(self, dm_user, player_user, dm_client, player_client):
        campaign, game_session = _create_campaign_with_session(dm_user)
        _add_member(campaign, player_user)

        message_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/chat/messages",
            json={"content": "message for report lifecycle"},
        )
        message_id = message_response.get_json()["message"]["id"]

        report_response = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/reports",
            json={"target_message_id": message_id, "reason_code": "spam"},
        )
        report_id = report_response.get_json()["report"]["id"]

        assign_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/reports/{report_id}/assign",
            json={"assigned_to_user_id": dm_user.id},
        )
        assert assign_response.status_code == 200
        assert assign_response.get_json()["report"]["status"] == "in_review"

        resolve_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/reports/{report_id}/resolve",
            json={"resolution": "resolved", "resolution_note": "handled"},
        )
        assert resolve_response.status_code == 200
        report = resolve_response.get_json()["report"]
        assert report["status"] == "resolved"
        assert report["resolved_at"] is not None
