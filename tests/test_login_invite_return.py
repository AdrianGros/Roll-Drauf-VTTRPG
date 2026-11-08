from threading import Thread
from urllib.parse import quote

import pytest
from werkzeug.serving import make_server

from vtt import create_app


@pytest.fixture(scope='module')
def login_site():
    app = create_app(config_name='testing')
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


@pytest.fixture
def login_browser(login_site):
    from playwright.sync_api import sync_playwright
    state = {'authenticated': False}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        def api(route):
            path = route.request.url.split('/api/', 1)[1]
            if path == 'auth/login':
                state['authenticated'] = True
                route.fulfill(json={'message': 'logged in'})
            elif path == 'auth/check':
                route.fulfill(status=200 if state['authenticated'] else 401,
                              json={'user': {'id': 1, 'username': 'Tester', 'role': 'Player'}} if state['authenticated'] else {})
            elif path.startswith('invites/'):
                route.fulfill(json={'campaign_id': 42, 'campaign_name': 'Test table', 'dm_username': 'DM', 'status': 'valid'})
            elif path == 'auth/discord/status':
                route.fulfill(json={'enabled': False})
            elif path == 'auth/refresh':
                route.fulfill(status=401, json={})
            else:
                route.fulfill(json=[])
        page.route('**/api/**', api)
        yield page, login_site, state
        browser.close()


def test_password_login_returns_to_invitation(login_browser):
    from playwright.sync_api import expect
    page, origin, _ = login_browser
    page.goto(origin + '/invite/test-invite')
    page.locator('#linkLogin').click()
    page.locator('#loginUsername').fill('Tester')
    page.locator('#loginPassword').fill('Password123!')
    page.locator('#passwordLoginSubmitBtn').click()
    expect(page).to_have_url(origin + '/invite/test-invite')
    expect(page.locator('#btnAcceptInvite')).to_be_visible()


def test_already_authenticated_login_honors_invitation(login_browser):
    from playwright.sync_api import expect
    page, origin, state = login_browser
    state['authenticated'] = True
    page.goto(origin + '/login.html?next=%2Finvite%2Ftest-invite')
    expect(page).to_have_url(origin + '/invite/test-invite')
    expect(page.locator('#btnAcceptInvite')).to_be_visible()


@pytest.mark.parametrize('target', [
    '/invite/test-invite?source=email#join', '/campaigns?campaign_id=42',
    'https://example.invalid', '//example.invalid', '/\\example.invalid',
    '/%5cexample.invalid', '/%2fexample.invalid', '/\n/example.invalid',
    '/.//example.invalid', '/a/..//example.invalid', '/%6cogin.html',
    'javascript:alert(1)', '/login.html?next=/invite/test-invite', '/signup.html',
])
def test_login_return_target_stays_local_and_avoids_auth_loops(login_browser, target):
    page, origin, _ = login_browser
    page.goto(origin + '/login.html?next=' + quote(target, safe=''))
    result = page.evaluate('loginReturnPath()')
    expected = target if target.startswith(('/invite/', '/campaigns')) else '/dashboard'
    assert result == expected
