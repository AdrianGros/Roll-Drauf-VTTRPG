"""M17.7 tests: map/asset pre-integration and session-prep deepening."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_session_prep_surface_exposes_real_session_map_prep_hooks(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Session-Map setzen" in html
    assert 'id="sessionPrepMapSelect"' in html
    assert "Als Session-Karte setzen" in html
    assert "activatePrepSessionMap(campaignId, sessionId)" in html
    assert "/maps/activate" in html


def test_session_prep_surface_exposes_session_scoped_asset_prep_hooks(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Session-Assets ansehen" in html
    assert "Session-Upload vorbereiten" in html
    assert "Session-Assets werden geladen" in html
    assert "refreshSessionPrepAssetStats(campaignId, sessionId)" in html
    assert "scope=session&session_id=" in html


def test_session_prep_surface_makes_remaining_blockers_clearer(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Noch offen vor Play" in html
    assert "Keine aktive Session-Karte gewählt" in html
    assert "Noch kein Session-Charakter zugewiesen" in html
    assert "Tieferer Map Workspace bleibt vorerst eigener Prep-Schritt" not in html
    assert "Paketierter Import / Export bleibt vorerst Platzhalter" not in html
    assert "Map Workspace folgt" not in html
    assert "Import / Export folgt" not in html
    assert "Assets, Uploads und Vorschau sind verfügbar." in html


def test_session_prep_deepening_keeps_play_entry_seam_owned(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function openPlay(campaignId, sessionId)" in html
    assert "BookScene.enterPlay({" in html
    assert "sourceRoute: 'campaigns'" in html
    assert "window.location.href = `/play" not in html
