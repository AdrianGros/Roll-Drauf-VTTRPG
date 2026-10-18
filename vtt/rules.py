"""Public, read-only Regelwerk routes (published package, or preview behind a flag)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, request, send_from_directory

from vtt.rules_content.generator import DEFAULT_PACKAGE, normalized_search_text


rules_bp = Blueprint("rules", __name__)
_PACKAGE = Path(DEFAULT_PACKAGE)
_GENERATED = _PACKAGE / "generated"
_TEMPLATES = Path(__file__).resolve().parent / "templates"
_RULESET_ID = "srd-5.2.1-de"
_SOURCE_VERSION = "5.2.1"
_ROUTE_LOCALE = "de"


def _package_status() -> str:
    return _load_json(_PACKAGE / "manifest.json")["status"]


def _enabled() -> bool:
    if _package_status() == "published":
        return True
    return bool(current_app.config.get("REGELWERK_PREVIEW", False))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _navigation() -> dict:
    return _load_json(_GENERATED / "navigation.json")


def _manifest() -> dict:
    return _load_json(_PACKAGE / "manifest.json")


def _etag_for(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _public_json(payload: dict, *, etag: str | None = None, status: int = 200):
    response = jsonify(payload)
    response.status_code = status
    response.cache_control.public = True
    response.cache_control.max_age = 60
    response.set_etag(etag or _etag_for(payload))
    return response.make_conditional(request)


def _json_not_found():
    return _public_json({"error": "not found"}, status=404)


def _document_entry_by_slug(slug: str) -> dict | None:
    for section in _navigation()["sections"]:
        for entry in section["documents"]:
            if entry["slug"] == slug:
                return entry
    return None


def _reader_shell():
    response = send_from_directory(_TEMPLATES, "regelwerk.html")
    response.cache_control.public = True
    response.cache_control.max_age = 60
    return response


@rules_bp.get("/regelwerk")
def reader_home():
    if not _enabled():
        abort(404)
    return _reader_shell()


@rules_bp.get("/regelwerk/lizenz")
def reader_license():
    if not _enabled():
        abort(404)
    return _reader_shell()


@rules_bp.get("/regelwerk/<source_version>/<locale>/<slug>")
def reader_document(source_version: str, locale: str, slug: str):
    if (
        not _enabled()
        or source_version != _SOURCE_VERSION
        or locale != _ROUTE_LOCALE
        or _document_entry_by_slug(slug) is None
    ):
        abort(404)
    return _reader_shell()


@rules_bp.get("/api/rulesets/main")
def main_ruleset():
    if not _enabled():
        return _public_json({"available": False})
    navigation = _navigation()
    payload = {
        "available": True,
        "rulesetId": navigation["rulesetId"],
        "rulesetVersion": navigation["rulesetVersion"],
        "sourceVersion": navigation["sourceVersion"],
        "locale": navigation["locale"],
        "status": navigation["status"],
        "title": navigation["title"],
        "readerUrl": navigation["readerUrl"],
    }
    return _public_json(payload, etag=navigation["packageDigest"].removeprefix("sha256:"))


@rules_bp.get(f"/api/rulesets/{_RULESET_ID}/manifest")
def public_manifest():
    if not _enabled():
        return _json_not_found()
    navigation = _navigation()
    return _public_json(
        navigation,
        etag=navigation["packageDigest"].removeprefix("sha256:"),
    )


@rules_bp.get(f"/api/rulesets/{_RULESET_ID}/documents/<document_id>")
def public_document(document_id: str):
    if not _enabled():
        return _json_not_found()
    manifest = _manifest()
    entry = next((item for item in manifest["documents"] if item["documentId"] == document_id), None)
    if entry is None:
        return _json_not_found()
    path = _PACKAGE / "documents" / f"{document_id}.json"
    try:
        document = _load_json(path)
    except (OSError, ValueError):
        return _json_not_found()
    return _public_json(document, etag=entry["digest"].removeprefix("sha256:"))


@rules_bp.get(f"/api/rulesets/{_RULESET_ID}/search")
def public_search():
    if not _enabled():
        return _json_not_found()
    query = request.args.get("q", "")
    if len(query) > 100:
        return _public_json({"error": "query must be at most 100 characters"}, status=400)
    normalized = normalized_search_text(query)
    results = []
    if len(normalized) >= 2:
        index = _load_json(_GENERATED / "search-index.json")
        tokens = normalized.split()
        matches = []
        for entry in index["entries"]:
            haystack = entry["normalizedText"]
            if not all(token in haystack for token in tokens):
                continue
            heading = normalized_search_text(entry["heading"])
            title = normalized_search_text(entry["title"])
            score = (
                int(normalized == heading) * 8
                + int(heading.startswith(normalized)) * 4
                + int(normalized == title) * 3
                + int(normalized in haystack) * 2
            )
            matches.append((-score, entry["order"], entry))
        matches.sort(key=lambda item: (item[0], item[1], item[2]["ruleId"]))
        for _, _, entry in matches[:20]:
            text = entry["text"].strip()
            snippet = text if len(text) <= 220 else text[:217].rstrip() + "…"
            results.append(
                {
                    "documentId": entry["documentId"],
                    "ruleId": entry["ruleId"],
                    "title": entry["title"],
                    "heading": entry["heading"],
                    "snippet": snippet,
                    "url": entry["url"],
                }
            )
    payload = {"query": query, "results": results}
    return _public_json(payload)


@rules_bp.get(f"/api/rulesets/{_RULESET_ID}/license")
def public_license():
    if not _enabled():
        return _json_not_found()
    manifest = _manifest()
    attribution = (_PACKAGE / manifest["license"]["attributionFile"]).read_text(encoding="utf-8")
    payload = {
        "rulesetId": manifest["rulesetId"],
        "source": manifest["source"],
        "license": manifest["license"],
        "attribution": attribution,
    }
    return _public_json(payload, etag=manifest["license"]["attributionSha256"])
