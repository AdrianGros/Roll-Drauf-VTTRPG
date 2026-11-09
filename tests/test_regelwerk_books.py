"""Own books in the Regelwerk reader: routes, API and the on/off switch.

The SRD stays the main book at /regelwerk; Oglans Book of Chaos is served at
/regelwerk/oglan with its own manifest, documents, search and license, and
disappears completely when its switch is off.
"""

from __future__ import annotations

import json

import pytest

from vtt import create_app
from vtt.rules_content import validate_package
from vtt.rules_content.generator import stale_artifacts
from vtt.rules_content.validator import CONTENT_ROOT

BOOK = "oglans-book-of-chaos-de"
PACKAGE = CONTENT_ROOT / BOOK
NAVIGATION = json.loads((PACKAGE / "generated" / "navigation.json").read_text(encoding="utf-8"))
FIRST = NAVIGATION["sections"][0]["documents"][0]


@pytest.fixture
def app():
    return create_app(config_name="testing")


@pytest.fixture
def client(app):
    return app.test_client()


def test_the_checked_in_book_is_valid_and_its_artifacts_are_current():
    report = validate_package(PACKAGE)
    assert report.status == "preview"
    assert stale_artifacts(PACKAGE) == ()


def test_book_list_names_the_srd_first_and_the_own_book(client):
    books = client.get("/api/rulesets").get_json()["rulesets"]
    assert [book["rulesetId"] for book in books] == ["srd-5.2.1-de", BOOK]
    own = books[1]
    assert own["kind"] == "original" and own["readerUrl"] == "/regelwerk/oglan" and own["status"] == "preview"


@pytest.mark.parametrize("path", ["/regelwerk/oglan", "/regelwerk/oglan/lizenz", FIRST["url"]])
def test_reader_pages_of_the_book_are_served_anonymously(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b'id="regelwerkBooks"' in response.data


@pytest.mark.parametrize("path", ["/regelwerk/unbekannt", "/regelwerk/oglan/de/gibt-es-nicht", "/regelwerk/oglan/en/" + FIRST["slug"]])
def test_unknown_book_coordinates_404(client, path):
    assert client.get(path).status_code == 404


def test_book_api_serves_manifest_document_search_and_license(client):
    manifest = client.get(f"/api/rulesets/{BOOK}/manifest").get_json()
    assert manifest == NAVIGATION
    document = client.get(f"/api/rulesets/{BOOK}/documents/{FIRST['documentId']}").get_json()
    assert document["rulesetId"] == BOOK and document["contentStatus"] == "original"
    word = document["title"].split()[0]
    results = client.get(f"/api/rulesets/{BOOK}/search", query_string={"q": word}).get_json()["results"]
    assert results and all(result["url"].startswith("/regelwerk/oglan/de/") for result in results)
    license_payload = client.get(f"/api/rulesets/{BOOK}/license").get_json()
    assert license_payload["kind"] == "original"
    assert "Roll Drauf" in license_payload["attribution"] and "SRD 5.2.1" in license_payload["attribution"]


def test_the_srd_api_is_still_the_srd(client):
    assert client.get("/api/rulesets/srd-5.2.1-de/manifest").get_json()["rulesetId"] == "srd-5.2.1-de"
    assert client.get("/api/rulesets/main").get_json()["rulesetId"] == "srd-5.2.1-de"


def test_unknown_ruleset_api_404s(client):
    assert client.get("/api/rulesets/kein-buch/manifest").status_code == 404


def test_switching_the_book_off_removes_it_everywhere(app, client):
    app.config["OGLAN_BOOK"] = False
    for path in ("/regelwerk/oglan", "/regelwerk/oglan/lizenz", FIRST["url"]):
        assert client.get(path).status_code == 404
    for path in ("manifest", f"documents/{FIRST['documentId']}", "search?q=zauber", "license"):
        assert client.get(f"/api/rulesets/{BOOK}/{path}").status_code == 404
    assert [book["rulesetId"] for book in client.get("/api/rulesets").get_json()["rulesets"]] == ["srd-5.2.1-de"]
    assert client.get("/regelwerk").status_code == 200
