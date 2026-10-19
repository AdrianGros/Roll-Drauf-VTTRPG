"""The core function set of core-safe-1 (spec v1.1.4 §6). Each call charges one operation (§18).

Unit rules: add, subtract, min and max need one dimension and answer in the
left operand's unit; multiply needs a dimensionless operand; divide takes a
dimensionless divisor, or two values of one dimension (giving a pure number).
core-safe-1 has no compound units. Rounding keeps the operand's unit.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from vtt.creation_engine.errors import SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.units import DIMENSIONLESS, Quantity, UnitTable


@dataclass(frozen=True, slots=True)
class CoreFunction:
    id: str
    arity: int
    apply: Callable[[UnitTable, tuple[Quantity, ...]], Quantity]


def _pure(units: UnitTable, quantity: Quantity) -> Rational | None:
    """The value as a pure number, or None when the quantity has a dimension."""
    if not units.is_dimensionless(quantity.unit):
        return None
    return units.convert(quantity, units.base_unit(DIMENSIONLESS)).value


def _add(units, args):
    return units.add(*args)


def _subtract(units, args):
    return units.subtract(*args)


def _multiply(units, args):
    left, right = args
    if (factor := _pure(units, left)) is not None:
        return right.scale(factor)
    if (factor := _pure(units, right)) is not None:
        return left.scale(factor)
    raise ContractViolation(SEMANTIC_INVALID, "core.multiply needs a dimensionless operand (no compound units)")


def _divide(units, args):
    left, right = args
    if (divisor := _pure(units, right)) is not None:
        return Quantity(left.value / divisor, left.unit)
    ratio = units.convert(left, right.unit).value / right.value      # same dimension, else SEMANTIC_INVALID
    return Quantity(ratio, units.base_unit(DIMENSIONLESS))


def _negate(units, args):
    (value,) = args
    return Quantity(-value.value, value.unit)


def _extreme(pick_right: Callable[[Rational, Rational], bool]):
    def apply(units, args):
        left, right = args
        converted = units.convert(right, left.unit)
        return converted if pick_right(converted.value, left.value) else left
    return apply


def _rounding(method: str):
    def apply(units, args):
        (value,) = args
        return Quantity(Rational.of(getattr(value.value, method)()), value.unit)
    return apply


CORE_FUNCTIONS: dict[str, CoreFunction] = {f.id: f for f in (
    CoreFunction("core.add", 2, _add),
    CoreFunction("core.subtract", 2, _subtract),
    CoreFunction("core.multiply", 2, _multiply),
    CoreFunction("core.divide", 2, _divide),
    CoreFunction("core.negate", 1, _negate),
    CoreFunction("core.min", 2, _extreme(lambda right, left: right < left)),
    CoreFunction("core.max", 2, _extreme(lambda right, left: right > left)),
    CoreFunction("core.floor", 1, _rounding("floor")),
    CoreFunction("core.ceil", 1, _rounding("ceil")),
    CoreFunction("core.truncate", 1, _rounding("truncate")),
    CoreFunction("core.round_nearest_ties_even", 1, _rounding("round_nearest_ties_even")),
)}

CORE_ARITIES: dict[str, int] = {f.id: f.arity for f in CORE_FUNCTIONS.values()}
