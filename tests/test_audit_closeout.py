"""Regression checks for the 2026-08-24 book UI audit closeout."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_book_routes_switch_without_transition_or_gsap_curtain():
    # Owner decision 2026-11-08: tabs switch instantly, no crossfade.
    scene = _read("vtt/static/js/book-scene.js")
    shell = _read("vtt/static/js/book-shell.js")

    assert "document.startViewTransition" not in scene
    assert "gsap" not in scene
    assert "gsap" not in shell
    assert not (REPO_ROOT / "vtt/static/js/book-animation.js").exists()


def test_landing_page_is_the_login_without_a_cover_click():
    login = _read("vtt/templates/login.html")
    scene = _read("vtt/static/js/book-scene.js")

    assert "/static/js/gsap.min.js" not in login
    assert 'id="passwordLoginStatus"' in login
    assert 'id="passwordLoginError"' in login
    assert 'aria-describedby="passwordLoginError"' in login
    assert "Zum Buchzugang" not in login
    assert "Zum Buchzugang" not in scene
    assert "Buchzugang öffnen" not in scene
    assert '<main id="login-content" class="visible">' in login
    assert 'class="spellbook book-scene-open book-login-open is-book-scene-login"' in login
    assert "BookScene.open();" in login
    assert "setCoverState" not in scene


def test_protected_routes_paint_the_open_book_instead_of_a_curtain():
    scene = _read("vtt/static/js/book-scene.js")
    css = _read("vtt/static/css/book-scene.css")

    assert "minimumStatusDuration" not in scene
    assert "showLoadingShell(routeKey) {" in scene
    assert "document.body.classList.add('book-scene-open');" in scene
    assert "body.book-scene-open .book-cover" in css
    for page, status_id in (
        ("dashboard", "dashboardSceneStatus"),
        ("campaigns", "campaignsSceneStatus"),
        ("characters", "charactersSceneStatus"),
        ("character-sheet", "characterSheetSceneStatus"),
    ):
        html = _read(f"vtt/templates/{page}.html")
        assert "minimumStatusDuration" not in html
        assert f'<div id="{status_id}" role="status" aria-live="polite" hidden>' in html
        assert "radial-gradient(ellipse at center, #2d1b35 0%, #0d0514 100%);\n            color" not in html
