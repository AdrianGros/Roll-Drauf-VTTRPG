"""WP1: strict JSON input, RFC 8785 canonical bytes and content digests (spec v1.1.4 §6)."""

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vtt.creation_engine.canonical import MAX_SAFE_INTEGER, canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.errors import SCHEMA_INVALID, ContractViolation


def _rejected(raw):
    with pytest.raises(ContractViolation) as caught:
        parse_strict_json(raw)
    assert caught.value.code == SCHEMA_INVALID
    return caught.value


def test_canonical_bytes_sort_keys_by_utf16_code_units_without_whitespace():
    # U+1F600 is encoded as the surrogate pair D83D DE00, which sorts before U+FF21 in UTF-16
    # although its code point is larger: RFC 8785 orders by UTF-16 code units.
    assert canonical_bytes({"Ａ": 1, "\U0001F600": 2, "a": [4.5, 1e30, None, True]}) == \
        '{"a":[4.5,1e+30,null,true],"\U0001F600":2,"Ａ":1}'.encode("utf-8")


def test_digest_identifies_exact_canonical_bytes():
    assert content_digest({"b": 1, "a": 2}) == content_digest({"a": 2, "b": 1})
    assert content_digest({"a": 2}).startswith("sha256:") and len(content_digest({"a": 2})) == 71


def test_strings_are_never_unicode_normalized():
    assert content_digest({"name": "é"}) != content_digest({"name": "é"})


@pytest.mark.parametrize("raw", [
    '{"a": 1, "a": 2}',                     # duplicate key
    '{"outer": {"k": true, "k": false}}',   # nested duplicate key
    '{"n": NaN}', '{"n": Infinity}', '{"n": -Infinity}',
    '{"n": 1e400}',                         # overflows to infinity
    '{"n": 9007199254740992}',              # just beyond the safe integer range
    '{"s": "\\ud800"}',                     # lone surrogate value
    '{"\\udc00": 1}',                       # lone surrogate key
    '{"a": 1',                              # malformed
    '{"n": ' + "9" * 5000 + '}',           # beyond Python's int conversion limit
])
def test_strict_parser_rejects_what_section_6_forbids(raw):
    _rejected(raw)


def test_strict_parser_rejects_invalid_utf8_bytes():
    _rejected(b'{"a": "\xff"}')


def test_strict_parser_accepts_the_safe_integer_boundaries():
    assert parse_strict_json(f'[{MAX_SAFE_INTEGER}, {-MAX_SAFE_INTEGER}]') == [MAX_SAFE_INTEGER, -MAX_SAFE_INTEGER]


@pytest.mark.parametrize("value", [(1, 2), {1, 2}, b"raw", object(), {1: "non-string key"},
                                   float("nan"), MAX_SAFE_INTEGER + 1, "\ud800"])
def test_canonical_bytes_reject_non_json_values(value):
    with pytest.raises(ContractViolation):
        canonical_bytes(value)


json_values = st.recursive(
    st.none() | st.booleans() | st.integers(-MAX_SAFE_INTEGER, MAX_SAFE_INTEGER)
    | st.text(alphabet=st.characters(exclude_categories=["Cs"]), max_size=12),
    lambda children: st.lists(children, max_size=4)
    | st.dictionaries(st.text(alphabet=st.characters(exclude_categories=["Cs"]), max_size=8), children, max_size=4),
    max_leaves=20)


def _shuffled(value, rng):
    if isinstance(value, dict):
        items = list(value.items())
        rng.shuffle(items)
        return {key: _shuffled(item, rng) for key, item in items}
    if isinstance(value, list):
        return [_shuffled(item, rng) for item in value]
    return value


@settings(max_examples=200, deadline=None)
@given(json_values, st.randoms(use_true_random=False))
def test_digest_is_independent_of_key_insertion_order(value, rng):
    assert content_digest(_shuffled(value, rng)) == content_digest(value)


@settings(max_examples=200, deadline=None)
@given(json_values)
def test_canonical_bytes_parse_back_to_the_same_value(value):
    assert parse_strict_json(canonical_bytes(value)) == value


def test_shuffle_helper_really_reorders():
    rng = random.Random(3)
    original = {str(i): i for i in range(8)}
    assert list(_shuffled(original, rng)) != list(original)
