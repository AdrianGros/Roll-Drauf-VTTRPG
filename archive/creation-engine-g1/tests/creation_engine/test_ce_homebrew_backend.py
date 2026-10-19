"""PostgreSQL and authenticated HTTP from authoring to persisted spell outcomes."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from vtt.creation_engine import homebrew_runtime as r
from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.compiler import homebrew as h
from vtt.creation_engine.content import new_id
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.store.homebrew import HomebrewService
from vtt.creation_engine.store.homebrew_models import HOMEBREW_TABLES, CeHomebrewEvent
from vtt.models.user import User
from homebrew_examples import build, examples
from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_authoring import authoring_engine, author, submit, wire
from test_ce_authoring_transports import transport

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[2]
M80 = ROOT / 'migrations/migration_m80_creation_engine_homebrew.sql'

@pytest.fixture(scope='module', autouse=True)
def homebrew_tables(authoring_engine):
    with authoring_engine.begin() as conn:
        with conn.connection.cursor() as cursor:
            cursor.execute((ROOT / 'migrations/migration_m79_creation_engine_sheets.sql').read_text())
            cursor.execute(M80.read_text())
    return authoring_engine


def save(a, kind, values, sender=submit, quality='runtime_ready'):
    _, created = sender(a, 'CreateDraft', {'schemaType': kind.to_wire(), 'authoringLocale': 'en'})
    a = {**a, 'draft': created['draftId']}
    for q in h.interview(kind).questions:
        value = values
        for key in q.path:
            if key not in value:
                break
            value = value[key]
        else:
            sender(a, 'RecordDraftDecision', {'question': {'questionId': q.id, 'questionVersion': q.version},
                   'answer': q.answer(value), 'promptLocale': 'en'})
    _, result = sender(a, 'CommitDraftRevision', {'declaredQuality': quality, 'definition': {'kind': 'new'}})
    return result['revision']


def command(operation, payload, sandbox=None, **changes):
    value = {'contractVersion': r.CONTRACT, 'idempotencyKey': new_id('hbkey'), 'operation': operation, 'payload': payload}
    if sandbox:
        value.update(sandboxId=sandbox['sandboxId'], expectedVersion=sandbox['version'])
    return {**value, **changes}


@pytest.fixture
def world(author, homebrew_tables):
    refs = [save(author, kind, value) for kind, value in examples()]
    service = HomebrewService(author['service'], random_below=lambda n: 3)
    def send(cmd):
        return service.submit(author['principal'], author['workspace'], cmd)
    sandbox = send(command('CreateSandbox', {'edition': 'dnd5e_2024', 'revisions': refs}))
    caster = send(command('BuildCharacter', build(refs[0]['id'], refs[1]['id']), sandbox))
    target = send(command('BuildCharacter', build(refs[0]['id'], refs[1]['id'], name='Target'), caster))
    return {**author, 'refs': refs, 'adapter': service, 'send': send, 'sandbox': target,
            'caster': caster['outcome']['characterId'], 'target': target['outcome']['characterId']}


def cast_command(w):
    return command('CastSpell', {'casterId': w['caster'], 'targetId': w['target'], 'spellKey': 'ember', 'castLevel': 1,
        'distanceFeet': 20, 'adjudication': {'timingSatisfied': True, 'componentsSatisfied': True}}, w['sandbox'])


def snapshot(w, adapter=None):
    return (adapter or w['adapter']).read(w['principal'], w['workspace'], w['sandbox']['sandboxId'])


def test_m80_models_repeatable_migration_and_immutable_events(world, homebrew_tables):
    with homebrew_tables.begin() as conn:
        with conn.connection.cursor() as cursor:
            cursor.execute(M80.read_text())
    for table in HOMEBREW_TABLES:
        assert {c['name'] for c in inspect(homebrew_tables).get_columns(table.name)} == set(table.columns.keys())
    with pytest.raises(DBAPIError):
        with homebrew_tables.begin() as conn:
            conn.execute(text('UPDATE ce_homebrew_events SET result = :result WHERE sandbox_id = :id'),
                         {'result': b'{}', 'id': world['sandbox']['sandboxId']})
    with pytest.raises(DBAPIError):
        with homebrew_tables.begin() as conn:
            conn.execute(text('UPDATE ce_homebrew_sandboxes SET execution_lock = :value WHERE id = :id'),
                         {'value': b'{}', 'id': world['sandbox']['sandboxId']})


def test_lost_response_and_fresh_service_retry_do_not_reroll_or_spend_twice(world):
    w, cmd = world, cast_command(world)
    def fault(point):
        if point == 'after_commit':
            raise RuntimeError('lost response')
    w['adapter'].fault = fault
    with pytest.raises(RuntimeError, match='lost response'):
        w['send'](cmd)
    def no_roll(n):
        raise AssertionError('retry must not roll')
    fresh = HomebrewService(w['service'], random_below=no_roll)
    first = fresh.submit(w['principal'], w['workspace'], cmd)
    assert first == fresh.submit(w['principal'], w['workspace'], cmd)
    assert first['outcome']['hpDelta'] == -9 and first['rolls'] == [{'sides': 6, 'value': 4}]*2
    state = snapshot(w, fresh)['state']
    assert state['characters'][w['caster']]['resources']['mana']['current'] == 8
    assert state['characters'][w['target']]['hp'] == 9
    with pytest.raises(ContractViolation, match='IDEMPOTENCY_KEY_REUSE'):
        fresh.submit(w['principal'], w['workspace'], {**cmd, 'payload': {**cmd['payload'], 'distanceFeet': 21}})


def test_precommit_failure_rolls_back_state_and_event(world):
    w, cmd = world, cast_command(world)
    before = snapshot(w)
    def fault(point):
        if point == 'before_commit':
            raise RuntimeError('transaction fault')
    w['adapter'].fault = fault
    with pytest.raises(RuntimeError):
        w['send'](cmd)
    assert snapshot(w) == before
    with Session(w['service'].store.engine) as session:
        assert session.get(CeHomebrewEvent, (w['workspace'], w['principal'], cmd['idempotencyKey'])) is None
    w['adapter'].fault = lambda p: None
    assert w['send'](cmd)['outcome']['hpDelta'] == -9


def test_competing_commands_serialize_and_only_one_spends(world):
    w, barrier = world, Barrier(2)
    def run(cmd):
        barrier.wait(timeout=10)
        try:
            return w['send'](cmd)['operation']
        except ContractViolation as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, [cast_command(w), cast_command(w)])) == ['CastSpell', 'SCOPE_VERSION_CONFLICT']
    assert snapshot(w)['state']['characters'][w['caster']]['resources']['mana']['current'] == 8


def test_concurrent_identical_commands_share_one_event(world):
    cmd = cast_command(world)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(pool.map(world['send'], [cmd, cmd]))
    assert a == b
    events = world['adapter'].history(world['principal'], world['workspace'], a['sandboxId'])
    assert len(events) == 4 and events[-1]['result'] == a


def test_current_account_and_ownership_checked_before_retries_and_reads(world):
    w, cmd = world, cast_command(world)
    w['send'](cmd)
    for operation in (lambda: w['adapter'].submit(1, w['workspace'], cmd),
                      lambda: w['adapter'].read(1, w['workspace'], w['sandbox']['sandboxId']),
                      lambda: w['adapter'].history(1, w['workspace'], w['sandbox']['sandboxId'])):
        with pytest.raises(ContractViolation, match='NOT_FOUND'):
            operation()
    with Session(w['service'].store.engine) as session, session.begin():
        session.get(User, w['principal']).is_suspended = True
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        w['send'](cmd)
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        snapshot(w)


def test_revision_identity_edition_and_runtime_pins_are_checked(world):
    w = world
    refs = deepcopy(w['refs'])
    refs[0]['digest'] = 'sha256:' + '0'*64
    with pytest.raises(ContractViolation, match='NOT_FOUND'):
        w['send'](command('CreateSandbox', {'edition': 'dnd5e_2024', 'revisions': refs}))
    with pytest.raises(ContractViolation, match='CHARACTER_SYSTEM_MISMATCH'):
        w['send'](command('CreateSandbox', {'edition': 'dnd5e_2014', 'revisions': w['refs']}))
    kind, content = examples()[0]
    content['class']['levels'][0]['hpGain'] = 100
    newer = save(w, kind, content)
    assert newer['id'] not in snapshot(w)['executionLock']['documents']
    with pytest.raises(ContractViolation, match='REVISION_NOT_IN_LOCK'):
        w['send'](command('BuildCharacter', build(newer['id'], w['refs'][1]['id']), w['sandbox']))


def test_http_author_create_reload_build_cast_progress_history_and_access(transport, homebrew_tables):
    app, _, client, _, csrf, a = transport
    headers = {'X-CSRF-TOKEN': csrf}
    base = f"/api/ce/authoring/workspaces/{a['workspace']}"
    def http_submit(context, operation, payload):
        cmd = wire(context, operation, payload)
        response = client.post('/api/ce/commands', data=canonical_bytes(cmd), headers=headers)
        assert response.status_code == 200, response.json
        part = '' if operation == 'CreateDraft' else f"/drafts/{context['draft']}"
        result = client.get(base + part + '/commands/' + cmd['idempotencyKey'])
        assert result.status_code == 200
        return response.json, result.json
    refs = [save(a, kind, value, sender=http_submit) for kind, value in examples()]
    catalog = client.get(base + '/homebrew')
    assert catalog.status_code == 200 and len(catalog.json['revisions']) == 5
    assert catalog.headers['Cache-Control'] == 'private, no-store'
    def send(cmd):
        response = client.post(base + '/homebrew/commands', data=canonical_bytes(cmd), headers=headers)
        assert response.status_code == 200, response.json
        return response.json
    created = send(command('CreateSandbox', {'edition': 'dnd5e_2024', 'revisions': refs}))
    caster = send(command('BuildCharacter', build(refs[0]['id'], refs[1]['id']), created))
    target = send(command('BuildCharacter', build(refs[0]['id'], refs[1]['id'], name='Target'), caster))
    w = {'sandbox': target, 'caster': caster['outcome']['characterId'], 'target': target['outcome']['characterId']}
    cast = send(cast_command(w))
    state_url = base + '/homebrew/sandboxes/' + cast['sandboxId']
    state = client.get(state_url).json['state']
    assert state['characters'][w['target']]['hp'] == 18-sum(d['value'] for d in cast['rolls'])-1
    assert state['characters'][w['caster']]['resources']['mana']['current'] == 8
    progressed = send(command('RebuildCharacter', {'characterId': w['caster'], 'build': build(refs[0]['id'], refs[1]['id'], level=2)}, cast))
    assert progressed['outcome']['character']['stats']['hpMax'] == 23
    assert progressed['outcome']['character']['resources']['mana']['current'] == 8
    assert len(client.get(state_url + '/history?after=3').json) == 2
    assert client.get(state_url + '/history?after=nope').status_code == 400
    assert app.test_client().get(state_url).status_code == 401
    assert client.post(base + '/homebrew/commands', data=canonical_bytes(cast_command(w))).status_code == 401
    assert client.get(state_url, headers={'X-CE-View-As': 'view:pretend'}).status_code == 403
    assert client.post(base + '/homebrew/commands', data=canonical_bytes(cast_command(w)), headers={**headers, 'X-CE-View-As': 'view:pretend'}).status_code == 403
    app.config.update(CE_AUTHORING=False, CE_RUNTIME=True)
    assert client.get(state_url).status_code == 404


@pytest.mark.parametrize('value', [{}, {'operation': []}, {'operation': 'Unknown'}, {'operation': 'BuildCharacter', 'payload': {}}])
def test_invalid_commands_are_client_errors(transport, homebrew_tables, value):
    _, _, client, _, csrf, a = transport
    url = f"/api/ce/authoring/workspaces/{a['workspace']}/homebrew/commands"
    response = client.post(url, data=canonical_bytes(value), headers={'X-CSRF-TOKEN': csrf})
    assert response.status_code == 400
