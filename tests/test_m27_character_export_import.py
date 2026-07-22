"""
M27 tests: Character Export / Import Contract.

Proof areas covered:
  - export happy path: Level-1 canonical character
  - export happy path: Level-3+ character with progression choices
  - export rejects non-canonical character (422)
  - export rejects access to another user's character (403)
  - export payload shape: all required top-level keys present
  - export identity_refs: avatar_url / token_url are None when no identity set
  - import happy path: Level-1 round-trip creates a new character
  - import happy path: Level-3 with choices, stats preserved
  - import creates character with campaign_id=None (identity neutralized)
  - import rejects: wrong export_kind
  - import rejects: wrong system_id
  - import rejects: unsupported system_version
  - import rejects: missing name
  - import rejects: unknown species slug
  - import rejects: faction not valid for species
  - import rejects: unknown class slug
  - import rejects: unknown background slug
  - import rejects: progression.current_level missing levels in scaffold
  - regression: M26 level-up still works after M27 additions
"""

import copy

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


def _make_user(app, username, email, password):
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        user = User(username=username, email=email, role_id=player_role.id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "username": username, "password": password}


@pytest.fixture
def user_data(app):
    return _make_user(app, "m27_user", "m27@example.com", "M27Pass123!")


@pytest.fixture
def other_user_data(app):
    return _make_user(app, "m27_other", "m27other@example.com", "M27Pass456!")


def _login(client, user_data):
    resp = client.post(
        "/api/auth/login",
        json={"username": user_data["username"], "password": user_data["password"]},
    )
    assert resp.status_code == 200
    return client


@pytest.fixture
def auth_client(client, user_data):
    return _login(client, user_data)


@pytest.fixture
def other_auth_client(app, other_user_data):
    """Separate test client so two users can hold independent JWT cookies."""
    return _login(app.test_client(), other_user_data)


def _create_rdl_char(auth_client, class_slug="kaempfer", name="ExportHeld"):
    resp = auth_client.post(
        "/api/characters",
        json={
            "name": name,
            "species": "mensch",
            "faction": "rote-rose",
            "class": class_slug,
            "background": "soldat",
        },
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _advance_to(auth_client, char_id, target_level, *, choices_by_level=None):
    """Advance char_id up to target_level, providing choices_by_level dict if needed."""
    choices_by_level = choices_by_level or {}
    # Get current level
    resp = auth_client.get(f"/api/characters/{char_id}")
    current = resp.get_json()["level"]
    for lvl in range(current + 1, target_level + 1):
        payload = {"choices": choices_by_level.get(lvl, {})}
        r = auth_client.post(f"/api/characters/{char_id}/level-up", json=payload)
        assert r.status_code == 200, f"level-up to {lvl} failed: {r.get_json()}"


# ---------------------------------------------------------------------------
# Export — happy paths
# ---------------------------------------------------------------------------

class TestExportHappyPath:
    def test_export_level1_returns_200(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer")
        resp = auth_client.get(f"/api/characters/{char['id']}/export")
        assert resp.status_code == 200

    def test_export_payload_top_level_keys(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer")
        data = auth_client.get(f"/api/characters/{char['id']}/export").get_json()
        for key in ("export_kind", "system_id", "system_version", "export_version", "name", "stats", "roll_drauf_light", "identity_refs"):
            assert key in data, f"Missing key: {key}"

    def test_export_kind_and_system_id(self, auth_client):
        char = _create_rdl_char(auth_client, "magier", name="Magus")
        data = auth_client.get(f"/api/characters/{char['id']}/export").get_json()
        assert data["export_kind"] == "character"
        assert data["system_id"] == "roll_drauf_light"
        assert data["system_version"] == 1

    def test_export_stats_block(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer")
        data = auth_client.get(f"/api/characters/{char['id']}/export").get_json()
        stats = data["stats"]
        for key in ("str", "dex", "con", "int", "wis", "cha", "level", "xp", "ac", "hp_max", "mana_max"):
            assert key in stats, f"Missing stats key: {key}"
        assert stats["level"] == 1

    def test_export_identity_refs_none_when_no_identity(self, auth_client):
        char = _create_rdl_char(auth_client, "schurke", name="Diebin")
        data = auth_client.get(f"/api/characters/{char['id']}/export").get_json()
        assert data["identity_refs"]["avatar_url"] is None
        assert data["identity_refs"]["token_url"] is None

    def test_export_level3_preserves_progression(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", name="Krieger3")
        char_id = char["id"]
        _advance_to(auth_client, char_id, 3, choices_by_level={
            3: {"kaempfer_signature": "defensiver_stil"},
        })
        data = auth_client.get(f"/api/characters/{char_id}/export").get_json()
        rdl = data["roll_drauf_light"]
        assert rdl["progression"]["current_level"] == 3
        assert rdl["system_id"] == "roll_drauf_light"
        assert data["stats"]["level"] == 3


# ---------------------------------------------------------------------------
# Export — rejection paths
# ---------------------------------------------------------------------------

class TestExportRejections:
    def test_export_non_canonical_character_422(self, auth_client):
        # Create a plain (non-RDL) character directly via the API without species/faction/class
        # by inserting directly — but the API requires canonical data, so we POST a valid RDL
        # char then clear its character_data via DB.
        # Instead: create then patch character_data via PUT (sets character_data but not rdl)
        # The simplest way: POST without canonical fields — but the API currently builds RDL
        # so we insert manually.
        from vtt.extensions import db as _db
        from vtt.models import Character as Char
        char = _create_rdl_char(auth_client, "kaempfer", name="NonCanon")
        char_id = char["id"]
        # Overwrite character_data to strip RDL
        import flask
        import json
        with auth_client.application.app_context():
            c = _db.session.get(Char, char_id)
            c.character_data = {}
            _db.session.commit()
        resp = auth_client.get(f"/api/characters/{char_id}/export")
        assert resp.status_code == 422

    def test_export_other_users_character_403(self, auth_client, other_auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", name="OwnerChar")
        resp = other_auth_client.get(f"/api/characters/{char['id']}/export")
        assert resp.status_code == 403

    def test_export_nonexistent_character_404(self, auth_client):
        resp = auth_client.get("/api/characters/99999/export")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Import — happy paths
# ---------------------------------------------------------------------------

class TestImportHappyPath:
    def _export(self, auth_client, char_id):
        return auth_client.get(f"/api/characters/{char_id}/export").get_json()

    def test_import_level1_creates_new_character(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", name="ExportBase")
        payload = self._export(auth_client, char["id"])
        payload["name"] = "ImportedKaempfer"

        resp = auth_client.post("/api/characters/import", json=payload)
        assert resp.status_code == 201, resp.get_json()
        data = resp.get_json()
        assert data["character"]["name"] == "ImportedKaempfer"
        assert data["character"]["level"] == 1

    def test_import_creates_separate_character_id(self, auth_client):
        char = _create_rdl_char(auth_client, "magier", name="OriginalMagus")
        payload = self._export(auth_client, char["id"])

        resp = auth_client.post("/api/characters/import", json=payload)
        assert resp.status_code == 201
        imported_id = resp.get_json()["character"]["id"]
        assert imported_id != char["id"]

    def test_import_campaign_id_is_none(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", name="CampChar")
        payload = self._export(auth_client, char["id"])
        payload["campaign_id"] = 99  # should be ignored

        resp = auth_client.post("/api/characters/import", json=payload)
        assert resp.status_code == 201
        assert resp.get_json()["character"]["campaign_id"] is None

    def test_import_level3_preserves_stats_and_progression(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", name="Krieger")
        char_id = char["id"]
        _advance_to(auth_client, char_id, 3, choices_by_level={
            3: {"kaempfer_signature": "defensiver_stil"},
        })
        payload = self._export(auth_client, char_id)

        resp = auth_client.post("/api/characters/import", json=payload)
        assert resp.status_code == 201
        imp = resp.get_json()["character"]
        assert imp["level"] == 3
        rdl = imp["progression"]
        assert rdl["current_level"] == 3

    def test_import_response_contains_message_and_character(self, auth_client):
        char = _create_rdl_char(auth_client, "schurke", name="Diebin")
        payload = self._export(auth_client, char["id"])

        resp = auth_client.post("/api/characters/import", json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "message" in data
        assert "character" in data


# ---------------------------------------------------------------------------
# Import — rejection paths
# ---------------------------------------------------------------------------

class TestImportRejections:
    def _base_payload(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", name="BaseForImport")
        return auth_client.get(f"/api/characters/{char['id']}/export").get_json()

    def test_reject_wrong_export_kind(self, auth_client):
        p = self._base_payload(auth_client)
        p["export_kind"] = "campaign"
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 400

    def test_reject_wrong_system_id(self, auth_client):
        p = self._base_payload(auth_client)
        p["system_id"] = "dnd5e"
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 400

    def test_reject_unsupported_system_version(self, auth_client):
        p = self._base_payload(auth_client)
        p["system_version"] = 99
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 422

    def test_reject_missing_name(self, auth_client):
        p = self._base_payload(auth_client)
        del p["name"]
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 400

    def test_reject_empty_name(self, auth_client):
        p = self._base_payload(auth_client)
        p["name"] = "   "
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 400

    def test_reject_unknown_species(self, auth_client):
        p = self._base_payload(auth_client)
        p["roll_drauf_light"]["species"]["slug"] = "drakonid"
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 422

    def test_reject_faction_not_valid_for_species(self, auth_client):
        p = self._base_payload(auth_client)
        # mensch has rote-rose and freie-staedte, not toldonar (zwerg faction)
        p["roll_drauf_light"]["faction"]["slug"] = "toldonar"
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 422

    def test_reject_unknown_class(self, auth_client):
        p = self._base_payload(auth_client)
        p["roll_drauf_light"]["class"]["slug"] = "paladin"
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 422

    def test_reject_unknown_background(self, auth_client):
        p = self._base_payload(auth_client)
        p["roll_drauf_light"]["background"]["slug"] = "adliger"
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 422

    def test_reject_progression_missing_level_scaffold(self, auth_client):
        p = self._base_payload(auth_client)
        # Manually claim current_level=3 but only provide level 1 in scaffold
        rdl = p["roll_drauf_light"]
        rdl["progression"]["current_level"] = 3
        # levels only has "1" — missing "2" and "3"
        levels = rdl["progression"]["levels"]
        for k in list(levels.keys()):
            if k != "1":
                del levels[k]
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 422

    def test_reject_missing_rdl_block(self, auth_client):
        p = self._base_payload(auth_client)
        del p["roll_drauf_light"]
        resp = auth_client.post("/api/characters/import", json=p)
        assert resp.status_code == 400

    def test_reject_non_json_body(self, auth_client):
        resp = auth_client.post(
            "/api/characters/import",
            data="not json",
            content_type="text/plain",
        )
        # Flask returns 415 Unsupported Media Type for non-JSON content on a JSON endpoint
        assert resp.status_code in (400, 415)


# ---------------------------------------------------------------------------
# Regression: M26 level-up still works
# ---------------------------------------------------------------------------

class TestM27Regression:
    def test_level_up_still_works_after_m27(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", name="RegressionHeld")
        char_id = char["id"]
        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 200
        assert resp.get_json()["level"] == 2

    def test_export_then_import_then_level_up(self, auth_client):
        """Imported character must also be able to level up."""
        char = _create_rdl_char(auth_client, "magier", name="Magus")
        payload = auth_client.get(f"/api/characters/{char['id']}/export").get_json()
        imp_resp = auth_client.post("/api/characters/import", json=payload)
        assert imp_resp.status_code == 201
        imp_id = imp_resp.get_json()["character"]["id"]

        lvlup = auth_client.post(f"/api/characters/{imp_id}/level-up", json={})
        assert lvlup.status_code == 200
        assert lvlup.get_json()["level"] == 2
