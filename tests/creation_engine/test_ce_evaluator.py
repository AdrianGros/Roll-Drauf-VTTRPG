"""WP2: the core-safe-1 evaluator (spec v1.1.4 §6–7, §18; acceptance T14, T15, T26 budget part, T53 foundation)."""

import itertools

import pytest

from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.errors import BUDGET_EXCEEDED, EFFECT_CONFLICT, SEMANTIC_INVALID, ArithmeticFault, ContractViolation
from vtt.creation_engine.evaluator import (CORE_ARITIES, Binding, EffectApplication, Fuel, Inputs, Limits, Rounding, Stage,
                                           evaluate, parse_formula, parse_predicate)
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import InstanceRef
from vtt.creation_engine.units import DIMENSIONLESS, Quantity, Unit, UnitTable

R = Rational.of
ZERO = "sha256:" + "0" * 64
TARGET = InstanceRef("actor:k", "scope:s")
UNITS = UnitTable([
    Unit("unit:dimensionless", DIMENSIONLESS, R(1)),
    Unit("unit:percent", DIMENSIONLESS, R(1, 100)),
    Unit("unit:point", "dimension:score", R(1)),
    Unit("unit:hp", "dimension:hp", R(1)),
    Unit("unit:meter", "dimension:distance", R(1)),
    Unit("unit:foot", "dimension:distance", R(3048, 10000)),
])


def q(n, d=1, unit="unit:point"):
    return {"value": {"numerator": n, "denominator": d}, "unit": unit}


def lit(n, d=1, unit="unit:point"):
    return {"node": "literal", "value": q(n, d, unit)}


def read(binding, stage="final"):
    return {"node": "read", "bindingId": binding, "stage": stage}


def call(function, *args):
    return {"node": "call", "functionId": function, "args": list(args)}


def app(app_id, binding, operator, value, *, priority=0, group=None, policy="all", source="item:sword",
        feature="feature:flames", target="actor:k"):
    return EffectApplication.from_wire({
        "applicationId": app_id,
        "sourceInstance": {"kind": "instance", "id": source, "scopeId": "scope:s"},
        "sourceRevision": {"kind": "revision", "id": "rev:1", "definitionId": "def:1", "digest": ZERO},
        "originId": "origin:1",
        "target": {"kind": "instance", "id": target, "scopeId": "scope:s"},
        "stackGroupId": group or f"group:{app_id}",
        "stackPolicy": policy,
        "sourceFeatureKey": feature,
        "priority": priority,
        "duration": {"kind": "permanent"},
        "cadence": None,
        "changes": [{"targetBindingId": binding, "operator": operator, "value": value}],
        "policyId": "policy:default",
    })


def defense(base=10, rounding=None):
    return Binding("rdl.defense", "unit:point", None if base is None else Quantity(R(base), "unit:point"), rounding)


def run(applications, bindings=None, **kwargs):
    return evaluate(TARGET, bindings or [defense()], applications, units=UNITS, **kwargs)


def result(applications, bindings=None, binding="rdl.defense", **kwargs):
    return run(applications, bindings, **kwargs).results[binding]


# --- T14: fixed stage order, independent of serialization order ------------------------------------

def test_t14_base_add_multiply_is_24_in_every_order():
    applications = [app("a:add", "rdl.defense", "ADD", lit(2)),
                    app("a:mul", "rdl.defense", "MULTIPLY", lit(2, unit="unit:dimensionless"))]
    outcomes = {result(list(order)) for order in itertools.permutations(applications)}
    assert len(outcomes) == 1
    (only,) = outcomes
    assert only.value == Quantity(R(24), "unit:point") and only.status == "resolved"
    assert [(c.stage, c.application_ids) for c in only.contributions] == [(Stage.ADD, ("a:add",)), (Stage.MULTIPLY, ("a:mul",))]
    assert dict(only.stage_values)[Stage.ADD] == Quantity(R(12), "unit:point")


def test_multiply_factors_convert_from_any_dimensionless_unit():
    assert result([app("a", "rdl.defense", "MULTIPLY", lit(150, unit="unit:percent"))]).value == Quantity(R(15), "unit:point")


# --- T15: SET resolution ---------------------------------------------------------------------------

def test_t15_equal_priority_sets_that_disagree_conflict_in_any_order():
    sets = [app("s:1", "rdl.defense", "SET", lit(13), priority=5), app("s:2", "rdl.defense", "SET", lit(15), priority=5)]
    for order in itertools.permutations(sets):
        outcome = result(list(order))
        assert outcome.status == "conflict" and outcome.code == EFFECT_CONFLICT
        assert outcome.conflicting_applications == ("s:1", "s:2")


def test_equal_valued_sets_coalesce_and_keep_all_provenance():
    outcome = result([app("s:1", "rdl.defense", "SET", lit(13), priority=5), app("s:2", "rdl.defense", "SET", lit(13), priority=5)])
    assert outcome.value == Quantity(R(13), "unit:point")
    assert outcome.contributions[0].application_ids == ("s:1", "s:2")


def test_highest_priority_set_wins_and_lower_unknowns_do_not_matter():
    outcome = result([app("s:low", "rdl.defense", "SET", read("rdl.unknown"), priority=1),
                      app("s:high", "rdl.defense", "SET", lit(17), priority=9)],
                     bindings=[defense(), Binding("rdl.unknown", "unit:point", None)])
    assert outcome.value == Quantity(R(17), "unit:point")


def test_set_replaces_an_unknown_base_but_an_unknown_winner_stays_unresolved():
    assert result([app("s", "rdl.defense", "SET", lit(12))], bindings=[defense(base=None)]).status == "resolved"
    outcome = result([app("s", "rdl.defense", "SET", read("rdl.unknown"))], bindings=[defense(), Binding("rdl.unknown", "unit:point", None)])
    assert outcome.status == "unresolved" and "base value of rdl.unknown is unknown" in outcome.reasons


# --- clamp and final rounding ----------------------------------------------------------------------

def test_clamp_takes_greatest_lower_and_least_upper_bound():
    outcome = result([app("lo:1", "rdl.defense", "LOWER_BOUND", lit(12)), app("lo:2", "rdl.defense", "LOWER_BOUND", lit(14)),
                      app("hi:1", "rdl.defense", "UPPER_BOUND", lit(20)), app("hi:2", "rdl.defense", "UPPER_BOUND", lit(18))])
    assert outcome.value == Quantity(R(14), "unit:point")
    assert {c.application_ids for c in outcome.contributions} == {("lo:2",), ("hi:2",)}


def test_empty_clamp_interval_is_an_effect_conflict():
    outcome = result([app("lo", "rdl.defense", "LOWER_BOUND", lit(15)), app("hi", "rdl.defense", "UPPER_BOUND", lit(12))])
    assert outcome.code == EFFECT_CONFLICT and outcome.conflicting_applications == ("hi", "lo")


@pytest.mark.parametrize("rounding, expected", [(None, R(21, 2)), (Rounding.FLOOR, R(10)), (Rounding.CEIL, R(11)),
                                                (Rounding.TRUNCATE, R(10)), (Rounding.NEAREST_TIES_EVEN, R(10))])
def test_final_rounding_is_the_binding_schemas_explicit_operator(rounding, expected):
    outcome = result([app("half", "rdl.defense", "ADD", lit(1, 2))], bindings=[defense(rounding=rounding)])
    assert outcome.value == Quantity(expected, "unit:point")
    assert dict(outcome.stage_values)[Stage.CLAMP] == Quantity(R(21, 2), "unit:point")


# --- stacking (§7) ---------------------------------------------------------------------------------

def test_all_policy_sums_every_contribution():
    assert result([app("a", "rdl.defense", "ADD", lit(1), group="g", policy="all"),
                   app("b", "rdl.defense", "ADD", lit(2), group="g", policy="all")]).value == Quantity(R(13), "unit:point")


def test_unique_by_source_coalesces_identical_payloads_from_one_source():
    outcome = result([app("a", "rdl.defense", "ADD", lit(1), group="g", policy="unique_by_source"),
                      app("b", "rdl.defense", "ADD", lit(1), group="g", policy="unique_by_source")])
    assert outcome.value == Quantity(R(11), "unit:point")
    assert outcome.contributions[0].application_ids == ("a", "b")


def test_unique_by_source_conflicts_on_differing_payloads_but_keeps_distinct_sources():
    same_source = result([app("a", "rdl.defense", "ADD", lit(1), group="g", policy="unique_by_source"),
                          app("b", "rdl.defense", "ADD", lit(2), group="g", policy="unique_by_source")])
    assert same_source.code == EFFECT_CONFLICT
    two_sources = result([app("a", "rdl.defense", "ADD", lit(1), group="g", policy="unique_by_source", source="item:ring"),
                          app("b", "rdl.defense", "ADD", lit(2), group="g", policy="unique_by_source", source="item:cloak")])
    assert two_sources.value == Quantity(R(13), "unit:point")


def test_highest_keeps_the_largest_and_all_equal_winners():
    outcome = result([app("a", "rdl.defense", "ADD", lit(2), group="g", policy="highest", source="item:a"),
                      app("b", "rdl.defense", "ADD", lit(3), group="g", policy="highest", source="item:b"),
                      app("c", "rdl.defense", "ADD", lit(3), group="g", policy="highest", source="item:c")])
    assert outcome.value == Quantity(R(13), "unit:point")
    assert outcome.contributions[0].application_ids == ("b", "c")


def test_highest_needs_same_unit_values():
    outcome = result([app("a", "rdl.defense", "ADD", lit(2), group="g", policy="highest"),
                      app("b", "rdl.defense", "ADD", lit(3, unit="unit:dimensionless"), group="g", policy="highest")])
    assert outcome.code == EFFECT_CONFLICT


def test_exclusive_group_needs_an_explicit_choice_between_sources():
    applications = [app("a", "rdl.defense", "ADD", lit(2), group="g:armor", policy="exclusive", source="item:plate"),
                    app("b", "rdl.defense", "ADD", lit(3), group="g:armor", policy="exclusive", source="item:mail")]
    assert result(applications).code == EFFECT_CONFLICT
    chosen = result(applications, inputs=Inputs(exclusive_choices={"g:armor": ("item:plate", "feature:flames")}))
    assert chosen.value == Quantity(R(12), "unit:point")


def test_mixed_policies_in_one_group_conflict():
    assert result([app("a", "rdl.defense", "ADD", lit(1), group="g", policy="all"),
                   app("b", "rdl.defense", "ADD", lit(1), group="g", policy="highest")]).code == EFFECT_CONFLICT


def test_priority_never_overrides_a_stack_conflict():
    outcome = result([app("low:a", "rdl.defense", "SET", lit(11), priority=1, group="g", policy="unique_by_source"),
                      app("low:b", "rdl.defense", "SET", lit(12), priority=1, group="g", policy="unique_by_source"),
                      app("high", "rdl.defense", "SET", lit(20), priority=9)])
    assert outcome.code == EFFECT_CONFLICT


# --- unresolved values and three-valued predicates (§6–7) ------------------------------------------

def _predicates(**named):
    return {name: parse_predicate(wire, arities=CORE_ARITIES) for name, wire in named.items()}


def test_unknown_base_stays_unresolved_through_add():
    outcome = result([app("a", "rdl.defense", "ADD", lit(2))], bindings=[defense(base=None)])
    assert outcome.status == "unresolved" and outcome.value is None


def test_conditional_on_an_unknown_predicate_is_unresolved_never_false():
    predicates = _predicates(**{"pred:undead": {"node": "human", "questionId": "q:undead", "questionVersion": 1,
                                                "responderRuleId": "rule:gm"}})
    formula = {"node": "if", "conditionBindingId": "pred:undead", "then": lit(4), "else": lit(1)}
    applications = [app("a", "rdl.defense", "ADD", formula)]
    assert result(applications, predicates=predicates).status == "unresolved"
    answered = Inputs(human_answers={("q:undead", 1, "rule:gm"): True})
    assert result(applications, predicates=predicates, inputs=answered).value == Quantity(R(14), "unit:point")


@pytest.mark.parametrize("node, expected", [("and", R(11)), ("or", R(14))])
def test_kleene_logic_decides_despite_an_unknown_operand(node, expected):
    unknown = {"node": "manual_toggle", "toggleId": "toggle:unset"}
    decisive = {"node": "manual_toggle", "toggleId": "toggle:set"}
    predicates = _predicates(**{"pred:p": {"node": node, "args": [unknown, decisive]}})
    toggles = Inputs(manual_toggles={"toggle:set": node == "or"})      # and(unknown, false)=false; or(unknown, true)=true
    formula = {"node": "if", "conditionBindingId": "pred:p", "then": lit(4), "else": lit(1)}
    assert result([app("a", "rdl.defense", "ADD", formula)], predicates=predicates, inputs=toggles).value == Quantity(expected, "unit:point")


def test_is_known_and_compare_read_other_bindings():
    predicates = _predicates(**{"pred:known": {"node": "is_known", "bindingId": "rdl.unknown"},
                                "pred:tough": {"node": "compare", "operator": "ge", "left": read("rdl.hp"),
                                               "right": {"node": "literal", "value": q(10, unit="unit:hp")}}})
    bindings = [defense(), Binding("rdl.unknown", "unit:point", None), Binding("rdl.hp", "unit:hp", Quantity(R(12), "unit:hp"))]
    applications = [app("a", "rdl.defense", "ADD", {"node": "if", "conditionBindingId": "pred:known", "then": lit(100), "else": lit(1)}),
                    app("b", "rdl.defense", "ADD", {"node": "if", "conditionBindingId": "pred:tough", "then": lit(2), "else": lit(0)})]
    assert result(applications, bindings=bindings, predicates=predicates).value == Quantity(R(13), "unit:point")


# --- reads, dependencies and cycles ----------------------------------------------------------------

def test_reads_follow_other_bindings_and_earlier_stages_of_the_same_binding():
    bindings = [defense(), Binding("rdl.dex", "unit:point", Quantity(R(3), "unit:point"))]
    applications = [app("dex", "rdl.defense", "ADD", read("rdl.dex")),
                    app("half", "rdl.defense", "ADD", call("core.divide", read("rdl.defense", "base"), lit(2, unit="unit:dimensionless")))]
    assert result(applications, bindings=bindings).value == Quantity(R(18), "unit:point")


@pytest.mark.parametrize("applications", [
    [app("self", "rdl.defense", "ADD", read("rdl.defense", "add"))],
    [app("x", "rdl.defense", "ADD", read("rdl.other")), app("y", "rdl.other", "ADD", read("rdl.defense"))],
])
def test_dependency_cycles_are_invalid(applications):
    bindings = [defense(), Binding("rdl.other", "unit:point", Quantity(R(1), "unit:point"))]
    with pytest.raises(ContractViolation) as caught:
        run(applications, bindings)
    assert caught.value.code == SEMANTIC_INVALID and "dependency cycle" in caught.value.detail


def test_predicate_cycles_are_invalid():
    predicates = _predicates(**{"pred:a": {"node": "binding", "bindingId": "pred:b"}, "pred:b": {"node": "not", "arg": {"node": "binding", "bindingId": "pred:a"}}})
    with pytest.raises(ContractViolation, match="dependency cycle"):
        run([], predicates=predicates)


# --- units (§6) ------------------------------------------------------------------------------------

def test_quantities_convert_exactly_into_the_binding_unit():
    speed = Binding("rdl.speed", "unit:meter", Quantity(R(9), "unit:meter"))
    outcome = result([app("boots", "rdl.speed", "ADD", lit(10, unit="unit:foot"))], bindings=[speed], binding="rdl.speed")
    assert outcome.value == Quantity(R(9) + R(381, 125), "unit:meter")


@pytest.mark.parametrize("applications", [
    [app("a", "rdl.defense", "ADD", lit(2, unit="unit:hp"))],
    [app("a", "rdl.defense", "MULTIPLY", lit(2))],
    [app("a", "rdl.defense", "ADD", call("core.multiply", lit(2), lit(3)))],
])
def test_dimension_errors_are_rejected(applications):
    with pytest.raises(ContractViolation) as caught:
        run(applications)
    assert caught.value.code == SEMANTIC_INVALID


def test_division_by_zero_fails_the_evaluation_instead_of_producing_nan():
    with pytest.raises(ArithmeticFault):
        run([app("a", "rdl.defense", "ADD", call("core.divide", lit(1), lit(0, unit="unit:dimensionless")))])


# --- budgets and admission (§18, T26 budget part) ----------------------------------------------------

def _nested(depth):
    formula = lit(1)
    for _ in range(depth - 1):
        formula = call("core.negate", formula)
    return formula


def test_formula_depth_and_node_limits_are_checked_at_admission():
    parse_formula(_nested(64), arities=CORE_ARITIES)
    with pytest.raises(ContractViolation) as caught:
        parse_formula(_nested(65), arities=CORE_ARITIES)
    assert caught.value.code == BUDGET_EXCEEDED
    wide = lit(0)
    for _ in range(12):
        wide = call("core.add", wide, wide)          # 2**13 - 1 = 8191 nodes, depth 13
    with pytest.raises(ContractViolation) as caught:
        parse_formula(wide, arities=CORE_ARITIES)
    assert caught.value.code == BUDGET_EXCEEDED


def test_pathologically_deep_json_is_a_budget_failure_not_a_crash():
    with pytest.raises(ContractViolation) as caught:
        parse_strict_json("[" * 100_000 + "]" * 100_000)
    assert caught.value.code == BUDGET_EXCEEDED


@pytest.mark.parametrize("wire, message", [
    (call("core.pow", lit(1), lit(2)), "not available"),
    (call("core.negate", lit(1), lit(2)), "argument"),
])
def test_unknown_functions_and_wrong_arity_are_semantic_errors(wire, message):
    with pytest.raises(ContractViolation, match=message) as caught:
        parse_formula(wire, arities=CORE_ARITIES)
    assert caught.value.code == SEMANTIC_INVALID


def test_fuel_is_charged_per_executed_node_and_bounded():
    applications = [app("a", "rdl.defense", "ADD", call("core.add", lit(1), lit(1)))]
    assert run(applications).fuel_used == 3
    with pytest.raises(ContractViolation) as caught:
        run(applications, fuel=Fuel(limit=2))
    assert caught.value.code == BUDGET_EXCEEDED


@pytest.mark.parametrize("limits", [Limits(max_applications=1), Limits(max_derived_nodes=5)])
def test_instance_limits_are_enforced(limits):
    with pytest.raises(ContractViolation) as caught:
        run([app("a", "rdl.defense", "ADD", lit(1)), app("b", "rdl.defense", "ADD", lit(1))], limits=limits)
    assert caught.value.code == BUDGET_EXCEEDED


# --- input validation --------------------------------------------------------------------------------

@pytest.mark.parametrize("applications, message", [
    ([app("a", "rdl.defense", "ADD", lit(1), target="actor:other")], "another occurrence"),
    ([app("a", "rdl.missing", "ADD", lit(1))], "not declared"),
    ([app("a", "rdl.defense", "ADD", read("rdl.missing"))], "not declared"),
    ([app("a", "rdl.defense", "ADD", {"node": "if", "conditionBindingId": "pred:none", "then": lit(1), "else": lit(0)})], "not registered"),
    ([app("a", "rdl.defense", "ADD", lit(1)), app("a", "rdl.defense", "ADD", lit(2))], "supplied twice"),
])
def test_invalid_inputs_are_semantic_errors(applications, message):
    with pytest.raises(ContractViolation, match=message) as caught:
        run(applications)
    assert caught.value.code == SEMANTIC_INVALID


def test_effect_applications_are_validated_against_the_wire_contract():
    with pytest.raises(ContractViolation) as caught:
        EffectApplication.from_wire({"applicationId": "a"})
    assert caught.value.code == "SCHEMA_INVALID"
