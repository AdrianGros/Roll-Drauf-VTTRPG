"""Regression checks for the 2026-08-24 book UI audit closeout."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_book_routes_have_one_transition_engine_and_no_gsap_curtain():
    scene = _read("vtt/static/js/book-scene.js")
    shell = _read("vtt/static/js/book-shell.js")

    assert "document.startViewTransition" in scene
    assert "gsap" not in scene
    assert "gsap" not in shell
    assert not (REPO_ROOT / "vtt/static/js/book-animation.js").exists()


def test_login_entry_and_failure_states_are_explicit_and_capture_safe():
    login = _read("vtt/templates/login.html")
    scene = _read("vtt/static/js/book-scene.js")

    assert "/static/js/gsap.min.js" not in login
    assert 'id="passwordLoginStatus"' in login
    assert 'id="passwordLoginError"' in login
    assert 'aria-describedby="passwordLoginError"' in login
    assert "Buchzugang öffnen" in scene
    assert "/static/icons/icon-book-sparkles.svg" in scene
    assert "BookScene.open();" not in login
    assert "this.bookCover.style.pointerEvents = 'auto';" in scene
    assert "this.bookCover.style.pointerEvents = 'none';" in scene


def test_dashboard_bootstrap_keeps_status_visible_long_enough_for_redirect_checkpoint():
    dashboard = _read("vtt/templates/dashboard.html")
    scene = _read("vtt/static/js/book-scene.js")

    assert "minimumStatusDuration: 620" in dashboard
    assert "minimumStatusDuration = 0" in scene
    assert "performance.now() - statusStartedAt" in scene
