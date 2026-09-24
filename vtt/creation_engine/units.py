"""Units and quantities (spec v1.1.4 §6).

Units are registered, namespaced IDs with exact conversion ratios to their
dimension's base unit. Quantities of different dimensions (currency,
distance, duration, dimensionless, ruleset-defined) can never be combined.
The table's canonical form is what an ExecutionLock pins as unitTableDigest
(§12); the ruleset package supplies the actual units.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from vtt.creation_engine.canonical import content_digest
from vtt.creation_engine.errors import SCHEMA_INVALID, SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import parse_id

Path = tuple[str | int, ...]
ONE = Rational.of(1)

# Core-registered dimension of pure numbers; MULTIPLY factors and unit ratios live here (§6, §7).
DIMENSIONLESS = "dimension:dimensionless"


@dataclass(frozen=True, slots=True)
class Unit:
    id: str
    dimension: str
    to_base: Rational   # exact factor: 1 of this unit == to_base of the dimension's base unit


@dataclass(frozen=True, slots=True)
class Quantity:
    value: Rational
    unit: str

    @classmethod
    def from_wire(cls, value: object, *, path: Path = ()) -> Quantity:
        if not isinstance(value, dict) or set(value) != {"value", "unit"}:
            raise ContractViolation(SCHEMA_INVALID, "quantity must have exactly value and unit", path=path)
        return cls(Rational.from_wire(value["value"], path=(*path, "value")), parse_id(value["unit"], path=(*path, "unit")))

    def to_wire(self) -> dict:
        return {"value": self.value.to_wire(), "unit": self.unit}

    def scale(self, factor: Rational) -> Quantity:
        """Multiply by a dimensionless factor; the unit is unchanged."""
        return Quantity(self.value * factor, self.unit)


class UnitTable:
    """An immutable registry of units, validated on construction."""

    def __init__(self, units: Iterable[Unit]):
        by_id: dict[str, Unit] = {}
        base_units: dict[str, str] = {}
        for unit in units:
            parse_id(unit.id)
            parse_id(unit.dimension)
            if unit.id in by_id:
                raise ContractViolation(SEMANTIC_INVALID, f"unit {unit.id} is registered twice")
            if unit.to_base <= Rational.of(0):
                raise ContractViolation(SEMANTIC_INVALID, f"unit {unit.id} needs a positive conversion ratio")
            if unit.to_base == ONE:
                if unit.dimension in base_units:
                    raise ContractViolation(SEMANTIC_INVALID, f"dimension {unit.dimension} has two base units")
                base_units[unit.dimension] = unit.id
            by_id[unit.id] = unit
        missing = {u.dimension for u in by_id.values()} - set(base_units)
        if missing:
            raise ContractViolation(SEMANTIC_INVALID, f"dimensions without a base unit: {sorted(missing)}")
        self._units = by_id
        self._base_units = base_units

    def unit(self, unit_id: str) -> Unit:
        try:
            return self._units[unit_id]
        except KeyError:
            raise ContractViolation(SEMANTIC_INVALID, f"unit {unit_id} is not registered") from None

    def base_unit(self, dimension: str) -> str:
        try:
            return self._base_units[dimension]
        except KeyError:
            raise ContractViolation(SEMANTIC_INVALID, f"dimension {dimension} is not registered") from None

    def is_dimensionless(self, unit_id: str) -> bool:
        return self.unit(unit_id).dimension == DIMENSIONLESS

    def convert(self, quantity: Quantity, unit_id: str) -> Quantity:
        source, target = self.unit(quantity.unit), self.unit(unit_id)
        if source.dimension != target.dimension:
            raise ContractViolation(SEMANTIC_INVALID,
                                    f"cannot convert {source.dimension} ({source.id}) to {target.dimension} ({target.id})")
        return Quantity(quantity.value * source.to_base / target.to_base, target.id)

    def add(self, left: Quantity, right: Quantity) -> Quantity:
        """Sum in the left operand's unit; incompatible dimensions are rejected, never coerced."""
        return Quantity(left.value + self.convert(right, left.unit).value, left.unit)

    def subtract(self, left: Quantity, right: Quantity) -> Quantity:
        return Quantity(left.value - self.convert(right, left.unit).value, left.unit)

    def canonical_form(self) -> dict:
        return {"units": [{"id": u.id, "dimension": u.dimension, "toBase": u.to_base.to_wire()}
                          for u in sorted(self._units.values(), key=lambda u: u.id)]}

    def digest(self) -> str:
        return content_digest(self.canonical_form())
