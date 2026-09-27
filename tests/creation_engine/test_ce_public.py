"""WP6 PostgreSQL proofs: current authority, private curse, cursors and View As."""

from dataclasses import replace
from datetime import timedelta
import multiprocessing

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.policy import Document, Field, Grant, Policy
from vtt.creation_engine.store.policy import PolicyStore
from vtt.creation_engine.store.public import PublicGateway
from vtt.creation_engine.store.policy_models import (CePolicy, CePolicyEpoch, CeSecurityAudit,
    CeSubscription, CeViewAsSession, POLICY_TABLES)
from vtt.creation_engine.store.runtime_models import CeInstance, CeRuntimeScope
from vtt.models import Campaign, CampaignMember, User

from test_ce_content_store import postgres_engine
from test_ce_kernel import kernel_engine, make_world, NOW, raw, M74
from test_ce_decisions import PLAN, SCHEMAS, service, answer, operator_wire
from test_ce_policy import RULE, OPEN, curse
from test_ce_evaluator import app as effect, defense, lit, result as evaluate_fixture

pytestmark = pytest.mark.postgres
CONFIGURATION = {"declassifications": [RULE.wire()]}


@pytest.fixture(scope="module")
def public_engine(kernel_engine):
    with kernel_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M74.with_name("migration_m76_creation_engine_policy.sql").read_text())
        for i in (2, 3):
            connection.execute(text("INSERT INTO users (id, username, email, password_hash, role_id, is_active, is_suspended, account_state) "
                "VALUES (:id, :name, :email, 'x', 1, true, false, 'active')"),
                {"id": i, "name": f"policy{i}", "email": f"policy{i}@example.test"})
    return kernel_engine


def document(tx, object_id):
    if object_id == "sheet:hero":
        # F-CURSE uses the actual evaluator, not a fake total.
        value = evaluate_fixture([effect("effect:secret", "rdl.defense", "ADD", lit(-1))], bindings=[defense(13)]).value.to_wire()
        base = curse()
        return replace(base, fields={**base.fields,
            "name": Field("Hero " + tx.scope.id, "policy:sheet"),
            "defense": replace(base.fields["defense"], value=value)})
    if object_id == "curse:secret":
        return Document(object_id, "policy:curse", {"name": Field("Secret curse", "policy:curse")})
    return None


def event_document(tx, event):
    policy_id = "policy:curse" if event["kind"] == "secret_event" else "policy:sheet"
    return Document(event["eventId"], policy_id, {"kind": Field(event["kind"], policy_id)})


def gateway_for(engine, *, clock=None, declassify=True, worker_id="worker:public"):
    k = service(engine, clock=clock, worker_id=worker_id, configuration=CONFIGURATION if declassify else {},
                responders=lambda tx, rule, action: [2] if rule == "responders:owner" else [1])
    return PublicGateway(k, PolicyStore(), document=document,
        snapshot_documents=lambda tx: (document(tx, "sheet:hero"), document(tx, "curse:secret")),
        event_document=event_document, outcome_document=lambda tx, action, outcome:
            Document(action.id, "policy:sheet", {"note": Field(outcome.get("outcomeNote", "Resolved"), "policy:sheet")}),
        configuration=CONFIGURATION if declassify else {}, declassifications=(RULE,) if declassify else ())


def build_world(engine, *, declassify=True, clock=None):
    world = make_world(engine, (PLAN,), registry=SCHEMAS, configuration=CONFIGURATION if declassify else {})
    with Session(engine) as session, session.begin():
        campaign = Campaign(name="WP6 fixture", owner_id=1, status="active")
        session.add(campaign)
        session.flush()
        for i in (2, 3):
            session.add(CampaignMember(campaign_id=campaign.id, user_id=i, campaign_role="Player", status="active"))
        scope = session.get(CeRuntimeScope, world["scope"])
        scope.kind, scope.campaign_id = "campaign", campaign.id
        for row in session.scalars(select(CeInstance).where(CeInstance.scope_id == scope.id)):
            row.controller_user_id = 2
        world["campaign"] = campaign.id
    gateway = gateway_for(engine, clock=clock, declassify=declassify)
    with gateway.store.transaction(world["scope"]) as tx:
        gateway.policy.bootstrap(tx, 1)
        for p in (Policy("policy:sheet", world["scope"], OPEN),
                  Policy("policy:private", world["scope"], OPEN + (Grant("respond", principals=(2,)),)),
                  Policy("policy:curse", world["scope"], OPEN, owner_id=1, owner_grants=(Grant("compute", roles=("engine",)),))):
            gateway.policy.replace(tx, gateway.kernel, 1, p, expected_version=tx.scope.policy_version, reason="fixture policy")
        # Owner-approved fixture installation, not a GM manufacturing private grants.
        p = Policy("policy:owner", world["scope"], OPEN, owner_id=2)
        tx.session.add(CePolicy(scope_id=tx.scope.id, policy_id=p.id, version=tx.scope.policy_version, canonical=canonical_bytes(p.wire())))
        world["wire"]["expectedScopeVersion"] = tx.scope.state_version
    return world, gateway


@pytest.fixture
def public_world(public_engine):
    return build_world(public_engine)


def pending(world, gateway):
    first = gateway.submit(2, raw(world["wire"]))
    with gateway.store.transaction(world["scope"]) as tx:
        return first, tx.open_decisions()[0]


@pytest.mark.parametrize("operation", ["read", "explain", "export"])
def test_t22_real_curse_evaluation_across_output_modes(public_world, operation):
    world, g = public_world
    value = g.read(2, world["scope"], "sheet:hero", operation=operation)
    assert value["fields"]["defense"]["value"] == {"numerator": 12, "denominator": 1}
    for secret in (b"Secret curse", b"effect:secret", b"private.invalid", b"sha256:"):
        assert secret not in canonical_bytes(value)


def test_without_reviewed_declassification_final_value_is_withheld(public_engine):
    world, g = build_world(public_engine, declassify=False)
    assert "defense" not in g.read(2, world["scope"], "sheet:hero")["fields"]


def test_t23_gm_cache_player_other_scope_and_epoch_separation(public_engine, public_world):
    world, g = public_world
    assert "sourceName" in g.read(1, world["scope"], "sheet:hero")["fields"]
    player = g.read(2, world["scope"], "sheet:hero")
    assert "sourceName" not in player["fields"]
    other, _ = build_world(public_engine)
    assert g.read(2, other["scope"], "sheet:hero")["fields"]["name"] != player["fields"]["name"]
    with g.store.transaction(world["scope"]) as tx:
        old = g.policy.policies(tx).policies["policy:sheet"]
        g.policy.replace(tx, g.kernel, 1, replace(old, denies=(Grant("read", principals=(2,)),)),
                         expected_version=tx.scope.policy_version, reason="revoke sheet")
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.read(2, world["scope"], "sheet:hero")


def test_t24_view_as_intersection_expiry_audit_and_mutation_refusal(public_engine):
    clock = [NOW]
    world, g = build_world(public_engine, clock=lambda: clock[0])
    view = g.enter_view(1, world["scope"], 2)
    value = g.read(1, world["scope"], "sheet:hero", view_id=view["viewAsId"])
    assert "privateNote" not in value["fields"] and "sourceName" not in value["fields"]
    with pytest.raises(ContractViolation, match="OPERATION_FORBIDDEN"):
        g.submit(1, raw(world["wire"]), view_id=view["viewAsId"])
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.read(2, world["scope"], "sheet:hero", view_id=view["viewAsId"])
    clock[0] += timedelta(minutes=15)
    with pytest.raises(ContractViolation, match="OPERATION_FORBIDDEN"):
        g.read(1, world["scope"], "sheet:hero", view_id=view["viewAsId"])
    g.maintain(world["scope"])
    with Session(public_engine) as session:
        assert session.get(CeViewAsSession, view["viewAsId"]).closed_at is not None
        kinds = list(session.scalars(select(CeSecurityAudit.kind).where(CeSecurityAudit.scope_id == world["scope"])))
        assert kinds.count("view_as_entered") == kinds.count("view_as_exited") == 1


def test_t47_public_decision_receipt_and_lost_ack_retry(public_world):
    world, g = public_world
    first, d = pending(world, g)
    assert "outcomeDigest" not in first
    visible = g.decision(2, world["scope"], d.id)
    assert visible["contextToken"] == d.wire["contextToken"]
    assert d.context_digest.encode() not in canonical_bytes(visible)
    wire = answer(world, d)
    result = g.submit(2, raw(wire))
    assert g.submit(2, raw({**wire, "commandId": "cmd:retry"})) == result
    assert g.receipt(2, world["scope"], wire["idempotencyKey"]) == result
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.receipt(1, world["scope"], wire["idempotencyKey"])


def test_view_as_cannot_obtain_response_tokens(public_world):
    world, g = public_world
    _, d = pending(world, g)
    view = g.enter_view(1, world["scope"], 2)
    assert "contextToken" not in g.decision(1, world["scope"], d.id, view_id=view["viewAsId"])


def test_t25_coordinated_revocation_invalidates_prompt_subscription_view_and_receipt(public_engine, public_world):
    world, g = public_world
    first, d = pending(world, g)
    sub = g.subscribe(2, world["scope"], "connection:a", contract_version="1.1.3", authority_epoch=1)
    view = g.enter_view(1, world["scope"], 2)
    with g.store.transaction(world["scope"]) as tx:
        member = tx.session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == world["campaign"], CampaignMember.user_id == 2))
        member.status = "kicked"
        g.policy.changed(tx, g.kernel, 1, reason="membership revoked", entitlement_principal=2)
    sent = []
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.poll(2, world["scope"], sub["subscriptionId"], sub["cursor"], "connection:a", deliver=sent.append)
    assert sent == []
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.receipt(2, world["scope"], world["wire"]["idempotencyKey"])
    with g.store.transaction(world["scope"]) as tx:
        assert tx.decision(d.id).wire["status"] == "invalidated"
        assert tx.action(first["operationId"]).state == "SUSPENDED"
        assert tx.scope.active_action_id == first["operationId"]
        assert tx.session.get(CeSubscription, sub["subscriptionId"]).revoked_at is not None
        assert tx.session.get(CeViewAsSession, view["viewAsId"]).closed_at is not None
        assert tx.session.get(CePolicyEpoch, (world["scope"], 2)).entitlement_epoch == 1


def test_maintenance_does_not_invalidate_a_scope_with_different_pinned_registrations(public_engine):
    from vtt.creation_engine.store.maintenance import tick
    world, other = build_world(public_engine, declassify=False)
    _, d = pending(world, other)
    g = gateway_for(public_engine)
    tick(g)
    with other.store.transaction(world["scope"]) as tx:
        assert tx.decision(d.id).wire["status"] == "open"


@pytest.mark.parametrize("change", ["membership", "account", "entitlement", "authority"])
def test_every_delivery_revalidates_current_access(public_engine, public_world, change):
    world, g = public_world
    sub = g.subscribe(2, world["scope"], "connection:a", contract_version="1.1.3", authority_epoch=1)
    with Session(public_engine) as session, session.begin():
        if change == "membership":
            member = session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == world["campaign"], CampaignMember.user_id == 2))
            member.status = "left"
        elif change == "account":
            session.get(User, 2).is_suspended = True
        elif change == "entitlement":
            session.add(CePolicyEpoch(scope_id=world["scope"], principal_id=2, entitlement_epoch=7))
        else:
            session.get(CeRuntimeScope, world["scope"]).authority_epoch += 1
    try:
        with pytest.raises(ContractViolation, match="NOT_FOUND"):
            g.poll(2, world["scope"], sub["subscriptionId"], sub["cursor"], "connection:a")
    finally:
        if change == "account":
            with Session(public_engine) as session, session.begin():
                session.get(User, 2).is_suspended = False


def test_t08_stream_replay_private_events_and_cursor_recovery(public_world):
    world, g = public_world
    first, _ = pending(world, g)
    sub = g.subscribe(2, world["scope"], "connection:a", contract_version="1.1.3", authority_epoch=0)
    assert sub["refresh"] is True
    with g.store.transaction(world["scope"]) as tx:
        a = tx.action(first["operationId"])
        hidden = tx.event(a, "secret_event")
        visible = tx.event(a, "public_event")
    page = g.poll(2, world["scope"], sub["subscriptionId"], sub["cursor"], "connection:a")
    assert [e["eventId"] for e in page["events"]] == [visible]
    assert hidden.encode() not in canonical_bytes(page)
    for secret in (b'"sequence"', b'"outcomeDigest"', b'"executionLockDigest"', b'"causationId"', b'"policyVersion"'):
        assert secret not in canonical_bytes(page)
    replay = g.poll(2, world["scope"], sub["subscriptionId"], sub["cursor"], "connection:a")
    assert replay["events"] == page["events"]
    recovered = g.poll(2, world["scope"], sub["subscriptionId"], "cursor:stale", "connection:a")
    assert recovered["refresh"] and recovered["snapshot"]["objects"][0]["fields"]["defense"]["value"]["numerator"] == 12
    other = g.subscribe(3, world["scope"], "connection:b", contract_version="1.1.3", authority_epoch=1)
    assert g.poll(3, world["scope"], other["subscriptionId"], page["cursor"], "connection:b")["refresh"]
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.poll(3, world["scope"], sub["subscriptionId"], page["cursor"], "connection:a")


def test_hidden_search_candidates_do_not_affect_ranking_or_counts(public_world):
    world, g = public_world
    assert g.search(2, world["scope"], "Secret") == {"items": [], "total": 0}
    assert g.search(1, world["scope"], "Secret")["total"] == 1


def test_operator_cannot_manufacture_owner_private_grants(public_world):
    world, g = public_world
    with g.store.transaction(world["scope"]) as tx:
        p = Policy("policy:new-private", tx.scope.id, OPEN, owner_id=2,
                   owner_grants=(Grant("policy_admin", principals=(1,)), Grant("read", principals=(1,))))
        with pytest.raises(ContractViolation, match="OPERATION_FORBIDDEN"):
            g.policy.replace(tx, g.kernel, 1, p, expected_version=tx.scope.policy_version, reason="attempt")


def test_t50_manual_labels_on_outcome_export_and_event(public_world):
    world, g = public_world
    first, d = pending(world, g)
    with g.store.transaction(world["scope"]) as tx:
        g.policy.changed(tx, g.kernel, 1, reason="request operator ruling")
    sub = g.subscribe(2, world["scope"], "connection:a", contract_version="1.1.3", authority_epoch=1)
    wire = operator_wire(world, g.kernel, "ResolveActionManually", actionId=first["operationId"],
                         adjustments=[], reason="table ruling", outcomeNote="Resolved manually")
    g.submit(1, raw(wire))
    for mode in ("read", "explain", "export"):
        outcome = g.outcome(2, world["scope"], first["operationId"], operation=mode)
        assert outcome["manual"] and outcome["automatedCompletion"] is False
    page = g.poll(2, world["scope"], sub["subscriptionId"], sub["cursor"], "connection:a")
    assert page["events"][0]["data"]["manual"] is True


def test_m76_matches_models_and_reapplies(public_engine):
    inspector = inspect(public_engine)
    for table in POLICY_TABLES:
        assert {c["name"] for c in inspector.get_columns(table.name)} == {c.name for c in table.columns}
    with public_engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            cursor.execute(M74.with_name("migration_m76_creation_engine_policy.sql").read_text())


@pytest.mark.parametrize("table", ["ce_policies", "ce_security_audit", "ce_public_receipt_requests"])
def test_policy_audit_and_request_history_are_database_immutable(public_engine, public_world, table):
    world, g = public_world
    pending(world, g)
    with public_engine.connect() as connection:
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(text(f"DELETE FROM {table} WHERE scope_id = :scope"), {"scope": world["scope"]})


def _delivery_worker(url, world, subscription, entered, release, results):
    g = gateway_for(create_engine(url), worker_id="worker:delivery")
    def send(value):
        entered.set()
        if not release.wait(20):
            raise RuntimeError("test delivery was not released")
        results.put("delivered")
    g.poll(2, world["scope"], subscription["subscriptionId"], subscription["cursor"], "connection:a", deliver=send)


def _revocation_worker(url, world, ready, results):
    g = gateway_for(create_engine(url), worker_id="worker:revocation")
    ready.set()
    with g.store.transaction(world["scope"]) as tx:
        member = tx.session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == world["campaign"], CampaignMember.user_id == 2))
        member.status = "kicked"
        g.policy.changed(tx, g.kernel, 1, reason="competing revocation")
    results.put("revoked")


def test_t25_competing_processes_order_delivery_and_revocation(public_engine, public_world):
    world, g = public_world
    sub = g.subscribe(2, world["scope"], "connection:a", contract_version="1.1.3", authority_epoch=1)
    ctx = multiprocessing.get_context("spawn")
    entered, release, ready, results = ctx.Event(), ctx.Event(), ctx.Event(), ctx.Queue()
    url = public_engine.url.render_as_string(hide_password=False)
    deliver = ctx.Process(target=_delivery_worker, args=(url, world, sub, entered, release, results))
    revoke = ctx.Process(target=_revocation_worker, args=(url, world, ready, results))
    deliver.start()
    try:
        assert entered.wait(20)
        revoke.start()
        assert ready.wait(20)
        release.set()
        assert [results.get(timeout=20), results.get(timeout=20)] == ["delivered", "revoked"]
        for child in (deliver, revoke):
            child.join(timeout=20)
            assert child.exitcode == 0
        with pytest.raises(ContractViolation, match="NOT_FOUND"):
            g.poll(2, world["scope"], sub["subscriptionId"], sub["cursor"], "connection:a")
    finally:
        release.set()
        for child in (deliver, revoke):
            if child.pid and child.is_alive():
                child.terminate()
                child.join(timeout=5)


@pytest.mark.parametrize("at_commit", [False, True])
def test_entitlement_expiry_rechecks_cache_and_delivery_at_commit(public_engine, at_commit):
    clock = [NOW]
    world, g = build_world(public_engine, clock=lambda: clock[0])
    with g.store.transaction(world["scope"]) as tx:
        policy = replace(g.policy.policies(tx).policies["policy:sheet"], required_entitlements=("license:fixture",))
        g.policy.replace(tx, g.kernel, 1, policy, expected_version=tx.scope.policy_version, reason="licensed fixture")
        g.policy.changed(tx, g.kernel, 1, reason="grant license", entitlement_principal=2,
                         entitlements=["license:fixture"], valid_until=NOW + timedelta(seconds=60))
    assert g.read(2, world["scope"], "sheet:hero")["fields"]["defense"]
    sub = g.subscribe(2, world["scope"], "connection:a", contract_version="1.1.3", authority_epoch=1)
    if at_commit:
        def load(tx, object_id):
            value = document(tx, object_id)
            clock[0] = NOW + timedelta(seconds=60)
            return value
        g.document = load
    else:
        clock[0] = NOW + timedelta(seconds=60)
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.read(2, world["scope"], "sheet:hero")
    sent = []
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.poll(2, world["scope"], sub["subscriptionId"], sub["cursor"], "connection:a", deliver=sent.append)
    assert sent == []


def test_projection_requires_scope_pinned_configuration(public_engine, public_world):
    world, _ = public_world
    wrong = gateway_for(public_engine, declassify=False)
    with pytest.raises(ContractViolation, match="ENGINE_UNAVAILABLE"):
        wrong.read(2, world["scope"], "sheet:hero")


def test_platform_admin_role_does_not_grant_scope_or_owner_private_rights(public_engine, public_world):
    world, g = public_world
    with Session(public_engine) as session, session.begin():
        session.get(User, 3).platform_role = "admin"
        member = session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == world["campaign"],
                                                             CampaignMember.user_id == 3))
        member.status = "left"
    try:
        with pytest.raises(ContractViolation, match="NOT_FOUND"):
            g.read(3, world["scope"], "sheet:hero")
        assert "privateNote" not in g.read(1, world["scope"], "sheet:hero")["fields"]
    finally:
        with Session(public_engine) as session, session.begin():
            session.get(User, 3).platform_role = None


def test_policy_replace_rollback_restores_epoch_prompt_and_subscription(public_world):
    world, g = public_world
    _, d = pending(world, g)
    sub = g.subscribe(2, world["scope"], "connection:a", contract_version="1.1.3", authority_epoch=1)
    with g.store.transaction(world["scope"]) as tx:
        before = tx.scope.policy_version
    with pytest.raises(RuntimeError, match="rollback"):
        with g.store.transaction(world["scope"]) as tx:
            g.policy.changed(tx, g.kernel, 1, reason="rolled back revocation", entitlement_principal=2)
            raise RuntimeError("rollback")
    with g.store.transaction(world["scope"]) as tx:
        assert tx.scope.policy_version == before
        assert tx.decision(d.id).wire["status"] == "open"
        assert tx.session.get(CeSubscription, sub["subscriptionId"]).revoked_at is None


def test_maintenance_worker_renews_fenced_heartbeat(public_engine):
    from vtt.creation_engine.store.maintenance import tick
    clock = [NOW]
    world, g = build_world(public_engine, clock=lambda: clock[0])
    first, d = pending(world, g)
    clock[0] = NOW + timedelta(seconds=30)
    tick(g)
    with g.store.transaction(world["scope"]) as tx:
        assert tx.scope.decision_heartbeat_at == clock[0]
        assert tx.decision(d.id).wire["status"] == "open"
        assert tx.scope.lease_owner == g.kernel.worker_id


def test_owner_can_explicitly_grant_private_read_without_becoming_operator(public_world):
    world, g = public_world
    assert "privateNote" not in g.read(1, world["scope"], "sheet:hero")["fields"]
    with g.store.transaction(world["scope"]) as tx:
        old = g.policy.policies(tx).policies["policy:owner"]
        changed = replace(old, owner_grants=(Grant("read", principals=(1,)),))
        g.policy.replace(tx, g.kernel, 2, changed, expected_version=tx.scope.policy_version, reason="owner shares note")
    assert g.read(1, world["scope"], "sheet:hero")["fields"]["privateNote"] == "Owner only"


@pytest.mark.parametrize("stage", ["before_commit", "after_commit"])
def test_public_receipt_authorization_record_is_atomic_with_kernel_commit(public_world, stage):
    from vtt.creation_engine.store.policy_models import CePublicReceiptRequest
    world, g = public_world
    def crash(point):
        if point == stage:
            raise RuntimeError("lost worker")
    g.kernel.fault = crash
    with pytest.raises(RuntimeError, match="lost worker"):
        g.submit(2, raw(world["wire"]))
    g.kernel.fault = lambda point: None
    key = world["wire"]["idempotencyKey"]
    with g.store.transaction(world["scope"]) as tx:
        retained = tx.session.get(CePublicReceiptRequest, (world["scope"], 2, key))
        if stage == "before_commit":
            assert retained is None and tx.receipt(2, key) is None
        else:
            assert retained is not None
    if stage == "after_commit":
        assert g.receipt(2, world["scope"], key)["status"] == "committed"


def test_expired_view_cannot_reopen_after_a_denied_read_and_clock_rollback(public_engine):
    clock = [NOW]
    world, g = build_world(public_engine, clock=lambda: clock[0])
    view = g.enter_view(1, world["scope"], 2)
    clock[0] = NOW + timedelta(minutes=15)
    with pytest.raises(ContractViolation, match="OPERATION_FORBIDDEN"):
        g.read(1, world["scope"], "sheet:hero", view_id=view["viewAsId"])
    clock[0] = NOW + timedelta(minutes=14)
    with pytest.raises(ContractViolation, match="OPERATION_FORBIDDEN"):
        g.read(1, world["scope"], "sheet:hero", view_id=view["viewAsId"])
    with g.store.transaction(world["scope"]) as tx:
        assert tx.session.get(CeViewAsSession, view["viewAsId"]).closed_at is not None


def test_personal_sandbox_delegation_requires_explicit_grants(public_engine):
    world = make_world(public_engine, (PLAN,), registry=SCHEMAS, configuration=CONFIGURATION)
    g = gateway_for(public_engine)
    with g.store.transaction(world["scope"]) as tx:
        g.policy.bootstrap(tx, 1)
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.read(2, world["scope"], "sheet:hero")
    with g.store.transaction(world["scope"]) as tx:
        root = g.policy.policies(tx).policies[world["scope"]]
        g.policy.replace(tx, g.kernel, 1, replace(root, grants=root.grants + (Grant("read", principals=(2,)),)),
                         expected_version=tx.scope.policy_version, reason="owner delegates sandbox read")
        g.policy.replace(tx, g.kernel, 1, Policy("policy:sheet", world["scope"], (Grant("read", principals=(2,)),)),
                         expected_version=tx.scope.policy_version, reason="owner shares sheet")
    assert g.read(2, world["scope"], "sheet:hero")["fields"]["name"].startswith("Hero")
    with pytest.raises(ContractViolation, match="NOT_FOUND"):
        g.submit(2, raw(world["wire"]))
