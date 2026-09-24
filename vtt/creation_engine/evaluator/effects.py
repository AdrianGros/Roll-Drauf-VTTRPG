"""Effect applications and numeric changes (spec v1.1.4 §7, contract 1.1.3 `EffectApplication`).

An application's changes resolve into the fixed stages; its stack group and
policy decide which changes survive before numeric reduction. Duration and
cadence decide whether an application is active; that is the time ledger's
job (G2), so the evaluator only receives active applications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from vtt.creation_engine.canonical import content_digest
from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.evaluator.functions import CORE_ARITIES
from vtt.creation_engine.evaluator.nodes import Formula, Stage, parse_formula
from vtt.creation_engine.types import InstanceRef, RevisionRef, parse_reference


class Operator(StrEnum):
    SET = "SET"
    ADD = "ADD"
    MULTIPLY = "MULTIPLY"
    LOWER_BOUND = "LOWER_BOUND"
    UPPER_BOUND = "UPPER_BOUND"


STAGE_OF = {Operator.SET: Stage.SET, Operator.ADD: Stage.ADD, Operator.MULTIPLY: Stage.MULTIPLY,
            Operator.LOWER_BOUND: Stage.CLAMP, Operator.UPPER_BOUND: Stage.CLAMP}


class StackPolicy(StrEnum):
    ALL = "all"
    UNIQUE_BY_SOURCE = "unique_by_source"
    HIGHEST = "highest"
    EXCLUSIVE = "exclusive"


@dataclass(frozen=True, slots=True)
class NumericChange:
    target_binding_id: str
    operator: Operator
    value: Formula
    payload_digest: str     # identity of the mechanical payload, for coalescing (§7)


@dataclass(frozen=True, slots=True)
class EffectApplication:
    application_id: str
    source_instance: InstanceRef
    source_revision: RevisionRef
    origin_id: str
    target: InstanceRef
    stack_group_id: str
    stack_policy: StackPolicy
    source_feature_key: str
    priority: int
    changes: tuple[NumericChange, ...]
    policy_id: str
    duration: dict = field(compare=False)
    cadence: dict | None = field(compare=False)

    @property
    def source_key(self) -> tuple[str, str]:
        """Source-instance-plus-feature identity used by unique_by_source and exclusive (§7)."""
        return (self.source_instance.id, self.source_feature_key)

    @classmethod
    def from_wire(cls, wire: object) -> EffectApplication:
        validate_definition("EffectApplication", wire)
        changes = tuple(NumericChange(change["targetBindingId"], Operator(change["operator"]),
                                      parse_formula(change["value"], arities=CORE_ARITIES), content_digest(change))
                        for change in wire["changes"])
        return cls(
            application_id=wire["applicationId"],
            source_instance=parse_reference(wire["sourceInstance"], accept=(InstanceRef,)),
            source_revision=parse_reference(wire["sourceRevision"], accept=(RevisionRef,)),
            origin_id=wire["originId"],
            target=parse_reference(wire["target"], accept=(InstanceRef,)),
            stack_group_id=wire["stackGroupId"],
            stack_policy=StackPolicy(wire["stackPolicy"]),
            source_feature_key=wire["sourceFeatureKey"],
            priority=wire["priority"],
            changes=changes,
            policy_id=wire["policyId"],
            duration=wire["duration"],
            cadence=wire["cadence"],
        )
