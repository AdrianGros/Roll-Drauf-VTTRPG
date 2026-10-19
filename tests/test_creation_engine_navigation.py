"""Creation Engine is discoverable from the rendered book and table navigation."""

import re
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.serving import make_server

from vtt import create_app
from vtt.extensions import db
from vtt.models import Campaign, GameSession, Role, User


@pytest.fixture
def navigation_app():
    app = create_app(config_name="testing")
    # The destination is the real Creation Engine page (Eagle Homebrew host); the editor's own behavior is
    # covered by test_creation_engine_eagle.py and the host's browser E2E.
    app.config['CE_AUTHORING'] = True
    with app.app_context():
        db.create_all()
        role = Role.query.filter_by(name='DM').first()
        if role is None:
            role = Role(name='DM'); db.session.add(role); db.session.flush()
        user = User(username='navigation-author', email='navigation@example.test',
                    password_hash='test', role_id=role.id, is_active=True,
                    is_suspended=False, account_state='active')
        db.session.add(user); db.session.flush()
        campaign = Campaign(name='Navigation campaign', owner_id=user.id)
        db.session.add(campaign); db.session.flush()
        game_session = GameSession(campaign_id=campaign.id, name='Navigation session')
        db.session.add(game_session); db.session.commit()
        token = create_access_token(identity=str(user.id))
        context = dict(token=token, user_id=user.id, campaign_id=campaign.id,
                       session_id=game_session.id)
    yield app, context
    with app.app_context():
        db.session.remove(); db.drop_all()


@pytest.mark.parametrize('state', ['enabled', 'flag_off', 'suspended', 'inactive', 'pending'])
def test_navigation_capability_is_authenticated_private_and_matches_authority(navigation_app, state):
    app, context = navigation_app
    client = app.test_client()
    assert client.get('/api/dashboard/capabilities').status_code == 401
    client.set_cookie('access_token_cookie', context['token'])
    if state == 'flag_off': app.config['CE_AUTHORING'] = False
    elif state in {'suspended', 'inactive', 'pending'}:
        with app.app_context():
            user = db.session.get(User, context['user_id'])
            if state == 'suspended': user.is_suspended = True
            elif state == 'inactive': user.is_active = False
            else: user.account_state = 'pending'
            db.session.commit()
    response = client.get('/api/dashboard/capabilities')
    if state == 'inactive':
        assert response.status_code == 404
    else:
        assert response.status_code == 200
        assert response.json == {'authoring_available': state == 'enabled'}
        assert response.headers['Cache-Control'] == 'private, no-store'
        assert response.headers['Vary'] == 'Cookie, Authorization'


@pytest.fixture
def navigation_browser(navigation_app):
    playwright = pytest.importorskip('playwright.sync_api')
    app, context = navigation_app
    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            browser_context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                                                  reduced_motion='reduce')
            browser_context.add_cookies([{'name': 'access_token_cookie', 'value': context['token'],
                                         'url': origin, 'httpOnly': True}])
            page = browser_context.new_page()
            yield page, origin, context
            browser.close()
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()


@pytest.mark.parametrize('path', ['/dashboard', '/campaigns', '/characters',
                                  '/campaigns?classic=1', '/characters?classic=1',
                                  '/character-sheet?id=42'])
def test_visible_book_navigation_reaches_editor_with_keyboard(navigation_browser, path):
    from playwright.sync_api import expect
    page, origin, _ = navigation_browser
    page.goto(origin + path)
    entry = page.locator('.book-dashboard-ribbon [data-creation-engine-nav]:visible')
    expect(entry).to_have_count(1)
    expect(entry).to_have_attribute('aria-disabled', 'false')
    entry.focus(); page.keyboard.press('Enter')
    expect(page).to_have_url(re.compile(r'/api/ce/authoring(?:\?character_id=42)?$'))
    expect(page.get_by_role('heading', name='Creation Engine', exact=True)).to_be_visible()


def test_contents_and_in_book_page_turn_keep_engine_available(navigation_browser):
    from playwright.sync_api import expect
    page, origin, _ = navigation_browser
    page.goto(origin + '/dashboard')
    contents = page.locator('.book-toc [data-creation-engine-nav]')
    expect(contents).to_have_attribute('href', '/api/ce/authoring')
    page.locator('.book-dashboard-ribbon [data-dashboard-route="/campaigns"]').click()
    expect(page).to_have_url(origin + '/campaigns')
    entry = page.locator('.book-dashboard-ribbon [data-creation-engine-nav]:visible')
    expect(entry).to_have_attribute('href', '/api/ce/authoring')
    entry.click()
    expect(page).to_have_url(origin + '/api/ce/authoring')


@pytest.mark.parametrize('path', ['/login.html', '/signup.html', '/register.html'])
def test_logged_out_capability_check_never_navigates(navigation_browser, path):
    # Regression: the capability probe used makeAuthRequest, whose 401 path
    # redirects to /login.html, so every logged-out book page reloaded itself.
    page, origin, _ = navigation_browser
    page.context.clear_cookies()
    # Count document loads, not framenavigated: BookScene's replaceState on
    # signup/register is a same-document navigation, not a reload.
    document_loads = []
    page.on('request', lambda request: request.is_navigation_request()
            and request.frame == page.main_frame and document_loads.append(request.url))
    with page.expect_response('**/api/dashboard/capabilities') as capability:
        page.goto(origin + path)
    assert capability.value.status == 401
    page.wait_for_timeout(1500)
    assert document_loads == [origin + path]


def test_disabled_engine_stays_visible_and_explained(navigation_browser, navigation_app):
    from playwright.sync_api import expect
    page, origin, _ = navigation_browser
    navigation_app[0].config['CE_AUTHORING'] = False
    page.goto(origin + '/dashboard')
    entry = page.locator('.book-dashboard-ribbon [data-creation-engine-nav]:visible')
    expect(entry).to_have_attribute('aria-disabled', 'true')
    expect(entry).to_have_text('Creation Engine · nicht verfügbar')
    expect(entry).not_to_have_attribute('href', '/api/ce/authoring')
    entry.focus(); page.keyboard.press('Enter')
    expect(page).to_have_url(origin + '/dashboard')


@pytest.mark.parametrize('mobile', [False, True])
def test_play_session_menu_uses_existing_return_transition(navigation_browser, mobile):
    from playwright.sync_api import expect
    page, origin, context = navigation_browser
    if mobile: page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(f"{origin}/play?campaign_id={context['campaign_id']}&session_id={context['session_id']}")
    if mobile:
        page.locator('#btnTableSheet').click()
        page.locator('#btnTableSheetBack').click()
    else:
        page.locator('#btnBack').click()
    entry = page.locator('#appMenuCreationEngine')
    expect(entry).to_be_visible()
    expect(entry).to_have_attribute('aria-disabled', 'false')
    entry.focus(); page.keyboard.press('Enter')
    expect(page).to_have_url(origin + '/api/ce/authoring')
    boundary = page.evaluate("JSON.parse(sessionStorage.getItem('vtt.book.return-boundary'))")
    assert boundary['target']['route'] == 'creation-engine'
    assert boundary['target']['href'] == '/api/ce/authoring'
    assert boundary['phase'] == 'book-route-entry'


def test_campaign_hub_keeps_visible_engine_navigation(navigation_browser):
    from playwright.sync_api import expect
    page, origin, context = navigation_browser
    page.goto(origin + '/campaigns')
    page.locator(f'[data-dashboard-detail="campaign:{context["campaign_id"]}"]').first.click()
    entry = page.locator('.book-dashboard-ribbon [data-creation-engine-nav]:visible')
    expect(entry).to_have_attribute('href', '/api/ce/authoring')
    entry.click()
    expect(page).to_have_url(origin + '/api/ce/authoring')


def test_character_overlay_opens_engine_in_top_level_with_character_context(navigation_browser):
    from playwright.sync_api import expect
    page, origin, _ = navigation_browser
    page.goto(origin + '/dashboard')
    page.set_content('<iframe title="Character overlay" src="/character-sheet?id=42" '
                     'style="width:100%;height:900px"></iframe>')
    frame = page.frame_locator('iframe')
    entry = frame.locator('a.btn[data-creation-engine-nav]:visible')
    expect(entry).to_have_attribute('href', '/api/ce/authoring?character_id=42')
    expect(entry).to_have_attribute('target', '_top')
    entry.click()
    expect(page).to_have_url(origin + '/api/ce/authoring?character_id=42')
    expect(page.locator('iframe')).to_have_count(0)
