"""Manual task profiles: explicit decisions, safe quality and frozen legacy pins."""

import pytest

from vtt.creation_engine.canonical import content_digest
from vtt.creation_engine.compiler import catalog, manual
from vtt.creation_engine.compiler.interview import StrictValidator
from vtt.creation_engine.errors import ContractViolation


ANSWERS = {
    manual.CONDITIONAL: {"content.name": "Shelter", "condition.affected": "Wearer's defence",
        "condition.when": "While standing behind the shield", "condition.change": "Add 2 defence points",
        "condition.until": "Remove the 2-point bonus on leaving cover"},
    manual.CHOICE: {"content.name": "Crossroads", "choice.prompt": "The traveller chooses on reaching the crossing",
        "choice.count": 2, "choice.option1.label": "Forest", "choice.option1.consequence": "Spend an extra day travelling",
        "choice.option2.label": "Bridge", "choice.option2.consequence": "Pay the stated toll manually", "choice.selection": 1},
    manual.LORE: {"content.name": "The old harbour", "content.prose": "The bells ring beneath the water. No damage is implied."},
}


def fill(kind, answers=None):
    guide = catalog.guide_for(kind)
    state = guide.empty()
    for key, value in (ANSWERS[kind] if answers is None else answers).items():
        q = guide.by_id[key]
        state, _, _ = guide.change(state, {"questionId": key, "questionVersion": q.version},
            answer=q.answer(value), author=1, locale="en")
    return guide, state


def test_original_flame_registry_bytes_remain_pinned():
    assert content_digest(catalog.registry().artifact()) == "sha256:8030551e4be578f08eba12fb3f03855530b957bb6a8241d3f33c2e5223d51e2a"


@pytest.mark.parametrize("kind", manual.TYPES)
def test_manual_profiles_require_author_decisions_and_never_claim_runtime(kind):
    guide = catalog.guide_for(kind)
    assert guide.values(guide.empty()) == {}
    assert catalog.quality_gates(guide.empty(), "lore_only")
    for locale in ("de", "en", "fr"):
        for mode in ("guided", "structured", "advanced"):
            view = guide.present(guide.empty(), locale=locale, mode=mode)
            assert view["nextQuestionId"] == "content.name"
            assert all(q["answer"] is None and q["label"] and q["help"] for q in view["questions"])
    guide, state = fill(kind)
    assert StrictValidator(manual.content_schema(kind)).is_valid(guide.values(state))
    assert not catalog.quality_gates(state, "lore_only" if kind == manual.LORE else "sheet_ready")
    for quality in ("runtime_ready", "automation_complete"):
        assert "MANUAL_PROFILE_ONLY" in {g["code"] for g in catalog.quality_gates(state, quality)}
    if kind == manual.LORE:
        assert {g["code"] for g in catalog.quality_gates(state, "sheet_ready")} == {"DESCRIPTIVE_ONLY"}


def test_choice_count_changes_invalidate_alternatives_consequences_and_cardinality():
    guide, state = fill(manual.CHOICE)
    q = guide.by_id["choice.count"]
    changed, _, invalidated = guide.change(state, {"questionId": q.id, "questionVersion": 1},
        answer=q.answer(3), author=1, locale="fr")
    assert set(invalidated) == {"choice.selection", "choice.option1.label", "choice.option1.consequence",
                               "choice.option2.label", "choice.option2.consequence"}
    assert guide.values(changed)["choice"] == {"prompt": ANSWERS[manual.CHOICE]["choice.prompt"], "count": 3}
    assert changed["stale"]["choice.option1.consequence"]["answer"]["value"] == "Spend an extra day travelling"
    assert guide.by_id["choice.option4.label"].id not in guide.present(changed)["unresolved"]
    assert catalog.quality_gates(changed, "sheet_ready")


def test_changed_condition_requires_review_of_change_and_removal():
    guide, state = fill(manual.CONDITIONAL)
    q = guide.by_id["condition.when"]
    changed, _, invalidated = guide.change(state, {"questionId": q.id, "questionVersion": 1},
        answer=q.answer("While asleep"), author=1, locale="en")
    assert set(invalidated) == {"condition.change", "condition.until"}
    assert "change" not in guide.values(changed)["condition"]
    assert catalog.quality_gates(changed, "sheet_ready")


def test_choice_labels_and_selection_counts_are_validated_without_correction():
    answers = {**ANSWERS[manual.CHOICE], "choice.option2.label": " forest ", "choice.selection": 3}
    guide, state = fill(manual.CHOICE, answers)
    assert {g["code"] for g in catalog.quality_gates(state, "sheet_ready")} == {"CHOICE_COUNT_EXCEEDED", "CHOICE_LABEL_DUPLICATE"}
    assert guide.values(state)["choice"]["selection"] == 3
    assert guide.values(state)["choice"]["alternatives"]["2"]["label"] == " forest "


@pytest.mark.parametrize("value", [True, 2.0, 1, 7, "2"])
def test_choice_count_requires_an_exact_supported_integer(value):
    with pytest.raises(ContractViolation):
        manual.interview(manual.CHOICE).by_id["choice.count"].answer(value)


def test_lore_requires_actual_prose_and_does_not_offer_mechanical_questions():
    guide, state = fill(manual.LORE, {"content.name": "A place"})
    assert set(guide.by_id) == {"content.name", "content.prose"}
    assert catalog.quality_gates(state, "lore_only") == [{"path": ["prose"], "code": "ANSWER_REQUIRED", "questionId": "content.prose"}]
    with pytest.raises(ContractViolation):
        guide.by_id["content.prose"].answer("  \n ")


def test_manual_schema_rejects_executable_or_unregistered_fields():
    guide, state = fill(manual.CONDITIONAL)
    values = guide.values(state)
    assert not StrictValidator(manual.content_schema(manual.CONDITIONAL)).is_valid({**values, "script": "change_hp()"})
    with pytest.raises(ContractViolation, match="SCHEMA_INVALID"):
        guide.advanced_answer(["condition", "executable"], True)
