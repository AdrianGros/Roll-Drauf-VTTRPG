"""M5 tests: persisted session state endpoints."""

from datetime import datetime

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import (
    Campaign,
    CampaignMap,
    CampaignMember,
    GameSession,
    Role,
    SceneLayer,
    SceneStack,
    SessionState,
    User,
)


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

    def test_activate_map_stays_in_sync_with_the_scene_stack(self, dm_user, dm_client):
        """Regression test for the write-path unification (robot audit,
        2026-08-23, Arc 0.4): this legacy endpoint (still called from
        campaigns.html's pre-session map picker) used to write
        SessionState.active_map_id directly, bypassing the scene-stack
        model entirely -- so a map activated here got silently discarded
        the moment init_scene_stack() next ran (it always activates its
        own first layer), and no scene-stack-aware client ever heard
        about the change. It must now go through the same
        activate_scene_layer() path /play uses, so scene_stack.active_layer_id
        and state.active_map_id can never diverge, and re-activating an
        already-picked map must not create a duplicate layer."""
        campaign = _create_campaign(dm_user)
        map_one = CampaignMap(campaign_id=campaign.id, name="Map 1", width=20, height=20, created_by=dm_user.id)
        map_two = CampaignMap(campaign_id=campaign.id, name="Map 2", width=20, height=20, created_by=dm_user.id)
        db.session.add_all([map_one, map_two])
        db.session.flush()
        session = GameSession(campaign_id=campaign.id, name="Session Sync", status="scheduled")
        db.session.add(session)
        db.session.commit()

        first = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/maps/activate",
            json={"map_id": map_one.id},
        )
        assert first.status_code == 200

        scene_stack = SceneStack.query.filter_by(game_session_id=session.id).first()
        assert scene_stack is not None, "activating a map must create a scene stack, not bypass it"
        state = SessionState.query.filter_by(game_session_id=session.id).first()
        active_layer = db.session.get(SceneLayer, scene_stack.active_layer_id)
        assert active_layer.campaign_map_id == map_one.id
        assert state.active_map_id == map_one.id, "state.active_map_id must match the scene stack's active layer"

        # Switching to a second map must reuse the same scene stack, not
        # fight it or spawn a second one.
        second = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/maps/activate",
            json={"map_id": map_two.id},
        )
        assert second.status_code == 200
        db.session.refresh(scene_stack)
        db.session.refresh(state)
        active_layer = db.session.get(SceneLayer, scene_stack.active_layer_id)
        assert active_layer.campaign_map_id == map_two.id
        assert state.active_map_id == map_two.id
        assert SceneStack.query.filter_by(game_session_id=session.id).count() == 1

        # Re-activating a map that already has a layer must not create a
        # duplicate layer for it (add_scene_layer's own 409 guard would
        # otherwise surface here as a user-facing error on a click that
        # should just be idempotent).
        third = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{session.id}/maps/activate",
            json={"map_id": map_one.id},
        )
        assert third.status_code == 200
        assert SceneLayer.query.filter_by(
            scene_stack_id=scene_stack.id, campaign_map_id=map_one.id
        ).count() == 1

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
