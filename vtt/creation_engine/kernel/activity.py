"""Typed checkpoint plans supplied by the trusted, lock-bound activity registry.

These are internal kernel inputs, not a new command wire schema. The compiler
must resolve a plan from the requested immutable revision. Plans are frozen in
the action at admission, so a restarted worker never consults a floating rule.
The resolver must include all requirements/derived calculations in its prepare
hook; the kernel itself owns resource changes, dice, budgets and atomic writes.
"""

from dataclasses import dataclass

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.errors import BudgetExceeded
from vtt.creation_engine.kernel.records import refuse
from vtt.creation_engine.kernel.decisions import Question
from vtt.creation_engine.types import parse_id
from vtt.creation_engine.units import Quantity


@dataclass(frozen=True)
class Cost:
    owner: str                         # actor or source; never an arbitrary object path
    resource_id: str
    amount: Quantity

    def wire(self):
        return {"owner": self.owner, "resourceId": self.resource_id, "amount": self.amount.to_wire()}


@dataclass(frozen=True)
class Dice:
    id: str
    count: int
    sides: int


@dataclass(frozen=True)
class Window:
    id: str
    costs: tuple[Cost, ...]
    dice: tuple[Dice, ...]
    primitive_bound: int
    wait_for_decision: bool = False
    question: Question | None = None

    def wire(self):
        return {"id": self.id, "costs": [c.wire() for c in self.costs],
                "dice": [{"id": d.id, "count": d.count, "sides": d.sides} for d in self.dice],
                "primitiveBound": self.primitive_bound, "waitForDecision": self.wait_for_decision,
                "question": self.question.wire() if self.question else None}


@dataclass(frozen=True)
class Activity:
    id: str
    windows: tuple[Window, ...]
    child_activity_ids: tuple[str, ...] = ()

    def __post_init__(self):
        parse_id(self.id)
        if not self.windows or len({w.id for w in self.windows}) != len(self.windows):
            refuse("SEMANTIC_INVALID", "activity needs distinct ordered windows")
        question_ids = [w.question.id for w in self.windows if w.question]
        if len(question_ids) != len(set(question_ids)):
            refuse("SEMANTIC_INVALID", "question IDs must be distinct within a frame")
        total = 0
        for window in self.windows:
            parse_id(window.id)
            if window.wait_for_decision != (window.question is not None):
                refuse("SEMANTIC_INVALID", "a waiting window must declare its exact question contract")
            if type(window.primitive_bound) is not int or window.primitive_bound < 0:
                refuse("SEMANTIC_INVALID", "window needs an explicit nonnegative work bound")
            minimum = len(window.costs)
            if len({d.id for d in window.dice}) != len(window.dice):
                refuse("SEMANTIC_INVALID", "roll IDs must be unique within a checkpoint")
            for die in window.dice:
                parse_id(die.id)
                if type(die.count) is not int or type(die.sides) is not int or die.count < 1 or not 2 <= die.sides <= 2**53 - 1:
                    refuse("SEMANTIC_INVALID", "invalid declared dice")
                minimum += die.count
            for cost in window.costs:
                parse_id(cost.resource_id)
                if cost.owner not in {"actor", "source"} or cost.amount.value.numerator < 0:
                    refuse("SEMANTIC_INVALID", "cost needs a declared owner and nonnegative amount")
            if minimum > window.primitive_bound:
                refuse("SEMANTIC_INVALID", "declared work bound is smaller than mandatory work")
            if window.primitive_bound > 100_000:
                raise BudgetExceeded("window's declared upper bound exceeds checkpoint budget")
            total += window.primitive_bound
        if total > 1_000_000 or len(self.windows) > 4096:
            raise BudgetExceeded("activity's declared upper bound exceeds root budget")
        for child in self.child_activity_ids:
            parse_id(child)

    def canonical(self):
        return canonical_bytes({"id": self.id, "windows": [w.wire() for w in self.windows],
                                "childActivityIds": list(self.child_activity_ids)})

    @classmethod
    def restore(cls, raw):
        value = parse_strict_json(raw)
        return cls(value["id"], tuple(Window(w["id"],
                   tuple(Cost(c["owner"], c["resourceId"], Quantity.from_wire(c["amount"])) for c in w["costs"]),
                   tuple(Dice(d["id"], d["count"], d["sides"]) for d in w["dice"]),
                   w["primitiveBound"], w["waitForDecision"],
                   Question.restore(w["question"]) if w.get("question") else None) for w in value["windows"]), tuple(value["childActivityIds"]))
