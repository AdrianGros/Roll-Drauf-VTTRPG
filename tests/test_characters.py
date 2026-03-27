"""Character CRUD endpoint tests."""

import pytest
from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMember, Character, Role, User
from vtt_app.models.role import init_default_roles


@pytest.fixture
def app():
    """Create and configure test app."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def user_data(app):
    """Create test user and return user metadata."""
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        user = User(
            username="testuser",
            email="test@example.com",
            role_id=player_role.id,
        )
        user.set_password("TestPass123!")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "username": "testuser", "password": "TestPass123!"}


@pytest.fixture
def auth_client(client, user_data):
    """Login as default test user and return authenticated client."""
    response = client.post(
        "/api/auth/login",
        json={"username": user_data["username"], "password": user_data["password"]},
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def campaign_data(app, user_data):
    """Create test campaign and return campaign ID."""
    with app.app_context():
        campaign = Campaign(
            name="Test Campaign",
            owner_id=user_data["id"],
            max_players=6,
        )
        db.session.add(campaign)
        db.session.commit()

        member = CampaignMember(
            user_id=user_data["id"],
            campaign_id=campaign.id,
            campaign_role="DM",
        )
        db.session.add(member)
        db.session.commit()
        return campaign.id


def _create_logged_in_other_client(app):
    """Helper: create a second authenticated client for unauthorized checks."""
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        other_user = User(
            username="other",
            email="other@example.com",
            role_id=player_role.id,
        )
        other_user.set_password("OtherPass123!")
        db.session.add(other_user)
        db.session.commit()

    other_client = app.test_client()
    login_response = other_client.post(
        "/api/auth/login",
        json={"username": "other", "password": "OtherPass123!"},
    )
    assert login_response.status_code == 200
    return other_client


class TestCharacterCreate:
    """Test character creation."""

    def test_create_character_success(self, auth_client):
        """Create character successfully."""
        response = auth_client.post(
            "/api/characters",
            json={
                "name": "Thorin Oakenshield",
                "race": "Dwarf",
                "class": "Fighter",
                "level": 5,
                "ac": 16,
                "hp_max": 52,
                "str": 15,
                "dex": 10,
                "con": 14,
                "int": 13,
                "wis": 11,
                "cha": 12,
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Thorin Oakenshield"
        assert data["level"] == 5
        assert data["class"] == "Fighter"
        assert data["hp"] == "52/52"

    def test_create_character_missing_name(self, auth_client):
        """Reject character without name."""
        response = auth_client.post(
            "/api/characters",
            json={"race": "Elf", "class": "Wizard"},
        )

        assert response.status_code == 400
        assert "name" in response.get_json()["error"].lower()

    def test_create_character_with_campaign(self, auth_client, campaign_data):
        """Create character in campaign."""
        response = auth_client.post(
            "/api/characters",
            json={
                "name": "Gandalf",
                "race": "Human",
                "class": "Wizard",
                "campaign_id": campaign_data,
                "level": 12,
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Gandalf"

    def test_create_character_invalid_campaign(self, auth_client):
        """Reject character with invalid campaign."""
        response = auth_client.post(
            "/api/characters",
            json={"name": "Frodo", "campaign_id": 9999},
        )

        assert response.status_code == 404

    def test_create_character_not_campaign_member(self, app, campaign_data):
        """Reject character if not campaign member."""
        other_client = _create_logged_in_other_client(app)
        response = other_client.post(
            "/api/characters",
            json={"name": "Boromir", "campaign_id": campaign_data},
        )
        assert response.status_code == 403


class TestCharacterList:
    """Test character listing."""

    def test_list_my_characters(self, auth_client, user_data):
        """List user's characters."""
        with auth_client.application.app_context():
            char1 = Character(
                user_id=user_data["id"],
                name="Legolas",
                race="Elf",
                class_name="Ranger",
            )
            char2 = Character(
                user_id=user_data["id"],
                name="Gimli",
                race="Dwarf",
                class_name="Fighter",
            )
            db.session.add_all([char1, char2])
            db.session.commit()

        response = auth_client.get("/api/characters/mine")

        assert response.status_code == 200
        chars = response.get_json()
        assert len(chars) == 2
        assert chars[0]["name"] == "Legolas"
        assert chars[1]["name"] == "Gimli"

    def test_list_characters_empty(self, auth_client):
        """List characters when none exist."""
        response = auth_client.get("/api/characters/mine")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_characters_excludes_deleted(self, auth_client, user_data):
        """List excludes soft-deleted characters."""
        from datetime import datetime

        with auth_client.application.app_context():
            char1 = Character(user_id=user_data["id"], name="Active", race="Human")
            char2 = Character(
                user_id=user_data["id"],
                name="Deleted",
                race="Human",
                deleted_at=datetime.utcnow(),
            )
            db.session.add_all([char1, char2])
            db.session.commit()

        response = auth_client.get("/api/characters/mine")

        assert response.status_code == 200
        chars = response.get_json()
        assert len(chars) == 1
        assert chars[0]["name"] == "Active"


class TestCharacterGet:
    """Test character retrieval."""

    def test_get_character_success(self, auth_client, user_data):
        """Get character details."""
        with auth_client.application.app_context():
            char = Character(
                user_id=user_data["id"],
                name="Aragorn",
                race="Human",
                class_name="Ranger",
                level=20,
                str_score=16,
                dex_score=14,
                con_score=15,
            )
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        response = auth_client.get(f"/api/characters/{char_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Aragorn"
        assert data["str"] == 16
        assert data["dex"] == 14

    def test_get_character_not_found(self, auth_client):
        """Handle nonexistent character."""
        response = auth_client.get("/api/characters/9999")
        assert response.status_code == 404

    def test_get_character_unauthorized(self, app, user_data):
        """Reject access to other user's character."""
        with app.app_context():
            char = Character(user_id=user_data["id"], name="Legolas", race="Elf")
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        other_client = _create_logged_in_other_client(app)
        response = other_client.get(f"/api/characters/{char_id}")
        assert response.status_code == 403


class TestCharacterUpdate:
    """Test character updates."""

    def test_update_character_success(self, auth_client, user_data):
        """Update character fields."""
        with auth_client.application.app_context():
            char = Character(
                user_id=user_data["id"],
                name="Aragorn",
                level=1,
                xp=0,
                hp_max=10,
                hp_current=10,
            )
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        response = auth_client.put(
            f"/api/characters/{char_id}",
            json={"level": 20, "xp": 50000, "hp_max": 100, "hp_current": 95},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["level"] == 20
        assert data["xp"] == 50000
        assert data["hp"] == "95/100"

    def test_update_character_ability_scores(self, auth_client, user_data):
        """Update ability scores."""
        with auth_client.application.app_context():
            char = Character(user_id=user_data["id"], name="Barbarian")
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        response = auth_client.put(
            f"/api/characters/{char_id}",
            json={"str": 18, "con": 16},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["str"] == 18
        assert data["con"] == 16

    def test_update_character_unauthorized(self, app, user_data):
        """Reject update by non-owner."""
        with app.app_context():
            char = Character(user_id=user_data["id"], name="Legolas")
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        other_client = _create_logged_in_other_client(app)
        response = other_client.put(f"/api/characters/{char_id}", json={"level": 20})
        assert response.status_code == 403

    def test_update_character_clamp_hp(self, auth_client, user_data):
        """Clamp HP to max when updating."""
        with auth_client.application.app_context():
            char = Character(user_id=user_data["id"], name="Fighter", hp_max=50)
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        response = auth_client.put(f"/api/characters/{char_id}", json={"hp_current": 999})

        assert response.status_code == 200
        data = response.get_json()
        assert data["hp"] == "50/50"


class TestCharacterDelete:
    """Test character deletion."""

    def test_delete_character_success(self, auth_client, user_data):
        """Soft delete character."""
        with auth_client.application.app_context():
            char = Character(user_id=user_data["id"], name="Boromir")
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        response = auth_client.delete(f"/api/characters/{char_id}")
        assert response.status_code == 200

        with auth_client.application.app_context():
            deleted_char = Character.query.get(char_id)
            assert deleted_char is not None
            assert deleted_char.deleted_at is not None

    def test_delete_character_not_found(self, auth_client):
        """Handle delete of nonexistent character."""
        response = auth_client.delete("/api/characters/9999")
        assert response.status_code == 404

    def test_delete_character_unauthorized(self, app, user_data):
        """Reject delete by non-owner."""
        with app.app_context():
            char = Character(user_id=user_data["id"], name="Gimli")
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        other_client = _create_logged_in_other_client(app)
        response = other_client.delete(f"/api/characters/{char_id}")
        assert response.status_code == 403

