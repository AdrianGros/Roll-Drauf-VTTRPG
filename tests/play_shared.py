"""Shared fixtures and helpers for M10 play runtime test suites."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMap, CampaignMember, GameSession, Role, TokenState, User


def login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response


def create_campaign(owner_user, name="M10 Campaign"):
    campaign = Campaign(
        name=name,
        description="campaign for m10 tests",
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


def add_member(campaign, user, campaign_role="Player"):
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


def add_map(campaign, creator_user, name="M10 Map"):
    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name=name,
        width=30,
        height=20,
        created_by=creator_user.id,
    )
    db.session.add(campaign_map)
    db.session.commit()
    return campaign_map


def create_session(campaign, name="M10 Session", status="scheduled", map_id=None):
    session = GameSession(
        campaign_id=campaign.id,
        name=name,
        status=status,
        map_id=map_id,
    )
    db.session.add(session)
    db.session.commit()
    return session


def create_token(campaign, session, state, owner_user_id, name="Hero", token_type="player", x=1, y=1):
    token = TokenState(
        session_state_id=state.id,
        campaign_id=campaign.id,
        game_session_id=session.id,
        map_id=state.active_map_id,
        owner_user_id=owner_user_id,
        name=name,
        token_type=token_type,
        x=x,
        y=y,
        size=1,
        rotation=0,
        visibility="public",
        metadata_json={},
        updated_by=owner_user_id,
        version=1,
    )
    db.session.add(token)
    db.session.commit()
    return token


@pytest.fixture
def play_app():
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
def play_dm_user(play_app):
    user = User(username="play_dm", email="play_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def play_player_user(play_app):
    user = User(username="play_player", email="play_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def play_codm_user(play_app):
    user = User(username="play_codm", email="play_codm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def play_observer_user(play_app):
    user = User(username="play_observer", email="play_observer@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def play_outsider_user(play_app):
    user = User(username="play_out", email="play_out@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def play_dm_client(play_app, play_dm_user):
    client = play_app.test_client()
    login(client, play_dm_user.username)
    return client


@pytest.fixture
def play_player_client(play_app, play_player_user):
    client = play_app.test_client()
    login(client, play_player_user.username)
    return client


@pytest.fixture
def play_codm_client(play_app, play_codm_user):
    client = play_app.test_client()
    login(client, play_codm_user.username)
    return client


@pytest.fixture
def play_observer_client(play_app, play_observer_user):
    client = play_app.test_client()
    login(client, play_observer_user.username)
    return client


@pytest.fixture
def play_outsider_client(play_app, play_outsider_user):
    client = play_app.test_client()
    login(client, play_outsider_user.username)
    return client
