"""Durable private test API using the existing authoring ownership/transaction boundary."""

import secrets

from sqlalchemy import select

from vtt.creation_engine import homebrew_runtime as runtime
from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.compiler import homebrew as profiles
from vtt.creation_engine.compiler.catalog import registry
from vtt.creation_engine.content import new_id
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.store.homebrew_models import CeHomebrewSandbox, CeHomebrewEvent
from vtt.creation_engine.store.models import CeDefinition, CeRevision
from vtt.creation_engine.types import parse_reference, RevisionRef

MAX_STATE_BYTES = 2 * 1024 * 1024


class HomebrewService:
    def __init__(self, authoring, *, fault=None, random_below=None):
        self.authoring = authoring
        self.fault = fault or (lambda point: None)
        self.random_below = random_below or secrets.randbelow

    @staticmethod
    def _revision(content, workspace_id, reference):
        ref = parse_reference(reference, accept=(RevisionRef,))
        revision = content.revision(ref.id)
        definition = content.definition(ref.definition_id)
        if (revision is None or definition is None or definition.workspace_id != workspace_id or
                definition.tombstoned_at or revision.ref() != ref or revision.schema_type not in profiles.TYPES):
            refuse("NOT_FOUND")
        provenance = parse_strict_json(revision.provenance)
        selected = registry(revision.schema_type)
        if (provenance.get("registry") != selected.artifact() or
                provenance.get("compilerVersion") != profiles.compiler_version(revision.schema_type)):
            refuse("AUTHORING_REGISTRY_MISMATCH")
        if provenance.get("declaredQuality") != "runtime_ready":
            refuse("QUALITY_CLAIM_UNMET")
        selected.validate(revision.schema_type, revision.content)
        guide, values = profiles.interview(revision.schema_type), revision.content
        state = guide.empty()
        for q in guide.questions:
            value = values
            for key in q.path:
                if not isinstance(value, dict) or key not in value:
                    break
                value = value[key]
            else:
                state, _, _ = guide.change(state, {"questionId": q.id, "questionVersion": q.version},
                    answer=q.answer(value), author=revision.author_user_id, locale="en")
        questions = [{"questionId": key, "questionVersion": answer["questionVersion"]}
                     for key, answer in sorted(state["answers"].items())]
        if provenance.get("questions") != questions or guide.values(state) != values:
            refuse("AUTHORING_REGISTRY_MISMATCH")
        if profiles.quality_gates(revision.schema_type, state, "runtime_ready"):
            refuse("QUALITY_CLAIM_UNMET")
        return revision

    def catalog(self, principal, workspace_id):
        with self.authoring._workspace(principal, workspace_id) as (session, content):
            rows = session.scalars(select(CeRevision).join(CeDefinition).where(
                CeDefinition.workspace_id == workspace_id, CeDefinition.tombstoned_at.is_(None),
                CeRevision.schema_type_id.in_([t.type_id for t in profiles.TYPES])).order_by(CeRevision.created_at, CeRevision.id))
            revisions = []
            for row in rows:
                revision = content.revision(row.id)
                if parse_strict_json(revision.provenance).get("declaredQuality") == "runtime_ready":
                    revisions.append({"revision": revision.ref().to_wire(), "schemaType": revision.schema_type.to_wire(),
                                      "content": revision.content})
            sandboxes = [{"sandboxId": row.id, "version": row.version} for row in session.scalars(
                select(CeHomebrewSandbox).where(CeHomebrewSandbox.workspace_id == workspace_id).order_by(CeHomebrewSandbox.id))]
            return {"contractVersion": runtime.CONTRACT, "runtime": runtime.RUNTIME, "revisions": revisions,
                    "sandboxes": sandboxes, "commands": {op: runtime.command_schema(op) for op in runtime.PAYLOADS}}

    @staticmethod
    def _sandbox(session, workspace_id, sandbox_id):
        row = session.scalar(select(CeHomebrewSandbox).where(CeHomebrewSandbox.id == sandbox_id,
            CeHomebrewSandbox.workspace_id == workspace_id).with_for_update())
        if row is None:
            refuse("NOT_FOUND")
        lock = parse_strict_json(row.execution_lock)
        if lock["runtime"] != runtime.RUNTIME:
            refuse("EXECUTION_LOCK_MISMATCH")
        return row, lock

    def read(self, principal, workspace_id, sandbox_id):
        with self.authoring._workspace(principal, workspace_id) as (session, _):
            row, lock = self._sandbox(session, workspace_id, sandbox_id)
            state = parse_strict_json(row.state)
            for identifier, character in state["characters"].items():
                character["effectiveStats"] = {**character["stats"], **{
                    stat: runtime.current_stat(state, identifier, stat) for stat in ("ac", "speed")}}
            return {"sandboxId": row.id, "version": row.version, "executionLockDigest": content_digest(lock),
                    "executionLock": lock, "state": state}

    def history(self, principal, workspace_id, sandbox_id, *, after=0):
        if type(after) is not int or after < 0:
            refuse("SCHEMA_INVALID")
        with self.authoring._workspace(principal, workspace_id) as (session, _):
            self._sandbox(session, workspace_id, sandbox_id)
            events = session.scalars(select(CeHomebrewEvent).where(CeHomebrewEvent.sandbox_id == sandbox_id,
                CeHomebrewEvent.version > after).order_by(CeHomebrewEvent.version).limit(100))
            return [{"command": parse_strict_json(e.command), "result": parse_strict_json(e.result),
                     "createdAt": e.created_at.isoformat()} for e in events]

    def submit(self, principal, workspace_id, command):
        if len(canonical_bytes(command)) > 262144:
            refuse("PAYLOAD_TOO_LARGE")
        runtime.validate_command(command)
        digest, operation, payload = content_digest(command), command["operation"], command["payload"]
        with self.authoring._workspace(principal, workspace_id) as (session, content):
            key = (workspace_id, principal, command["idempotencyKey"])
            previous = session.get(CeHomebrewEvent, key)
            if previous:
                # Recheck sandbox ownership/runtime before disclosing a historical result.
                self._sandbox(session, workspace_id, previous.sandbox_id)
                if previous.request_digest != digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                return parse_strict_json(previous.result)
            rolls = []
            def roll(sides):
                if len(rolls) >= 202:
                    refuse("BUDGET_EXCEEDED")
                value = self.random_below(sides) + 1
                if type(value) is not int or not 1 <= value <= sides:
                    refuse("SEMANTIC_INVALID")
                rolls.append({"sides": sides, "value": value})
                return value
            if operation == "CreateSandbox":
                documents, spell_keys, kinds = {}, set(), set()
                for ref in payload["revisions"]:
                    revision = self._revision(content, workspace_id, ref)
                    kind = profiles.KINDS[revision.schema_type]
                    if revision.id in documents:
                        refuse("SEMANTIC_INVALID")
                    if revision.content[kind]["edition"] != payload["edition"]:
                        refuse("CHARACTER_SYSTEM_MISMATCH")
                    if kind == "spell":
                        spell_key = revision.content[kind]["key"]
                        if spell_key in spell_keys:
                            refuse("SPELL_KEY_AMBIGUOUS")
                        spell_keys.add(spell_key)
                    kinds.add(kind)
                    documents[revision.id] = {"kind": kind, "revision": ref,
                        "registry": registry(revision.schema_type).artifact(), "content": revision.content}
                if kinds != {"class", "race", "spell"}:
                    refuse("SEMANTIC_INVALID")
                lock = {"runtime": runtime.RUNTIME, "edition": payload["edition"], "documents": documents}
                if len(canonical_bytes(lock)) > MAX_STATE_BYTES:
                    refuse("BUDGET_EXCEEDED")
                state = {"round": 0, "characters": {}, "effects": [], "pendingConcentration": None}
                row = CeHomebrewSandbox(id=new_id("hbsandbox"), workspace_id=workspace_id, version=1,
                                       execution_lock=canonical_bytes(lock), state=canonical_bytes(state))
                session.add(row)
                outcome = {"executionLockDigest": content_digest(lock)}
            else:
                row, lock = self._sandbox(session, workspace_id, command["sandboxId"])
                if row.version != command["expectedVersion"]:
                    refuse("SCOPE_VERSION_CONFLICT")
                state = parse_strict_json(row.state)
                outcome = runtime.execute(state, lock["documents"], operation, payload, new_id=new_id, roll=roll)
                row.version += 1
                row.state = canonical_bytes(state)
            if len(row.state) > MAX_STATE_BYTES:
                refuse("BUDGET_EXCEEDED")
            session.flush()
            result = {"contractVersion": runtime.CONTRACT, "sandboxId": row.id, "version": row.version,
                      "operation": operation, "outcome": outcome, "rolls": rolls, "stateDigest": content_digest(state)}
            session.add(CeHomebrewEvent(workspace_id=workspace_id, principal_id=principal, idempotency_key=key[2],
                sandbox_id=row.id, version=row.version, request_digest=digest, command=canonical_bytes(command),
                result=canonical_bytes(result), created_at=self.authoring.store.now(session)))
            session.flush()
            self.fault("before_commit")
        self.fault("after_commit")
        return result
