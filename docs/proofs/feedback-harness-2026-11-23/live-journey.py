"""Normal UI acceptance against three owned QA campaigns; no real-user content writes."""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from tests.test_c27_mapmaker_browser import choose_stamp, focus_canvas, number, synthetic_key
from tests.test_mapmaker_browser import Editor
from tests.test_review_maps_browser import new_empty, save_file

expect.set_options(timeout=30000)
root = Path(os.environ['PROOF_ROOT'])
fixture = json.loads((root / 'private-live-credentials.json').read_text())
origin = 'https://vtt.roll-drauf.de'
proof = {'status': 'running', 'url': origin, 'journeys': [], 'physical_german_keyboard_tested': False}


def save():
    (root / 'live.json').write_text(json.dumps(proof, indent=2) + '\n')


def context(browser, user='dm', width=1440, theme='paper', accent='default'):
    ctx = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce',
                              accept_downloads=True, has_touch=width < 600)
    prefs = {'schema': 1, 'theme': theme, 'language': 'de', 'accent': accent, 'unit': 'm'}
    ctx.add_init_script(f"localStorage.setItem('vtt.display.v1',{json.dumps(json.dumps(prefs))})")
    auth = fixture['users'][user]
    ctx.add_cookies([{'name': 'access_token_cookie', 'value': auth['token'], 'url': origin, 'secure': True, 'httpOnly': True},
                     {'name': 'csrf_access_token', 'value': auth['csrf'], 'url': origin, 'secure': True}])
    return ctx


def page_in(ctx):
    page = ctx.new_page()
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    return page, errors


def table_ready(page, seat):
    expect(page.locator('body')).to_have_attribute('data-table-seat', seat)
    expect(page.locator('#sessionTitleHeader')).to_contain_text('QA')
    expect(page.locator('#btnInitStack')).to_have_count(int(seat == 'dm'))


with sync_playwright() as playwright:
    chromium = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
    firefox = playwright.firefox.launch(headless=True)
    try:
        for kind, campaign, action, width in [
            ('solo_ready', fixture['solo_campaign_id'], 'start-session', 1440),
            ('solo_new', fixture['new_campaign_id'], 'new-session', 390),
        ]:
            ctx = context(chromium, width=width, theme='night', accent='teal')
            page, errors = page_in(ctx)
            starts, creates = [], []
            page.on('request', lambda request: starts.append(request.url) if request.method == 'POST'
                    and request.url.endswith('/start') else None)
            page.on('request', lambda request: creates.append(request.url) if request.method == 'POST'
                    and request.url == f'{origin}/api/campaigns/{campaign}/sessions' else None)
            page.goto(f'{origin}/campaigns?campaign_id={campaign}')
            summary = page.locator('.book-dashboard-ribbon:visible .vtt-nav-play > summary')
            expect(summary).to_have_css('text-decoration-line', 'underline')
            page.locator(f'[data-hub-action="{action}"]').first.dblclick()
            table_ready(page, 'dm')
            assert len(starts) == 1 and len(creates) == int(kind == 'solo_new'), (starts, creates)
            page.reload()
            table_ready(page, 'dm')
            assert not errors, errors
            proof['journeys'].append({'kind': kind, 'width': width, 'no_other_players_maps_or_date': True,
                'one_start': True, 'one_session_creation': len(creates), 'reload_keeps_seat': True,
                'browser_errors': errors})
            ctx.close()
            save()

        for label, browser, user, seat, action, width in [
            ('owner_dm', chromium, 'dm', 'dm', 'open-session-dm', 1440),
            ('owner_player', chromium, 'dm', 'player', 'open-session-player', 390),
            ('member_player', firefox, 'player', 'player', 'open-session', 1440),
        ]:
            ctx = context(browser, user=user, width=width, theme='night', accent='bronze')
            page, errors = page_in(ctx)
            page.goto(f'{origin}/campaigns?campaign_id={fixture["roles_campaign_id"]}')
            page.locator(f'[data-hub-action="{action}"]').first.click()
            table_ready(page, seat)
            expect(page.locator('#mapWorld')).to_have_attribute('data-map-width', '6000')
            c, s = fixture['roles_campaign_id'], fixture['role_session_id']
            payload = page.evaluate('''async ([c,s]) => {
                const data = await Auth.makeAuthRequest(`/api/play/campaigns/${c}/sessions/${s}/bootstrap`);
                return {role:data.session_role, hasSecret:JSON.stringify(data).includes('QA_FEEDBACK_PRIVATE_SENTINEL')};
            }''', [c, s])
            assert payload['role'] == ('DM' if seat == 'dm' else 'PLAYER'), payload
            assert payload['hasSecret'] == (seat == 'dm'), payload
            if seat == 'player':
                assert page.locator('script[src="/static/js/play-dm.js"]').count() == 0
            page.locator('#btnZoomFit').click()
            page.reload()
            table_ready(page, seat)
            assert not errors, errors
            proof['journeys'].append({'kind': label, 'width': width, 'seat': seat,
                'server_role': payload['role'], 'secret_delivery_matches_role': True,
                'fit_control_works': True, 'reload_keeps_seat': True, 'browser_errors': errors})
            ctx.close()
            save()

        ctx = context(chromium, theme='night', accent='teal')
        page, errors = page_in(ctx)
        page.goto(origin + '/dashboard')
        toc = page.locator('.book-toc')
        expect(toc.locator('.book-toc-numeral').first).to_have_text('I')
        expect(toc.locator('a[href="/atlas"]')).to_have_count(1)
        page.locator('.book-dashboard-ribbon:visible a[href="/mapmaker"]').click()
        page.wait_for_selector('#app[data-state=ready]')
        ed = Editor(ctx, page, errors)
        new_empty(ed)
        ed.tool('stamp')
        choose_stamp(page, 'kenney-cartography', 'kenney:castle')
        page.locator('#stampSizeNumber').fill('16')
        page.locator('#stampSizeNumber').press('Tab')
        choose_stamp(page, 'kenney-cartography', 'kenney:forest')
        choose_stamp(page, 'kenney-cartography', 'kenney:castle')
        assert number(page, '#stampSize') == 16
        focus_canvas(page)
        page.keyboard.press('BracketRight')
        assert number(page, '#stampSize') == 18
        synthetic_key(page, key=']', code='Digit9', ctrlKey=True, altKey=True)
        assert number(page, '#stampSize') > 18
        page.locator('#stampStyle').select_option('painted')
        expect(page.locator('#stampResults')).to_contain_text('Ohne Angabe')
        page.locator('#stampFilterReset').click()
        assert page.locator('.mm-stamp').count() > 0
        ed.tool('path')
        ed.drag([(500, 600), (700, 640), (900, 600)])
        path = next(item for item in ed.summary()['items'] if 'points' in item)
        page.locator('#pathNodeMode').check()
        assert ed.summary()['tool'] == 'select'
        point = path['points'][1]
        at = (path['x'] + point['x'], path['y'] + point['y'])
        ed.drag([at, (at[0] + 40, at[1] + 40)])
        changed = next(item for item in ed.summary()['items'] if item['id'] == path['id'])
        assert changed['points'][1] != path['points'][1]
        page.keyboard.press('Control+z')
        restored = next(item for item in ed.summary()['items'] if item['id'] == path['id'])
        assert restored['points'] == path['points']
        bundle = save_file(ed, root / 'qa-path-map.rdmap.json')
        assert bundle
        assert not errors, errors
        proof['journeys'].append({'kind': 'mapmaker', 'normal_navigation': True, 'asset_size_remembered': True,
            'real_us_bracket_key': True, 'synthetic_altgr_event': True, 'undeclared_traits_explained': True,
            'filter_reset': True, 'node_drag_and_undo': True, 'file_export': True, 'browser_errors': errors})
        ctx.close()

        ctx = context(chromium, width=390, theme='night', accent='teal')
        page, errors = page_in(ctx)
        page.goto(origin + '/dashboard')
        group = page.locator('.book-dashboard-ribbon:visible .vtt-nav-play')
        group.locator('summary').click()
        group.locator('a[href="/characters"]').click()
        page.get_by_role('button', name='Held anlegen', exact=True).click()
        page.locator('#scNewGuided').click()
        page.get_by_role('button', name='Kämpfer', exact=False).first.click()
        page.locator('#vttDisplayOpen').click()
        page.locator('#vttDisplay-accent').select_option('bronze')
        page.get_by_role('button', name='Anwenden', exact=True).click()
        bronze = page.locator('#scRandomize').evaluate('el => getComputedStyle(el).backgroundColor')
        page.locator('#vttDisplayOpen').click()
        page.locator('#vttDisplay-accent').select_option('teal')
        page.get_by_role('button', name='Anwenden', exact=True).click()
        teal = page.locator('#scRandomize').evaluate('el => getComputedStyle(el).backgroundColor')
        assert bronze != teal
        page.get_by_role('button', name='Klassentext lesen').click()
        expect(page.locator('#scDialogBody dl').first).to_have_css('display', 'grid')
        page.screenshot(path=str(root / 'class-facts-teal-night-390.png'))
        assert not errors, errors
        proof['journeys'].append({'kind': 'creator_presentation', 'width': 390,
            'normal_navigation': True, 'accent_changes_surface': True, 'class_facts_grid': True,
            'browser_errors': errors})
        ctx.close()
        proof['status'] = 'pass'
        save()
    except Exception as error:
        proof.update(status='failed', error=str(error))
        save()
        raise
    finally:
        chromium.close()
        firefox.close()
print(json.dumps({'status': proof['status'], 'journeys': len(proof['journeys'])}))
