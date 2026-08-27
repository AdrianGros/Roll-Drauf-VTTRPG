"""S05: the canonical condition catalog and its validator.

vtt/play/conditions.py is the whole "claude_safe_subscope" for this slice
per docs/PLAYTABLE_FEATURE_WORK_PACKAGE_2026-08-27.md -- a genuinely
isolated data/validation module, tested directly rather than only through
the socket-handler integration it's wired into.
"""

from vtt.play.conditions import CONDITION_CATALOG, CONDITION_IDS, validate_condition_ids


def test_catalog_has_the_fifteen_core_5e_conditions():
    assert len(CONDITION_CATALOG) == 16  # includes "concentrating", a common house-rule addition beyond the core 15
    assert len(CONDITION_IDS) == len(CONDITION_CATALOG)  # no duplicate ids
    for entry in CONDITION_CATALOG:
        assert entry["id"] and entry["label"]


def test_validate_condition_ids_accepts_known_ids():
    validated, error = validate_condition_ids(["blinded", "poisoned"])
    assert error is None
    assert validated == ["blinded", "poisoned"]


def test_validate_condition_ids_rejects_unknown_id_instead_of_silently_dropping_it():
    """Before S05, token.metadata_json.conditions accepted any free-form
    string with zero validation. A typo or stale client value must now
    surface as a hard rejection, not vanish silently."""
    validated, error = validate_condition_ids(["blinded", "confuzed"])
    assert validated is None
    assert error is not None
    assert "confuzed" in error["message"]


def test_validate_condition_ids_deduplicates_preserving_first_seen_order():
    validated, _ = validate_condition_ids(["poisoned", "blinded", "poisoned"])
    assert validated == ["poisoned", "blinded"]


def test_validate_condition_ids_normalizes_case_and_whitespace():
    validated, error = validate_condition_ids([" Blinded ", "POISONED"])
    assert error is None
    assert validated == ["blinded", "poisoned"]


def test_validate_condition_ids_treats_none_as_empty_list():
    validated, error = validate_condition_ids(None)
    assert error is None
    assert validated == []


def test_validate_condition_ids_rejects_non_list():
    validated, error = validate_condition_ids("blinded")
    assert validated is None
    assert error is not None
