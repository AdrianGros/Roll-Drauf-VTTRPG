"""WP1: rules the Creation Engine enforces by test (registry addendum A1 §7.7).

1. Engine modules import no Flask, SQLAlchemy or legacy model code. Only the
   transport and store adapters (added in later work packages) may.
2. The packaged schemas are byte-identical to the approved contracts pinned
   in the v1.1.4 package manifest.
"""

import ast
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "vtt" / "creation_engine"
ADAPTER_DIRS = {"transports", "store"}
FORBIDDEN = ("flask", "flask_socketio", "flask_sqlalchemy", "sqlalchemy", "vtt.models", "vtt.extensions")


def _engine_modules():
    for path in sorted(ENGINE.rglob("*.py")):
        if not ADAPTER_DIRS & set(path.relative_to(ENGINE).parts):
            yield path


def _imports(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def test_guard_scans_the_engine():
    assert len(list(_engine_modules())) >= 7


@pytest.mark.parametrize("path", list(_engine_modules()), ids=lambda p: str(p.relative_to(ENGINE)))
def test_engine_modules_import_no_framework_or_legacy_code(path):
    offending = [name for name in _imports(path)
                 if any(name == banned or name.startswith(banned + ".") for banned in FORBIDDEN)]
    assert offending == []


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_packaged_schemas_match_the_pinned_approved_contracts():
    docs = ROOT / "docs" / "creation-engine"
    manifest = json.loads((docs / "v1.1.4" / "review-package-manifest.json").read_text())
    pinned = {Path(entry["path"]).name: entry["sha256"] for entry in manifest["companions"]}
    packaged = {
        "creation-engine-v1.1.3-contracts.schema.json": ENGINE / "contracts" / "core-contracts-1.1.3.schema.json",
        "creation-engine-v1.1-registry-a1.schema.json": ENGINE / "contracts" / "registry-a1.schema.json",
    }
    for approved_name, packaged_path in packaged.items():
        assert _sha256(packaged_path) == pinned[approved_name], f"{packaged_path.name} drifted from {approved_name}"
