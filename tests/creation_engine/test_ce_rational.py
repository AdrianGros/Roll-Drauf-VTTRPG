"""WP1: exact rationals, explicit rounding and the 256-bit budget (spec v1.1.4 §6, §18)."""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from vtt.creation_engine.canonical import MAX_SAFE_INTEGER
from vtt.creation_engine.errors import (BUDGET_EXCEEDED, SCHEMA_INVALID, SEMANTIC_INVALID, ArithmeticFault,
                                        BudgetExceeded, ContractViolation)
from vtt.creation_engine.rational import Rational

R = Rational.of


def test_values_are_always_reduced_with_positive_denominator():
    assert R(2, -4) == Rational(-1, 2)
    assert R(0, -7) == Rational(0, 1)
    assert R(6, 3) == Rational(2, 1)


def test_direct_construction_refuses_unreduced_parts():
    with pytest.raises(ValueError):
        Rational(2, 4)
    with pytest.raises(TypeError):
        Rational(True, 1)


def test_stage_example_from_section_7_is_exact():
    # base 10, ADD 2, MULTIPLY 2 -> 24 (T14 foundation; stage ordering itself is WP2)
    assert (R(10) + R(2)) * R(2) == R(24)


@pytest.mark.parametrize("value, floor, ceil, truncate, even", [
    (R(5, 2), 2, 3, 2, 2),
    (R(7, 2), 3, 4, 3, 4),
    (R(-5, 2), -3, -2, -2, -2),
    (R(-7, 2), -4, -3, -3, -4),
    (R(1, 3), 0, 1, 0, 0),
    (R(-1, 3), -1, 0, 0, 0),
    (R(2, 3), 0, 1, 0, 1),
    (R(4), 4, 4, 4, 4),
])
def test_explicit_rounding_operations(value, floor, ceil, truncate, even):
    assert (value.floor(), value.ceil(), value.truncate(), value.round_nearest_ties_even()) == \
        (floor, ceil, truncate, even)


def test_division_by_zero_is_a_fault_not_nan():
    with pytest.raises(ArithmeticFault):
        R(1) / R(0)
    with pytest.raises(ArithmeticFault):
        R(1, 0)


def test_intermediate_values_are_bounded_at_256_bits():
    assert R(2**255).numerator.bit_length() == 256
    with pytest.raises(BudgetExceeded) as caught:
        R(2**256)
    assert caught.value.code == BUDGET_EXCEEDED
    with pytest.raises(BudgetExceeded):
        R(2**200) * R(2**100)


def test_wire_values_must_fit_the_safe_integer_range():
    assert R(MAX_SAFE_INTEGER).to_wire() == {"numerator": MAX_SAFE_INTEGER, "denominator": 1}
    with pytest.raises(BudgetExceeded):
        R(MAX_SAFE_INTEGER + 1).to_wire()


def test_from_wire_round_trip():
    assert Rational.from_wire({"numerator": -3, "denominator": 4}).to_wire() == {"numerator": -3, "denominator": 4}


@pytest.mark.parametrize("wire, code", [
    ({"numerator": 2, "denominator": 4}, SEMANTIC_INVALID),     # not reduced
    ({"numerator": 0, "denominator": 5}, SEMANTIC_INVALID),     # zero must be 0/1
    ({"numerator": 1, "denominator": 0}, SCHEMA_INVALID),
    ({"numerator": 1, "denominator": -2}, SCHEMA_INVALID),
    ({"numerator": 1.0, "denominator": 2}, SCHEMA_INVALID),
    ({"numerator": True, "denominator": 1}, SCHEMA_INVALID),
    ({"numerator": MAX_SAFE_INTEGER + 1, "denominator": 1}, SCHEMA_INVALID),
    ({"numerator": 1}, SCHEMA_INVALID),
    ({"numerator": 1, "denominator": 2, "extra": 0}, SCHEMA_INVALID),
])
def test_from_wire_rejects_invalid_forms(wire, code):
    with pytest.raises(ContractViolation) as caught:
        Rational.from_wire(wire)
    assert caught.value.code == code


def test_mixing_with_python_numbers_is_refused():
    with pytest.raises(TypeError):
        R(1) + 1
    with pytest.raises(TypeError):
        R(1) * 0.5


small = st.integers(-10**6, 10**6)
rationals = st.builds(R, small, st.integers(1, 10**6))


@settings(max_examples=300, deadline=None)
@given(rationals, rationals, rationals)
def test_field_laws_hold_exactly(a, b, c):
    assert a + b == b + a and a * b == b * a
    assert (a + b) + c == a + (b + c)
    assert a * (b + c) == a * b + a * c
    assert (a - b) + b == a


@settings(max_examples=300, deadline=None)
@given(rationals, rationals)
def test_division_inverts_multiplication(a, b):
    assume(b != R(0))
    assert (a / b) * b == a


@settings(max_examples=300, deadline=None)
@given(rationals)
def test_rounding_brackets_the_value(x):
    assert R(x.floor()) <= x < R(x.floor() + 1)
    assert R(x.ceil() - 1) < x <= R(x.ceil())
    assert x.truncate() == (x.floor() if x >= R(0) else x.ceil())
    nearest = R(x.round_nearest_ties_even())
    distance = nearest - x if nearest >= x else x - nearest
    assert distance <= R(1, 2)
    if distance == R(1, 2):
        assert x.round_nearest_ties_even() % 2 == 0
