"""Content records (spec v1.1.4 §4, §13, §15): workspaces, definitions, revisions and drafts.

A revision is immutable canonical bytes: its content is re-read from those
bytes, so no caller can alter what the digest identifies. Drafts may hold
incomplete content; each draft version is an immutable snapshot, so undo is a
new version that restores an earlier snapshot (§13), and a stale expected
version is DRAFT_VERSION_CONFLICT.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime

from vtt.creation_engine.canonical import canonical_bytes, parse_strict_json
from vtt.creation_engine.content.registry import SchemaRegistry, SchemaTypeRef
from vtt.creation_engine.errors import DRAFT_VERSION_CONFLICT, SEMANTIC_INVALID, ContractViolation
from vtt.creation_engine.types import RevisionRef, parse_id, parse_reference


def new_id(prefix: str) -> str:
    """A fresh opaque ID. System-generated IDs may default because they carry no game meaning (§15)."""
    return parse_id(f"{prefix}:{uuid.uuid4().hex}")


@dataclass(frozen=True, slots=True)
class Workspace:
    id: str
    owner_user_id: int          # a local account; never derived from a Discord guild (§1)
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Definition:
    id: str
    workspace_id: str
    name: str                   # a mutable label; the ID is the identity (§4)
    schema_type_id: str
    created_at: datetime
    tombstoned_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Revision:
    id: str
    definition_id: str
    schema_type: SchemaTypeRef
    canonical: bytes
    digest: str
    provenance: bytes           # canonical bytes; metadata outside the content digest
    author_user_id: int
    created_at: datetime

    def validate_integrity(self) -> None:
        parse_id(self.id)
        parse_id(self.definition_id)
        actual = "sha256:" + hashlib.sha256(self.canonical).hexdigest()
        if actual != self.digest:
            raise ContractViolation(SEMANTIC_INVALID, "revision digest does not identify its content bytes")
        if canonical_bytes(self.content) != self.canonical:
            raise ContractViolation(SEMANTIC_INVALID, "revision content is not canonical JSON")
        if canonical_bytes(parse_strict_json(self.provenance)) != self.provenance:
            raise ContractViolation(SEMANTIC_INVALID, "revision provenance is not canonical JSON")

    @property
    def content(self) -> dict:
        return parse_strict_json(self.canonical)

    def ref(self) -> RevisionRef:
        return RevisionRef(self.id, self.definition_id, self.digest)

    def dependencies(self) -> tuple[RevisionRef, ...]:
        """Revision references anywhere in the content; tagged references are unambiguous (§4)."""
        found: set[RevisionRef] = set()
        pending: list[object] = [self.content]
        while pending:
            node = pending.pop()
            if isinstance(node, dict):
                if node.get("kind") == "revision":
                    found.add(parse_reference(node, accept=(RevisionRef,)))
                else:
                    # §5's declared inert legacy container is not a reference
                    # source, even when imported keys resemble tagged wire refs.
                    pending.extend(value for key, value in node.items() if key != "legacyMetadata")
            elif isinstance(node, list):
                pending.extend(node)
        return tuple(sorted(found, key=lambda ref: (ref.definition_id, ref.id)))


def create_revision(definition_id: str, schema_type: SchemaTypeRef, content: object, *, registry: SchemaRegistry,
                    author_user_id: int, provenance: object, now: datetime) -> Revision:
    """Validate content against its registered schema and freeze it as canonical bytes (§6)."""
    parse_id(definition_id)
    canonical = canonical_bytes(content)
    registry.validate(schema_type, parse_strict_json(canonical))
    return Revision(new_id("rev"), definition_id, schema_type, canonical,
                    "sha256:" + hashlib.sha256(canonical).hexdigest(), canonical_bytes(provenance), author_user_id, now)


@dataclass(frozen=True, slots=True)
class Draft:
    id: str
    workspace_id: str
    definition_id: str | None   # None until the first revision creates the definition
    schema_type: SchemaTypeRef
    authoring_locale: str
    version: int
    content: bytes              # canonical bytes of the (possibly incomplete) proposed content
    created_at: datetime
    updated_at: datetime
    schema_bundle: bytes       # canonical LockedArtifact of the authoring registry (addendum A1 §2)


def require_draft_version(draft: Draft, expected_version: int) -> None:
    if draft.version != expected_version:
        raise ContractViolation(DRAFT_VERSION_CONFLICT,
                                f"draft {draft.id} is at version {draft.version}, not {expected_version}")


@dataclass(frozen=True, slots=True)
class DraftAnswer:
    """One entry of the append-only decision log (§15). A later answer to the same question supersedes it."""
    draft_id: str
    draft_version: int          # the version this answer produced
    question_id: str
    question_version: int
    answer: bytes               # canonical DraftAnswer wire value
    prompt_locale: str
    author_user_id: int
    mutations: bytes            # canonical list of resulting canonical mutations
    invalidated: bytes          # canonical list of invalidated descendant question IDs
    created_at: datetime
