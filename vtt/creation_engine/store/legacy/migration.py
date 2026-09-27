"""Scope-wide legacy migration, serialized with runtime and legacy writers.

LEGACY/SHADOW never write legacy rows or live resource ledgers. Cutover consumes
an exact frozen report and installs occurrences/resources in one transaction.
Fixture status is a trusted provisioning argument, never a client payload.
"""

from contextlib import ExitStack

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vtt.creation_engine.adapter.mapping import (CHARACTER_TYPE, ITEM_TYPE, CONFIGURATION, VERSION, map_character)
from vtt.creation_engine.store.legacy.snapshots import characters, snapshot
from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.content import create_revision, new_id, resolve_lock
from vtt.creation_engine.evaluator.identity import evaluator_artifact
from vtt.creation_engine.kernel.records import TERMINAL, receipt, refuse
from vtt.creation_engine.policy import Grant, Policy
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.models import CeWorkspace
from vtt.creation_engine.store.migration_models import (CeLegacyGrant, CeLegacyInput, CeLegacyScopeLink, CeMigrationLedger,
    CeMigrationState, CeParityApproval, CeParityReport, CeRepresentation, CeWorkspaceCommand)
from vtt.creation_engine.store.policy_models import CePolicy
from vtt.creation_engine.store.runtime import RuntimeTransaction
from vtt.creation_engine.store.runtime_models import CeAction, CeInstance, CeResourceLedger, CeRuntimeScope
from vtt.models.campaign import Campaign
from vtt.models.campaign_member import CampaignMember
from vtt.models.user import User

OPERATIONS = frozenset(("MapLegacyCharacter", "BeginScopeShadow", "ApproveParityDifference",
                        "FreezeScopeForCutover", "CommitScopeCutover", "AbortScopeCutover"))


class MigrationService:
    def __init__(self, kernel, policy, *, configuration=CONFIGURATION):
        self.kernel, self.store, self.policy = kernel, kernel.store, policy
        self.configuration = configuration

    def provision(self, principal, *, campaign_id=None, fixture=False, session=None):
        """Trusted host entry point. Public provisioning always passes fixture=False."""
        with ExitStack() as stack:
            if session is None:
                session = stack.enter_context(Session(self.store.engine))
                stack.enter_context(session.begin())
            kind, source = ("campaign", campaign_id) if campaign_id is not None else ("sandbox", principal)
            session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"ce-provision:{kind}:{source}", 0))))
            link = session.get(CeLegacyScopeLink, (kind, source))
            if link:
                session.scalar(select(CeRuntimeScope).where(CeRuntimeScope.id == link.scope_id).with_for_update())
            user = session.scalar(select(User).where(User.id == principal).with_for_update(read=True))
            if user is None or not user.is_active or user.is_suspended or user.account_state != "active":
                refuse("OPERATION_FORBIDDEN")
            owner = principal
            if campaign_id is not None:
                campaign = session.scalar(select(Campaign).where(Campaign.id == campaign_id).with_for_update(read=True))
                member = session.scalar(select(CampaignMember).where(CampaignMember.campaign_id == campaign_id,
                                                                      CampaignMember.user_id == principal).with_for_update(read=True))
                if (campaign is None or campaign.deleted_at or campaign.status != "active" or
                    (campaign.owner_id != principal and not (member and member.status == "active" and member.is_operator()))):
                    refuse("NOT_FOUND")
                owner = campaign.owner_id
            if link:
                self._registration(RuntimeTransaction(self.store, session, session.get(CeRuntimeScope, link.scope_id)))
                return link.scope_id
            now, content = self.store.now(session), ContentStore(session)
            lock = resolve_lock([], fetch=content.revision, ruleset=self.kernel.ruleset,
                registry=self.kernel.schema_registry, evaluator=evaluator_artifact(), configuration=self.configuration)
            content.save_lock(lock, now=now)
            scope = CeRuntimeScope(id=new_id("scope"), kind=kind, campaign_id=campaign_id,
                owner_user_id=owner, fixture=fixture, migration_state="LEGACY", lock_id=lock.lock_id, time_watermark=now)
            session.add(scope)
            session.flush()
            session.add_all([CeLegacyScopeLink(source_type=kind, source_id=source, scope_id=scope.id),
                             CeMigrationState(scope_id=scope.id)])
            self.policy.bootstrap(RuntimeTransaction(self.store, session, scope), owner)
            return scope.id

    def open_campaign(self, principal, command, *, record_request=None):
        wire = command.wire
        with Session(self.store.engine) as session, session.begin():
            session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("ce-workspace:" + wire["workspaceId"], 0))))
            workspace = session.get(CeWorkspace, wire["workspaceId"])
            if workspace is None or workspace.owner_user_id != principal:
                refuse("NOT_FOUND")
            if wire["authorityEpoch"] != 1:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            key = (workspace.id, principal, wire["idempotencyKey"])
            existing = session.get(CeWorkspaceCommand, key)
            scope_id = self.provision(principal, campaign_id=wire["payload"]["legacyCampaignId"], session=session)
            if existing:
                if existing.request_digest != command.digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                return parse_strict_json(existing.receipt)
            tx = RuntimeTransaction(self.store, session, session.get(CeRuntimeScope, scope_id))
            result = receipt(command, new_id("open"), tx.scope, status="committed")
            # Workspace creation keys must not occupy the new runtime scope's
            # receipt namespace. Recovery uses this workspace command's retry.
            session.add(CeWorkspaceCommand(workspace_id=key[0], principal_id=principal, idempotency_key=key[2],
                scope_id=scope_id, request_digest=command.digest, receipt=canonical_bytes(result)))
            self.policy.audit(tx, principal, "OpenLegacyCampaignScope", {"commandId": wire["commandId"]})
            self.kernel.fault("before_commit")
        self.kernel.fault("after_commit")
        return result

    def authorized(self, tx, principal_id, wire):
        principal = self.policy.require_scope(tx, principal_id)
        if self.policy.policies(tx).allows(principal, tx.scope.id, "operates"):
            return True
        if wire["operation"] == "ApproveParityDifference":
            _, difference = self._difference(tx, wire["payload"]["discrepancyId"])
            return principal_id == difference["controllerId"]
        return False

    def _registration(self, tx):
        locked = tx.lock.wire
        if (locked["ruleset"] != self.kernel.ruleset.artifact() or
            locked["schemaBundle"] != self.kernel.schema_registry.artifact() or
            locked["configurationDigest"] != self.kernel.configuration_digest or
            locked["evaluator"] != evaluator_artifact() or
            locked["unitTableDigest"] != self.kernel.ruleset.units.digest()):
            refuse("EXECUTION_LOCK_MISMATCH")

    def submit(self, principal, command, *, record_request=None):
        w = command.wire
        with self.store.transaction(w["scopeId"]) as tx:
            self.kernel._authorize(tx, principal, command)
            self._registration(tx)
            if w["authorityEpoch"] != tx.scope.authority_epoch:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            existing = tx.receipt(principal, w["idempotencyKey"])
            if existing:
                if existing["requestDigest"] != command.digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                return existing
            if w["expectedScopeVersion"] != tx.scope.state_version:
                refuse("SCOPE_VERSION_CONFLICT")
            handlers = {"MapLegacyCharacter": self._map, "BeginScopeShadow": self._shadow,
                "ApproveParityDifference": self._approve, "FreezeScopeForCutover": self._freeze,
                "CommitScopeCutover": self._commit, "AbortScopeCutover": self._abort}
            handlers[w["operation"]](tx, principal, w["payload"])
            tx.scope.state_version += 1
            result = receipt(command, new_id("migration"), tx.scope, status="committed")
            tx.save_receipt(principal, w["idempotencyKey"], result)
            if record_request:
                record_request(tx, principal, command)
            self.policy.audit(tx, principal, w["operation"], {"commandId": w["commandId"], "state": tx.scope.migration_state})
            self.kernel.fault("before_commit")
        self.kernel.fault("after_commit")
        return result

    @staticmethod
    def _state(tx, allowed):
        if tx.scope.migration_state not in allowed:
            refuse("MIGRATION_STATE_CONFLICT")
        return tx.session.get(CeMigrationState, tx.scope.id)

    @staticmethod
    def _ledger(tx, source_type, source_id, version=VERSION):
        key = (source_type, source_id, version)
        row = tx.session.get(CeMigrationLedger, key)
        if row is not None and row.scope_id != tx.scope.id:
            refuse("SCOPE_TRANSFER_UNSUPPORTED")
        if row is None:
            row = CeMigrationLedger(source_type=source_type, source_id=source_id, migration_version=version,
                opaque_id=new_id("legacy"), scope_id=tx.scope.id)
            tx.session.add(row)
            tx.session.flush()
        return row

    def _map(self, tx, principal, payload):
        self._state(tx, {"LEGACY", "SHADOW"})
        if payload["migrationVersion"] != VERSION:
            refuse("SEMANTIC_INVALID", "unsupported migration version")
        source_id = payload["source"]["sourceId"]
        if source_id not in {c.id for c in characters(tx)}:
            refuse("NOT_FOUND")
        self._ledger(tx, "vtt.character", source_id)

    def _sources(self, tx):
        rows = characters(tx)
        mapped = {row.source_id: row.opaque_id for row in tx.session.scalars(select(CeMigrationLedger).where(
            CeMigrationLedger.scope_id == tx.scope.id, CeMigrationLedger.source_type == "vtt.character",
            CeMigrationLedger.migration_version == VERSION))}
        if not rows or set(mapped) != {row.id for row in rows}:
            refuse("PARITY_UNRESOLVED", "every active character must be mapped together")
        sources = [{"instanceId": mapped[c.id], "snapshot": snapshot(tx, c)} for c in rows]
        if len(canonical_bytes(sources)) > self.kernel.max_request_bytes:
            refuse("PAYLOAD_TOO_LARGE", "migration preview exceeds the configured interactive byte bound")
        if sum(1 + sum(len(s["snapshot"][k]) for k in ("equipment", "inventory", "spells")) for s in sources) > 128:
            refuse("BUDGET_EXCEEDED", "scope migration exceeds the interactive instance bound")
        return sources

    def _refresh(self, tx):
        state = tx.session.get(CeMigrationState, tx.scope.id)
        sources = self._sources(tx)
        digest = content_digest(sources)
        old = tx.session.get(CeParityReport, state.report_id) if state.report_id else None
        if old and old.source_digest == digest:
            return old
        if tx.scope.migration_state == "FROZEN_FOR_CUTOVER":
            refuse("PARITY_UNRESOLVED", "frozen legacy snapshot changed")
        report = {"reportId": new_id("parity"), "scopeId": tx.scope.id, "characters": [], "differences": []}
        for source in sources:
            mapped = map_character(source["snapshot"], source["instanceId"], tx.scope.id)
            c = source["snapshot"]["character"]
            report["characters"].append({"sourceId": c["id"], "instanceId": source["instanceId"],
                "fields": mapped["fields"], "unsupported": mapped["unsupported"]})
            for difference in mapped["differences"]:
                report["differences"].append({**difference, "discrepancyId": new_id("difference"),
                    "sourceId": c["id"], "controllerId": c["user_id"], "instanceId": source["instanceId"]})
        row = CeParityReport(id=report["reportId"], scope_id=tx.scope.id, source_digest=digest,
            digest=content_digest(report), canonical=canonical_bytes(report), snapshots=canonical_bytes(sources))
        tx.session.add(row)
        state.report_id = row.id
        tx.session.flush()
        return row

    def _shadow(self, tx, principal, payload):
        self._state(tx, {"LEGACY"})
        if payload["ruleset"] != self.kernel.ruleset.artifact():
            refuse("EXECUTION_LOCK_MISMATCH")
        self._refresh(tx)
        tx.scope.migration_state = "SHADOW"

    def preview(self, principal, scope_id, *, character_id=None):
        with self.store.transaction(scope_id) as tx:
            actor = self.policy.require_scope(tx, principal)
            self._registration(tx)
            operator = self.policy.policies(tx).allows(actor, scope_id, "operates")
            state = self._state(tx, {"SHADOW", "FROZEN_FOR_CUTOVER", "ENGINE"})
            report = tx.session.get(CeParityReport, state.report_id) if tx.scope.migration_state == "ENGINE" else self._refresh(tx)
            value = parse_strict_json(report.canonical)
            if not operator:
                owned = {s["snapshot"]["character"]["id"] for s in parse_strict_json(report.snapshots)
                         if s["snapshot"]["character"]["user_id"] == principal}
                if character_id not in owned:
                    refuse("NOT_FOUND")
            if character_id is not None:
                value["characters"] = [c for c in value["characters"] if c["sourceId"] == character_id]
                value["differences"] = [d for d in value["differences"] if d["sourceId"] == character_id]
                if not value["characters"]:
                    refuse("NOT_FOUND")
            if operator:
                value["parityReportDigest"] = report.digest
            value["stateVersion"], value["authorityEpoch"] = tx.scope.state_version, tx.scope.authority_epoch
            return value

    def _difference(self, tx, discrepancy_id):
        state = tx.session.get(CeMigrationState, tx.scope.id)
        report = tx.session.get(CeParityReport, state.report_id) if state and state.report_id else None
        if report:
            for difference in parse_strict_json(report.canonical)["differences"]:
                if difference["discrepancyId"] == discrepancy_id:
                    return report, difference
        refuse("NOT_FOUND")

    def _approve(self, tx, principal, payload):
        self._state(tx, {"SHADOW", "FROZEN_FOR_CUTOVER"})
        self._refresh(tx)
        report, difference = self._difference(tx, payload["discrepancyId"])
        if payload["resolution"] == "keep_legacy_override" and not difference["keepLegacyAllowed"]:
            refuse("PARITY_UNRESOLVED", "a conflicting representation cannot become a second authority")
        actor = self.policy.require_scope(tx, principal)
        capacities = (["controller"] if principal == difference["controllerId"] else [])
        if self.policy.policies(tx).allows(actor, tx.scope.id, "operates"):
            capacities.append("operator")
        if not capacities:
            refuse("OPERATION_FORBIDDEN")
        for capacity in capacities:
            key = (report.id, difference["discrepancyId"], principal, capacity)
            old = tx.session.get(CeParityApproval, key)
            if old and old.resolution != payload["resolution"]:
                refuse("PARITY_UNRESOLVED")
            if old is None:
                tx.session.add(CeParityApproval(report_id=key[0], discrepancy_id=key[1], principal_id=principal,
                    capacity=capacity, resolution=payload["resolution"], reason=payload["reason"]))

    @staticmethod
    def _quiescent(tx):
        if tx.scope.active_action_id or tx.session.scalar(select(CeAction.id).where(
            CeAction.scope_id == tx.scope.id, CeAction.state.not_in(TERMINAL)).limit(1)):
            refuse("SCOPE_NOT_QUIESCENT")

    def _freeze(self, tx, principal, payload):
        state = self._state(tx, {"SHADOW"})
        if not tx.scope.fixture:
            refuse("CUTOVER_FIXTURE_ONLY")
        self._quiescent(tx)
        state.frozen_digest = self._refresh(tx).source_digest
        tx.scope.migration_state = "FROZEN_FOR_CUTOVER"

    def _abort(self, tx, principal, payload):
        state = self._state(tx, {"FROZEN_FOR_CUTOVER"})
        state.frozen_digest = None
        tx.scope.migration_state = "SHADOW"

    def _commit(self, tx, principal, payload):
        state = self._state(tx, {"FROZEN_FOR_CUTOVER"})
        if not tx.scope.fixture:
            refuse("CUTOVER_FIXTURE_ONLY")
        self._quiescent(tx)
        report = self._refresh(tx)
        if report.digest != payload["parityReportDigest"] or report.source_digest != state.frozen_digest:
            refuse("PARITY_UNRESOLVED")
        for difference in parse_strict_json(report.canonical)["differences"]:
            rows = list(tx.session.scalars(select(CeParityApproval).where(CeParityApproval.report_id == report.id,
                CeParityApproval.discrepancy_id == difference["discrepancyId"])))
            capacities = set()
            for approval in rows:
                actor = self.policy.require_scope(tx, approval.principal_id)
                if (approval.capacity == "controller" and actor.id == difference["controllerId"] or
                    approval.capacity == "operator" and self.policy.policies(tx).allows(actor, tx.scope.id, "operates")):
                    capacities.add(approval.capacity)
            if capacities != {"operator", "controller"} or len({r.resolution for r in rows}) != 1:
                refuse("PARITY_UNRESOLVED")
        roots = []
        for source in parse_strict_json(report.snapshots):
            roots.extend(self._install_character(tx, source))
        lock = resolve_lock(roots, fetch=tx.content.revision, ruleset=self.kernel.ruleset,
            registry=self.kernel.schema_registry, evaluator=evaluator_artifact(), configuration=self.configuration)
        tx.content.save_lock(lock, now=tx.now)
        tx.scope.lock_id, tx.lock = lock.lock_id, lock
        tx.scope.migration_state = "ENGINE"
        tx.scope.authority_epoch += 1
        state.cutover_version = tx.scope.state_version + 1
        self.policy.changed(tx, self.kernel, principal, reason="scope cutover")
        state.cutover_version = tx.scope.state_version + 1

    def _revision(self, tx, owner, name, schema, content):
        workspace = tx.content.workspace_for(owner, now=tx.now)
        definition = tx.content.add_definition(workspace.id, name[:200], schema.type_id, now=tx.now)
        revision = create_revision(definition.id, schema, content, registry=self.kernel.schema_registry,
            author_user_id=owner, provenance={"kind": "imported_legacy_baseline", "migrationVersion": VERSION}, now=tx.now)
        tx.content.append_revision(revision)
        return revision

    def _install_character(self, tx, source):
        snap, instance_id = source["snapshot"], source["instanceId"]
        c = snap["character"]
        mapped = map_character(snap, instance_id, tx.scope.id)
        revision = self._revision(tx, c["user_id"], c["name"], CHARACTER_TYPE, mapped["content"])
        tx.session.add(CeInstance(id=instance_id, scope_id=tx.scope.id, revision_id=revision.id, controller_user_id=c["user_id"]))
        tx.session.flush()
        tx.session.add(CeLegacyInput(instance_id=instance_id, bases=canonical_bytes(mapped["content"]["bases"]), overrides=b"{}"))
        for choice, option in mapped["content"]["selections"].items():
            tx.session.add(CeLegacyGrant(id=new_id("grant"), source_instance_id=instance_id, choice_id=choice,
                canonical=canonical_bytes({"choiceId": choice, "optionId": option, "provenance": "imported_selection", "manual": True})))
        for key, value in mapped["resources"].items():
            spec = next(r for r in self.kernel.ruleset.resources if r.id == key)
            tx.session.add(CeResourceLedger(instance_id=instance_id, resource_id=key, unit=value["unit"],
                current=canonical_bytes(Rational.of(value["current"]).to_wire()),
                maximum=canonical_bytes(Rational.of(value["maximum"]).to_wire()), adjust_bound_policy=spec.adjust_bound_policy))
        self._instance_policy(tx, instance_id, c["user_id"])
        tx.session.add(CeRepresentation(source_type="vtt.character", source_id=c["id"], scope_id=tx.scope.id, instance_id=instance_id))
        for token in snap["tokens"]:
            self._ledger(tx, "vtt.token", token["id"])
            tx.session.add(CeRepresentation(source_type="vtt.token", source_id=token["id"], scope_id=tx.scope.id, instance_id=instance_id))
        roots = [revision.ref()]
        for kind in ("equipment", "inventory", "spells"):
            for item in snap[kind]:
                ledger = self._ledger(tx, "vtt." + kind, item["id"])
                item_revision = self._revision(tx, c["user_id"], item["name"], ITEM_TYPE,
                    {"name": item["name"], "legacyMetadata": item, "manual": True})
                tx.session.add(CeInstance(id=ledger.opaque_id, scope_id=tx.scope.id, revision_id=item_revision.id,
                    controller_user_id=c["user_id"], holder_id=instance_id))
                tx.session.flush()
                tx.session.add(CeLegacyInput(instance_id=ledger.opaque_id, bases=b"{}", overrides=b"{}",
                                            equipped=item.get("is_equipped")))
                tx.session.add(CeRepresentation(source_type="vtt." + kind, source_id=item["id"],
                                                scope_id=tx.scope.id, instance_id=ledger.opaque_id))
                self._instance_policy(tx, ledger.opaque_id, c["user_id"])
                roots.append(item_revision.ref())
        return roots

    @staticmethod
    def _instance_policy(tx, instance_id, controller):
        policy = Policy(instance_id, tx.scope.id, tuple(Grant(op, roles=("member",)) for op in ("read", "explain", "export")) +
            tuple(Grant(op, principals=(controller,)) for op in ("controls", "invoke", "adjust", "respond")) +
            (Grant("compute", roles=("engine",)),))
        private = Policy(instance_id + ":private", instance_id,
            tuple(Grant(op, principals=(controller,)) for op in ("read", "explain", "export")), owner_id=controller)
        for row in (policy, private):
            tx.session.add(CePolicy(scope_id=tx.scope.id, policy_id=row.id, version=tx.scope.policy_version,
                                   canonical=canonical_bytes(row.wire())))
