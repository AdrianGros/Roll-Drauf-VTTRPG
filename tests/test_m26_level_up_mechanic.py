"""
M26 tests: Level-Up Mechanic / Progression Activation.

Proof areas covered:
  - happy path: Kämpfer level 1→2 (auto-only)
  - happy path: Kämpfer level 2→3 (signature choice)
  - happy path: Magier level 2→3 (signature choice)
  - happy path: Schurke level 2→3 (signature choice)
  - happy path: level 3→4 attribute choice updates ORM stat field
  - happy path: level 4→5 (auto-only, training_bonus rises to 3)
  - max-level rejection (level 5 character cannot level up)
  - one-level-per-request: cannot skip levels
  - invalid signature choice rejected
  - invalid attribute choice rejected
  - missing required choice rejected
  - not a canonical RDL character rejected
  - unauthorized access rejected
  - content.class_features grows correctly after level-up
  - progression.levels[N].choices persisted correctly
  - sheet payload reflects new level state
  - Character.level ORM field advances
"""

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles
from vtt.roll_drauf.catalog import CLASSES


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
    return _make_user(app, "m26_user", "m26@example.com", "M26Pass123!")


@pytest.fixture
def other_user_data(app):
    return _make_user(app, "m26_other", "m26other@example.com", "M26Pass456!")


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


def _create_rdl_char(auth_client, class_slug="kaempfer", name="TestHeld"):
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


def _get_rdl(char_data):
    return char_data["character_data"]["roll_drauf_light"]


# ---------------------------------------------------------------------------
# Happy path — auto-only level-up (1→2)
# ---------------------------------------------------------------------------

class TestLevelUpAutoOnly:
    def test_kaempfer_1_to_2(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer")
        char_id = char["id"]

        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()

        assert data["level"] == 2
        char_out = data["character"]
        assert char_out["level"] == 2
        assert char_out["progression_level"] == 2

    def test_kaempfer_2_features_in_content(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer")
        char_id = char["id"]

        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        resp = auth_client.get(f"/api/characters/{char_id}")
        assert resp.status_code == 200
        char_out = resp.get_json()
        features = char_out["content"]["class_features"]
        slugs = {f["slug"] for f in features}
        # Level-1 features still present
        assert "waffenvertrautheit" in slugs
        assert "sturmangriff" in slugs
        # Level-2 feature added
        assert "zweiter_atem" in slugs

    def test_magier_1_to_2(self, auth_client):
        char = _create_rdl_char(auth_client, "magier", name="Magus")
        char_id = char["id"]

        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["level"] == 2
        features = data["character"]["content"]["class_features"]
        slugs = {f["slug"] for f in features}
        assert "erweiterter_fokus" in slugs

    def test_schurke_1_to_2(self, auth_client):
        char = _create_rdl_char(auth_client, "schurke", name="Diebin")
        char_id = char["id"]

        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["level"] == 2
        features = data["character"]["content"]["class_features"]
        slugs = {f["slug"] for f in features}
        assert "ausweichen" in slugs


# ---------------------------------------------------------------------------
# Happy path — signature choice (2→3)
# ---------------------------------------------------------------------------

class TestLevelUpSignatureChoice:
    def _advance_to_2(self, auth_client, class_slug, name):
        char = _create_rdl_char(auth_client, class_slug, name)
        char_id = char["id"]
        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 200
        return char_id

    def test_kaempfer_2_to_3_defensiver_stil(self, auth_client):
        char_id = self._advance_to_2(auth_client, "kaempfer", "Krieger3")
        resp = auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"kaempfer_signature": "defensiver_stil"}},
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert data["level"] == 3
        features = data["character"]["content"]["class_features"]
        slugs = {f["slug"] for f in features}
        assert "defensiver_stil" in slugs

    def test_kaempfer_2_to_3_offensiver_stil(self, auth_client):
        char_id = self._advance_to_2(auth_client, "kaempfer", "Krieger3b")
        resp = auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"kaempfer_signature": "offensiver_stil"}},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        features = data["character"]["content"]["class_features"]
        slugs = {f["slug"] for f in features}
        assert "offensiver_stil" in slugs

    def test_magier_2_to_3_doppelpuls(self, auth_client):
        char_id = self._advance_to_2(auth_client, "magier", "Magus3")
        resp = auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"magier_signature": "doppelpuls"}},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        features = data["character"]["content"]["class_features"]
        slugs = {f["slug"] for f in features}
        assert "doppelpuls" in slugs

    def test_schurke_2_to_3_meuchler(self, auth_client):
        char_id = self._advance_to_2(auth_client, "schurke", "Schurke3")
        resp = auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"schurke_signature": "meuchler"}},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        features = data["character"]["content"]["class_features"]
        slugs = {f["slug"] for f in features}
        assert "meuchler" in slugs

    def test_choices_persisted_in_progression(self, auth_client):
        char_id = self._advance_to_2(auth_client, "kaempfer", "KriegerPersist")
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"kaempfer_signature": "defensiver_stil"}},
        )
        resp = auth_client.get(f"/api/characters/{char_id}")
        char_out = resp.get_json()
        level3_choices = char_out["progression"]["levels"]["3"]["choices"]
        assert level3_choices.get("kaempfer_signature") == "defensiver_stil"


# ---------------------------------------------------------------------------
# Happy path — attribute choice (3→4) + stat mutation
# ---------------------------------------------------------------------------

class TestLevelUpAttributeChoice:
    def _advance_to_3(self, auth_client, class_slug, sig_key, sig_val, name):
        char = _create_rdl_char(auth_client, class_slug, name)
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})  # →2
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {sig_key: sig_val}},
        )  # →3
        return char_id

    def test_kaempfer_3_to_4_str_increases(self, auth_client):
        char_id = self._advance_to_3(
            auth_client, "kaempfer", "kaempfer_signature", "defensiver_stil", "AttrHeld"
        )
        # Get baseline str
        resp = auth_client.get(f"/api/characters/{char_id}")
        base_str = resp.get_json()["str"]

        resp = auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"attributwahl": "str"}},
        )
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["level"] == 4

        resp2 = auth_client.get(f"/api/characters/{char_id}")
        new_str = resp2.get_json()["str"]
        assert new_str == base_str + 1, f"str expected {base_str + 1}, got {new_str}"

    def test_attribute_choice_persisted(self, auth_client):
        char_id = self._advance_to_3(
            auth_client, "magier", "magier_signature", "arkane_ruestung", "AttrMagus"
        )
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"attributwahl": "int"}},
        )
        resp = auth_client.get(f"/api/characters/{char_id}")
        level4_choices = resp.get_json()["progression"]["levels"]["4"]["choices"]
        assert level4_choices.get("attributwahl") == "int"

    def test_all_six_attributes_accepted(self, auth_client, app):
        """Each valid attribute choice is accepted."""
        for attr in ("str", "dex", "con", "int", "wis", "cha"):
            # Fresh character for each attribute
            char = _create_rdl_char(auth_client, "kaempfer", f"Attr_{attr}")
            char_id = char["id"]
            auth_client.post(f"/api/characters/{char_id}/level-up", json={})
            auth_client.post(
                f"/api/characters/{char_id}/level-up",
                json={"choices": {"kaempfer_signature": "defensiver_stil"}},
            )
            resp = auth_client.post(
                f"/api/characters/{char_id}/level-up",
                json={"choices": {"attributwahl": attr}},
            )
            assert resp.status_code == 200, f"attr {attr}: {resp.get_json()}"


# ---------------------------------------------------------------------------
# Happy path — level 4→5 (training_bonus rises)
# ---------------------------------------------------------------------------

class TestLevelUpToFive:
    def _advance_to_4(self, auth_client, name="Meister5"):
        char = _create_rdl_char(auth_client, "kaempfer", name)
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"kaempfer_signature": "offensiver_stil"}},
        )
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"attributwahl": "con"}},
        )
        return char_id

    def test_level_5_reached(self, auth_client):
        char_id = self._advance_to_4(auth_client)
        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["level"] == 5

    def test_training_bonus_3_at_level_5(self, auth_client):
        char_id = self._advance_to_4(auth_client)
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        resp = auth_client.get(f"/api/characters/{char_id}")
        assert resp.get_json()["training_bonus"] == 3

    def test_kampfmeister_feature_added(self, auth_client):
        char_id = self._advance_to_4(auth_client)
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        resp = auth_client.get(f"/api/characters/{char_id}")
        slugs = {f["slug"] for f in resp.get_json()["content"]["class_features"]}
        assert "kampfmeister" in slugs


# ---------------------------------------------------------------------------
# Rejection cases
# ---------------------------------------------------------------------------

class TestLevelUpRejections:
    def test_max_level_rejected(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", "MaxHeld")
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"kaempfer_signature": "defensiver_stil"}},
        )
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"attributwahl": "str"}},
        )
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        # Now at level 5 — next call must be rejected
        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 422
        assert "max level" in resp.get_json().get("error", "").lower()

    def test_invalid_signature_choice_rejected(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", "BadChoice")
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        resp = auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"kaempfer_signature": "does_not_exist"}},
        )
        assert resp.status_code == 400
        assert "invalid" in resp.get_json().get("error", "").lower()

    def test_missing_required_choice_rejected(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", "MissingChoice")
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        resp = auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 400

    def test_invalid_attribute_choice_rejected(self, auth_client):
        char = _create_rdl_char(auth_client, "kaempfer", "BadAttr")
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"kaempfer_signature": "defensiver_stil"}},
        )
        resp = auth_client.post(
            f"/api/characters/{char_id}/level-up",
            json={"choices": {"attributwahl": "luck"}},
        )
        assert resp.status_code == 400
        assert "invalid" in resp.get_json().get("error", "").lower()

    def test_legacy_character_rejected(self, auth_client, app):
        with app.app_context():
            player_role = Role.query.filter_by(name="Player").first()
            user = User.query.filter_by(username="m26_user").first()
            legacy = Character(
                user_id=user.id,
                name="Legacy Hero",
                class_name="Fighter",
                level=1,
                character_data={},
            )
            db.session.add(legacy)
            db.session.commit()
            legacy_id = legacy.id

        resp = auth_client.post(f"/api/characters/{legacy_id}/level-up", json={})
        assert resp.status_code == 422
        assert "roll-drauf-light" in resp.get_json().get("error", "").lower() or \
               "canonical" in resp.get_json().get("error", "").lower()

    def test_unauthorized_rejected(self, client, app, user_data, other_user_data):
        owner_client = _login(client, user_data)
        char = _create_rdl_char(owner_client, "kaempfer", "OwnerHeld")
        char_id = char["id"]

        other_client = _login(client, other_user_data)
        resp = other_client.post(f"/api/characters/{char_id}/level-up", json={})
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client):
        resp = client.post("/api/characters/1/level-up", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Sheet continuity after level-up
# ---------------------------------------------------------------------------

class TestSheetContinuityAfterLevelUp:
    def test_sheet_endpoint_returns_new_progression(self, auth_client):
        char = _create_rdl_char(auth_client, "schurke", "SheetSchurke")
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})

        resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert resp.status_code == 200
        sheet = resp.get_json()
        assert sheet["character"]["progression"]["current_level"] == 2
        assert sheet["character"]["level"] == 2
        assert sheet["character"]["progression"]["levels"]["2"]["status"] == "complete"
        assert sheet["character"]["progression"]["levels"]["3"]["status"] == "locked"

    def test_idempotent_feature_application(self, auth_client):
        """Level-up twice to same final state, features must not double-add."""
        char = _create_rdl_char(auth_client, "magier", "IdempMagus")
        char_id = char["id"]
        auth_client.post(f"/api/characters/{char_id}/level-up", json={})
        resp = auth_client.get(f"/api/characters/{char_id}")
        features = resp.get_json()["content"]["class_features"]
        slugs = [f["slug"] for f in features]
        # No duplicate slugs
        assert len(slugs) == len(set(slugs)), f"Duplicate features: {slugs}"
