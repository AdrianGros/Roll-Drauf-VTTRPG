"""D&D homebrew races retain explicit sheet rules without claiming automation."""

from copy import deepcopy

import pytest

from vtt.creation_engine.canonical import canonical_bytes, content_digest
from vtt.creation_engine.compiler import catalog, flame, manual, race
from vtt.creation_engine.compiler.interview import LOCALES, MODES, StrictValidator
from vtt.creation_engine.errors import ContractViolation


TRAITS = [
    {"name": "Stone memory", "kind": "trait", "description": "Recall a place touched by bare hands.",
     "usage": "Passive; no limit."},
    {"name": "Echo step", "kind": "feature", "description": "Move through a familiar echo.",
     "usage": "Once after a long rest; resolved by the player.",
     "choices": "Choose one visible destination.", "prerequisites": "Character level 3."},
]
ANSWERS = {
    "content.name": "Echo folk",
    "race.edition": "dnd5e_2024",
    "race.creatureType": "Humanoid",
    "race.size": "small_or_medium",
    "race.speed": 30,
    "race.languages": "No species-granted languages.",
    "race.traits": TRAITS,
    "race.abilityScoreRules": "No race-granted ability score changes.",
    "content.prose": "People who remember the mountain's song.",
}


def answer(guide, state, key, value, *, locale="en", mode="structured"):
    question = guide.by_id[key]
    decision = guide.advanced_answer(question.path, value) if mode == "advanced" else {
        "question": {"questionId": key, "questionVersion": question.version}, "answer": question.answer(value)}
    return guide.change(state, decision["question"], answer=decision["answer"], author=7, locale=locale)


def fill(answers=None, *, locale="en", mode="structured"):
    guide = catalog.guide_for(race.RACE_TYPE)
    state = guide.empty()
    for key, value in (ANSWERS if answers is None else answers).items():
        state, _, _ = answer(guide, state, key, value, locale=locale, mode=mode)
    return guide, state


@pytest.mark.parametrize("schema_type,digest", [
    (flame.ITEM_TYPE, "sha256:8030551e4be578f08eba12fb3f03855530b957bb6a8241d3f33c2e5223d51e2a"),
    (manual.CONDITIONAL, "sha256:e6c1f17c418f2b21f206015d16c87279ceb42bbd6c01a81c87fd2c3a0918259e"),
    (manual.CHOICE, "sha256:b80f6b87745024b363e972c330b5a1d75ce9e539e455f6b0dd5c9bdfd0c4065e"),
    (manual.LORE, "sha256:52311a2f40ad8a536f7888fbee8bd2385c47ce7285b1865676318a72cb5e6fd3"),
])
def test_existing_profile_registry_bytes_are_unchanged(schema_type, digest):
    assert content_digest(catalog.registry(schema_type).artifact()) == digest


def test_race_draft_starts_empty_with_no_inferred_mechanics_or_edition():
    guide = race.interview()
    state = guide.empty()
    assert guide.values(state) == {}
    assert guide.present(state)["nextQuestionId"] == "content.name"
    assert all(question["answer"] is None for question in guide.present(state)["questions"])
    assert b'"default"' not in canonical_bytes(catalog.registry(race.RACE_TYPE).artifact())
    state, _, _ = answer(guide, state, "content.prose", "Faster than lightning, born of dragons.")
    assert guide.values(state) == {"prose": "Faster than lightning, born of dragons."}
    assert {gate["questionId"] for gate in catalog.quality_gates(state, "sheet_ready")} == {
        "content.name", "race.edition", "race.creatureType", "race.size", "race.speed", "race.languages", "race.traits"}


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("mode", MODES)
def test_all_modes_and_locales_preserve_named_traits_and_edition(locale, mode):
    guide, state = fill(locale=locale, mode=mode)
    values = guide.values(state)
    assert values["race"]["traits"] == TRAITS
    assert values["race"]["edition"] == "dnd5e_2024"
    assert StrictValidator(race.content_schema()).is_valid(values)
    assert catalog.quality_gates(state, "sheet_ready") == []
    before = canonical_bytes(state)
    for switched in MODES:
        assert guide.present(state, locale=locale, mode=switched)["content"] == values
    assert canonical_bytes(state) == before
    assert {entry["promptLocale"] for entry in state["answers"].values()} == {locale}


@pytest.mark.parametrize("edition", race.EDITIONS)
def test_each_explicit_edition_is_sheet_ready_but_never_runtime_ready(edition):
    _, state = fill({**ANSWERS, "race.edition": edition})
    assert catalog.quality_gates(state, "sheet_ready") == []
    for quality in ("runtime_ready", "automation_complete"):
        assert catalog.quality_gates(state, quality) == [{"path": [], "code": "MANUAL_PROFILE_ONLY"}]


def test_switching_edition_invalidates_rules_but_retains_author_history_and_identity():
    guide, state = fill()
    before = canonical_bytes(state)
    changed, _, invalidated = answer(guide, state, "race.edition", "dnd5e_2014")
    assert set(invalidated) == {key for key in ANSWERS if key.startswith("race.") and key != "race.edition"}
    assert guide.values(changed) == {"name": ANSWERS["content.name"], "prose": ANSWERS["content.prose"],
                                    "race": {"edition": "dnd5e_2014"}}
    assert changed["stale"]["race.traits"]["answer"]["value"] == TRAITS
    assert catalog.quality_gates(changed, "sheet_ready")
    assert canonical_bytes(state) == before


def test_trait_row_edit_or_removal_does_not_erase_other_race_fields():
    guide, state = fill()
    remaining = [{**TRAITS[0], "description": "Recall a place touched in the last year."}]
    changed, _, invalidated = answer(guide, state, "race.traits", remaining)
    assert invalidated == []
    assert guide.values(changed)["race"] == {**guide.values(state)["race"], "traits": remaining}
    assert guide.values(state)["race"]["traits"] == TRAITS
    assert catalog.quality_gates(changed, "sheet_ready") == []


def test_duplicate_trait_names_block_sheet_claim_without_changing_author_text():
    traits = [TRAITS[0], {**TRAITS[1], "name": "  STONE MEMORY  "}]
    guide, state = fill({**ANSWERS, "race.traits": traits})
    assert catalog.quality_gates(state, "sheet_ready") == [{
        "path": ["race", "traits", "1", "name"], "code": "TRAIT_NAME_DUPLICATE", "questionId": "race.traits"}]
    assert guide.values(state)["race"]["traits"] == traits


def test_optional_prose_and_ability_rules_are_not_needed_for_sheet_quality():
    guide, state = fill({key: value for key, value in ANSWERS.items()
                         if key not in {"content.prose", "race.abilityScoreRules"}})
    for key in ("content.prose", "race.abilityScoreRules"):
        state, _, _ = guide.change(state, {"questionId": key, "questionVersion": 1}, author=7, locale="en", skip=True)
    assert catalog.quality_gates(state, "sheet_ready") == []
    assert "abilityScoreRules" not in guide.values(state)["race"]


@pytest.mark.parametrize("key,value", [
    ("content.name", "x" * 51), ("content.name", "  "),
    ("race.edition", "dnd5e"), ("race.edition", "roll_drauf_light"),
    ("race.creatureType", ""), ("race.languages", "\n"),
    ("race.size", "automatic"), ("race.speed", True), ("race.speed", 30.0),
    ("race.speed", "30"), ("race.speed", -1), ("race.speed", 301),
    ("race.traits", []), ("race.traits", TRAITS * 11),
    ("race.traits", [{**TRAITS[0], "usage": ""}]),
    ("race.traits", [{**TRAITS[0], "kind": "script"}]),
    ("race.traits", [{key: value for key, value in TRAITS[0].items() if key != "description"}]),
    ("race.traits", [{**TRAITS[0], "script": "change_hp()"}]),
])
def test_invalid_or_unbounded_answers_are_rejected_without_coercion(key, value):
    with pytest.raises(ContractViolation, match="SCHEMA_INVALID"):
        race.interview().by_id[key].answer(value)


def test_content_schema_and_advanced_editor_reject_unregistered_mechanical_paths():
    guide, state = fill()
    content = deepcopy(guide.values(state))
    content["race"]["abilityBonuses"] = {"str": 2}
    assert not StrictValidator(race.content_schema()).is_valid(content)
    with pytest.raises(ContractViolation, match="SCHEMA_INVALID"):
        guide.advanced_answer(["race", "abilityBonuses"], {"str": 2})
    with pytest.raises(ContractViolation, match="SCHEMA_INVALID"):
        catalog.quality_gates(state, "published")


def test_partial_race_can_be_saved_as_lore_without_claiming_sheet_completeness():
    _, state = fill({"content.name": "Unfinished folk"})
    assert catalog.quality_gates(state, "lore_only") == []
    assert catalog.quality_gates(state, "sheet_ready")
