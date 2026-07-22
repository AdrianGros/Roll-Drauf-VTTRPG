"""Targeted route/runtime checks for M08 non-play ownership cleanup."""

import pytest

from vtt import create_app


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
    assert 'book-shell-app' not in html


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
    assert 'book-shell-app' not in html


def test_login_route_remains_bookscene_owned(client):
    response = client.get("/login.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert '/static/js/book-scene.js' in html
    assert '/static/js/book-shell.js' not in html
    assert 'BookShell.navigate(' not in html


@pytest.mark.parametrize("path", ["/signup.html", "/register.html"])
def test_signup_and_register_redirect_to_canonical_login(path, client):
    response = client.get(path, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login.html?auth_notice=discord_only")
