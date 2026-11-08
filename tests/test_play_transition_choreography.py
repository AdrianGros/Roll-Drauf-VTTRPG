"""Targeted checks for M10 play transition choreography."""

import pytest

from vtt import create_app


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_bookscene_hands_off_to_play_without_exit_choreography(client):
    # Owner decision 2026-11-08: the table opens like any other tab.
    response = client.get("/static/js/book-scene.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "_runPlayExitTransition(handoff) {" in js
    assert "handoff.book_exit_completed_at = new Date().toISOString();" in js
    assert "this.setSceneState('play-transition');" not in js
    assert "document.body.dataset.bookSceneTransitionPhase = 'BOOK_TO_TABLE_TRANSITION';" not in js


def test_bookscene_play_transition_state_is_styled(client):
    response = client.get("/static/css/book-scene.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)

    assert "body.is-book-scene-play-transition" in css
    assert "body.is-book-scene-play-transition .book-dashboard-scene" in css
    assert "body.is-book-scene-play-transition .book-scene-backdrop" in css


def test_play_entry_shell_starts_at_the_table(client):
    response = client.get("/play?campaign_id=9&session_id=11")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'data-play-mode-family="table" data-play-transition-stage="table"' in html
    assert 'data-play-entry-phase="pending"' in html
    assert "The spellbook closes into table focus" not in html


def test_play_runtime_skips_the_arrival_curtain(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "_beginEntryArrival() {" in js
    assert "_finalizeEntryArrival() {" in js
    assert 'body.dataset.playTransitionStage = "arrival";' not in js
    assert 'document.body.dataset.playTransitionStage = "settling";' not in js
    assert 'document.body.dataset.playTransitionStage = "table";' in js
    assert 'body.dataset.playEntryPhase = String(boundary.phase || "BOOK_TO_TABLE_TRANSITION");' in js
