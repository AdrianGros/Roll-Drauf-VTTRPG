"""Deterministic derived artifacts for a validated Regelwerk package."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable

from vtt.creation_engine.canonical import parse_strict_json

from .validator import CONTENT_ROOT, ValidationReport, validate_package


DEFAULT_PACKAGE = CONTENT_ROOT / "srd-5.2.1-de"
GENERATED_FILENAMES = ("navigation.json", "search-index.json", "coverage.json", "compendium.json", "creator-data.json")
# Compendium and creator data parse the SRD's structure; an original book gets reader artifacts only.
ORIGINAL_GENERATED_FILENAMES = ("navigation.json", "search-index.json", "coverage.json")
_SOURCE_VERSION = re.compile(r"\b(\d+\.\d+(?:\.\d+)?)\b")


def _read_json(path: Path) -> dict:
    value = parse_strict_json(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def normalized_search_text(value: object) -> str:
    """Normalize authored text for deterministic, locale-safe substring search."""
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(normalized.split())


def _source_version(manifest: dict) -> str:
    match = _SOURCE_VERSION.search(manifest["source"]["title"])
    if not match:
        raise ValueError("source title does not contain a version")
    return match.group(1)


def is_original(manifest: dict) -> bool:
    return manifest.get("kind", "srd") == "original"


def _route_key(manifest: dict) -> str:
    return manifest["routeKey"] if is_original(manifest) else _source_version(manifest)


def _route_locale(manifest: dict) -> str:
    return manifest["locale"].split("-", 1)[0]


def reader_url(manifest: dict) -> str:
    return f"/regelwerk/{manifest['routeKey']}" if is_original(manifest) else "/regelwerk"


def document_url(manifest: dict, document: dict, rule_id: str | None = None) -> str:
    path = f"/regelwerk/{_route_key(manifest)}/{_route_locale(manifest)}/{document['slug']}"
    return f"{path}#{rule_id}" if rule_id else path


def _block_text(block: dict) -> str:
    block_type = block["type"]
    if block_type == "heading":
        return block["text"]
    if block_type == "paragraph":
        return block["text"]
    if block_type in {"ordered-list", "unordered-list"}:
        return " ".join(block["items"])
    if block_type == "definition-list":
        return " ".join(
            f"{entry['term']} {entry['definition']}" for entry in block["entries"]
        )
    if block_type == "table":
        cells: Iterable[str] = (
            [block["caption"], *block["columns"]]
            + [cell for row in block["rows"] for cell in row]
        )
        return " ".join(cells)
    if block_type in {"rule-callout", "page-note"}:
        return " ".join(value for value in (block.get("title"), block["text"]) if value)
    if block_type == "stat-block":
        parts = [block["name"]]
        parts.extend(f"{entry['label']} {entry['value']}" for entry in block["entries"])
        parts.extend(f"{section['title']} {section['text']}" for section in block["sections"])
        return " ".join(parts)
    if block_type == "original-note":
        return " ".join(value for value in (block.get("title"), block["text"]) if value)
    raise ValueError(f"unsupported block type {block_type}")


def load_validated_package(package_dir: str | Path = DEFAULT_PACKAGE) -> tuple[dict, list[dict], ValidationReport]:
    package_path = Path(package_dir).resolve()
    report = validate_package(package_path)
    manifest = _read_json(package_path / "manifest.json")
    documents = [
        _read_json(package_path / "documents" / f"{entry['documentId']}.json")
        for entry in manifest["documents"]
    ]
    documents.sort(key=lambda item: (item["order"], item["documentId"]))
    return manifest, documents, report


def _navigation(manifest: dict, documents: list[dict], report: ValidationReport) -> dict:
    grouped: dict[str, list[dict]] = {}
    for document in documents:
        section_title = document["navigationPath"][0]
        grouped.setdefault(section_title, []).append(
            {
                "documentId": document["documentId"],
                "slug": document["slug"],
                "title": document["title"],
                "navigationPath": document["navigationPath"],
                "order": document["order"],
                "url": document_url(manifest, document),
            }
        )
    sections = []
    for expected in manifest["coverage"]["expectedTopLevelSections"]:
        section_documents = grouped.get(expected["title"], [])
        if section_documents:
            sections.append(
                {
                    "sectionId": expected["sectionId"],
                    "title": expected["title"],
                    "documents": section_documents,
                }
            )
    navigation = {
        "schemaVersion": "regelwerk.navigation.v1",
        "rulesetId": manifest["rulesetId"],
        "rulesetVersion": manifest["rulesetVersion"],
        "sourceVersion": manifest["rulesetVersion"] if is_original(manifest) else _source_version(manifest),
        "locale": manifest["locale"],
        "status": manifest["status"],
        "title": manifest["title"],
        "packageDigest": report.package_digest,
        "readerUrl": reader_url(manifest),
        "licenseUrl": f"{reader_url(manifest)}/lizenz",
        "sections": sections,
    }
    if is_original(manifest):
        navigation["kind"] = "original"
        navigation["routeKey"] = manifest["routeKey"]
    return navigation


def _search_index(manifest: dict, documents: list[dict], report: ValidationReport) -> dict:
    entries = []
    for document in documents:
        heading_stack: list[tuple[int, str]] = []
        for position, block in enumerate(document["blocks"]):
            if block["type"] == "heading":
                level = block["level"]
                heading_stack = [item for item in heading_stack if item[0] < level]
                heading_stack.append((level, block["text"]))
            heading = heading_stack[-1][1] if heading_stack else document["title"]
            text = _block_text(block)
            entries.append(
                {
                    "documentId": document["documentId"],
                    "ruleId": block["ruleId"],
                    "title": document["title"],
                    "heading": heading,
                    "headingPath": [item[1] for item in heading_stack],
                    "text": text,
                    "normalizedText": normalized_search_text(
                        " ".join([document["title"], heading, text])
                    ),
                    "url": document_url(manifest, document, block["ruleId"]),
                    "order": [document["order"], position],
                }
            )
    return {
        "schemaVersion": "regelwerk.search-index.v1",
        "rulesetId": manifest["rulesetId"],
        "rulesetVersion": manifest["rulesetVersion"],
        "packageDigest": report.package_digest,
        "entries": entries,
    }


def generate_artifacts(package_dir: str | Path = DEFAULT_PACKAGE) -> dict[str, dict]:
    from .compendium import build_compendium
    from .creator_data import build_creator_data

    manifest, documents, report = load_validated_package(package_dir)
    if is_original(manifest):
        coverage = report.coverage.to_wire()
        coverage.update({
            "schemaVersion": "regelwerk.coverage.v1",
            "rulesetId": manifest["rulesetId"],
            "rulesetVersion": manifest["rulesetVersion"],
            "packageDigest": report.package_digest,
        })
        return {
            "navigation.json": _navigation(manifest, documents, report),
            "search-index.json": _search_index(manifest, documents, report),
            "coverage.json": coverage,
        }
    compendium = build_compendium(manifest, documents)
    compendium["packageDigest"] = report.package_digest
    creator_data = build_creator_data(manifest, documents, compendium)
    creator_data["packageDigest"] = report.package_digest
    coverage = report.coverage.to_wire()
    coverage.update(
        {
            "schemaVersion": "regelwerk.coverage.v1",
            "rulesetId": manifest["rulesetId"],
            "rulesetVersion": manifest["rulesetVersion"],
            "packageDigest": report.package_digest,
        }
    )
    return {
        "navigation.json": _navigation(manifest, documents, report),
        "search-index.json": _search_index(manifest, documents, report),
        "coverage.json": coverage,
        "compendium.json": compendium,
        "creator-data.json": creator_data,
    }


def encode_artifact(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_artifacts(package_dir: str | Path = DEFAULT_PACKAGE) -> tuple[Path, ...]:
    package_path = Path(package_dir).resolve()
    generated_dir = package_path / "generated"
    generated_dir.mkdir(exist_ok=True)
    written = []
    for filename, value in generate_artifacts(package_path).items():
        path = generated_dir / filename
        path.write_text(encode_artifact(value), encoding="utf-8")
        written.append(path)
    return tuple(written)


def stale_artifacts(package_dir: str | Path = DEFAULT_PACKAGE) -> tuple[str, ...]:
    package_path = Path(package_dir).resolve()
    expected = generate_artifacts(package_path)
    stale = []
    for filename, value in expected.items():
        path = package_path / "generated" / filename
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            stale.append(filename)
            continue
        if actual != encode_artifact(value):
            stale.append(filename)
    return tuple(stale)
