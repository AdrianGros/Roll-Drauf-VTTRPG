"""
M25 tests: Sheet rendering / content display for Roll-Drauf-Light characters.

Proof areas:
  - template contains all M25 element IDs and render functions
  - sheet payload exposes canonical progression + content blocks
  - sheet renders species trait / background perk / class features / training bonus
  - sheet renders progression ladder with locked/unlocked states
  - legacy characters still return HTTP 200 and safe payloads
  - avatar/token surfaces still work (no regression)
  - no BookScene ownership regression
  - M24 canonical creation + sheet roundtrip still intact
"""

from pathlib import Path

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles


REPO_ROOT = Path(__file__).resolve().parents[1]
SHEET_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "character-sheet.html"


def _tpl() -> str:
    return SHEET_TEMPLATE.read_text(encoding="utf-8")


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


@pytest.fixture
def user_data(app):
    with app.app_context():
        player_role = Role.query.filter_by(name="Player").first()
        user = User(
            username="m25_user",
            email="m25@example.com",
            role_id=player_role.id,
        )
        user.set_password("M25Pass123!")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "username": user.username, "password": "M25Pass123!"}


@pytest.fixture
def auth_client(client, user_data):
    resp = client.post(
        "/api/auth/login",
        json={"username": user_data["username"], "password": user_data["password"]},
    )
    assert resp.status_code == 200
    return client


# ---------------------------------------------------------------------------
# Template static analysis — element IDs and JS render functions
# ---------------------------------------------------------------------------

class TestTemplateHasM25Elements:
    def test_rdl_content_pane_present(self):
        assert 'id="rdlContentPane"' in _tpl()

    def test_rdl_progression_pane_present(self):
        assert 'id="rdlProgressionPane"' in _tpl()

    def test_rdl_features_pane_present(self):
        assert 'id="rdlFeaturesPane"' in _tpl()

    def test_rdl_profile_section_present(self):
        assert 'id="rdlProfileSection"' in _tpl()

    def test_rdl_progression_section_present(self):
        assert 'id="rdlProgressionSection"' in _tpl()

    def test_rdl_features_section_present(self):
        assert 'id="rdlFeaturesSection"' in _tpl()

    def test_render_roll_drauf_content_function_exists(self):
        assert 'function renderRollDraufContent(' in _tpl()

    def test_render_class_features_function_exists(self):
        assert 'function renderClassFeatures(' in _tpl()

    def test_render_progression_ladder_function_exists(self):
        assert 'function renderProgressionLadder(' in _tpl()

    def test_render_sheet_calls_rdl_functions(self):
        tpl = _tpl()
        assert 'renderRollDraufContent(sheet.character)' in tpl
        assert 'renderClassFeatures(sheet.character)' in tpl
        assert 'renderProgressionLadder(sheet.character)' in tpl

    def test_legacy_fallback_text_present(self):
        tpl = _tpl()
        assert 'Altcharakter' in tpl

    def test_rdl_css_classes_defined(self):
        tpl = _tpl()
        assert '.rdl-feature-card' in tpl
        assert '.rdl-prog-level' in tpl
        assert '.rdl-prog-level--complete' in tpl
        assert '.rdl-prog-level--locked' in tpl
        assert '.rdl-prog-level--current' in tpl
        assert '.rdl-tag' in tpl
        assert '.rdl-profile-grid' in tpl

    def test_identity_surface_still_present(self):
        """Identity pane must not have been removed."""
        assert 'id="sheetIdentityGrid"' in _tpl()
        assert 'renderIdentity(' in _tpl()

    def test_existing_faction_save_flow_still_present(self):
        """M23 save flow must remain intact."""
        assert "payload.faction = factionValue;" in _tpl()
        assert "payload.species = payload.race;" in _tpl()


# ---------------------------------------------------------------------------
# API-level: sheet payload now exposes M25 content blocks
# ---------------------------------------------------------------------------

class TestSheetPayloadExposesM24Blocks:
    def _create_canonical(self, auth_client, name, species, faction, cls, bg):
        return auth_client.post(
            "/api/characters",
            json={
                "name": name,
                "species": species,
                "faction": faction,
                "class": cls,
                "background": bg,
            },
        )

    def test_sheet_has_content_block(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Brok", "zwerg", "toldonar", "kaempfer", "soldat")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert sheet_resp.status_code == 200
        character = sheet_resp.get_json()["character"]
        assert character["content"] is not None

    def test_sheet_content_has_species_trait(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Elara", "elf", "prankeninseln", "magier", "gelehrte")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        assert character["content"]["species_trait"]["slug"] == "praezise"
        assert character["content"]["species_trait"]["name"]
        assert character["content"]["species_trait"]["description"]

    def test_sheet_content_has_background_perk(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Nix", "mensch", "freie-staedte", "schurke", "gassenkind")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        assert character["content"]["background_perk"]["slug"] == "stadtkundig"
        assert character["content"]["background_perk"]["description"]

    def test_sheet_content_has_class_features(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Vera", "mensch", "rote-rose", "kaempfer", "soldat")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        feature_slugs = [f["slug"] for f in character["content"]["class_features"]]
        assert "waffenvertrautheit" in feature_slugs
        assert "sturmangriff" in feature_slugs

    def test_sheet_content_has_training_bonus(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Scar", "turtonen", "die-schwarze-hand", "schurke", "bote")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        assert character["content"]["training_bonus"] == 2

    def test_sheet_content_has_faction_tags(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Kroll", "turtonen", "panzerbund-von-talkaruum", "kaempfer", "handwerker")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        tags = character["content"]["faction_tags"]
        assert "defensiv" in tags
        assert "solidarisch" in tags

    def test_sheet_has_progression_block(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Thorek", "zwerg", "ugotah", "kaempfer", "novize")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        assert character["progression"] is not None

    def test_sheet_progression_current_level(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Frey", "mensch", "rote-rose", "magier", "novize")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        assert character["progression"]["current_level"] == 1
        assert character["progression"]["level_cap"] == 5

    def test_sheet_progression_level1_complete(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Mira", "elf", "emperium-drohm", "schurke", "gelehrte")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        assert character["progression"]["levels"]["1"]["status"] == "complete"

    def test_sheet_progression_levels_2_to_5_locked(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Grim", "zwerg", "toldonar", "kaempfer", "handwerker")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        for lvl in ["2", "3", "4", "5"]:
            assert character["progression"]["levels"][lvl]["status"] == "locked"

    def test_sheet_progression_level3_has_signature_options(self, app, auth_client, user_data):
        r = self._create_canonical(auth_client, "Rook", "mensch", "freie-staedte", "kaempfer", "soldat")
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        lvl3 = character["progression"]["levels"]["3"]
        assert len(lvl3["choices_available"]) == 1
        choice = lvl3["choices_available"][0]
        assert choice["choice_type"] == "signature"
        assert len(choice["options"]) == 2


# ---------------------------------------------------------------------------
# Legacy character safety
# ---------------------------------------------------------------------------

class TestLegacyCharacterSheetSafety:
    def test_pre_m24_character_sheet_returns_200(self, app, auth_client, user_data):
        """Characters without content/progression block must still return 200."""
        with app.app_context():
            char = Character(
                user_id=user_data["id"],
                name="OldHero",
                race="Mensch",
                class_name="Kämpfer",
                background="Soldat",
                level=2,
                character_data={
                    "roll_drauf_light": {
                        "system_id": "roll_drauf_light",
                        "system_version": 1,
                        "species": {"slug": "mensch", "name": "Mensch", "id": "species_mensch"},
                        "faction": {"slug": "rote-rose", "name": "Rote Rose", "id": "faction_rote_rose"},
                        "class": {"slug": "kaempfer", "name": "Kämpfer", "id": "class_kaempfer"},
                        "background": {"slug": "soldat", "name": "Soldat", "id": "background_soldat"},
                        # no 'content' or 'progression' — pre-M24 archive
                    }
                },
            )
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert resp.status_code == 200
        character = resp.get_json()["character"]
        assert character["race"] == "Mensch"
        assert character["faction"] == "Rote Rose"
        # M24 blocks absent → None (graceful fallback)
        assert character["content"] is None
        assert character["progression"] is None

    def test_pure_legacy_character_sheet_returns_200(self, app, auth_client, user_data):
        """Characters with no roll_drauf_light at all must not crash the sheet."""
        with app.app_context():
            char = Character(
                user_id=user_data["id"],
                name="VeryOldHero",
                race="Mensch",
                class_name="Krieger",
                background="Söldner",
                level=5,
                character_data={},
            )
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert resp.status_code == 200
        character = resp.get_json()["character"]
        assert character["race"] == "Mensch"
        assert character["content"] is None
        assert character["progression"] is None
        assert character["training_bonus"] is None

    def test_legacy_character_identity_fields_still_correct(self, app, auth_client, user_data):
        """Legacy fields race/class/background must still be exposed correctly."""
        with app.app_context():
            char = Character(
                user_id=user_data["id"],
                name="Archive",
                race="Zwerg",
                class_name="Magier",
                background="Gelehrte",
                level=3,
                character_data={},
            )
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert resp.status_code == 200
        character = resp.get_json()["character"]
        assert character["race"] == "Zwerg"
        assert character["class"] == "Magier"
        assert character["background"] == "Gelehrte"


# ---------------------------------------------------------------------------
# Avatar / token identity surfaces not regressed
# ---------------------------------------------------------------------------

class TestIdentitySurfaceNotRegressed:
    def test_sheet_still_exposes_avatar_token_urls(self, app, auth_client, user_data):
        """M25 must not break identity url fields in the sheet payload."""
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "IdentChar",
                "species": "turtonen",
                "faction": "panzerbund-von-talkaruum",
                "class": "kaempfer",
                "background": "soldat",
            },
        )
        char_id = resp.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert sheet_resp.status_code == 200
        character = sheet_resp.get_json()["character"]
        assert "avatar_url" in character
        assert "token_url" in character


# ---------------------------------------------------------------------------
# Non-play / BookScene route not regressed
# ---------------------------------------------------------------------------

class TestNonPlayRouteNotRegressed:
    def test_character_sheet_html_route_returns_200(self, client):
        """The non-play character-sheet route must still serve HTML."""
        resp = client.get("/character-sheet")
        assert resp.status_code == 200
        assert b"character-sheet-route-book-scene" in resp.data

    def test_characters_html_route_still_returns_200(self, client):
        """Characters archive route must still work."""
        resp = client.get("/characters")
        assert resp.status_code == 200
        assert b"characters-route-book-scene" in resp.data


# ---------------------------------------------------------------------------
# M24 creator roundtrip: full create → sheet → verify content still intact
# ---------------------------------------------------------------------------

class TestM24CreatorRoundtripStillWorks:
    def test_kaempfer_create_then_sheet_shows_correct_content(self, app, auth_client, user_data):
        r = auth_client.post(
            "/api/characters",
            json={
                "name": "Thorek",
                "species": "zwerg",
                "faction": "toldonar",
                "class": "kaempfer",
                "background": "handwerker",
            },
        )
        assert r.status_code == 201
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert sheet_resp.status_code == 200
        character = sheet_resp.get_json()["character"]
        # Identity
        assert character["species"] == "Zwerg"
        assert character["faction"] == "Toldonar"
        assert character["class"] == "Kämpfer"
        assert character["background"] == "Handwerker"
        # M24 content
        assert character["content"]["species_trait"]["slug"] == "robust"
        assert character["content"]["background_perk"]["slug"] == "werkzeugkundig"
        feature_slugs = [f["slug"] for f in character["content"]["class_features"]]
        assert "waffenvertrautheit" in feature_slugs
        assert "sturmangriff" in feature_slugs
        # Progression
        assert character["progression"]["current_level"] == 1
        assert character["progression"]["levels"]["1"]["status"] == "complete"
        assert character["progression"]["levels"]["5"]["status"] == "locked"
        # Legacy bridge
        assert character["race"] == "Zwerg"
        assert character["system_id"] == "roll_drauf_light"

    def test_magier_sheet_shows_fokuspuls(self, app, auth_client, user_data):
        r = auth_client.post(
            "/api/characters",
            json={
                "name": "Elara",
                "species": "elf",
                "faction": "emperium-drohm",
                "class": "magier",
                "background": "gelehrte",
            },
        )
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        feature_slugs = [f["slug"] for f in character["content"]["class_features"]]
        assert "fokuspuls" in feature_slugs
        assert "schriftkundig" in feature_slugs

    def test_schurke_sheet_shows_hinterhaeltiger_stich(self, app, auth_client, user_data):
        r = auth_client.post(
            "/api/characters",
            json={
                "name": "Nix",
                "species": "mensch",
                "faction": "freie-staedte",
                "class": "schurke",
                "background": "gassenkind",
            },
        )
        char_id = r.get_json()["id"]
        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        character = sheet_resp.get_json()["character"]
        feature_slugs = [f["slug"] for f in character["content"]["class_features"]]
        assert "hinterhaeltiger_stich" in feature_slugs
        assert "akrobatik" in feature_slugs
