"""M23 tests: Roll Drauf Light character creator contract implementation."""

from pathlib import Path

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles


REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTERS_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "characters.html"
CHARACTER_SHEET_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "character-sheet.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_data(app):
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        user = User(
            username="creator_user",
            email="creator@example.com",
            role_id=player_role.id,
        )
        user.set_password("CreatorPass123!")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "username": user.username, "password": "CreatorPass123!"}


@pytest.fixture
def auth_client(client, user_data):
    response = client.post(
        "/api/auth/login",
        json={"username": user_data["username"], "password": user_data["password"]},
    )
    assert response.status_code == 200
    return client


def test_characters_template_exposes_roll_drauf_light_creator_contract():
    content = _read(CHARACTERS_TEMPLATE)

    assert 'id="charRace"' in content
    assert 'id="charFaction"' in content
    assert 'updateFactionOptions()' in content
    assert 'value="mensch">Mensch<' in content
    assert 'value="turtonen">Turtonen<' in content
    assert 'value="kaempfer">Kämpfer<' in content
    assert 'value="magier">Magier<' in content
    assert 'value="schurke">Schurke<' in content
    assert 'value="soldat">Soldat<' in content
    assert "attribute_mode: selectedArrayMode ? 'standard_array' : 'point_buy'" in content
    assert 'id="summaryFaction"' in content
    assert 'Barbarian' not in content
    assert 'Wizard' not in content


def test_character_sheet_surfaces_faction_without_reopening_sheet_architecture():
    content = _read(CHARACTER_SHEET_TEMPLATE)

    assert 'label for="charFaction">Fraktion</label>' in content
    assert "document.getElementById('charFaction').value = character.faction || '';" in content
    assert "payload.faction = factionValue;" in content


def test_create_character_accepts_canonical_roll_drauf_light_payload(app, auth_client, user_data):
    response = auth_client.post(
        "/api/characters",
        json={
            "name": "Talar",
            "species": "turtonen",
            "faction": "panzerbund-von-talkaruum",
            "class": "kaempfer",
            "background": "soldat",
            "attribute_mode": "standard_array",
            "str": 15,
            "dex": 12,
            "con": 14,
            "int": 8,
            "wis": 10,
            "cha": 13,
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Talar"
    assert data["race"] == "Turtonen"
    assert data["species"] == "Turtonen"
    assert data["faction"] == "Panzerbund von Talkaruum"
    assert data["class"] == "Kämpfer"
    assert data["background"] == "Soldat"
    assert data["level"] == 1
    assert data["system_id"] == "roll_drauf_light"

    with app.app_context():
        char = Character.query.filter_by(user_id=user_data["id"], name="Talar").first()
        assert char is not None
        roll_drauf_light = char.character_data["roll_drauf_light"]
        assert roll_drauf_light["species"]["slug"] == "turtonen"
        assert roll_drauf_light["faction"]["slug"] == "panzerbund-von-talkaruum"
        assert roll_drauf_light["class"]["slug"] == "kaempfer"
        assert roll_drauf_light["background"]["slug"] == "soldat"
        assert roll_drauf_light["attribute_mode"] == "standard_array"
        assert char.race == "Turtonen"
        assert char.class_name == "Kämpfer"
        assert char.background == "Soldat"


def test_create_character_rejects_faction_outside_selected_species(auth_client):
    response = auth_client.post(
        "/api/characters",
        json={
            "name": "Broken Hero",
            "species": "elf",
            "faction": "ugotah",
            "class": "magier",
            "background": "gelehrte",
        },
    )

    assert response.status_code == 400
    assert "Faction must match the selected species" in response.get_json()["error"]


def test_sheet_payload_keeps_canonical_fields_and_legacy_bridge(app, auth_client, user_data):
    with app.app_context():
        character = Character(
            user_id=user_data["id"],
            name="Mira",
            race="Mensch",
            class_name="Schurke",
            background="Gassenkind",
            level=1,
            character_data={
                "roll_drauf_light": {
                    "system_id": "roll_drauf_light",
                    "system_version": 1,
                    "species": {"slug": "mensch", "name": "Mensch"},
                    "faction": {"slug": "freie-staedte", "name": "Freie Städte"},
                    "class": {"slug": "schurke", "name": "Schurke"},
                    "background": {"slug": "gassenkind", "name": "Gassenkind"},
                }
            },
        )
        db.session.add(character)
        db.session.commit()
        char_id = character.id

    response = auth_client.get(f"/api/characters/{char_id}/sheet")

    assert response.status_code == 200
    payload = response.get_json()["character"]
    assert payload["race"] == "Mensch"
    assert payload["species"] == "Mensch"
    assert payload["faction"] == "Freie Städte"
    assert payload["class"] == "Schurke"
    assert payload["background"] == "Gassenkind"
    assert payload["system_id"] == "roll_drauf_light"
    assert payload["character_data"]["roll_drauf_light"]["species"]["slug"] == "mensch"
