"""Command admission, scope gate, atomic checkpoints and recorded randomness.

Required trusted ports: authorize(tx, principal, command) -> literal True;
resolve_activity(revision, activity_id) -> Activity; prepare(tx, action,
window, fuel) -> Prepared. None comes from wire content. Authorization reads
current membership/grants inside the unit of work, even for duplicates. Native
resolver/preparer registrations must be versioned in the supplied locked
configuration; ordinary content cannot register or replace these functions.

All returned receipts/outcomes are INTERNAL. No Flask/Socket.IO endpoint is
registered until current-policy projection and the remaining operations exist.
"""

import copy
import secrets
from dataclasses import dataclass
from datetime import timedelta

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.content import new_id
from vtt.creation_engine.errors import ArithmeticFault, BudgetExceeded, ContractViolation
from vtt.creation_engine.evaluator.fuel import Fuel
from vtt.creation_engine.evaluator.effects import EffectApplication
from vtt.creation_engine.evaluator.identity import evaluator_artifact
from vtt.creation_engine.kernel.activity import Activity, Window
from vtt.creation_engine.kernel.records import (Action, ActionState, Command, KernelError, PRECOMMIT,
                                                charge_root, receipt, refuse)
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import parse_id
from vtt.creation_engine.units import Quantity


@dataclass(frozen=True)
class Adjustment:
    instance_id: str
    resource_id: str
    delta: Quantity
    reason: str


@dataclass(frozen=True)
class Prepared:
    result: object
    adjustments: tuple[Adjustment, ...] = ()
    effects: tuple[dict, ...] = ()


class Kernel:
    def __init__(self, store, *, ruleset, schema_registry, configuration, authorize, resolve_activity, prepare, worker_id,
                 random=None, fault=None, precommit_seconds=120, max_request_bytes=1024 * 1024):
        self.store, self.ruleset = store, ruleset
        self.schema_registry = schema_registry
        self.configuration_digest = content_digest(configuration)
        self.authorize, self.resolve_activity, self.prepare = authorize, resolve_activity, prepare
        self.worker_id = parse_id(worker_id)
        self.random = random or secrets.SystemRandom()
        self.random_algorithm = getattr(self.random, "algorithm_id", "python.secrets.SystemRandom")
        self.fault = fault or (lambda stage: None)
        if not 30 <= precommit_seconds <= 600:
            raise ValueError("precommit deadline must be within the visible 30–600 second policy range")
        self.precommit_seconds, self.max_request_bytes = precommit_seconds, max_request_bytes

    def _authorize(self, tx, principal, command):
        tx.require_usable_account(principal)
        if self.authorize(tx, principal, command.wire) is not True:
            refuse("OPERATION_FORBIDDEN")

    def _authority(self, tx, command, *, check_version):
        w, scope = command.wire, tx.scope
        if w["authorityEpoch"] != scope.authority_epoch:
            refuse("AUTHORITY_EPOCH_MISMATCH")
        if check_version and w["expectedScopeVersion"] != scope.state_version:
            refuse("SCOPE_VERSION_CONFLICT")
        if w["executionLockDigest"] != tx.lock.digest:
            refuse("EXECUTION_LOCK_MISMATCH")
        if tx.lock.wire["evaluator"] != evaluator_artifact() or tx.lock.wire["ruleset"] != self.ruleset.artifact():
            refuse("SEMANTIC_INVALID", "locked evaluator/ruleset is unavailable")
        if (tx.lock.wire["schemaBundle"] != self.schema_registry.artifact()
                or tx.lock.wire["configurationDigest"] != self.configuration_digest
                or tx.lock.wire["unitTableDigest"] != self.ruleset.units.digest()):
            refuse("EXECUTION_LOCK_MISMATCH", "installed schema/configuration/units do not match the execution lock")
        if scope.migration_state != "ENGINE" or (scope.kind == "campaign" and not scope.fixture):
            refuse("MIGRATION_STATE_CONFLICT", "G1 cannot mutate legacy or live campaign authority")

    def _invocation_source(self, tx, command):
        p = command.wire["payload"]
        actor, source = tx.instance(p["actorInstance"]), tx.instance(p["sourceInstance"])
        if source.id != actor.id and source.holder_id != actor.id:
            refuse("OPERATION_FORBIDDEN", "source occurrence is not held by the actor")
        for target in p["targets"]:
            tx.instance(target)
        revision = tx.content.revision(source.revision_id)
        if revision is None or revision.ref().to_wire() != p["activityRevisionRef"] or revision.ref() not in tx.lock.revisions:
            refuse("REVISION_NOT_IN_LOCK", "activity must come from the named source's locked revision")
        self.schema_registry.validate(revision.schema_type, revision.content)
        return revision

    def _invocation(self, tx, command):
        revision = self._invocation_source(tx, command)
        p = command.wire["payload"]
        plan = self.resolve_activity(revision, p["activityId"])
        if not isinstance(plan, Activity) or plan.id != p["activityId"]:
            refuse("SEMANTIC_INVALID", "registry did not resolve the requested activity")
        # Roundtrip both validates the typed plan and disconnects mutable caller data.
        return Activity.restore(plan.canonical())

    def submit(self, principal, raw, *, defer=False):
        return self._submit(principal, raw, defer=defer)

    def spawn_child(self, principal, raw, *, parent_action_id, checkpoint_id):
        """Server-only declared child dispatch; there are no parent IDs on client wire."""
        return self._submit(principal, raw, parent=(parent_action_id, checkpoint_id))

    def _submit(self, principal, raw, *, defer=False, parent=None):
        command = Command.parse(raw, max_bytes=self.max_request_bytes)
        w = command.wire
        if w["operation"] not in {"InvokeActivity", "AdjustResource"}:
            refuse("SEMANTIC_INVALID", "operation is not implemented by this kernel package")
        with self.store.transaction(w["scopeId"]) as tx:
            self._authorize(tx, principal, command)
            # Restore/cutover fencing applies even to an old matching retry.
            if w["authorityEpoch"] != tx.scope.authority_epoch:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            existing = tx.receipt(principal, w["idempotencyKey"])
            if existing is not None:
                if existing["requestDigest"] != command.digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                if existing["status"] == "accepted":
                    previous = tx.action(existing["operationId"])
                    if previous.state in PRECOMMIT and tx.now >= previous.deadline:
                        self._cancel(tx, previous, Command.parse(previous.request, max_bytes=self.max_request_bytes))
                        return tx.receipt(principal, w["idempotencyKey"])
                return existing
            self._authority(tx, command, check_version=True)
            if not defer and parent is None and tx.scope.active_action_id is not None:
                refuse("SCOPE_BUSY")
            plan = self._invocation(tx, command) if w["operation"] == "InvokeActivity" else Activity(
                "manual.adjust", (Window("adjust", (), (), 1),))
            if w["operation"] == "AdjustResource":
                tx.instance(w["payload"]["instance"])
            self._expire(tx)
            proposals = [tx.action(i) for i in tx.open_proposals()]
            if len(proposals) >= 100 or sum(a.principal_id == principal for a in proposals) >= 20:
                refuse("ADMISSION_LIMIT")
            action_id = new_id("action")
            action = Action(action_id, tx.scope.id, principal, command.canonical, plan.canonical(), ActionState.PROPOSED,
                            tx.now + timedelta(seconds=self.precommit_seconds), action_id)
            if parent is not None:
                parent_action = tx.action(parent[0])
                parent_plan = Activity.restore(parent_action.plan)
                if (parent_action.last_checkpoint_id != parent[1] or parent[1] is None
                        or parent_action.state not in {ActionState.ACTIVE, ActionState.WAITING_DECISION}
                        or tx.scope.active_action_id != parent_action.root_id
                        or w["operation"] != "InvokeActivity" or plan.id not in parent_plan.child_activity_ids):
                    refuse("OPERATION_FORBIDDEN", "child is not declared by the active committed parent")
                parent_wire = parse_strict_json(parent_action.request)
                if w["payload"]["actorInstance"] != parent_wire["payload"]["actorInstance"]:
                    refuse("OPERATION_FORBIDDEN", "child cannot replace its parent's actor")
                root = tx.action(parent_action.root_id)
                action.parent_id, action.root_id, action.depth = parent_action.id, root.id, parent_action.depth + 1
                try:
                    if action.depth > 16:
                        raise BudgetExceeded("child nesting exceeds depth 16")
                    ancestor = parent_action
                    while ancestor:
                        aw = parse_strict_json(ancestor.request)
                        if (Activity.restore(ancestor.plan).id, aw["payload"].get("sourceInstance")) == (plan.id, w["payload"]["sourceInstance"]):
                            raise BudgetExceeded("recursive activity/source re-entry is forbidden")
                        ancestor = tx.action(ancestor.parent_id) if ancestor.parent_id else None
                    charge_root(root, children=1, triggers=1)
                except BudgetExceeded as exc:
                    self._suspend(tx, parent_action, exc.code)
                    return {"status": "suspended", "errorCode": exc.code, "actionId": parent_action.id,
                            "checkpointId": parent_action.last_checkpoint_id}
                tx.save_action(root)
            tx.save_action(action)
            accepted = receipt(command, action.id, tx.scope, status="accepted")
            tx.save_receipt(principal, w["idempotencyKey"], accepted)
            if not defer:
                self._activate(tx, action, command)
            result = tx.receipt(principal, w["idempotencyKey"])
            self.fault("before_commit")
        self.fault("after_commit")
        return result

    def _activate(self, tx, action, command):
        if tx.scope.active_action_id not in (None, action.root_id):
            refuse("SCOPE_BUSY")
        try:
            self._authority(tx, command, check_version=True)
            self._authorize(tx, action.principal_id, command)
            if command.wire["operation"] == "InvokeActivity":
                self._invocation_source(tx, command)
            tx.claim_lease(self.worker_id)
            tx.scope.active_action_id = action.root_id
            tx.activation_deadline = action.deadline
            action.transition(ActionState.ACTIVE)
            return self._atomic_checkpoint(tx, action, command)
        except (ContractViolation, ArithmeticFault) as exc:
            if isinstance(exc, KernelError) and exc.code in {"WORKER_FENCED", "LEASE_BUSY"}:
                raise
            # ACTIVE is only in-memory until the first checkpoint succeeds.
            action.state = ActionState.PROPOSED
            action.transition(ActionState.FAILED_PRECOMMIT)
            action.error_code = getattr(exc, "code", "SEMANTIC_INVALID")
            if action.parent_id is None:
                tx.scope.active_action_id = None
                tx.release_lease = True
            else:
                self._suspend(tx, tx.action(action.parent_id), action.error_code)
            tx.save_action(action)
            failed = receipt(command, action.id, tx.scope, status="rejected", code=action.error_code)
            tx.save_receipt(action.principal_id, command.wire["idempotencyKey"], failed)
            return {"status": "failed_precommit", "errorCode": action.error_code, "checkpointId": None}

    def _atomic_checkpoint(self, tx, action, command):
        before = copy.deepcopy(action)
        try:
            with tx.checkpoint_boundary():
                return self._checkpoint(tx, action, command)
        except Exception:
            action.__dict__.clear()
            action.__dict__.update(before.__dict__)
            raise

    def _checkpoint(self, tx, action, command):
        plan = Activity.restore(action.plan)
        window = plan.windows[action.next_window]
        fuel = Fuel(window.primitive_bound)
        if command.wire["operation"] == "AdjustResource":
            p = command.wire["payload"]
            prepared = Prepared({"manual": True, "adjudicator": action.principal_id, "reason": p["reason"]},
                                (Adjustment(p["instance"]["id"], p["resourceId"], Quantity.from_wire(p["delta"]), p["reason"]),))
        else:
            prepared = self.prepare(tx, action, window, fuel)
        if not isinstance(prepared, Prepared):
            refuse("SEMANTIC_INVALID", "checkpoint preparation must return a typed mutation set")
        # Prepare every delta before writes; repeated costs use the running value.
        changes, resources = [], {}
        for cost in window.costs:
            fuel.charge()
            instance = command.wire["payload"][cost.owner + "Instance"]["id"]
            changes.append(self._change(tx, resources, instance, cost.resource_id,
                                        Quantity(-cost.amount.value, cost.amount.unit), "activity cost", spending=True))
        for adjustment in prepared.adjustments:
            fuel.charge()
            if adjustment.instance_id not in self._involved(command):
                refuse("OPERATION_FORBIDDEN", "prepared adjustment addresses an undeclared target")
            changes.append(self._change(tx, resources, adjustment.instance_id, adjustment.resource_id,
                                        adjustment.delta, adjustment.reason))
        effects, seen_effects, target_counts = [], set(), {}
        for value in prepared.effects:
            fuel.charge()
            effect = EffectApplication.from_wire(value)
            payload = command.wire["payload"]
            if (command.wire["operation"] != "InvokeActivity" or effect.origin_id != action.id
                    or effect.source_instance.to_wire() != payload["sourceInstance"]
                    or effect.source_revision.to_wire() != payload["activityRevisionRef"]
                    or effect.target.id not in self._involved(command)):
                refuse("OPERATION_FORBIDDEN", "effect is outside the declared action context")
            tx.instance(effect.target.to_wire())
            if effect.application_id in seen_effects or tx.effect_exists(effect.application_id):
                refuse("SEMANTIC_INVALID", "effect application identity is already used")
            seen_effects.add(effect.application_id)
            for change in effect.changes:
                self.ruleset.binding(change.target_binding_id)
            target_counts[effect.target.id] = target_counts.get(effect.target.id, tx.effect_count(effect.target.id)) + 1
            if target_counts[effect.target.id] > 2000:
                raise BudgetExceeded("occurrence exceeds the G1 effect application limit")
            effects.append(parse_strict_json(canonical_bytes(value)))
        root = action if action.root_id == action.id else tx.action(action.root_id)
        # Charge random work before drawing; a declared overrun exposes no draw.
        fuel.charge(sum(d.count for d in window.dice))
        charge_root(root, operations=fuel.used, events=1,
                    instances=[c["instanceId"] for c in changes] + self._involved(command))
        canonical_bytes(prepared.result)
        checkpoint_id = new_id("checkpoint")
        rolls = [{"id": d.id, "count": d.count, "sides": d.sides,
                  "raw": [self.random.randrange(1, d.sides + 1) for _ in range(d.count)],
                  "algorithm": self.random_algorithm, "checkpointId": checkpoint_id,
                  "executionLockDigest": tx.lock.digest} for d in window.dice]
        outcome = {"result": prepared.result, "changes": changes, "rolls": rolls, "effects": effects, "windowId": window.id}
        canonical_bytes(outcome)
        self.fault("after_draw")
        tx.scope.state_version += 1
        tx.save_checkpoint(action, checkpoint_id, outcome, changes, rolls, effects)
        self.fault("checkpoint_written")
        action.last_checkpoint_id = checkpoint_id
        action.next_window += 1
        if window.wait_for_decision:
            action.transition(ActionState.WAITING_DECISION)
        elif action.next_window == len(plan.windows):
            action.transition(ActionState.COMPLETED)
            if action.parent_id is None:
                tx.scope.active_action_id = None
                tx.release_lease = True
        else:
            action.version += 1
        tx.save_action(action)
        if root.id != action.id:
            tx.save_action(root)
        event_id = tx.event(action, "checkpoint_committed", checkpoint_id)
        old_receipt = tx.receipt(action.principal_id, command.wire["idempotencyKey"])
        if old_receipt["status"] == "accepted":
            tx.save_receipt(action.principal_id, command.wire["idempotencyKey"],
                            receipt(command, action.id, tx.scope, status="committed", checkpoint_id=checkpoint_id,
                                    outcome=outcome, events=[event_id]))
        return {"status": action.state, "checkpointId": checkpoint_id, "outcome": outcome,
                "stateVersion": tx.scope.state_version}

    def _change(self, tx, cache, instance_id, resource_id, delta, reason, *, spending=False):
        key = (instance_id, resource_id)
        resource = cache.setdefault(key, tx.resource(*key))
        before, maximum = resource["current"], resource["maximum"]
        if maximum < Rational.of(0) or not Rational.of(0) <= before <= maximum:
            refuse("SEMANTIC_INVALID", "stored resource violates its declared bounds")
        converted = self.ruleset.units.convert(delta, resource["unit"]).value
        after = before + converted
        policy = "reject" if spending else resource["policy"]
        if policy not in {"reject", "clamp_report_delta"}:
            refuse("SEMANTIC_INVALID", "resource lacks an adjustment policy")
        if not Rational.of(0) <= after <= maximum:
            if policy == "reject":
                refuse("RESOURCE_BOUND_EXCEEDED")
            after = max(Rational.of(0), min(maximum, after))
        resource["current"] = after
        applied = after - before
        return {"instanceId": instance_id, "resourceId": resource_id, "unit": resource["unit"],
                "before": before.to_wire(), "after": after.to_wire(), "appliedDelta": applied.to_wire(),
                "discardedRemainder": (converted - applied).to_wire(), "reason": reason}

    @staticmethod
    def _involved(command):
        p = command.wire["payload"]
        if command.wire["operation"] == "AdjustResource":
            return [p["instance"]["id"]]
        return [p["actorInstance"]["id"], p["sourceInstance"]["id"], *(t["id"] for t in p["targets"])]

    def advance(self, scope_id, action_id, *, window_index, fence):
        """Internal worker continuation. Index and fence make retries unambiguous."""
        with self.store.transaction(scope_id) as tx:
            tx.check_fence(fence)
            action = tx.action(action_id)
            prior = tx.checkpoint(action_id, window_index)
            if prior is not None:
                return prior
            if window_index != action.next_window:
                refuse("ACTION_VERSION_CONFLICT")
            command = Command.parse(action.request, max_bytes=self.max_request_bytes)
            if action.state in PRECOMMIT:
                if tx.now >= action.deadline:
                    self._cancel(tx, action, command)
                    return {"status": action.state, "checkpointId": None}
                result = self._activate(tx, action, command)
            else:
                if action.state != ActionState.ACTIVE or tx.scope.active_action_id != action.root_id:
                    refuse("ACTION_STATE_CONFLICT")
                if tx.live_children(action.id):
                    refuse("SCOPE_BUSY", "parent must wait for its declared child")
                try:
                    self._authorize(tx, action.principal_id, command)
                    self._authority(tx, command, check_version=False)
                    if command.wire["operation"] == "InvokeActivity":
                        self._invocation_source(tx, command)
                    result = self._atomic_checkpoint(tx, action, command)
                except (ContractViolation, ArithmeticFault) as exc:
                    self._suspend(tx, action, getattr(exc, "code", "SEMANTIC_INVALID"))
                    result = {"status": action.state, "errorCode": action.error_code,
                              "checkpointId": action.last_checkpoint_id}
            self.fault("before_commit")
        self.fault("after_commit")
        return result

    def claim(self, scope_id):
        with self.store.transaction(scope_id) as tx:
            return tx.claim_lease(self.worker_id)

    def cancel(self, principal, scope_id, action_id):
        with self.store.transaction(scope_id) as tx:
            action = tx.action(action_id)
            command = Command.parse(action.request, max_bytes=self.max_request_bytes)
            self._authorize(tx, principal, command)
            if action.principal_id != principal or action.state not in PRECOMMIT:
                refuse("ACTION_STATE_CONFLICT", "only the invoker can withdraw an uncommitted proposal")
            self._cancel(tx, action, command)
            return tx.receipt(principal, command.wire["idempotencyKey"])

    def expire_proposals(self, scope_id):
        with self.store.transaction(scope_id) as tx:
            return self._expire(tx)

    def _expire(self, tx):
        expired = 0
        for action_id in tx.open_proposals():
            action = tx.action(action_id)
            if tx.now >= action.deadline:
                self._cancel(tx, action, Command.parse(action.request, max_bytes=self.max_request_bytes))
                expired += 1
        return expired

    @staticmethod
    def _cancel(tx, action, command):
        action.transition(ActionState.CANCELLED)
        tx.save_action(action)
        tx.save_receipt(action.principal_id, command.wire["idempotencyKey"],
                        receipt(command, action.id, tx.scope, status="rejected", code="ACTION_CANCELLED"))

    @staticmethod
    def _suspend(tx, action, code):
        action.transition(ActionState.SUSPENDED)
        action.error_code = code
        tx.scope.state_version += 1
        tx.save_action(action)
        tx.event(action, "action_suspended")
