"""Targeted checks for M12 fallback cleanup and return seam preparation."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_campaigns_no_longer_uses_direct_play_fallback_as_operating_path(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "const emergencyDirectPlayFallback = window.__VTT_ALLOW_DIRECT_PLAY_FALLBACK === true;" not in html
    assert "showMessage('Play handoff unavailable. Please reload and try again.', true);" in html
    assert "window.location.href = `/play?campaign_id=${campaignId}&session_id=${sessionId}`;" not in html


def test_play_route_exposes_explicit_return_targets(client):
    response = client.get("/play?campaign_id=9&session_id=11")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'data-book-return-target="/dashboard"' in html
    assert 'data-book-return-target="/campaigns"' in html
    assert 'data-book-return-target="/characters"' in html
    assert "onclick=\"window.location.href='/dashboard'\"" not in html
    assert "onclick=\"window.location.href='/campaigns'\"" not in html
    assert "onclick=\"window.location.href='/characters'\"" not in html


def test_play_runtime_exposes_return_seam_helper(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert 'const BOOK_RETURN_STORAGE_KEY = "vtt.book.return-boundary";' in js
    assert 'const BOOK_RETURN_PHASES = new Set(["table-exit", "book-route-entry"]);' in js
    assert "_normalizeBookReturnTarget(targetHref) {" in js
    assert "_persistBookReturnBoundary(target) {" in js
    assert 'transition_mode: "TABLE_TO_BOOK_TRANSITION",' in js
    assert 'target_mode: "BOOK_MODE",' in js
    assert 'family: "book",' in js
    assert "returnToBook(targetHref) {" in js
    assert "this.returnToBook(`/campaigns?campaign_id=${this.campaignId}`);" in js


def test_bookscene_consumes_return_boundary_context(client):
    response = client.get("/static/js/book-scene.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "const BOOK_RETURN_STORAGE_KEY = 'vtt.book.return-boundary';" in js
    assert "consumeBookEntryBoundary(routeKey) {" in js
    assert "document.body.dataset.bookSceneEntryBoundary = 'table-to-book';" in js
    assert "document.body.dataset.bookSceneEntryPhase = 'TABLE_TO_BOOK_TRANSITION';" in js
    assert "this.finalizeBookEntryBoundary(entryBoundary);" in js
