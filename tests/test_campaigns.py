"""M4 Tests: Campaign endpoints."""

from datetime import datetime, timedelta

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMember, GameSession, InviteToken, Role, User


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name="Test Campaign"):
    campaign = Campaign(
        name=name,
        description="A test campaign",
        owner_id=owner_user.id,
        status="active",
        max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()

    owner_member = CampaignMember(
        campaign_id=campaign.id,
        user_id=owner_user.id,
        campaign_role="DM",
        status="active",
        joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(),
        invited_by=owner_user.id,
    )
    db.session.add(owner_member)
    db.session.commit()
    return campaign


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
    user = User(username="dm_test", email="dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="player_test", email="player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def other_user(app):
    user = User(username="other_test", email="other@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "dm_test")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "player_test")
    return client


@pytest.fixture
def other_client(app, other_user):
    client = app.test_client()
    _login(client, "other_test")
    return client


class TestCampaignCRUD:
    def test_create_campaign(self, dm_client):
        response = dm_client.post(
            "/api/campaigns",
            json={"name": "Dragon Quest", "description": "Slay dragons", "max_players": 6},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Dragon Quest"
        assert data["status"] == "active"
        assert data["is_owner"] is True

    def test_get_campaign_details_success(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        response = dm_client.get(f"/api/campaigns/{campaign.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["campaign"]["id"] == campaign.id
        assert "members" in data
        assert "sessions" in data

    def test_get_campaign_details_forbidden_for_non_member(self, player_client, dm_user):
        campaign = _create_campaign(dm_user)
        response = player_client.get(f"/api/campaigns/{campaign.id}")
        assert response.status_code == 403

    def test_list_my_campaigns(self, dm_client, dm_user):
        _create_campaign(dm_user, name="Mine")
        response = dm_client.get("/api/campaigns/mine")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["campaigns"]) == 1
        assert data["campaigns"][0]["name"] == "Mine"

    def test_update_campaign(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        response = dm_client.put(
            f"/api/campaigns/{campaign.id}",
            json={"name": "Updated Campaign", "status": "paused", "max_players": 8},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated Campaign"
        assert data["status"] == "paused"
        assert data["max_players"] == 8

    def test_update_campaign_forbidden_for_player(self, player_client, dm_user, player_user):
        campaign = _create_campaign(dm_user)
        db.session.add(
            CampaignMember(
                campaign_id=campaign.id,
                user_id=player_user.id,
                campaign_role="Player",
                status="active",
                joined_at=datetime.utcnow(),
            )
        )
        db.session.commit()

        response = player_client.put(
            f"/api/campaigns/{campaign.id}",
            json={"name": "Not Allowed"},
        )
        assert response.status_code == 403

    def test_delete_campaign_soft_delete(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        response = dm_client.delete(f"/api/campaigns/{campaign.id}")
        assert response.status_code == 200

        deleted = Campaign.query.get(campaign.id)
        assert deleted is not None
        assert deleted.deleted_at is not None

    def test_delete_campaign_forbidden_for_non_owner(self, player_client, dm_user, player_user):
        campaign = _create_campaign(dm_user)
        db.session.add(
            CampaignMember(
                campaign_id=campaign.id,
                user_id=player_user.id,
                campaign_role="Player",
                status="active",
                joined_at=datetime.utcnow(),
            )
        )
        db.session.commit()

        response = player_client.delete(f"/api/campaigns/{campaign.id}")
        assert response.status_code == 403


class TestCampaignInvites:
    def test_invite_player(self, dm_client, dm_user, player_user):
        campaign = _create_campaign(dm_user)

        response = dm_client.post(
            f"/api/campaigns/{campaign.id}/invite",
            json={"player_username": "player_test"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "invite_token" in data
        assert data["invited_user"] == "player_test"

    def test_duplicate_invite_returns_409(self, dm_client, dm_user, player_user):
        campaign = _create_campaign(dm_user)

        first = dm_client.post(
            f"/api/campaigns/{campaign.id}/invite",
            json={"player_username": "player_test"},
        )
        second = dm_client.post(
            f"/api/campaigns/{campaign.id}/invite",
            json={"player_username": "player_test"},
        )

        assert first.status_code == 201
        assert second.status_code == 409

    def test_accept_invite_success(self, dm_client, player_client, dm_user, player_user):
        campaign = _create_campaign(dm_user)
        invite_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/invite",
            json={"player_username": "player_test"},
        )
        token = invite_response.get_json()["invite_token"]

        response = player_client.post(
            f"/api/campaigns/{campaign.id}/accept-invite",
            json={"token": token},
        )
        assert response.status_code == 200

        member = CampaignMember.query.filter_by(campaign_id=campaign.id, user_id=player_user.id).first()
        assert member is not None
        assert member.status == "active"
        assert member.accepted_at is not None

        invite = InviteToken.query.filter_by(campaign_id=campaign.id, token=token).first()
        assert invite is not None
        assert invite.used_at is not None

    def test_accept_invite_invalid_token(self, player_client, dm_user):
        campaign = _create_campaign(dm_user)
        response = player_client.post(
            f"/api/campaigns/{campaign.id}/accept-invite",
            json={"token": "invalid-token"},
        )
        assert response.status_code == 400

    def test_members_endpoint(self, dm_client, dm_user, player_user):
        campaign = _create_campaign(dm_user)
        db.session.add(
            CampaignMember(
                campaign_id=campaign.id,
                user_id=player_user.id,
                campaign_role="Player",
                status="active",
                joined_at=datetime.utcnow(),
            )
        )
        db.session.commit()

        response = dm_client.get(f"/api/campaigns/{campaign.id}/members")
        assert response.status_code == 200
        data = response.get_json()
        assert "members" in data
        assert len(data["members"]) >= 2

    def test_members_endpoint_forbidden(self, other_client, dm_user):
        campaign = _create_campaign(dm_user)
        response = other_client.get(f"/api/campaigns/{campaign.id}/members")
        assert response.status_code == 403


class TestGameSessions:
    def test_create_session(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        scheduled = (datetime.utcnow() + timedelta(days=1)).isoformat()
        response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions",
            json={"name": "Session 1", "scheduled_at": scheduled, "duration_minutes": 180},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Session 1"
        assert data["status"] == "scheduled"

    def test_list_sessions(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        session = GameSession(campaign_id=campaign.id, name="Session Alpha", status="scheduled")
        db.session.add(session)
        db.session.commit()

        response = dm_client.get(f"/api/campaigns/{campaign.id}/sessions")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["name"] == "Session Alpha"

    def test_start_session(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        session = GameSession(campaign_id=campaign.id, name="Session Start", status="scheduled")
        db.session.add(session)
        db.session.commit()

        response = dm_client.post(f"/api/campaigns/{campaign.id}/sessions/{session.id}/start")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "in_progress"
        assert data["started_at"] is not None

    def test_end_session(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        session = GameSession(
            campaign_id=campaign.id,
            name="Session End",
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db.session.add(session)
        db.session.commit()

        response = dm_client.post(f"/api/campaigns/{campaign.id}/sessions/{session.id}/end")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "completed"

    def test_start_session_conflict_when_other_active_exists(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        session_one = GameSession(campaign_id=campaign.id, name="Session 1", status="scheduled")
        session_two = GameSession(campaign_id=campaign.id, name="Session 2", status="scheduled")
        db.session.add_all([session_one, session_two])
        db.session.commit()

        first_start = dm_client.post(f"/api/campaigns/{campaign.id}/sessions/{session_one.id}/start")
        second_start = dm_client.post(f"/api/campaigns/{campaign.id}/sessions/{session_two.id}/start")

        assert first_start.status_code == 200
        assert second_start.status_code == 409

    def test_end_session_conflict_wrong_state(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        session = GameSession(campaign_id=campaign.id, name="Session Pending", status="scheduled")
        db.session.add(session)
        db.session.commit()

        response = dm_client.post(f"/api/campaigns/{campaign.id}/sessions/{session.id}/end")
        assert response.status_code == 409
