"""R1 Regelwerk reader vertical slice: public route and API contracts.

Covers the testable half of the Program R1 acceptance criteria (anonymous
reads, navigation visibility hook, stable deep links, search resolution,
disabled-by-default behaviour, attribution visibility). Browser-level
criteria (keyboard, reduced-motion, narrow-screen, print) need Playwright
and are out of scope here.
"""

from __future__ import annotations

import json

import pytest

from vtt import create_app


KNOWN_SLUG = "w20-pruefungen"
SOURCE_VERSION = "5.2.1"
LOCALE = "de"


@pytest.fixture
def app():
    return create_app(config_name="testing")


@pytest.fixture
def client(app):
    return app.test_client()


def _enable(app):
    app.config["REGELWERK_PREVIEW"] = True


# ---------------------------------------------------------------------------
# Disabled by default
# ---------------------------------------------------------------------------


def test_preview_flag_defaults_off(app):
    assert app.config["REGELWERK_PREVIEW"] is False


@pytest.mark.parametrize(
    "path",
    [
        "/regelwerk",
        "/regelwerk/lizenz",
        f"/regelwerk/{SOURCE_VERSION}/{LOCALE}/{KNOWN_SLUG}",
    ],
)
def test_reader_pages_404_when_disabled(client, path):
    response = client.get(path)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/api/rulesets/srd-5.2.1-de/manifest",
        f"/api/rulesets/srd-5.2.1-de/documents/core.d20-tests",
        "/api/rulesets/srd-5.2.1-de/search?q=prüfung",
        "/api/rulesets/srd-5.2.1-de/license",
    ],
)
def test_ruleset_api_404s_when_disabled(client, path):
    response = client.get(path)
    assert response.status_code == 404


def test_main_ruleset_api_reports_unavailable_when_disabled(client):
    response = client.get("/api/rulesets/main")
    assert response.status_code == 200
    assert response.get_json() == {"available": False}


# ---------------------------------------------------------------------------
# Enabled: public, anonymous reads
# ---------------------------------------------------------------------------


def test_reader_home_serves_anonymously_when_enabled(app, client):
    _enable(app)
    response = client.get("/regelwerk")
    assert response.status_code == 200
    assert b"Vorschau" in response.data


def test_reader_license_page_serves_when_enabled(app, client):
    _enable(app)
    response = client.get("/regelwerk/lizenz")
    assert response.status_code == 200


def test_known_document_deep_link_resolves(app, client):
    _enable(app)
    response = client.get(f"/regelwerk/{SOURCE_VERSION}/{LOCALE}/{KNOWN_SLUG}")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        f"/regelwerk/9.9.9/{LOCALE}/{KNOWN_SLUG}",
        f"/regelwerk/{SOURCE_VERSION}/en/{KNOWN_SLUG}",
        f"/regelwerk/{SOURCE_VERSION}/{LOCALE}/does-not-exist",
    ],
)
def test_unknown_document_coordinates_404(app, client, path):
    _enable(app)
    response = client.get(path)
    assert response.status_code == 404


def test_main_ruleset_api_reports_available_when_enabled(app, client):
    _enable(app)
    response = client.get("/api/rulesets/main")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["available"] is True
    assert payload["rulesetId"] == "srd-5.2.1-de"
    assert payload["readerUrl"] == "/regelwerk"


def test_manifest_api_matches_generated_navigation(app, client):
    _enable(app)
    response = client.get("/api/rulesets/srd-5.2.1-de/manifest")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rulesetId"] == "srd-5.2.1-de"
    slugs = {doc["slug"] for section in payload["sections"] for doc in section["documents"]}
    assert KNOWN_SLUG in slugs


def test_document_api_returns_full_document(app, client):
    _enable(app)
    response = client.get("/api/rulesets/srd-5.2.1-de/documents/core.d20-tests")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["documentId"] == "core.d20-tests"
    assert payload["blocks"]


def test_document_api_404_for_unknown_id(app, client):
    _enable(app)
    response = client.get("/api/rulesets/srd-5.2.1-de/documents/does-not-exist")
    assert response.status_code == 404


def test_search_resolves_known_term(app, client):
    _enable(app)
    response = client.get("/api/rulesets/srd-5.2.1-de/search?q=W20")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["results"]
    assert any(r["documentId"] == "core.d20-tests" for r in payload["results"])


def test_search_rejects_overlong_query(app, client):
    _enable(app)
    response = client.get("/api/rulesets/srd-5.2.1-de/search?q=" + "a" * 101)
    assert response.status_code == 400


def test_search_short_query_returns_no_results_not_an_error(app, client):
    _enable(app)
    response = client.get("/api/rulesets/srd-5.2.1-de/search?q=a")
    assert response.status_code == 200
    assert response.get_json()["results"] == []


def test_license_api_includes_visible_attribution(app, client):
    _enable(app)
    response = client.get("/api/rulesets/srd-5.2.1-de/license")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["attribution"].strip()
    assert payload["license"]["id"] == "CC-BY-4.0"


# ---------------------------------------------------------------------------
# Deep-link stability: the manifest/navigation/API responses carrying the
# slug a browser would reload against stay internally consistent.
# ---------------------------------------------------------------------------


def test_navigation_url_round_trips_to_a_reachable_route(app, client):
    _enable(app)
    manifest = client.get("/api/rulesets/srd-5.2.1-de/manifest").get_json()
    url = manifest["sections"][0]["documents"][0]["url"]
    response = client.get(url)
    assert response.status_code == 200
