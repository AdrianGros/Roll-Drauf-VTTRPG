"""Wire-contract validation (spec v1.1.4 §17; core contract 1.1.3 plus registry addendum A1).

The schema files in this package are byte-identical copies of the approved
contracts in docs/creation-engine/ (drift-guarded by tests). Validation only
proves wire shape; semantic, authorization and transaction rules follow in
the admission pipeline.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match
from referencing import Registry, Resource

from vtt.creation_engine.canonical import parse_strict_json
from vtt.creation_engine.errors import SCHEMA_INVALID, ContractViolation

CONTRACT_VERSION = "1.1.3"
CORE_SCHEMA_ID = "urn:rolldrauf:creation-engine:contracts:1.1.3"
REGISTRY_SCHEMA_ID = "urn:rolldrauf:creation-engine:registry:a1"
CORE_OPERATIONS = frozenset({"InvokeActivity", "ResolveDecision", "AdjustResource"})

_DIRECTORY = Path(__file__).parent
SCHEMA_FILES = {
    CORE_SCHEMA_ID: _DIRECTORY / "core-contracts-1.1.3.schema.json",
    REGISTRY_SCHEMA_ID: _DIRECTORY / "registry-a1.schema.json",
}


@cache
def _schema(schema_id: str) -> dict:
    schema = json.loads(SCHEMA_FILES[schema_id].read_text(encoding="utf-8"))
    if schema.get("$id") != schema_id:
        raise RuntimeError(f"{SCHEMA_FILES[schema_id].name} does not declare {schema_id}")
    return schema


@cache
def _registry() -> Registry:
    return Registry().with_resources((sid, Resource.from_contents(_schema(sid))) for sid in SCHEMA_FILES)


@cache
def _validator(schema_id: str, definition: str | None) -> Draft202012Validator:
    schema = _schema(schema_id)
    if definition is not None:
        if definition not in schema["$defs"]:
            raise KeyError(f"{schema_id} has no definition {definition}")
        schema = {"$ref": f"{schema_id}#/$defs/{definition}"}
    return Draft202012Validator(schema, registry=_registry())


def _check(validator: Draft202012Validator, value: object) -> None:
    error = best_match(validator.iter_errors(value))
    if error is not None:
        raise ContractViolation(SCHEMA_INVALID, error.message, path=tuple(error.absolute_path))


def validate_command(envelope: object) -> None:
    """Validate a command envelope against the core contract or registry addendum A1."""
    operation = envelope.get("operation") if isinstance(envelope, dict) else None
    schema_id = CORE_SCHEMA_ID if operation in CORE_OPERATIONS else REGISTRY_SCHEMA_ID
    _check(_validator(schema_id, None), envelope)


def validate_definition(name: str, value: object, *, schema_id: str = CORE_SCHEMA_ID) -> None:
    """Validate a value against one named definition, e.g. 'PendingDecision' or 'PublicReceipt'."""
    _check(_validator(schema_id, name), value)


def parse_command(raw: str | bytes) -> dict:
    """Strict-parse wire JSON (§6) and validate it as a command envelope (§17)."""
    envelope = parse_strict_json(raw)
    validate_command(envelope)
    return envelope
