"""Targeted checks for M14 fallback removal and boundary residue cleanup."""

from pathlib import Path

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_campaigns_play_entry_no_longer_exposes_ordinary_direct_fallback(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "BookScene.enterPlay({" in html
    assert "showMessage('Play handoff unavailable. Please reload and try again.', true);" in html
    assert "__VTT_ALLOW_DIRECT_PLAY_FALLBACK" not in html
    assert "window.location.href = `/play?campaign_id=${campaignId}&session_id=${sessionId}`;" not in html


def test_play_template_remains_formally_clean_after_boundary_chain_changes():
    play_template = Path("/home/admin/projects/roll-drauf-vtt/vtt/templates/play.html").read_text()

    assert play_template.count("<body") == 1
    assert play_template.count("</body>") == 1
    assert play_template.count('data-play-return-boundary="idle"') == 1
    assert play_template.count(".play-entry-curtain-copy {") == 1
    assert play_template.count(".play-return-curtain-copy {") == 1


def test_bookscene_cleans_return_boundary_residue_after_arrival(client):
    response = client.get("/static/js/book-scene.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "delete document.body.dataset.bookSceneTransitionTarget;" in js
    assert "delete document.body.dataset.bookSceneEntrySourceMode;" in js
    assert "delete document.body.dataset.bookSceneEntrySourceRoute;" in js
    assert "delete document.body.dataset.bookSceneEntryTargetRoute;" in js
    assert "document.body.dataset.bookSceneTransitionPhase = 'BOOK_MODE';" in js

