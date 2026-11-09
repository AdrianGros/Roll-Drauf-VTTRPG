"""Public, read-only Regelwerk routes (published package, or preview behind a flag).

Besides the SRD, the reader serves Roll Drauf's own books (`original` packages)
under /regelwerk/<routeKey>. Each has an on/off switch (app config or
environment, default on) so a book can be withdrawn without touching the SRD.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, request, send_from_directory

from vtt.rules_content.compendium import CompendiumQueryError, entry_excerpt, query_compendium
from vtt.rules_content.generator import DEFAULT_PACKAGE, normalized_search_text
from vtt.rules_content.validator import CONTENT_ROOT


rules_bp = Blueprint("rules", __name__)
_PACKAGE = Path(DEFAULT_PACKAGE)
_GENERATED = _PACKAGE / "generated"
_TEMPLATES = Path(__file__).resolve().parent / "templates"
_RULESET_ID = "srd-5.2.1-de"
_SOURCE_VERSION = "5.2.1"
_ROUTE_LOCALE = "de"
# Own books: rulesetId -> name of the on/off switch.
_EXTRA_BOOKS = {"oglans-book-of-chaos-de": "OGLAN_BOOK"}
_OFF = {"0", "false", "no", "off"}


def _package_status() -> str:
    return _load_json(_PACKAGE / "manifest.json")["status"]


def _enabled() -> bool:
    if _package_status() == "published":
        return True
    return bool(current_app.config.get("REGELWERK_PREVIEW", False))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


_COMPENDIUM_CACHE: dict[str, tuple[int, dict]] = {}


def _compendium() -> dict:
    path = _GENERATED / "compendium.json"
    stamp = path.stat().st_mtime_ns
    cached = _COMPENDIUM_CACHE.get("data")
    if cached is None or cached[0] != stamp:
        cached = _COMPENDIUM_CACHE["data"] = (stamp, _load_json(path))
    return cached[1]


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


def _document_entry_by_slug(slug: str, navigation: dict | None = None) -> dict | None:
    for section in (navigation or _navigation())["sections"]:
        for entry in section["documents"]:
            if entry["slug"] == slug:
                return entry
    return None


def _book_package(ruleset_id: str) -> Path:
    return CONTENT_ROOT / ruleset_id


def _book_enabled(ruleset_id: str) -> bool:
    switch = _EXTRA_BOOKS.get(ruleset_id)
    if switch is None or not (_book_package(ruleset_id) / "generated" / "navigation.json").is_file():
        return False
    value = current_app.config.get(switch)
    if value is None:
        value = os.getenv(switch, "1").strip().lower() not in _OFF
    return bool(value)


def _book_navigation(ruleset_id: str) -> dict:
    return _load_json(_book_package(ruleset_id) / "generated" / "navigation.json")


def _book_by_route_key(route_key: str) -> str | None:
    for ruleset_id in _EXTRA_BOOKS:
        if _book_enabled(ruleset_id) and _book_navigation(ruleset_id).get("routeKey") == route_key:
            return ruleset_id
    return None


def _search_results(index_path: Path, query: str) -> list[dict]:
    normalized = normalized_search_text(query)
    results = []
    if len(normalized) >= 2:
        index = _load_json(index_path)
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
    return results


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


@rules_bp.get("/regelwerk/compendium")
def reader_compendium():
    if not _enabled():
        abort(404)
    response = send_from_directory(_TEMPLATES, "regelwerk-compendium.html")
    response.cache_control.public = True
    response.cache_control.max_age = 60
    return response


@rules_bp.get("/regelwerk/lizenz")
def reader_license():
    if not _enabled():
        abort(404)
    return _reader_shell()


@rules_bp.get("/regelwerk/<route_key>")
@rules_bp.get("/regelwerk/<route_key>/lizenz")
def reader_book_home(route_key: str):
    if _book_by_route_key(route_key) is None:
        abort(404)
    return _reader_shell()


@rules_bp.get("/regelwerk/<source_version>/<locale>/<slug>")
def reader_document(source_version: str, locale: str, slug: str):
    if source_version != _SOURCE_VERSION:
        ruleset_id = _book_by_route_key(source_version)
        if (
            ruleset_id is None
            or locale != _ROUTE_LOCALE
            or _document_entry_by_slug(slug, _book_navigation(ruleset_id)) is None
        ):
            abort(404)
        return _reader_shell()
    if (
        not _enabled()
        or locale != _ROUTE_LOCALE
        or _document_entry_by_slug(slug) is None
    ):
        abort(404)
    return _reader_shell()


@rules_bp.get("/api/rulesets")
def list_rulesets():
    books = []
    if _enabled():
        navigation = _navigation()
        books.append({"rulesetId": navigation["rulesetId"], "kind": "srd", "title": navigation["title"],
                      "status": navigation["status"], "readerUrl": navigation["readerUrl"]})
    for ruleset_id in _EXTRA_BOOKS:
        if _book_enabled(ruleset_id):
            navigation = _book_navigation(ruleset_id)
            books.append({"rulesetId": ruleset_id, "kind": "original", "title": navigation["title"],
                          "status": navigation["status"], "readerUrl": navigation["readerUrl"]})
    return _public_json({"rulesets": books})


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
    results = _search_results(_GENERATED / "search-index.json", query)
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


@rules_bp.get(f"/api/rulesets/{_RULESET_ID}/compendium")
def public_compendium():
    if not _enabled():
        return _json_not_found()
    data = _compendium()
    try:
        payload = query_compendium(data, request.args.to_dict())
    except CompendiumQueryError as error:
        return _public_json({"error": str(error)}, status=400)
    payload["rulesetVersion"] = data["rulesetVersion"]
    return _public_json(payload)


@rules_bp.get(f"/api/rulesets/{_RULESET_ID}/compendium/entry/<path:entity_id>")
def public_compendium_entry(entity_id: str):
    if not _enabled():
        return _json_not_found()
    data = _compendium()
    entity = next((item for item in data["entities"] if item["id"] == entity_id), None)
    if entity is None:
        return _json_not_found()
    try:
        document = _load_json(_PACKAGE / "documents" / f"{entity['documentId']}.json")
        blocks = entry_excerpt(document, entity)
    except (OSError, ValueError, KeyError):
        return _json_not_found()
    return _public_json({"entity": entity, "blocks": blocks, "rulesetVersion": data["rulesetVersion"]})


@rules_bp.get(f"/api/rulesets/{_RULESET_ID}/compendium/summary")
def public_compendium_summary():
    if not _enabled():
        return _json_not_found()
    data = _compendium()
    return _public_json({"counts": data["counts"], "rulesetVersion": data["rulesetVersion"]})


# ---------------------------------------------------------------------------
# Own books. The SRD routes above are literal paths and win over these.
# ---------------------------------------------------------------------------


@rules_bp.get("/api/rulesets/<ruleset_id>/manifest")
def book_manifest(ruleset_id: str):
    if not _book_enabled(ruleset_id):
        return _json_not_found()
    navigation = _book_navigation(ruleset_id)
    return _public_json(navigation, etag=navigation["packageDigest"].removeprefix("sha256:"))


@rules_bp.get("/api/rulesets/<ruleset_id>/documents/<document_id>")
def book_document(ruleset_id: str, document_id: str):
    if not _book_enabled(ruleset_id):
        return _json_not_found()
    package = _book_package(ruleset_id)
    manifest = _load_json(package / "manifest.json")
    entry = next((item for item in manifest["documents"] if item["documentId"] == document_id), None)
    if entry is None:
        return _json_not_found()
    try:
        document = _load_json(package / "documents" / f"{document_id}.json")
    except (OSError, ValueError):
        return _json_not_found()
    return _public_json(document, etag=entry["digest"].removeprefix("sha256:"))


@rules_bp.get("/api/rulesets/<ruleset_id>/search")
def book_search(ruleset_id: str):
    if not _book_enabled(ruleset_id):
        return _json_not_found()
    query = request.args.get("q", "")
    if len(query) > 100:
        return _public_json({"error": "query must be at most 100 characters"}, status=400)
    results = _search_results(_book_package(ruleset_id) / "generated" / "search-index.json", query)
    return _public_json({"query": query, "results": results})


@rules_bp.get("/api/rulesets/<ruleset_id>/license")
def book_license(ruleset_id: str):
    if not _book_enabled(ruleset_id):
        return _json_not_found()
    package = _book_package(ruleset_id)
    manifest = _load_json(package / "manifest.json")
    attribution = (package / manifest["license"]["attributionFile"]).read_text(encoding="utf-8")
    payload = {
        "rulesetId": manifest["rulesetId"],
        "kind": "original",
        "title": manifest["title"],
        "source": manifest["source"],
        "license": manifest["license"],
        "attribution": attribution,
    }
    return _public_json(payload, etag=manifest["license"]["attributionSha256"])
