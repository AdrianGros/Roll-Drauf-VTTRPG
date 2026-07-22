"""M18a tests: direct character-to-session assignment productization."""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Character, GameSession, Role, User


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def _create_campaign(owner_user, name="Session Assignment Campaign"):
    campaign = Campaign(
        name=name,
        description="Assignment test campaign",
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


def _add_active_member(campaign, user, role="Player", invited_by=None):
    member = CampaignMember(
        campaign_id=campaign.id,
        user_id=user.id,
        campaign_role=role,
        status="active",
        joined_at=datetime.utcnow(),
        invited_at=datetime.utcnow(),
        accepted_at=datetime.utcnow(),
        invited_by=invited_by or campaign.owner_id,
    )
    db.session.add(member)
    db.session.commit()
    return member


def _create_campaign_character(user, campaign, name):
    character = Character(
        user_id=user.id,
        campaign_id=campaign.id,
        name=name,
        race="Human",
        class_name="Wizard",
        level=3,
    )
    db.session.add(character)
    db.session.commit()
    return character


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
def client(app):
    return app.test_client()


@pytest.fixture
def dm_user(app):
    user = User(username="dm_assign", email="dm_assign@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="player_assign", email="player_assign@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def other_player_user(app):
    user = User(username="other_assign", email="other_assign@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dm_client(app, dm_user):
    client = app.test_client()
    _login(client, "dm_assign")
    return client


@pytest.fixture
def player_client(app, player_user):
    client = app.test_client()
    _login(client, "player_assign")
    return client


def test_campaigns_route_exposes_real_session_assignment_surface(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="sessionPrepCharacterCard"' in html
    assert "assignCharacterToPrepSession(campaignId, sessionId, characterId)" in html
    assert "unassignCharacterFromPrepSession(campaignId, sessionId, characterId)" in html
    assert "Eligibility:" in html
    assert "Session-Besetzung oeffnen" in html
    assert "Open Sheet" in html


def test_campaign_detail_exposes_campaign_characters_and_assignment_state(dm_client, dm_user, player_user):
    campaign = _create_campaign(dm_user)
    _add_active_member(campaign, player_user, invited_by=dm_user.id)
    game_session = GameSession(campaign_id=campaign.id, name="Session Prep", status="scheduled")
    db.session.add(game_session)
    db.session.commit()
    character = _create_campaign_character(player_user, campaign, "Mira")

    assign_response = dm_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/characters",
        json={"character_id": character.id},
    )
    assert assign_response.status_code == 201

    response = dm_client.get(f"/api/campaigns/{campaign.id}")
    assert response.status_code == 200
    payload = response.get_json()

    assert any(item["id"] == character.id for item in payload["characters"])
    assert any(
        assignment["session_id"] == game_session.id and assignment["character_id"] == character.id
        for assignment in payload["session_character_assignments"]
    )


def test_dm_can_assign_and_remove_session_character(dm_client, dm_user, player_user):
    campaign = _create_campaign(dm_user)
    _add_active_member(campaign, player_user, invited_by=dm_user.id)
    game_session = GameSession(campaign_id=campaign.id, name="Rostered Session", status="scheduled")
    db.session.add(game_session)
    db.session.commit()
    character = _create_campaign_character(player_user, campaign, "Thalia")

    assign_response = dm_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/characters",
        json={"character_id": character.id},
    )
    assert assign_response.status_code == 201
    assert assign_response.get_json()["assignment"]["character_id"] == character.id

    duplicate_response = dm_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/characters",
        json={"character_id": character.id},
    )
    assert duplicate_response.status_code == 409

    remove_response = dm_client.delete(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/characters/{character.id}"
    )
    assert remove_response.status_code == 200
    assert remove_response.get_json()["character_id"] == character.id


def test_player_can_assign_own_character_but_not_another_players_character(
    player_client,
    dm_user,
    player_user,
    other_player_user,
):
    campaign = _create_campaign(dm_user)
    _add_active_member(campaign, player_user, invited_by=dm_user.id)
    _add_active_member(campaign, other_player_user, invited_by=dm_user.id)
    game_session = GameSession(campaign_id=campaign.id, name="Player Assignment", status="scheduled")
    db.session.add(game_session)
    db.session.commit()
    own_character = _create_campaign_character(player_user, campaign, "Kara")
    other_character = _create_campaign_character(other_player_user, campaign, "Dain")

    own_response = player_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/characters",
        json={"character_id": own_character.id},
    )
    assert own_response.status_code == 201

    forbidden_response = player_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/characters",
        json={"character_id": other_character.id},
    )
    assert forbidden_response.status_code == 403


def test_live_session_rejects_assignment_changes(dm_client, dm_user, player_user):
    campaign = _create_campaign(dm_user)
    _add_active_member(campaign, player_user, invited_by=dm_user.id)
    game_session = GameSession(campaign_id=campaign.id, name="Live Session", status="in_progress")
    db.session.add(game_session)
    db.session.commit()
    character = _create_campaign_character(player_user, campaign, "Soren")

    response = dm_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/characters",
        json={"character_id": character.id},
    )

    assert response.status_code == 409
    assert "before table entry or while paused" in response.get_json()["error"]
