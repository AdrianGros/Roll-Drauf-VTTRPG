"""WP5 acceptance: real PostgreSQL, typed answers and controlled authority time."""

import copy
import multiprocessing
import os
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.content import SchemaRegistry, SchemaType, SchemaTypeRef, new_id
from vtt.creation_engine.contracts import CORE_SCHEMA_ID, validate_definition
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.kernel.activity import Activity, Window
from vtt.creation_engine.kernel.decisions import Question
from vtt.creation_engine.kernel.service import Adjustment, Prepared
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.runtime_models import CeAction, CeCheckpoint, CeDomainEvent, CePendingDecision, CeRuntimeScope
from vtt.creation_engine.units import Quantity

from test_ce_content_store import postgres_engine
from test_ce_kernel import (kernel_engine, kernel, make_world, REGISTRY, TYPE, NOW, STRIKE, FixedRandom,
                            policy, amount, raw)

pytestmark = pytest.mark.postgres
ANSWER = SchemaTypeRef('test.answer.boolean', 1)
ANSWER_SCHEMA = {'allOf': [{'$ref': CORE_SCHEMA_ID + '#/$defs/DecisionAnswer'},
                           {'properties': {'kind': {'const': 'boolean'}}}]}
SCHEMAS = SchemaRegistry('ce.decision-fixture', '1', [REGISTRY.get(TYPE), SchemaType(ANSWER.type_id, 1, ANSWER_SCHEMA)])
QUESTION = Question('question:hit', 1, ANSWER, 'responders:owner', 'policy:private')
PLAN = Activity('strike', (replace(STRIKE.windows[0], wait_for_decision=True, question=QUESTION), Window('finish', (), (), 1)))


def authorization(tx, principal, wire):
    if wire['operation'] in {'InvokeActivity', 'AdjustResource'}:
        return policy(tx, principal, wire)
    return tx.scope.owner_user_id == principal


def responders(tx, rule, action):
    return [tx.scope.owner_user_id] if rule in {'responders:owner', 'responders:adjudicator'} else []


def service(engine, *, clock=None, **kwargs):
    return kernel(engine, clock=clock or (lambda: NOW), schema_registry=SCHEMAS,
                  authorize=kwargs.pop('authorize', authorization),
                  responders=kwargs.pop('responders', responders),
                  decision_facts=kwargs.pop('decision_facts', lambda tx, action, question: {}),
                  authorize_operator=kwargs.pop('authorize_operator', lambda tx, principal, wire: principal == tx.scope.owner_user_id),
                  **kwargs)


def start(engine, *, plan=PLAN, clock=None, **kwargs):
    world = make_world(engine, (plan,), registry=SCHEMAS)
    engine_service = service(engine, clock=clock, **kwargs)
    first = engine_service.submit(1, raw(world['wire']))
    assert first['status'] == 'committed', first
    with engine_service.store.transaction(world['scope']) as tx:
        pending = tx.open_decisions(first['operationId'])[0]
    return world, engine_service, first, pending


def envelope(world, operation, payload, version):
    return {**world['wire'], 'operation': operation, 'payload': payload, 'expectedScopeVersion': version,
            'idempotencyKey': new_id('key'), 'commandId': new_id('cmd')}


def answer(world, decision, value=True):
    return envelope(world, 'ResolveDecision', {'actionId': decision.wire['actionId'], 'decisionId': decision.id,
                    'expectedDecisionVersion': decision.version, 'contextToken': decision.wire['contextToken'],
                    'answer': {'kind': 'boolean', 'value': value}}, decision.created_scope_version)


def operator_wire(world, engine_service, operation, **payload):
    with engine_service.store.transaction(world['scope']) as tx:
        action = tx.action(payload['actionId'])
        version = tx.scope.state_version
        if operation in {'ResumeSuspendedAction', 'ResolveActionManually'}:
            payload.setdefault('expectedActionVersion', action.version)
    return envelope(world, operation, payload, version)


def state(engine, world, action_id):
    with Session(engine) as session:
        a = session.get(CeAction, action_id)
        s = session.get(CeRuntimeScope, world['scope'])
        return a.state, s.active_action_id


def tick(engine_service, world, clock, seconds):
    clock[0] = NOW + timedelta(seconds=seconds)
    fence = engine_service.claim(world['scope'])
    engine_service.heartbeat(world['scope'], fence=fence)


def test_prompt_binds_schema_snapshot_and_opaque_nonce(kernel_engine):
    world, k, first, d = start(kernel_engine)
    validate_definition('PendingDecision', d.wire)
    assert d.wire['answerSchemaDigest'] == content_digest(ANSWER_SCHEMA)
    assert d.deadline == NOW + timedelta(seconds=120)
    assert d.wire['contextToken'].startswith('ctx:') and len(d.wire['contextToken']) == 47
    assert d.wire['contextToken'] != d.context_digest
    assert d.wire['checkpointId'] == first['checkpointId']
    assert state(kernel_engine, world, first['operationId']) == ('WAITING_DECISION', first['operationId'])
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)


def test_answer_once_retry_and_continuation_use_retained_input(kernel_engine):
    rng = FixedRandom()
    world, k, first, d = start(kernel_engine, random=rng)
    wire = answer(world, d)
    result = k.submit(1, raw(wire))
    assert result['status'] == 'committed'
    assert k.submit(1, raw({**wire, 'commandId': 'cmd:retry'})) == result
    assert k.submit(1, raw(answer(world, d, False)))['errorCode'] == 'DECISION_STALE'
    seen = []
    def prepare(tx, action, window, fuel):
        seen.append(tx.answers(action.id))
        return Prepared({'answer': seen[-1]})
    k.prepare = prepare
    fence = k.claim(world['scope'])
    done = k.advance(world['scope'], first['operationId'], window_index=1, fence=fence)
    assert done['status'] == 'COMPLETED'
    assert seen == [{'question:hit': {'kind': 'boolean', 'value': True}}]
    assert rng.calls == 1
    assert state(kernel_engine, world, first['operationId']) == ('COMPLETED', None)


def test_last_window_decision_completes_root(kernel_engine):
    world, k, first, d = start(kernel_engine, plan=replace(PLAN, windows=PLAN.windows[:1]))
    assert k.submit(1, raw(answer(world, d)))['status'] == 'committed'
    assert state(kernel_engine, world, first['operationId']) == ('COMPLETED', None)


@pytest.mark.parametrize('change,code', [
    ({'contextToken': 'ctx:' + 'A' * 43}, 'DECISION_STALE'),
    ({'expectedDecisionVersion': 1}, 'DECISION_STALE'),
    ({'answer': {'kind': 'text', 'value': 'yes'}}, 'SCHEMA_INVALID'),
    ({'answer': {'kind': 'boolean', 'value': 'true'}}, 'SCHEMA_INVALID'),
])
def test_bad_response_cannot_change_prompt(kernel_engine, change, code):
    world, k, first, d = start(kernel_engine)
    wire = answer(world, d)
    wire['payload'].update(change)
    with pytest.raises(ContractViolation) as exc:
        k.submit(1, raw(wire))
    assert exc.value.code == code
    with k.store.transaction(world['scope']) as tx:
        assert tx.decision(d.id).wire['status'] == 'open'
    assert state(kernel_engine, world, first['operationId'])[0] == 'WAITING_DECISION'


def test_scope_version_floor_not_equality(kernel_engine):
    world, k, first, d = start(kernel_engine)
    wire = answer(world, d)
    wire['expectedScopeVersion'] = d.created_scope_version - 1
    with pytest.raises(ContractViolation, match='SCOPE_VERSION_CONFLICT'):
        k.submit(1, raw(wire))
    with k.store.transaction(world['scope']) as tx:
        tx.scope.state_version += 3  # nonmechanical version growth leaves context unchanged
    wire['expectedScopeVersion'] = d.created_scope_version
    assert k.submit(1, raw(wire))['status'] == 'committed'


def test_t09_revocation_is_atomic_inside_held_gate(kernel_engine):
    permitted = [1]
    world, k, first, d = start(kernel_engine, responders=lambda tx, rule, action: permitted)
    with k.store.transaction(world['scope']) as tx:
        permitted.clear()  # fixture grant; production writer updates its grant rows here
        k.policy_changed(tx, reason='scope membership revoked')
        assert tx.scope.policy_version == 2
        assert tx.decision(d.id).wire['status'] == 'invalidated'
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        k.submit(1, raw(answer(world, d)))
    assert state(kernel_engine, world, first['operationId']) == ('SUSPENDED', first['operationId'])
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)


def test_revoked_responder_cannot_read_old_receipt(kernel_engine):
    permitted = [1]
    world, k, first, d = start(kernel_engine, responders=lambda tx, rule, action: permitted)
    wire = answer(world, d)
    k.submit(1, raw(wire))
    permitted.clear()
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        k.submit(1, raw(wire))


def test_t10_operator_adjustment_invalidates_prompt_in_same_frame(kernel_engine):
    world, k, first, d = start(kernel_engine)
    delta = Quantity(Rational.of(1), 'unit:point').to_wire()
    wire = envelope(world, 'AdjustResource', {'instance': world['wire']['payload']['sourceInstance'],
                    'resourceId': 'charges', 'delta': delta, 'reason': 'correct recorded charge'}, 1)
    adjustment = k.submit(1, raw(wire))
    assert adjustment['status'] == 'committed'
    assert state(kernel_engine, world, first['operationId']) == ('SUSPENDED', first['operationId'])
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)
    with Session(kernel_engine) as session:
        assert session.get(CeCheckpoint, adjustment['checkpointId']).action_id == first['operationId']
    assert k.submit(1, raw(answer(world, d)))['errorCode'] == 'DECISION_STALE'


def test_unannounced_mechanical_change_is_detected(kernel_engine):
    facts = {'hitThreshold': 10}
    world, k, first, d = start(kernel_engine, decision_facts=lambda tx, action, question: facts)
    facts['hitThreshold'] = 12
    assert k.submit(1, raw(answer(world, d)))['errorCode'] == 'DECISION_STALE'
    assert state(kernel_engine, world, first['operationId'])[0] == 'SUSPENDED'


@pytest.mark.parametrize('optional', [False, True])
def test_t11_timeout_preserves_roll_and_declines_only_when_declared(kernel_engine, optional):
    clock = [NOW]
    q = replace(QUESTION, decline={'kind': 'boolean', 'value': False}) if optional else QUESTION
    plan = replace(PLAN, windows=(replace(PLAN.windows[0], question=q), PLAN.windows[1]))
    world, k, first, d = start(kernel_engine, plan=plan, clock=lambda: clock[0])
    for seconds in (30, 60, 90, 120):
        tick(k, world, clock, seconds)
    with k.store.transaction(world['scope']) as tx:
        expired = tx.decision(d.id)
        assert expired.wire['status'] == 'expired'
        assert expired.answer == ({'kind': 'boolean', 'value': False} if optional else None)
        assert tx.action(first['operationId']).state == ('ACTIVE' if optional else 'SUSPENDED')
        assert tx.scope.active_action_id == first['operationId']
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)
    clock[0] = NOW + timedelta(seconds=119)  # rollback never reopens an expired prompt
    assert k.submit(1, raw(answer(world, d)))['errorCode'] == 'DECISION_STALE'


def test_acceptance_checks_commit_time_not_request_time(kernel_engine):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    for seconds in (30, 60, 90):
        tick(k, world, clock, seconds)
    times = iter([NOW + timedelta(seconds=119), NOW + timedelta(seconds=120)])
    k.store.clock = lambda: next(times)
    result = k.submit(1, raw(answer(world, d)))
    assert result['errorCode'] == 'DECISION_STALE'
    assert state(kernel_engine, world, first['operationId'])[0] == 'SUSPENDED'
    with Session(kernel_engine) as session:
        drow = session.get(CePendingDecision, (d.id, 0))
        assert drow.status == 'expired' and drow.answer is None
        assert drow.closed_at == NOW + timedelta(seconds=120)


@pytest.mark.parametrize('via_response', [False, True])
def test_t54_forward_gap_suspends_without_expiring_or_answering(kernel_engine, via_response):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    clock[0] += timedelta(seconds=300)
    if via_response:
        assert k.submit(1, raw(answer(world, d)))['errorCode'] == 'DECISION_STALE'
    else:
        tick(k, world, clock, 300)
    with k.store.transaction(world['scope']) as tx:
        stored = tx.decision(d.id)
        assert stored.wire['status'] == 'invalidated' and stored.answer is None
        assert tx.action(first['operationId']).error_code == 'CLOCK_ANOMALY'
    clock[0] = NOW
    assert k.submit(1, raw(answer(world, d)))['errorCode'] == 'DECISION_STALE'
    assert state(kernel_engine, world, first['operationId']) == ('SUSPENDED', first['operationId'])


def test_reissue_new_version_deadline_and_nonce_old_response_never_valid(kernel_engine):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    tick(k, world, clock, 300)
    wire = operator_wire(world, k, 'ReissueDecision', actionId=first['operationId'], decisionId=d.id,
                         expectedDecisionVersion=0, deadlineSeconds=45)
    result = k.submit(1, raw(wire))
    assert k.submit(1, raw(wire)) == result
    with k.store.transaction(world['scope']) as tx:
        fresh = tx.decision(d.id)
        assert fresh.version == 1 and fresh.deadline == clock[0] + timedelta(seconds=45)
        assert fresh.wire['contextToken'] != d.wire['contextToken']
        assert tx.decision(d.id, 0).wire['status'] == 'invalidated'
    with pytest.raises(ContractViolation, match='DECISION_STALE'):
        k.submit(1, raw(answer(world, d)))
    assert k.submit(1, raw(answer(world, fresh)))['status'] == 'committed'


def test_reassign_requires_registered_eligible_rule_and_rotates_version(kernel_engine):
    world, k, first, d = start(kernel_engine)
    payload = dict(actionId=first['operationId'], decisionId=d.id, expectedDecisionVersion=0)
    invalid = operator_wire(world, k, 'ReassignDecisionResponder', **payload, responderRuleId='responders:nobody')
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        k.submit(1, raw(invalid))
    valid = operator_wire(world, k, 'ReassignDecisionResponder', **payload, responderRuleId='responders:adjudicator')
    assert k.submit(1, raw(valid))['status'] == 'committed'
    with k.store.transaction(world['scope']) as tx:
        fresh = tx.decision(d.id)
        assert fresh.version == 1 and fresh.deadline == d.deadline
        assert fresh.question.responder_rule_id == 'responders:adjudicator'
    assert k.submit(1, raw(answer(world, fresh)))['status'] == 'committed'


def test_reassign_after_expiry_still_requires_explicit_reissue(kernel_engine):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    tick(k, world, clock, 300)
    command = operator_wire(world, k, 'ReassignDecisionResponder', actionId=first['operationId'], decisionId=d.id,
                            expectedDecisionVersion=0, responderRuleId='responders:adjudicator')
    k.submit(1, raw(command))
    with k.store.transaction(world['scope']) as tx:
        assert tx.decision(d.id).wire['status'] == 'invalidated'
    command = operator_wire(world, k, 'ReissueDecision', actionId=first['operationId'], decisionId=d.id,
                            expectedDecisionVersion=1, deadlineSeconds=120)
    k.submit(1, raw(command))
    with k.store.transaction(world['scope']) as tx:
        fresh = tx.decision(d.id)
    assert k.submit(1, raw(answer(world, fresh)))['status'] == 'committed'


def test_resume_cannot_bypass_unresolved_question(kernel_engine):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    tick(k, world, clock, 300)
    command = operator_wire(world, k, 'ResumeSuspendedAction', actionId=first['operationId'])
    with pytest.raises(ContractViolation, match='DECISION_STALE'):
        k.submit(1, raw(command))


def test_t50_manual_completion_is_checkpoint_with_adjudicator_and_reason(kernel_engine):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    tick(k, world, clock, 300)
    adjustment = {'instance': world['wire']['payload']['sourceInstance'], 'resourceId': 'charges',
                  'delta': Quantity(Rational.of(1), 'unit:point').to_wire()}
    wire = operator_wire(world, k, 'ResolveActionManually', actionId=first['operationId'], adjustments=[adjustment],
                         outcomeNote='Adjudicated miss; return charge', reason='table ruling')
    result = k.submit(1, raw(wire))
    assert result['status'] == 'committed' and k.submit(1, raw(wire)) == result
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)
    with Session(kernel_engine) as session:
        outcome = parse_strict_json(session.get(CeCheckpoint, result['checkpointId']).outcome)
        assert outcome['manual'] is True and outcome['adjudicator'] == 1 and outcome['reason'] == 'table ruling'
        assert outcome['automatedCompletion'] is False
        assert session.get(CeCheckpoint, first['checkpointId']) is not None
    assert state(kernel_engine, world, first['operationId']) == ('COMPLETED', None)


def test_t50_operator_role_does_not_grant_other_resource_control(kernel_engine):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    tick(k, world, clock, 300)
    k.authorize = lambda tx, p, w: w['operation'] != 'AdjustResource'
    wire = operator_wire(world, k, 'ResolveActionManually', actionId=first['operationId'],
        adjustments=[{'instance': world['wire']['payload']['sourceInstance'], 'resourceId': 'charges',
                      'delta': Quantity(Rational.of(1), 'unit:point').to_wire()}], outcomeNote='manual', reason='ruling')
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        k.submit(1, raw(wire))
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)
    assert state(kernel_engine, world, first['operationId'])[0] == 'SUSPENDED'


def test_operator_commands_default_deny(kernel_engine):
    world, k, first, d = start(kernel_engine, authorize_operator=None)
    wire = operator_wire(world, k, 'ReissueDecision', actionId=first['operationId'], decisionId=d.id,
                         expectedDecisionVersion=0, deadlineSeconds=120)
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        k.submit(1, raw(wire))


def test_failed_response_transaction_leaves_answer_unaccepted(kernel_engine):
    world, k, first, d = start(kernel_engine)
    def failure(stage):
        if stage == 'before_commit':
            raise RuntimeError('injected failure')
    k.fault = failure
    wire = answer(world, d)
    with pytest.raises(RuntimeError):
        k.submit(1, raw(wire))
    with k.store.transaction(world['scope']) as tx:
        assert tx.decision(d.id).wire['status'] == 'open'
        assert tx.receipt(1, wire['idempotencyKey']) is None
    k.fault = lambda stage: None
    assert k.submit(1, raw(wire))['status'] == 'committed'


def test_lost_ack_response_retry_does_not_duplicate_checkpoint(kernel_engine):
    world, k, first, d = start(kernel_engine)
    def failure(stage):
        if stage == 'after_commit':
            raise RuntimeError('lost acknowledgement')
    k.fault = failure
    wire = answer(world, d)
    with pytest.raises(RuntimeError):
        k.submit(1, raw(wire))
    k.fault = lambda stage: None
    result = k.submit(1, raw(wire))
    with k.store.transaction(world['scope']) as tx:
        assert tx.intervention_index(first['operationId']) == -2
        assert tx.receipt(1, wire['idempotencyKey']) == result


@pytest.mark.parametrize('sql', [
    "DELETE FROM ce_pending_decisions WHERE id=:id",
    "UPDATE ce_pending_decisions SET answer=convert_to('{}','UTF8') WHERE id=:id",
    "UPDATE ce_pending_decisions SET context_digest='sha256:forged' WHERE id=:id",
])
def test_final_decision_history_is_database_immutable(kernel_engine, sql):
    world, k, first, d = start(kernel_engine)
    k.submit(1, raw(answer(world, d)))
    with pytest.raises(IntegrityError), kernel_engine.begin() as connection:
        connection.execute(text(sql), {'id': d.id})


def _resolve_process(url, wire, barrier, queue):
    engine = create_engine(url)
    k = service(engine, worker_id=f'worker:response-{os.getpid()}')
    barrier.wait(timeout=20)
    try:
        queue.put(k.submit(1, raw(wire)))
    except ContractViolation as exc:
        queue.put({'errorCode': exc.code})
    finally:
        engine.dispose()


@pytest.mark.parametrize('same_key', [False, True])
def test_competing_processes_accept_one_response(kernel_engine, same_key):
    world, k, first, d = start(kernel_engine)
    ctx = multiprocessing.get_context('spawn')
    barrier, queue = ctx.Barrier(2), ctx.Queue()
    wire = answer(world, d)
    other = wire if same_key else answer(world, d, False)
    url = kernel_engine.url.render_as_string(hide_password=False)
    processes = [ctx.Process(target=_resolve_process, args=(url, w, barrier, queue)) for w in (wire, other)]
    for process in processes:
        process.start()
    results = [queue.get(timeout=40) for _ in processes]
    for process in processes:
        process.join(timeout=40)
        assert process.exitcode == 0
    if same_key:
        assert results[0] == results[1] and results[0]['status'] == 'committed'
    else:
        assert sorted(r.get('status', '') for r in results) == ['committed', 'rejected']
        assert sum(r.get('errorCode') == 'DECISION_STALE' for r in results) == 1
    with k.store.transaction(world['scope']) as tx:
        assert tx.intervention_index(first['operationId']) == -2


def test_migration_is_repeatable(kernel_engine):
    from test_ce_kernel import M74
    with kernel_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M74.with_name('migration_m75_creation_engine_decisions.sql').read_text())


@pytest.mark.parametrize('port', ['responders', 'decision_facts'])
def test_missing_question_registration_cannot_commit_first_cost(kernel_engine, port):
    world = make_world(kernel_engine, (PLAN,), registry=SCHEMAS)
    k = service(kernel_engine, **{port: None})
    result = k.submit(1, raw(world['wire']))
    assert result['status'] == 'rejected'
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)
    with k.store.transaction(world['scope']) as tx:
        assert not tx.open_decisions()
        assert tx.scope.active_action_id is None


def test_heartbeat_requires_current_lease_holder_and_fence(kernel_engine):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    fence = k.claim(world['scope'])
    other = service(kernel_engine, clock=lambda: clock[0], worker_id='worker:b')
    with pytest.raises(ContractViolation, match='WORKER_FENCED'):
        other.heartbeat(world['scope'], fence=fence)
    clock[0] += timedelta(seconds=31)
    new_fence = other.claim(world['scope'])
    with pytest.raises(ContractViolation, match='WORKER_FENCED'):
        k.heartbeat(world['scope'], fence=fence)
    other.heartbeat(world['scope'], fence=new_fence)
    assert state(kernel_engine, world, first['operationId'])[0] == 'WAITING_DECISION'


def test_visible_timeout_is_copied_not_reloaded_for_existing_prompt(kernel_engine):
    world = make_world(kernel_engine, (PLAN,), registry=SCHEMAS)
    k = service(kernel_engine)
    with k.store.transaction(world['scope']) as tx:
        tx.scope.decision_timeout_seconds = 60
    first = k.submit(1, raw(world['wire']))
    with k.store.transaction(world['scope']) as tx:
        d = tx.open_decisions(first['operationId'])[0]
        tx.scope.decision_timeout_seconds = 600
    assert d.deadline == NOW + timedelta(seconds=60) and d.timeout_seconds == 60


def test_resume_operational_failure_preserves_inputs_and_window_index(kernel_engine):
    from vtt.creation_engine.errors import BudgetExceeded
    world, k, first, d = start(kernel_engine)
    k.submit(1, raw(answer(world, d)))
    def fail(tx, action, window, fuel):
        raise BudgetExceeded('fixture operational failure')
    k.prepare = fail
    fence = k.claim(world['scope'])
    failed = k.advance(world['scope'], first['operationId'], window_index=1, fence=fence)
    assert failed['status'] == 'SUSPENDED'
    wire = operator_wire(world, k, 'ResumeSuspendedAction', actionId=first['operationId'])
    assert k.submit(1, raw(wire))['status'] == 'committed'
    k.prepare = lambda tx, action, window, fuel: Prepared({'answer': tx.answers(action.id)})
    fence = k.claim(world['scope'])
    result = k.advance(world['scope'], first['operationId'], window_index=1, fence=fence)
    assert result['status'] == 'COMPLETED'
    assert result['outcome']['result']['answer']['question:hit']['value'] is True
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)


def test_manual_completion_when_locked_evaluator_is_unavailable(kernel_engine, monkeypatch):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    tick(k, world, clock, 300)
    monkeypatch.setattr('vtt.creation_engine.kernel.service.evaluator_artifact', lambda: {'unavailable': True})
    wire = operator_wire(world, k, 'ResolveActionManually', actionId=first['operationId'], adjustments=[],
                         outcomeNote='Resolved at table', reason='locked evaluator unavailable')
    assert k.submit(1, raw(wire))['status'] == 'committed'
    assert state(kernel_engine, world, first['operationId'])[0] == 'COMPLETED'


def test_unusable_account_cannot_answer_or_automatically_decline(kernel_engine):
    clock = [NOW]
    q = replace(QUESTION, decline={'kind': 'boolean', 'value': False})
    plan = replace(PLAN, windows=(replace(PLAN.windows[0], question=q), PLAN.windows[1]))
    world, k, first, d = start(kernel_engine, plan=plan, clock=lambda: clock[0])
    for seconds in (30, 60, 90):
        tick(k, world, clock, seconds)
    try:
        with kernel_engine.begin() as connection:
            connection.execute(text('UPDATE users SET is_suspended=true WHERE id=1'))
        with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
            k.submit(1, raw(answer(world, d)))
        tick(k, world, clock, 120)
        with k.store.transaction(world['scope']) as tx:
            assert tx.decision(d.id).wire['status'] == 'invalidated'
            assert tx.decision(d.id).answer is None
    finally:
        with kernel_engine.begin() as connection:
            connection.execute(text('UPDATE users SET is_suspended=false WHERE id=1'))


def test_exact_answer_schema_rejects_undeclared_optional_timeout_answer(kernel_engine):
    invalid = replace(QUESTION, decline={'kind': 'text', 'value': 'declined'})
    plan = replace(PLAN, windows=(replace(PLAN.windows[0], question=invalid), PLAN.windows[1]))
    world = make_world(kernel_engine, (plan,), registry=SCHEMAS)
    k = service(kernel_engine)
    assert k.submit(1, raw(world['wire']))['errorCode'] == 'SCHEMA_INVALID'
    assert amount(kernel_engine, world['items'][1]) == Rational.of(1)


def test_reissue_cannot_edit_accepted_outcome(kernel_engine):
    world, k, first, d = start(kernel_engine)
    k.submit(1, raw(answer(world, d)))
    wire = operator_wire(world, k, 'ReissueDecision', actionId=first['operationId'], decisionId=d.id,
                         expectedDecisionVersion=0, deadlineSeconds=120)
    with pytest.raises(ContractViolation, match='DECISION_STALE'):
        k.submit(1, raw(wire))
    with k.store.transaction(world['scope']) as tx:
        assert tx.answers(first['operationId'])['question:hit']['value'] is True


def test_response_on_another_worker_preserves_execution_lease(kernel_engine):
    world, original, first, d = start(kernel_engine)
    with original.store.transaction(world['scope']) as tx:
        owner, fence = tx.scope.lease_owner, tx.scope.fence_epoch
    other = service(kernel_engine, worker_id='worker:response')
    result = other.submit(1, raw(answer(world, d)))
    assert result['status'] == 'committed'
    with original.store.transaction(world['scope']) as tx:
        assert (tx.scope.lease_owner, tx.scope.fence_epoch) == (owner, fence)
    # The execution worker reads the accepted answer from the retained frame.
    original.prepare = lambda tx, action, window, fuel: Prepared({'answer': tx.answers(action.id)})
    done = original.advance(world['scope'], first['operationId'], window_index=1, fence=fence)
    assert done['status'] == 'COMPLETED'
    assert done['outcome']['result']['answer']['question:hit']['value'] is True


@pytest.mark.parametrize('operation', ['ReissueDecision', 'AdjustResource'])
def test_operator_intervention_on_another_worker_does_not_steal_lease(kernel_engine, operation):
    world, original, first, d = start(kernel_engine)
    other = service(kernel_engine, worker_id='worker:operator')
    with original.store.transaction(world['scope']) as tx:
        owner, fence = tx.scope.lease_owner, tx.scope.fence_epoch
    if operation == 'ReissueDecision':
        wire = operator_wire(world, other, operation, actionId=first['operationId'], decisionId=d.id,
                             expectedDecisionVersion=0, deadlineSeconds=120)
    else:
        wire = envelope(world, operation, {'instance': world['wire']['payload']['sourceInstance'],
            'resourceId': 'charges', 'delta': Quantity(Rational.of(1), 'unit:point').to_wire(),
            'reason': 'operator correction'}, 1)
    assert other.submit(1, raw(wire))['status'] == 'committed'
    with original.store.transaction(world['scope']) as tx:
        assert (tx.scope.lease_owner, tx.scope.fence_epoch) == (owner, fence)
        assert tx.decision(d.id, 0).wire['status'] == 'invalidated'


@pytest.mark.parametrize('via_response', [False, True])
def test_heartbeat_gap_before_deadline_does_not_discard_valid_question(kernel_engine, via_response):
    clock = [NOW]
    world, k, first, d = start(kernel_engine, clock=lambda: clock[0])
    clock[0] = NOW + timedelta(seconds=91)  # beyond 30 + 30 tolerance, before the 120s deadline
    if not via_response:
        tick(k, world, clock, 91)
        with k.store.transaction(world['scope']) as tx:
            assert tx.decision(d.id).wire['status'] == 'open'
    assert k.submit(1, raw(answer(world, d)))['status'] == 'committed'
    assert state(kernel_engine, world, first['operationId'])[0] == 'ACTIVE'


def _crash_response_process(url, wire, stage):
    engine = create_engine(url)
    def crash(point):
        if point == stage:
            os._exit(23)
    k = service(engine, worker_id=f'worker:crash-{os.getpid()}', fault=crash)
    k.submit(1, raw(wire))
    os._exit(24)  # the requested crash boundary must have been reached


@pytest.mark.parametrize('stage', ['before_commit', 'after_commit'])
def test_process_death_during_answer_recovers_one_retained_outcome(kernel_engine, stage):
    world, original, first, d = start(kernel_engine)
    wire = answer(world, d)
    ctx = multiprocessing.get_context('spawn')
    process = ctx.Process(target=_crash_response_process,
        args=(kernel_engine.url.render_as_string(hide_password=False), wire, stage))
    process.start()
    process.join(timeout=40)
    try:
        assert not process.is_alive(), 'response process did not reach its crash boundary'
        assert process.exitcode == 23
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
    with original.store.transaction(world['scope']) as tx:
        stored = tx.decision(d.id)
        if stage == 'before_commit':
            assert stored.wire['status'] == 'open' and stored.answer is None
            assert tx.receipt(1, wire['idempotencyKey']) is None
        else:
            assert stored.wire['status'] == 'answered'
            assert tx.receipt(1, wire['idempotencyKey'])['status'] == 'committed'
    recovered = service(kernel_engine, worker_id='worker:recovery')
    result = recovered.submit(1, raw(wire))
    assert result['status'] == 'committed'
    assert recovered.submit(1, raw({**wire, 'commandId': 'cmd:recovered-response'})) == result
    with recovered.store.transaction(world['scope']) as tx:
        assert tx.intervention_index(first['operationId']) == -2
        assert tx.answers(first['operationId']) == {'question:hit': {'kind': 'boolean', 'value': True}}
        assert tx.action(first['operationId']).state == 'ACTIVE'
    assert amount(kernel_engine, world['items'][1]) == Rational.of(0)
