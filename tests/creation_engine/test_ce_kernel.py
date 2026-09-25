"""WP4 acceptance through PostgreSQL, competing processes and abrupt exits."""

import multiprocessing
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.content import SchemaRegistry, SchemaType, SchemaTypeRef, create_revision, new_id, resolve_lock
from vtt.creation_engine.errors import BudgetExceeded, ContractViolation
from vtt.creation_engine.evaluator.identity import evaluator_artifact
from vtt.creation_engine.kernel.activity import Activity, Cost, Dice, Window
from vtt.creation_engine.kernel.records import ActionState, Command, KernelError
from vtt.creation_engine.kernel.service import Adjustment, Kernel, Prepared
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.runtime import RuntimeStore
from vtt.creation_engine.store.runtime_models import (CeAction, CeCheckpoint, CeDomainEvent, CeEventConsumption, CeEffectApplication,
    CeInstance, CeOutbox, CeRandomRecord, CeReceipt, CeResourceEntry, CeResourceLedger, CeRuntimeScope, RUNTIME_TABLES)
from vtt.creation_engine.units import Quantity

from test_ce_content import RULESET
from test_ce_content_store import postgres_engine

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 1, 1, tzinfo=UTC)
M74 = Path(__file__).resolve().parents[2] / 'migrations/migration_m74_creation_engine_kernel.sql'
TYPE = SchemaTypeRef('test.kernel-owner', 1)
REGISTRY = SchemaRegistry('ce.kernel-fixture', '1', [SchemaType(TYPE.type_id, TYPE.version, {
    'type': 'object', 'properties': {'plans': {'type': 'array'}}, 'required': ['plans'], 'additionalProperties': False,
})])
STRIKE = Activity('strike', (Window('activation', (Cost('source', 'charges', Quantity(Rational.of(1), 'unit:point')),),
                                  (Dice('attack', 1, 20),), 2),))


@pytest.fixture(scope='module')
def kernel_engine(postgres_engine):
    with postgres_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M74.read_text())
        connection.execute(text("UPDATE users SET is_active=true, is_suspended=false, account_state='active' WHERE id=1"))
        connection.execute(text('CREATE TABLE ce_test_consumer_counts (consumer TEXT PRIMARY KEY, hits INTEGER NOT NULL)'))
    return postgres_engine


def make_world(engine, plans=(STRIKE,)):
    with Session(engine) as session, session.begin():
        store = ContentStore(session)
        workspace = store.workspace_for(1, now=NOW)
        definition = store.add_definition(workspace.id, 'Kernel fixture', TYPE.type_id, now=NOW)
        revision = create_revision(definition.id, TYPE, {'plans': [parse_strict_json(p.canonical()) for p in plans]},
                                   registry=REGISTRY, author_user_id=1, provenance={}, now=NOW)
        store.append_revision(revision)
        lock = resolve_lock([revision.ref()], fetch=store.revision, ruleset=RULESET, registry=REGISTRY,
                            evaluator=evaluator_artifact(), configuration={})
        store.save_lock(lock, now=NOW)
        scope = CeRuntimeScope(id=new_id('scope'), kind='sandbox', owner_user_id=1, fixture=True,
                               migration_state='ENGINE', lock_id=lock.lock_id, time_watermark=NOW)
        session.add(scope)
        session.flush()
        actor = CeInstance(id=new_id('actor'), scope_id=scope.id, revision_id=revision.id, controller_user_id=1)
        session.add(actor)
        session.flush()
        items = []
        for _ in range(2):
            item = CeInstance(id=new_id('item'), scope_id=scope.id, revision_id=revision.id,
                              controller_user_id=1, holder_id=actor.id)
            session.add(item)
            session.flush()
            session.add(CeResourceLedger(instance_id=item.id, resource_id='charges', unit='unit:point',
                        current=canonical_bytes(Rational.of(1).to_wire()), maximum=canonical_bytes(Rational.of(3).to_wire()),
                        adjust_bound_policy='clamp_report_delta'))
            items.append(item.id)
        def ref(i):
            return {'kind': 'instance', 'id': i, 'scopeId': scope.id}
        wire = {'contractVersion': '1.1.3', 'commandId': new_id('cmd'), 'idempotencyKey': new_id('key'),
                'scopeId': scope.id, 'expectedScopeVersion': 0, 'authorityEpoch': 1, 'executionLockDigest': lock.digest,
                'operation': 'InvokeActivity', 'payload': {'actorInstance': ref(actor.id), 'sourceInstance': ref(items[1]),
                'activityRevisionRef': revision.ref().to_wire(), 'activityId': plans[0].id, 'targets': []}}
        return {'wire': wire, 'items': items, 'actor': actor.id, 'scope': scope.id}


@pytest.fixture
def world(kernel_engine):
    return make_world(kernel_engine)


def policy(tx, principal, wire):
    """Explicit fixture grants. Live policy is WP6, never an allow-all fallback."""
    if tx.scope.owner_user_id != principal:
        return False
    p = wire['payload']
    controlled = p['actorInstance'] if wire['operation'] == 'InvokeActivity' else p['instance']
    return tx.instance(controlled).controller_user_id == principal


def resolve(revision, activity_id):
    for plan in revision.content['plans']:
        if plan['id'] == activity_id:
            return Activity.restore(canonical_bytes(plan))
    raise ContractViolation('SEMANTIC_INVALID', 'unknown fixture activity')


def prepare(tx, action, window, fuel):
    if window.id == 'apply-effect':
        p = parse_strict_json(action.request)['payload']
        effect = {
            'applicationId': 'effect:' + action.id, 'sourceInstance': p['sourceInstance'],
            'sourceRevision': p['activityRevisionRef'], 'originId': action.id, 'target': p['actorInstance'],
            'stackGroupId': 'group:fixture', 'stackPolicy': 'all', 'sourceFeatureKey': 'feature:fixture',
            'priority': 0, 'duration': {'kind': 'permanent'}, 'cadence': None, 'policyId': 'policy:fixture',
            'changes': [{'targetBindingId': 'defense', 'operator': 'ADD',
                         'value': {'node': 'literal', 'value': Quantity(Rational.of(1), 'unit:point').to_wire()}}],
        }
        return Prepared({'resolved': True}, effects=(effect,))
    return Prepared({'resolved': True})


def kernel(engine, **kwargs):
    clock = kwargs.pop('clock', None)
    return Kernel(RuntimeStore(engine, clock=clock), ruleset=RULESET, schema_registry=kwargs.pop('schema_registry', REGISTRY),
                  configuration=kwargs.pop('configuration', {}), authorize=kwargs.pop('authorize', policy),
                  resolve_activity=resolve, prepare=kwargs.pop('prepare', prepare), worker_id=kwargs.pop('worker_id', 'worker:a'),
                  **kwargs)


def raw(wire):
    return canonical_bytes(wire)


def amount(engine, instance):
    with Session(engine) as session:
        return Rational.from_wire(parse_strict_json(session.get(CeResourceLedger, (instance, 'charges')).current))


def counts(engine, scope_id):
    with Session(engine) as session:
        return {table.__tablename__: session.scalar(select(func.count()).select_from(table).where(table.scope_id == scope_id))
                for table in (CeAction, CeReceipt, CeCheckpoint, CeDomainEvent)}


class FixedRandom:
    algorithm_id = 'test.fixed'
    def __init__(self):
        self.calls = 0
    def randrange(self, start, stop):
        self.calls += 1
        return 7


def test_t49_named_source_pays_and_retry_ignores_command_id(kernel_engine, world):
    rng = FixedRandom()
    service = kernel(kernel_engine, random=rng)
    first = service.submit(1, raw(world['wire']))
    retry = service.submit(1, raw({**world['wire'], 'commandId': 'cmd:another-transport'}))
    assert first == retry and first['commandId'] == world['wire']['commandId']
    assert first['status'] == 'committed' and rng.calls == 1
    assert [amount(kernel_engine, i) for i in world['items']] == [Rational.of(1), Rational.of(0)]
    with Session(kernel_engine) as session:
        rolls = list(session.scalars(select(CeRandomRecord).where(CeRandomRecord.checkpoint_id == first['checkpointId'])))
        assert parse_strict_json(rolls[0].canonical)['raw'] == [7]
        assert session.get(CeRuntimeScope, world['scope']).active_action_id is None


def test_t07_altered_retry_does_not_execute(kernel_engine, world):
    service = kernel(kernel_engine)
    service.submit(1, raw(world['wire']))
    changed = {**world['wire'], 'payload': {**world['wire']['payload'], 'targets': [world['wire']['payload']['actorInstance']]}}
    with pytest.raises(KernelError) as caught:
        service.submit(1, raw(changed))
    assert caught.value.code == 'IDEMPOTENCY_KEY_REUSE'
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 1


def _worker_submit(url, wire, output, start=None, stage=None):
    engine = create_engine(url)
    def fault(point):
        if point == stage:
            os._exit(79)
    service = kernel(engine, fault=fault, worker_id=f'worker:p{os.getpid()}')
    if start:
        start.wait(timeout=15)
    try:
        output.put(service.submit(1, raw(wire)))
    except ContractViolation as exc:
        output.put({'errorCode': exc.code})
    finally:
        engine.dispose()


@pytest.mark.parametrize('same_key', [False, True])
def test_t04_two_processes_contend_for_one_charge(kernel_engine, world, same_key):
    ctx = multiprocessing.get_context('spawn')
    barrier, output = ctx.Barrier(2), ctx.Queue()
    url = kernel_engine.url.render_as_string(hide_password=False)
    second = {**world['wire'], 'commandId': 'cmd:second'}
    if not same_key:
        second['idempotencyKey'] = 'key:second'
    processes = [ctx.Process(target=_worker_submit, args=(url, wire, output, barrier))
                 for wire in (world['wire'], second)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=25)
        if process.is_alive():
            process.kill()
            process.join()
            pytest.fail('competing worker did not finish')
        assert process.exitcode == 0
    results = [output.get(timeout=5) for _ in processes]
    if same_key:
        assert results[0] == results[1]
    else:
        assert sorted(r.get('status', r.get('errorCode')) for r in results) == ['SCOPE_VERSION_CONFLICT', 'committed']
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 1


@pytest.mark.parametrize('with_effect', [False, True])
@pytest.mark.parametrize('stage,committed', [('after_draw', False), ('before_commit', False), ('after_commit', True)])
def test_t05_t06_process_death_and_retry_on_another_worker(kernel_engine, stage, committed, with_effect):
    plan = replace(STRIKE, windows=(replace(STRIKE.windows[0], id='apply-effect', primitive_bound=3),)) if with_effect else STRIKE
    world = make_world(kernel_engine, (plan,))
    ctx = multiprocessing.get_context('spawn')
    output = ctx.Queue()  # retain the semaphore until the spawned process has unpickled it
    process = ctx.Process(target=_worker_submit, args=(kernel_engine.url.render_as_string(hide_password=False),
                                                     world['wire'], output, None, stage))
    process.start()
    process.join(timeout=25)
    if process.is_alive():
        process.kill()
        process.join()
        pytest.fail('crash worker did not finish')
    assert process.exitcode == 79
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == int(committed)
    rng = FixedRandom()
    result = kernel(kernel_engine, worker_id='worker:restarted', random=rng).submit(1, raw(world['wire']))
    assert result['status'] == 'committed'
    assert rng.calls == (0 if committed else 1)
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 1
    with Session(kernel_engine) as session:
        assert session.scalar(select(func.count()).select_from(CeEffectApplication)
                              .where(CeEffectApplication.scope_id == world['scope'])) == int(with_effect)

def test_later_failure_suspends_and_preserves_prior_checkpoint(kernel_engine):
    plan = replace(STRIKE, windows=STRIKE.windows + (replace(STRIKE.windows[0], id='after-hit'),))
    world = make_world(kernel_engine, (plan,))
    service = kernel(kernel_engine)
    first = service.submit(1, raw(world['wire']))
    fence = service.claim(world['scope'])
    failed = service.advance(world['scope'], first['operationId'], window_index=1, fence=fence)
    assert failed == {'status': 'SUSPENDED', 'errorCode': 'RESOURCE_BOUND_EXCEEDED', 'checkpointId': first['checkpointId']}
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 1
    assert service.submit(1, raw(world['wire'])) == first
    with Session(kernel_engine) as session:
        assert session.get(CeRuntimeScope, world['scope']).active_action_id == first['operationId']


def test_t12_cancel_after_roll_cannot_refund_or_reroll(kernel_engine, world):
    service = kernel(kernel_engine)
    first = service.submit(1, raw(world['wire']))
    with pytest.raises(KernelError, match='ACTION_STATE_CONFLICT'):
        service.cancel(1, world['scope'], first['operationId'])
    assert service.submit(1, raw(world['wire'])) == first


def test_t52_proposals_cancel_or_expire_without_checkpoint(kernel_engine, world):
    now = [NOW]
    service = kernel(kernel_engine, clock=lambda: now[0])
    first = service.submit(1, raw(world['wire']), defer=True)
    service.cancel(1, world['scope'], first['operationId'])
    next_wire = {**world['wire'], 'idempotencyKey': 'key:expire'}
    expired = service.submit(1, raw(next_wire), defer=True)
    now[0] += timedelta(seconds=121)
    assert service.expire_proposals(world['scope']) == 1
    now[0] -= timedelta(seconds=120)
    assert service.expire_proposals(world['scope']) == 0
    with Session(kernel_engine) as session:
        assert session.get(CeAction, expired['operationId']).state == 'CANCELLED'
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 0
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)


def test_precommit_admission_limit_and_released_count(kernel_engine, world):
    service = kernel(kernel_engine)
    for i in range(20):
        value = service.submit(1, raw({**world['wire'], 'idempotencyKey': f'key:{i}'}), defer=True)
    with pytest.raises(KernelError) as caught:
        service.submit(1, raw({**world['wire'], 'idempotencyKey': 'key:overflow'}), defer=True)
    assert caught.value.http_status == 429
    service.cancel(1, world['scope'], value['operationId'])
    assert service.submit(1, raw({**world['wire'], 'idempotencyKey': 'key:replacement'}), defer=True)['status'] == 'accepted'


def test_fencing_preserves_gate_and_authority_epoch(kernel_engine):
    plan = replace(STRIKE, windows=STRIKE.windows + (Window('finish', (), (), 0),))
    world = make_world(kernel_engine, (plan,))
    now = [NOW]
    one = kernel(kernel_engine, clock=lambda: now[0])
    first = one.submit(1, raw(world['wire']))
    old_fence = one.claim(world['scope'])
    other = kernel(kernel_engine, worker_id='worker:b', clock=lambda: now[0])
    with pytest.raises(KernelError, match='LEASE_BUSY'):
        other.claim(world['scope'])
    now[0] += timedelta(seconds=31)
    new_fence = other.claim(world['scope'])
    assert new_fence > old_fence
    with pytest.raises(KernelError, match='WORKER_FENCED'):
        one.advance(world['scope'], first['operationId'], window_index=1, fence=old_fence)
    assert other.advance(world['scope'], first['operationId'], window_index=1, fence=new_fence)['status'] == 'COMPLETED'
    with Session(kernel_engine) as session:
        scope = session.get(CeRuntimeScope, world['scope'])
        assert scope.authority_epoch == 1 and scope.active_action_id is None


def test_lease_expiring_during_calculation_cannot_commit(kernel_engine, world):
    now = [NOW]
    def fault(stage):
        if stage == 'after_draw':
            now[0] += timedelta(seconds=31)
    with pytest.raises(KernelError, match='WORKER_FENCED'):
        kernel(kernel_engine, clock=lambda: now[0], fault=fault).submit(1, raw(world['wire']))
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 0
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)


def test_scope_gate_and_authority_revalidation(kernel_engine):
    plan = replace(STRIKE, windows=STRIKE.windows + (Window('finish', (), (), 0),))
    world = make_world(kernel_engine, (plan,))
    service = kernel(kernel_engine)
    first = service.submit(1, raw(world['wire']))
    fresh = {**world['wire'], 'idempotencyKey': 'key:unrelated', 'expectedScopeVersion': 1}
    with pytest.raises(KernelError, match='SCOPE_BUSY'):
        service.submit(1, raw(fresh))
    with Session(kernel_engine) as session, session.begin():
        session.get(CeRuntimeScope, world['scope']).authority_epoch += 1
    with pytest.raises(KernelError, match='AUTHORITY_EPOCH_MISMATCH'):
        service.submit(1, raw(world['wire']))


def test_t08_duplicate_delivery_and_snapshot_recovery(kernel_engine, world):
    service = kernel(kernel_engine)
    receipt = service.submit(1, raw(world['wire']))
    # Other tests' scopes have pending events too. Mark those delivered in this
    # disposable fixture, so this exercise targets exactly the requested event.
    with Session(kernel_engine) as session, session.begin():
        for row in session.scalars(select(CeOutbox).where(CeOutbox.event_id != receipt['eventIds'][0])):
            row.delivered_at = NOW
    consumer, deliveries = new_id('consumer'), []
    def apply(session, event):
        session.execute(text('INSERT INTO ce_test_consumer_counts VALUES (:consumer,1) ON CONFLICT (consumer) '
                             'DO UPDATE SET hits=ce_test_consumer_counts.hits+1'), {'consumer': consumer})
    def deliver(event):
        deliveries.append(event['eventId'])
        service.store.consume_once(consumer, event, apply)
        if len(deliveries) == 1:
            raise OSError('lost ACK after consumer commit')
    with pytest.raises(OSError):
        service.store.dispatch(deliver, limit=1)
    service.store.dispatch(deliver, limit=1)
    assert deliveries[0] == deliveries[1]
    with kernel_engine.connect() as connection:
        assert connection.execute(text('SELECT hits FROM ce_test_consumer_counts WHERE consumer=:consumer'),
                                  {'consumer': consumer}).scalar_one() == 1
    snapshot = service.store.snapshot(world['scope'])
    assert snapshot['stateVersion'] == 1 and snapshot['eventSequence'] == 1
    assert next(r for r in snapshot['resources'] if r['instanceId'] == world['items'][1])['current']['numerator'] == 0


def test_duplicate_rechecks_current_policy_and_account(kernel_engine, world):
    kernel(kernel_engine).submit(1, raw(world['wire']))
    with pytest.raises(KernelError, match='OPERATION_FORBIDDEN'):
        kernel(kernel_engine, authorize=lambda *args: False).submit(1, raw(world['wire']))
    with Session(kernel_engine) as session, session.begin():
        session.execute(text('UPDATE users SET is_suspended=true WHERE id=1'))
    try:
        with pytest.raises(KernelError, match='OPERATION_FORBIDDEN'):
            kernel(kernel_engine).submit(1, raw(world['wire']))
    finally:
        with kernel_engine.begin() as connection:
            connection.execute(text('UPDATE users SET is_suspended=false WHERE id=1'))


def test_t53_transport_structural_and_runtime_limits(kernel_engine, world):
    with pytest.raises(KernelError) as caught:
        kernel(kernel_engine, max_request_bytes=1).submit(1, raw(world['wire']))
    assert caught.value.http_status == 413
    with pytest.raises(BudgetExceeded):
        replace(STRIKE, windows=(replace(STRIKE.windows[0], primitive_bound=100001),))
    def too_much(tx, action, window, fuel):
        fuel.charge(100001)
    result = kernel(kernel_engine, prepare=too_much).submit(1, raw(world['wire']))
    assert result['status'] == 'rejected' and result['errorCode'] == 'BUDGET_EXCEEDED'
    assert result['checkpointId'] is None
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)


def test_manual_adjustment_reports_clamp_delta(kernel_engine, world):
    wire = {**world['wire'], 'operation': 'AdjustResource', 'payload': {
        'instance': world['wire']['payload']['sourceInstance'], 'resourceId': 'charges',
        'delta': Quantity(Rational.of(5), 'unit:point').to_wire(), 'reason': 'explicit test adjustment'}}
    result = kernel(kernel_engine).submit(1, raw(wire))
    with Session(kernel_engine) as session:
        outcome = parse_strict_json(session.get(CeCheckpoint, result['checkpointId']).outcome)
    assert outcome['result']['manual'] is True
    assert outcome['changes'][0]['appliedDelta'] == Rational.of(2).to_wire()
    assert outcome['changes'][0]['discardedRemainder'] == Rational.of(3).to_wire()


def test_m74_matches_model_columns_and_reapplies(kernel_engine):
    inspector = inspect(kernel_engine)
    for table in RUNTIME_TABLES:
        assert {c['name']: (c['nullable'], c['type'].compile(dialect=kernel_engine.dialect))
                for c in inspector.get_columns(table.name)} == {
                    c.name: (c.nullable, c.type.compile(dialect=kernel_engine.dialect)) for c in table.columns}
    with kernel_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M74.read_text())


@pytest.mark.parametrize('table', ['ce_checkpoints', 'ce_random_records', 'ce_resource_entries', 'ce_domain_events', 'ce_receipts'])
def test_runtime_history_cannot_be_deleted(kernel_engine, world, table):
    kernel(kernel_engine).submit(1, raw(world['wire']))
    with kernel_engine.connect() as connection, pytest.raises(IntegrityError):
        connection.execute(text(f'DELETE FROM {table}'))

def test_late_checkpoint_error_rolls_back_sql_before_failure_receipt(kernel_engine, world):
    def fault(stage):
        if stage == 'checkpoint_written':
            raise BudgetExceeded('injected late checkpoint failure')
    result = kernel(kernel_engine, fault=fault).submit(1, raw(world['wire']))
    assert result['status'] == 'rejected' and result['errorCode'] == 'BUDGET_EXCEEDED'
    assert counts(kernel_engine, world['scope']) == {
        'ce_actions': 1, 'ce_receipts': 1, 'ce_checkpoints': 0, 'ce_domain_events': 0}
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)


def test_t53_later_budget_failure_keeps_previous_roll_and_charge(kernel_engine):
    plan = replace(STRIKE, windows=STRIKE.windows + (Window('later', (), (), 1),))
    world = make_world(kernel_engine, (plan,))
    def prepare_budget(tx, action, window, fuel):
        if window.id == 'later':
            fuel.charge(2)
        return Prepared({})
    service = kernel(kernel_engine, prepare=prepare_budget)
    first = service.submit(1, raw(world['wire']))
    failed = service.advance(world['scope'], first['operationId'], window_index=1, fence=service.claim(world['scope']))
    assert failed['status'] == 'SUSPENDED' and failed['errorCode'] == 'BUDGET_EXCEEDED'
    assert failed['checkpointId'] == first['checkpointId']
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 1


def test_t13_child_cycle_suspends_parent_without_repeating_its_roll(kernel_engine):
    plan = replace(STRIKE, windows=STRIKE.windows + (Window('finish', (), (), 0),), child_activity_ids=('strike',))
    world = make_world(kernel_engine, (plan,))
    service = kernel(kernel_engine)
    first = service.submit(1, raw(world['wire']))
    child = {**world['wire'], 'idempotencyKey': 'key:child', 'expectedScopeVersion': 1}
    result = service.spawn_child(1, raw(child), parent_action_id=first['operationId'], checkpoint_id=first['checkpointId'])
    assert result['errorCode'] == 'BUDGET_EXCEEDED' and result['status'] == 'suspended'
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 1


def test_t13_depth_limit_and_parent_waiting_for_child(kernel_engine):
    plans = tuple(Activity(f'chain:{i}', (Window('activate', (), (), 0), Window('finish', (), (), 0)),
                           (f'chain:{i+1}',) if i < 17 else ()) for i in range(18))
    world = make_world(kernel_engine, plans)
    service = kernel(kernel_engine)
    root = current = service.submit(1, raw(world['wire']))
    for i in range(1, 18):
        child = {**world['wire'], 'idempotencyKey': f'key:child:{i}', 'expectedScopeVersion': i,
                 'payload': {**world['wire']['payload'], 'activityId': f'chain:{i}'}}
        result = service.spawn_child(1, raw(child), parent_action_id=current['operationId'], checkpoint_id=current['checkpointId'])
        if i == 1:
            with pytest.raises(KernelError, match='SCOPE_BUSY'):
                service.advance(world['scope'], root['operationId'], window_index=1, fence=service.claim(world['scope']))
        if i <= 16:
            assert result['status'] == 'committed'
            current = result
        else:
            assert result['status'] == 'suspended' and result['errorCode'] == 'BUDGET_EXCEEDED'
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 17
    with Session(kernel_engine) as session:
        assert session.get(CeRuntimeScope, world['scope']).active_action_id == root['operationId']


def test_cumulative_root_work_includes_child_frames(kernel_engine):
    plans = tuple(Activity(f'work:{i}', (Window('activate', (), (), 100000), Window('finish', (), (), 0)),
                           (f'work:{i+1}',) if i < 10 else ()) for i in range(11))
    world = make_world(kernel_engine, plans)
    def work(tx, action, window, fuel):
        fuel.charge(window.primitive_bound)
        return Prepared({})
    service = kernel(kernel_engine, prepare=work)
    parent = service.submit(1, raw(world['wire']))
    for i in range(1, 11):
        child = {**world['wire'], 'idempotencyKey': f'key:work:{i}', 'expectedScopeVersion': i,
                 'payload': {**world['wire']['payload'], 'activityId': f'work:{i}'}}
        result = service.spawn_child(1, raw(child), parent_action_id=parent['operationId'], checkpoint_id=parent['checkpointId'])
        if i < 10:
            parent = result
        else:
            assert result['status'] == 'rejected' and result['errorCode'] == 'BUDGET_EXCEEDED'
    with Session(kernel_engine) as session:
        assert session.get(CeAction, parent['operationId']).state == 'SUSPENDED'
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 10


def test_deferred_activation_revalidates_source_relationship(kernel_engine, world):
    service = kernel(kernel_engine)
    accepted = service.submit(1, raw(world['wire']), defer=True)
    with Session(kernel_engine) as session, session.begin():
        session.get(CeInstance, world['items'][1]).holder_id = None
    result = service.advance(world['scope'], accepted['operationId'], window_index=0, fence=service.claim(world['scope']))
    assert result['status'] == 'failed_precommit' and result['errorCode'] == 'OPERATION_FORBIDDEN'
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)


@pytest.mark.parametrize('field', ['actorInstance', 'sourceInstance'])
def test_cross_scope_references_cannot_address_resources(kernel_engine, world, field):
    other = make_world(kernel_engine)
    wire = {**world['wire'], 'payload': {**world['wire']['payload'], field: other['wire']['payload'][field]}}
    with pytest.raises(KernelError, match='NOT_FOUND'):
        kernel(kernel_engine).submit(1, raw(wire))
    assert counts(kernel_engine, world['scope'])['ce_receipts'] == 0


def test_terminal_receipt_and_random_outcomes_cannot_be_rewritten(kernel_engine, world):
    result = kernel(kernel_engine).submit(1, raw(world['wire']))
    for statement, params in [
        ("UPDATE ce_receipts SET status='accepted' WHERE scope_id=:id", {'id': world['scope']}),
        ("UPDATE ce_random_records SET canonical='{}' WHERE checkpoint_id=:id", {'id': result['checkpointId']}),
    ]:
        with kernel_engine.connect() as connection, pytest.raises(IntegrityError):
            connection.execute(text(statement), params)


def test_undeclared_target_from_prepare_fails_without_spending(kernel_engine, world):
    other = make_world(kernel_engine)
    def wrong_target(tx, action, window, fuel):
        return Prepared({}, (Adjustment(other['items'][0], 'charges', Quantity(Rational.of(-1), 'unit:point'), 'bad target'),))
    result = kernel(kernel_engine, prepare=wrong_target).submit(1, raw(world['wire']))
    assert result['status'] == 'rejected' and result['errorCode'] == 'OPERATION_FORBIDDEN'
    assert amount(kernel_engine, world['items'][1]) == amount(kernel_engine, other['items'][0]) == Rational.of(1)

@pytest.mark.parametrize('value', [{'numerator': -1, 'denominator': 1}, {'numerator': 4, 'denominator': 1}])
def test_database_rejects_out_of_bounds_resource_writes(kernel_engine, world, value):
    with kernel_engine.begin() as connection, pytest.raises(IntegrityError, match='resource bound'):
        connection.execute(text('UPDATE ce_resource_ledger SET current=:value WHERE instance_id=:instance'),
                           {'value': canonical_bytes(value), 'instance': world['items'][1]})


def test_structurally_oversized_targets_are_rejected_before_admission(kernel_engine, world):
    payload = {**world['wire']['payload'], 'targets': [
        {'kind': 'instance', 'id': f'actor:{i}', 'scopeId': world['scope']} for i in range(65)]}
    with pytest.raises(BudgetExceeded):
        kernel(kernel_engine).submit(1, raw({**world['wire'], 'payload': payload}))
    assert counts(kernel_engine, world['scope'])['ce_actions'] == 0

@pytest.mark.parametrize('mismatch', ['configuration', 'schema'])
def test_installed_configuration_and_schema_must_match_lock(kernel_engine, world, mismatch):
    kwargs = {'configuration': {'unexpected': True}} if mismatch == 'configuration' else {
        'schema_registry': SchemaRegistry('another.registry', '1', [])}
    with pytest.raises(KernelError, match='EXECUTION_LOCK_MISMATCH'):
        kernel(kernel_engine, **kwargs).submit(1, raw(world['wire']))
    assert counts(kernel_engine, world['scope'])['ce_actions'] == 0

@pytest.mark.parametrize('bad_wire', ['\ud800', '{"commandId":"a","commandId":"b"}'])
def test_invalid_wire_is_rejected_before_admission(kernel_engine, world, bad_wire):
    with pytest.raises(ContractViolation) as caught:
        kernel(kernel_engine).submit(1, bad_wire)
    assert caught.value.code == 'SCHEMA_INVALID'
    assert counts(kernel_engine, world['scope'])['ce_actions'] == 0



def test_expired_proposal_retry_returns_cancellation(kernel_engine, world):
    now = [NOW]
    service = kernel(kernel_engine, clock=lambda: now[0])
    accepted = service.submit(1, raw(world['wire']), defer=True)
    now[0] += timedelta(seconds=121)
    cancelled = service.submit(1, raw({**world['wire'], 'commandId': 'cmd:retry'}))
    assert cancelled['status'] == 'rejected' and cancelled['errorCode'] == 'ACTION_CANCELLED'
    assert cancelled['operationId'] == accepted['operationId']
    assert cancelled['commandId'] == world['wire']['commandId']
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 0


def test_proposal_expiring_during_activation_cannot_commit(kernel_engine, world):
    now = [NOW]
    def fault(stage):
        if stage == 'after_draw':
            now[0] += timedelta(seconds=2)
    service = kernel(kernel_engine, clock=lambda: now[0], fault=fault)
    accepted = service.submit(1, raw(world['wire']), defer=True)
    now[0] += timedelta(seconds=119)
    with pytest.raises(KernelError, match='ACTION_CANCELLED'):
        service.advance(world['scope'], accepted['operationId'], window_index=0, fence=service.claim(world['scope']))
    assert counts(kernel_engine, world['scope'])['ce_checkpoints'] == 0
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)


def test_consumer_failure_rolls_back_deduplication_and_its_database_write(kernel_engine, world):
    service = kernel(kernel_engine)
    result = service.submit(1, raw(world['wire']))
    event = {'eventId': result['eventIds'][0]}
    consumer = new_id('consumer')
    def fail(session, stored_event):
        session.execute(text('INSERT INTO ce_test_consumer_counts VALUES (:consumer,1)'), {'consumer': consumer})
        raise RuntimeError('consumer failed before commit')
    with pytest.raises(RuntimeError):
        service.store.consume_once(consumer, event, fail)
    with kernel_engine.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM ce_test_consumer_counts WHERE consumer=:consumer'),
                                  {'consumer': consumer}).scalar_one() == 0
    with Session(kernel_engine) as session:
        assert session.get(CeEventConsumption, (consumer, event['eventId'])) is None
    assert service.store.consume_once(consumer, event, lambda session, event: None) is True



def test_new_command_cannot_overdraw_even_after_refresh(kernel_engine, world):
    service = kernel(kernel_engine)
    service.submit(1, raw(world['wire']))
    second = service.submit(1, raw({**world['wire'], 'idempotencyKey': 'key:refreshed', 'expectedScopeVersion': 1}))
    assert second['status'] == 'rejected' and second['errorCode'] == 'RESOURCE_BOUND_EXCEEDED'
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)


def test_mutable_resolver_cannot_replace_an_admitted_plan(kernel_engine):
    plan = replace(STRIKE, windows=STRIKE.windows + (Window('finish', (), (), 0),))
    world = make_world(kernel_engine, (plan,))
    service = kernel(kernel_engine)
    first = service.submit(1, raw(world['wire']))
    service.resolve_activity = lambda *args: (_ for _ in ()).throw(AssertionError('must use frozen plan'))
    result = service.advance(world['scope'], first['operationId'], window_index=1, fence=service.claim(world['scope']))
    assert result['status'] == 'COMPLETED'


def test_legacy_and_live_campaign_scopes_cannot_be_mutated(kernel_engine, world):
    service = kernel(kernel_engine)
    with Session(kernel_engine) as session, session.begin():
        scope = session.get(CeRuntimeScope, world['scope'])
        scope.migration_state = 'SHADOW'
    with pytest.raises(KernelError, match='MIGRATION_STATE_CONFLICT'):
        service.submit(1, raw(world['wire']))
    with Session(kernel_engine) as session, session.begin():
        scope = session.get(CeRuntimeScope, world['scope'])
        scope.kind, scope.migration_state, scope.fixture = 'campaign', 'ENGINE', False
    with pytest.raises(KernelError, match='MIGRATION_STATE_CONFLICT'):
        service.submit(1, raw(world['wire']))
    assert counts(kernel_engine, world['scope'])['ce_actions'] == 0
