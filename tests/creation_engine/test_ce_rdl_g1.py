"""The D3 test ruleset is explicit, reproducible and isolated from legacy state."""

from dataclasses import replace

import pytest

from vtt.creation_engine.content.rdl_g1 import rdl_g1_ruleset
from vtt.creation_engine.evaluator import Binding, evaluate
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import InstanceRef
from vtt.creation_engine.units import Quantity


def test_g1_package_pin():
    assert rdl_g1_ruleset().artifact() == {
        "kind": "ruleset", "id": "rules.roll-drauf-light-g1", "version": "1.0.0",
        "digest": "sha256:7b203d9e4c506b78f0d983a417b902248e33ee8dd3fccc404fbc94e841214587",
    }


def test_signature_ids_match_the_existing_catalogue_without_importing_it_at_runtime():
    from vtt.roll_drauf.catalog import CLASSES
    legacy = {choice['slug']: tuple(option['slug'] for option in choice['options'])
              for character_class in CLASSES.values() for level in character_class['progression'].values()
              for choice in level['choices_available'] if choice['choice_type'] == 'signature'}
    assert {choice.id: choice.options for choice in rdl_g1_ruleset().choices} == legacy


def test_unreconciled_bases_stay_unknown_in_the_real_evaluator():
    rules = rdl_g1_ruleset()
    bindings = [Binding(b.id, b.unit, None, b.final_rounding) for b in rules.bindings]
    result = evaluate(InstanceRef("actor:unreconciled", "scope:test"), bindings, [], units=rules.units)
    assert set(result.results) == {"str", "dex", "con", "int", "wis", "cha", "defense", "training_bonus",
                                   "hp_max", "fokus_max"}
    assert all(r.status == "unresolved" and r.value is None for r in result.results.values())


def test_g1_rounding_is_applied_by_the_real_evaluator():
    rules = rdl_g1_ruleset()
    template = rules.binding("defense")
    binding = Binding(template.id, template.unit, Quantity(Rational.of(25, 2), template.unit), template.final_rounding)
    result = evaluate(InstanceRef("actor:reconciled", "scope:test"), [binding], [], units=rules.units)
    assert result.results["defense"].value == Quantity(Rational.of(12), "rdl:point")


def test_health_and_focus_are_not_interchangeable():
    with pytest.raises(ContractViolation):
        rdl_g1_ruleset().units.convert(Quantity(Rational.of(1), "rdl:hp"), "rdl:fokus")


def test_signature_choices_are_pinned_with_the_ruleset():
    rules = rdl_g1_ruleset()
    assert replace(rules, choices=()).artifact()['digest'] != rules.artifact()['digest']
    assert replace(rules, choices=tuple(reversed(rules.choices))).artifact() == rules.artifact()
