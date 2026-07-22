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


def test_bookscene_exit_choreography_is_defined_on_play_handoff(client):
    response = client.get("/static/js/book-scene.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "const PLAY_EXIT_DURATION_MS = 560;" in js
    assert "const PLAY_ARRIVAL_DURATION_MS = 720;" in js
    assert "_runPlayExitTransition(handoff) {" in js
    assert "this.setSceneState('play-transition');" in js
    assert "document.body.dataset.bookSceneTransitionTarget = 'play';" in js
    assert "document.body.dataset.bookSceneTransitionPhase = 'BOOK_TO_TABLE_TRANSITION';" in js
    assert "handoff.book_exit_completed_at = new Date().toISOString();" in js


def test_bookscene_play_transition_state_is_styled(client):
    response = client.get("/static/css/book-scene.css")

    assert response.status_code == 200
    css = response.get_data(as_text=True)

    assert "body.is-book-scene-play-transition" in css
    assert "body.is-book-scene-play-transition .book-dashboard-scene" in css
    assert "body.is-book-scene-play-transition .book-scene-backdrop" in css


def test_play_entry_shell_exposes_arrival_choreography_state(client):
    response = client.get("/play?campaign_id=9&session_id=11")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'data-play-transition-stage="pending"' in html
    assert 'data-play-entry-phase="pending"' in html
    assert 'class="play-entry-curtain"' in html
    assert "The spellbook closes into table focus before the live workspace settles into view." in html


def test_play_runtime_honors_arrival_transition_states(client):
    response = client.get("/static/js/play-ui.js")

    assert response.status_code == 200
    js = response.get_data(as_text=True)

    assert "_beginEntryArrival() {" in js
    assert "_finalizeEntryArrival() {" in js
    assert 'body.dataset.playTransitionStage = "arrival";' in js
    assert 'document.body.dataset.playTransitionStage = "settling";' in js
    assert 'document.body.dataset.playTransitionStage = "table";' in js
    assert 'body.dataset.playEntryPhase = String(boundary.phase || "BOOK_TO_TABLE_TRANSITION");' in js
