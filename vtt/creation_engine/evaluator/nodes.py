"""Typed formula and predicate nodes (spec v1.1.4 §6–7, contract 1.1.3 `Formula` / `Predicate`).

The §18 admission limits (depth 64, 4,096 nodes per expression) are checked
iteratively first, so hostile nesting never reaches recursive code. The value
is then validated against the approved schema and parsed into immutable
nodes, checking each function against the profile's registry and arity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.errors import SEMANTIC_INVALID, BudgetExceeded, ContractViolation
from vtt.creation_engine.units import Quantity

MAX_DEPTH = 64
MAX_NODES = 4096


class Stage(StrEnum):
    BASE = "base"
    SET = "set"
    ADD = "add"
    MULTIPLY = "multiply"
    CLAMP = "clamp"
    FINAL = "final"


STAGES = tuple(Stage)   # evaluation order (§7)


@dataclass(frozen=True, slots=True)
class Literal:
    value: Quantity


@dataclass(frozen=True, slots=True)
class Read:
    binding_id: str
    stage: Stage


@dataclass(frozen=True, slots=True)
class Call:
    function_id: str
    args: tuple[Formula, ...]


@dataclass(frozen=True, slots=True)
class If:
    condition: str          # a registered Predicate binding (§6)
    then: Formula
    otherwise: Formula


Formula = Literal | Read | Call | If


@dataclass(frozen=True, slots=True)
class PredicateRef:
    binding_id: str


@dataclass(frozen=True, slots=True)
class And:
    args: tuple[Predicate, ...]


@dataclass(frozen=True, slots=True)
class Or:
    args: tuple[Predicate, ...]


@dataclass(frozen=True, slots=True)
class Not:
    arg: Predicate


@dataclass(frozen=True, slots=True)
class Compare:
    operator: str           # lt, le, eq, ne, ge, gt
    left: Formula
    right: Formula


@dataclass(frozen=True, slots=True)
class IsKnown:
    binding_id: str


@dataclass(frozen=True, slots=True)
class Human:
    question_id: str
    question_version: int
    responder_rule_id: str


@dataclass(frozen=True, slots=True)
class ManualToggle:
    toggle_id: str


Predicate = PredicateRef | And | Or | Not | Compare | IsKnown | Human | ManualToggle


_CHILD_KEYS = ("args", "then", "else", "left", "right", "arg")


def _check_limits(wire: object) -> None:
    """Enforce §18 depth/node limits iteratively, before any recursive validation touches the value."""
    nodes, pending = 0, [(wire, 1)]
    while pending:
        item, depth = pending.pop()
        if not isinstance(item, dict):
            continue                     # shape errors are reported by schema validation
        nodes += 1
        if depth > MAX_DEPTH:
            raise BudgetExceeded(f"expression deeper than {MAX_DEPTH} levels")
        if nodes > MAX_NODES:
            raise BudgetExceeded(f"expression has more than {MAX_NODES} nodes")
        for key in _CHILD_KEYS:
            child = item.get(key)
            children = child if isinstance(child, list) else [child]
            pending.extend((c, depth + 1) for c in children if isinstance(c, dict))


def parse_formula(wire: object, *, arities: dict[str, int]) -> Formula:
    """Parse a wire Formula. ``arities`` is the function registry of the evaluation profile."""
    _check_limits(wire)
    validate_definition("Formula", wire)
    return _formula(wire, arities)


def parse_predicate(wire: object, *, arities: dict[str, int]) -> Predicate:
    _check_limits(wire)
    validate_definition("Predicate", wire)
    return _predicate(wire, arities)


def _formula(wire: dict, arities: dict[str, int]) -> Formula:
    node = wire["node"]
    if node == "literal":
        return Literal(Quantity.from_wire(wire["value"]))
    if node == "read":
        return Read(wire["bindingId"], Stage(wire["stage"]))
    if node == "call":
        function_id = wire["functionId"]
        if function_id not in arities:
            raise ContractViolation(SEMANTIC_INVALID, f"function {function_id} is not available in core-safe-1")
        if len(wire["args"]) != arities[function_id]:
            raise ContractViolation(SEMANTIC_INVALID, f"{function_id} takes {arities[function_id]} argument(s)")
        return Call(function_id, tuple(_formula(arg, arities) for arg in wire["args"]))
    return If(wire["conditionBindingId"], _formula(wire["then"], arities),
              _formula(wire["else"], arities))


def _predicate(wire: dict, arities: dict[str, int]) -> Predicate:
    node = wire["node"]
    if node == "binding":
        return PredicateRef(wire["bindingId"])
    if node in ("and", "or"):
        args = tuple(_predicate(arg, arities) for arg in wire["args"])
        return And(args) if node == "and" else Or(args)
    if node == "not":
        return Not(_predicate(wire["arg"], arities))
    if node == "compare":
        return Compare(wire["operator"], _formula(wire["left"], arities),
                       _formula(wire["right"], arities))
    if node == "is_known":
        return IsKnown(wire["bindingId"])
    if node == "human":
        return Human(wire["questionId"], wire["questionVersion"], wire["responderRuleId"])
    return ManualToggle(wire["toggleId"])
