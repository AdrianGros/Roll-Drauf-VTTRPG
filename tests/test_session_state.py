"""M5 tests: persisted session state endpoints."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, SessionState, User


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name="State Campaign"):
    campaign = Campaign(
        name=name,
        description="campaign for state tests",
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
    member = CampaignMember(
        campaign_id=campaign.id,
        user_id=user.id,
        campaign_role=campaign_role,
        status="active",
        joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(),
        invited_by=campaign.owner_id,
    )
    db.session.add(member)
    db.session.commit()
    return member


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
    user = User(username="state_dm", email="state_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="state_player", email="state_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def outsider_user(app):
    user = User(username="state_out", email="state_out@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "state_dm")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "state_player")
    return client


@pytest.fixture
def outsider_client(app, outsider_user):
    client = app.test_client()
    _login(client, "state_out")
    return client


class TestSessionState:
    def test_get_state_bootstraps_state(self, dm_user, player_user, player_client):
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")
        map_row = CampaignMap(
            campaign_id=campaign.id,
            name="Bootstrap Map",
            width=30,
            height=20,
            created_by=dm_user.id,
        )
        db.session.add(map_row)
        db.session.flush()
        session = GameSession(campaign_id=campaign.id, name="Session Bootstrap", status="scheduled")
        db.session.add(session)
        db.session.commit()

        response = player_client.get(f"/api/campaigns/{campaign.id}/sessions/{session.id}/state")
        assert response.status_code == 200
        data = response.get_json()
        assert data["state"]["game_session_id"] == session.id
        assert data["active_map"]["id"] == map_row.id

    def test_activate_map_dm_only(self, dm_user, player_user, dm_client, player_client):
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")
        map_one = CampaignMap(campaign_id=campaign.id, name="Map 1", width=20, height=20, created_by=dm_user.id)
        map_two = CampaignMap(campaign_id=campaign.id, name="Map 2", width=20, height=20, created_by=dm_user.id)
        db.session.add_all([map_one, map_two])
        db.session.flush()
        session = GameSession(campaign_id=campaign.id, name="Session Activate", status="scheduled")
        db.session.add(session)
        db.session.commit()

        forbidden = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/maps/activate",
            json={"map_id": map_two.id},
        )
        assert forbidden.status_code == 403

        allowed = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/maps/activate",
            json={"map_id": map_two.id},
        )
        assert allowed.status_code == 200
        body = allowed.get_json()
        assert body["active_map"]["id"] == map_two.id

    def test_state_persists_between_requests(self, dm_user, dm_client):
        campaign = _create_campaign(dm_user)
        map_row = CampaignMap(campaign_id=campaign.id, name="Persist Map", width=20, height=20, created_by=dm_user.id)
        db.session.add(map_row)
        db.session.flush()
        session = GameSession(campaign_id=campaign.id, name="Persist Session", status="scheduled")
        db.session.add(session)
        db.session.commit()

        first = dm_client.get(f"/api/campaigns/{campaign.id}/sessions/{session.id}/state")
        second = dm_client.get(f"/api/campaigns/{campaign.id}/sessions/{session.id}/state")
        assert first.status_code == 200
        assert second.status_code == 200

        first_id = first.get_json()["state"]["id"]
        second_id = second.get_json()["state"]["id"]
        assert first_id == second_id
        assert SessionState.query.filter_by(game_session_id=session.id).count() == 1

    def test_non_member_cannot_get_state(self, dm_user, outsider_client):
        campaign = _create_campaign(dm_user)
        session = GameSession(campaign_id=campaign.id, name="Protected Session", status="scheduled")
        db.session.add(session)
        db.session.commit()

        response = outsider_client.get(f"/api/campaigns/{campaign.id}/sessions/{session.id}/state")
        assert response.status_code == 403
