"""Content schema registry (spec v1.1.4 §6): trusted configuration mapping type ID and version to a schema.

Content schemas may $ref the approved wire contracts. Unknown types or versions
are unsupported (they could only be stored inert via an archival import, not
in G1). The registry's LockedArtifact pins every content schema and the wire
contracts by digest, so an execution lock names the exact validation rules.
Semantic validators are code, which the digest cannot see: changing one
requires a new bundle version.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.contracts import SCHEMA_FILES, contract_registry
from vtt.creation_engine.errors import SCHEMA_INVALID, SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.types import parse_id


@dataclass(frozen=True, slots=True)
class SchemaTypeRef:
    type_id: str
    version: int

    def __post_init__(self) -> None:
        parse_id(self.type_id)
        if type(self.version) is not int or not 0 <= self.version <= 2**53 - 1:
            raise ContractViolation(SCHEMA_INVALID, "schema version must be a nonnegative safe integer")

    def to_wire(self) -> dict:
        return {"typeId": self.type_id, "version": self.version}


@dataclass(frozen=True)
class SchemaType:
    type_id: str
    version: int
    schema: Mapping                                  # JSON Schema 2020-12; objects must be closed (§6)
    semantic: Callable[[dict], None] | None = None   # raises ContractViolation(SEMANTIC_INVALID)

    @property
    def ref(self) -> SchemaTypeRef:
        return SchemaTypeRef(self.type_id, self.version)


class SchemaRegistry:
    def __init__(self, bundle_id: str, bundle_version: str, types: Iterable[SchemaType]):
        self.bundle_id = parse_id(bundle_id)
        self.bundle_version = parse_id(bundle_version)
        self._types: dict[SchemaTypeRef, SchemaType] = {}
        self._validators: dict[SchemaTypeRef, Draft202012Validator] = {}
        for schema_type in types:
            parse_id(schema_type.type_id)
            if schema_type.ref in self._types:
                raise ValueError(f"{schema_type.type_id}@{schema_type.version} is registered twice")
            Draft202012Validator.check_schema(schema_type.schema)
            # The caller's nested dicts must not be able to change a registered
            # validator or its pinned digest after registration.
            snapshot = SchemaType(schema_type.type_id, schema_type.version,
                                  parse_strict_json(canonical_bytes(schema_type.schema)), schema_type.semantic)
            self._types[snapshot.ref] = snapshot
            self._validators[snapshot.ref] = Draft202012Validator(snapshot.schema, registry=contract_registry())
        self._artifact = self._build_artifact()

    def get(self, ref: SchemaTypeRef) -> SchemaType:
        try:
            registered = self._types[ref]
            return SchemaType(registered.type_id, registered.version,
                              parse_strict_json(canonical_bytes(registered.schema)), registered.semantic)
        except KeyError:
            raise ContractViolation(SEMANTIC_INVALID, f"schema type {ref.type_id}@{ref.version} is not supported") from None

    def validate(self, ref: SchemaTypeRef, content: object) -> None:
        """Schema first (SCHEMA_INVALID), then the type's semantic validator (SEMANTIC_INVALID)."""
        schema_type = self.get(ref)
        error = best_match(self._validators[ref].iter_errors(content))
        if error is not None:
            raise ContractViolation(SCHEMA_INVALID, error.message, path=tuple(error.absolute_path))
        if schema_type.semantic is not None:
            schema_type.semantic(content)

    def artifact(self) -> dict:
        """The schema bundle as an ExecutionLock LockedArtifact (§12)."""
        return dict(self._artifact)

    def _build_artifact(self) -> dict:
        document = {
            "contracts": {schema_id: content_digest(json.loads(path.read_text(encoding="utf-8")))
                          for schema_id, path in sorted(SCHEMA_FILES.items())},
            "types": [{"typeId": t.type_id, "version": t.version, "schema": t.schema}
                      for t in sorted(self._types.values(), key=lambda t: (t.type_id, t.version))],
        }
        return {"kind": "schema-bundle", "id": self.bundle_id, "version": self.bundle_version,
                "digest": content_digest(document)}
