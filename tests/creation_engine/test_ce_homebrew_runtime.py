"""Mechanical outcomes, choices, progression, validation and bounded execution."""

from copy import deepcopy

import pytest

from vtt.creation_engine import homebrew_runtime as r
from vtt.creation_engine.compiler import homebrew as h
from vtt.creation_engine.compiler.catalog import registry
from vtt.creation_engine.content import new_id
from vtt.creation_engine.errors import ContractViolation
from homebrew_examples import build, documents, examples, feature, grants


def compile_state(kind, values):
    guide, state = h.interview(kind), h.interview(kind).empty()
    for q in guide.questions:
        value = values
        for key in q.path:
            if key not in value:
                break
            value = value[key]
        else:
            state, _, _ = guide.change(state, {"questionId": q.id, "questionVersion": q.version},
                answer=q.answer(value), author=1, locale="en")
    return state


@pytest.mark.parametrize("kind,values", examples())
def test_profiles_validate_and_modes_preserve_authored_mechanics(kind, values):
    state = compile_state(kind, values)
    assert h.quality_gates(kind, state, "runtime_ready") == []
    assert h.quality_gates(kind, state, "automation_complete")
    registry(kind).validate(kind, values)
    for mode in ("guided", "structured", "advanced"):
        for locale in ("de", "en", "fr"):
            assert h.interview(kind).present(state, mode=mode, locale=locale)["content"] == values


def test_edition_change_invalidates_all_mechanical_answers():
    kind, values = examples()[0]
    guide = h.interview(kind)
    state, _, invalidated = guide.change(compile_state(kind, values), {"questionId": "class.edition", "questionVersion": 1},
        answer=guide.by_id["class.edition"].answer("dnd5e_2014"), author=1, locale="en")
    assert set(invalidated) == {"class.hitDie", "class.levels"}
    assert h.quality_gates(kind, state, "runtime_ready")


def test_bad_progression_choices_duplicates_and_spell_semantics_block_commit():
    kind, clazz = examples()[0]
    clazz["class"]["levels"][1]["level"] = 3
    assert "CLASS_LEVEL_SEQUENCE_INVALID" in h.semantic_errors(kind, clazz)
    kind, race = examples()[1]
    race["race"]["features"] *= 2
    assert "FEATURE_ID_DUPLICATE" in h.semantic_errors(kind, race)
    kind, spell = examples()[2]
    spell["spell"]["durationRounds"] = 3
    spell["spell"]["cost"]["resource"] = None
    assert set(h.semantic_errors(kind, spell)) >= {"SPELL_DURATION_INVALID", "SPELL_COST_INVALID", "SPELL_SCALING_INVALID"}


@pytest.mark.parametrize("value", [True, 1.0, -1, 21])
def test_build_rejects_coercions_and_out_of_range_levels(value):
    command = {"contractVersion": r.CONTRACT, "idempotencyKey": "key:test", "operation": "BuildCharacter",
               "sandboxId": "sandbox:test", "expectedVersion": 1, "payload": build(level=value)}
    with pytest.raises(ContractViolation, match="SCHEMA_INVALID"):
        r.validate_command(command)


def test_choices_are_required_and_not_silently_selected():
    for choices in ({}, {"race/echo/training": ["missing"]}, {"race/echo/training": ["mind", "mind"]}):
        with pytest.raises(ContractViolation, match="CHOICE_REQUIRED"):
            r.build_character(build(choices=choices), documents())
    with pytest.raises(ContractViolation, match="CHOICE_INVALID"):
        r.build_character(build(choices={"race/echo/training": ["mind"], "class/extra/pick": ["x"]}), documents())


def test_progression_rebuild_keeps_spent_resources_and_duplicate_grant_sources():
    docs = documents()
    initial = r.build_character(build(), docs)
    assert initial["stats"]["int"] == 16 and initial["stats"]["dex"] == 13
    assert initial["stats"]["hpMax"] == 18 and len(initial["proficiencies"]["arcana"]) == 3
    initial["resources"]["mana"]["current"] = 4
    initial["hp"] = 7
    next_level = r.build_character(build(level=2), docs, previous=initial)
    assert next_level["stats"]["hpMax"] == 23 and next_level["hp"] == 7
    assert next_level["resources"]["mana"]["maximum"] == 15 and next_level["resources"]["mana"]["current"] == 4
    other_choice = r.build_character(build(choices={"race/echo/training": ["body"]}), docs, previous=next_level)
    assert len(other_choice["proficiencies"]["arcana"]) == 2 and other_choice["stats"]["int"] == 14
    assert other_choice["stats"]["con"] == 14 and other_choice["stats"]["hpMax"] == 18
    with pytest.raises(ContractViolation, match="CLASS_LEVEL_UNSUPPORTED"):
        r.build_character(build(level=3), docs)


def world():
    docs = documents()
    state = {"round": 0, "characters": {key: r.build_character(build(name=key), docs) for key in ("caster", "target")},
             "effects": [], "pendingConcentration": None}
    return state, docs


def cast(state, docs, **values):
    payload = {"casterId": "caster", "targetId": "target", "spellKey": "ember", "castLevel": 1, "distanceFeet": 20,
               "adjudication": {"timingSatisfied": True, "componentsSatisfied": True}, **values}
    return r.execute(state, docs, "CastSpell", payload, new_id=new_id, roll=lambda sides: 4)


def test_damage_healing_upcast_resources_and_range_are_real():
    state, docs = world()
    result = cast(state, docs, castLevel=2)
    assert result["amount"] == 13 and result["hpDelta"] == -13
    assert state["characters"]["target"]["hp"] == 5
    assert state["characters"]["caster"]["resources"]["mana"]["current"] == 7
    assert cast(state, docs, spellKey="mend")["hpDelta"] == 6
    assert cast(state, docs, spellKey="mend")["hpDelta"] == 6
    assert cast(state, docs, spellKey="mend")["hpDelta"] == 1
    for values, code in [({"distanceFeet": 61}, "SPELL_TARGET_INVALID"), ({"castLevel": 0}, "SPELL_LEVEL_INVALID"),
                         ({"spellKey": "unknown"}, "SPELL_NOT_KNOWN"), ({}, "RESOURCE_BOUND_EXCEEDED")]:
        before = deepcopy(state)
        with pytest.raises(ContractViolation, match=code):
            cast(state, docs, **values)
        assert state == before


def test_temporary_effect_replacement_expiry_and_concentration_gate():
    state, docs = world()
    cast(state, docs, spellKey="ward", targetId="caster", distanceFeet=0)
    assert r.current_stat(state, "caster", "ac") == 15
    cast(state, docs, spellKey="ward", targetId="caster", distanceFeet=0)
    assert len(state["effects"]) == 1 and r.current_stat(state, "caster", "ac") == 15
    result = cast(state, docs, casterId="target", targetId="caster")
    assert result["concentrationCheckRequired"] == {"characterId": "caster", "dc": 10}
    with pytest.raises(ContractViolation, match="SCOPE_BUSY"):
        cast(state, docs)
    r.execute(state, docs, "ResolveConcentration", {"characterId": "caster", "maintained": False, "reason": "Failed check"}, new_id=new_id, roll=None)
    assert not state["effects"]
    cast(state, docs, spellKey="ward", targetId="caster", distanceFeet=0)
    r.execute(state, docs, "AdvanceRounds", {"rounds": 2}, new_id=new_id, roll=None)
    assert not state["effects"] and r.current_stat(state, "caster", "ac") == 12


@pytest.mark.parametrize("die,hit,critical", [(1, False, False), (20, True, True), (4, False, False)])
def test_attack_rolls_misses_and_criticals(die, hit, critical):
    state, docs = world()
    docs["spell:ember"]["content"]["spell"]["resolution"] = {"kind": "attack", "ability": "int"}
    result = r.cast(state, docs, {"casterId": "caster", "targetId": "target", "spellKey": "ember", "castLevel": 1, "distanceFeet": 20},
                    new_id=new_id, roll=lambda sides: die if sides == 20 else 4)
    assert result["hit"] == hit and result["critical"] == critical
    assert state["characters"]["caster"]["resources"]["mana"]["current"] == 8
    assert result["hpDelta"] == (-17 if critical else 0)


def test_saves_and_resistance_reduce_damage_and_recovery_is_declared():
    state, docs = world()
    s = docs["spell:ember"]["content"]["spell"]
    s["resolution"] = {"kind": "save", "ability": "int", "saveAbility": "con", "halfOnSave": True}
    s["effect"]["damageType"] = "cold"
    result = r.cast(state, docs, {"casterId": "caster", "targetId": "target", "spellKey": "ember", "castLevel": 1, "distanceFeet": 20},
                    new_id=new_id, roll=lambda sides: 20 if sides == 20 else 4)
    assert result["saved"] and result["hpDelta"] == -2
    r.execute(state, docs, "RecoverResources", {"characterId": "caster", "event": "short_rest", "reason": "Rest"}, new_id=new_id, roll=None)
    assert state["characters"]["caster"]["resources"]["mana"]["current"] == 8
    r.execute(state, docs, "RecoverResources", {"characterId": "caster", "event": "long_rest", "reason": "Rest"}, new_id=new_id, roll=None)
    assert state["characters"]["caster"]["resources"]["mana"]["current"] == 10


def test_multiple_casters_of_one_spell_do_not_stack_and_remaining_duration_survives():
    state, docs = world()
    docs["spell:ward"]["content"]["spell"].update(target="single", rangeFeet=60)
    cast(state, docs, spellKey="ward", targetId="target")
    cast(state, docs, spellKey="ward", casterId="target", targetId="target", distanceFeet=0)
    assert len(state["effects"]) == 2 and r.current_stat(state, "target", "ac") == 15
    r.end_concentration(state, "caster")
    assert len(state["effects"]) == 1 and r.current_stat(state, "target", "ac") == 15


def test_unsupported_effect_code_and_unattested_cast_are_rejected_at_boundary():
    kind, spell = examples()[2]
    spell["spell"]["effect"] = {"kind": "python", "code": "arbitrary()"}
    with pytest.raises(ContractViolation, match="SCHEMA_INVALID"):
        compile_state(kind, spell)
    cmd = {"contractVersion": r.CONTRACT, "idempotencyKey": "key:test", "operation": "CastSpell",
           "sandboxId": "sandbox:test", "expectedVersion": 1, "payload": {"casterId": "a", "targetId": "b",
           "spellKey": "ember", "castLevel": 1, "distanceFeet": 1,
           "adjudication": {"timingSatisfied": False, "componentsSatisfied": True}}}
    with pytest.raises(ContractViolation, match="SCHEMA_INVALID"):
        r.validate_command(cmd)


def test_conflicting_resource_recovery_and_unpinned_spells_block_build():
    docs = documents()
    docs["race:fixture"]["content"]["race"]["features"][0]["grants"]["resources"] = [
        {"id": "mana", "maximum": 5, "recovery": "short_rest"}]
    with pytest.raises(ContractViolation, match="RESOURCE_RECOVERY_CONFLICT"):
        r.build_character(build(), docs)
    docs = documents()
    del docs["spell:ember"]
    with pytest.raises(ContractViolation, match="SPELL_NOT_IN_LOCK"):
        r.build_character(build(), docs)
