"""D&D portable files create owned copies and retain public homebrew rules atomically."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from vtt import create_app
from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.models import CeDefinition, CeRevision, CeWorkspace
from vtt.creation_engine.store.sheet_models import CeCharacterOrigin
from vtt.extensions import db
from vtt.models import Character, Equipment, InventoryItem, Spell, User
from vtt.models.role import init_default_roles


ORIGIN = {
    'name': 'Echo folk', 'edition': 'dnd5e_2024', 'creatureType': 'Humanoid', 'size': 'medium',
    'speed': 30, 'languages': 'Common and one chosen language',
    'abilityScoreRules': 'No automatic attribute changes.', 'prose': 'People of the echoing hills.',
    'traits': [
        {'name': 'Stone memory', 'kind': 'trait', 'description': 'Remember the path through stone.', 'usage': 'Passive'},
        {'name': 'Echo step', 'kind': 'feature', 'description': 'Follow an echo to a visible space.',
         'usage': 'Once per long rest', 'choices': 'Choose a visible space.', 'prerequisites': 'Level 3'},
    ],
}


def portable(*, origin=False, edition='dnd5e_2024'):
    payload = {
        'export_kind': 'dnd5e_character', 'export_version': 1, 'system_id': edition,
        'name': 'Portable Mara', 'race': 'Echo folk', 'class': 'Wizard', 'background': 'Sage',
        'stats': {'str': 8, 'dex': 14, 'con': 12, 'int': 18, 'wis': 13, 'cha': 10,
                  'level': 5, 'xp': 7000, 'ac': 14, 'hp_current': 7, 'hp_max': 31,
                  'mana_current': 2, 'mana_max': 4, 'proficiency_bonus': 3},
        'character_data': {'notes': 'Keep my notes.', 'skills': {'Arcana': 7},
                           'custom': {'kind': ['inert', {'detail': True}]}},
        'spells': [{'name': 'Shield', 'level': 1, 'school': 'Abjuration', 'casting_time': '1 reaction',
                    'range': 'Self', 'duration': '1 round', 'is_prepared': True, 'is_ritual': False,
                    'description': 'An authored spell description.', 'damage_dice': None,
                    'damage_type': None, 'custom_data': {'notes': 'resource note'}}],
        'equipment': [{'name': 'Staff', 'type': 'Weapon', 'rarity': 'Common', 'ac_bonus': 0,
                       'damage_dice': '1d6', 'damage_type': 'Bludgeoning', 'is_equipped': True,
                       'is_cursed': False, 'weight': 4.5, 'cost': '2 gp', 'description': 'Oak.',
                       'special_properties': {'requires_attunement': False}}],
        'inventory': [{'name': 'Potion', 'type': 'Consumable', 'quantity': 3, 'weight_per_unit': 0.5,
                       'cost': '50 gp', 'is_consumable': True, 'is_cursed': False,
                       'description': 'Red liquid.', 'effects': {'dice': '2d4+2'}}],
    }
    if origin:
        payload['homebrew_origin'] = {**deepcopy(ORIGIN), 'edition': edition}
    return payload


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        init_default_roles(db.session)
        for username in ('portable_owner', 'portable_other'):
            user = User(username=username, email=username + '@example.test', role_id=1,
                        is_active=True, is_suspended=False, account_state='active')
            user.set_password('PortablePass123!')
            db.session.add(user)
        db.session.commit()
        # The adapter uses the real SQLAlchemy transaction; this host only advertises capability.
        app.extensions['ce_gateway'] = SimpleNamespace(authoring=SimpleNamespace(store=SimpleNamespace(engine=db.engine)))
        app.config['CE_AUTHORING'] = True
        yield app
        db.session.remove()
        db.drop_all()


def login(app, name='portable_owner'):
    client = app.test_client()
    assert client.post('/api/auth/login', json={'username': name, 'password': 'PortablePass123!'}).status_code == 200
    return client


@pytest.fixture
def client(app):
    return login(app)


def imported(client, payload):
    response = client.post('/api/characters/import', json=payload)
    assert response.status_code == 201, response.json
    return response.json['character']['id']


@pytest.mark.parametrize('edition', ['dnd5e_2014', 'dnd5e_2024'])
def test_plain_portable_roundtrip_retains_all_stats_resources_and_metadata_without_engine(app, client, edition):
    app.config['CE_AUTHORING'] = False
    app.extensions.pop('ce_gateway')
    payload = portable(edition=edition)
    character_id = imported(client, payload)
    exported = client.get(f'/api/characters/{character_id}/export')
    assert exported.status_code == 200 and exported.json == payload
    copied_id = imported(client, exported.json)
    assert copied_id != character_id
    with app.app_context():
        character = db.session.get(Character, copied_id)
        assert character.hp_current == 7 and character.hp_max == 31 and character.mana_current == 2
        assert character.class_name == 'Wizard' and character.background == 'Sage'
        assert character.campaign_id is None and character.avatar_url is None and character.token_url is None
        assert character.avatar_storage_key is None and character.token_storage_key is None
        assert character.user.username == 'portable_owner'
        assert len(character.spells) == len(character.equipment) == len(character.inventory) == 1
        assert character.character_data == {**payload['character_data'], 'system_id': edition}
        assert db.session.query(CeRevision).count() == 0


def test_homebrew_roundtrip_creates_new_owned_revision_without_private_source_ids(app, client):
    payload = portable(origin=True)
    original_id = imported(client, payload)
    with app.app_context():
        original_revision = db.session.get(CeCharacterOrigin, original_id).revision_id
    exported = client.get(f'/api/characters/{original_id}/export')
    assert exported.status_code == 200 and exported.json == payload
    assert original_revision not in exported.get_data(as_text=True)
    other = login(app, 'portable_other')
    copied_id = imported(other, exported.json)
    sheet = other.get(f'/api/characters/{copied_id}/sheet').json['character']
    assert sheet['homebrew_origin'] == ORIGIN and sheet['system_id'] == 'dnd5e'
    assert sheet['str'] == 8 and sheet['hp_current'] == 7
    with app.app_context():
        origin = db.session.get(CeCharacterOrigin, copied_id)
        assert origin.revision_id != original_revision and origin.version == 1
        revision = ContentStore(db.session).revision(origin.revision_id)
        definition = db.session.get(CeDefinition, revision.definition_id)
        workspace = db.session.get(CeWorkspace, definition.workspace_id)
        copied = db.session.get(Character, copied_id)
        assert workspace.owner_user_id == copied.user_id == revision.author_user_id
        provenance = parse_strict_json(revision.provenance)
        assert provenance['kind'] == 'portable_import' and provenance['declaredQuality'] == 'sheet_ready'
        assert copied.character_data == {**payload['character_data'], 'system_id': 'dnd5e_2024'}
    assert client.get(f'/api/characters/{copied_id}/export').status_code == 403


def test_attached_origin_survives_disabled_editor_and_replaced_legacy_metadata(app, client):
    character_id = imported(client, portable(origin=True))
    # Existing legacy clients can replace their JSON blob; the association is authoritative.
    assert client.put(f'/api/characters/{character_id}', json={'character_data': {'notes': 'updated'}}).status_code == 200
    app.config['CE_AUTHORING'] = False
    app.extensions.pop('ce_gateway')
    sheet = client.get(f'/api/characters/{character_id}/sheet')
    assert sheet.status_code == 200 and sheet.json['character']['homebrew_origin'] == ORIGIN
    exported = client.get(f'/api/characters/{character_id}/export')
    assert exported.status_code == 200 and exported.json['homebrew_origin'] == ORIGIN
    assert exported.json['system_id'] == 'dnd5e_2024'
    response = client.post('/api/characters/import', json=exported.json)
    assert response.status_code == 409 and 'Creation Engine' in response.json['error']
    with app.app_context():
        assert db.session.query(Character).count() == 1


@pytest.mark.parametrize('change', [
    {'system_id': 'pathfinder'}, {'export_version': True}, {'user_id': 1},
    {'campaign_id': 1}, {'avatar_url': 'https://example.test/private.png'},
    {'character_data': {'revisionId': 'rev:foreign'}},
    {'character_data': {'nested': {'kind': 'revision', 'id': 'rev:foreign'}}},
    {'character_data': {'ce_private': {'secret': 'foreign'}}},
    {'character_data': {'homebrew_origin': ORIGIN}},
    {'character_data': {'too_large': 10 ** 400}},
    {'spells': [{'name': 'Injected', 'id': 14}]},
    {'equipment': [{'name': 'Injected', 'character_id': 14}]},
    {'inventory': [{'name': 'Bad quantity', 'quantity': -1}]},
])
def test_invalid_or_authoritative_import_fields_are_rejected_without_writes(app, client, change):
    response = client.post('/api/characters/import', json={**portable(), **change})
    assert response.status_code == 422, response.json
    with app.app_context():
        assert db.session.query(Character).count() == db.session.query(CeRevision).count() == 0


@pytest.mark.parametrize('stats', [{'str': True}, {'level': 21}, {'hp_current': 32}, {'mana_current': 5}])
def test_invalid_or_inconsistent_statistics_do_not_create_a_partial_character(app, client, stats):
    payload = portable()
    payload['stats'].update(stats)
    assert client.post('/api/characters/import', json=payload).status_code == 422
    with app.app_context():
        assert db.session.query(Character).count() == 0


@pytest.mark.parametrize('change', [
    {'edition': 'dnd5e_2014'}, {'name': 'Different race'}, {'traits': []},
    {'traits': [ORIGIN['traits'][0], {**ORIGIN['traits'][1], 'name': ' STONE MEMORY '}]},
    {'revisionId': 'rev:foreign'},
])
def test_homebrew_import_rebuilds_and_validates_race_rules_before_any_write(app, client, change):
    payload = portable(origin=True)
    payload['homebrew_origin'].update(change)
    assert client.post('/api/characters/import', json=payload).status_code == 422
    with app.app_context():
        assert db.session.query(Character).count() == db.session.query(CeRevision).count() == 0


def test_failure_after_character_insert_rolls_back_character_items_workspace_and_revision(app, client, monkeypatch):
    def cannot_save(*args, **kwargs):
        raise SQLAlchemyError('test-only database interruption')
    monkeypatch.setattr(ContentStore, 'append_revision', cannot_save)
    response = client.post('/api/characters/import', json=portable(origin=True))
    assert response.status_code == 503 and 'No character was imported' in response.json['error']
    with app.app_context():
        for model in (Character, Spell, Equipment, InventoryItem, CeWorkspace, CeDefinition, CeRevision, CeCharacterOrigin):
            assert db.session.query(model).count() == 0, model.__name__


def test_homebrew_import_does_not_bypass_view_as_or_current_suspension(app, client):
    assert client.post('/api/characters/import', json=portable(origin=True),
                       headers={'X-CE-View-As': 'view:pretend'}).status_code == 403
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == 'portable_owner'))
        user.is_suspended = True
        db.session.commit()
    assert client.post('/api/characters/import', json=portable(origin=True)).status_code == 403
    with app.app_context():
        assert db.session.query(Character).count() == 0


def test_portable_export_rejects_engine_owned_projection_instead_of_stale_legacy_stats(app, client):
    character_id = imported(client, portable())
    calls = []

    class EngineOwnedCharacter:
        """Runtime authority is a host boundary; the HTTP route and adapter call are real."""
        def representation(self, kind, source_id):
            assert (kind, source_id) == ('vtt.character', character_id)
            return {'scopeId': 'scope:owned', 'instanceId': 'instance:owned'}

        def read(self, principal, kind, source_id, *, operation='read'):
            calls.append((principal, kind, source_id, operation))
            return {'hp_current': 28, 'hp_max': 40, 'engine': {'scopeId': 'scope:owned'}}

    app.extensions['ce_legacy'] = EngineOwnedCharacter()
    response = client.get(f'/api/characters/{character_id}/export')
    assert response.status_code == 409
    assert 'stats' not in response.json and 'character' not in response.json
    assert len(calls) == 1 and calls[0][1:] == ('vtt.character', character_id, 'export')


def test_portable_export_denies_view_as_even_for_a_readable_owned_character(app, client):
    character_id = imported(client, portable(origin=True))
    response = client.get(f'/api/characters/{character_id}/export', headers={'X-CE-View-As': 'view:pretend'})
    assert response.status_code == 403
    assert 'stats' not in response.json and 'homebrew_origin' not in response.json
