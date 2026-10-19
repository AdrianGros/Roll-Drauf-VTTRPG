"""T31/T32: no invented mechanics, stale decisions and mode/locale equivalence."""

from dataclasses import replace

import pytest

from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.compiler.flame import (COMPILER_VERSION, apply_preset, content_schema, interview, preset, quality_gates)
from vtt.creation_engine.compiler.interview import Interview, LOCALES, MODES, StrictValidator
from vtt.creation_engine.contracts import contract_registry
from vtt.creation_engine.kernel.records import KernelError


def answer(guide, state, key, value, *, locale="de"):
    q = guide.by_id[key]
    return guide.change(state, {"questionId": key, "questionVersion": q.version},
                        answer=q.answer(value), author=1, locale=locale)


def filled(kind="g1.harmless-flames", locale="de"):
    preview = preset(kind, locale=locale)
    return apply_preset(interview().empty(), {"presetId": kind, "version": 1}, preview["previewDigest"],
                        author=1, locale=locale)[0]


def test_t31_first_mechanical_question_does_not_infer_damage_or_day():
    guide = interview()
    state, _, _ = answer(guide, guide.empty(), "item.prose", "a sword that bursts into flames three times per day")
    view = guide.present(state)
    assert view["nextQuestionId"] == "flame.behavior"
    assert view["content"] == {"prose": "a sword that bursts into flames three times per day"}
    assert not next(q for q in view["questions"] if q["questionId"] == "flame.damage")["visible"]


def test_t31_harmless_preset_has_no_damage_primitive():
    guide, state = interview(), filled()
    content = guide.values(state)
    assert content["flames"]["behavior"] == "visual"
    assert "damage" not in content["flames"] and "damageType" not in content["flames"]
    assert not quality_gates(state, "runtime_ready")
    assert all(a["source"] == "preset:g1.harmless-flames" for a in state["answers"].values())
    assert StrictValidator(content_schema(), registry=contract_registry()).is_valid(content)


def test_t31_changing_behavior_removes_dependent_effects_and_marks_answers_stale():
    guide, state = interview(), filled("g1.post-hit-flames")
    old = canonical_bytes(state)
    updated, mutations, invalidated = answer(guide, state, "flame.behavior", "visual")
    assert canonical_bytes(state) == old
    assert set(guide.values(updated)) == {"name", "flames"}
    assert guide.values(updated)["flames"] == {"behavior": "visual"}
    assert "flame.damage" in invalidated and "flame.cost" in invalidated
    assert updated["stale"]["flame.damage"]["answer"]["value"] == {"count": 2, "sides": 6}
    assert any(m["path"] == ["flames", "damage"] and m["after"] == {"present": False} for m in mutations)
    assert quality_gates(updated, "runtime_ready")


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("mode", MODES)
def test_t32_modes_and_locales_preserve_identity_and_canonical_meaning(locale, mode):
    guide = interview()
    state = guide.empty()
    decisions = preset("g1.harmless-flames")["decisions"]
    for d in decisions:
        q = guide.question(d["question"])
        if mode == "advanced":
            d = guide.advanced_answer(q.path, d["answer"]["value"])
        state, _, _ = guide.change(state, d["question"], answer=d["answer"], author=1, locale=locale)
    before = canonical_bytes(state)
    for switched in MODES:
        view = guide.present(state, locale=locale, mode=switched)
        assert view["nextQuestionId"] == "item.prose"  # optional answers are asked, never silently skipped
        assert canonical_bytes(view["content"]) == canonical_bytes(guide.values(filled()))
        assert canonical_bytes(state) == before
    assert {a["promptLocale"] for a in state["answers"].values()} == {locale}


def test_t32_unreviewed_compiler_upgrade_cannot_reapply_answers():
    state = filled()
    state["compilerVersion"] = "unreviewed:2"
    with pytest.raises(KernelError) as error:
        interview().present(state)
    assert error.value.code == "AUTHORING_REGISTRY_MISMATCH"


def test_reanswer_same_value_keeps_valid_descendants():
    guide, state = interview(), filled()
    result, mutations, invalidated = answer(guide, state, "flame.behavior", "visual", locale="fr")
    assert guide.values(result) == guide.values(state)
    assert mutations == invalidated == []
    assert result["answers"]["flame.behavior"]["promptLocale"] == "fr"


def test_optional_skip_and_required_question_rejection():
    guide, state = interview(), interview().empty()
    state, _, _ = guide.change(state, {"questionId": "item.prose", "questionVersion": 1}, author=1, locale="de", skip=True)
    assert state["skipped"] == ["item.prose"]
    with pytest.raises(KernelError) as error:
        guide.change(state, {"questionId": "flame.behavior", "questionVersion": 1}, author=1, locale="de", skip=True)
    assert error.value.code == "QUESTION_REQUIRED"


def test_early_dependent_answer_is_not_silently_retained():
    with pytest.raises(KernelError) as error:
        answer(interview(), interview().empty(), "flame.damage", {"count": 2, "sides": 6})
    assert error.value.code == "QUESTION_NOT_READY"


@pytest.mark.parametrize("value", [True, 3.0, "3", -1, 1001, None])
def test_no_integer_coercion_or_defaults(value):
    guide = interview()
    state, _, _ = answer(guide, guide.empty(), "flame.behavior", "visual")
    with pytest.raises(KernelError) as error:
        answer(guide, state, "flame.maximum", value)
    assert error.value.code == "SCHEMA_INVALID"


def test_nested_dice_integer_is_exact_and_extra_paths_are_forbidden():
    guide = interview()
    with pytest.raises(KernelError):
        guide.advanced_answer(("flames", "damage"), {"count": 2.0, "sides": 6})
    with pytest.raises(KernelError):
        guide.advanced_answer(("flames", "damage"), {"count": 2, "sides": 6, "script": "run()"})
    with pytest.raises(KernelError):
        guide.advanced_answer(("flames", "script"), "run()")


def test_preset_preview_and_question_version_are_bound():
    guide = interview()
    with pytest.raises(KernelError) as error:
        apply_preset(guide.empty(), {"presetId": "g1.harmless-flames", "version": 1}, "sha256:" + "0" * 64,
                     author=1, locale="de")
    assert error.value.code == "PRESET_PREVIEW_STALE"
    with pytest.raises(KernelError) as error:
        guide.question({"questionId": "flame.behavior", "questionVersion": 2})
    assert error.value.code == "AUTHORING_REGISTRY_MISMATCH"


def test_quality_claims_preserve_unresolved_values_and_manual_semantics():
    guide = interview()
    state, _, _ = answer(guide, guide.empty(), "item.name", "Manual concept")
    assert not quality_gates(state, "lore_only")
    assert quality_gates(state, "runtime_ready")
    state, _, _ = answer(guide, state, "flame.behavior", "transformation")
    assert not quality_gates(state, "sheet_ready")
    assert any(g["code"] == "MANUAL_BEHAVIOR" for g in quality_gates(state, "runtime_ready"))
    assert quality_gates(filled(), "automation_complete")


def test_cycle_duplicate_ownership_and_missing_translation_are_registration_failures():
    questions = interview().questions
    a = replace(questions[0], dependencies=(questions[1].id,))
    b = replace(questions[1], dependencies=(questions[0].id,))
    with pytest.raises(KernelError) as error:
        Interview((a, b), compiler_version=COMPILER_VERSION).present(interview().empty())
    assert error.value.code == "GUIDE_DEAD_END"
    recovered = Interview((a, b), compiler_version=COMPILER_VERSION).present(interview().empty(), mode="structured")
    assert recovered["guideError"] == "GUIDE_DEAD_END" and recovered["content"] == {}
    with pytest.raises(ValueError, match="owning question"):
        Interview((questions[0], replace(questions[1], path=questions[0].path)), compiler_version=COMPILER_VERSION)
    with pytest.raises(ValueError, match="de, en and fr"):
        Interview((replace(questions[0], text={"de": questions[0].text["de"]}),), compiler_version=COMPILER_VERSION)


def test_retract_maximum_invalidates_cost_initial_and_recovery_but_retains_behavior():
    guide, state = interview(), filled()
    state, _, invalidated = guide.change(state, {"questionId": "flame.maximum", "questionVersion": 1},
                                        author=1, locale="en", retract=True)
    assert set(invalidated) == {"flame.initial", "flame.cost", "flame.recovery"}
    assert "maximumCharges" not in guide.values(state)["flames"]
    assert guide.values(state)["flames"]["behavior"] == "visual"
