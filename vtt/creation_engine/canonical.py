"""Strict JSON input and canonical bytes (spec v1.1.4 §6).

Commits reject duplicate keys, non-finite numbers, integers outside the safe
range and invalid Unicode. Canonical bytes follow RFC 8785 (JCS); a content
digest is SHA-256 over those bytes. Strings are never Unicode-normalized.
"""

from __future__ import annotations

import hashlib
import json
import math

import rfc8785

from vtt.creation_engine.errors import SCHEMA_INVALID, BudgetExceeded, ContractViolation

MAX_SAFE_INTEGER = 9_007_199_254_740_991

Path = tuple[str | int, ...]


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ContractViolation(SCHEMA_INVALID, f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(name: str) -> object:
    raise ContractViolation(SCHEMA_INVALID, f"non-finite number {name} is not JSON")


def _parse_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ContractViolation(SCHEMA_INVALID, f"number {text} is not finite")
    return value


def _check_tree(value: object, path: Path) -> None:
    """Accept only JSON values with safe integers, finite floats and valid Unicode."""
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise ContractViolation(SCHEMA_INVALID, "integer outside the safe range", path=path)
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractViolation(SCHEMA_INVALID, "number is not finite", path=path)
        return
    if isinstance(value, str):
        _check_unicode(value, path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_tree(item, (*path, index))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractViolation(SCHEMA_INVALID, "object keys must be strings", path=path)
            _check_unicode(key, (*path, key))
            _check_tree(item, (*path, key))
        return
    raise ContractViolation(SCHEMA_INVALID, f"{type(value).__name__} is not a JSON value", path=path)


def _check_unicode(text: str, path: Path) -> None:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise ContractViolation(SCHEMA_INVALID, "string contains invalid Unicode", path=path) from None


def parse_strict_json(raw: str | bytes) -> object:
    """Parse wire JSON, rejecting everything §6 forbids instead of repairing it."""
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ContractViolation(SCHEMA_INVALID, "body is not valid UTF-8") from None
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys,
                           parse_constant=_reject_constant, parse_float=_parse_float)
    except json.JSONDecodeError as exc:
        raise ContractViolation(SCHEMA_INVALID, f"malformed JSON: {exc.msg}") from None
    except ValueError:
        # e.g. integer literals beyond Python's int-conversion digit limit
        raise ContractViolation(SCHEMA_INVALID, "malformed JSON number") from None
    except RecursionError:
        raise BudgetExceeded("JSON nesting exceeds the structural limit") from None
    _checked(value)
    return value


def _checked(value: object) -> None:
    try:
        _check_tree(value, ())
    except RecursionError:
        raise BudgetExceeded("JSON nesting exceeds the structural limit") from None


def canonical_bytes(value: object) -> bytes:
    """RFC 8785 canonical UTF-8 bytes of a JSON value."""
    _checked(value)
    try:
        return rfc8785.dumps(value)
    except RecursionError:
        raise BudgetExceeded("JSON nesting exceeds the structural limit") from None


def content_digest(value: object) -> str:
    """'sha256:' digest of the canonical bytes; identifies exact bytes, not author intent (§6)."""
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()
