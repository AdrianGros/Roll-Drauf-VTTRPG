"""M17.5 tests: campaign hub and session-prep productization.

Scope note (Desktop-Audit F1, 2026-08-26): every assertion here is a
Flask-test-client string match against the raw HTML `GET /campaigns`
returns. That HTML always contained this markup - it just used to be the
page's PRIMARY (book-scene-hidden-via-CSS) render, and after the F1 fix it
is the classic fallback, now wrapped in an inert
<template id="campaignsClassicTemplate"> (see campaigns.html). A raw HTML
string match cannot tell those two states apart: it stayed green the whole
time "Hub öffnen" was hard-navigating players into this exact markup
instead of the book UI (the actual bug), and it stays green now that this
markup is reachable only as a deliberate, rarely-used fallback. These tests
are still worth keeping - they guard the classic fallback's own content
from silently regressing - but they prove NOTHING about which render path
a real click lands on. That is what
tools/robots/flows.py::_campaign_hub_click_flow (a real Playwright click
through the campaigns book page) exists to cover; see its docstring.
"""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_campaign_hub_surfaces_prep_state_more_explicitly(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Prep-Status:" in html
    # Desktop-Audit D12 (2026-08-25): diese Strings waren englisches
    # Chrome-Leck im sichtbaren Hub-Render und wurden auf Deutsch
    # umgestellt (docs/FIX_RESEARCH_DESKTOP_AUDIT_2026-08-25.md §6).
    assert "Kampagnen-Vorbereitung / Session-Hub" in html
    assert "Vorbereitungs-Überblick" in html
    assert "Aktueller Stand:" in html
    assert "Vorbereitungs-Checkliste" in html
    assert "Sessions prüfen" in html


def test_campaign_hub_exposes_clearer_session_action_hierarchy(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Karte + Session vorbereiten" in html
    assert "Erste Session anlegen" in html
    assert "Session starten" in html
    assert "Session fortsetzen" in html
    assert "Session betreten" in html
    assert "Auf Sessionstart warten" in html
    assert "Play erneut öffnen" in html
    assert "Nächste Session anlegen" in html


def test_campaign_hub_connects_map_asset_and_character_prep_surfaces_honestly(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Desktop-Audit D12: siehe Kommentar oben.
    assert "Vorbereitungs-Links" in html
    assert "Charaktere öffnen" in html
    assert "Kartenvorbereitung ansehen" in html
    assert 'id="campaignAssetLibraryPanel"' in html
    assert "Session-Besetzung:" in html
    assert "Session-Besetzung öffnen" in html
    assert "Map Workspace folgt" not in html
    assert "Import / Export folgt hier" not in html
    assert "Karte hochladen" in html


def test_campaign_hub_play_entry_remains_bookscene_seam_owned(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function openPlay(campaignId, sessionId)" in html
    assert "BookScene.enterPlay({" in html
    assert "sourceRoute: 'campaigns'" in html
    assert "window.location.href = `/play" not in html
