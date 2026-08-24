"""M17.5 tests: campaign hub and session-prep productization."""

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
    assert "Campaign Prep / Session Hub" in html
    assert "Prep Overview" in html
    assert "Aktueller Stand:" in html
    assert "Preparation Checklist" in html
    assert "Sessions pruefen" in html


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

    assert "Prep Links" in html
    assert "Charaktere öffnen" in html
    assert "Map Prep ansehen" in html
    assert 'id="campaignAssetLibraryPanel"' in html
    assert "Session-Besetzung:" in html
    assert "Session-Besetzung öffnen" in html
    assert "Map Workspace folgt" in html
    assert "Import / Export folgt hier" in html


def test_campaign_hub_play_entry_remains_bookscene_seam_owned(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function openPlay(campaignId, sessionId)" in html
    assert "BookScene.enterPlay({" in html
    assert "sourceRoute: 'campaigns'" in html
    assert "window.location.href = `/play" not in html
