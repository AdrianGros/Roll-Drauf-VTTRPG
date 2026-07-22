"""M17.3 tests: character identity productization."""

from base64 import b64decode
from io import BytesIO
from pathlib import Path

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles


PNG_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlH0uoAAAAASUVORK5CYII="
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CHARACTERS_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "characters.html"
CHARACTER_SHEET_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "character-sheet.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture
def app(tmp_path):
    app = create_app("testing")
    app.config["LOCAL_STORAGE_PATH"] = str(tmp_path / "identity-storage")

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
            username="identity_user",
            email="identity@example.com",
            role_id=player_role.id,
        )
        user.set_password("IdentityPass123!")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "username": user.username, "password": "IdentityPass123!"}


@pytest.fixture
def auth_client(client, user_data):
    response = client.post(
        "/api/auth/login",
        json={"username": user_data["username"], "password": user_data["password"]},
    )
    assert response.status_code == 200
    return client


def _create_character(app, user_id, name="Identity Hero"):
    with app.app_context():
        character = Character(
            user_id=user_id,
            name=name,
            race="Elf",
            class_name="Wizard",
        )
        db.session.add(character)
        db.session.commit()
        return character.id


def _upload_identity(client, char_id, identity_kind, filename):
    return client.post(
        f"/api/characters/{char_id}/identity/{identity_kind}",
        data={"file": (BytesIO(PNG_BYTES), filename)},
        content_type="multipart/form-data",
    )


def test_identity_uploads_are_user_and_character_scoped(app, auth_client, user_data):
    char_id = _create_character(app, user_data["id"], name="Scoped Hero")

    avatar_response = _upload_identity(auth_client, char_id, "avatar", "portrait.png")
    token_response = _upload_identity(auth_client, char_id, "token", "token.png")

    assert avatar_response.status_code == 200
    assert token_response.status_code == 200

    with app.app_context():
        char = db.session.get(Character, char_id)
        assert char.avatar_url == f"/api/characters/{char_id}/identity/avatar"
        assert char.token_url == f"/api/characters/{char_id}/identity/token"
        assert char.avatar_storage_key.startswith(
            f"uploads/users/{user_data['id']}/characters/{char_id}/avatar/originals/"
        )
        assert char.token_storage_key.startswith(
            f"uploads/users/{user_data['id']}/characters/{char_id}/token/originals/"
        )

        avatar_path = Path(app.config["LOCAL_STORAGE_PATH"]) / char.avatar_storage_key
        token_path = Path(app.config["LOCAL_STORAGE_PATH"]) / char.token_storage_key
        assert avatar_path.exists()
        assert token_path.exists()


def test_identity_uploads_surface_in_archive_and_sheet_payloads(app, auth_client, user_data):
    char_id = _create_character(app, user_data["id"], name="Visible Hero")
    _upload_identity(auth_client, char_id, "avatar", "visible-avatar.png")
    _upload_identity(auth_client, char_id, "token", "visible-token.png")

    list_response = auth_client.get("/api/characters/mine")
    sheet_response = auth_client.get(f"/api/characters/{char_id}/sheet")

    assert list_response.status_code == 200
    assert sheet_response.status_code == 200

    listed = list_response.get_json()[0]
    sheet_payload = sheet_response.get_json()["character"]
    assert listed["avatar_url"] == f"/api/characters/{char_id}/identity/avatar"
    assert listed["token_url"] == f"/api/characters/{char_id}/identity/token"
    assert sheet_payload["avatar_url"] == f"/api/characters/{char_id}/identity/avatar"
    assert sheet_payload["token_url"] == f"/api/characters/{char_id}/identity/token"


def test_identity_files_can_be_served_replaced_and_removed(app, auth_client, user_data):
    char_id = _create_character(app, user_data["id"], name="Mutable Hero")

    first_upload = _upload_identity(auth_client, char_id, "avatar", "avatar-a.png")
    assert first_upload.status_code == 200

    first_get = auth_client.get(f"/api/characters/{char_id}/identity/avatar")
    assert first_get.status_code == 200
    assert first_get.mimetype == "image/png"

    second_upload = _upload_identity(auth_client, char_id, "avatar", "avatar-b.png")
    assert second_upload.status_code == 200

    delete_response = auth_client.delete(f"/api/characters/{char_id}/identity/avatar")
    assert delete_response.status_code == 200

    missing_response = auth_client.get(f"/api/characters/{char_id}/identity/avatar")
    assert missing_response.status_code == 404


def test_character_templates_expose_real_identity_surfaces():
    characters = _read(CHARACTERS_TEMPLATE)
    sheet = _read(CHARACTER_SHEET_TEMPLATE)

    assert 'id="identityFilePicker"' in characters
    assert "openCharacterIdentityPicker" in characters
    assert "Identity Surface" in characters
    assert "Avatar First" in characters
    assert "Token Ready" in characters

    assert 'id="sheetIdentityFilePicker"' in sheet
    assert 'id="sheetIdentityGrid"' in sheet
    assert "function openIdentityPicker(identityKind)" in sheet
    assert "function removeIdentity(identityKind)" in sheet
