"""Deterministic questions, typed answers and explicit descendant invalidation.

No text parsing, executable user code or creative defaults live here. Locale and
editing mode affect presentation only. The store owns authority and versions.
"""

from dataclasses import dataclass, replace

from jsonschema import Draft202012Validator
from jsonschema.validators import extend

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.contracts import contract_registry
from vtt.creation_engine.kernel.records import refuse

LOCALES = ("de", "en", "fr")
MODES = ("guided", "structured", "advanced")
StrictValidator = extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda checker, value: type(value) is int))


def copy(value):
    return parse_strict_json(canonical_bytes(value))


@dataclass(frozen=True)
class Question:
    id: str
    path: tuple[str, ...]
    schema: dict
    text: dict
    version: int = 1
    kind: str = "text"
    answer_type: str | None = None
    priority: int = 0
    required: bool = True
    dependencies: tuple[str, ...] = ()
    conditions: tuple[tuple[str, tuple], ...] = ()

    def answer(self, value):
        result = {"kind": self.kind, "value": value}
        if self.kind == "structured":
            result["schemaType"] = {"typeId": self.answer_type, "version": self.version}
        self.validate(result)
        return copy(result)

    def validate(self, answer):
        keys = {"kind", "value", "schemaType"} if self.kind == "structured" else {"kind", "value"}
        if not isinstance(answer, dict) or set(answer) != keys:
            refuse("SCHEMA_INVALID", "answer must use the registered typed envelope")
        if answer["kind"] != self.kind or (self.kind == "structured" and
                answer["schemaType"] != {"typeId": self.answer_type, "version": self.version}):
            refuse("SCHEMA_INVALID", "answer type or version does not match the question")
        # JSON Schema considers 1.0 an integer; authoring accepts exact JSON types.
        if self.schema.get("type") == "integer" and type(answer["value"]) is not int:
            refuse("SCHEMA_INVALID", "answer requires an integer without coercion")
        if not StrictValidator(self.schema, registry=contract_registry()).is_valid(answer["value"]):
            refuse("SCHEMA_INVALID", "answer does not match the registered schema")


class Interview:
    def __init__(self, questions, *, compiler_version):
        self.questions = tuple(replace(q, schema=copy(q.schema), text=copy(q.text)) for q in questions)
        self.compiler_version = compiler_version
        self.by_id = {q.id: q for q in self.questions}
        if len(self.by_id) != len(self.questions):
            raise ValueError("question IDs must be unique")
        paths = [q.path for q in self.questions]
        if len(set(paths)) != len(paths) or any(a != b and b[:len(a)] == a for a in paths for b in paths):
            raise ValueError("every editable path has exactly one owning question")
        for q in self.questions:
            if set(q.text) != set(LOCALES) or any(set(q.text[l]) != {"label", "help"} or
                    not all(isinstance(v, str) and v for v in q.text[l].values()) for l in LOCALES):
                raise ValueError("each question needs display/help in de, en and fr")
            if set(q.dependencies) - self.by_id.keys() or any(i not in q.dependencies for i, _ in q.conditions):
                raise ValueError("conditions must name declared question dependencies")
            if q.kind not in {"text", "structured"} or (q.kind == "structured" and not q.answer_type):
                raise ValueError("question needs an explicit answer type")
            Draft202012Validator.check_schema(q.schema)
        self._cycle = self._has_cycle()

    def _has_cycle(self):
        done, active = set(), set()
        def visit(key):
            if key in active:
                return True
            if key in done:
                return False
            active.add(key)
            if any(visit(dep) for dep in self.by_id[key].dependencies):
                return True
            active.remove(key)
            done.add(key)
            return False
        return any(visit(q.id) for q in self.questions)

    def artifact(self):
        return {"compilerVersion": self.compiler_version, "questions": [
            {"id": q.id, "version": q.version, "path": list(q.path), "answerSchema": q.schema,
             "answerKind": q.kind, "answerType": q.answer_type, "text": q.text,
             "priority": q.priority, "required": q.required, "dependencies": list(q.dependencies),
             "conditions": [[key, list(values)] for key, values in q.conditions]}
            for q in self.questions]}

    def empty(self):
        return {"compilerVersion": self.compiler_version, "answers": {}, "stale": {}, "skipped": []}

    def check(self, state, *, allow_dead_end=False):
        if state["compilerVersion"] != self.compiler_version:
            refuse("AUTHORING_REGISTRY_MISMATCH", "a reviewed schema migration is required")
        if self._cycle and not allow_dead_end:
            refuse("GUIDE_DEAD_END", "registered question dependencies contain a cycle")

    def question(self, ref):
        q = self.by_id.get(ref["questionId"])
        if q is None or ref["questionVersion"] != q.version:
            refuse("AUTHORING_REGISTRY_MISMATCH")
        return q

    def visible(self, q, state):
        return all(key in state["answers"] and state["answers"][key]["answer"]["value"] in choices
                   for key, choices in q.conditions)

    def ready(self, q, state):
        return self.visible(q, state) and all(key in state["answers"] for key in q.dependencies)

    def descendants(self, key):
        found = set()
        pending = [key]
        while pending:
            parent = pending.pop()
            for q in self.questions:
                if parent in q.dependencies and q.id not in found:
                    found.add(q.id)
                    pending.append(q.id)
        return [q.id for q in self.questions if q.id in found]

    def values(self, state):
        self.check(state, allow_dead_end=True)
        content = {}
        for q in self.questions:
            if q.id not in state["answers"] or not self.visible(q, state):
                continue
            parent = content
            for key in q.path[:-1]:
                parent = parent.setdefault(key, {})
            parent[q.path[-1]] = copy(state["answers"][q.id]["answer"]["value"])
        return content

    def change(self, state, ref, *, answer=None, author, locale, source="answer", skip=False, retract=False):
        self.check(state, allow_dead_end=retract)
        if locale not in LOCALES:
            refuse("SCHEMA_INVALID")
        q = self.question(ref)
        if skip and q.required:
            refuse("QUESTION_REQUIRED")
        if not retract and not self.ready(q, state):
            refuse("QUESTION_NOT_READY")
        if not skip and not retract:
            q.validate(answer)
        result = copy(state)
        previous = state["answers"].get(q.id)
        changed = retract or skip or previous is None or previous["answer"] != answer
        invalidated = []
        if changed:
            for key in self.descendants(q.id):
                old = result["answers"].pop(key, None)
                if old is not None:
                    result["stale"][key] = {**old, "invalidatedBy": q.id}
                    invalidated.append(key)
                if key in result["skipped"]:
                    result["skipped"].remove(key)
        result["answers"].pop(q.id, None)
        result["stale"].pop(q.id, None)
        if q.id in result["skipped"]:
            result["skipped"].remove(q.id)
        if skip:
            result["skipped"].append(q.id)
        elif not retract:
            result["answers"][q.id] = {"questionVersion": q.version, "answer": copy(answer),
                "author": author, "promptLocale": locale, "source": source}
        before, after = self.values(state), self.values(result)
        mutations = [{"path": list(owner.path), "before": _at(before, owner.path), "after": _at(after, owner.path)}
                     for owner in self.questions if _at(before, owner.path) != _at(after, owner.path)]
        return result, mutations, invalidated

    def present(self, state, *, locale="de", mode="guided"):
        self.check(state, allow_dead_end=mode != "guided")
        if locale not in LOCALES or mode not in MODES:
            refuse("SCHEMA_INVALID")
        unresolved = [q for q in self.questions if self.visible(q, state) and
                      q.id not in state["answers"] and q.id not in state["skipped"]]
        ready = [q for q in unresolved if self.ready(q, state)]
        ordered = sorted(ready, key=lambda q: (-q.priority, self.questions.index(q), q.id))
        dead_end = self._cycle or bool(unresolved and not ordered)
        if dead_end and mode == "guided":
            refuse("GUIDE_DEAD_END", "no valid next question; recover in Structured mode")
        return {"compilerVersion": self.compiler_version, "locale": locale, "mode": mode,
                "nextQuestionId": ordered[0].id if ordered and not dead_end else None,
                "guideError": "GUIDE_DEAD_END" if dead_end else None,
                "unresolved": [q.id for q in unresolved], "content": self.values(state),
                "stale": copy(state["stale"]), "questions": [
                    {"questionId": q.id, "questionVersion": q.version, "path": list(q.path),
                     "label": q.text[locale]["label"], "help": q.text[locale]["help"],
                     "schema": copy(q.schema), "answerKind": q.kind,
                     "answerType": {"typeId": q.answer_type, "version": q.version} if q.answer_type else None,
                     "required": q.required, "visible": self.visible(q, state), "ready": self.ready(q, state),
                     "answer": copy(state["answers"][q.id]["answer"]) if q.id in state["answers"] else None,
                     "skipped": q.id in state["skipped"], "stale": q.id in state["stale"]}
                    for q in self.questions]}

    def advanced_answer(self, path, value):
        owner = next((q for q in self.questions if q.path == tuple(path)), None)
        if owner is None:
            refuse("SCHEMA_INVALID", "canonical path has no registered owning question")
        answer = owner.answer(value)
        owner.validate(answer)
        return {"question": {"questionId": owner.id, "questionVersion": owner.version}, "answer": answer}


def _at(value, path):
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return {"present": False}
        value = value[key]
    return {"present": True, "value": value}
