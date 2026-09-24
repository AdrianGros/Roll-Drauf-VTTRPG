"""Canonical wire primitives: IDs, digests, context tokens, tagged references, UTC timestamps.

Spec v1.1.4 §4 (identity and tagged references), §6 (digests and context
tokens) and §10 (UTC deadlines). Every parser rejects instead of coercing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from vtt.creation_engine.errors import SCHEMA_INVALID, ContractViolation

Path = tuple[str | int, ...]

_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
_CONTEXT_TOKEN = re.compile(r"ctx:[A-Za-z0-9_-]{43}")
_UTC_TIMESTAMP = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]{1,9}))?Z")


def _require(pattern: re.Pattern[str], value: object, what: str, path: Path) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ContractViolation(SCHEMA_INVALID, f"not a valid {what}", path=path)
    return value


def parse_id(value: object, *, path: Path = ()) -> str:
    """An opaque ASCII ID of 1–128 letters, digits, '.', '_', ':' or '-' (§4)."""
    return _require(_ID, value, "id", path)


def parse_digest(value: object, *, path: Path = ()) -> str:
    """A content digest: 'sha256:' plus 64 lowercase hex digits (§6)."""
    return _require(_DIGEST, value, "content digest", path)


def parse_context_token(value: object, *, path: Path = ()) -> str:
    """An opaque context token (§6). Only its shape is checked here; the server binds its meaning."""
    return _require(_CONTEXT_TOKEN, value, "context token", path)


def _exact_keys(value: object, keys: set[str], what: str, path: Path) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ContractViolation(SCHEMA_INVALID, f"{what} must have exactly the keys {sorted(keys)}", path=path)
    return value


@dataclass(frozen=True, slots=True)
class DefinitionRef:
    id: str
    kind: ClassVar[str] = "definition"

    def to_wire(self) -> dict:
        return {"kind": self.kind, "id": self.id}


@dataclass(frozen=True, slots=True)
class RevisionRef:
    id: str
    definition_id: str
    digest: str
    kind: ClassVar[str] = "revision"

    def to_wire(self) -> dict:
        return {"kind": self.kind, "id": self.id, "definitionId": self.definition_id, "digest": self.digest}


@dataclass(frozen=True, slots=True)
class InstanceRef:
    id: str
    scope_id: str
    kind: ClassVar[str] = "instance"

    def to_wire(self) -> dict:
        return {"kind": self.kind, "id": self.id, "scopeId": self.scope_id}


@dataclass(frozen=True, slots=True)
class WorldRef:
    id: str
    scope_id: str
    kind: ClassVar[str] = "world"

    def to_wire(self) -> dict:
        return {"kind": self.kind, "id": self.id, "scopeId": self.scope_id}


Reference = DefinitionRef | RevisionRef | InstanceRef | WorldRef
REFERENCE_TYPES: tuple[type, ...] = (DefinitionRef, RevisionRef, InstanceRef, WorldRef)


def parse_reference(value: object, *, accept: tuple[type, ...] = REFERENCE_TYPES, path: Path = ()) -> Reference:
    """Parse a tagged reference. A kind outside ``accept`` is rejected, never substituted (§4)."""
    kind = value.get("kind") if isinstance(value, dict) else None
    ref_type = next((t for t in accept if t.kind == kind), None)
    if ref_type is None:
        expected = ", ".join(t.kind for t in accept)
        raise ContractViolation(SCHEMA_INVALID, f"reference kind must be one of: {expected}", path=path)
    if ref_type is DefinitionRef:
        _exact_keys(value, {"kind", "id"}, "definition reference", path)
        return DefinitionRef(parse_id(value["id"], path=(*path, "id")))
    if ref_type is RevisionRef:
        _exact_keys(value, {"kind", "id", "definitionId", "digest"}, "revision reference", path)
        return RevisionRef(parse_id(value["id"], path=(*path, "id")),
                           parse_id(value["definitionId"], path=(*path, "definitionId")),
                           parse_digest(value["digest"], path=(*path, "digest")))
    _exact_keys(value, {"kind", "id", "scopeId"}, f"{kind} reference", path)
    return ref_type(parse_id(value["id"], path=(*path, "id")), parse_id(value["scopeId"], path=(*path, "scopeId")))


def parse_utc_timestamp(value: object, *, path: Path = ()) -> datetime:
    """An RFC 3339 UTC timestamp with the 'Z' designator (§10). Offsets and naive times are rejected.

    Fractions beyond microseconds are truncated to microsecond precision.
    """
    match = _UTC_TIMESTAMP.fullmatch(value) if isinstance(value, str) and len(value) <= 40 else None
    if match is None:
        raise ContractViolation(SCHEMA_INVALID, "timestamp must be UTC with a 'Z' designator", path=path)
    whole, fraction = match.groups()
    try:
        moment = datetime.strptime(whole, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        raise ContractViolation(SCHEMA_INVALID, "timestamp is not a real calendar time", path=path) from None
    return moment.replace(microsecond=int((fraction or "0")[:6].ljust(6, "0")))


def format_utc_timestamp(moment: datetime) -> str:
    """Format an aware datetime as a UTC wire timestamp."""
    if moment.tzinfo is None:
        raise ValueError("naive datetimes have no defined instant")
    moment = moment.astimezone(UTC)
    fraction = f".{moment.microsecond:06d}" if moment.microsecond else ""
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + fraction + "Z"
