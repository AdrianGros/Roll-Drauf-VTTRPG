"""Audience-specific engine gateway shared by REST and Socket.IO.

Mechanical commits finish before projection. Every read/delivery then takes a
fresh scope lock and current account/membership locks. Optional delivery sinks
must enqueue immediately; they are not remote callbacks or checkpoint ports.
Raw events, snapshots, hashes and diagnostics never leave through this gateway.
"""

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from threading import RLock

from sqlalchemy import select, delete, update

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.kernel.records import Command, refuse
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.types import parse_id
from vtt.creation_engine.policy import Document, cache_key, project, public_receipt
from vtt.creation_engine.store.policy import nonce
from vtt.creation_engine.store.policy_models import CeDeliveryCursor, CePublicReceiptRequest, CeSubscription
from vtt.creation_engine.store.runtime_models import CeCheckpoint, CeDomainEvent


class PublicGateway:
    def __init__(self, kernel, policy, *, document, snapshot_documents, event_document, configuration,
                 outcome_document=None, declassifications=(), representation_version="g1:1", cache_size=256):
        self.kernel, self.store, self.policy = kernel, kernel.store, policy
        self.document, self.snapshot_documents, self.event_document = document, snapshot_documents, event_document
        self.outcome_document = outcome_document
        self.declassifications = tuple(declassifications)
        self.representation_version, self.cache_size, self.cache = representation_version, cache_size, OrderedDict()
        self.cache_lock = RLock()
        if type(cache_size) is not int or cache_size < 1:
            raise ValueError("projection cache size must be positive")
        if content_digest(configuration) != kernel.configuration_digest:
            raise ValueError("projection configuration must match the execution lock")
        declared = configuration.get("declassifications", [])
        if canonical_bytes(declared) != canonical_bytes([d.wire() for d in self.declassifications]):
            raise ValueError("reviewed declassifications must be pinned in the configuration")
        # Every transport uses the same current-policy command ports.
        kernel.authorize, kernel.authorize_operator = policy.authorize, policy.authorize_operator

    @contextmanager
    def _transaction(self, scope_id):
        parse_id(scope_id)
        tx = None
        try:
            with self.store.transaction(scope_id) as tx:
                yield tx
        except ContractViolation as exc:
            if tx is not None and exc.code in {"NOT_FOUND", "OPERATION_FORBIDDEN"}:
                # Keep only the observed authority time and expiry housekeeping
                # after a denied read rolls back. A later backward clock step
                # must not revive the expired view/entitlement it just rejected.
                with self.store.transaction(scope_id) as observed:
                    observed.now = max(observed.now, tx.now)
                    observed.scope.time_watermark = max(observed.scope.time_watermark, observed.now)
                    self.policy.expire_views(observed)
            raise

    def _audience(self, tx, principal, view_id=None):
        audience = self.policy.audience(tx, principal, view_id)
        if not self.supports_scope(tx):
            refuse("ENGINE_UNAVAILABLE", "locked projection registrations are unavailable")
        expected = self.policy.access_stamp(audience)
        def revalidate():
            current = self.policy.audience(tx, principal, view_id)
            if self.policy.access_stamp(current) != expected:
                refuse("NOT_FOUND")
        tx.commit_callbacks.append(revalidate)
        return audience

    def supports_scope(self, tx):
        return (tx.lock.wire["configurationDigest"] == self.kernel.configuration_digest
                and tx.lock.wire["schemaBundle"] == self.kernel.schema_registry.artifact()
                and tx.lock.wire["ruleset"] == self.kernel.ruleset.artifact())

    def _project(self, tx, audience, document, operation="read"):
        if document is None:
            return None
        return project(document, self.policy.policies(tx), audience, operation=operation,
                       declassifications=self.declassifications)

    def read(self, principal, scope_id, object_id, *, operation="read", view_id=None):
        parse_id(object_id)
        if operation not in {"read", "explain", "export"}:
            refuse("OPERATION_FORBIDDEN")
        with self._transaction(scope_id) as tx:
            audience = self._audience(tx, principal, view_id)
            key = cache_key(audience=audience, scope_id=scope_id, policy_epoch=tx.scope.policy_version,
                access_stamp=self.policy.access_stamp(audience), state_version=tx.scope.state_version,
                lock_digest=tx.lock.digest, representation_version=self.representation_version,
                object_id=object_id, operation=operation)
            # Recheck even a cached object's current read grant. Loaders cannot
            # depend on external unversioned data; all mutations bump scope state.
            document = self.document(tx, object_id)
            if document is None or not self.policy.policies(tx).allows_audience(audience, document.policy_id):
                refuse("NOT_FOUND")
            with self.cache_lock:
                if key not in self.cache:
                    value = self._project(tx, audience, document, operation)
                    if value is None:
                        refuse("NOT_FOUND")
                    self.cache[key] = canonical_bytes(value)
                    if len(self.cache) > self.cache_size:
                        self.cache.popitem(last=False)
                self.cache.move_to_end(key)
                return parse_strict_json(self.cache[key])

    def search(self, principal, scope_id, query, *, view_id=None, limit=50):
        if not isinstance(query, str) or len(query) > 256 or type(limit) is not int or not 1 <= limit <= 100:
            refuse("SCHEMA_INVALID")
        with self._transaction(scope_id) as tx:
            audience = self._audience(tx, principal, view_id)
            # Authorization and field projection precede matching/ranking/counts.
            visible = [value for d in self.snapshot_documents(tx)
                       if (value := self._project(tx, audience, d)) is not None]
            matches = [value for value in visible if query.casefold() in str(value["fields"].get("name", "")).casefold()]
            matches.sort(key=lambda v: (str(v["fields"].get("name", "")).casefold(), v["id"]))
            return {"items": matches[:limit], "total": len(matches)}

    def _event(self, tx, audience, row):
        raw = parse_strict_json(row.canonical)
        document = self.event_document(tx, raw)
        if document is None:
            return None
        checkpoint_id = raw.get("checkpointId")
        checkpoint = tx.session.get(CeCheckpoint, checkpoint_id) if checkpoint_id else None
        if checkpoint and parse_strict_json(checkpoint.outcome).get("manual") is True:
            document = replace(document, manual=True)
        value = self._project(tx, audience, document)
        if value is None:
            return None
        return {"eventId": row.id, "scopeId": tx.scope.id, "stateVersion": raw["stateVersion"],
                "authorityEpoch": raw["authorityEpoch"], "data": value}

    def _receipt(self, tx, principal, command, internal):
        self.kernel._authorize(tx, principal, command)
        if command.wire["operation"] == "ResolveDecision":
            payload = command.wire["payload"]
            self.kernel._eligible(tx, principal, tx.decision(payload["decisionId"], payload["expectedDecisionVersion"]))
        audience = self._audience(tx, principal)
        visible, checkpoint_visible = [], False
        for event_id in internal["eventIds"]:
            row = tx.session.get(CeDomainEvent, event_id)
            if row and row.scope_id == tx.scope.id and self._event(tx, audience, row) is not None:
                visible.append(event_id)
                checkpoint_visible |= parse_strict_json(row.canonical).get("checkpointId") == internal["checkpointId"]
        return public_receipt(internal, visible_event_ids=visible, checkpoint_visible=checkpoint_visible)

    def submit(self, principal, raw, *, view_id=None):
        if view_id is not None:
            refuse("OPERATION_FORBIDDEN", "View As cannot issue commands")
        command = Command.parse(raw, max_bytes=self.kernel.max_request_bytes)
        internal = self.kernel.submit(principal, raw, record_request=self._record_request)
        with self._transaction(command.wire["scopeId"]) as tx:
            return self._receipt(tx, principal, command, internal)

    @staticmethod
    def _record_request(tx, principal, command):
        # Only envelopes actually received from this client are registered for
        # public lookup. Server-created child requests are not client receipts.
        key = (tx.scope.id, principal, command.wire["idempotencyKey"])
        if tx.session.get(CePublicReceiptRequest, key) is None:
            tx.session.add(CePublicReceiptRequest(scope_id=key[0], principal_id=key[1], idempotency_key=key[2], request=command.canonical))
        tx.session.flush()

    def receipt(self, principal, scope_id, key, *, view_id=None):
        parse_id(key)
        if view_id is not None:
            refuse("OPERATION_FORBIDDEN")
        with self._transaction(scope_id) as tx:
            self.policy.require_scope(tx, principal)
            request = tx.session.get(CePublicReceiptRequest, (scope_id, principal, key))
            if request is None:
                refuse("NOT_FOUND")
            return self._receipt(tx, principal, Command.parse(request.request), tx.receipt(principal, key))

    def decision(self, principal, scope_id, decision_id, *, view_id=None):
        parse_id(decision_id)
        with self._transaction(scope_id) as tx:
            audience = self._audience(tx, principal, view_id)
            decision = tx.decision(decision_id)
            policies = self.policy.policies(tx)
            if not policies.allows_audience(audience, decision.question.policy_id):
                refuse("NOT_FOUND")
            for target in decision.wire["targets"]:
                if not policies.allows_audience(audience, tx.instance(target).id):
                    refuse("NOT_FOUND")
            if view_id is not None:
                return {key: decision.wire[key] for key in ("decisionId", "status", "createdAt", "deadline")}
            self.kernel._eligible(tx, principal, decision)
            if not policies.allows_audience(audience, decision.question.policy_id, "respond"):
                refuse("OPERATION_FORBIDDEN")
            return parse_strict_json(canonical_bytes(decision.wire))

    def outcome(self, principal, scope_id, action_id, *, view_id=None, operation="read"):
        parse_id(action_id)
        if operation not in {"read", "explain", "export"}:
            refuse("OPERATION_FORBIDDEN")
        with self._transaction(scope_id) as tx:
            audience = self._audience(tx, principal, view_id)
            action = tx.action(action_id)
            checkpoint = tx.session.get(CeCheckpoint, action.last_checkpoint_id) if action.last_checkpoint_id else None
            if checkpoint is None or self.outcome_document is None:
                refuse("NOT_FOUND")
            internal = parse_strict_json(checkpoint.outcome)
            document = self.outcome_document(tx, action, internal)
            if document is not None and internal.get("manual") is True:
                document = replace(document, manual=True)
            result = self._project(tx, audience, document, operation)
            if result is None:
                refuse("NOT_FOUND")
            return result

    def enter_view(self, principal, scope_id, member_id):
        with self._transaction(scope_id) as tx:
            return self.policy.enter_view(tx, principal, member_id)

    def exit_view(self, principal, scope_id, view_id):
        parse_id(view_id)
        with self._transaction(scope_id) as tx:
            tx.require_usable_account(principal)
            self.policy.close_view(tx, principal, view_id)
        return {"closed": True}

    def _snapshot(self, tx, audience):
        return {"contractVersion": "1.1.3", "scopeId": tx.scope.id, "stateVersion": tx.scope.state_version,
                "authorityEpoch": tx.scope.authority_epoch,
                "status": tx.action(tx.scope.active_action_id).state if tx.scope.active_action_id else "IDLE",
                "objects": [value for d in self.snapshot_documents(tx) if (value := self._project(tx, audience, d)) is not None]}

    def subscribe(self, principal, scope_id, connection_id, *, contract_version, authority_epoch):
        if contract_version != "1.1.3":
            refuse("SCHEMA_INVALID")
        if type(authority_epoch) is not int or not 0 <= authority_epoch <= 2**53 - 1:
            refuse("SCHEMA_INVALID")
        if not isinstance(connection_id, str) or not connection_id or len(connection_id) > 128:
            refuse("SCHEMA_INVALID")
        with self._transaction(scope_id) as tx:
            audience = self._audience(tx, principal)
            row = CeSubscription(id=nonce("subscription"), scope_id=scope_id, principal_id=principal,
                connection_id=connection_id, access_stamp=self.policy.access_stamp(audience),
                policy_epoch=tx.scope.policy_version, authority_epoch=tx.scope.authority_epoch,
                expires_at=tx.now + timedelta(minutes=15))
            tx.session.add(row)
            tx.session.flush()
            cursor = self._cursor(tx, row, tx.scope.event_sequence)
            return {"subscriptionId": row.id, "cursor": cursor, "refresh": authority_epoch != tx.scope.authority_epoch,
                    "snapshot": self._snapshot(tx, audience)}

    def _cursor(self, tx, subscription, sequence):
        row = CeDeliveryCursor(id=nonce("cursor"), subscription_id=subscription.id, sequence=sequence,
                              expires_at=subscription.expires_at)
        tx.session.add(row)
        return row.id

    def poll(self, principal, scope_id, subscription_id, cursor_id, connection_id, *, deliver=None):
        """Project just before each delivery; no role-room broadcast or raw outbox replay."""
        parse_id(subscription_id)
        rejected = False
        with self._transaction(scope_id) as tx:
            row = tx.session.get(CeSubscription, subscription_id)
            if row is None or row.scope_id != scope_id or row.principal_id != principal or row.connection_id != connection_id:
                refuse("NOT_FOUND")
            # Changed legacy membership also invalidates delivery, even if a
            # legacy writer has not yet adopted the coordinated epoch hook.
            try:
                audience = self._audience(tx, principal)
            except ContractViolation:
                audience = ()
            if (not audience or row.revoked_at is not None or tx.now >= row.expires_at
                    or row.access_stamp != self.policy.access_stamp(audience)
                    or row.policy_epoch != tx.scope.policy_version or row.authority_epoch != tx.scope.authority_epoch):
                row.revoked_at = row.revoked_at or tx.now
                rejected = True
            else:
                cursor = tx.session.get(CeDeliveryCursor, cursor_id) if isinstance(cursor_id, str) else None
                if cursor is None or cursor.subscription_id != row.id or tx.now >= cursor.expires_at:
                    result = {"snapshot": self._snapshot(tx, audience), "events": [], "refresh": True,
                              "cursor": self._cursor(tx, row, tx.scope.event_sequence)}
                else:
                    events, sequence = [], cursor.sequence
                    query = select(CeDomainEvent).where(CeDomainEvent.scope_id == scope_id, CeDomainEvent.sequence > sequence).order_by(CeDomainEvent.sequence)
                    for event in tx.session.scalars(query).yield_per(250):
                        sequence = event.sequence
                        public = self._event(tx, audience, event)
                        if public is not None:
                            events.append(public)
                        if len(events) >= 100:
                            break
                    result = {"events": events, "refresh": False, "cursor": self._cursor(tx, row, sequence)}
                if deliver is not None:
                    def enqueue():
                        if tx.now >= row.expires_at:
                            refuse("NOT_FOUND")
                        deliver(result)
                    # Current authority time is read and audience revalidated
                    # before this bounded enqueue, with policy locks still held.
                    tx.commit_callbacks.append(enqueue)
        if rejected:
            refuse("NOT_FOUND")
        return result

    def disconnect(self, principal, scope_id, connection_id):
        with self._transaction(scope_id) as tx:
            for row in tx.session.scalars(select(CeSubscription).where(CeSubscription.scope_id == scope_id,
                        CeSubscription.principal_id == principal, CeSubscription.connection_id == connection_id)):
                row.revoked_at = row.revoked_at or tx.now

    def maintain(self, scope_id):
        """The host's periodic job closes expired View As sessions and cursor rows."""
        with self._transaction(scope_id) as tx:
            self.policy.expire_views(tx)
            tx.session.execute(update(CeSubscription).where(CeSubscription.scope_id == scope_id,
                CeSubscription.revoked_at.is_(None), CeSubscription.expires_at <= tx.now).values(revoked_at=tx.now))
            tx.session.execute(delete(CeDeliveryCursor).where(CeDeliveryCursor.subscription_id.in_(
                select(CeSubscription.id).where(CeSubscription.scope_id == scope_id)), CeDeliveryCursor.expires_at <= tx.now))
