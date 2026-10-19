"""Internal, lock-bound question templates and retained decision versions (§10).

Only the opaque nonce crosses the future projection boundary. The canonical
context hash, exact schema reference and answers remain internal records.
"""

from dataclasses import dataclass
from datetime import datetime

from vtt.creation_engine.content.registry import SchemaTypeRef
from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.types import parse_id


@dataclass(frozen=True)
class Question:
    id: str
    version: int
    answer_type: SchemaTypeRef
    responder_rule_id: str
    policy_id: str
    # None means mandatory; an optional timeout must declare the exact answer.
    decline: dict | None = None

    def __post_init__(self):
        for value in (self.id, self.responder_rule_id, self.policy_id):
            parse_id(value)
        if type(self.version) is not int or not 0 <= self.version <= 2**53 - 1:
            refuse("SEMANTIC_INVALID", "question version must be a safe nonnegative integer")
        if self.decline is not None:
            validate_definition("DecisionAnswer", self.decline)

    def wire(self):
        return {"id": self.id, "version": self.version, "answerType": self.answer_type.to_wire(),
                "responderRuleId": self.responder_rule_id, "policyId": self.policy_id, "decline": self.decline}

    @classmethod
    def restore(cls, value):
        return cls(value["id"], value["version"], SchemaTypeRef(value["answerType"]["typeId"],
                   value["answerType"]["version"]), value["responderRuleId"], value["policyId"], value["decline"])


@dataclass
class Decision:
    wire: dict
    context_digest: str
    created_scope_version: int
    question: Question
    timeout_seconds: int
    answer: dict | None = None
    responder_id: int | None = None
    closed_at: datetime | None = None

    @property
    def id(self):
        return self.wire["decisionId"]

    @property
    def version(self):
        return self.wire["decisionVersion"]

    @property
    def deadline(self):
        return datetime.fromisoformat(self.wire["deadline"])

    def close(self, status, now, *, answer=None, responder=None):
        if self.wire["status"] != "open":
            refuse("DECISION_STALE")
        self.wire["status"] = status
        self.answer, self.responder_id, self.closed_at = answer, responder, now


def timestamp(now):
    return now.isoformat().replace("+00:00", "Z")
