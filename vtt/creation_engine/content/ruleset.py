"""Ruleset packages (spec v1.1.4 §5, §7, §12): trusted configuration a scope executes under.

A ruleset declares its units, the numeric bindings of an occurrence (unit,
explicit final rounding, whether a manual override or a base edit is allowed)
and its resources (unit, maximum binding, adjustment bound policy with no
default, G0-09). Its LockedArtifact digest pins all of that in a lock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from vtt.creation_engine.canonical import content_digest
from vtt.creation_engine.errors import SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.evaluator.engine import Rounding
from vtt.creation_engine.types import parse_id
from vtt.creation_engine.units import UnitTable


class AdjustBoundPolicy(StrEnum):
    REJECT = "reject"
    CLAMP_REPORT_DELTA = "clamp_report_delta"


@dataclass(frozen=True, slots=True)
class BindingTemplate:
    id: str
    unit: str
    final_rounding: Rounding | None
    overrideable: bool = False      # manual override command allowed (§4, §5)
    base_editable: bool = False     # base edit command allowed (§5)


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    id: str
    unit: str
    maximum_binding: str | None
    adjust_bound_policy: AdjustBoundPolicy


@dataclass(frozen=True, slots=True)
class ChoiceTemplate:
    """Recognized selection IDs; no default selection or implicit numeric effect."""
    id: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class Ruleset:
    id: str
    version: str
    units: UnitTable
    bindings: tuple[BindingTemplate, ...] = field(default=())
    resources: tuple[ResourceSpec, ...] = field(default=())
    choices: tuple[ChoiceTemplate, ...] = field(default=())

    def __post_init__(self) -> None:
        parse_id(self.id)
        parse_id(self.version)
        ids = [b.id for b in self.bindings] + [r.id for r in self.resources] + [c.id for c in self.choices]
        for identifier in ids:
            parse_id(identifier)
        if len(ids) != len(set(ids)):
            raise ContractViolation(SEMANTIC_INVALID, f"ruleset {self.id} declares an ID twice")
        by_id = {b.id: b for b in self.bindings}
        for binding in self.bindings:
            self.units.unit(binding.unit)
            if binding.final_rounding is not None and not isinstance(binding.final_rounding, Rounding):
                raise ContractViolation(SEMANTIC_INVALID, f"binding {binding.id} needs a declared rounding policy")
        for resource in self.resources:
            if not isinstance(resource.adjust_bound_policy, AdjustBoundPolicy):
                raise ContractViolation(SEMANTIC_INVALID, f"resource {resource.id} needs an explicit adjustment policy")
            unit = self.units.unit(resource.unit)
            if resource.maximum_binding is not None:
                maximum = by_id.get(resource.maximum_binding)
                if maximum is None or self.units.unit(maximum.unit).dimension != unit.dimension:
                    raise ContractViolation(SEMANTIC_INVALID,
                                            f"resource {resource.id} needs a maximum binding of its own dimension")
        for choice in self.choices:
            if not choice.options or len(choice.options) != len(set(choice.options)):
                raise ContractViolation(SEMANTIC_INVALID, f"choice {choice.id} needs distinct options")
            for option in choice.options:
                parse_id(option)

    def binding(self, binding_id: str) -> BindingTemplate:
        for binding in self.bindings:
            if binding.id == binding_id:
                return binding
        raise ContractViolation(SEMANTIC_INVALID, f"binding {binding_id} is not declared by ruleset {self.id}")

    def canonical_form(self) -> dict:
        return {
            "id": self.id,
            "version": self.version,
            "units": self.units.canonical_form()["units"],
            "bindings": [{"id": b.id, "unit": b.unit, "finalRounding": b.final_rounding.value if b.final_rounding else None,
                          "overrideable": b.overrideable, "baseEditable": b.base_editable}
                         for b in sorted(self.bindings, key=lambda b: b.id)],
            "resources": [{"id": r.id, "unit": r.unit, "maximumBinding": r.maximum_binding,
                           "adjustBoundPolicy": r.adjust_bound_policy.value}
                          for r in sorted(self.resources, key=lambda r: r.id)],
            "choices": [{"id": c.id, "options": sorted(c.options)} for c in sorted(self.choices, key=lambda c: c.id)],
        }

    def artifact(self) -> dict:
        return {"kind": "ruleset", "id": self.id, "version": self.version, "digest": content_digest(self.canonical_form())}
