"""Private authoring transactions for the approved A1 draft operations.

Workspace keys are shared with migration provisioning. Draft keys, answer logs,
compiler snapshots, content versions and revisions are committed atomically.
An authenticated retry is resolved before testing the now-outdated draft version.
"""

from contextlib import contextmanager

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.compiler import flame
from vtt.creation_engine.compiler.catalog import OPERATIONS, QUALITIES, SCHEMA_TYPES, guide_for, registry, quality_gates
from vtt.creation_engine.content import DraftAnswer, SchemaTypeRef, create_revision, new_id, require_draft_version
from vtt.creation_engine.kernel.records import Command, KernelError, refuse
from vtt.creation_engine.store.authoring_models import CeAuthoringSnapshot, CeDraftCommand, CeWorkspaceResult
from vtt.creation_engine.store.content import ContentStore
from vtt.creation_engine.store.migration_models import CeWorkspaceCommand
from vtt.creation_engine.store.models import CeDraft, CeWorkspace
from vtt.models.user import User


class QualityClaimUnmet(KernelError):
    def __init__(self, gates):
        super().__init__("QUALITY_CLAIM_UNMET", "the declared quality has unmet gates")
        self.gates = gates


class AuthoringService:
    def __init__(self, runtime_store, *, fault=None, native_runtime=False):
        self.store, self.registry = runtime_store, registry()
        self.native_runtime = native_runtime
        self.fault = fault or (lambda point: None)

    def schema_registry(self, schema_type):
        # Preserve the original host registration and its drift checks. New
        # profiles never amend the artifact pinned by existing flame drafts.
        return self.registry if schema_type == flame.ITEM_TYPE else registry(schema_type)

    @staticmethod
    def _account(session, principal):
        user = session.scalar(select(User).where(User.id == principal).with_for_update(read=True))
        if user is None or not user.is_active or user.is_suspended or user.account_state != "active":
            refuse("OPERATION_FORBIDDEN")

    @contextmanager
    def _workspace(self, principal, workspace_id):
        with Session(self.store.engine) as session, session.begin():
            session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("ce-workspace:" + workspace_id, 0))))
            workspace = session.get(CeWorkspace, workspace_id)
            if workspace is None or workspace.owner_user_id != principal:
                refuse("NOT_FOUND")
            self._account(session, principal)
            yield session, ContentStore(session)

    def workspace(self, principal):
        with Session(self.store.engine) as session, session.begin():
            self._account(session, principal)
            content = ContentStore(session)
            workspace = content.workspace_for(principal, now=self.store.now(session))
            drafts = session.scalars(select(CeDraft).where(CeDraft.workspace_id == workspace.id).order_by(CeDraft.created_at, CeDraft.id))
            return {"workspaceId": workspace.id, "authorityEpoch": 1, "schemaTypes": [kind.to_wire() for kind in SCHEMA_TYPES],
                    "drafts": [{"draftId": d.id, "version": d.version, "authoringLocale": d.authoring_locale,
                                "schemaType": {"typeId": d.schema_type_id, "version": d.schema_version}} for d in drafts]}

    def _draft(self, session, content, workspace_id, draft_id):
        row = session.scalar(select(CeDraft).where(CeDraft.id == draft_id, CeDraft.workspace_id == workspace_id).with_for_update())
        if row is None:
            refuse("NOT_FOUND")
        draft = content.draft(draft_id)
        if draft.schema_bundle != canonical_bytes(self.schema_registry(draft.schema_type).artifact()):
            refuse("AUTHORING_REGISTRY_MISMATCH")
        guide = guide_for(draft.schema_type)
        state = self._state(session, draft_id, draft.version)
        guide.check(state, allow_dead_end=True)
        return draft, guide, state

    @staticmethod
    def _state(session, draft_id, version):
        row = session.get(CeAuthoringSnapshot, (draft_id, version))
        if row is None:
            refuse("AUTHORING_REGISTRY_MISMATCH")
        return parse_strict_json(row.state)

    def read(self, principal, workspace_id, draft_id, *, locale="de", mode="guided"):
        with self._workspace(principal, workspace_id) as (session, content):
            draft, guide, state = self._draft(session, content, workspace_id, draft_id)
            return {"workspaceId": workspace_id, "draftId": draft.id, "draftVersion": draft.version,
                "authoringLocale": draft.authoring_locale, "schemaType": draft.schema_type.to_wire(),
                "registry": self.schema_registry(draft.schema_type).artifact(), "definitionId": draft.definition_id,
                **guide.present(state, locale=locale, mode=mode),
                "qualityGates": {quality: self.quality_gates(state, quality) for quality in QUALITIES}}

    def quality_gates(self, state, quality):
        gates = quality_gates(state, quality)
        if state["compilerVersion"] == flame.COMPILER_VERSION and not self.native_runtime and quality in {"runtime_ready", "automation_complete"}:
            # The WP7 host has no native authored activities yet. A valid
            # compiler result alone cannot promise working runtime behavior.
            gates.append({"path": ["flames"], "code": "RUNTIME_REGISTRATION_PENDING"})
        return gates

    def command_result(self, principal, workspace_id, key, *, draft_id=None):
        with self._workspace(principal, workspace_id) as (session, content):
            if draft_id is None:
                row = session.get(CeWorkspaceResult, (workspace_id, principal, key))
            else:
                self._draft(session, content, workspace_id, draft_id)
                row = session.get(CeDraftCommand, (draft_id, principal, key))
            if row is None:
                refuse("NOT_FOUND")
            return parse_strict_json(row.result)

    def history(self, principal, workspace_id, draft_id):
        with self._workspace(principal, workspace_id) as (session, content):
            self._draft(session, content, workspace_id, draft_id)
            rows = session.scalars(select(CeDraftCommand).where(CeDraftCommand.draft_id == draft_id))
            return sorted((parse_strict_json(row.result) for row in rows), key=lambda x: x["draftVersion"])

    def preview(self, principal, workspace_id, preset_id, *, locale="de"):
        with self._workspace(principal, workspace_id):
            return flame.preset(preset_id, locale=locale)

    @staticmethod
    def _receipt(command, scope_id, version):
        return {"commandId": command.wire["commandId"], "operationId": new_id("authoring"),
            "requestDigest": command.digest, "status": "committed", "scopeId": scope_id,
            "stateVersion": version, "authorityEpoch": 1, "checkpointId": None, "errorCode": None, "eventIds": []}

    def submit(self, principal, raw):
        command = Command.parse(raw)
        wire = command.wire
        if wire["operation"] not in OPERATIONS:
            refuse("SEMANTIC_INVALID")
        with self._workspace(principal, wire["workspaceId"]) as (session, content):
            if wire["authorityEpoch"] != 1:
                refuse("AUTHORITY_EPOCH_MISMATCH")
            creation = wire["operation"] == "CreateDraft"
            key = (wire["workspaceId"] if creation else wire["draftId"], principal, wire["idempotencyKey"])
            if not creation:
                draft, guide, state = self._draft(session, content, wire["workspaceId"], wire["draftId"])
            existing = session.get(CeWorkspaceCommand if creation else CeDraftCommand, key)
            if existing:
                if existing.request_digest != command.digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                return parse_strict_json(existing.receipt)
            now = self.store.now(session)
            if creation:
                payload = wire["payload"]
                schema_type = SchemaTypeRef(payload["schemaType"]["typeId"], payload["schemaType"]["version"])
                guide = guide_for(schema_type)
                draft = content.create_draft(wire["workspaceId"], schema_type, payload["authoringLocale"], {},
                    author_user_id=principal, now=now, registry=self.schema_registry(schema_type))
                session.add(CeAuthoringSnapshot(draft_id=draft.id, version=1, state=canonical_bytes(guide.empty())))
                result = {"draftId": draft.id, "draftVersion": 1, "operation": "CreateDraft"}
                receipt = self._receipt(command, wire["workspaceId"], 0)
                session.add(CeWorkspaceCommand(workspace_id=key[0], principal_id=principal, idempotency_key=key[2],
                    scope_id=None, request_digest=command.digest, receipt=canonical_bytes(receipt)))
                session.flush()
                session.add(CeWorkspaceResult(workspace_id=key[0], principal_id=principal, idempotency_key=key[2], result=canonical_bytes(result)))
            else:
                require_draft_version(draft, wire["expectedDraftVersion"])
                result = self._change(session, content, draft, guide, state, wire, principal, now)
                receipt = self._receipt(command, draft.id, result["draftVersion"])
                session.add(CeDraftCommand(draft_id=key[0], principal_id=principal, idempotency_key=key[2],
                    request_digest=command.digest, receipt=canonical_bytes(receipt), result=canonical_bytes(result)))
            session.flush()
            self.fault("before_commit")
        self.fault("after_commit")
        return receipt

    def _change(self, session, content, draft, guide, state, wire, principal, now):
        operation, payload = wire["operation"], wire["payload"]
        result = {"draftId": draft.id, "operation": operation, "payload": payload}
        logs = []
        locale = payload.get("promptLocale", draft.authoring_locale)
        if operation in {"RecordDraftDecision", "SkipDraftQuestion", "RetractDraftDecision"}:
            state, mutations, invalidated = guide.change(state, payload["question"], answer=payload.get("answer"),
                author=principal, locale=locale, skip=operation == "SkipDraftQuestion", retract=operation == "RetractDraftDecision")
            result.update(mutations=mutations, invalidated=invalidated)
            if operation == "RecordDraftDecision":
                logs = [{**payload, "mutations": mutations, "invalidated": invalidated}]
        elif operation == "ApplyDraftPreset":
            if draft.schema_type != flame.ITEM_TYPE:
                refuse("SEMANTIC_INVALID", "this preset is not registered for the draft type")
            state, logs = flame.apply_preset(state, payload["preset"], payload["previewDigest"], author=principal, locale=locale)
            result["decisions"] = logs
        elif operation == "RevertDraft":
            if payload["toDraftVersion"] >= draft.version:
                refuse("SEMANTIC_INVALID")
            state = self._state(session, draft.id, payload["toDraftVersion"])
            guide.check(state)
        elif operation == "CommitDraftRevision":
            gates = self.quality_gates(state, payload["declaredQuality"])
            if gates:
                raise QualityClaimUnmet(gates)
            values = guide.values(state)
            if payload["definition"]["kind"] == "new":
                definition = content.add_definition(draft.workspace_id, values["name"], draft.schema_type.type_id, now=now)
            else:
                definition = content.definition(payload["definition"]["id"])
                if (definition is None or definition.workspace_id != draft.workspace_id or definition.tombstoned_at or
                        definition.schema_type_id != draft.schema_type.type_id):
                    refuse("NOT_FOUND")
            selected_registry = self.schema_registry(draft.schema_type)
            revision = create_revision(definition.id, draft.schema_type, values, registry=selected_registry,
                author_user_id=principal, now=now, provenance={"kind": "authored", "draftId": draft.id,
                    "draftVersion": draft.version, "declaredQuality": payload["declaredQuality"],
                    "registry": selected_registry.artifact(), "compilerVersion": guide.compiler_version,
                    "questions": [{"questionId": key, "questionVersion": answer["questionVersion"]}
                                  for key, answer in sorted(state["answers"].items())]})
            content.append_revision(revision)
            session.get(CeDraft, draft.id).definition_id = definition.id
            result["revision"] = revision.ref().to_wire()
        else:
            refuse("SEMANTIC_INVALID")
        updated = content.advance_draft(draft.id, draft.version, guide.values(state), author_user_id=principal, now=now)
        session.add(CeAuthoringSnapshot(draft_id=draft.id, version=updated.version, state=canonical_bytes(state)))
        for log in logs:
            question = log["question"]
            content.append_answer(DraftAnswer(draft.id, updated.version, question["questionId"], question["questionVersion"],
                canonical_bytes(log["answer"]), log.get("promptLocale", locale), principal, canonical_bytes(log["mutations"]),
                canonical_bytes(log["invalidated"]), now))
        return {**result, "draftVersion": updated.version}
