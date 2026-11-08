"""D&D portable files create owned copies of plain 5E characters atomically.

The homebrew-race part of this format (`homebrew_origin`) belonged to Creation Engine G1 and is archived
with it (archive/creation-engine-g1/tests/test_dnd5e_portable.py); such payloads are refused without writes.
"""

from copy import deepcopy

import pytest
from sqlalchemy import select

from vtt import create_app
from vtt.extensions import db
from vtt.models import Character, User
from vtt.models.role import init_default_roles


ORIGIN = {
    'name': 'Echo folk', 'edition': 'dnd5e_2024', 'creatureType': 'Humanoid', 'size': 'medium',
    'speed': 30, 'languages': 'Common and one chosen language',
    'abilityScoreRules': 'No automatic attribute changes.', 'prose': 'People of the echoing hills.',
    'traits': [{'name': 'Stone memory', 'kind': 'trait', 'description': 'Remember the path through stone.', 'usage': 'Passive'}],
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
def test_plain_portable_roundtrip_retains_all_stats_resources_and_metadata(app, client, edition):
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
        assert db.session.query(Character).count() == 0


@pytest.mark.parametrize('stats', [{'str': True}, {'level': 21}, {'hp_current': 32}, {'mana_current': 5}])
def test_invalid_or_inconsistent_statistics_do_not_create_a_partial_character(app, client, stats):
    payload = portable()
    payload['stats'].update(stats)
    assert client.post('/api/characters/import', json=payload).status_code == 422
    with app.app_context():
        assert db.session.query(Character).count() == 0


def test_previous_engine_homebrew_race_payloads_are_refused_without_writes(app, client):
    response = client.post('/api/characters/import', json=portable(origin=True))
    assert response.status_code == 409 and 'previous Creation Engine' in response.json['error']
    with app.app_context():
        assert db.session.query(Character).count() == 0


def test_import_refuses_a_suspended_account(app, client):
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == 'portable_owner'))
        user.is_suspended = True
        db.session.commit()
    # The route's usable-account gate (_get_current_user) answers before the importer runs.
    assert client.post('/api/characters/import', json=portable()).status_code == 404
    with app.app_context():
        assert db.session.query(Character).count() == 0
