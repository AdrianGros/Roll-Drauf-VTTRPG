"""Touch journeys on both engines; Chromium CDP supplies real multi-touch input."""
import pytest
from playwright.sync_api import expect, sync_playwright

from tests.play_shared import create_token
from tests.test_personal_actions_browser import action_site  # noqa: F401
from tests.test_playtable_token_clipboard_browser import client_point
from vtt.extensions import db
from vtt.models import Campaign, CampaignMap, GameSession, TokenState
from vtt.play.service import ensure_session_state



def close_windows(page):
    for _ in range(12):
        visible = page.locator('.play-window:visible')
        if not visible.count(): return
        target = visible.evaluate_all("rows => rows.sort((a,b) => Number(b.style.zIndex)-Number(a.style.zIndex))[0].id")
        page.locator('#' + target + ' .play-window-head button').tap()

def seed_hidden(app, info):
    with app.app_context():
        campaign = db.session.get(Campaign, info['campaign'])
        session = db.session.get(GameSession, info['session'])
        map_ = db.session.get(CampaignMap, session.map_id)
        map_.width, map_.height, map_.grid_size = 1200, 900, 70
        for name, x in [('Goblin', 140), ('Goblin 2', 210)]:
            token = create_token(campaign, session, ensure_session_state(campaign, session), campaign.owner_id,
                                 name=name, token_type='monster', x=x, y=140)
            token.metadata_json = {'position_mode': 'pixel'}
            token.visibility = 'dm_only'
        db.session.commit()


def open_dm(browser, origin, info, device=None):
    options = device or {'viewport': {'width': 390, 'height': 844}, 'is_mobile': True,
                         'has_touch': True, 'device_scale_factor': 2}
    context = browser.new_context(**options, reduced_motion='reduce')
    context.add_cookies([{'name': 'access_token_cookie', 'value': info['dm_auth'], 'url': origin, 'httpOnly': True}])
    page = context.new_page()
    page.set_default_timeout(15000)
    page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=dm")
    expect(page.locator('body')).to_have_attribute('data-table-seat', 'dm')
    expect(page.locator('#presenceRoster')).to_contain_text('action-dm')
    expect(page.locator('#mapWorld')).to_have_attribute('data-has-map', 'true')
    return context, page


@pytest.mark.parametrize('engine', ['chromium', 'webkit'])
def test_mobile_dm_touch_layers_clipboard_and_core_panels(action_site, engine):
    app, origin, info = action_site
    seed_hidden(app, info)
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, args=['--no-sandbox'] if engine == 'chromium' else [])
        context, page = open_dm(browser, origin, info, p.devices['Pixel 7' if engine == 'chromium' else 'iPhone 13'])
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        player_context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        player_context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
        player = player_context.new_page()
        requests = []
        player.on('request', lambda request: requests.append(request.url))
        player.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player")
        expect(page.locator('#presenceRoster')).to_contain_text('action-player')
        expect(player.locator('.token-marker')).to_have_count(1)
        page.locator('#dock-tokenWidget').tap();page.locator('#dock-tokenLayersWidget').tap()
        page.locator('[data-token-layer=dm_only]').tap()
        page.locator('#tokenMultiSelect').tap()
        expect(page.locator('#tokenMultiSelect')).to_have_attribute('aria-pressed', 'true')
        close_windows(page)
        page.locator('.token-marker:not(.token-inactive-layer)', has_text='Goblin').first.tap()
        page.locator('.token-marker', has_text='Goblin 2').tap()
        expect(page.locator('#tokenSelectionCount')).to_have_text('2 ausgewählt')
        page.locator('#tokenSelectionCopy').tap()
        page.locator('[data-selection-layer=public]').tap()
        expect(player.locator('.token-marker')).to_have_count(3)
        page.locator('#dock-tokenWidget').tap();page.locator('#dock-tokenLayersWidget').tap()
        page.locator('[data-token-layer=dm_only]').tap()
        page.locator('#tokenLayerPaste').tap()
        expect(page.locator('.token-marker')).to_have_count(5)
        expect(player.locator('.token-marker')).to_have_count(3)
        page.locator('#tokenMultiSelect').tap()
        close_windows(page)
        page.locator('.token-marker:not(.token-inactive-layer)', has_text='Goblin').first.tap()
        expect(page.locator('#tokenWidget')).to_be_visible()
        close_windows(page)
        page.locator('#btnZoomFit').tap()
        page.locator('#dock-tokenWidget').tap()
        page.locator('#btnPlaceNewToken').tap()
        close_windows(page)
        page.touchscreen.tap(*client_point(page, 350, 350))
        expect(page.locator('#tokenCreatePanel')).to_be_visible()
        expect(page.locator('#tokenCreateVisibility')).to_have_value('dm_only')
        page.locator('#tokenCreateName').fill('Mobile reinforcement')
        page.locator('#btnTokenCreateConfirm').tap()
        expect(page.locator('.token-marker')).to_have_count(6)
        expect(player.locator('.token-marker')).to_have_count(3)
        # Rotation must leave every dock entry and pan reachable using touch.
        page.set_viewport_size({'width': 844, 'height': 390})
        page.locator('#dock-turnOrderWidget').tap()
        expect(page.locator('#turnOrderWidget')).to_be_visible()
        page.locator('#btnStartCombat').tap()
        expect(page.locator('#btnNextTurn')).to_be_visible()
        summary = page.locator('#turnOrderSummary').inner_text()
        page.locator('#btnNextTurn').tap()
        expect(page.locator('#turnOrderSummary')).not_to_have_text(summary)
        page.locator('#btnEndCombat').tap()
        expect(page.locator('#btnStartCombat')).to_be_visible()
        close_windows(page)
        page.locator('[data-tool=pan]').tap()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('#btnChatToggle').tap()
        page.locator('#chatInput').fill('Hallo vom Handy')
        page.locator('#btnSendChat').tap()
        expect(page.locator('#campaignRoomLog')).to_contain_text('Hallo vom Handy')
        page.locator('#window-panel-chat .play-window-head button').tap()
        page.locator('#btnDiceWindow').tap()
        page.locator('[data-dice-preset="1d20"]').tap()
        page.locator('#btnRoll').tap()
        expect(page.locator('#diceResult')).not_to_contain_text('Noch kein Wurf')
        close_windows(page)
        page.locator('#btnTableMore').tap();page.locator('#btnSidebarToggle').tap()
        expect(page.locator('#panel-journal')).to_be_visible()
        page.locator('#window-panel-journal .play-window-head button').tap()
        page.reload()
        expect(page.locator('body')).to_have_attribute('data-table-seat', 'dm')
        expect(page.locator('.token-marker')).to_have_count(6)
        player.reload()
        expect(player.locator('.token-marker')).to_have_count(3)
        expect(player.locator('#tokenLayersWidget,#tokenSelectionBar')).to_have_count(0)
        assert not any('play-dm.js' in url or 'play-token-layers-dm' in url for url in requests)
        assert not errors, errors
        page.screenshot(path=f'/tmp/mobile-{engine}-dm.png')
        context.close()
        browser.close()


def test_android_real_touch_drag_pan_pinch_and_cancel(action_site):
    app, origin, info = action_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context, page = open_dm(browser, origin, info)
        page.locator('#btnZoomFit').tap()
        marker = page.locator('.token-marker').first
        cdp = context.new_cdp_session(page)

        def touch(kind, points):
            cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [
                {'id': i, 'x': x, 'y': y, 'radiusX': 2, 'radiusY': 2} for i, x, y in points]})

        def position():
            with app.app_context():
                db.session.expire_all()
                token = db.session.get(TokenState, info['token'])
                return token.x, token.y, token.version

        box = marker.bounding_box()
        x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        before = position()
        touch('touchStart', [(0, x, y)])
        touch('touchMove', [(0, x + 50, y + 45)])
        touch('touchEnd', [])
        expect(marker).not_to_have_attribute('data-token-version', str(before[2]))
        moved = position()
        assert moved[:2] != before[:2]
        expect(page.locator('#tableSheet')).to_be_hidden()
        # PAN starting on a token must move the map, never the token.
        for _ in range(6):
            page.locator('#btnZoomIn').tap()
        page.locator('[data-tool=pan]').tap()
        from tests.play_canvas_shared import pan_by,usable
        area=usable(page);target=marker.bounding_box()
        pan_by(page,(area['left']+area['right'])/2-target['x']-target['width']/2,(area['top']+area['bottom'])/2-target['y']-target['height']/2,cdp)
        box = marker.bounding_box()
        x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        map_before = page.locator('#mapWorld').bounding_box()
        touch('touchStart', [(0, x, y)])
        touch('touchMove', [(0, x - 45, y - 30)])
        touch('touchEnd', [])
        assert page.locator('#mapWorld').bounding_box()['x'] != map_before['x']
        assert position() == moved
        # Real multi-touch changes map zoom, not the page scale.
        page.locator('#btnZoomFit').tap()
        viewport = page.locator('#mapViewport').bounding_box()
        x, y = viewport['x'] + 180, viewport['y'] + 230
        zoom = page.locator('#zoomLabel').inner_text()
        touch('touchStart', [(0, x - 35, y), (1, x + 35, y)])
        touch('touchMove', [(0, x - 65, y - 10), (1, x + 65, y + 10)])
        touch('touchEnd', [])
        expect(page.locator('#zoomLabel')).not_to_have_text(zoom, timeout=5000)
        assert page.evaluate('visualViewport.scale') == 1
        assert position() == moved
        # Browser cancellation and a second finger discard an unsaved token drag.
        page.locator('[data-tool=select]').tap()
        for end in ('cancel', 'pinch'):
            page.locator('#btnZoomFit').tap()
            box = marker.bounding_box()
            x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
            touch('touchStart', [(0, x, y)])
            touch('touchMove', [(0, x + 30, y + 30)])
            if end == 'cancel':
                touch('touchCancel', [])
            else:
                touch('touchStart', [(0, x + 30, y + 30), (1, x + 70, y + 30)])
                touch('touchEnd', [])
            expect(page.locator('.token-marker.dragging')).to_have_count(0)
            assert position() == moved
        # A tap still exposes token details after separating it from dragging.
        marker.tap()
        expect(page.locator('#tokenWidget')).to_be_visible()
        expect(page.locator('#window-tokenWidget')).to_be_visible()
        browser.close()
