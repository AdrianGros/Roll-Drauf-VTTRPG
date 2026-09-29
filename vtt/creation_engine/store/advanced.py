"""Atomic whole-document editing over the existing versioned draft store."""

from types import SimpleNamespace

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.compiler.catalog import QUALITIES
from vtt.creation_engine.compiler.interview import StrictValidator, copy
from vtt.creation_engine.content import DraftAnswer, new_id, require_draft_version
from vtt.creation_engine.contracts import contract_registry
from vtt.creation_engine.kernel.records import KernelError, refuse
from vtt.creation_engine.store.authoring_models import CeAuthoringSnapshot, CeDraftCommand
from vtt.creation_engine.types import parse_id

CONTRACT = "advanced-document:1"


class DocumentInvalid(KernelError):
    def __init__(self, issues):
        super().__init__("DOCUMENT_INVALID", "The document has invalid fields")
        self.issues = issues


def pointer(path):
    return "/" + "/".join(str(x).replace("~", "~0").replace("/", "~1") for x in path) if path else ""


class AdvancedService:
    def __init__(self, authoring):
        self.authoring = authoring

    def workspace(self, principal):
        result = self.authoring.workspace(principal)
        with self.authoring._workspace(principal, result["workspaceId"]) as (session, content):
            for entry in result["drafts"]:
                draft = content.draft(entry["draftId"])
                entry["name"] = parse_strict_json(draft.content).get("name", "")
                entry["definitionId"] = draft.definition_id
        return result

    def read(self, principal, workspace_id, draft_id, *, locale="en"):
        view = self.authoring.read(principal, workspace_id, draft_id, locale=locale, mode="advanced")
        from vtt.creation_engine.content import SchemaTypeRef
        schema_type = SchemaTypeRef(view["schemaType"]["typeId"], view["schemaType"]["version"])
        schema = dict(self.authoring.schema_registry(schema_type).get(schema_type).schema)
        schema.pop("x-authoring", None)
        schema.pop("x-presets", None)
        return {**view, "documentContract": CONTRACT, "contentSchema": schema}

    @staticmethod
    def _payload(payload, *, save):
        keys = {"contractVersion", "expectedDraftVersion", "promptLocale", "content"}
        if save:
            keys.add("idempotencyKey")
        if (not isinstance(payload, dict) or set(payload) != keys or payload["contractVersion"] != CONTRACT or
                type(payload["expectedDraftVersion"]) is not int or payload["expectedDraftVersion"] < 1 or
                payload["promptLocale"] not in ("de", "en", "fr") or not isinstance(payload["content"], dict)):
            refuse("SCHEMA_INVALID")
        if len(canonical_bytes(payload)) > 262144:
            refuse("PAYLOAD_TOO_LARGE")
        if save:
            parse_id(payload["idempotencyKey"])

    def _candidate(self, draft, guide, state, document, principal, locale):
        schema = self.authoring.schema_registry(draft.schema_type).get(draft.schema_type).schema
        errors = list(StrictValidator(schema, registry=contract_registry()).iter_errors(document))
        if errors:
            raise DocumentInvalid([{"path": pointer(error.absolute_path), "code": str(error.validator),
                                    "message": error.message[:400]} for error in errors[:50]])
        values = {}
        for q in guide.questions:
            value = document
            for key in q.path:
                if not isinstance(value, dict) or key not in value:
                    break
                value = value[key]
            else:
                values[q.id] = value
        candidate, changes, logs = copy(state), [], []
        for q in guide.questions:
            if q.id in candidate["answers"] and q.id not in values:
                candidate, mutations, invalidated = guide.change(candidate,
                    {"questionId": q.id, "questionVersion": q.version}, author=principal, locale=locale, retract=True)
                changes.extend(mutations)
        remaining = set(values)
        while remaining:
            q = next((q for q in guide.questions if q.id in remaining and
                      not any(dep in remaining for dep in q.dependencies) and guide.ready(q, candidate)), None)
            if q is None:
                raise DocumentInvalid([{"path": pointer(guide.by_id[key].path), "code": "QUESTION_NOT_READY",
                                        "message": "A required dependency is missing or this field is inapplicable."}
                                       for key in sorted(remaining)])
            answer = q.answer(values[q.id])
            if candidate["answers"].get(q.id, {}).get("answer") != answer:
                candidate, mutations, invalidated = guide.change(candidate,
                    {"questionId": q.id, "questionVersion": q.version}, answer=answer,
                    author=principal, locale=locale, source="advanced_document")
                changes.extend(mutations)
                logs.append({"question": q, "answer": answer, "mutations": mutations, "invalidated": invalidated})
            remaining.remove(q.id)
        if guide.values(candidate) != document:
            raise DocumentInvalid([{"path": "", "code": "UNOWNED_CONTENT",
                                    "message": "Every supplied field must belong to an active registered question."}])
        gates = {quality: self.authoring.quality_gates(candidate, quality) for quality in QUALITIES}
        return candidate, changes, logs, gates

    def validate(self, principal, workspace_id, draft_id, payload):
        self._payload(payload, save=False)
        with self.authoring._workspace(principal, workspace_id) as (session, content):
            draft, guide, state = self.authoring._draft(session, content, workspace_id, draft_id)
            require_draft_version(draft, payload["expectedDraftVersion"])
            _, changes, _, gates = self._candidate(draft, guide, state, payload["content"], principal, payload["promptLocale"])
            return {"valid": True, "draftVersion": draft.version, "qualityGates": gates, "changes": changes}

    def save(self, principal, workspace_id, draft_id, payload):
        self._payload(payload, save=True)
        digest = content_digest({"operation": "SaveAdvancedDocument", "workspaceId": workspace_id,
                                 "draftId": draft_id, **payload})
        with self.authoring._workspace(principal, workspace_id) as (session, content):
            draft, guide, state = self.authoring._draft(session, content, workspace_id, draft_id)
            key = (draft_id, principal, payload["idempotencyKey"])
            previous = session.get(CeDraftCommand, key)
            if previous:
                if previous.request_digest != digest:
                    refuse("IDEMPOTENCY_KEY_REUSE")
                return parse_strict_json(previous.result)
            require_draft_version(draft, payload["expectedDraftVersion"])
            candidate, changes, logs, gates = self._candidate(draft, guide, state, payload["content"], principal, payload["promptLocale"])
            now = self.authoring.store.now(session)
            updated = content.advance_draft(draft_id, draft.version, guide.values(candidate), author_user_id=principal, now=now)
            session.add(CeAuthoringSnapshot(draft_id=draft_id, version=updated.version, state=canonical_bytes(candidate)))
            for entry in logs:
                q = entry["question"]
                content.append_answer(DraftAnswer(draft_id, updated.version, q.id, q.version,
                    canonical_bytes(entry["answer"]), payload["promptLocale"], principal,
                    canonical_bytes(entry["mutations"]), canonical_bytes(entry["invalidated"]), now))
            result = {"operation": "SaveAdvancedDocument", "draftId": draft_id, "draftVersion": updated.version,
                      "changes": changes, "qualityGates": gates}
            command = SimpleNamespace(wire={"commandId": new_id("advanced")}, digest=digest)
            receipt = self.authoring._receipt(command, draft_id, updated.version)
            session.add(CeDraftCommand(draft_id=draft_id, principal_id=principal, idempotency_key=key[2],
                                      request_digest=digest, receipt=canonical_bytes(receipt), result=canonical_bytes(result)))
            session.flush()
            self.authoring.fault("before_commit")
        self.authoring.fault("after_commit")
        return result
