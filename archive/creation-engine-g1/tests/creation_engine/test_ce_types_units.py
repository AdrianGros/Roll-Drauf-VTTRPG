"""WP1: IDs, tagged references, UTC timestamps and units (spec v1.1.4 §4, §6, §10)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from vtt.creation_engine.errors import SCHEMA_INVALID, SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.rational import Rational
from vtt.creation_engine.types import (DefinitionRef, InstanceRef, RevisionRef, WorldRef, format_utc_timestamp,
                                       parse_context_token, parse_digest, parse_id, parse_reference,
                                       parse_utc_timestamp)
from vtt.creation_engine.units import Quantity, Unit, UnitTable

R = Rational.of
DIGEST = "sha256:" + "ab" * 32


def _code(fn, *args, **kwargs):
    with pytest.raises(ContractViolation) as caught:
        fn(*args, **kwargs)
    return caught.value.code


@pytest.mark.parametrize("value", ["a", "item:flame-sword.v2_1", "x" * 128])
def test_valid_ids(value):
    assert parse_id(value) == value


@pytest.mark.parametrize("value", ["", "x" * 129, "has space", "slash/no", "ümlaut", "٣", 7, None])
def test_invalid_ids(value):
    assert _code(parse_id, value) == SCHEMA_INVALID


def test_digest_and_context_token_shapes():
    assert parse_digest(DIGEST) == DIGEST
    assert _code(parse_digest, "sha256:" + "AB" * 32) == SCHEMA_INVALID       # uppercase hex
    assert parse_context_token("ctx:" + "A" * 43)
    assert _code(parse_context_token, DIGEST) == SCHEMA_INVALID               # an unkeyed digest is not a token


@pytest.mark.parametrize("ref", [
    DefinitionRef("item:flame"),
    RevisionRef("rev:1", "item:flame", DIGEST),
    InstanceRef("actor:k", "campaign:7"),
    WorldRef("npc:mira", "campaign:7"),
])
def test_references_round_trip(ref):
    assert parse_reference(ref.to_wire()) == ref


def test_reference_kinds_are_never_substituted():
    world = WorldRef("npc:mira", "campaign:7").to_wire()
    assert _code(parse_reference, world, accept=(InstanceRef,)) == SCHEMA_INVALID


@pytest.mark.parametrize("wire", [
    {"kind": "instance", "id": "a"},                                   # missing scopeId
    {"kind": "instance", "id": "a", "scopeId": "s", "extra": 1},      # unknown key
    {"kind": "revision", "id": "r", "definitionId": "d", "digest": "sha256:x"},
    {"kind": "thing", "id": "a"},
    "actor:k",                                                         # bare ID is not a reference
])
def test_malformed_references(wire):
    assert _code(parse_reference, wire) == SCHEMA_INVALID


def test_utc_timestamps():
    assert parse_utc_timestamp("2026-09-24T12:02:00Z") == datetime(2026, 9, 24, 12, 2, tzinfo=UTC)
    assert parse_utc_timestamp("2026-09-24T12:02:00.5Z").microsecond == 500000
    assert parse_utc_timestamp("2026-09-24T12:02:00.123456789Z").microsecond == 123456   # truncated, documented


@pytest.mark.parametrize("value", ["2026-09-24T14:02:00+02:00", "2026-09-24T12:02:00", "2026-09-24 12:02:00Z",
                                   "2026-09-24T12:02:00z", "2026-02-30T00:00:00Z", "٢٠٢٦-09-24T12:02:00Z", 0])
def test_non_utc_or_invalid_timestamps_are_rejected(value):
    assert _code(parse_utc_timestamp, value) == SCHEMA_INVALID


def test_timestamp_formatting_normalizes_to_utc():
    moment = datetime(2026, 9, 24, 14, 2, tzinfo=timezone(timedelta(hours=2)))
    assert format_utc_timestamp(moment) == "2026-09-24T12:02:00Z"
    assert parse_utc_timestamp(format_utc_timestamp(moment)) == moment
    with pytest.raises(ValueError):
        format_utc_timestamp(datetime(2026, 9, 24, 12, 2))


UNITS = [
    Unit("unit:meter", "dimension:distance", R(1)),
    Unit("unit:foot", "dimension:distance", R(3048, 10000)),
    Unit("unit:second", "dimension:duration", R(1)),
    Unit("unit:round", "dimension:duration", R(6)),
    Unit("unit:dimensionless", "dimension:dimensionless", R(1)),
]


def _table(*extra):
    return UnitTable([*UNITS, *extra])


def test_exact_conversion_and_addition_within_a_dimension():
    table = _table()
    thirty_feet = Quantity(R(30), "unit:foot")
    assert table.convert(thirty_feet, "unit:meter") == Quantity(R(1143, 125), "unit:meter")   # 9.144 m exactly
    assert table.add(Quantity(R(1), "unit:round"), Quantity(R(3), "unit:second")) == Quantity(R(3, 2), "unit:round")
    assert table.subtract(Quantity(R(10), "unit:meter"), thirty_feet) == Quantity(R(107, 125), "unit:meter")


def test_incompatible_dimensions_are_never_added():
    table = _table()
    assert _code(table.add, Quantity(R(1), "unit:meter"), Quantity(R(1), "unit:second")) == SEMANTIC_INVALID
    assert _code(table.convert, Quantity(R(1), "unit:meter"), "unit:dimensionless") == SEMANTIC_INVALID
    assert _code(table.unit, "unit:parsec") == SEMANTIC_INVALID


@pytest.mark.parametrize("extra", [
    Unit("unit:meter", "dimension:distance", R(1)),             # duplicate id
    Unit("unit:yard", "dimension:distance", R(1)),              # second base unit
    Unit("unit:gold", "dimension:currency", R(10)),             # dimension without base
    Unit("unit:neg", "dimension:distance", R(-1)),              # non-positive ratio
])
def test_invalid_unit_tables(extra):
    assert _code(_table, extra) == SEMANTIC_INVALID


def test_unit_table_digest_is_order_independent_and_pinnable():
    forward = _table()
    backward = UnitTable(reversed(UNITS))
    assert forward.digest() == backward.digest()
    assert forward.digest() != _table(Unit("unit:gold", "dimension:currency", R(1))).digest()


def test_quantity_wire_round_trip_and_scaling():
    wire = {"value": {"numerator": 7, "denominator": 2}, "unit": "unit:meter"}
    quantity = Quantity.from_wire(wire)
    assert quantity.to_wire() == wire
    assert quantity.scale(R(2)) == Quantity(R(7), "unit:meter")
    assert _code(Quantity.from_wire, {"value": {"numerator": 1, "denominator": 1}}) == SCHEMA_INVALID
