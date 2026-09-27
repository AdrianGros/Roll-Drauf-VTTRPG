"""PostgreSQL unit of work for the WP4 kernel.

Scope row locking is the consistency boundary for every runtime write. The
kernel runs inside it and returns only after commit. All policy implementations
must read/revalidate through this transaction and coordinate policy changes on
the same scope row. User-account reads take shared locks until commit.

This adapter deliberately refuses SQLite: it cannot prove these guarantees.
Outbox payloads/snapshots are INTERNAL and require projection before delivery
to users; `dispatch` accepts only trusted server-side consumers.
"""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.content import new_id
from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.kernel.decisions import Decision, Question
from vtt.creation_engine.kernel.records import Action, PRECOMMIT, TERMINAL, refuse
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.runtime_models import (CeRuntimeScope, CeInstance, CeResourceLedger, CeAction,
    CeCheckpoint, CeReceipt, CeResourceEntry, CeRandomRecord, CeEffectApplication, CeDomainEvent, CeOutbox, CeEventConsumption, CePendingDecision)
from vtt.models.user import User


class RuntimeStore:
    def __init__(self, engine, *, clock=None):
        if engine.dialect.name != "postgresql":
            raise ValueError("the runtime kernel requires PostgreSQL")
        self.engine, self.clock = engine, clock

    def now(self, session):
        return self.clock() if self.clock else session.scalar(select(func.clock_timestamp()))

    @contextmanager
    def transaction(self, scope_id):
        with Session(self.engine) as session, session.begin():
            scope = session.scalar(select(CeRuntimeScope).where(CeRuntimeScope.id == scope_id).with_for_update())
            if scope is None or scope.deleted:
                refuse("NOT_FOUND")
            tx = RuntimeTransaction(self, session, scope)
            yield tx
            session.flush()
            commit_time = max(self.now(session), scope.time_watermark)
            scope.time_watermark = commit_time
            tx.now = commit_time
            # Decision acceptance/expiry uses this single boundary-time reading.
            # Hooks execute under the scope lock before the transaction commits.
            for callback in tx.commit_callbacks:
                callback()
            session.flush()
            # The row lock prevents reassignment; expiry is also checked at the
            # durable-write boundary so a slow old worker cannot finish late.
            if tx.required_fence is not None:
                tx.check_fence(tx.required_fence, now=commit_time)
            if tx.activation_deadline is not None and commit_time >= tx.activation_deadline:
                refuse("ACTION_CANCELLED", "proposal expired before activation could commit")
            if tx.release_lease:
                scope.lease_owner = scope.lease_expires_at = None

    def dispatch(self, deliver, *, limit=100):
        """At least once. A lost ACK deliberately causes another delivery."""
        with Session(self.engine) as session:
            ids = list(session.scalars(select(CeOutbox.event_id).join(CeDomainEvent)
                       .where(CeOutbox.delivered_at.is_(None)).order_by(CeDomainEvent.scope_id, CeDomainEvent.sequence)
                       .limit(limit)))
        for event_id in ids:
            with Session(self.engine) as session:
                event = parse_strict_json(session.get(CeDomainEvent, event_id).canonical)
            error = None
            try:
                deliver(event)
            except Exception as exc:
                error = exc
            with Session(self.engine) as session, session.begin():
                row = session.get(CeOutbox, event_id, with_for_update=True)
                row.attempts += 1
                if error is None:
                    row.delivered_at = self.now(session)
            if error is not None:
                raise error
        return len(ids)

    def consume_once(self, consumer, event, apply):
        """Deduplicate and apply a trusted consumer's database changes atomically."""
        with Session(self.engine) as session, session.begin():
            inserted = session.scalar(insert(CeEventConsumption).values(consumer=consumer, event_id=event["eventId"])
                       .on_conflict_do_nothing().returning(CeEventConsumption.event_id))
            if inserted is None:
                return False
            stored = session.get(CeDomainEvent, inserted)
            # Never trust the payload in a redelivered message.
            apply(session, parse_strict_json(stored.canonical))
            return True

    def snapshot(self, scope_id):
        """Consistent internal recovery snapshot; WP6 must filter and issue cursors."""
        with self.transaction(scope_id) as tx:
            rows = tx.session.execute(select(CeResourceLedger).join(CeInstance)
                                      .where(CeInstance.scope_id == scope_id)).scalars()
            return {"scopeId": scope_id, "stateVersion": tx.scope.state_version,
                    "authorityEpoch": tx.scope.authority_epoch, "eventSequence": tx.scope.event_sequence,
                    "executionLockDigest": tx.lock.digest, "activeActionId": tx.scope.active_action_id,
                    "effects": [parse_strict_json(e.canonical) for e in tx.session.scalars(
                        select(CeEffectApplication).where(CeEffectApplication.scope_id == scope_id).order_by(CeEffectApplication.id))],
                    "resources": sorted([{"instanceId": r.instance_id, "resourceId": r.resource_id,
                                          "current": parse_strict_json(r.current)} for r in rows],
                                         key=lambda r: (r["instanceId"], r["resourceId"]))}


class RuntimeTransaction:
    def __init__(self, store, session, scope):
        self.store, self.session, self.scope = store, session, scope
        self.now = max(store.now(session), scope.time_watermark)
        scope.time_watermark = self.now
        self.required_fence = None
        self.release_lease = False
        self.activation_deadline = None
        self.commit_callbacks = []
        self.content = ContentStore(session)
        self.lock = self.content.lock(scope.lock_id)
        if self.lock is None:
            refuse("SEMANTIC_INVALID", "scope's execution lock is unavailable")

    def require_usable_account(self, principal_id):
        if type(principal_id) is not int:
            refuse("OPERATION_FORBIDDEN")
        user = self.session.scalar(select(User).where(User.id == principal_id).with_for_update(read=True))
        if user is None or not user.is_active or user.is_suspended or user.account_state != "active":
            refuse("OPERATION_FORBIDDEN")

    def instance(self, ref):
        if ref["scopeId"] != self.scope.id:
            refuse("NOT_FOUND")
        row = self.session.get(CeInstance, ref["id"])
        if row is None or row.scope_id != self.scope.id:
            refuse("NOT_FOUND")
        revision = self.content.revision(row.revision_id)
        if revision is None or revision.ref() not in self.lock.revisions:
            refuse("REVISION_NOT_IN_LOCK")
        return row

    def action(self, action_id):
        row = self.session.get(CeAction, action_id)
        if row is None or row.scope_id != self.scope.id:
            refuse("NOT_FOUND")
        fields = {name: getattr(row, name) for name in Action.__dataclass_fields__ if name != "budget"}
        return Action(**fields, budget=parse_strict_json(row.budget))

    def save_action(self, action):
        row = self.session.get(CeAction, action.id)
        if row is None:
            row = CeAction(id=action.id)
            self.session.add(row)
        for key, value in asdict(action).items():
            setattr(row, key, canonical_bytes(value) if key == "budget" else value)
        self.session.flush()

    def open_proposals(self):
        return list(self.session.scalars(select(CeAction.id).where(CeAction.scope_id == self.scope.id,
                                          CeAction.state.in_(PRECOMMIT))))

    def live_children(self, action_id):
        return self.session.scalar(select(CeAction.id).where(CeAction.parent_id == action_id,
                                   CeAction.state.not_in(TERMINAL)).limit(1)) is not None

    @contextmanager
    def checkpoint_boundary(self):
        # The outer transaction retains admission/status; the savepoint rolls
        # back every mechanical write if validation fails late in a checkpoint.
        callbacks = len(self.commit_callbacks)
        try:
            with self.session.begin_nested():
                yield
        except Exception:
            del self.commit_callbacks[callbacks:]
            raise

    def receipt(self, principal, key):
        row = self.session.get(CeReceipt, (self.scope.id, principal, key))
        return parse_strict_json(row.canonical) if row else None

    def save_receipt(self, principal, key, value):
        validate_definition("Receipt", value)
        row = self.session.get(CeReceipt, (self.scope.id, principal, key))
        if row is None:
            row = CeReceipt(scope_id=self.scope.id, principal_id=principal, idempotency_key=key,
                            operation_id=value["operationId"], request_digest=value["requestDigest"])
            self.session.add(row)
        elif row.status != "accepted":
            if row.canonical != canonical_bytes(value):
                refuse("IDEMPOTENCY_KEY_REUSE", "terminal receipt is immutable")
            return
        row.status, row.canonical = value["status"], canonical_bytes(value)
        self.session.flush()

    def resource(self, instance_id, resource_id):
        instance = self.session.get(CeInstance, instance_id)
        if instance is None or instance.scope_id != self.scope.id:
            refuse("NOT_FOUND")
        row = self.session.get(CeResourceLedger, (instance_id, resource_id))
        if row is None:
            refuse("SEMANTIC_INVALID", "resource is not declared on this occurrence")
        return {"instanceId": instance_id, "resourceId": resource_id, "unit": row.unit,
                "current": Rational.from_wire(parse_strict_json(row.current)),
                "maximum": Rational.from_wire(parse_strict_json(row.maximum)), "policy": row.adjust_bound_policy}

    def set_resource(self, change, checkpoint_id):
        row = self.session.get(CeResourceLedger, (change["instanceId"], change["resourceId"]))
        row.current = canonical_bytes(change["after"])
        self.session.add(CeResourceEntry(id=new_id("entry"), checkpoint_id=checkpoint_id,
                         instance_id=row.instance_id, resource_id=row.resource_id, canonical=canonical_bytes(change)))

    def checkpoint(self, action_id, index):
        row = self.session.scalar(select(CeCheckpoint).where(CeCheckpoint.action_id == action_id,
                                                           CeCheckpoint.window_index == index))
        if row is None:
            return None
        outcome = parse_strict_json(row.outcome)
        if content_digest(outcome) != row.outcome_digest:
            refuse("SEMANTIC_INVALID", "checkpoint integrity failure")
        return {"checkpointId": row.id, "outcome": outcome, "stateVersion": row.state_version}

    def effect_exists(self, application_id):
        return self.session.get(CeEffectApplication, application_id) is not None

    def effect_count(self, target_id):
        return self.session.scalar(select(func.count()).select_from(CeEffectApplication)
                                   .where(CeEffectApplication.target_id == target_id))

    def save_checkpoint(self, action, checkpoint_id, outcome, changes, rolls, effects, *, index=None):
        self.session.add(CeCheckpoint(id=checkpoint_id, scope_id=self.scope.id, action_id=action.id,
                         window_index=action.next_window if index is None else index, state_version=self.scope.state_version,
                         outcome=canonical_bytes(outcome), outcome_digest=content_digest(outcome), created_at=self.now))
        self.session.flush()
        for change in changes:
            self.set_resource(change, checkpoint_id)
        for roll in rolls:
            self.session.add(CeRandomRecord(checkpoint_id=checkpoint_id, roll_id=roll["id"], canonical=canonical_bytes(roll)))
        for effect in effects:
            self.session.add(CeEffectApplication(id=effect["applicationId"], scope_id=self.scope.id,
                             checkpoint_id=checkpoint_id, target_id=effect["target"]["id"], canonical=canonical_bytes(effect)))

    def event(self, action, kind, checkpoint_id=None, *, details=None):
        self.scope.event_sequence += 1
        event_id = new_id("event")
        event = {"eventId": event_id, "scopeId": self.scope.id, "sequence": self.scope.event_sequence,
                 "stateVersion": self.scope.state_version, "authorityEpoch": self.scope.authority_epoch,
                 "actionId": action.id, "checkpointId": checkpoint_id, "kind": kind,
                 "executionLockDigest": self.lock.digest, "policyVersion": self.scope.policy_version,
                 "audience": "engine-internal", "details": details}
        self.session.add(CeDomainEvent(id=event_id, scope_id=self.scope.id, sequence=self.scope.event_sequence,
                         action_id=action.id, checkpoint_id=checkpoint_id, canonical=canonical_bytes(event)))
        self.session.flush()
        self.session.add(CeOutbox(event_id=event_id, attempts=0))
        return event_id

    def claim_lease(self, worker_id, *, seconds=30):
        s = self.scope
        if s.active_action_id and s.lease_expires_at and s.lease_expires_at > self.now and s.lease_owner != worker_id:
            refuse("LEASE_BUSY")
        if s.lease_owner != worker_id or s.lease_expires_at is None or s.lease_expires_at <= self.now:
            s.fence_epoch += 1
        s.lease_owner, s.lease_expires_at = worker_id, self.now + timedelta(seconds=seconds)
        self.required_fence = s.fence_epoch
        return s.fence_epoch

    def check_fence(self, fence, *, now=None):
        s = self.scope
        if s.fence_epoch != fence or s.lease_expires_at is None or (now or self.now) >= s.lease_expires_at:
            refuse("WORKER_FENCED", "worker lease expired or was reassigned")
        self.required_fence = fence


    def decision(self, decision_id, version=None):
        query = select(CePendingDecision).where(CePendingDecision.scope_id == self.scope.id,
                                               CePendingDecision.id == decision_id)
        if version is not None:
            query = query.where(CePendingDecision.version == version)
        row = self.session.scalar(query.order_by(CePendingDecision.version.desc()).limit(1))
        if row is None:
            refuse("DECISION_STALE" if version is not None else "NOT_FOUND")
        return Decision(parse_strict_json(row.canonical), row.context_digest, row.created_scope_version,
                        Question.restore(parse_strict_json(row.question)), row.timeout_seconds,
                        parse_strict_json(row.answer) if row.answer is not None else None, row.responder_id, row.closed_at)

    def save_decision(self, decision):
        w = decision.wire
        validate_definition("PendingDecision", w)
        row = self.session.get(CePendingDecision, (decision.id, decision.version))
        if row is None:
            row = CePendingDecision(id=decision.id, version=decision.version, scope_id=self.scope.id,
                                    action_id=w["actionId"], checkpoint_id=w["checkpointId"],
                                    context_digest=decision.context_digest, created_scope_version=decision.created_scope_version,
                                    question=canonical_bytes(decision.question.wire()), timeout_seconds=decision.timeout_seconds)
            self.session.add(row)
        row.status, row.canonical = w["status"], canonical_bytes(w)
        row.answer = canonical_bytes(decision.answer) if decision.answer is not None else None
        row.responder_id, row.closed_at = decision.responder_id, decision.closed_at
        self.session.flush()

    def open_decisions(self, action_id=None):
        query = select(CePendingDecision.id).where(CePendingDecision.scope_id == self.scope.id,
                                                 CePendingDecision.status == "open")
        if action_id is not None:
            query = query.where(CePendingDecision.action_id == action_id)
        return [self.decision(i) for i in self.session.scalars(query.order_by(CePendingDecision.id))]

    def decisions_for(self, action_id):
        ids = self.session.scalars(select(CePendingDecision.id).where(CePendingDecision.scope_id == self.scope.id,
                                        CePendingDecision.action_id == action_id).distinct())
        return [self.decision(i) for i in ids]

    def answers(self, action_id):
        """Retained typed inputs for the trusted checkpoint preparer, never client output."""
        return {d.wire["questionId"]: d.answer for d in self.decisions_for(action_id) if d.answer is not None}

    def intervention_index(self, action_id):
        # Activity indexes stay stable across operator/decision checkpoints.
        smallest = self.session.scalar(select(func.min(CeCheckpoint.window_index))
                                       .where(CeCheckpoint.action_id == action_id))
        return min(0, smallest or 0) - 1

    def decision_snapshot(self):
        """Conservative full mechanical read set; no raw digest is published."""
        instances = list(self.session.scalars(select(CeInstance).where(CeInstance.scope_id == self.scope.id)
                                              .order_by(CeInstance.id)))
        resources = self.session.scalars(select(CeResourceLedger).join(CeInstance)
                                        .where(CeInstance.scope_id == self.scope.id)
                                        .order_by(CeResourceLedger.instance_id, CeResourceLedger.resource_id))
        effects = self.session.scalars(select(CeEffectApplication).where(CeEffectApplication.scope_id == self.scope.id)
                                      .order_by(CeEffectApplication.id))
        return {"instances": [{"id": i.id, "revision": i.revision_id, "holder": i.holder_id,
                               "controller": i.controller_user_id} for i in instances],
                "resources": [{"instanceId": r.instance_id, "resourceId": r.resource_id, "unit": r.unit,
                               "current": parse_strict_json(r.current), "maximum": parse_strict_json(r.maximum),
                               "boundPolicy": r.adjust_bound_policy} for r in resources],
                "effects": [parse_strict_json(e.canonical) for e in effects]}
