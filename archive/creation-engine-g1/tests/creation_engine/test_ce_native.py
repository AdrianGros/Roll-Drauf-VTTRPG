"""WP8 authored revisions through real sandbox, resource, decision and RNG ports."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vtt.creation_engine.adapter import mapping
from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.compiler import runtime as native
from vtt.creation_engine.content import create_revision, new_id
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.runtime_models import CeAction, CeCheckpoint, CeRandomRecord
from vtt.creation_engine.transports.legacy_host import build_gateway
from vtt.creation_engine.units import Quantity

from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_authoring import authoring_engine, author, preset, submit, wire

pytestmark = pytest.mark.postgres


class FixedRandom:
    algorithm_id = "test-fixed-3"
    def __init__(self):
        self.draws = 0
    def randrange(self, start, stop):
        self.draws += 1
        return 3


def native_world(author, *, damage=False):
    a = dict(author)
    a["gateway"] = g = build_gateway(author["gateway"].store.engine, native_authoring=True)
    a["service"] = g.authoring
    g.kernel.random = FixedRandom()
    g.kernel.random_algorithm = g.kernel.random.algorithm_id
    preset(a, "g1.post-hit-flames" if damage else "g1.harmless-flames")
    _, result = submit(a, "CommitDraftRevision", {"declaredQuality": "runtime_ready", "definition": {"kind": "new"}})
    a["revision"] = result["revision"]
    # Explicit test fixture for an already imported RDL actor, not a product default.
    with Session(g.store.engine) as session, session.begin():
        content = ContentStore(session); now = g.store.now(session)
        definition = content.add_definition(a["workspace"], "Imported target fixture", mapping.CHARACTER_TYPE.type_id, now=now)
        values = {key: Quantity(Rational.of(30 if key == 'hp_max' else 4 if key == 'fokus_max' else 10),
                               g.kernel.ruleset.binding(key).unit).to_wire() for key in mapping.BINDINGS.values()}
        revision = create_revision(definition.id, mapping.CHARACTER_TYPE, {
            "name": "Imported target fixture", "bases": values, "selections": {}, "provenance": "imported_legacy_baseline",
            "legacyMetadata": {"character": {"hp_current": 20, "mana_current": 2, "character_data": {}}}},
            registry=g.kernel.schema_registry, author_user_id=a['principal'], now=now, provenance={"kind": "test_fixture"})
        content.append_revision(revision); a["actorRevision"] = revision.ref().to_wire()
    command = {**wire(a, "CreateDraft", {}), "operation": "CreateSandboxScope", "payload": {
        "ruleset": g.kernel.ruleset.artifact(), "revisions": [a["revision"], a["actorRevision"]]}}
    result = g.submit(a["principal"], canonical_bytes(command))
    a["scope"] = result["scopeId"]
    a["actor"] = instantiate(a, a["actorRevision"])
    a["target"] = instantiate(a, a["actorRevision"])
    a["item"] = instantiate(a, a["revision"], holder=a["actor"])
    mechanical(a, "SetItemEquipped", {"item": ref(a, a["item"]), "equipped": True})
    return a


def ref(a, instance):
    return {"kind": "instance", "id": instance, "scopeId": a["scope"]}


def mechanical_wire(a, operation, payload):
    with a["gateway"].store.transaction(a["scope"]) as tx:
        return {"contractVersion": "1.1.3", "commandId": new_id("cmd"), "idempotencyKey": new_id("key"),
            "scopeId": a["scope"], "expectedScopeVersion": tx.scope.state_version, "authorityEpoch": tx.scope.authority_epoch,
            "executionLockDigest": tx.lock.digest, "operation": operation, "payload": payload}


def mechanical(a, operation, payload):
    return a["gateway"].submit(a["principal"], canonical_bytes(mechanical_wire(a, operation, payload)))


def instantiate(a, revision, holder=None):
    result = mechanical(a, "InstantiateRevision", {"revision": revision, "holder": ref(a, holder) if holder else None, "reason": "Sandbox fixture copy"})
    return a["gateway"].outcome(a["principal"], a["scope"], result["operationId"])["fields"]["outcome"]["instanceId"]


def invoke(a, activity, *, item=None, target=None):
    return mechanical(a, "InvokeActivity", {"actorInstance": ref(a, a["actor"]), "sourceInstance": ref(a, item or a["item"]),
        "activityRevisionRef": a["revision"], "activityId": activity, "targets": [ref(a, target)] if target else []})


def fields(a, instance):
    return a["gateway"].read(a["principal"], a["scope"], instance)["fields"]


def resolve_wire(a, value):
    with a["gateway"].store.transaction(a["scope"]) as tx:
        decision = tx.open_decisions()[0]
        payload = {"decisionId": decision.id, "actionId": decision.wire["actionId"], "expectedDecisionVersion": decision.version,
                   "contextToken": decision.wire["contextToken"], "answer": {"kind": "boolean", "value": value}}
    return mechanical_wire(a, "ResolveDecision", payload)


def test_native_cosmetic_flames_have_independent_charges_and_no_damage(author):
    a = native_world(author)
    other = instantiate(a, a["revision"], holder=a["actor"])
    for _ in range(3):
        assert invoke(a, native.ACTIVATE)["status"] == "committed"
    assert fields(a, a["item"])["charges"] == 0 and fields(a, other)["charges"] == 3
    assert fields(a, a["target"])["hp_current"] == 20 and a["gateway"].kernel.random.draws == 0
    failed = invoke(a, native.ACTIVATE)
    assert failed["status"] == "rejected" and failed["errorCode"] == "RESOURCE_BOUND_EXCEEDED"
    assert invoke(a, native.RECOVER + "long_rest")["status"] == "committed"
    assert fields(a, a["item"])["charges"] == 3


@pytest.mark.parametrize("accept", [False, True])
def test_committed_hit_optional_child_is_explicit_and_atomic(author, accept):
    a = native_world(author, damage=True)
    hit = invoke(a, native.HIT, target=a["target"])
    assert hit["status"] == "committed" and fields(a, a["item"])["charges"] == 3
    command = resolve_wire(a, accept)
    a["gateway"].submit(a["principal"], canonical_bytes(command))
    assert fields(a, a["item"])["charges"] == (2 if accept else 3)
    assert fields(a, a["target"])["hp_current"] == (14 if accept else 20)
    assert a["gateway"].kernel.random.draws == (2 if accept else 0)
    with a["gateway"].store.transaction(a["scope"]) as tx:
        assert tx.action(hit["operationId"]).state == "COMPLETED" and tx.scope.active_action_id is None
        assert tx.checkpoint(hit["operationId"], 0)["outcome"]["result"]["hitConfirmed"] is True
        children = list(tx.session.scalars(select(CeAction).where(CeAction.parent_id == hit["operationId"])))
        assert len(children) == int(accept)
        if accept:
            checkpoint = tx.checkpoint(children[0].id, 0)
            assert len(checkpoint["outcome"]["changes"]) == 2 and len(checkpoint["outcome"]["rolls"]) == 1
            child_id = children[0].id
    if accept:
        roll = a['gateway'].outcome(a['principal'], a['scope'], child_id)['fields']['outcome']['rolls'][0]
        assert roll['raw'] == [3, 3] and roll['algorithm'] == FixedRandom.algorithm_id


def test_direct_child_or_unequipped_item_cannot_bypass_hit(author):
    a = native_world(author, damage=True)
    assert invoke(a, native.DAMAGE, target=a["target"])["status"] == "rejected"
    mechanical(a, "SetItemEquipped", {"item": ref(a, a["item"]), "equipped": False})
    assert invoke(a, native.HIT, target=a["target"])["status"] == "rejected"
    assert a["gateway"].kernel.random.draws == 0 and fields(a, a["item"])["charges"] == 3


@pytest.mark.parametrize("stage", ["after_draw", "after_commit"])
def test_child_crash_recovery_never_repeats_committed_cost_or_roll(author, stage):
    a = native_world(author, damage=True)
    invoke(a, native.HIT, target=a["target"])
    command = resolve_wire(a, True)
    kernel = a["gateway"].kernel
    armed = True
    def fault(point):
        nonlocal armed
        # after_commit of ResolveDecision precedes drawing the child; wait for
        # the child draw so this exercises the intended durability boundary.
        if armed and point == stage and kernel.random.draws:
            armed = False
            raise RuntimeError("simulated child process failure")
    kernel.fault = fault
    with pytest.raises(RuntimeError):
        a["gateway"].submit(a["principal"], canonical_bytes(command))
    kernel.fault = lambda point: None
    a["gateway"].submit(a["principal"], canonical_bytes(command))
    assert fields(a, a["item"])["charges"] == 2 and fields(a, a["target"])["hp_current"] == 14
    with a["gateway"].store.transaction(a["scope"]) as tx:
        assert tx.scope.active_action_id is None
        rolls = list(tx.session.scalars(select(CeRandomRecord).join(CeCheckpoint).where(CeCheckpoint.scope_id == a["scope"])))
        assert len(rolls) == 1
    assert kernel.random.draws == (4 if stage == "after_draw" else 2)


def test_lock_membership_and_current_scope_owner_are_required(author):
    a = native_world(author)
    wrong = {**a["revision"], "digest": "sha256:" + "0" * 64}
    with pytest.raises(ContractViolation, match="REVISION_NOT_IN_LOCK"):
        instantiate(a, wrong)
    command = mechanical_wire(a, "InstantiateRevision", {"revision": a["revision"], "holder": None, "reason": "foreign owner"})
    with pytest.raises(ContractViolation):
        a["gateway"].submit(1, canonical_bytes(command))


def test_worker_finishes_explicit_optional_timeout_without_spending(author):
    from datetime import timedelta
    from vtt.creation_engine.store.maintenance import tick
    a = native_world(author, damage=True)
    invoke(a, native.HIT, target=a['target'])
    with a['gateway'].store.transaction(a['scope']) as tx:
        now = tx.now
    clock = [now]
    a['gateway'].store.clock = lambda: clock[0]
    for _ in range(5):
        clock[0] += timedelta(seconds=30)
        tick(a['gateway'])
    assert fields(a, a['item'])['charges'] == 3 and fields(a, a['target'])['hp_current'] == 20
    with a['gateway'].store.transaction(a['scope']) as tx:
        assert tx.scope.active_action_id is None and not tx.open_decisions()
    assert a['gateway'].kernel.random.draws == 0


def test_native_event_is_hidden_when_an_involved_source_loses_read_permission(author):
    from dataclasses import replace
    from vtt.creation_engine.policy import Grant
    from vtt.creation_engine.store.runtime_models import CeDomainEvent
    a = native_world(author)
    result = invoke(a, native.ACTIVATE)
    g = a['gateway']
    with g.store.transaction(a['scope']) as tx:
        policy = g.policy.policies(tx).policies[a['item']]
        g.policy.replace(tx, g.kernel, a['principal'], replace(policy, denies=(Grant('read', principals=(a['principal'],)),)),
            expected_version=tx.scope.policy_version, reason='Private test revocation')
    with g.store.transaction(a['scope']) as tx:
        actor = g.policy.require_scope(tx, a['principal'])
        event = tx.session.get(CeDomainEvent, result['eventIds'][0])
        assert g._event(tx, (actor,), event) is None


def test_native_calculation_requires_explicit_engine_compute_grant(author):
    from dataclasses import replace
    from vtt.creation_engine.policy import Grant
    a = native_world(author)
    g = a['gateway']
    with g.store.transaction(a['scope']) as tx:
        policy = g.policy.policies(tx).policies[a['item'] + ':private']
        g.policy.replace(tx, g.kernel, a['principal'], replace(policy, denies=(Grant('compute', roles=('engine',)),)),
            expected_version=tx.scope.policy_version, reason='Decline automated computation')
    result = invoke(a, native.ACTIVATE)
    assert result['status'] == 'rejected' and result['errorCode'] == 'OPERATION_FORBIDDEN'
    assert fields(a, a['item'])['charges'] == 3


def test_fixture_campaign_requires_separate_explicit_deploy_capability(author):
    from dataclasses import replace
    from vtt.creation_engine.policy import Grant
    from vtt.creation_engine.store.runtime_models import CeRuntimeScope
    from vtt.models.campaign import Campaign
    a = native_world(author)
    g = a['gateway']
    # Trusted fixture provisioning. No public operation converts sandbox scope.
    with Session(g.store.engine) as session, session.begin():
        campaign = Campaign(name='Native campaign fixture', owner_id=a['principal'])
        session.add(campaign); session.flush()
        scope = session.get(CeRuntimeScope, a['scope'])
        scope.kind, scope.campaign_id, scope.fixture = 'campaign', campaign.id, True
    with pytest.raises(ContractViolation, match='OPERATION_FORBIDDEN'):
        instantiate(a, a['revision'])
    with g.store.transaction(a['scope']) as tx:
        policy = g.policy.policies(tx).policies[tx.scope.id]
        g.policy.replace(tx, g.kernel, a['principal'], replace(policy, grants=(*policy.grants, Grant('deploy', principals=(a['principal'],)))),
                         expected_version=tx.scope.policy_version, reason='Fixture deployment approval')
    assert instantiate(a, a['revision'])
    with Session(g.store.engine) as session, session.begin():
        session.get(CeRuntimeScope, a['scope']).fixture = False
    with pytest.raises(ContractViolation):
        instantiate(a, a['revision'])


def test_revision_compiler_and_registry_identity_are_checked_before_execution(author):
    from dataclasses import replace
    from vtt.creation_engine.canonical import parse_strict_json
    a = native_world(author)
    with Session(a['gateway'].store.engine) as session:
        revision = ContentStore(session).revision(a['revision']['id'])
    assert native.runtime_content(revision)['behavior'] == 'visual'
    for field in ('registry', 'compilerVersion', 'questions'):
        provenance = parse_strict_json(revision.provenance)
        provenance[field] = 'unreviewed-version'
        changed = replace(revision, provenance=canonical_bytes(provenance))
        with pytest.raises(ContractViolation, match='AUTHORING_REGISTRY_MISMATCH'):
            native.resolve_activity(changed, native.ACTIVATE)


def test_sandbox_summary_uses_the_public_error_allowlist(author):
    a = native_world(author, damage=True)
    result = invoke(a, native.HIT, target=a['target'])
    with a['gateway'].store.transaction(a['scope']) as tx:
        action = tx.action(result['operationId'])
        action.error_code = 'private-diagnostic-identifier'
        tx.save_action(action)
    summary = a['gateway'].kernel.native.summary(a['gateway'], a['principal'], a['scope'])
    assert summary['activeAction']['errorCode'] == 'SEMANTIC_INVALID'
