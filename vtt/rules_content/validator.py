"""Validation and deterministic coverage reporting for Regelwerk packages.

The official source lock lives outside an individual content package so a
manifest cannot silently replace its own source or attribution. Published
content is identified by an RFC 8785/SHA-256 digest; callers can pin that
digest and reject changed bytes under the same package version.

An `original` package is Roll Drauf's own clean-room book. Its "source" is
the private hand-off of mechanics cards: `source.sha256` pins that hand-off,
`pageCount` is the card number space and a document's `sourcePages` are the
card numbers it was written from, so the page-based coverage contract carries
over unchanged. Its documents must be `original` text, must not use
third-party brand terms and must not reuse an SRD entity name as a heading.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from jsonschema import Draft202012Validator, FormatChecker

from vtt.creation_engine.canonical import content_digest, parse_strict_json


CONTENT_ROOT = Path(__file__).resolve().parent
SCHEMA_ROOT = CONTENT_ROOT / "schemas"
SOURCE_LOCKS_PATH = CONTENT_ROOT / "source-locks.json"
BRAND_DENYLIST_PATH = CONTENT_ROOT / "brand-denylist.txt"
SRD_COMPENDIUM_PATH = CONTENT_ROOT / "srd-5.2.1-de" / "generated" / "compendium.json"
_SRD_NAME_TYPES = frozenset({
    "background", "class", "class-feature", "class-option", "feat", "magic-item", "species", "spell", "subclass",
})
MAX_DOCUMENT_BYTES = 1_048_576
_HTML_TAG = re.compile(r"<\s*/?\s*[A-Za-z][^>]*>")


class PackageValidationError(ValueError):
    """A package cannot be trusted or published."""


@dataclass(frozen=True, slots=True)
class CoverageReport:
    required_pages: tuple[int, ...]
    represented_pages: tuple[int, ...]
    covered_pages: tuple[int, ...]
    missing_pages: tuple[int, ...]
    unexpected_pages: tuple[int, ...]
    covered_sections: tuple[str, ...]
    missing_sections: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_pages and not self.unexpected_pages and not self.missing_sections

    def to_wire(self) -> dict:
        return {
            "complete": self.complete,
            "requiredPageCount": len(self.required_pages),
            "representedPageCount": len(self.represented_pages),
            "representedPageRanges": _compress_ranges(self.represented_pages),
            "coveredPageCount": len(self.covered_pages),
            "coveredPageRanges": _compress_ranges(self.covered_pages),
            "missingPageRanges": _compress_ranges(self.missing_pages),
            "unexpectedPageRanges": _compress_ranges(self.unexpected_pages),
            "coveredSections": list(self.covered_sections),
            "missingSections": list(self.missing_sections),
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    ruleset_id: str
    ruleset_version: str
    status: str
    package_digest: str
    document_count: int
    attribution_sha256: str
    coverage: CoverageReport

    def to_wire(self) -> dict:
        return {
            "rulesetId": self.ruleset_id,
            "rulesetVersion": self.ruleset_version,
            "status": self.status,
            "packageDigest": self.package_digest,
            "documentCount": self.document_count,
            "attributionSha256": self.attribution_sha256,
            "coverage": self.coverage.to_wire(),
        }


def _compress_ranges(values: Iterable[int]) -> list[dict[str, int]]:
    ordered = sorted(set(values))
    if not ordered:
        return []
    ranges: list[dict[str, int]] = []
    first = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append({"first": first, "last": previous})
        first = previous = value
    ranges.append({"first": first, "last": previous})
    return ranges


def _read_json(path: Path) -> dict:
    try:
        value = parse_strict_json(path.read_bytes())
    except OSError as exc:
        raise PackageValidationError(f"cannot read {path}: {exc}") from exc
    except Exception as exc:
        raise PackageValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackageValidationError(f"{path} must contain a JSON object")
    return value


def _validator(schema_name: str) -> Draft202012Validator:
    schema = _read_json(SCHEMA_ROOT / schema_name)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise PackageValidationError(f"invalid trusted schema {schema_name}: {exc}") from exc
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_schema(validator: Draft202012Validator, value: object, label: str) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda error: tuple(str(part) for part in error.absolute_path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.absolute_path) or "$"
    raise PackageValidationError(f"{label} schema violation at {path}: {error.message}")


def _expand_ranges(ranges: Iterable[dict]) -> set[int]:
    pages: set[int] = set()
    for page_range in ranges:
        first, last = page_range["first"], page_range["last"]
        if first > last:
            raise PackageValidationError(f"invalid page range {first}-{last}")
        expanded = set(range(first, last + 1))
        if pages & expanded:
            raise PackageValidationError(f"page range {first}-{last} overlaps an earlier range")
        pages.update(expanded)
    return pages


def _walk_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)


def _without_digest(document: dict) -> dict:
    return {key: value for key, value in document.items() if key != "digest"}


def document_digest(document: dict) -> str:
    """Return the digest a document must declare, excluding the digest field itself."""
    return content_digest(_without_digest(document))


def _load_source_lock(ruleset_id: str) -> dict:
    registry = _read_json(SOURCE_LOCKS_PATH)
    _validate_schema(_validator("regelwerk-source-locks-v1.schema.json"), registry, "source locks")
    by_id: dict[str, dict] = {}
    for source in registry["sources"]:
        if source["rulesetId"] in by_id:
            raise PackageValidationError(f"source lock {source['rulesetId']} is declared twice")
        by_id[source["rulesetId"]] = source
    try:
        return by_id[ruleset_id]
    except KeyError:
        raise PackageValidationError(f"ruleset {ruleset_id} has no approved source lock") from None


def _validate_source_lock(manifest: dict, package_dir: Path) -> str:
    source_lock = _load_source_lock(manifest["rulesetId"])
    source = manifest["source"]
    license_info = manifest["license"]
    expected_source = {
        "title": source_lock["sourceTitle"],
        "publicationDate": source_lock["sourcePublicationDate"],
        "retrievedAt": source_lock["retrievedAt"],
        "url": source_lock["sourceUrl"],
        "sha256": source_lock["sourceSha256"],
        "pageCount": source_lock["sourcePageCount"],
    }
    expected_license = {
        "id": source_lock["licenseId"],
        "url": source_lock["licenseUrl"],
        "attributionFile": source_lock["attributionFile"],
        "attributionSha256": source_lock["attributionSha256"],
    }
    if source != expected_source:
        raise PackageValidationError("manifest source does not match the approved source lock")
    if license_info != expected_license:
        raise PackageValidationError("manifest license does not match the approved source lock")

    attribution_path = package_dir / source_lock["attributionFile"]
    try:
        attribution_bytes = attribution_path.read_bytes()
    except OSError as exc:
        raise PackageValidationError(f"cannot read attribution file: {exc}") from exc
    actual_hash = hashlib.sha256(attribution_bytes).hexdigest()
    if actual_hash != source_lock["attributionSha256"]:
        raise PackageValidationError("attribution file does not match the approved source lock")
    if not attribution_bytes.strip():
        raise PackageValidationError("attribution file is empty")
    return actual_hash


def _validate_coverage_contract(manifest: dict) -> tuple[set[int], set[int], list[dict]]:
    coverage = manifest["coverage"]
    page_count = manifest["source"]["pageCount"]
    required = _expand_ranges(coverage["requiredPageRanges"])
    excluded = _expand_ranges(coverage["excludedPageRanges"])
    all_pages = set(range(1, page_count + 1))
    if required & excluded:
        raise PackageValidationError("required and excluded source pages overlap")
    if required | excluded != all_pages:
        raise PackageValidationError("coverage ranges must account for every source page exactly once")

    reviewed = _expand_ranges(coverage["reviewedPageRanges"])
    if not reviewed <= required:
        raise PackageValidationError("reviewed source pages must be inside required content")

    sections = coverage["expectedTopLevelSections"]
    section_ids: set[str] = set()
    section_pages: set[int] = set()
    for section in sections:
        section_id = section["sectionId"]
        if section_id in section_ids:
            raise PackageValidationError(f"top-level section {section_id} is declared twice")
        section_ids.add(section_id)
        first, last = section["firstPage"], section["lastPage"]
        if first > last:
            raise PackageValidationError(f"invalid section page range {section_id}: {first}-{last}")
        pages = set(range(first, last + 1))
        if not pages <= required:
            raise PackageValidationError(f"section {section_id} includes pages outside required content")
        if section_pages & pages:
            raise PackageValidationError(f"section {section_id} overlaps another top-level section")
        section_pages |= pages
    if section_pages != required:
        raise PackageValidationError("top-level sections must partition all required content pages")
    return required, reviewed, sections


def _validate_document_semantics(document: dict, manifest: dict) -> set[str]:
    document_id = document["documentId"]
    if document["rulesetId"] != manifest["rulesetId"]:
        raise PackageValidationError(f"document {document_id} belongs to another ruleset")
    if document["sourcePages"] != sorted(document["sourcePages"]):
        raise PackageValidationError(f"document {document_id} source pages must be sorted")
    if any(_HTML_TAG.search(text) for text in _walk_strings(document)):
        raise PackageValidationError(f"document {document_id} contains arbitrary HTML markup")

    rule_ids: set[str] = set()
    for block in document["blocks"]:
        rule_id = block["ruleId"]
        if rule_id in rule_ids:
            raise PackageValidationError(f"document {document_id} repeats rule ID {rule_id}")
        if rule_id != document_id and not rule_id.startswith(document_id + "."):
            raise PackageValidationError(f"rule ID {rule_id} is outside document {document_id}")
        rule_ids.add(rule_id)
        if block["type"] == "table":
            width = len(block["columns"])
            if any(len(row) != width for row in block["rows"]):
                raise PackageValidationError(f"table {rule_id} has a row with the wrong column count")
    return rule_ids


def _brand_pattern() -> re.Pattern:
    try:
        lines = BRAND_DENYLIST_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PackageValidationError(f"cannot read brand denylist: {exc}") from exc
    terms = sorted({line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")}, key=len, reverse=True)
    if not terms:
        raise PackageValidationError("brand denylist is empty")
    return re.compile("|".join(rf"(?<!\w){re.escape(term)}(?!\w)" for term in terms), re.IGNORECASE)


def _fold(value: str) -> str:
    return " ".join(value.casefold().split())


def _srd_entity_names() -> set[str]:
    compendium = _read_json(SRD_COMPENDIUM_PATH)
    return {_fold(entity["name"]) for entity in compendium["entities"] if entity.get("type") in _SRD_NAME_TYPES}


def _validate_original_documents(documents: list[dict]) -> None:
    brand = _brand_pattern()
    srd_names = _srd_entity_names()
    for document in documents:
        document_id = document["documentId"]
        if document["contentStatus"] != "original":
            raise PackageValidationError(f"document {document_id} in an original package must be original text")
        for text in _walk_strings(document):
            match = brand.search(text)
            if match:
                raise PackageValidationError(f"document {document_id} uses the third-party brand term {match.group(0)!r}")
        for block in document["blocks"]:
            if block["type"] == "heading" and block["level"] <= 4 and _fold(block["text"]) in srd_names:
                raise PackageValidationError(f"document {document_id} reuses the SRD name {block['text']!r}")


def validate_package(package_dir: str | Path, *, expected_digest: str | None = None) -> ValidationReport:
    """Validate one package and return deterministic identity and coverage evidence."""
    package_path = Path(package_dir).resolve()
    manifest_path = package_path / "manifest.json"
    manifest = _read_json(manifest_path)
    _validate_schema(_validator("regelwerk-package-v1.schema.json"), manifest, "manifest")
    if package_path.name != manifest["rulesetId"]:
        raise PackageValidationError("package directory must match rulesetId")
    is_original = manifest.get("kind", "srd") == "original"
    if is_original and "routeKey" not in manifest:
        raise PackageValidationError("original packages must declare a routeKey")

    attribution_sha256 = _validate_source_lock(manifest, package_path)
    required_pages, reviewed_pages, sections = _validate_coverage_contract(manifest)
    document_validator = _validator("regelwerk-document-v1.schema.json")

    manifest_entries: dict[str, dict] = {}
    used_slugs: set[str] = set()
    for entry in manifest["documents"]:
        document_id = entry["documentId"]
        if document_id in manifest_entries:
            raise PackageValidationError(f"manifest repeats document {document_id}")
        slugs = {entry["slug"], *entry.get("aliases", [])}
        duplicate_slugs = used_slugs & slugs
        if duplicate_slugs:
            raise PackageValidationError(f"manifest repeats slug {sorted(duplicate_slugs)[0]}")
        used_slugs |= slugs
        manifest_entries[document_id] = entry

    documents_dir = package_path / "documents"
    actual_files = {path.stem: path for path in documents_dir.glob("*.json")} if documents_dir.is_dir() else {}
    if set(actual_files) != set(manifest_entries):
        missing = sorted(set(manifest_entries) - set(actual_files))
        unlisted = sorted(set(actual_files) - set(manifest_entries))
        raise PackageValidationError(f"manifest/document inventory mismatch: missing={missing}, unlisted={unlisted}")

    represented_pages: set[int] = set()
    all_rule_ids: set[str] = set()
    documents: list[dict] = []
    for document_id, entry in manifest_entries.items():
        path = actual_files[document_id]
        if path.stat().st_size > MAX_DOCUMENT_BYTES:
            raise PackageValidationError(f"document {document_id} exceeds {MAX_DOCUMENT_BYTES} bytes")
        document = _read_json(path)
        _validate_schema(document_validator, document, f"document {document_id}")
        if document["documentId"] != document_id:
            raise PackageValidationError(f"document file {document_id}.json declares another documentId")
        for field in ("slug", "title"):
            if document[field] != entry[field]:
                raise PackageValidationError(f"document {document_id} {field} differs from manifest")
        actual_digest = document_digest(document)
        if document["digest"] != actual_digest or entry["digest"] != actual_digest:
            raise PackageValidationError(f"document {document_id} digest mismatch")
        rule_ids = _validate_document_semantics(document, manifest)
        duplicate_rule_ids = all_rule_ids & rule_ids
        if duplicate_rule_ids:
            raise PackageValidationError(f"package repeats rule ID {sorted(duplicate_rule_ids)[0]}")
        all_rule_ids |= rule_ids
        represented_pages.update(document["sourcePages"])
        documents.append(document)

    if is_original:
        _validate_original_documents(documents)

    unexpected_pages = represented_pages - required_pages
    if unexpected_pages:
        raise PackageValidationError("documents cover excluded or unknown source pages")
    unrepresented_reviews = reviewed_pages - represented_pages
    if unrepresented_reviews:
        raise PackageValidationError("reviewed source pages must be represented by a document")

    for document in documents:
        for reference in document["ruleRefs"]:
            if reference["rulesetId"] == manifest["rulesetId"] and reference["ruleId"] not in all_rule_ids:
                raise PackageValidationError(
                    f"document {document['documentId']} references missing rule ID {reference['ruleId']}"
                )

    covered_sections = []
    missing_sections = []
    for section in sections:
        pages = set(range(section["firstPage"], section["lastPage"] + 1))
        target = covered_sections if pages <= reviewed_pages else missing_sections
        target.append(section["sectionId"])
    coverage = CoverageReport(
        required_pages=tuple(sorted(required_pages)),
        represented_pages=tuple(sorted(represented_pages)),
        covered_pages=tuple(sorted(reviewed_pages)),
        missing_pages=tuple(sorted(required_pages - reviewed_pages)),
        unexpected_pages=tuple(sorted(unexpected_pages)),
        covered_sections=tuple(covered_sections),
        missing_sections=tuple(missing_sections),
    )

    if manifest["status"] in {"published", "retired"} and not coverage.complete:
        raise PackageValidationError(f"{manifest['status']} package must have complete source coverage")

    package_digest = content_digest(
        {
            "manifest": manifest,
            "documentDigests": [document["digest"] for document in documents],
        }
    )
    if expected_digest is not None and package_digest != expected_digest:
        raise PackageValidationError(
            f"package digest changed: expected {expected_digest}, got {package_digest}"
        )
    return ValidationReport(
        ruleset_id=manifest["rulesetId"],
        ruleset_version=manifest["rulesetVersion"],
        status=manifest["status"],
        package_digest=package_digest,
        document_count=len(documents),
        attribution_sha256=attribution_sha256,
        coverage=coverage,
    )
