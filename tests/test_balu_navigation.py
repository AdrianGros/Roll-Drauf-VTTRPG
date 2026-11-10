"""Real navigation regressions for Balu's /it reports #9, #10, #12 and #14."""
from threading import Thread
from pathlib import Path
import os

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.serving import make_server, WSGIRequestHandler

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Campaign, CampaignMap, GameSession, Role, User


class QuietHandler(WSGIRequestHandler):
    def log(self, *args):
        pass


@pytest.fixture
def balu_site(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path}/test.db')
    app = create_app('testing')
    app.config['LOCAL_STORAGE_PATH'] = str(tmp_path / 'assets')
    with app.app_context():
        db.create_all()
        role = Role(name='DM'); db.session.add(role); db.session.flush()
        user = User(username='navigation-dm', email='navigation@example.test',
                    password_hash='test', role_id=role.id, is_active=True,
                    is_suspended=False, account_state='active', profile_tier='headmaster')
        db.session.add(user); db.session.flush()
        campaign = Campaign(name='Balu navigation campaign', owner_id=user.id)
        db.session.add(campaign); db.session.flush()
        map_ = CampaignMap(campaign_id=campaign.id, name='Navigation map',
                           width=1000, height=1000, grid_size=50, created_by=user.id)
        db.session.add(map_); db.session.flush()
        session = GameSession(campaign_id=campaign.id, map_id=map_.id,
                              name='Navigation session', status='in_progress')
        db.session.add(session); db.session.commit()
        data = dict(campaign_id=campaign.id, session_id=session.id,
                    token=create_access_token(identity=str(user.id)))
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', data
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()
        with app.app_context():
            db.session.remove(); db.engine.dispose()


@pytest.fixture(params=['chromium', 'firefox'])
def balu_browser(balu_site, request):
    from playwright.sync_api import sync_playwright
    origin, data = balu_site
    with sync_playwright() as p:
        browser = getattr(p, request.param).launch(headless=True,
            **({'args': ['--no-sandbox'], 'ignore_default_args': ['--disable-back-forward-cache']}
               if request.param == 'chromium' else {}))
        context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                                      reduced_motion='reduce')
        context.add_cookies([{'name': 'access_token_cookie', 'value': data['token'],
                             'url': origin, 'httpOnly': True}])
        context.add_init_script("""window.addEventListener('pageshow', e => {
            if (e.persisted) sessionStorage.setItem('bfcache-restored', 'yes');
        });""")
        page = context.new_page(); page.set_default_timeout(6000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        yield page, origin, data
        browser.close()
        assert errors == [], errors


def save_proof(page, name):
    if os.environ.get('VTT_PROOF_DIR'):
        out = Path(os.environ['VTT_PROOF_DIR']); out.mkdir(parents=True, exist_ok=True)
        engine = page.context.browser.browser_type.name
        page.screenshot(path=str(out / f'{name}-{engine}-{page.viewport_size["width"]}.png'))


@pytest.mark.parametrize('path', ['/campaigns?classic=1', '/characters?classic=1'])
def test_old_overview_shortcut_uses_modern_book(balu_browser, path):
    from playwright.sync_api import expect
    page, origin, _ = balu_browser
    page.goto(origin + path)
    expect(page.locator('#book-dashboard-scene')).to_be_visible()
    expect(page.locator('.book-dashboard-ribbon [data-dashboard-route="/dashboard"]')).to_be_visible()
    page.locator('.book-dashboard-ribbon [data-dashboard-route="/dashboard"]').click()
    expect(page).to_have_url(origin + '/dashboard')


@pytest.mark.parametrize('action', ['return', 'leave'])
def test_session_exit_and_reload_keep_modern_campaign_hub(balu_browser, action):
    from playwright.sync_api import expect
    page, origin, data = balu_browser
    page.goto(f"{origin}/play?campaign_id={data['campaign_id']}&session_id={data['session_id']}")
    page.locator('#btnBack').click()
    if action == 'leave':
        page.locator('#appMenuLeave').click(); page.locator('#appMenuLeaveConfirm').click()
    else:
        page.locator('#appMenuReturn').click()
    expect(page.locator('#campaignHubSessionPrep')).to_be_visible()
    expect(page).to_have_url(f"{origin}/campaigns?campaign_id={data['campaign_id']}")
    expect(page.locator('#campaignDetail')).to_have_count(0)
    page.reload()
    expect(page.locator('#campaignHubSessionPrep')).to_be_visible()
    save_proof(page, 'session-return')


def test_back_after_actual_session_entry_unfreezes_book(balu_browser):
    from playwright.sync_api import expect
    page, origin, data = balu_browser
    page.goto(origin + '/campaigns')
    page.locator(f'[data-dashboard-detail="campaign:{data["campaign_id"]}"]').first.click()
    page.locator('[data-hub-action="open-session-dm"]').click()
    expect(page).to_have_url(f"{origin}/play?campaign_id={data['campaign_id']}&session_id={data['session_id']}&seat=dm")
    expect(page.locator('#btnBack')).to_be_visible()
    page.go_back()
    page.locator('.book-dashboard-ribbon [data-dashboard-route="/characters"]').click()
    expect(page).to_have_url(origin + '/characters')
    expect(page.locator('#book-dashboard-scene')).to_be_visible()
    save_proof(page, 'browser-back')


def test_cached_exit_state_is_rebuilt_on_pageshow(balu_browser):
    from playwright.sync_api import expect
    page, origin, data = balu_browser
    # Chromium can decline BFCache under automation. A 204 navigation keeps
    # the real pre-exit document alive; replay its persisted lifecycle event.
    # No production flags or security headers are changed to force caching.
    page.route('**/play?**', lambda route: route.fulfill(status=204))
    page.goto(origin + '/campaigns')
    page.locator(f'[data-dashboard-detail="campaign:{data["campaign_id"]}"]').first.click()
    with page.expect_request('**/play?**'):
        page.locator('[data-hub-action="open-session-dm"]').click()
    assert page.evaluate('BookScene.transitionInFlight') is True
    with page.expect_navigation(wait_until='domcontentloaded'):
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}))")
    page.locator('.book-dashboard-ribbon [data-dashboard-route="/characters"]').click()
    expect(page).to_have_url(origin + '/characters')


@pytest.mark.parametrize('width', [1440, 390])
def test_creation_and_preparation_have_no_legacy_view(balu_browser, width):
    from playwright.sync_api import expect
    page, origin, _ = balu_browser
    page.set_viewport_size({'width': width, 'height': 1000 if width == 1440 else 844})
    page.goto(origin + '/campaigns?classic=1&intent=create')
    expect(page.locator('#book-dashboard-scene')).to_be_visible()
    expect(page.locator('#campaignsClassicTemplate, body > header, body > main, body > footer')).to_have_count(0)
    page.locator('#campaignCreateName').fill('Modern campaign')
    save_proof(page, 'campaign-create')
    with page.expect_response(lambda r: r.url.endswith('/api/campaigns') and r.request.method == 'POST') as response:
        page.locator('#campaignCreateSubmit').click()
    assert response.value.status == 201
    campaign_id = response.value.json()['id']
    expect(page.locator('#campaignHubSessionPrep')).to_be_visible()
    page.get_by_role('button', name='Karten und Besetzung vorbereiten').click()
    expect(page.locator('#book-dashboard-scene #campaignPrep')).to_be_visible()
    expect(page.locator('#book-dashboard-scene #campaignAssetLibraryPanel')).to_be_visible()
    box = page.locator('#campaignPrep').bounding_box()
    assert box['x'] + box['width'] <= width + 1
    save_proof(page, 'campaign-prep')
    page.locator('#refreshDetailBtn').click()
    expect(page.locator('#book-dashboard-scene #campaignPrep')).to_be_visible()
    # Exercise a moved control against the real isolated upload + map APIs.
    from io import BytesIO
    from PIL import Image
    jpeg = BytesIO(); Image.new('RGB', (96, 64), '#58713c').save(jpeg, format='JPEG')
    page.locator(f'#newMapName_{campaign_id}').fill('Navigation JPEG map')
    page.locator(f'#newMapFile_{campaign_id}').set_input_files({
        'name': 'navigation.jpg', 'mimeType': 'image/jpeg', 'buffer': jpeg.getvalue()})
    with page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith(f'/campaigns/{campaign_id}/maps')) as uploaded:
        page.locator(f'#newMapUploadBtn_{campaign_id}').click()
    assert uploaded.value.status == 201
    expect(page.get_by_text('Navigation JPEG map', exact=True).first).to_be_visible()
    page.get_by_role('button', name='Zum Kampagnen-Hub').click()
    expect(page.locator('#campaignHubSessionPrep')).to_be_visible()


def test_late_campaign_response_does_not_replace_newer_route(balu_browser):
    from playwright.sync_api import expect
    page, origin, data = balu_browser
    pending = []
    page.goto(origin + '/campaigns')
    page.route(f'**/api/campaigns/{data["campaign_id"]}', lambda route: pending.append(route))
    page.locator(f'[data-dashboard-detail="campaign:{data["campaign_id"]}"]').first.click()
    page.locator('.book-dashboard-ribbon [data-dashboard-route="/characters"]').click()
    expect(page).to_have_url(origin + '/characters')
    assert len(pending) == 1
    pending[0].fulfill(response=pending[0].fetch())
    page.wait_for_timeout(100)
    expect(page.locator('#book-dashboard-scene')).to_have_attribute('data-book-route', 'characters')
    expect(page.locator('#campaignHubSessionPrep')).to_have_count(0)


def test_failed_snapshot_does_not_lock_future_navigation(balu_browser):
    from playwright.sync_api import expect
    page, origin, _ = balu_browser
    page.goto(origin + '/campaigns')
    expect(page.locator('#book-dashboard-scene')).to_be_visible()
    page.evaluate("""async () => {
        const load = BookScene.loadSceneSnapshot;
        BookScene.loadSceneSnapshot = async () => { throw new Error('test failure'); };
        try { await BookScene.pageTurn('/characters'); } catch (_) {}
        finally { BookScene.loadSceneSnapshot = load; }
    }""")
    page.locator('.book-dashboard-ribbon [data-dashboard-route="/characters"]').click()
    expect(page).to_have_url(origin + '/characters')
