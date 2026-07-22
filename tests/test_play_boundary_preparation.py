"""Targeted route/runtime checks for M09 play-boundary preparation."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_campaigns_route_uses_explicit_bookscene_play_handoff(client):
    response = client.get("/campaigns")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "function openPlay(campaignId, sessionId) {" in html
    assert "if (window.BookScene && typeof BookScene.enterPlay === 'function')" in html
    assert "BookScene.enterPlay({" in html
    assert "sourceRoute: 'campaigns'" in html


def test_bookscene_serves_play_boundary_handoff_helper(client):
    response = client.get("/static/js/book-scene.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "const PLAY_ENTRY_STORAGE_KEY = 'vtt.play.entry-boundary';" in js
    assert "function buildPlayHref(campaignId, sessionId) {" in js
    assert "enterPlay(config = {}) {" in js
    assert "transition_mode: 'BOOK_TO_TABLE_TRANSITION'" in js
    assert "target_mode: 'TABLE_MODE'" in js
    assert "persistPlayHandoff(handoff);" in js
    assert "return this._runPlayExitTransition(handoff);" in js


def test_play_route_marks_table_mode_entry_shell(client):
    response = client.get("/play?campaign_id=9&session_id=11")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'data-play-entry-boundary="pending"' in html
    assert 'data-play-mode-family="table"' in html
    assert "/static/js/play-ui.js" in html


def test_play_runtime_consumes_boundary_context_without_replacing_bootstrap(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert 'const PLAY_ENTRY_STORAGE_KEY = "vtt.play.entry-boundary";' in js
    assert "this._consumeEntryBoundary();" in js
    assert '_consumeEntryBoundary() {' in js
    assert 'body.dataset.playEntryBoundary = "direct";' in js
    assert 'body.dataset.playEntryBoundary = "book-to-table";' in js
    assert "await this.loadBootstrap();" in js
    assert "this._connectSocket();" in js
