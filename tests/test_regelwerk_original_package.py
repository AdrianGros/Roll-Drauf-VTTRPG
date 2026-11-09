"""Original (clean-room) Regelwerk packages: validator and generator contracts.

An own book reuses the page-based coverage contract with clean-room card
numbers as pages, must be original text, must not carry third-party brand
terms or reuse SRD names, and only gets reader artifacts at its own URL.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from vtt.rules_content import PackageValidationError, validate_package
from vtt.rules_content import validator as validator_module
from vtt.rules_content.generator import DEFAULT_PACKAGE, generate_artifacts, stale_artifacts
from vtt.rules_content.validator import document_digest

RULESET_ID = "oglans-book-of-chaos-de"
ATTRIBUTION = "Testbuch © Roll Drauf.\n"


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _document(text: str = "Eigener Testinhalt.", heading: str = "Funkelnde Probe", status: str = "original") -> dict:
    document = {
        "schemaVersion": "regelwerk.document.v1",
        "rulesetId": RULESET_ID,
        "documentId": "frame.test",
        "slug": "testkapitel",
        "title": "Testkapitel",
        "navigationPath": ["Vorwort"],
        "order": 1,
        "sourcePages": [1],
        "contentStatus": status,
        "blocks": [
            {"type": "heading", "ruleId": "frame.test.heading", "level": 2, "text": heading},
            {"type": "paragraph", "ruleId": "frame.test.text", "text": text},
        ],
        "ruleRefs": [],
    }
    document["digest"] = document_digest(document)
    return document


@pytest.fixture
def make_package(tmp_path, monkeypatch):
    def build(document: dict | None = None, *, route_key: str | None = "oglan") -> Path:
        package = tmp_path / RULESET_ID
        (package / "documents").mkdir(parents=True, exist_ok=True)
        (package / "attribution.txt").write_text(ATTRIBUTION, encoding="utf-8")
        attribution_sha = hashlib.sha256(ATTRIBUTION.encode("utf-8")).hexdigest()
        document = document or _document()
        _write_json(package / "documents" / f"{document['documentId']}.json", document)
        source = {
            "title": "Testbuch — Clean-Room-Karten 0.1", "publicationDate": "2026-11-09",
            "retrievedAt": "2026-11-09", "url": "https://vtt.roll-drauf.de/regelwerk/oglan/lizenz",
            "sha256": "1" * 64, "pageCount": 999,
        }
        license_info = {"id": "LicenseRef-RollDrauf", "url": "https://vtt.roll-drauf.de/regelwerk/oglan/lizenz",
                        "attributionFile": "attribution.txt", "attributionSha256": attribution_sha}
        manifest = {
            "schemaVersion": "regelwerk.package.v1", "kind": "original", "rulesetId": RULESET_ID,
            "rulesetVersion": "0.1.0", "edition": "2024", "locale": "de-DE", "status": "preview",
            "title": "Testbuch", "source": source, "license": license_info,
            "documents": [{"documentId": document["documentId"], "slug": document["slug"],
                           "title": document["title"], "digest": document["digest"]}],
            "coverage": {
                "requiredPageRanges": [{"first": 1, "last": 1}],
                "excludedPageRanges": [{"first": 2, "last": 999, "reason": "Noch nicht in diesem Paketstand."}],
                "reviewedPageRanges": [],
                "expectedTopLevelSections": [{"sectionId": "frame", "title": "Vorwort", "firstPage": 1, "lastPage": 1}],
            },
        }
        if route_key:
            manifest["routeKey"] = route_key
        _write_json(package / "manifest.json", manifest)
        locks = tmp_path / "source-locks.json"
        _write_json(locks, {"schemaVersion": "regelwerk.source-locks.v1", "sources": [{
            "rulesetId": RULESET_ID, "sourceTitle": source["title"], "sourcePublicationDate": source["publicationDate"],
            "retrievedAt": source["retrievedAt"], "sourceUrl": source["url"], "sourceSha256": source["sha256"],
            "sourcePageCount": source["pageCount"], "licenseId": license_info["id"], "licenseUrl": license_info["url"],
            "attributionFile": "attribution.txt", "attributionSha256": attribution_sha,
        }]})
        monkeypatch.setattr(validator_module, "SOURCE_LOCKS_PATH", locks)
        return package
    return build


def test_original_package_validates_with_card_numbers_as_pages(make_package):
    report = validate_package(make_package())
    assert report.ruleset_id == RULESET_ID
    assert report.coverage.represented_pages == (1,)
    assert report.coverage.complete is False  # nothing owner-reviewed yet: stays preview


def test_original_package_needs_a_route_key(make_package):
    with pytest.raises(PackageValidationError, match="routeKey"):
        validate_package(make_package(route_key=None))


@pytest.mark.parametrize("text", [
    "Ein Zauber aus Tashas Feder.", "Wie bei Dungeons & Dragons üblich.", "Ein Betrachter starrt dich an.",
])
def test_third_party_brand_terms_are_rejected(make_package, text):
    with pytest.raises(PackageValidationError, match="brand term"):
        validate_package(make_package(_document(text=text)))


def test_brand_terms_only_match_whole_words(make_package):
    validate_package(make_package(_document(text="Der Daofisch und die Raoulbrücke.")))


def test_an_srd_name_cannot_be_reused_as_a_heading(make_package):
    with pytest.raises(PackageValidationError, match="SRD name"):
        validate_package(make_package(_document(heading="Feuerball")))


def test_original_package_rejects_transcribed_content(make_package):
    with pytest.raises(PackageValidationError, match="original text"):
        validate_package(make_package(_document(status="verbatim")))


def test_original_package_gets_reader_artifacts_at_its_own_url(make_package):
    artifacts = generate_artifacts(make_package())
    assert sorted(artifacts) == ["coverage.json", "navigation.json", "search-index.json"]
    navigation = artifacts["navigation.json"]
    assert navigation["readerUrl"] == "/regelwerk/oglan"
    assert navigation["licenseUrl"] == "/regelwerk/oglan/lizenz"
    assert navigation["kind"] == "original" and navigation["routeKey"] == "oglan"
    assert navigation["sections"][0]["documents"][0]["url"] == "/regelwerk/oglan/de/testkapitel"
    assert artifacts["search-index.json"]["entries"][0]["url"].startswith("/regelwerk/oglan/de/testkapitel#")


def test_srd_artifacts_are_unchanged():
    assert stale_artifacts(DEFAULT_PACKAGE) == ()
