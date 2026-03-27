"""M6 tests: character sheet resource endpoints."""

from datetime import datetime

import pytest

from vtt_app import create_app
from vtt_app.extensions import db
from vtt_app.models import Campaign, CampaignMember, Character, Equipment, InventoryItem, Role, Spell, User


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
def owner_user(app):
    user = User(username="sheet_owner", email="sheet_owner@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def member_user(app):
    user = User(username="sheet_member", email="sheet_member@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def outsider_user(app):
    user = User(username="sheet_outsider", email="sheet_out@test.com", role_id=1)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def owner_client(app, owner_user):
    client = app.test_client()
    _login(client, owner_user.username)
    return client


@pytest.fixture
def member_client(app, member_user):
    client = app.test_client()
    _login(client, member_user.username)
    return client


@pytest.fixture
def outsider_client(app, outsider_user):
    client = app.test_client()
    _login(client, outsider_user.username)
    return client


def _create_campaign_with_member(owner_user, member_user):
    campaign = Campaign(
        name="Sheet Campaign",
        description="sheet access campaign",
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
    db.session.add(
        CampaignMember(
            campaign_id=campaign.id,
            user_id=member_user.id,
            campaign_role="Player",
            status="active",
            joined_at=datetime.utcnow(),
            invited_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            invited_by=owner_user.id,
        )
    )
    db.session.commit()
    return campaign


class TestCharacterSheetRead:
    def test_sheet_endpoint_owner_and_member_access(self, owner_user, member_user, owner_client, member_client, outsider_client):
        campaign = _create_campaign_with_member(owner_user, member_user)
        character = Character(
            user_id=owner_user.id,
            campaign_id=campaign.id,
            name="Aelar",
            class_name="Wizard",
            race="Elf",
        )
        db.session.add(character)
        db.session.flush()

        db.session.add(Spell(character_id=character.id, name="Magic Missile", level=1))
        db.session.add(Equipment(character_id=character.id, name="Staff", equipment_type="Weapon"))
        db.session.add(InventoryItem(character_id=character.id, name="Potion", quantity=2, item_type="Consumable"))
        db.session.commit()

        owner_response = owner_client.get(f"/api/characters/{character.id}/sheet")
        assert owner_response.status_code == 200
        owner_payload = owner_response.get_json()
        assert owner_payload["character"]["name"] == "Aelar"
        assert len(owner_payload["spells"]) == 1
        assert len(owner_payload["equipment"]) == 1
        assert len(owner_payload["inventory"]) == 1

        member_response = member_client.get(f"/api/characters/{character.id}/sheet")
        assert member_response.status_code == 200

        outsider_response = outsider_client.get(f"/api/characters/{character.id}/sheet")
        assert outsider_response.status_code == 403


class TestCharacterSheetResources:
    def test_spell_crud_owner_only(self, owner_user, owner_client, member_client):
        character = Character(user_id=owner_user.id, name="Caster", class_name="Wizard", race="Human")
        db.session.add(character)
        db.session.commit()

        create_response = owner_client.post(
            f"/api/characters/{character.id}/spells",
            json={"name": "Shield", "level": 1, "school": "Abjuration"},
        )
        assert create_response.status_code == 201
        spell_id = create_response.get_json()["id"]

        list_response = owner_client.get(f"/api/characters/{character.id}/spells")
        assert list_response.status_code == 200
        assert len(list_response.get_json()["spells"]) == 1

        update_response = owner_client.put(
            f"/api/characters/{character.id}/spells/{spell_id}",
            json={"level": 2, "damage_type": "Force"},
        )
        assert update_response.status_code == 200
        assert update_response.get_json()["level"] == 2

        forbidden = member_client.put(
            f"/api/characters/{character.id}/spells/{spell_id}",
            json={"level": 3},
        )
        assert forbidden.status_code == 403

        delete_response = owner_client.delete(f"/api/characters/{character.id}/spells/{spell_id}")
        assert delete_response.status_code == 200

    def test_equipment_and_inventory_crud(self, owner_user, owner_client):
        character = Character(user_id=owner_user.id, name="Tank", class_name="Fighter", race="Dwarf")
        db.session.add(character)
        db.session.commit()

        equipment_create = owner_client.post(
            f"/api/characters/{character.id}/equipment",
            json={"name": "Plate Armor", "type": "Armor", "ac_bonus": 8},
        )
        assert equipment_create.status_code == 201
        equipment_id = equipment_create.get_json()["id"]

        equipment_update = owner_client.put(
            f"/api/characters/{character.id}/equipment/{equipment_id}",
            json={"is_equipped": True},
        )
        assert equipment_update.status_code == 200
        assert equipment_update.get_json()["is_equipped"] is True

        inventory_create = owner_client.post(
            f"/api/characters/{character.id}/inventory",
            json={"name": "Healing Potion", "type": "Consumable", "quantity": 3},
        )
        assert inventory_create.status_code == 201
        inventory_id = inventory_create.get_json()["id"]

        inventory_update = owner_client.put(
            f"/api/characters/{character.id}/inventory/{inventory_id}",
            json={"quantity": 5},
        )
        assert inventory_update.status_code == 200
        assert inventory_update.get_json()["quantity"] == 5

        inventory_delete = owner_client.delete(f"/api/characters/{character.id}/inventory/{inventory_id}")
        assert inventory_delete.status_code == 200
