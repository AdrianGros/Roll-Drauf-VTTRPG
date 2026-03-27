"""M6 tests: combat API lifecycle and authorization."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMap, CampaignMember, Character, GameSession, Role, User


def _login(client, username, password="Password123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


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
    user = User(username="combat_dm", email="combat_dm@test.com", role_id=2)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def player_user(app):
    user = User(username="combat_player", email="combat_player@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def outsider_user(app):
    user = User(username="combat_out", email="combat_out@test.com", role_id=1)
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
def outsider_client(app, outsider_user):
    client = app.test_client()
    _login(client, outsider_user.username)
    return client


@pytest.fixture
def combat_context(dm_user, player_user, dm_client):
    campaign = Campaign(
        name="Combat Campaign",
        description="combat api testing",
        owner_id=dm_user.id,
        status="active",
        max_players=6,
    )
    db.session.add(campaign)
    db.session.flush()

    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=dm_user.id,
            campaign_role="DM",
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=dm_user.id,
        )
    )
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=player_user.id,
            campaign_role="Player",
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=dm_user.id,
        )
    )

    campaign_map = CampaignMap(
        campaign_id=campaign.id,
        name="Battle Map",
        width=20,
        height=20,
        created_by=dm_user.id,
    )
    db.session.add(campaign_map)
    db.session.flush()

    game_session = GameSession(
        campaign_id=campaign.id,
        map_id=campaign_map.id,
        name="Battle Session",
        status="in_progress",
    )
    db.session.add(game_session)
    db.session.flush()

    linked_character = Character(
        user_id=player_user.id,
        campaign_id=campaign.id,
        name="Frontliner",
        class_name="Fighter",
        hp_current=20,
        hp_max=20,
        dex_score=12,
    )
    db.session.add(linked_character)
    db.session.commit()

    token_one_response = dm_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/tokens",
        json={
            "name": "Frontliner Token",
            "x": 2,
            "y": 3,
            "token_type": "player",
            "owner_user_id": player_user.id,
            "character_id": linked_character.id,
            "hp_current": 20,
            "hp_max": 20,
        },
    )
    assert token_one_response.status_code == 201
    token_one_id = token_one_response.get_json()["token"]["id"]

    token_two_response = dm_client.post(
        f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/tokens",
        json={
            "name": "Orc",
            "x": 5,
            "y": 6,
            "token_type": "monster",
            "hp_current": 15,
            "hp_max": 15,
        },
    )
    assert token_two_response.status_code == 201
    token_two_id = token_two_response.get_json()["token"]["id"]

    return {
        "campaign": campaign,
        "session": game_session,
        "linked_character_id": linked_character.id,
        "token_one_id": token_one_id,
        "token_two_id": token_two_id,
    }


class TestCombatApi:
    def test_start_and_read_combat_state(self, dm_client, combat_context):
        campaign = combat_context["campaign"]
        game_session = combat_context["session"]

        start_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/start",
            json={"mode": "auto"},
        )
        assert start_response.status_code == 201
        body = start_response.get_json()
        assert body["encounter"]["status"] == "active"
        assert len(body["participants"]) == 2

        state_response = dm_client.get(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/state"
        )
        assert state_response.status_code == 200
        state_body = state_response.get_json()
        assert state_body["encounter"]["id"] == body["encounter"]["id"]

    def test_initiative_conflict_and_update(self, dm_client, combat_context):
        campaign = combat_context["campaign"]
        game_session = combat_context["session"]
        token_one_id = combat_context["token_one_id"]
        token_two_id = combat_context["token_two_id"]

        start_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/start",
            json={"mode": "manual"},
        )
        assert start_response.status_code == 201
        encounter_version = start_response.get_json()["encounter"]["version"]

        conflict_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/initiative",
            json={
                "base_version": 999,
                "entries": [{"token_id": token_one_id, "initiative": 18}],
            },
        )
        assert conflict_response.status_code == 409

        update_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/initiative",
            json={
                "base_version": encounter_version,
                "entries": [
                    {"token_id": token_one_id, "initiative": 18},
                    {"token_id": token_two_id, "initiative": 12},
                ],
            },
        )
        assert update_response.status_code == 200
        update_payload = update_response.get_json()
        assert update_payload["encounter"]["version"] > encounter_version
        assert update_payload["encounter"]["initiative_order"][0] == token_one_id

    def test_turn_advance_and_end(self, dm_client, combat_context):
        campaign = combat_context["campaign"]
        game_session = combat_context["session"]

        start_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/start",
            json={"mode": "manual"},
        )
        assert start_response.status_code == 201
        version = start_response.get_json()["encounter"]["version"]

        advance_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/turn/advance",
            json={"base_version": version},
        )
        assert advance_response.status_code == 200
        advanced = advance_response.get_json()
        assert advanced["encounter"]["version"] > version

        end_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/end",
            json={"base_version": advanced["encounter"]["version"]},
        )
        assert end_response.status_code == 200
        assert end_response.get_json()["encounter"]["status"] == "completed"

    def test_hp_adjust_mirrors_linked_character(self, dm_client, combat_context):
        campaign = combat_context["campaign"]
        game_session = combat_context["session"]
        token_one_id = combat_context["token_one_id"]
        linked_character_id = combat_context["linked_character_id"]

        start_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/start",
            json={"mode": "manual"},
        )
        assert start_response.status_code == 201
        version = start_response.get_json()["encounter"]["version"]

        adjust_response = dm_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/hp-adjust",
            json={
                "base_version": version,
                "target_token_id": token_one_id,
                "delta": -7,
                "reason": "test hit",
            },
        )
        assert adjust_response.status_code == 200
        payload = adjust_response.get_json()
        participant = next(token for token in payload["participants"] if token["id"] == token_one_id)
        assert participant["hp_current"] == 13

        linked_character = Character.query.get(linked_character_id)
        assert linked_character.hp_current == 13

    def test_non_dm_cannot_mutate_combat(self, player_client, combat_context):
        campaign = combat_context["campaign"]
        game_session = combat_context["session"]

        forbidden_start = player_client.post(
            f"/api/campaigns/{campaign.id}/sessions/{game_session.id}/combat/start",
            json={"mode": "auto"},
        )
        assert forbidden_start.status_code == 403
