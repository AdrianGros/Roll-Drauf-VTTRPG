"""Exact rational numbers for mechanical values (spec v1.1.4 §6, §18).

Values are always reduced, the denominator is positive and zero is 0/1.
Intermediate numerators/denominators are bounded at 256 bits and wire values
at the safe integer range; exceeding either is BUDGET_EXCEEDED. Division by
zero is an ArithmeticFault. Default arithmetic never rounds: rounding is one
of four explicit operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
from math import gcd

from vtt.creation_engine.canonical import MAX_SAFE_INTEGER
from vtt.creation_engine.errors import (SCHEMA_INVALID, SEMANTIC_INVALID, ArithmeticFault,
                                        BudgetExceeded, ContractViolation)

MAX_INTERMEDIATE_BITS = 256

Path = tuple[str | int, ...]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@total_ordering
@dataclass(frozen=True, slots=True)
class Rational:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if not (_is_int(self.numerator) and _is_int(self.denominator)):
            raise TypeError("Rational parts must be int")
        if self.denominator <= 0 or gcd(self.numerator, self.denominator) != 1:
            raise ValueError("Rational must be reduced with a positive denominator; use Rational.of()")
        if max(self.numerator.bit_length(), self.denominator.bit_length()) > MAX_INTERMEDIATE_BITS:
            raise BudgetExceeded(f"rational exceeds the {MAX_INTERMEDIATE_BITS}-bit intermediate budget")

    @classmethod
    def of(cls, numerator: int, denominator: int = 1) -> Rational:
        """Build a reduced rational from any integer pair."""
        if not (_is_int(numerator) and _is_int(denominator)):
            raise TypeError("Rational parts must be int")
        if denominator == 0:
            raise ArithmeticFault("division by zero")
        if denominator < 0:
            numerator, denominator = -numerator, -denominator
        divisor = gcd(numerator, denominator)
        return cls(numerator // divisor, denominator // divisor)

    @classmethod
    def from_wire(cls, value: object, *, path: Path = ()) -> Rational:
        """Parse {numerator, denominator}; the wire form must already be reduced (§6)."""
        if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
            raise ContractViolation(SCHEMA_INVALID, "rational must have exactly numerator and denominator", path=path)
        numerator, denominator = value["numerator"], value["denominator"]
        if not (_is_int(numerator) and _is_int(denominator)) or denominator < 1 \
                or abs(numerator) > MAX_SAFE_INTEGER or denominator > MAX_SAFE_INTEGER:
            raise ContractViolation(SCHEMA_INVALID, "rational parts must be safe integers with denominator >= 1", path=path)
        if gcd(numerator, denominator) != 1:
            raise ContractViolation(SEMANTIC_INVALID, "rational is not in reduced form (zero is 0/1)", path=path)
        return cls(numerator, denominator)

    def to_wire(self) -> dict:
        if abs(self.numerator) > MAX_SAFE_INTEGER or self.denominator > MAX_SAFE_INTEGER:
            raise BudgetExceeded("rational exceeds the safe integer range of wire values")
        return {"numerator": self.numerator, "denominator": self.denominator}

    def __add__(self, other: Rational) -> Rational:
        if not isinstance(other, Rational):
            return NotImplemented
        return Rational.of(self.numerator * other.denominator + other.numerator * self.denominator,
                           self.denominator * other.denominator)

    def __sub__(self, other: Rational) -> Rational:
        if not isinstance(other, Rational):
            return NotImplemented
        return self + (-other)

    def __neg__(self) -> Rational:
        return Rational(-self.numerator, self.denominator)

    def __mul__(self, other: Rational) -> Rational:
        if not isinstance(other, Rational):
            return NotImplemented
        return Rational.of(self.numerator * other.numerator, self.denominator * other.denominator)

    def __truediv__(self, other: Rational) -> Rational:
        if not isinstance(other, Rational):
            return NotImplemented
        if other.numerator == 0:
            raise ArithmeticFault("division by zero")
        return Rational.of(self.numerator * other.denominator, self.denominator * other.numerator)

    def __lt__(self, other: Rational) -> bool:
        if not isinstance(other, Rational):
            return NotImplemented
        return self.numerator * other.denominator < other.numerator * self.denominator

    def floor(self) -> int:
        return self.numerator // self.denominator

    def ceil(self) -> int:
        return -((-self.numerator) // self.denominator)

    def truncate(self) -> int:
        quotient = abs(self.numerator) // self.denominator
        return quotient if self.numerator >= 0 else -quotient

    def round_nearest_ties_even(self) -> int:
        quotient, remainder = divmod(self.numerator, self.denominator)
        twice = 2 * remainder
        if twice < self.denominator or (twice == self.denominator and quotient % 2 == 0):
            return quotient
        return quotient + 1

    def __str__(self) -> str:
        return str(self.numerator) if self.denominator == 1 else f"{self.numerator}/{self.denominator}"
