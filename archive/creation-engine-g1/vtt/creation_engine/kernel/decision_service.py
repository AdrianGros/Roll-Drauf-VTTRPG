"""WP5 decision/operator behavior shared by all future transports.

Required trusted ports for activities containing questions:
  responders(tx, rule_id, action) -> current eligible principal IDs
  decision_facts(tx, action, question) -> additional canonical mechanical facts
Operator commands additionally require authorize_operator(tx, principal, wire).
All are server registrations pinned by the host configuration, never content
callbacks. Missing registrations deny the corresponding capability.
"""

import secrets
from dataclasses import replace
from datetime import timedelta

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.content import new_id
from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.kernel.activity import Activity
from vtt.creation_engine.kernel.decisions import Decision, timestamp
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.kernel.records import ActionState, Command, KernelError, charge_root, receipt, refuse
from vtt.creation_engine.units import Quantity

DECISION_OPERATIONS = frozenset({"ResolveDecision", "ReissueDecision", "ReassignDecisionResponder",
                                 "ResumeSuspendedAction", "ResolveActionManually"})


class DecisionCommands:
    def _responders(self, tx, action, question):
        if self.responders is None:
            refuse("OPERATION_FORBIDDEN", "no responder registry is installed")
        candidates = tuple(self.responders(tx, question.responder_rule_id, action))
        if len(candidates) > 128 or any(type(p) is not int for p in candidates):
            refuse("SEMANTIC_INVALID", "invalid registered responder rule")
        usable = []
        for principal in sorted(set(candidates)):
            try:
                tx.require_usable_account(principal)
            except KernelError as exc:
                if exc.code != "OPERATION_FORBIDDEN":
                    raise
            else:
                usable.append(principal)
        return usable

    def _eligible(self, tx, principal, decision):
        tx.require_usable_account(principal)
        if principal not in self._responders(tx, tx.action(decision.wire["actionId"]), decision.question):
            refuse("OPERATION_FORBIDDEN")

    def _operator(self, tx, principal, command):
        if self.authorize_operator is None or self.authorize_operator(tx, principal, command.wire) is not True:
            refuse("OPERATION_FORBIDDEN")

    def _context(self, tx, action, question):
        if self.decision_facts is None:
            refuse("SEMANTIC_INVALID", "question context provider is not registered")
        return content_digest({"snapshot": tx.decision_snapshot(), "lock": tx.lock.digest,
            "authorityEpoch": tx.scope.authority_epoch, "policyVersion": tx.scope.policy_version,
            "actionId": action.id, "checkpointId": action.last_checkpoint_id, "nextWindow": action.next_window,
            "plan": content_digest(parse_strict_json(action.plan)), "question": question.wire(),
            "targets": parse_strict_json(action.request)["payload"]["targets"],
            "answers": tx.answers(action.id), "responders": self._responders(tx, action, question),
            "facts": self.decision_facts(tx, action, question)})

    def _issue(self, tx, action, window, question, *, previous=None, seconds=None, deadline=None):
        schema = self.schema_registry.get(question.answer_type)
        if question.decline is not None:
            self.schema_registry.validate(question.answer_type, question.decline)
        if not self._responders(tx, action, question):
            refuse("OPERATION_FORBIDDEN", "question has no eligible responder rule")
        seconds = tx.scope.decision_timeout_seconds if seconds is None else seconds
        first_open = not tx.open_decisions()
        wire = {"decisionId": previous.id if previous else new_id("decision"), "actionId": action.id,
            "checkpointId": action.last_checkpoint_id, "questionId": question.id, "questionVersion": question.version,
            "answerSchemaDigest": content_digest(schema.schema), "contextToken": "ctx:" + secrets.token_urlsafe(32),
            "decisionVersion": previous.version + 1 if previous else 0, "responderRuleId": question.responder_rule_id,
            "targets": parse_strict_json(action.request)["payload"]["targets"], "createdAt": timestamp(tx.now),
            "deadline": timestamp(deadline or tx.now + timedelta(seconds=seconds)), "windowId": window,
            "timeoutPolicy": "decline_optional" if question.decline is not None else "suspend_mandatory",
            "status": "open", "policyId": question.policy_id}
        decision = Decision(wire, self._context(tx, action, question), tx.scope.state_version, question, seconds)
        tx.save_decision(decision)
        if first_open:
            tx.scope.decision_heartbeat_at = tx.now
        tx.event(action, "decision_opened", action.last_checkpoint_id)
        return decision

    def _frame(self, tx, action):
        if tx.scope.active_action_id != action.root_id or tx.live_children(action.id):
            refuse("ACTION_STATE_CONFLICT", "decision/operator command is outside the active leaf frame")

    def _decision_matches(self, tx, command):
        p = command.wire["payload"]
        decision = tx.decision(p["decisionId"])
        if decision.wire["actionId"] != p["actionId"] or decision.version != p["expectedDecisionVersion"]:
            refuse("DECISION_STALE")
        return decision

    def _resume_after_answer(self, tx, action):
        action.transition(ActionState.ACTIVE)
        action.error_code = None
        if action.next_window == len(Activity.restore(action.plan).windows):
            action.transition(ActionState.COMPLETED)
            if action.parent_id is None:
                tx.scope.active_action_id = None
                tx.release_lease = True
        tx.save_action(action)

    def _record_intervention(self, tx, action, outcome, *, changes=(), kind="operator_intervention"):
        root = action if action.root_id == action.id else tx.action(action.root_id)
        charge_root(root, operations=1 + len(changes), events=1,
                    instances=[c["instanceId"] for c in changes])
        if root is not action:
            tx.save_action(root)
        checkpoint_id = new_id("checkpoint")
        tx.scope.state_version += 1
        tx.save_checkpoint(action, checkpoint_id, outcome, changes, (), (), index=tx.intervention_index(action.id))
        action.last_checkpoint_id = checkpoint_id
        action.version += 1
        tx.save_action(action)
        event = tx.event(action, kind, checkpoint_id)
        return checkpoint_id, event

    def _invalidate(self, tx, decision, code):
        decision.close("invalidated", tx.now)
        tx.save_decision(decision)
        action = tx.action(decision.wire["actionId"])
        if action.state != ActionState.SUSPENDED:
            self._suspend(tx, action, code)
        tx.event(action, "decision_invalidated", action.last_checkpoint_id)

    def _decision_time(self, tx):
        decisions = tx.open_decisions()
        heartbeat = tx.scope.decision_heartbeat_at
        anomaly = bool(decisions and (heartbeat is None or
                       tx.now > heartbeat + timedelta(seconds=30 + tx.scope.clock_tolerance_seconds)))
        for decision in decisions:
            action = tx.action(decision.wire["actionId"])
            # Only deadlines crossed during the unobserved interval need an
            # operator ruling. A still-open response window remains usable.
            if anomaly and tx.now >= decision.deadline:
                self._invalidate(tx, decision, "CLOCK_ANOMALY")
            elif not self._context_current(tx, action, decision):
                self._invalidate(tx, decision, "DECISION_STALE")
            elif tx.now >= decision.deadline:
                # An ancestor's response cannot resolve through an active child.
                if tx.live_children(action.id) or action.state != ActionState.WAITING_DECISION:
                    self._invalidate(tx, decision, "DECISION_STALE")
                    continue
                decision.close("expired", tx.now, answer=decision.question.decline)
                tx.save_decision(decision)
                if decision.question.decline is None:
                    self._suspend(tx, action, "DECISION_EXPIRED")
                    tx.event(action, "decision_expired_operator_required", action.last_checkpoint_id)
                else:
                    self._record_intervention(tx, action, {"decisionId": decision.id,
                        "decisionVersion": decision.version, "answer": decision.answer, "automaticDecline": True},
                        kind="decision_declined")
                    self._resume_after_answer(tx, action)
        return anomaly

    def _context_current(self, tx, action, decision):
        try:
            invocation = Command.parse(action.request)
            self._authority(tx, invocation, check_version=False)
            self._authorize(tx, action.principal_id, invocation)
            self._invocation_source(tx, invocation)
            return decision.context_digest == self._context(tx, action, decision.question)
        except ContractViolation:
            return False

    def heartbeat(self, scope_id, *, fence):
        """Lease holder job: schedule every 30 seconds while questions are open.

        A claimant must acquire a new fence after its lease expires. An outage
        does not reset the last heartbeat before anomaly handling runs.
        """
        with self.store.transaction(scope_id) as tx:
            tx.check_fence(fence)
            if tx.scope.lease_owner != self.worker_id:
                refuse("WORKER_FENCED")
            def commit():
                tx.check_fence(fence)
                self._decision_time(tx)
                tx.scope.decision_heartbeat_at = tx.now
                tx.claim_lease(self.worker_id, seconds=60)
            tx.commit_callbacks.append(commit)

    def policy_changed(self, tx, *, reason):
        """Trusted policy writer hook, in the SAME scope-locked revocation UoW.

        This never checks the mechanical gate or waits for its release. WP6
        policy writers must call it with membership/grant changes and use the
        resulting policy version to invalidate subscriptions. No wire endpoint.
        """
        if not isinstance(reason, str) or not reason.strip():
            refuse("SEMANTIC_INVALID", "policy changes need an audit reason")
        tx.scope.policy_version += 1
        tx.scope.state_version += 1
        for decision in tx.open_decisions():
            self._invalidate(tx, decision, "OPERATION_FORBIDDEN")
        if tx.scope.active_action_id:
            action = tx.action(tx.scope.active_action_id)
            tx.event(action, "policy_changed", details={"reason": reason})
        # Without an active frame the host policy audit retains the reason.

    def _decision_submit(self, principal, command, *, record_request=None):
        w = command.wire
        result = {}
        with self.store.transaction(w["scopeId"]) as tx:
            self._authorize(tx, principal, command)
            if w["authorityEpoch"] != tx.scope.authority_epoch:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            if w["operation"] == "ResolveDecision":
                # Revalidate current responder eligibility even on retained retries.
                old = tx.decision(w["payload"]["decisionId"], w["payload"]["expectedDecisionVersion"])
                self._eligible(tx, principal, old)
            else:
                self._operator(tx, principal, command)
            existing = tx.receipt(principal, w["idempotencyKey"])
            if existing:
                if existing["requestDigest"] != command.digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                if record_request is not None:
                    record_request(tx, principal, command)
                return existing
            self._authority(tx, command, check_version=w["operation"] != "ResolveDecision",
                            manual=w["operation"] == "ResolveActionManually")
            def commit():
                # Auth/grants are read under the same lock, including account row
                # locks. No network work or publication is allowed in these ports.
                self._authorize(tx, principal, command)
                # Human commands use the scope row lock, not the execution
                # lease. Any transport worker can accept the response without
                # taking the execution worker's lease or changing its fence.
                if w["operation"] == "ResolveDecision":
                    value = self._resolve_decision(tx, principal, command)
                else:
                    value = self._operator_command(tx, principal, command)
                tx.save_receipt(principal, w["idempotencyKey"], value)
                if record_request is not None:
                    record_request(tx, principal, command)
                result.update(value)
                self.fault("before_commit")
            tx.commit_callbacks.append(commit)
        self.fault("after_commit")
        return result

    def _resolve_decision(self, tx, principal, command):
        p = command.wire["payload"]
        decision = self._decision_matches(tx, command)
        self._eligible(tx, principal, decision)
        if command.wire["expectedScopeVersion"] < decision.created_scope_version:
            refuse("SCOPE_VERSION_CONFLICT")
        if not secrets.compare_digest(p["contextToken"], decision.wire["contextToken"]):
            refuse("DECISION_STALE")
        validate_definition("DecisionAnswer", p["answer"])
        self.schema_registry.validate(decision.question.answer_type, p["answer"])
        self._decision_time(tx)
        decision = tx.decision(decision.id)
        operation_id = new_id("operation")
        if decision.wire["status"] != "open":
            return receipt(command, operation_id, tx.scope, status="rejected", code="DECISION_STALE")
        action = tx.action(p["actionId"])
        self._frame(tx, action)
        if action.state != ActionState.WAITING_DECISION:
            refuse("ACTION_STATE_CONFLICT")
        decision.close("answered", tx.now, answer=p["answer"], responder=principal)
        tx.save_decision(decision)
        checkpoint, event = self._record_intervention(tx, action, {"decisionId": decision.id,
            "decisionVersion": decision.version, "answer": decision.answer, "responder": principal}, kind="decision_answered")
        self._resume_after_answer(tx, action)
        return receipt(command, operation_id, tx.scope, status="committed", checkpoint_id=checkpoint,
                       outcome={"answer": decision.answer}, events=[event])

    def _operator_command(self, tx, principal, command):
        self._operator(tx, principal, command)
        w, p = command.wire, command.wire["payload"]
        action = tx.action(p["actionId"])
        self._frame(tx, action)
        if action.state not in {ActionState.SUSPENDED, ActionState.WAITING_DECISION, ActionState.ACTIVE}:
            refuse("ACTION_STATE_CONFLICT")
        outcome = {"operation": w["operation"], "adjudicator": principal, "payload": p}
        if w["operation"] in {"ReissueDecision", "ReassignDecisionResponder"}:
            previous = self._decision_matches(tx, command)
            if previous.answer is not None:
                refuse("DECISION_STALE", "accepted outcomes cannot be rewritten")
            if previous.wire["status"] == "open":
                previous.close("invalidated", tx.now)
                tx.save_decision(previous)
            question = previous.question
            if w["operation"] == "ReassignDecisionResponder":
                question = replace(question, responder_rule_id=p["responderRuleId"])
            checkpoint, event = self._record_intervention(tx, action, outcome)
            if w["operation"] == "ReissueDecision":
                decision = self._issue(tx, action, previous.wire["windowId"], question,
                                       previous=previous, seconds=p["deadlineSeconds"])
                if action.state == ActionState.SUSPENDED:
                    action.transition(ActionState.ACTIVE)
                if action.state == ActionState.ACTIVE:
                    action.transition(ActionState.WAITING_DECISION)
                action.error_code = None
            else:
                decision = self._issue(tx, action, previous.wire["windowId"], question, previous=previous,
                                       seconds=previous.timeout_seconds, deadline=previous.deadline)
                if previous.wire["status"] == "expired" or tx.now >= previous.deadline or action.state == ActionState.SUSPENDED:
                    self._invalidate(tx, decision, "DECISION_STALE")
                    action = tx.action(action.id)
            tx.save_action(action)
        else:
            if action.version != p["expectedActionVersion"]:
                refuse("ACTION_VERSION_CONFLICT")
            if action.state != ActionState.SUSPENDED:
                refuse("ACTION_STATE_CONFLICT", "action must be suspended before recovery")
            if w["operation"] == "ResumeSuspendedAction":
                if any(d.answer is None for d in tx.decisions_for(action.id)):
                    refuse("DECISION_STALE", "an unresolved question must be reissued or resolved manually")
                invocation = Command.parse(action.request)
                self._authorize(tx, action.principal_id, invocation)
                self._invocation_source(tx, invocation)
                checkpoint, event = self._record_intervention(tx, action, outcome)
                action.transition(ActionState.ACTIVE)
                action.error_code = None
            else:
                changes, resources = [], {}
                for adjustment in p["adjustments"]:
                    # Operator status is not permission to edit every resource.
                    adjustment_wire = {**w, "operation": "AdjustResource", "payload": {**adjustment, "reason": p["reason"]}}
                    self._authorize(tx, principal, Command.parse(canonical_bytes(adjustment_wire)))
                    tx.instance(adjustment["instance"])
                    changes.append(self._change(tx, resources, adjustment["instance"]["id"], adjustment["resourceId"],
                                                Quantity.from_wire(adjustment["delta"]), p["reason"]))
                outcome.update(manual=True, reason=p["reason"], outcomeNote=p["outcomeNote"], changes=changes,
                               executionLockDigest=tx.lock.digest, automatedCompletion=False)
                for decision in tx.open_decisions(action.id):
                    decision.close("invalidated", tx.now)
                    tx.save_decision(decision)
                checkpoint, event = self._record_intervention(tx, action, outcome, changes=changes, kind="action_resolved_manually")
                action.transition(ActionState.COMPLETED)
                if action.parent_id is None:
                    tx.scope.active_action_id = None
                    tx.release_lease = True
            tx.save_action(action)
        return receipt(command, new_id("operation"), tx.scope, status="committed", checkpoint_id=checkpoint,
                       outcome=outcome, events=[event])

    def _adjust_active(self, tx, principal, command):
        """Explicit operator adjustment is a checkpoint within the held frame."""
        self._operator(tx, principal, command)
        action = tx.action(tx.scope.active_action_id)
        self._frame(tx, action)
        p = command.wire["payload"]
        tx.instance(p["instance"])
        change = self._change(tx, {}, p["instance"]["id"], p["resourceId"], Quantity.from_wire(p["delta"]), p["reason"])
        outcome = {"manual": True, "adjudicator": principal, "reason": p["reason"], "changes": [change]}
        checkpoint, event = self._record_intervention(tx, action, outcome, changes=[change])
        for decision in tx.open_decisions(action.id):
            self._invalidate(tx, decision, "DECISION_STALE")
        value = receipt(command, new_id("operation"), tx.scope, status="committed", checkpoint_id=checkpoint,
                        outcome=outcome, events=[event])
        tx.save_receipt(principal, command.wire["idempotencyKey"], value)
        return value
