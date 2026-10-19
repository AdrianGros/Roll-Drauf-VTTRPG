"""Persisted D&D race handoffs preserve character state and enforce ownership."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from vtt.characters import characters_bp
from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.compiler import race
from vtt.creation_engine.content import new_id
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.store.race_sheets import CONTRACT, RaceSheetService, character_state
from vtt.creation_engine.store.runtime_models import CeRuntimeScope
from vtt.creation_engine.store.sheet_models import SHEET_TABLES, CeCharacterOrigin, CeSheetCommand
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Character, Equipment, User

from test_ce_authoring import author, authoring_engine, read, submit
from test_ce_authoring_transports import transport
from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_race_compiler import ANSWERS

pytestmark = pytest.mark.postgres
M79 = Path(__file__).resolve().parents[2] / 'migrations/migration_m79_creation_engine_sheets.sql'
CORE = {'name': 'Mara', 'class': 'Wizard', 'background': 'Sage', 'level': 5,
        'ac': 14, 'hp_max': 31, 'str': 8, 'dex': 14, 'con': 12, 'int': 18, 'wis': 13, 'cha': 10}


@pytest.fixture(scope='module', autouse=True)
def sheet_tables(authoring_engine):
    with authoring_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M79.read_text())
    return authoring_engine


def answer(a, key, value):
    question = race.interview().by_id[key]
    return submit(a, 'RecordDraftDecision', {'question': {'questionId': key, 'questionVersion': question.version},
                  'answer': question.answer(value), 'promptLocale': 'en'})


def saved_race(a, *, edition='dnd5e_2024', quality='sheet_ready'):
    _, created = submit(a, 'CreateDraft', {'schemaType': race.RACE_TYPE.to_wire(), 'authoringLocale': 'en'})
    a = {**a, 'draft': created['draftId']}
    for key, value in {**ANSWERS, 'race.edition': edition}.items():
        answer(a, key, value)
    _, result = submit(a, 'CommitDraftRevision', {'declaredQuality': quality, 'definition': {'kind': 'new'}})
    return {**a, 'revision': result['revision'], 'sheets': RaceSheetService(a['service'])}


@pytest.fixture
def race_author(author, sheet_tables):
    return saved_race(author)


def apply(a, payload):
    return a['sheets'].apply(a['principal'], a['workspace'], payload)


def request(a, **values):
    return {'contractVersion': CONTRACT, 'idempotencyKey': new_id('sheet'), 'revision': a['revision'], **values}


def catalog(a):
    return a['sheets'].catalog(a['principal'], a['workspace'])


def target(a, character_id):
    entry = next(row for row in catalog(a)['characters'] if row['id'] == character_id)
    return {'characterId': character_id, 'expectedState': entry['expectedState']}


def imported(a, **values):
    with Session(a['gateway'].store.engine) as session, session.begin():
        character = Character(user_id=a['principal'], name='Imported hero', race='Old race',
                              str_score=19, hp_current=7, hp_max=41, ac=18, xp=3450,
                              character_data={'imported': {'notes': 'keep me', 'skills': ['Arcana']},
                                              'system_id': 'dnd5e_2024'})
        for key, value in values.items():
            setattr(character, key, value)
        session.add(character); session.flush()
        session.add(Equipment(character_id=character.id, name='Imported staff', ac_bonus=2,
                              is_equipped=True, special_properties={'source': 'import'}))
        return character.id


def test_m79_schema_matches_models_and_command_results_are_immutable(sheet_tables):
    with sheet_tables.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M79.read_text())
    inspector = inspect(sheet_tables)
    for table in SHEET_TABLES:
        assert {column['name'] for column in inspector.get_columns(table.name)} == set(table.columns.keys())


def test_create_requires_explicit_core_values_and_pins_race_without_invented_effects(race_author):
    a = race_author
    command = request(a, character=CORE)
    result = apply(a, command)
    with Session(a['gateway'].store.engine) as session:
        character = session.get(Character, result['characterId'])
        origin = session.get(CeCharacterOrigin, character.id)
        assert character.name == CORE['name'] and character.class_name == CORE['class']
        assert character.background == CORE['background'] and character.level == 5
        assert character.hp_current == character.hp_max == 31 and character.ac == 14
        assert character.proficiency_bonus == 3 and character.mana_max == 0
        assert [getattr(character, key + '_score') for key in ('str', 'dex', 'con', 'int', 'wis', 'cha')] == [8, 14, 12, 18, 13, 10]
        assert character.race == ANSWERS['content.name']
        assert character.character_data == {'system_id': 'dnd5e_2024'}
        assert origin.revision_id == a['revision']['id'] and origin.version == 1
        assert a['sheets'].projection(character)['traits'] == ANSWERS['race.traits']
        assert character.equipment == [] and character.spells == []
    assert result['href'] == f"/character-sheet?id={result['characterId']}"
    for change in ({'character': {'name': 'Too little'}}, {'character': {**CORE, 'dex': True}},
                   {'character': {**CORE, 'level': 21}}, {'character': {**CORE, 'name': '   '}},
                   {'character': {**CORE, 'user_id': 1}}):
        with pytest.raises(ContractViolation, match='SCHEMA_INVALID'):
            apply(a, request(a, **change))


def test_existing_import_keeps_stats_equipment_and_unrelated_json(race_author):
    a = race_author
    character_id = imported(a)
    with Session(a['gateway'].store.engine) as session:
        before = session.get(Character, character_id)
        previous = {column.key: deepcopy(getattr(before, column.key)) for column in Character.__table__.columns}
        equipment = before.equipment[0].serialize()
    apply(a, request(a, target=target(a, character_id)))
    with Session(a['gateway'].store.engine) as session:
        after = session.get(Character, character_id)
        for key, value in previous.items():
            if key not in {'race', 'updated_at'}:
                assert getattr(after, key) == value, key
        assert after.equipment[0].serialize() == equipment
        assert after.race == ANSWERS['content.name']


def test_same_key_is_exactly_once_even_for_concurrent_retry_and_reuse_is_rejected(race_author):
    a = race_author
    command = request(a, character=CORE)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: apply(a, command), range(2)))
    assert results[0] == results[1] == apply(a, command)
    with pytest.raises(ContractViolation, match='IDEMPOTENCY_KEY_REUSE'):
        apply(a, {**command, 'character': {**CORE, 'name': 'Different'}})
    with Session(a['gateway'].store.engine) as session:
        assert session.scalar(select(func.count()).select_from(Character).where(Character.user_id == a['principal'])) == 1
    with pytest.raises(DBAPIError):
        with a['gateway'].store.engine.begin() as connection:
            connection.execute(text('UPDATE ce_sheet_commands SET request_digest=:digest WHERE principal_id=:id'),
                               {'digest': 'sha256:' + '0' * 64, 'id': a['principal']})


def test_stale_target_refuses_after_sheet_edit_without_creating_association(race_author):
    a = race_author
    character_id = imported(a)
    command = request(a, target=target(a, character_id))
    with Session(a['gateway'].store.engine) as session, session.begin():
        session.get(Character, character_id).hp_current = 6
    with pytest.raises(ContractViolation, match='CHARACTER_STATE_CONFLICT'):
        apply(a, command)
    with Session(a['gateway'].store.engine) as session:
        assert session.get(CeCharacterOrigin, character_id) is None
        assert session.get(Character, character_id).race == 'Old race'
        assert session.get(CeSheetCommand, (a['principal'], command['idempotencyKey'])) is None


def test_same_revision_does_not_stack_and_new_revision_changes_only_pinned_origin(race_author):
    a = race_author
    result = apply(a, request(a, character=CORE))
    character_id = result['characterId']
    again = apply(a, request(a, target=target(a, character_id)))
    assert again['originVersion'] == 1
    answer(a, 'content.name', 'Revised echo folk')
    answer(a, 'race.traits', [ANSWERS['race.traits'][1]])
    _, committed = submit(a, 'CommitDraftRevision', {'declaredQuality': 'sheet_ready',
                         'definition': {'kind': 'definition', 'id': a['revision']['definitionId']}})
    with Session(a['gateway'].store.engine) as session:
        character = session.get(Character, character_id)
        assert a['sheets'].projection(character)['name'] == ANSWERS['content.name']
        assert len(a['sheets'].projection(character)['traits']) == 2
    changed = apply(a, {**request(a, target=target(a, character_id)), 'revision': committed['revision']})
    assert changed['originVersion'] == 2
    with Session(a['gateway'].store.engine) as session:
        character = session.get(Character, character_id)
        assert character.str_score == CORE['str'] and character.hp_max == CORE['hp_max']
        assert a['sheets'].projection(character)['name'] == 'Revised echo folk'
        assert a['sheets'].projection(character)['traits'] == [ANSWERS['race.traits'][1]]


@pytest.mark.parametrize('data', [{'system_id': 'dnd5e_2014'}, {'system_id': 'pathfinder'},
                                 {'roll_drauf_light': {'system_id': 'roll_drauf_light'}}])
def test_incompatible_rulesets_and_rdl_cannot_receive_race(race_author, data):
    a = race_author
    character_id = imported(a, character_data=data)
    with Session(a['gateway'].store.engine) as session:
        state = character_state(session.get(Character, character_id), None)
    with pytest.raises(ContractViolation, match='CHARACTER_SYSTEM_MISMATCH'):
        apply(a, request(a, target={'characterId': character_id, 'expectedState': state}))
    if data.get('system_id') != 'dnd5e_2014':
        assert character_id not in [row['id'] for row in catalog(a)['characters']]


def test_character_and_workspace_ownership_checked_before_apply_or_retry(race_author):
    a = race_author
    character_id = imported(a, user_id=1)
    with pytest.raises(ContractViolation, match='NOT_FOUND'):
        apply(a, request(a, target={'characterId': character_id, 'expectedState': 'guessed'}))
    command = request(a, character=CORE)
    apply(a, command)
    with pytest.raises(ContractViolation, match='NOT_FOUND'):
        a['sheets'].apply(1, a['workspace'], command)
    with pytest.raises(ContractViolation, match='NOT_FOUND'):
        a['sheets'].catalog(1, a['workspace'])
    with Session(a['gateway'].store.engine) as session, session.begin():
        session.get(User, a['principal']).is_suspended = True
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        apply(a, command)


def test_incomplete_or_foreign_revisions_cannot_be_attached(author, sheet_tables):
    a = saved_race(author, quality='lore_only')
    assert catalog(a)['revisions'] == []
    with pytest.raises(ContractViolation, match='RACE_REVISION_REQUIRED'):
        apply(a, request(a, character=CORE))
    foreign = {**a, 'principal': 1, 'workspace': a['service'].workspace(1)['workspaceId']}
    with pytest.raises(ContractViolation, match='NOT_FOUND'):
        apply(foreign, request(a, character=CORE))


def test_engine_owned_target_is_fenced_even_for_same_revision(race_author):
    a = race_author
    result = apply(a, request(a, character=CORE))
    command = request(a, target=target(a, result['characterId']))
    scope_id = a['gateway'].kernel.migration.provision(a['principal'], fixture=True)
    with Session(a['gateway'].store.engine) as session, session.begin():
        session.get(CeRuntimeScope, scope_id).migration_state = 'ENGINE'
    with pytest.raises(ContractViolation, match='LEGACY_FIELD_READ_ONLY'):
        apply(a, command)
    with pytest.raises(ContractViolation, match='LEGACY_FIELD_READ_ONLY'):
        apply(a, request(a, character=CORE))


def test_http_requires_csrf_authoring_and_real_owner_not_view_as(transport, race_author):
    app, _, client, _, csrf, _ = transport
    a = race_author
    url = f"/api/ce/authoring/workspaces/{a['workspace']}/sheets"
    command = request(a, character=CORE)
    assert app.test_client().get(url).status_code == 401
    assert client.post(url, data=canonical_bytes(command)).status_code == 401
    headers = {'X-CSRF-TOKEN': csrf}
    assert client.get(url, headers={'X-CE-View-As': 'view:pretend'}).status_code == 403
    assert client.post(url, data=canonical_bytes(command), headers={**headers, 'X-CE-View-As': 'view:pretend'}).status_code == 403
    response = client.post(url, data=canonical_bytes(command), headers=headers)
    assert response.status_code == 200 and response.headers['Cache-Control'] == 'private, no-store'
    assert client.post(url, data=canonical_bytes(command), headers=headers).json == response.json
    assert client.get(url).json['revisions'][0]['content']['traits'] == ANSWERS['race.traits']
    app.config.update(CE_AUTHORING=False, CE_RUNTIME=True)
    assert client.get(url).status_code == 404
    assert client.post(url, data=canonical_bytes(command), headers=headers).status_code == 404


def test_sheet_readers_get_rules_without_private_authoring_ids_or_history(transport, race_author):
    app, _, client, _, _, _ = transport
    a = race_author
    app.config['SQLALCHEMY_DATABASE_URI'] = a['gateway'].store.engine.url.render_as_string(hide_password=False)
    db.init_app(app)
    app.register_blueprint(characters_bp, url_prefix='/api')
    result = apply(a, request(a, character=CORE))
    with Session(a['gateway'].store.engine) as session, session.begin():
        campaign = Campaign(name='D&D party', owner_id=a['principal'])
        session.add(campaign); session.flush()
        session.get(Character, result['characterId']).campaign_id = campaign.id
        session.add(CampaignMember(campaign_id=campaign.id, user_id=1, campaign_role='Player', status='active'))
    url = f"/api/characters/{result['characterId']}/sheet"
    response = client.get(url)
    assert response.status_code == 200
    public = response.json['character']
    assert public['system_id'] == 'dnd5e' and public['system_version'] == 'dnd5e_2024'
    assert public['homebrew_origin']['traits'] == ANSWERS['race.traits']
    body = response.get_data(as_text=True)
    for private in [a['workspace'], a['draft'], a['revision']['id'], a['revision']['definitionId'],
                    'authoringLocale', 'promptLocale', 'draftVersion', 'provenance']:
        assert private not in body
    with app.app_context():
        token = create_access_token(identity='1')
    member = app.test_client(); member.set_cookie('access_token_cookie', token)
    assert member.get(url).json['character']['homebrew_origin'] == public['homebrew_origin']
    assert member.get(f"/api/ce/authoring/workspaces/{a['workspace']}/sheets").status_code == 404
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
