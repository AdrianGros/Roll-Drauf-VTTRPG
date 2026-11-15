"""Live mobile-engine acceptance through login and campaign-hub navigation.

Uses the existing, scoped consolidation-layers create/cleanup fixture scripts.
The private /delivery/live-credentials.json is never copied into the repository.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from tests.test_playtable_token_clipboard_browser import client_point

ROOT = Path('/delivery')
ORIGIN = 'https://vtt.roll-drauf.de'
fixture = json.loads((ROOT / 'live-credentials.json').read_text())
proof = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
         'url': ORIGIN, 'hardware_test': False, 'engines': {}, 'errors': []}
expect.set_options(timeout=30000)
PROBE = '''window.__mobileWire=[];let factory;
Object.defineProperty(window,'io',{configurable:true,get(){return factory;},set(value){
factory=new Proxy(value,{apply(target,self,args){const socket=Reflect.apply(target,self,args);
socket.onAny((event,...args)=>window.__mobileWire.push({event,args}));return socket;}});}});'''


def request(page, path, method='GET', body=None):
    return page.evaluate('''async ([path,method,body])=>{const r=await fetch(path,{
        method,headers:Auth.buildHeaders(method,true),credentials:'include',
        ...(body?{body:JSON.stringify(body)}:{})});return {status:r.status,data:await r.json()}}''',
        [path, method, body])


def enter(context, kind, seat):
    context.add_init_script(PROBE)
    page = context.new_page()
    page.set_default_timeout(30000)
    page.on('pageerror', lambda error: proof['errors'].append(str(error)))
    page.goto(ORIGIN + '/login.html')
    page.locator('#loginUsername').fill(fixture['users'][kind]['username'])
    page.locator('#loginPassword').fill(fixture['users'][kind]['password'])
    page.locator('#passwordLoginSubmitBtn').tap()
    page.wait_for_url(lambda url: '/login' not in url)
    page.goto(f"{ORIGIN}/campaigns?campaign_id={fixture['campaign_id']}")
    action = 'open-session-dm' if seat == 'dm' else 'open-session'
    page.locator(f'[data-hub-action="{action}"][data-hub-session-id="{fixture["session_id"]}"]').tap()
    page.wait_for_url(lambda url: '/play' in url)
    expect(page.locator('body')).to_have_attribute('data-table-seat', seat)
    expect(page.locator('#mapWorld')).to_have_attribute('data-has-map', 'true')
    return page


def android_gestures(context, page, base):
    """Native Chromium touch input with independent server-state confirmation."""
    marker = page.locator(f'.token-marker[data-token-id="{fixture["token_ids"]["Hero"]}"]')
    cdp = context.new_cdp_session(page)

    def touch(kind, points):
        cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [
            {'id': i, 'x': x, 'y': y, 'radiusX': 2, 'radiusY': 2} for i, x, y in points]})

    def state():
        payload = request(page, base + '/bootstrap')
        assert payload['status'] == 200
        token = next(t for t in payload['data']['state_payload']['tokens'] if t['id'] == fixture['token_ids']['Hero'])
        return token['x'], token['y'], token['version']

    def center():
        box = marker.bounding_box()
        return box['x'] + box['width'] / 2, box['y'] + box['height'] / 2

    page.locator('#btnZoomFit').tap()
    before = state()
    x, y = center()
    touch('touchStart', [(0, x, y)])
    touch('touchMove', [(0, x + 40, y + 35)])
    touch('touchEnd', [])
    expect(marker).not_to_have_attribute('data-token-version', str(before[2]))
    moved = state()
    assert moved[:2] != before[:2]
    expect(page.locator('#tableSheet')).to_be_hidden()
    # Overlays deliberately intercept touch; uncover the token before testing pan.
    page.locator('#tokenSelectionClear').tap()
    for _ in range(6):
        page.locator('#btnZoomIn').tap()
    marker.scroll_into_view_if_needed()
    page.locator('[data-tool=pan]').tap()
    scroll = page.locator('#mapViewport').evaluate('(v) => [v.scrollLeft,v.scrollTop]')
    x, y = center()
    assert page.evaluate('''([x,y]) => document.elementFromPoint(x,y)?.closest('.token-marker')?.dataset.tokenId''', [x, y]) == str(fixture['token_ids']['Hero'])
    touch('touchStart', [(0, x, y)])
    touch('touchMove', [(0, x - 35, y - 25)])
    touch('touchEnd', [])
    assert page.locator('#mapViewport').evaluate('(v) => [v.scrollLeft,v.scrollTop]') != scroll
    assert state() == moved
    page.locator('#btnZoomFit').tap()
    viewport = page.locator('#mapViewport').bounding_box()
    x, y = viewport['x'] + 180, viewport['y'] + 230
    zoom = page.locator('#zoomLabel').inner_text()
    touch('touchStart', [(0, x - 35, y), (1, x + 35, y)])
    touch('touchMove', [(0, x - 65, y - 10), (1, x + 65, y + 10)])
    touch('touchEnd', [])
    expect(page.locator('#zoomLabel')).not_to_have_text(zoom)
    assert page.evaluate('() => visualViewport.scale') == 1
    assert state() == moved
    page.locator('[data-tool=select]').tap()
    for ending in ('cancel', 'second_finger'):
        page.locator('#btnZoomFit').tap()
        x, y = center()
        touch('touchStart', [(0, x, y)])
        touch('touchMove', [(0, x + 30, y + 30)])
        if ending == 'cancel':
            touch('touchCancel', [])
        else:
            touch('touchStart', [(0, x + 30, y + 30), (1, x + 70, y + 30)])
            touch('touchEnd', [])
        expect(page.locator('.token-marker.dragging')).to_have_count(0)
        assert state() == moved


with sync_playwright() as p:
    try:
        for engine, device in [('chromium', 'Pixel 7'), ('webkit', 'iPhone 13')]:
            report = {'profile': device, 'journey': 'Login → Kampagnenhub → Sitzung als DM', 'checks': {}}
            proof['engines'][engine] = report
            browser = getattr(p, engine).launch(headless=True, args=['--no-sandbox'] if engine == 'chromium' else [])
            dc = browser.new_context(**p.devices[device], reduced_motion='reduce')
            pc = browser.new_context(**p.devices[device], reduced_motion='reduce')
            requests = []
            pc.on('request', lambda req: requests.append(req.url))
            player = enter(pc, 'player', 'player')
            dm = enter(dc, 'dm', 'dm')
            expect(dm.locator('#presenceRoster')).to_contain_text(fixture['users']['player']['username'])
            expect(player.locator('#presenceRoster')).to_contain_text(fixture['users']['dm']['username'])
            expect(player.locator('.token-marker')).to_have_count(1)
            initial = dm.locator('.token-marker').count()
            base = f"/api/play/campaigns/{fixture['campaign_id']}/sessions/{fixture['session_id']}"
            assert request(player, base + '/surface')['status'] == 403
            assert 'Goblin' not in json.dumps(request(player, base + '/bootstrap')['data'])
            assert 'Goblin' not in player.evaluate('() => JSON.stringify(window.__mobileWire)')
            expect(player.locator('#tokenLayersWidget,#tokenSelectionBar')).to_have_count(0)
            assert not any('play-dm.js' in url or 'play-token-layers-dm' in url for url in requests)
            report['checks']['login_hub_role_and_private_data'] = 'pass'
            if engine == 'chromium':
                android_gestures(dc, dm, base)
                report['checks']['native_touch_drag_pan_pinch_cancel_server_state'] = 'pass'
            dm.locator('#btnZoomFit').tap()
            dm.locator(f'.token-marker[data-token-id="{fixture["token_ids"]["Hero"]}"]').tap()
            expect(dm.locator('#tokenWidget')).to_be_visible()
            dm.locator('.table-dock-close').tap()
            report['checks']['touch_token_inspector'] = 'pass'
            dm.locator('#dock-tokenLayersWidget').tap()
            dm.locator('[data-token-layer=dm_only]').tap()
            dm.locator('#tokenMultiSelect').tap()
            dm.locator('.table-dock-close').tap()
            for name in ('Goblin', 'Goblin 2'):
                dm.locator(f'.token-marker[data-token-id="{fixture["token_ids"][name]}"]').tap()
            expect(dm.locator('#tokenSelectionCount')).to_have_text('2 ausgewählt')
            dm.locator('#tokenSelectionCopy').tap()
            dm.screenshot(path=str(ROOT / f'{engine}-portrait-selection.png'))
            dm.locator('[data-selection-layer=public]').tap()
            expect(player.locator('.token-marker')).to_have_count(3)
            report['checks']['touch_multiselect_copy_and_reveal'] = 'pass'
            # Hide the same original tokens again; copied reinforcements stay private.
            for name in ('Goblin', 'Goblin 2'):
                dm.locator(f'.token-marker[data-token-id="{fixture["token_ids"][name]}"]').tap()
            dm.locator('[data-selection-layer=dm_only]').tap()
            expect(player.locator('.token-marker')).to_have_count(1)
            dm.locator('#dock-tokenLayersWidget').tap()
            dm.locator('#tokenLayerPaste').tap()
            expect(dm.locator('.token-marker')).to_have_count(initial + 2)
            expect(player.locator('.token-marker')).to_have_count(1)
            dm.locator('#tokenMultiSelect').tap()
            dm.locator('.table-dock-close').tap()
            dm.locator('#btnZoomFit').tap()
            dm.locator('[data-tool=token]').tap()
            dm.locator('.table-dock-close').tap()
            dm.touchscreen.tap(*client_point(dm, 350, 350))
            expect(dm.locator('#tokenCreateVisibility')).to_have_value('dm_only')
            dm.locator('#tokenCreateName').fill('Mobile reinforcement ' + engine)
            dm.locator('#btnTokenCreateConfirm').tap()
            expect(dm.locator('.token-marker')).to_have_count(initial + 3)
            expect(player.locator('.token-marker')).to_have_count(1)
            report['checks']['hide_paste_and_private_placement'] = 'pass'
            dm.set_viewport_size({'width': 844, 'height': 390})
            dm.locator('#dock-turnOrderWidget').tap()
            dm.locator('#btnStartCombat').tap()
            expect(dm.locator('#btnNextTurn')).to_be_visible()
            summary = dm.locator('#turnOrderSummary').inner_text()
            dm.locator('#btnNextTurn').tap()
            expect(dm.locator('#turnOrderSummary')).not_to_have_text(summary)
            dm.locator('#btnEndCombat').tap()
            expect(dm.locator('#btnStartCombat')).to_be_visible()
            dm.screenshot(path=str(ROOT / f'{engine}-landscape-initiative.png'))
            dm.locator('.table-dock-close').tap()
            dm.locator('[data-tool=pan]').tap()
            report['checks']['landscape_initiative_and_toolbar'] = 'pass'
            dm.set_viewport_size({'width': 390, 'height': 844})
            dm.locator('#btnChatToggle').tap()
            text = 'Mobile Live-Abnahme ' + engine
            dm.locator('#chatInput').fill(text)
            dm.locator('#btnSendChat').tap()
            expect(dm.locator('#chatLog')).to_contain_text(text)
            dm.locator('#btnChatClose').tap()
            dm.locator('#btnSidebarToggle').tap()
            dm.locator('.sidebar-tab[data-tab=tools]').tap()
            dm.locator('[data-dice-preset="1d20"]').tap()
            dm.locator('#btnRoll').tap()
            expect(dm.locator('#diceResult')).not_to_contain_text('Noch kein Wurf')
            dm.locator('.sidebar-tab[data-tab=journal]').tap()
            expect(dm.locator('#panel-journal')).to_be_visible()
            dm.locator('#btnSidebarClose').tap()
            report['checks']['chat_dice_and_journal'] = 'pass'
            dm.reload()
            expect(dm.locator('body')).to_have_attribute('data-table-seat', 'dm')
            expect(dm.locator('.token-marker')).to_have_count(initial + 3)
            player.reload()
            expect(player.locator('.token-marker')).to_have_count(1)
            expect(player.locator('#presenceRoster')).to_contain_text(fixture['users']['dm']['username'])
            assert 'Goblin' not in json.dumps(request(player, base + '/bootstrap')['data'])
            assert 'Goblin' not in player.evaluate('() => JSON.stringify(window.__mobileWire)')
            report['checks']['reload_persistence_and_player_privacy'] = 'pass'
            dm.screenshot(path=str(ROOT / f'{engine}-portrait-reloaded.png'))
            browser.close()
        assert not proof['errors'], proof['errors']
        proof['status'] = 'pass'
    except Exception as error:
        proof['status'] = 'fail'
        proof['failure'] = str(error)
        if 'dm' in globals():
            dm.screenshot(path=str(ROOT / 'failure.png'))
        raise
    finally:
        proof['finished_at'] = datetime.now(timezone.utc).isoformat()
        (ROOT / 'live.json').write_text(json.dumps(proof, indent=2, ensure_ascii=False))
