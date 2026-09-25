"""Domain records and deterministic bounds for the §8–9 kernel."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.contracts import validate_command
from vtt.creation_engine.errors import BudgetExceeded, ContractViolation
from vtt.creation_engine.types import parse_id


class KernelError(ContractViolation):
    @property
    def http_status(self):
        return {"SCHEMA_INVALID": 400, "NOT_FOUND": 404, "OPERATION_FORBIDDEN": 403,
                "SEMANTIC_INVALID": 422, "BUDGET_EXCEEDED": 422, "PAYLOAD_TOO_LARGE": 413,
                "ADMISSION_LIMIT": 429, "WORKER_FENCED": 503, "LEASE_BUSY": 503}.get(self.code, 409)


def refuse(code, detail="command cannot be applied"):
    raise KernelError(code, detail)


class ActionState(StrEnum):
    PROPOSED = "PROPOSED"
    WAITING_PRECOMMIT = "WAITING_PRECOMMIT"
    ACTIVE = "ACTIVE"
    WAITING_DECISION = "WAITING_DECISION"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED_PRECOMMIT = "FAILED_PRECOMMIT"


TRANSITIONS = {
    ActionState.PROPOSED: {ActionState.WAITING_PRECOMMIT, ActionState.ACTIVE, ActionState.CANCELLED, ActionState.FAILED_PRECOMMIT},
    ActionState.WAITING_PRECOMMIT: {ActionState.ACTIVE, ActionState.CANCELLED, ActionState.FAILED_PRECOMMIT},
    ActionState.ACTIVE: {ActionState.WAITING_DECISION, ActionState.SUSPENDED, ActionState.COMPLETED},
    ActionState.WAITING_DECISION: {ActionState.ACTIVE, ActionState.SUSPENDED},
    ActionState.SUSPENDED: {ActionState.ACTIVE, ActionState.COMPLETED},
}
TERMINAL = {ActionState.COMPLETED, ActionState.CANCELLED, ActionState.FAILED_PRECOMMIT}
PRECOMMIT = {ActionState.PROPOSED, ActionState.WAITING_PRECOMMIT}


@dataclass
class Action:
    id: str
    scope_id: str
    principal_id: int
    request: bytes
    plan: bytes
    state: str
    deadline: datetime
    root_id: str
    parent_id: str | None = None
    depth: int = 0
    next_window: int = 0
    version: int = 0
    last_checkpoint_id: str | None = None
    error_code: str | None = None
    budget: dict = field(default_factory=lambda: {"operations": 0, "events": 0, "children": 0, "triggers": 0, "instances": []})

    def transition(self, state):
        if state not in TRANSITIONS.get(self.state, set()):
            refuse("ACTION_STATE_CONFLICT", f"cannot transition {self.state} to {state}")
        if state == ActionState.CANCELLED and self.last_checkpoint_id is not None:
            refuse("ACTION_STATE_CONFLICT", "a committed action cannot be cancelled")
        self.state = state
        self.version += 1


@dataclass(frozen=True)
class Command:
    wire: dict
    canonical: bytes
    digest: str

    @classmethod
    def parse(cls, raw: bytes | str, *, max_bytes: int = 1024 * 1024):
        if isinstance(raw, str):
            try:
                raw = raw.encode("utf-8")
            except UnicodeEncodeError:
                refuse("SCHEMA_INVALID", "command contains invalid Unicode")
        if len(raw) > max_bytes:
            refuse("PAYLOAD_TOO_LARGE", "command exceeds configured transport bound")
        wire = parse_strict_json(raw)
        if isinstance(wire, dict) and isinstance(wire.get("payload"), dict):
            targets = wire["payload"].get("targets")
            if isinstance(targets, list) and len(targets) > 64:
                raise BudgetExceeded("activity exceeds the structural limit of 64 targets")
        validate_command(wire)
        canonical = canonical_bytes(wire)
        # Schema validation has already rejected transport extras/spoofed identities.
        digest = content_digest({k: v for k, v in wire.items() if k != "commandId"})
        return cls(wire, canonical, digest)


def charge_root(action: Action, *, operations=0, events=0, children=0, triggers=0, instances=()):
    proposed = {**action.budget, "instances": sorted(set(action.budget["instances"]) | set(instances))}
    for key, amount, limit in (("operations", operations, 1_000_000), ("events", events, 4096),
                                ("children", children, 256), ("triggers", triggers, 1024)):
        if type(amount) is not int or amount < 0:
            refuse("SEMANTIC_INVALID", "invalid deterministic work accounting")
        proposed[key] += amount
        if proposed[key] > limit:
            raise BudgetExceeded(f"root action exceeds {key} limit {limit}")
    if len(proposed["instances"]) > 128:
        raise BudgetExceeded("root action affects more than 128 instances")
    action.budget = proposed


def receipt(command: Command, operation_id: str, scope, *, status, checkpoint_id=None, outcome=None, code=None, events=()):
    return {"commandId": command.wire["commandId"], "operationId": parse_id(operation_id),
            "requestDigest": command.digest, "status": status, "scopeId": scope.id,
            "stateVersion": scope.state_version, "authorityEpoch": scope.authority_epoch,
            "checkpointId": checkpoint_id, "outcomeDigest": content_digest(outcome) if outcome is not None else None,
            "errorCode": code, "eventIds": list(events)}
