"""M5 tests: campaign map catalog endpoints."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMap, CampaignMember, Role, User


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name="Map Campaign"):
    campaign = Campaign(
        name=name,
        description="campaign for map tests",
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
    user = User(username="map_dm", email="map_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="map_player", email="map_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def other_user(app):
    user = User(username="map_other", email="map_other@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "map_dm")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "map_player")
    return client


@pytest.fixture
def other_client(app, other_user):
    client = app.test_client()
    _login(client, "map_other")
    return client


class TestCampaignMaps:
    def test_dm_can_create_map(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        response = dm_client.post(
            f"/api/campaigns/{campaign.id}/maps",
            json={
                "name": "Dungeon Level 1",
                "width": 40,
                "height": 30,
                "grid_size": 32,
                "fog_enabled": True,
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Dungeon Level 1"
        assert data["campaign_id"] == campaign.id
        assert data["fog_enabled"] is True

    def test_player_cannot_create_map(self, dm_user, player_user, player_client):
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")
        response = player_client.post(
            f"/api/campaigns/{campaign.id}/maps",
            json={"name": "Not Allowed", "width": 20, "height": 20},
        )
        assert response.status_code == 403

    def test_member_can_list_maps(self, dm_client, player_client, dm_user, player_user):
        campaign = _create_campaign(dm_user)
        _add_member(campaign, player_user, "Player")
        map_row = CampaignMap(
            campaign_id=campaign.id,
            name="City Map",
            width=25,
            height=25,
            created_by=dm_user.id,
        )
        db.session.add(map_row)
        db.session.commit()

        response = player_client.get(f"/api/campaigns/{campaign.id}/maps")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["maps"]) == 1
        assert data["maps"][0]["name"] == "City Map"

    def test_non_member_cannot_list_maps(self, dm_user, other_client):
        campaign = _create_campaign(dm_user)
        response = other_client.get(f"/api/campaigns/{campaign.id}/maps")
        assert response.status_code == 403

    def test_archive_map_hides_from_listing(self, dm_client, dm_user):
        campaign = _create_campaign(dm_user)
        map_row = CampaignMap(
            campaign_id=campaign.id,
            name="Archive Me",
            width=20,
            height=20,
            created_by=dm_user.id,
        )
        db.session.add(map_row)
        db.session.commit()

        archive_response = dm_client.delete(f"/api/campaigns/{campaign.id}/maps/{map_row.id}")
        assert archive_response.status_code == 200

        list_response = dm_client.get(f"/api/campaigns/{campaign.id}/maps")
        assert list_response.status_code == 200
        listed_ids = [entry["id"] for entry in list_response.get_json()["maps"]]
        assert map_row.id not in listed_ids
