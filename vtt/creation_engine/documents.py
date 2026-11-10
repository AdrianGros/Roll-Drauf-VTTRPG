"""Pure document rules behind the Creation Engine's Eagle Homebrew editor (no Flask, no database).

The editor is Matt's unmodified Eagle Homebrew (vendor/eagle-homebrew). In Foundry it talks to Eagle Flight
Control; here the VTT answers the same three requests. This module holds everything about them that does not
need a session: Foundry-shaped UUIDs, the Library pack names, the document.update path semantics and the limits.
"""

from __future__ import annotations

import copy
import json
import re

# core/catalog.ts, in catalog order: key -> (document name, dnd5e subtype or None, versioned).
CATALOG = {
    "loot": ("Item", "loot", True),
    "tools": ("Item", "tool", True),
    "weapons": ("Item", "weapon", True),
    "equipment": ("Item", "equipment", True),
    "consumables": ("Item", "consumable", True),
    "containers": ("Item", "container", True),
    "feats": ("Item", "feat", True),
    "spells": ("Item", "spell", True),
    "species": ("Item", "race", True),
    "backgrounds": ("Item", "background", True),
    "npcs": ("Actor", "npc", True),
    "vehicles": ("Actor", "vehicle", True),
    "classes": ("Item", "class", True),
    "subclasses": ("Item", "subclass", True),
    "facilities": ("Item", "facility", True),
    "encounters": ("Actor", "encounter", False),
    "groups": ("Actor", "group", False),
    "rolltables": ("RollTable", None, False),
}
DOCUMENT_NAMES = ("Actor", "Item", "RollTable")
RULES_VERSIONS = ("2014", "2024")

# Flight Control's limits as Matt's core enforces them client-side (core/edit-projection.ts).
MAX_PATHS = 50
MAX_REQUEST_BYTES = 65_536
MAX_DOCUMENT_BYTES = 1_048_576
MAX_DOCUMENTS_PER_SCOPE = 5_000
MAX_DEPTH = 32

ID_PATTERN = re.compile(r"^[A-Za-z0-9]{1,64}$")
PACK_PATTERN = re.compile(r"^world\.eagle-([a-z]+)(?:-(2014|2024))?$")
FORBIDDEN_SEGMENTS = {"__proto__", "constructor", "prototype", ""}


class RequestFailure(Exception):
    """A Flight Control style failure: returned as {ok: false, reason, detail}, never raised to the client."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail[:500]


def fail(reason: str, detail: str = ""):
    raise RequestFailure(reason, detail)


def pack_entry(pack: str):
    """(catalog key, document name, subtype) for an Eagle Library pack name, or a failure."""
    match = PACK_PATTERN.match(pack) if isinstance(pack, str) else None
    entry = CATALOG.get(match.group(1)) if match else None
    if not entry or bool(match.group(2)) != entry[2]:
        fail("invalid-payload", f"unknown Library pack {str(pack)[:80]}")
    return match.group(1), entry[0], entry[1]


def library_uuid(pack: str, document_name: str, document_id: str) -> str:
    return f"Compendium.{pack}.{document_name}.{document_id}"


def world_uuid(document_name: str, document_id: str) -> str:
    return f"{document_name}.{document_id}"


def parse_uuid(uuid):
    """('library', pack, document_name, id) or ('world', None, document_name, id)."""
    if not isinstance(uuid, str) or len(uuid) > 200:
        fail("invalid-payload", "uuid must be a string")
    parts = uuid.split(".")
    if len(parts) == 2 and parts[0] in DOCUMENT_NAMES and ID_PATTERN.match(parts[1]):
        return "world", None, parts[0], parts[1]
    if len(parts) == 5 and parts[0] == "Compendium" and parts[3] in DOCUMENT_NAMES and ID_PATTERN.match(parts[4]):
        pack = f"{parts[1]}.{parts[2]}"
        _, document_name, _ = pack_entry(pack)
        if document_name != parts[3]:
            fail("invalid-payload", f"{parts[3]} does not belong in {pack}")
        return "library", pack, parts[3], parts[4]
    fail("invalid-payload", f"unsupported uuid {uuid[:80]}")


def check_id(document_id):
    if not isinstance(document_id, str) or not ID_PATTERN.match(document_id):
        fail("invalid-payload", "id must be 1-64 letters or digits")
    return document_id


def check_json(value, *, depth=0):
    """Rejects anything Flight Control's isJsonValue would reject (NaN, Infinity, non-JSON types, deep nesting)."""
    if depth > MAX_DEPTH:
        fail("invalid-payload", "nesting too deep")
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, (int, float)):
        if value != value or value in (float("inf"), float("-inf")):
            fail("invalid-payload", "numbers must be finite")
        return
    if isinstance(value, list):
        for item in value:
            check_json(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                fail("invalid-payload", "object keys must be strings")
            check_json(item, depth=depth + 1)
        return
    fail("invalid-payload", f"not JSON: {type(value).__name__}")


def encoded_size(value) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def check_document(source: dict, document_name: str, subtype):
    if not isinstance(source, dict):
        fail("invalid-payload", "document data must be an object")
    name = source.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        fail("invalid-payload", "name must be 1-200 characters")
    if subtype is not None and source.get("type") != subtype:
        fail("invalid-payload", f"{document_name} type must be {subtype}")
    if encoded_size(source) > MAX_DOCUMENT_BYTES:
        fail("invalid-payload", "document too large")


def split_path(path):
    if not isinstance(path, str) or len(path) > 300:
        fail("invalid-payload", "paths must be strings")
    parts = path.split(".")
    if any(part in FORBIDDEN_SEGMENTS for part in parts):
        fail("invalid-payload", f"invalid path {path[:80]}")
    return parts


def apply_update(source: dict, changes: dict) -> list[str]:
    """document.update as Eagle Homebrew relies on it: each dotted path's value is replaced as a whole.

    Matt's editor merges client-side (core/edit-projection.ts mergeJsonObjects/projectCollection/projectMapping)
    and sends the complete target value per path, including unmodelled entries, so removing an Activity means
    the path's new value no longer contains it. A last segment starting with "-=" deletes that key. `_id` and
    `type` are immutable, as in Foundry.
    """
    if not isinstance(changes, dict) or not changes:
        fail("invalid-payload", "changes must be a non-empty object")
    if len(changes) > MAX_PATHS:
        fail("invalid-payload", f"at most {MAX_PATHS} paths per update")
    check_json(changes)
    updated = copy.deepcopy(source)
    changed = []
    for path, value in changes.items():
        parts = split_path(path)
        last = parts[-1]
        deleting = last.startswith("-=")
        key = last[2:] if deleting else last
        if key in FORBIDDEN_SEGMENTS or (len(parts) == 1 and key in ("_id", "type")):
            fail("invalid-payload", f"{path[:80]} cannot be changed")
        node = updated
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                if deleting:
                    break
                child = node[part] = {}
            node = child
        else:
            if deleting:
                node.pop(key, None)
            else:
                node[key] = copy.deepcopy(value)
            changed.append(path)
    source.clear()
    source.update(updated)
    return changed


def index_row(source: dict) -> dict:
    """What readIndex needs (core/creation-target.ts: name + requirements) plus type for pickers."""
    system = source.get("system") if isinstance(source.get("system"), dict) else {}
    return {"_id": source.get("_id"), "name": source.get("name"), "type": source.get("type"),
            "requirements": system.get("requirements")}
