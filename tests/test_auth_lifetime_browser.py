"""C03 in real browsers: server-issued cookie paths, CSRF refresh, password change.

JWT_COOKIE_CSRF_PROTECT is enabled and every cookie is issued by the real login
form, so the browser's own path matching is exercised (a test client with
cookies on "/" would not prove this).  The six-hour absolute bound is covered by
the controlled-clock tests in test_auth_lifetime.py; here dropping only
access_token_cookie simulates the short access expiry.
"""

import time

import pytest

from tests.test_personal_actions_browser import action_site  # noqa: F401
from vtt.config import TestingConfig

PASSWORD = "Test-only-123!"
NEW_PASSWORD = "Another-Test-456!"
LIFE = 6 * 3600
ENGINES = ["firefox", "chromium"]


@pytest.fixture
def csrf_on(monkeypatch):
    # Must be requested BEFORE action_site so create_app sees it.
    monkeypatch.setattr(TestingConfig, "JWT_COOKIE_CSRF_PROTECT", True, raising=False)


def launch(playwright, engine):
    return getattr(playwright, engine).launch(headless=True, args=["--no-sandbox"] if engine == "chromium" else [])


def login(context, origin, username="action-player", password=PASSWORD):
    page = context.new_page()
    page.set_default_timeout(30000)
    page.goto(f"{origin}/login.html")
    page.fill("#loginUsername", username)
    page.fill("#loginPassword", password)
    page.click("#passwordLoginSubmitBtn")
    page.wait_for_function("() => !location.pathname.includes('login')")
    return page


def cookies_named(context, name):
    return [c for c in context.cookies() if c["name"] == name]


def drop_access_cookie(context):
    """Simulate the one-hour access expiry: everything else stays as issued."""
    kept = [c for c in context.cookies() if c["name"] != "access_token_cookie"]
    context.clear_cookies()
    context.add_cookies(kept)
    assert not cookies_named(context, "access_token_cookie")


def me_status(page):
    return page.evaluate("fetch('/api/auth/me', {credentials: 'include'}).then(r => r.status)")


@pytest.mark.parametrize("engine", ENGINES)
def test_server_issued_cookie_paths_and_page_refresh_with_csrf(csrf_on, action_site, engine):
    from playwright.sync_api import sync_playwright
    app, origin, info = action_site
    with sync_playwright() as p:
        browser = launch(p, engine)
        context = browser.new_context()
        login(context, origin)

        (refresh,) = cookies_named(context, "refresh_token_cookie")
        (csrf,) = cookies_named(context, "csrf_refresh_token")
        assert refresh["path"] == "/api/auth" and refresh["httpOnly"] is True
        assert csrf["path"] == "/" and csrf["httpOnly"] is False
        assert cookies_named(context, "access_token_cookie")[0]["path"] == "/"
        now = time.time()
        for cookie in (refresh, csrf, cookies_named(context, "access_token_cookie")[0]):
            assert now < cookie["expires"] <= now + LIFE + 60  # never longer than the absolute bound

        page = context.new_page()
        page.goto(f"{origin}/regelwerk")
        visible = page.evaluate("document.cookie")
        assert f"csrf_refresh_token={csrf['value']}" in visible
        assert "refresh_token_cookie" not in visible and refresh["value"] not in visible
        assert refresh["value"] not in page.content() and refresh["value"] not in page.url

        drop_access_cookie(context)
        assert me_status(page) == 401
        # the existing, unmodified client helper on a normal page
        assert page.evaluate("Auth.refreshAccessToken()") is True
        assert cookies_named(context, "access_token_cookie")
        assert me_status(page) == 200
        browser.close()


@pytest.mark.parametrize("engine", ENGINES)
def test_password_change_keeps_this_browser_and_rejects_the_second(csrf_on, action_site, engine):
    from playwright.sync_api import sync_playwright
    app, origin, info = action_site
    with sync_playwright() as p:
        browser = launch(p, engine)
        first, second = browser.new_context(), browser.new_context()
        first_page = login(first, origin)
        second_page = login(second, origin)  # typically in the same second: same expires_at
        first_page.goto(f"{origin}/regelwerk")
        second_page.goto(f"{origin}/regelwerk")
        assert me_status(first_page) == 200 and me_status(second_page) == 200

        status = first_page.evaluate("""async (body) => {
            const response = await fetch('/api/auth/password/change', {
                method: 'POST', credentials: 'include',
                headers: Auth.buildHeaders('POST', true), body: JSON.stringify(body)});
            return response.status;
        }""", {"current_password": PASSWORD, "new_password": NEW_PASSWORD})
        assert status == 200

        # current browser: access still fine, and after its access "expires" the refresh survives
        assert me_status(first_page) == 200
        drop_access_cookie(first)
        assert first_page.evaluate("Auth.refreshAccessToken()") is True
        assert me_status(first_page) == 200

        # the other browser (same user, possibly same second) lost both tokens
        assert me_status(second_page) == 401
        assert second_page.evaluate("Auth.refreshAccessToken()") is False
        drop_access_cookie(second)
        assert second_page.evaluate("Auth.refreshAccessToken()") is False
        assert me_status(second_page) == 401
        browser.close()


@pytest.mark.parametrize("engine", ENGINES)
def test_old_path_cookies_are_cleared_by_login_and_logout(csrf_on, action_site, engine):
    from playwright.sync_api import sync_playwright
    app, origin, info = action_site
    host = origin.split("//", 1)[1].split(":", 1)[0]
    shadows = [{"name": name, "value": "stale-shadow", "domain": host, "path": "/api/auth/refresh",
                "httpOnly": name == "refresh_token_cookie"}
               for name in ("refresh_token_cookie", "csrf_refresh_token")]

    def old_path_cookies(context):
        return [c for c in context.cookies() if c["path"] == "/api/auth/refresh"]

    with sync_playwright() as p:
        browser = launch(p, engine)
        context = browser.new_context()
        context.add_cookies(shadows)
        assert len(old_path_cookies(context)) == 2
        page = login(context, origin)
        assert old_path_cookies(context) == []
        # with the shadows gone, the page's refresh hits the new cookies
        page.goto(f"{origin}/regelwerk")
        drop_access_cookie(context)
        assert page.evaluate("Auth.refreshAccessToken()") is True

        context.add_cookies(shadows)  # reappear (e.g. another tab of an old deployment)
        status = page.evaluate("""fetch('/api/auth/logout', {method: 'POST', credentials: 'include',
            headers: Auth.buildHeaders('POST')}).then(r => r.status)""")
        assert status == 200
        assert old_path_cookies(context) == []
        assert not cookies_named(context, "refresh_token_cookie")
        assert not cookies_named(context, "access_token_cookie")
        browser.close()
