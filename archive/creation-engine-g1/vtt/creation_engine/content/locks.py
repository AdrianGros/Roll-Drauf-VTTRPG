"""Execution locks (spec v1.1.4 §12, contract 1.1.3 `ExecutionLock`).

A lock pins the exact closure a scope executes: every transitively referenced
revision, the ruleset, the schema bundle, the evaluator, the configuration and
the unit table. Resolution rejects missing dependencies, digest mismatches,
ambiguous identity (two revisions of one definition) and unsupported schema
types before the lock exists. The lock ID is content-addressed, so the same
closure always yields the same lock. Revision dependency cycles cannot occur:
a revision can only reference digests that already exist.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from vtt.creation_engine.canonical import canonical_bytes, content_digest, parse_strict_json
from vtt.creation_engine.content.records import Revision
from vtt.creation_engine.content.registry import SchemaRegistry
from vtt.creation_engine.content.ruleset import Ruleset
from vtt.creation_engine.contracts import validate_definition
from vtt.creation_engine.errors import SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.evaluator.identity import evaluator_artifact
from vtt.creation_engine.types import RevisionRef, parse_reference

PROFILE_ID = "core-safe-1"


@dataclass(frozen=True, slots=True)
class ExecutionLock:
    lock_id: str
    canonical: bytes
    digest: str

    def validate_integrity(self) -> None:
        wire = self.wire
        validate_definition("ExecutionLock", wire)
        if canonical_bytes(wire) != self.canonical:
            raise ContractViolation(SEMANTIC_INVALID, "execution lock is not canonical JSON")
        if "sha256:" + hashlib.sha256(self.canonical).hexdigest() != self.digest:
            raise ContractViolation(SEMANTIC_INVALID, "execution lock digest identifies different content")
        body = {key: value for key, value in wire.items() if key != "lockId"}
        expected_id = "lock:" + content_digest(body).removeprefix("sha256:")
        if wire["lockId"] != self.lock_id or self.lock_id != expected_id:
            raise ContractViolation(SEMANTIC_INVALID, "execution lock identity does not match its content")

    @property
    def wire(self) -> dict:
        return parse_strict_json(self.canonical)

    @property
    def revisions(self) -> tuple[RevisionRef, ...]:
        return tuple(parse_reference(ref, accept=(RevisionRef,)) for ref in self.wire["revisions"])


def resolve_lock(roots: Iterable[RevisionRef], *, fetch: Callable[[str], Revision | None], ruleset: Ruleset,
                 registry: SchemaRegistry, evaluator: Mapping, configuration: Mapping) -> ExecutionLock:
    if dict(evaluator) != evaluator_artifact():
        raise ContractViolation(SEMANTIC_INVALID, "incompatible evaluator: G1 supports only the installed core-safe-1 artifact")
    closure: dict[str, Revision] = {}
    pending = list(roots)
    while pending:
        ref = pending.pop()
        revision = fetch(ref.id)
        if revision is None:
            raise ContractViolation(SEMANTIC_INVALID, f"missing dependency: revision {ref.id}")
        if revision.id != ref.id:
            raise ContractViolation(SEMANTIC_INVALID, f"revision identity mismatch for {ref.id}")
        revision.validate_integrity()
        if revision.digest != ref.digest or revision.definition_id != ref.definition_id:
            raise ContractViolation(SEMANTIC_INVALID, f"digest mismatch for revision {ref.id}")
        registry.validate(revision.schema_type, revision.content)
        existing = closure.get(revision.definition_id)
        if existing is not None:
            if existing.id != revision.id:
                raise ContractViolation(SEMANTIC_INVALID, f"ambiguous identity: definition {revision.definition_id} "
                                                          f"resolves to {existing.id} and {revision.id}")
            continue
        closure[revision.definition_id] = revision
        pending.extend(revision.dependencies())
    body = {
        "profileId": PROFILE_ID,
        "ruleset": ruleset.artifact(),
        "schemaBundle": registry.artifact(),
        "evaluator": dict(evaluator),
        "configurationDigest": content_digest(dict(configuration)),
        "unitTableDigest": ruleset.units.digest(),
        "packages": [],
        "revisions": [r.ref().to_wire() for r in sorted(closure.values(), key=lambda r: (r.definition_id, r.id))],
        "assets": [],
    }
    wire = {"lockId": "lock:" + content_digest(body).removeprefix("sha256:"), **body}
    validate_definition("ExecutionLock", wire)
    return ExecutionLock(wire["lockId"], canonical_bytes(wire), content_digest(wire))
