"""R0 source, rights, schema, digest, and coverage contracts for Regelwerk."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from vtt.rules_content import PackageValidationError, validate_package
from vtt.rules_content.validator import CONTENT_ROOT, document_digest


PACKAGE_ROOT = CONTENT_ROOT / "srd-5.2.1-de"
SOURCE_LOCKS = CONTENT_ROOT / "source-locks.json"
SOURCE_SHA256 = "f06989dcdf98c8e93b52ba5ea9db52d5e1b054d6d87a148ff295138bafe8a65b"
ATTRIBUTION_SHA256 = "c0bd7a2a58d6ac29c8adbdf3e2750ec6262fcba6ecaed923c8cc2dede2fb87c9"


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _minimal_complete_package(tmp_path: Path, *, status: str = "preview") -> Path:
    package = tmp_path / "srd-5.2.1-de"
    shutil.copytree(PACKAGE_ROOT, package)
    for existing_document in (package / "documents").glob("*.json"):
        existing_document.unlink()
    manifest = _load_json(package / "manifest.json")
    manifest["status"] = status
    manifest["coverage"] = {
        "requiredPageRanges": [{"first": 5, "last": 5}],
        "excludedPageRanges": [
            {"first": 1, "last": 4, "reason": "Test fixture excludes source front matter."},
            {"first": 6, "last": 412, "reason": "Test fixture limits the content range."},
        ],
        "reviewedPageRanges": [{"first": 5, "last": 5}],
        "expectedTopLevelSections": [
            {"sectionId": "core", "title": "Die Spielregeln", "firstPage": 5, "lastPage": 5}
        ],
    }
    if status == "published":
        manifest["publishedAt"] = "2026-10-15T12:00:00Z"

    document = {
        "schemaVersion": "regelwerk.document.v1",
        "rulesetId": "srd-5.2.1-de",
        "documentId": "core.test",
        "slug": "testregel",
        "title": "Testregel",
        "navigationPath": ["Die Spielregeln", "Testregel"],
        "order": 1,
        "sourcePages": [5],
        "contentStatus": "format-only",
        "blocks": [
            {"type": "paragraph", "ruleId": "core.test", "text": "Geprüfter Testinhalt."}
        ],
        "ruleRefs": [],
    }
    document["digest"] = document_digest(document)
    _write_json(package / "documents" / "core.test.json", document)
    manifest["documents"] = [
        {
            "documentId": document["documentId"],
            "slug": document["slug"],
            "title": document["title"],
            "digest": document["digest"],
        }
    ]
    _write_json(package / "manifest.json", manifest)
    return package


def _rewrite_document(package: Path, mutation) -> None:
    document_path = package / "documents" / "core.test.json"
    document = _load_json(document_path)
    mutation(document)
    document["digest"] = document_digest(document)
    _write_json(document_path, document)
    manifest = _load_json(package / "manifest.json")
    manifest["documents"][0]["digest"] = document["digest"]
    _write_json(package / "manifest.json", manifest)


def test_r0_source_and_attribution_are_pinned():
    registry = _load_json(SOURCE_LOCKS)
    assert registry["schemaVersion"] == "regelwerk.source-locks.v1"
    assert len(registry["sources"]) == 1
    source = registry["sources"][0]
    assert source["rulesetId"] == "srd-5.2.1-de"
    assert source["sourceSha256"] == SOURCE_SHA256
    assert source["sourcePageCount"] == 412
    assert source["licenseId"] == "CC-BY-4.0"
    assert source["attributionSha256"] == ATTRIBUTION_SHA256
    assert hashlib.sha256((PACKAGE_ROOT / "attribution.txt").read_bytes()).hexdigest() == ATTRIBUTION_SHA256


def test_live_package_distinguishes_provenance_from_reviewed_coverage():
    """Published live-package snapshot: update the represented/covered expectations whenever
    R2+ transcription adds or reviews another document; the identity, provenance-
    vs-reviewed distinction, and incompleteness this guards stay the same."""
    report = validate_package(PACKAGE_ROOT)
    assert report.ruleset_id == "srd-5.2.1-de"
    assert report.ruleset_version == "1.0.0"
    assert report.status == "published"
    assert report.document_count == 101
    assert report.attribution_sha256 == ATTRIBUTION_SHA256
    assert report.coverage.required_pages == tuple(range(5, 413))
    assert report.coverage.represented_pages == tuple(range(5, 413))
    assert report.coverage.covered_pages == tuple(range(5, 413))
    assert report.coverage.missing_pages == ()
    assert report.coverage.covered_sections == ("core", "character-creation", "classes", "character-origins", "feats", "equipment", "spells", "rules-glossary", "gameplay-toolbox", "magic-items", "monsters", "animals")
    assert report.coverage.missing_sections == ()
    assert report.coverage.complete


def test_partial_page_provenance_cannot_claim_complete_coverage(tmp_path):
    package = _minimal_complete_package(tmp_path)
    manifest = _load_json(package / "manifest.json")
    manifest["coverage"]["reviewedPageRanges"] = []
    _write_json(package / "manifest.json", manifest)

    report = validate_package(package)

    assert report.coverage.represented_pages == (5,)
    assert report.coverage.covered_pages == ()
    assert report.coverage.missing_pages == (5,)
    assert not report.coverage.complete


def test_complete_published_fixture_validates(tmp_path):
    package = _minimal_complete_package(tmp_path, status="published")
    report = validate_package(package)
    assert report.status == "published"
    assert report.document_count == 1
    assert report.coverage.complete
    assert report.coverage.covered_sections == ("core",)


def test_incomplete_package_cannot_be_published(tmp_path):
    package = tmp_path / "srd-5.2.1-de"
    shutil.copytree(PACKAGE_ROOT, package)
    manifest = _load_json(package / "manifest.json")
    manifest["status"] = "published"
    manifest["publishedAt"] = "2026-10-15T12:00:00Z"
    manifest["coverage"]["reviewedPageRanges"] = [{"first": 5, "last": 294}]
    _write_json(package / "manifest.json", manifest)
    with pytest.raises(PackageValidationError, match="complete source coverage"):
        validate_package(package)


def test_attribution_tampering_is_rejected(tmp_path):
    package = _minimal_complete_package(tmp_path)
    (package / "attribution.txt").write_text("Changed attribution.\n", encoding="utf-8")
    with pytest.raises(PackageValidationError, match="attribution file"):
        validate_package(package)


def test_manifest_cannot_replace_the_approved_source(tmp_path):
    package = _minimal_complete_package(tmp_path)
    manifest = _load_json(package / "manifest.json")
    manifest["source"]["sha256"] = "0" * 64
    _write_json(package / "manifest.json", manifest)
    with pytest.raises(PackageValidationError, match="approved source lock"):
        validate_package(package)


def test_cross_edition_document_is_rejected(tmp_path):
    package = _minimal_complete_package(tmp_path)
    _rewrite_document(package, lambda document: document.__setitem__("rulesetId", "srd-5.1-de"))
    with pytest.raises(PackageValidationError, match="another ruleset"):
        validate_package(package)


def test_arbitrary_content_markup_is_rejected(tmp_path):
    package = _minimal_complete_package(tmp_path)

    def add_markup(document):
        document["blocks"][0]["text"] = "<script>alert('no')</script>"

    _rewrite_document(package, add_markup)
    with pytest.raises(PackageValidationError, match="arbitrary HTML"):
        validate_package(package)


def test_closed_document_schema_rejects_unknown_fields(tmp_path):
    package = _minimal_complete_package(tmp_path)
    _rewrite_document(package, lambda document: document.__setitem__("html", "<p>unsafe</p>"))
    with pytest.raises(PackageValidationError, match="schema violation"):
        validate_package(package)


def test_table_rows_must_match_the_declared_columns(tmp_path):
    package = _minimal_complete_package(tmp_path)

    def replace_with_bad_table(document):
        document["blocks"] = [
            {
                "type": "table",
                "ruleId": "core.test",
                "caption": "Testtabelle",
                "columns": ["A", "B"],
                "rows": [["nur eine Zelle"]],
            }
        ]

    _rewrite_document(package, replace_with_bad_table)
    with pytest.raises(PackageValidationError, match="wrong column count"):
        validate_package(package)


def test_internal_rule_references_must_resolve(tmp_path):
    package = _minimal_complete_package(tmp_path)

    def add_missing_reference(document):
        document["ruleRefs"] = [
            {"rulesetId": "srd-5.2.1-de", "ruleId": "core.missing", "label": "Fehlt"}
        ]

    _rewrite_document(package, add_missing_reference)
    with pytest.raises(PackageValidationError, match="missing rule ID"):
        validate_package(package)


def test_document_digest_mismatch_is_rejected(tmp_path):
    package = _minimal_complete_package(tmp_path)
    document_path = package / "documents" / "core.test.json"
    document = _load_json(document_path)
    document["title"] = "Ungeprüfte Änderung"
    _write_json(document_path, document)
    with pytest.raises(PackageValidationError, match="differs from manifest|digest mismatch"):
        validate_package(package)


def test_pinned_package_digest_detects_mutation_under_the_same_version(tmp_path):
    package = _minimal_complete_package(tmp_path, status="published")
    original = validate_package(package)
    manifest = _load_json(package / "manifest.json")
    manifest["title"] = "Geänderter Titel"
    _write_json(package / "manifest.json", manifest)
    with pytest.raises(PackageValidationError, match="package digest changed"):
        validate_package(package, expected_digest=original.package_digest)


def test_manifest_and_document_inventory_must_match(tmp_path):
    package = _minimal_complete_package(tmp_path)
    (package / "documents" / "unlisted.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(PackageValidationError, match="inventory mismatch"):
        validate_package(package)
