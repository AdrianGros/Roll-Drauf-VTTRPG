"""
M24 tests: Roll Drauf Light content packages and Level 1–5 progression scaffold.

Proof areas covered:
  - controlled content catalogs exist (species, factions, classes, backgrounds)
  - level-1 package is applied on character creation
  - level-2–5 scaffold exists and is locked
  - invalid species/faction combos remain rejected
  - canonical serialization exposes progression + content data
  - archive (serialize) still renders sensible identity/class/species/faction summaries
  - legacy bridge (race/class_name/background) remains intact
  - sheet payload includes full progression + content blocks
"""

import pytest

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, Role, User
from vtt.models.role import init_default_roles
from vtt.roll_drauf.catalog import SPECIES, CLASSES, BACKGROUNDS, LEVEL_ONE_BASELINES
from vtt.roll_drauf.progression import build_progression_scaffold, apply_level1_package


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
            username="m24_user",
            email="m24@example.com",
            role_id=player_role.id,
        )
        user.set_password("M24Pass123!")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "username": user.username, "password": "M24Pass123!"}


@pytest.fixture
def auth_client(client, user_data):
    resp = client.post(
        "/api/auth/login",
        json={"username": user_data["username"], "password": user_data["password"]},
    )
    assert resp.status_code == 200
    return client


# ---------------------------------------------------------------------------
# Catalog structure tests
# ---------------------------------------------------------------------------

class TestCatalogsExist:
    def test_all_four_species_present(self):
        assert set(SPECIES.keys()) == {'mensch', 'zwerg', 'elf', 'turtonen'}

    def test_each_species_has_required_fields(self):
        for slug, entry in SPECIES.items():
            assert entry['id'], f"{slug}: missing id"
            assert entry['slug'] == slug
            assert entry['name']
            assert 'trait' in entry, f"{slug}: missing trait"
            assert entry['trait']['slug']
            assert entry['trait']['name']
            assert entry['trait']['description']
            assert 'factions' in entry, f"{slug}: missing factions"

    def test_each_species_has_exactly_two_factions(self):
        for slug, entry in SPECIES.items():
            assert len(entry['factions']) == 2, f"{slug}: expected 2 factions"

    def test_each_faction_has_tags(self):
        for sp_slug, sp in SPECIES.items():
            for f_slug, f in sp['factions'].items():
                assert 'tags' in f, f"{sp_slug}/{f_slug}: missing tags"
                assert len(f['tags']) >= 1

    def test_all_three_classes_present(self):
        assert set(CLASSES.keys()) == {'kaempfer', 'magier', 'schurke'}

    def test_each_class_has_progression_levels_1_to_5(self):
        for slug, entry in CLASSES.items():
            assert 'progression' in entry, f"{slug}: missing progression"
            for lvl in range(1, 6):
                assert lvl in entry['progression'], f"{slug}: missing level {lvl}"
                level_data = entry['progression'][lvl]
                assert 'auto_features' in level_data
                assert 'choices_available' in level_data

    def test_level_1_has_auto_features_for_all_classes(self):
        for slug, entry in CLASSES.items():
            feats = entry['progression'][1]['auto_features']
            assert len(feats) >= 1, f"{slug}: no level-1 auto_features"
            for f in feats:
                assert f['slug']
                assert f['name']
                assert f['description']

    def test_level_3_has_signature_choice_for_all_classes(self):
        for slug, entry in CLASSES.items():
            choices = entry['progression'][3]['choices_available']
            assert len(choices) == 1, f"{slug}: level 3 must have exactly 1 signature choice"
            choice = choices[0]
            assert choice['choice_type'] == 'signature'
            assert len(choice['options']) == 2

    def test_level_4_has_attribute_choice_for_all_classes(self):
        for slug, entry in CLASSES.items():
            choices = entry['progression'][4]['choices_available']
            assert len(choices) == 1, f"{slug}: level 4 must have 1 attribute choice"
            assert choices[0]['choice_type'] == 'attribute'

    def test_level_5_has_milestone_feature_for_all_classes(self):
        for slug, entry in CLASSES.items():
            feats = entry['progression'][5]['auto_features']
            assert len(feats) >= 1, f"{slug}: no level-5 milestone feature"

    def test_all_six_backgrounds_present(self):
        expected = {'soldat', 'gelehrte', 'gassenkind', 'handwerker', 'bote', 'novize'}
        assert set(BACKGROUNDS.keys()) == expected

    def test_each_background_has_perk(self):
        for slug, entry in BACKGROUNDS.items():
            assert 'perk' in entry, f"{slug}: missing perk"
            assert entry['perk']['slug']
            assert entry['perk']['name']
            assert entry['perk']['description']

    def test_level_one_baselines_match_classes(self):
        assert set(LEVEL_ONE_BASELINES.keys()) == set(CLASSES.keys())
        for slug, baseline in LEVEL_ONE_BASELINES.items():
            assert 'hp_max' in baseline
            assert 'ac' in baseline
            assert 'mana_max' in baseline


# ---------------------------------------------------------------------------
# Progression scaffold unit tests
# ---------------------------------------------------------------------------

class TestProgressionScaffold:
    def test_scaffold_has_five_levels(self):
        entry = CLASSES['kaempfer']
        scaffold = build_progression_scaffold(entry, current_level=1)
        assert scaffold['current_level'] == 1
        assert scaffold['level_cap'] == 5
        assert len(scaffold['levels']) == 5

    def test_level_1_is_complete(self):
        scaffold = build_progression_scaffold(CLASSES['kaempfer'], current_level=1)
        assert scaffold['levels']['1']['status'] == 'complete'

    def test_levels_2_to_5_are_locked_at_creation(self):
        scaffold = build_progression_scaffold(CLASSES['kaempfer'], current_level=1)
        for lvl in ['2', '3', '4', '5']:
            assert scaffold['levels'][lvl]['status'] == 'locked', f"level {lvl} should be locked"

    def test_level_1_features_present_in_scaffold(self):
        scaffold = build_progression_scaffold(CLASSES['magier'], current_level=1)
        feats = scaffold['levels']['1']['auto_features']
        slugs = [f['slug'] for f in feats]
        assert 'fokuspuls' in slugs
        assert 'schriftkundig' in slugs

    def test_level_3_scaffold_has_choices_available(self):
        scaffold = build_progression_scaffold(CLASSES['schurke'], current_level=1)
        level3 = scaffold['levels']['3']
        assert len(level3['choices_available']) == 1
        assert level3['choices_available'][0]['choice_type'] == 'signature'

    def test_level_choices_are_empty_dict(self):
        scaffold = build_progression_scaffold(CLASSES['kaempfer'], current_level=1)
        for lvl_data in scaffold['levels'].values():
            assert lvl_data['choices'] == {}

    def test_apply_level1_package_adds_content_and_progression(self):
        rdl = {'system_id': 'roll_drauf_light'}
        apply_level1_package(
            rdl,
            SPECIES['mensch'],
            SPECIES['mensch']['factions']['rote-rose'],
            CLASSES['kaempfer'],
            BACKGROUNDS['soldat'],
        )
        assert 'content' in rdl
        assert 'progression' in rdl
        content = rdl['content']
        assert content['species_trait']['slug'] == 'vielseitig'
        assert 'militärisch' in content['faction_tags']
        assert content['background_perk']['slug'] == 'kampferfahren'
        assert any(f['slug'] == 'waffenvertrautheit' for f in content['class_features'])
        assert content['training_bonus'] == 2

    def test_apply_level1_package_does_not_mutate_catalog(self):
        rdl1 = {'system_id': 'roll_drauf_light'}
        rdl2 = {'system_id': 'roll_drauf_light'}
        apply_level1_package(
            rdl1,
            SPECIES['elf'],
            SPECIES['elf']['factions']['prankeninseln'],
            CLASSES['magier'],
            BACKGROUNDS['gelehrte'],
        )
        apply_level1_package(
            rdl2,
            SPECIES['zwerg'],
            SPECIES['zwerg']['factions']['toldonar'],
            CLASSES['schurke'],
            BACKGROUNDS['bote'],
        )
        # Both must differ without corrupting each other
        assert rdl1['content']['species_trait']['slug'] == 'praezise'
        assert rdl2['content']['species_trait']['slug'] == 'robust'


# ---------------------------------------------------------------------------
# API-level tests (via HTTP client)
# ---------------------------------------------------------------------------

class TestCreatorOutputsLevel1Package:
    def test_create_kaempfer_carries_level1_features(self, app, auth_client, user_data):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Brok",
                "species": "zwerg",
                "faction": "toldonar",
                "class": "kaempfer",
                "background": "soldat",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['class'] == 'Kämpfer'
        assert data['training_bonus'] == 2
        assert data['progression_level'] == 1
        assert data['progression_level_cap'] == 5

        with app.app_context():
            char = Character.query.filter_by(user_id=user_data['id'], name='Brok').first()
            rdl = char.character_data['roll_drauf_light']
            assert 'content' in rdl
            assert 'progression' in rdl
            content = rdl['content']
            assert content['species_trait']['slug'] == 'robust'
            assert 'bergvolk' in content['faction_tags']
            assert content['background_perk']['slug'] == 'kampferfahren'
            feature_slugs = [f['slug'] for f in content['class_features']]
            assert 'waffenvertrautheit' in feature_slugs
            assert 'sturmangriff' in feature_slugs
            assert content['training_bonus'] == 2

    def test_create_magier_carries_fokuspuls(self, app, auth_client, user_data):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Elara",
                "species": "elf",
                "faction": "emperium-drohm",
                "class": "magier",
                "background": "gelehrte",
            },
        )
        assert resp.status_code == 201
        with app.app_context():
            char = Character.query.filter_by(user_id=user_data['id'], name='Elara').first()
            rdl = char.character_data['roll_drauf_light']
            content = rdl['content']
            assert content['species_trait']['slug'] == 'praezise'
            feature_slugs = [f['slug'] for f in content['class_features']]
            assert 'fokuspuls' in feature_slugs
            assert 'schriftkundig' in feature_slugs

    def test_create_schurke_carries_hinterhaeltiger_stich(self, app, auth_client, user_data):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Nix",
                "species": "mensch",
                "faction": "freie-staedte",
                "class": "schurke",
                "background": "gassenkind",
            },
        )
        assert resp.status_code == 201
        with app.app_context():
            char = Character.query.filter_by(user_id=user_data['id'], name='Nix').first()
            rdl = char.character_data['roll_drauf_light']
            content = rdl['content']
            assert content['species_trait']['slug'] == 'vielseitig'
            assert 'händlerisch' in content['faction_tags']
            assert content['background_perk']['slug'] == 'stadtkundig'
            feature_slugs = [f['slug'] for f in content['class_features']]
            assert 'hinterhaeltiger_stich' in feature_slugs
            assert 'akrobatik' in feature_slugs

    def test_turtonen_trait_present(self, app, auth_client, user_data):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Kroll",
                "species": "turtonen",
                "faction": "panzerbund-von-talkaruum",
                "class": "kaempfer",
                "background": "soldat",
            },
        )
        assert resp.status_code == 201
        with app.app_context():
            char = Character.query.filter_by(user_id=user_data['id'], name='Kroll').first()
            rdl = char.character_data['roll_drauf_light']
            assert rdl['content']['species_trait']['slug'] == 'widerstandsfaehig'


class TestProgressionScaffoldViaAPI:
    def test_progression_scaffold_has_all_five_levels(self, app, auth_client, user_data):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Thorek",
                "species": "zwerg",
                "faction": "ugotah",
                "class": "kaempfer",
                "background": "handwerker",
            },
        )
        assert resp.status_code == 201
        with app.app_context():
            char = Character.query.filter_by(user_id=user_data['id'], name='Thorek').first()
            prog = char.character_data['roll_drauf_light']['progression']
            assert prog['current_level'] == 1
            assert prog['level_cap'] == 5
            assert set(prog['levels'].keys()) == {'1', '2', '3', '4', '5'}

    def test_levels_2_to_5_locked_after_creation(self, app, auth_client, user_data):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Vera",
                "species": "mensch",
                "faction": "rote-rose",
                "class": "magier",
                "background": "novize",
            },
        )
        assert resp.status_code == 201
        with app.app_context():
            char = Character.query.filter_by(user_id=user_data['id'], name='Vera').first()
            prog = char.character_data['roll_drauf_light']['progression']
            assert prog['levels']['1']['status'] == 'complete'
            for lvl in ['2', '3', '4', '5']:
                assert prog['levels'][lvl]['status'] == 'locked'

    def test_level3_scaffold_has_signature_options(self, app, auth_client, user_data):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Scar",
                "species": "turtonen",
                "faction": "die-schwarze-hand",
                "class": "schurke",
                "background": "gassenkind",
            },
        )
        assert resp.status_code == 201
        with app.app_context():
            char = Character.query.filter_by(user_id=user_data['id'], name='Scar').first()
            prog = char.character_data['roll_drauf_light']['progression']
            lvl3 = prog['levels']['3']
            assert len(lvl3['choices_available']) == 1
            choice = lvl3['choices_available'][0]
            assert choice['choice_type'] == 'signature'
            option_slugs = [o['slug'] for o in choice['options']]
            assert 'meuchler' in option_slugs
            assert 'fluchtexperte' in option_slugs


class TestInvalidCombosStillRejected:
    def test_elf_with_zwerg_faction_rejected(self, auth_client):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "BadCombo",
                "species": "elf",
                "faction": "ugotah",
                "class": "magier",
                "background": "gelehrte",
            },
        )
        assert resp.status_code == 400
        assert 'Faction must match the selected species' in resp.get_json()['error']

    def test_mensch_with_turtonen_faction_rejected(self, auth_client):
        resp = auth_client.post(
            "/api/characters",
            json={
                "name": "BadCombo2",
                "species": "mensch",
                "faction": "panzerbund-von-talkaruum",
                "class": "kaempfer",
                "background": "soldat",
            },
        )
        assert resp.status_code == 400


class TestSerializationExposeProgression:
    def test_list_endpoint_exposes_training_bonus_and_progression_level(
        self, app, auth_client, user_data
    ):
        auth_client.post(
            "/api/characters",
            json={
                "name": "Frey",
                "species": "mensch",
                "faction": "rote-rose",
                "class": "kaempfer",
                "background": "soldat",
            },
        )
        resp = auth_client.get("/api/characters/mine")
        assert resp.status_code == 200
        chars = resp.get_json()
        frey = next((c for c in chars if c['name'] == 'Frey'), None)
        assert frey is not None
        assert frey['training_bonus'] == 2
        assert frey['progression_level'] == 1
        assert frey['progression_level_cap'] == 5

    def test_sheet_endpoint_exposes_full_progression_and_content(
        self, app, auth_client, user_data
    ):
        create_resp = auth_client.post(
            "/api/characters",
            json={
                "name": "Mira",
                "species": "elf",
                "faction": "prankeninseln",
                "class": "schurke",
                "background": "bote",
            },
        )
        char_id = create_resp.get_json()['id']

        sheet_resp = auth_client.get(f"/api/characters/{char_id}/sheet")
        assert sheet_resp.status_code == 200
        character = sheet_resp.get_json()['character']

        assert character['progression'] is not None
        assert character['content'] is not None
        assert character['progression']['current_level'] == 1
        assert character['content']['species_trait']['slug'] == 'praezise'
        assert character['content']['background_perk']['slug'] == 'weitgereist'

    def test_archive_still_renders_identity_class_species_faction(
        self, app, auth_client, user_data
    ):
        """Legacy archive fields must remain stable."""
        create_resp = auth_client.post(
            "/api/characters",
            json={
                "name": "ArchiveChar",
                "species": "zwerg",
                "faction": "toldonar",
                "class": "kaempfer",
                "background": "handwerker",
            },
        )
        char_id = create_resp.get_json()['id']
        resp = auth_client.get(f"/api/characters/{char_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['race'] == 'Zwerg'
        assert data['species'] == 'Zwerg'
        assert data['faction'] == 'Toldonar'
        assert data['class'] == 'Kämpfer'
        assert data['background'] == 'Handwerker'
        assert data['system_id'] == 'roll_drauf_light'


class TestLegacyCharacterCompatibility:
    def test_legacy_character_without_content_block_still_serializes(self, app, auth_client, user_data):
        """Characters from before M24 (no content/progression block) must not break."""
        with app.app_context():
            char = Character(
                user_id=user_data['id'],
                name='OldChar',
                race='Mensch',
                class_name='Kämpfer',
                background='Soldat',
                level=1,
                character_data={
                    'roll_drauf_light': {
                        'system_id': 'roll_drauf_light',
                        'system_version': 1,
                        'species': {'slug': 'mensch', 'name': 'Mensch', 'id': 'species_mensch'},
                        'faction': {'slug': 'rote-rose', 'name': 'Rote Rose', 'id': 'faction_rote_rose'},
                        'class': {'slug': 'kaempfer', 'name': 'Kämpfer', 'id': 'class_kaempfer'},
                        'background': {'slug': 'soldat', 'name': 'Soldat', 'id': 'background_soldat'},
                    }
                    # no 'content' or 'progression' keys — pre-M24 archive
                },
            )
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        resp = auth_client.get(f"/api/characters/{char_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        # identity fields still work
        assert data['race'] == 'Mensch'
        assert data['species'] == 'Mensch'
        assert data['faction'] == 'Rote Rose'
        assert data['class'] == 'Kämpfer'
        # M24 fields gracefully absent
        assert data['training_bonus'] is None
        assert data['progression_level'] is None

    def test_pure_legacy_character_no_rdl_still_serializes(self, app, auth_client, user_data):
        """Characters with no roll_drauf_light at all must not break."""
        with app.app_context():
            char = Character(
                user_id=user_data['id'],
                name='VeryOldChar',
                race='Mensch',
                class_name='Krieger',
                background='Soldat',
                level=3,
                character_data={},
            )
            db.session.add(char)
            db.session.commit()
            char_id = char.id

        resp = auth_client.get(f"/api/characters/{char_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['race'] == 'Mensch'
        assert data['training_bonus'] is None
        assert data['progression_level'] is None
