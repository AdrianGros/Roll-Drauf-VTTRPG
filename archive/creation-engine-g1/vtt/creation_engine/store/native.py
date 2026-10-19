"""Owned sandbox provisioning and bounded native flame execution for WP8."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vtt.creation_engine.adapter import mapping
from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.compiler import flame
from vtt.creation_engine.compiler import runtime as registered
from vtt.creation_engine.content import new_id, resolve_lock
from vtt.creation_engine.evaluator.identity import evaluator_artifact
from vtt.creation_engine.kernel.activity import Activity, Window
from vtt.creation_engine.kernel.records import Action, ActionState, receipt, refuse
from vtt.creation_engine.kernel.service import Adjustment, Prepared, RollAdjustment
from vtt.creation_engine.policy import Grant, Policy, Principal
from vtt.creation_engine.policy.public_errors import safe_code
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.authoring import AuthoringService
from vtt.creation_engine.store.authoring_models import CeWorkspaceResult
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.migration_models import CeLegacyInput, CeWorkspaceCommand
from vtt.creation_engine.store.models import CeDefinition, CeRevision, CeWorkspace
from vtt.creation_engine.store.policy_models import CePolicy
from vtt.creation_engine.store.runtime import RuntimeTransaction
from vtt.creation_engine.store.runtime_models import CeInstance, CeResourceLedger, CeRuntimeScope
from vtt.creation_engine.types import parse_reference, RevisionRef
from vtt.creation_engine.units import Quantity


class NativeService:
    def __init__(self, kernel, policy):
        self.kernel, self.policy, self.store = kernel, policy, kernel.store

    def catalog(self, principal):
        with Session(self.store.engine) as session, session.begin():
            AuthoringService._account(session, principal)
            content = ContentStore(session)
            workspace = content.workspace_for(principal, now=self.store.now(session))
            revisions = []
            for row in session.scalars(select(CeRevision).join(CeDefinition).where(
                    CeDefinition.workspace_id == workspace.id, CeDefinition.tombstoned_at.is_(None)).order_by(CeRevision.created_at, CeRevision.id)):
                revision = content.revision(row.id)
                quality = parse_strict_json(revision.provenance).get("declaredQuality")
                if revision.schema_type == mapping.CHARACTER_TYPE or revision.schema_type == flame.ITEM_TYPE and quality == "runtime_ready":
                    revisions.append({"revision": revision.ref().to_wire(), "name": revision.content["name"],
                                      "schemaType": revision.schema_type.to_wire()})
            scopes = []
            for scope in session.scalars(select(CeRuntimeScope).where(CeRuntimeScope.kind == "sandbox",
                    CeRuntimeScope.owner_user_id == principal, CeRuntimeScope.deleted.is_(False)).order_by(CeRuntimeScope.id)):
                if content.lock(scope.lock_id).wire["configurationDigest"] == self.kernel.configuration_digest:
                    scopes.append({"scopeId": scope.id})
            return {"workspaceId": workspace.id, "ruleset": self.kernel.ruleset.artifact(), "revisions": revisions, "sandboxes": scopes}

    def summary(self, gateway, principal, scope_id):
        with gateway._transaction(scope_id) as tx:
            audience = gateway._audience(tx, principal)
            if tx.scope.kind != "sandbox" or tx.scope.owner_user_id != principal:
                refuse("NOT_FOUND")
            instances = [gateway._project(tx, audience, document) for document in gateway.snapshot_documents(tx)]
            decisions = []
            for decision in tx.open_decisions():
                policies = self.policy.policies(tx)
                if (all(policies.allows_audience(audience, decision.question.policy_id, op) for op in ("read", "respond")) and
                        all(policies.allows_audience(audience, ref["id"]) for ref in decision.wire["targets"])):
                    self.kernel._eligible(tx, principal, decision)
                    decisions.append(decision.wire)
            active = tx.action(tx.scope.active_action_id) if tx.scope.active_action_id else None
            return {"scopeId": scope_id, "stateVersion": tx.scope.state_version, "authorityEpoch": tx.scope.authority_epoch,
                    "executionLockDigest": tx.lock.digest, "revisions": [ref.to_wire() for ref in tx.lock.revisions],
                    "instances": [document for document in instances if document is not None], "decisions": decisions,
                    "activeAction": {"actionId": active.id, "version": active.version, "state": active.state,
                                     "errorCode": safe_code(active.error_code)} if active else None}

    def create_sandbox(self, principal, command):
        wire, payload = command.wire, command.wire["payload"]
        with Session(self.store.engine) as session, session.begin():
            session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("ce-workspace:" + wire["workspaceId"], 0))))
            workspace = session.get(CeWorkspace, wire["workspaceId"])
            if workspace is None or workspace.owner_user_id != principal:
                refuse("NOT_FOUND")
            AuthoringService._account(session, principal)
            if wire["authorityEpoch"] != 1:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            key = (workspace.id, principal, wire["idempotencyKey"])
            previous = session.get(CeWorkspaceCommand, key)
            if previous:
                if previous.request_digest != command.digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                return parse_strict_json(previous.receipt)
            if payload["ruleset"] != self.kernel.ruleset.artifact():
                refuse("EXECUTION_LOCK_MISMATCH")
            content, now = ContentStore(session), self.store.now(session)
            def fetch(revision_id):
                revision = content.revision(revision_id)
                definition = content.definition(revision.definition_id) if revision else None
                if definition is None or definition.workspace_id != workspace.id or definition.tombstoned_at:
                    refuse("NOT_FOUND")
                return revision
            roots = [parse_reference(ref, accept=(RevisionRef,)) for ref in payload["revisions"]]
            lock = resolve_lock(roots, fetch=fetch, ruleset=self.kernel.ruleset, registry=self.kernel.schema_registry,
                                evaluator=evaluator_artifact(), configuration=registered.CONFIGURATION)
            content.save_lock(lock, now=now)
            scope = CeRuntimeScope(id=new_id("scope"), kind="sandbox", owner_user_id=principal, fixture=False,
                                   migration_state="ENGINE", lock_id=lock.lock_id, time_watermark=now)
            session.add(scope); session.flush()
            tx = RuntimeTransaction(self.store, session, scope)
            self.policy.bootstrap(tx, principal)
            question_policy = Policy(registered.DECISION_POLICY, scope.id,
                tuple(Grant(op, principals=(principal,)) for op in ("read", "respond", "explain", "export")))
            session.add(CePolicy(scope_id=scope.id, policy_id=question_policy.id, version=scope.policy_version,
                                 canonical=canonical_bytes(question_policy.wire())))
            result = receipt(command, new_id("sandbox"), scope, status="committed")
            session.add(CeWorkspaceCommand(workspace_id=workspace.id, principal_id=principal, idempotency_key=key[2],
                scope_id=scope.id, request_digest=command.digest, receipt=canonical_bytes(result)))
            session.flush()
            session.add(CeWorkspaceResult(workspace_id=workspace.id, principal_id=principal, idempotency_key=key[2],
                result=canonical_bytes({"scopeId": scope.id, "executionLockDigest": lock.digest, "revisions": [r.to_wire() for r in roots]})))
            self.kernel.fault("before_commit")
        self.kernel.fault("after_commit")
        return result

    def instantiate(self, principal, command, *, record_request=None):
        wire, payload = command.wire, command.wire["payload"]
        with self.store.transaction(wire["scopeId"]) as tx:
            self.kernel._authorize(tx, principal, command)
            if wire["authorityEpoch"] != tx.scope.authority_epoch:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            previous = tx.receipt(principal, wire["idempotencyKey"])
            if previous:
                if previous["requestDigest"] != command.digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                return previous
            self.kernel._authority(tx, command, check_version=True)
            if tx.scope.active_action_id:
                refuse("SCOPE_BUSY")
            ref = parse_reference(payload["revision"], accept=(RevisionRef,))
            if ref not in tx.lock.revisions:
                refuse("REVISION_NOT_IN_LOCK")
            revision = tx.content.revision(ref.id)
            if revision is None or revision.ref() != ref:
                refuse("REVISION_NOT_IN_LOCK")
            self.kernel.schema_registry.validate(revision.schema_type, revision.content)
            holder = tx.instance(payload["holder"]) if payload["holder"] else None
            if holder and holder.controller_user_id != principal:
                refuse("OPERATION_FORBIDDEN")
            instance = CeInstance(id=new_id("instance"), scope_id=tx.scope.id, revision_id=revision.id,
                                  holder_id=holder.id if holder else None, controller_user_id=principal)
            tx.session.add(instance); tx.session.flush()
            self._inputs(tx, instance, revision)
            self._instance_policy(tx, instance.id, principal)
            if registered.DECISION_POLICY not in self.policy.policies(tx).policies:
                question_policy = Policy(registered.DECISION_POLICY, tx.scope.id,
                    tuple(Grant(op, roles=("member",)) for op in ("read", "respond", "explain", "export")))
                tx.session.add(CePolicy(scope_id=tx.scope.id, policy_id=question_policy.id, version=tx.scope.policy_version,
                                       canonical=canonical_bytes(question_policy.wire())))
            action_id, checkpoint_id = new_id("action"), new_id("checkpoint")
            plan = Activity("g1.instantiate", (Window("instantiate", (), (), 1),))
            action = Action(action_id, tx.scope.id, principal, command.canonical, plan.canonical(), ActionState.COMPLETED,
                            tx.now, action_id, next_window=1, last_checkpoint_id=checkpoint_id)
            tx.claim_lease(self.kernel.worker_id); tx.release_lease = True
            tx.scope.state_version += 1
            tx.save_action(action)
            outcome = {"instanceId": instance.id, "revision": ref.to_wire(), "reason": payload["reason"], "changes": []}
            tx.save_checkpoint(action, checkpoint_id, outcome, (), (), (), index=0)
            event_id = tx.event(action, "instance_created", checkpoint_id)
            result = receipt(command, action.id, tx.scope, status="committed", checkpoint_id=checkpoint_id, outcome=outcome, events=[event_id])
            tx.save_receipt(principal, wire["idempotencyKey"], result)
            if record_request:
                record_request(tx, principal, command)
            self.kernel.fault("before_commit")
        self.kernel.fault("after_commit")
        return result

    def _inputs(self, tx, instance, revision):
        if revision.schema_type == flame.ITEM_TYPE:
            f = registered.runtime_content(revision)
            tx.session.add(CeLegacyInput(instance_id=instance.id, bases=b"{}", overrides=b"{}", equipped=False))
            self._resource(tx, instance.id, "charges", "g1:charge", f["initialCharges"], f["maximumCharges"])
        elif revision.schema_type == mapping.CHARACTER_TYPE and instance.holder_id is None:
            c = revision.content
            tx.session.add(CeLegacyInput(instance_id=instance.id, bases=canonical_bytes(c["bases"]), overrides=b"{}"))
            for column, resource, maximum in (("hp_current", "hp", "hp_max"), ("mana_current", "fokus", "fokus_max")):
                value = Quantity.from_wire(c["bases"][maximum])
                self._resource(tx, instance.id, resource, value.unit, c["legacyMetadata"]["character"][column], value.value.floor())
        else:
            refuse("SEMANTIC_INVALID", "this schema has no native sandbox instantiator")

    @staticmethod
    def _instance_policy(tx, instance_id, controller):
        # These copies belong to the private sandbox. Calculation and private
        # source disclosure are separate grants, even for the same owner.
        root = Policy(instance_id, tx.scope.id, tuple(Grant(op, principals=(controller,)) for op in
            ("read", "explain", "export", "controls", "invoke", "adjust", "respond")) + (Grant("compute", roles=("engine",)),))
        private = Policy(instance_id + ":private", instance_id, tuple(Grant(op, principals=(controller,)) for op in
            ("read", "explain", "export")) + (Grant("compute", roles=("engine",)),), owner_id=controller,
            owner_grants=(Grant("compute", roles=("engine",)),))
        for policy in (root, private):
            tx.session.add(CePolicy(scope_id=tx.scope.id, policy_id=policy.id, version=tx.scope.policy_version,
                                   canonical=canonical_bytes(policy.wire())))

    @staticmethod
    def _resource(tx, instance, resource, unit, current, maximum):
        if type(current) is not int or type(maximum) is not int or not 0 <= current <= maximum:
            refuse("RESOURCE_BOUND_EXCEEDED")
        tx.session.add(CeResourceLedger(instance_id=instance, resource_id=resource, unit=unit,
            current=canonical_bytes(Rational.of(current).to_wire()), maximum=canonical_bytes(Rational.of(maximum).to_wire()),
            adjust_bound_policy="clamp_report_delta"))

    def prepare(self, tx, action, window, fuel):
        payload = parse_strict_json(action.request)["payload"]
        source = tx.instance(payload["sourceInstance"])
        policies = self.policy.policies(tx)
        engine = Principal(0, frozenset({"engine"}))
        if (not policies.allows(engine, source.id + ":private", "compute") or
                any(not policies.allows(engine, target["id"], "compute") for target in payload["targets"])):
            refuse("OPERATION_FORBIDDEN", "native calculation lacks its source compute grant")
        revision = tx.content.revision(source.revision_id)
        f = registered.runtime_content(revision)
        activity = payload["activityId"]
        if activity in {registered.ACTIVATE, registered.HIT, registered.DAMAGE} and source.holder_id:
            row = tx.session.get(CeLegacyInput, source.id)
            if row is None or row.equipped is not True:
                refuse("SEMANTIC_INVALID", "held items must be explicitly equipped")
        if activity == registered.ACTIVATE:
            if payload["targets"]:
                refuse("SEMANTIC_INVALID")
            return Prepared({"visibleFlames": True, "duration": f["duration"], "damage": False})
        if activity == registered.HIT:
            actor = tx.instance(payload["actorInstance"])
            if tx.content.revision(actor.revision_id).schema_type != mapping.CHARACTER_TYPE:
                refuse("SEMANTIC_INVALID", "a hit must be attested for an imported actor")
            if len(payload["targets"]) != 1:
                refuse("SEMANTIC_INVALID", "a confirmed hit has exactly one target")
            tx.resource(payload["targets"][0]["id"], "hp")
            return Prepared({"manual": True, "adjudicator": action.principal_id, "hitConfirmed": True,
                             "target": payload["targets"][0], "flameDecision": tx.answers(action.id).get(registered.FLAME_QUESTION)})
        if activity == registered.DAMAGE:
            if action.parent_id is None:
                refuse("OPERATION_FORBIDDEN", "damage is a declared child of a committed hit")
            parent = tx.action(action.parent_id)
            parent_payload = parse_strict_json(parent.request)["payload"]
            hit = tx.checkpoint(parent.id, 0)
            if (parent_payload["activityId"] != registered.HIT or parent_payload["sourceInstance"] != payload["sourceInstance"]
                    or parent_payload["targets"] != payload["targets"] or not hit or not hit["outcome"]["result"]["hitConfirmed"]
                    or tx.answers(parent.id).get(registered.FLAME_QUESTION) != {"kind": "boolean", "value": True}):
                refuse("OPERATION_FORBIDDEN")
            return Prepared({"damageType": "fire", "parentHitCheckpoint": hit["checkpointId"]}, roll_adjustments=(
                RollAdjustment(payload["targets"][0]["id"], "hp", "fire", Quantity(Rational.of(-1), "rdl:hp"), "authored fire damage"),))
        if activity == registered.RECOVER + f["recovery"]:
            if payload["targets"]:
                refuse("SEMANTIC_INVALID")
            resource = tx.resource(source.id, "charges")
            return Prepared({"manual": True, "adjudicator": action.principal_id, "attestedEvent": f["recovery"]},
                (Adjustment(source.id, "charges", Quantity(resource["maximum"] - resource["current"], "g1:charge"), "confirmed recovery event"),))
        refuse("SEMANTIC_INVALID")

    def responders(self, tx, rule, action):
        if rule != "g1.actor-controller":
            refuse("SEMANTIC_INVALID")
        actor = tx.instance(parse_strict_json(action.request)["payload"]["actorInstance"])
        principal = self.policy.require_scope(tx, actor.controller_user_id)
        if not self.policy.policies(tx).allows(principal, actor.id, "controls"):
            return ()
        return (actor.controller_user_id,)

    def drive(self, scope_id):
        """Resume only this host's native frames. Each step is separately fenced."""
        with self.store.transaction(scope_id) as tx:
            if tx.lock.wire["configurationDigest"] != self.kernel.configuration_digest or not tx.scope.active_action_id:
                return
            action = tx.action(tx.scope.active_action_id)
            if action.state != ActionState.ACTIVE or Activity.restore(action.plan).id != registered.HIT:
                return
            payload = parse_strict_json(action.request)["payload"]
            answer = tx.answers(action.id).get(registered.FLAME_QUESTION)
            if answer is None:
                return
            action_id, principal, checkpoint_id = action.id, action.principal_id, action.last_checkpoint_id
            index = action.next_window
            key = "child:" + content_digest({"parent": action.id})[7:]
            wire = {"contractVersion": "1.1.3", "commandId": key, "idempotencyKey": key, "scopeId": scope_id,
                "expectedScopeVersion": tx.scope.state_version, "authorityEpoch": tx.scope.authority_epoch,
                "executionLockDigest": tx.lock.digest, "operation": "InvokeActivity", "payload": {**payload, "activityId": registered.DAMAGE}}
            previous = tx.receipt(principal, key)
            if previous:
                # Recover the exact original child request after a crash. Scope
                # versions in a new request would change its idempotency digest.
                wire = parse_strict_json(tx.action(previous["operationId"]).request)
        if answer == {"kind": "boolean", "value": True}:
            child = self.kernel.spawn_child(principal, canonical_bytes(wire), parent_action_id=action_id, checkpoint_id=checkpoint_id)
            if child["status"] != "committed":
                return  # failed child leaves the committed hit suspended for explicit recovery
        fence = self.kernel.claim(scope_id)
        self.kernel.advance(scope_id, action_id, window_index=index, fence=fence)
