"""Targeted checks for M13 reverse TABLE_TO_BOOK transition choreography."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_play_runtime_choreographs_table_exit_before_book_return(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert 'const PLAY_RETURN_EXIT_DURATION_MS = 520;' in js
    assert 'const BOOK_RETURN_ARRIVAL_DURATION_MS = 680;' in js
    assert "_beginReturnTransition(boundary) {" in js
    assert 'body.dataset.playReturnBoundary = "table-to-book";' in js
    assert 'body.dataset.playReturnPhase = "TABLE_TO_BOOK_TRANSITION";' in js
    assert 'body.dataset.playTransitionStage = "table-exit";' in js
    assert 'boundary.table_exit_completed_at = new Date().toISOString();' in js
    assert 'document.body.dataset.playTransitionStage = "book-handoff";' in js


def test_play_route_exposes_reverse_transition_choreography_shell(client):
    response = client.get("/play?campaign_id=9&session_id=11")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'data-play-return-boundary="idle"' in html
    assert 'data-play-return-phase="TABLE_MODE"' in html
    assert 'class="play-return-curtain"' in html
    assert "The table folds back into the spellbook" not in html
    assert 'body[data-play-transition-stage="table-exit"] .play-return-curtain' in html
    assert 'body[data-play-transition-stage="book-handoff"] .play-return-curtain' in html


def test_bookscene_honors_reverse_arrival_transition_state(client):
    js_response = client.get("/static/js/book-scene.js")

    assert js_response.status_code == 200
    js = js_response.get_data(as_text=True)

    assert "const BOOK_RETURN_ARRIVAL_DURATION_MS = 680;" in js
    assert "bookEntryArrivalTimer: null," in js
    assert "document.body.classList.toggle('is-book-scene-return-transition', state === 'return-transition');" in js
    assert "document.body.dataset.bookSceneEntryTargetRoute = String(target.route || routeKey);" in js
    assert "this.setSceneState('return-transition');" in js
    assert "document.body.dataset.bookSceneTransitionPhase = 'TABLE_TO_BOOK_TRANSITION';" in js
    assert "document.body.dataset.bookSceneEntryBoundary = 'arrived';" in js

    css_response = client.get("/static/css/book-scene.css")

    assert css_response.status_code == 200
    css = css_response.get_data(as_text=True)

    assert "body.is-book-scene-return-transition" in css
    assert 'body[data-book-scene-entry-boundary="table-to-book"] .book-dashboard-camera' in css
    assert 'body[data-book-scene-entry-boundary="arrived"] .book-dashboard-camera' in css
