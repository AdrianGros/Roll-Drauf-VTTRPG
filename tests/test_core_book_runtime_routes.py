"""Targeted route/runtime checks for M08 non-play ownership cleanup."""

import re

import pytest

from vtt import create_app


def _body_tag(html):
    match = re.search(r"<body[^>]*>", html)
    assert match is not None, "response has no <body> tag"
    return match.group(0)


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.parametrize(
    ("path", "body_class", "route_key"),
    [
        ("/dashboard", "dashboard-route-book-scene", "dashboard"),
        ("/campaigns", "campaigns-route-book-scene", "campaigns"),
        ("/characters", "characters-route-book-scene", "characters"),
    ],
)
def test_core_book_routes_use_bookscene_as_runtime_owner(client, path, body_class, route_key):
    response = client.get(path)

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert f'<body class="spellbook {body_class}">' in html
    assert '/static/js/book-scene.js' in html
    assert 'BookScene.bootstrapProtectedRoute({' in html
    assert f"routeKey: '{route_key}'" in html
    assert 'BookScene.pageTurn(path, BookScene.sceneUser || null);' in html
    assert '/static/js/book-routes.js' not in html
    assert '/static/js/book-shell.js' not in html
    assert 'BookShell.navigate(' not in html
    # Guards the actual rendered <body> element only (the M08 regression this
    # pins is the old BookShell runtime being live-active on this route) --
    # not a bare substring search, since a page may legitimately reference
    # "book-shell-app" inside a CSS selector for cross-context styling
    # (e.g. an overlay component also rendered inside the play-table shell)
    # without that class ever being applied to this route's own body.
    assert 'book-shell-app' not in _body_tag(html)


def test_character_sheet_route_uses_bookscene_focus_template(client):
    response = client.get('/character-sheet?id=42&mode=edit')

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert '<body class="spellbook character-sheet-route-book-scene">' in html
    assert 'characterSheetSceneTemplate' in html
    assert "/static/js/book-scene.js" in html
    assert 'BookScene.bootstrapProtectedRoute({' in html
    assert "routeKey: 'character-sheet'" in html
    assert "window.BookSceneRouteInit['character-sheet']" in html
    assert 'BookScene.pageTurn(path, window.BookScene.sceneUser || currentUser || null);' in html
    assert '/static/js/book-routes.js' not in html
    assert '/static/js/book-shell.js' not in html
    assert 'BookShell.navigate(' not in html
    assert 'book-shell-app' not in _body_tag(html)


def test_login_route_remains_bookscene_owned(client):
    response = client.get("/login.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert '/static/js/book-scene.js' in html
    assert '/static/js/book-shell.js' not in html
    assert 'BookShell.navigate(' not in html


@pytest.mark.parametrize("path", ["/signup.html", "/register.html"])
def test_signup_and_register_remain_reachable_with_discord_enabled(path, client, app):
    app.config["DISCORD_LOGIN_ENABLED"] = True

    response = client.get(path, follow_redirects=False)

    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/signup.html", "/register.html"])
def test_signup_and_register_reachable_when_discord_login_disabled(path, client, app):
    app.config["DISCORD_LOGIN_ENABLED"] = False

    response = client.get(path, follow_redirects=False)

    assert response.status_code == 200
