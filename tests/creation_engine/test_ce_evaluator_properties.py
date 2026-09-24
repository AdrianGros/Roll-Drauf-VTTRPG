"""WP2 property tests: the evaluator matches the §7 stage algebra and ignores serialization order (T14)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from vtt.creation_engine.errors import EFFECT_CONFLICT
from vtt.creation_engine.evaluator import Binding, evaluate
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.units import Quantity

from test_ce_evaluator import TARGET, UNITS, app, lit

R = Rational.of

values = st.builds(R, st.integers(-50, 50), st.integers(1, 6))
changes = st.lists(st.tuples(st.sampled_from(["ADD", "MULTIPLY", "LOWER_BOUND", "UPPER_BOUND"]), values), max_size=8)


def _wire_value(operator, value):
    unit = "unit:dimensionless" if operator == "MULTIPLY" else "unit:point"
    return lit(value.numerator, value.denominator, unit)


def _expected(base, drawn):
    total = base
    for operator, value in drawn:
        if operator == "ADD":
            total = total + value
    for operator, value in drawn:
        if operator == "MULTIPLY":
            total = total * value
    lowers = [v for o, v in drawn if o == "LOWER_BOUND"]
    uppers = [v for o, v in drawn if o == "UPPER_BOUND"]
    lower, upper = (max(lowers) if lowers else None), (min(uppers) if uppers else None)
    if lower is not None and upper is not None and lower > upper:
        return None
    if lower is not None and total < lower:
        total = lower
    if upper is not None and total > upper:
        total = upper
    return total


@settings(max_examples=250, deadline=None)
@given(values, changes, st.randoms(use_true_random=False))
def test_stage_algebra_holds_for_any_set_of_numeric_changes(base, drawn, rng):
    applications = [app(f"app:{i:02d}", "rdl.defense", operator, _wire_value(operator, value))
                    for i, (operator, value) in enumerate(drawn)]
    bindings = [Binding("rdl.defense", "unit:point", Quantity(base, "unit:point"))]
    first = evaluate(TARGET, bindings, applications, units=UNITS).results["rdl.defense"]
    shuffled = list(applications)
    rng.shuffle(shuffled)
    second = evaluate(TARGET, bindings, shuffled, units=UNITS)
    assert second.results["rdl.defense"] == first                 # identical value, stages and provenance
    expected = _expected(base, drawn)
    if expected is None:
        assert first.code == EFFECT_CONFLICT
    else:
        assert first.value == Quantity(expected, "unit:point")
