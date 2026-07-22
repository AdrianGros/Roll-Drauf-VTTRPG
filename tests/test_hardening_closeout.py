"""Targeted hardening checks for the accepted M06-M10 delivery chain."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_campaigns_play_handoff_requires_explicit_bookscene_seam(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function openPlay(campaignId, sessionId) {" in html
    assert "try {" in html
    assert "BookScene.enterPlay({" in html
    assert "console.warn('BookScene play handoff failed.', error);" in html
    assert "showMessage('Play handoff unavailable. Please reload and try again.', true);" in html
    assert "window.location.href = `/play?campaign_id=${campaignId}&session_id=${sessionId}`;" not in html


def test_play_runtime_validates_and_cleans_boundary_metadata(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert 'const PLAY_ENTRY_PHASES = new Set(["book-exit", "play-route-entry"]);' in js
    assert "_isValidEntryBoundary(boundary) {" in js
    assert 'if (boundary.kind !== "book-to-table") {' in js
    assert 'if (boundary.transition_mode !== "BOOK_TO_TABLE_TRANSITION") {' in js
    assert 'if (boundary.target_mode !== "TABLE_MODE") {' in js
    assert 'if (target.family !== "play") {' in js
    assert 'if (!PLAY_ENTRY_PHASES.has(String(boundary.phase || "book-exit"))) {' in js
    assert 'window.sessionStorage.removeItem(PLAY_ENTRY_STORAGE_KEY);' in js


def test_play_runtime_clears_arrival_timer_on_beforeunload(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert 'window.addEventListener("beforeunload", () => {' in js
    assert 'if (this.entryArrivalTimer) {' in js
    assert 'window.clearTimeout(this.entryArrivalTimer);' in js
    assert "this.socket.disconnect();" in js
