"""Table <-> book switches without curtains (owner decision 2026-11-08,
supersedes the M13 reverse transition choreography)."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_play_runtime_leaves_for_the_book_without_exit_curtain(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "_beginReturnTransition(boundary) {" in js
    assert 'body.dataset.playReturnBoundary = "table-to-book";' in js
    assert 'boundary.table_exit_completed_at = new Date().toISOString();' in js
    assert 'body.dataset.playTransitionStage = "table-exit";' not in js
    assert 'document.body.dataset.playTransitionStage = "book-handoff";' not in js
    assert "            navigateToBook();\n            return true;" in js


def test_play_route_starts_in_table_stage_without_entry_curtain(client):
    response = client.get("/play?campaign_id=9&session_id=11")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'data-play-return-boundary="idle"' in html
    assert 'data-play-return-phase="TABLE_MODE"' in html
    assert 'data-play-mode-family="table" data-play-transition-stage="table"' in html


def test_bookscene_has_no_return_arrival_choreography(client):
    js_response = client.get("/static/js/book-scene.js")

    assert js_response.status_code == 200
    js = js_response.get_data(as_text=True)

    assert "BOOK_RETURN_ARRIVAL_DURATION_MS" not in js
    assert "this.setSceneState('return-transition');" not in js
    assert "this.setSceneState('play-transition');" not in js
