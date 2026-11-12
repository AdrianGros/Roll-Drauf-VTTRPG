"""C01 acceptance through delayed/failed network responses and real controls."""
import json
import re

import pytest

from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import contrast, preferences


def gate_first_sheet_response(context, character_id, fail=False):
    context.add_init_script("""({target, fail}) => {
        const nativeFetch = window.fetch.bind(window);
        let armed = true;
        window.__c01Release = null;
        window.fetch = (input, options) => {
            const path = new URL(typeof input === 'string' ? input : input.url, location.href).pathname;
            if (armed && path === target) {
                armed = false;
                return new Promise((resolve, reject) => {
                    window.__c01Release = () => fail
                        ? resolve(new Response(JSON.stringify({error:'Controlled C01 load failure'}), {
                            status:503, headers:{'Content-Type':'application/json'}}))
                        : nativeFetch(input, options).then(resolve, reject);
                });
            }
            return nativeFetch(input, options);
        };
    }""".replace('({target, fail}) =>', '(function({target, fail})')
        + ')(' + json.dumps({'target':f'/api/characters/{character_id}/sheet','fail':fail}) + ');')


@pytest.mark.parametrize('engine,width,language,theme', [
    ('chromium',1440,'de','paper'), ('firefox',390,'en','night'),
])
def test_delayed_sheet_has_no_legacy_flash_and_movement_control_works(
        action_site,engine,width,language,theme):
    from playwright.sync_api import expect, sync_playwright
    _app,origin,info = action_site
    with sync_playwright() as playwright:
        browser = getattr(playwright,engine).launch(headless=True,
            args=['--no-sandbox'] if engine=='chromium' else [])
        context = browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        preferences(context,language=language,theme=theme,unit='m')
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        gate_first_sheet_response(context,info['character'])
        page=context.new_page();page.set_default_timeout(30000)
        page.goto(f"{origin}/character-sheet?id={info['character']}")
        page.wait_for_function('() => typeof window.__c01Release === "function"')
        expect(page.locator('#sheetLoadState')).to_be_visible()
        expect(page.locator('#sheetSpread')).not_to_be_visible()
        expect(page.locator('#charName')).not_to_be_visible()
        expect(page.locator('#sheetLoadMessage')).to_have_text(
            'Loading character sheet …' if language=='en' else 'Charakterbogen wird geladen …')
        page.evaluate('window.__c01Release()')
        expect(page.locator('#sfTab-play')).to_be_visible()
        expect(page.locator('#sheetLoadState')).not_to_be_visible()
        expect(page.locator('#sheetModeActionBtn')).to_have_count(1)
        expect(page.locator('#sheetModeActionBtn')).to_be_visible()
        expect(page.locator('.sheet-journey-nav [data-book-route="/characters"]')).to_have_count(0)
        expect(page.locator('.sheet-journey-nav [data-creation-engine-nav]')).to_have_count(0)
        movement=page.locator('[data-sheet-stat="speed"] .srd-sheet-value')
        expect(movement).to_have_text(re.compile(r'\d.* m$'))
        original=movement.inner_text()
        page.locator('#sfUnits').select_option('ft')
        expect(movement).to_have_text(re.compile(r'\d.* ft$'))
        page.locator('#sfUnits').select_option('m')
        expect(movement).to_have_text(original)
        assert page.evaluate('document.documentElement.scrollWidth') <= width+1
        browser.close()


def test_failed_first_sheet_response_keeps_error_and_working_retry(action_site):
    from playwright.sync_api import expect,sync_playwright
    _app,origin,info=action_site
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        gate_first_sheet_response(context,info['character'],fail=True)
        page=context.new_page();page.set_default_timeout(30000)
        page.goto(f"{origin}/character-sheet?id={info['character']}")
        page.wait_for_function('() => typeof window.__c01Release === "function"')
        page.evaluate('window.__c01Release()')
        expect(page.locator('#sheetLoadState')).to_have_attribute('data-state','error')
        expect(page.locator('#sheetLoadState')).to_be_visible()
        expect(page.locator('#sheetSpread')).not_to_be_visible()
        page.locator('#sheetLoadRetry').click()
        expect(page.locator('#sfTab-play')).to_be_visible()
        expect(page.locator('#sheetLoadState')).not_to_be_visible()
        browser.close()


def test_non_json_sheet_response_shows_error_and_can_retry(action_site):
    from playwright.sync_api import expect,sync_playwright
    _app,origin,info=action_site
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context()
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000)
        pattern=f"**/api/characters/{info['character']}/sheet"
        def non_json_once(route):
            route.fulfill(status=200,content_type='text/html',body='<html>Temporary response</html>')
            page.unroute(pattern,non_json_once)
        page.route(pattern,non_json_once)
        page.goto(f"{origin}/character-sheet?id={info['character']}")
        expect(page.locator('#sheetLoadState')).to_have_attribute('data-state','error')
        expect(page.locator('#sheetSpread')).not_to_be_visible()
        page.locator('#sheetLoadRetry').click()
        expect(page.locator('#sfTab-play')).to_be_visible()
        expect(page.locator('#sheetLoadState')).not_to_be_visible()
        browser.close()


@pytest.mark.parametrize('theme,language',[('paper','de'),('night','en')])
def test_creator_keeps_book_frame_and_readable_controls(action_site,theme,language):
    from playwright.sync_api import expect,sync_playwright
    _app,origin,info=action_site
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
        preferences(context,language=language,theme=theme)
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000)
        page.goto(origin+'/srd-creator')
        expect(page.locator('#scMain')).to_be_visible()
        page.locator('#scNewGuided').click()
        expect(page.locator('#scSteps .sc-step').first).to_be_visible()
        contrast(page,'.sc-step, .regelwerk-titlebar h1')
        assert page.evaluate('document.documentElement.scrollWidth') <= 391
        assert page.locator('.regelwerk-site-header').evaluate(
            'node=>getComputedStyle(node).borderTopStyle') == 'solid'
        browser.close()


def rename_user_content(app, info):
    """User content that collides with authored German UI words ("Aktiv", "Speichern")."""
    from vtt.extensions import db
    from vtt.models import Campaign, Character
    with app.app_context():
        db.session.get(Campaign, info['campaign']).name = 'Aktiv'
        db.session.get(Character, info['character']).name = 'Speichern'
        db.session.commit()


def english_context(playwright, origin, auth, width, theme='paper'):
    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
    preferences(context, language='en', theme=theme)
    context.add_cookies([{'name': 'access_token_cookie', 'value': auth, 'url': origin, 'httpOnly': True}])
    page = context.new_page()
    page.set_default_timeout(30000)
    return browser, page


@pytest.mark.parametrize('theme', ['paper', 'night'])
def test_english_hub_ledger_and_archive_keep_user_names_and_localize_authored_text(action_site, theme):
    from playwright.sync_api import expect, sync_playwright
    app, origin, info = action_site
    rename_user_content(app, info)
    with sync_playwright() as playwright:
        # DM: campaign ledger + hub (primary action button and name-bearing hint).
        browser, page = english_context(playwright, origin, info['dm_auth'], 1440, theme)
        page.goto(origin + '/campaigns')
        expect(page.get_by_text('Aktiv', exact=True).first).to_be_visible()
        nav = page.locator('.book-dashboard-ribbon')
        expect(nav).to_have_count(1)
        assert 'Kampagnen' not in nav.inner_text() and 'Übersicht' not in nav.inner_text()
        page.evaluate(f"viewCampaign({info['campaign']}, false)")
        expect(page.get_by_text('Aktiv', exact=True).first).to_be_visible()
        body = page.locator('body')
        expect(body).to_contain_text('is already running')
        text = body.inner_text()
        for german in ('läuft bereits', 'Zu Play', 'Session fortsetzen', 'Spieler einladen', 'Session betreten'):
            assert german not in text, german
        contrast(page, '.hub-badge, .btn-primary, .book-dashboard-ribbon-btn')
        assert page.evaluate('document.documentElement.scrollWidth') <= 1441
        browser.close()

        # Player: characters archive and dashboard.
        browser, page = english_context(playwright, origin, info['player_auth'], 390, theme)
        page.goto(origin + '/characters')
        expect(page.get_by_text('Speichern', exact=True).first).to_be_visible()
        expect(page.locator('.book-dashboard-ribbon')).to_have_count(1)
        contrast(page, '.book-dashboard-ribbon-btn')
        page.goto(origin + '/dashboard')
        expect(page.locator('.book-dashboard-ribbon')).to_have_count(1)
        contrast(page, '.book-dashboard-ribbon-btn')
        assert page.evaluate('document.documentElement.scrollWidth') <= 391
        browser.close()


def test_sheet_keeps_main_navigation_exactly_once_and_character_name_verbatim(action_site):
    from playwright.sync_api import expect, sync_playwright
    app, origin, info = action_site
    rename_user_content(app, info)
    with sync_playwright() as playwright:
        browser, page = english_context(playwright, origin, info['player_auth'], 1440)
        page.goto(f"{origin}/character-sheet?id={info['character']}")
        expect(page.locator('#sfTab-play')).to_be_visible()
        expect(page.locator('.book-dashboard-ribbon')).to_have_count(1)
        expect(page.locator('.book-dashboard-ribbon a[href="/characters"]')).to_have_count(1)
        expect(page.locator('.book-dashboard-ribbon a[href="/campaigns"]')).to_have_count(1)
        expect(page.locator('#charName')).to_have_value('Speichern')
        expect(page.locator('#sheetLoadState')).not_to_be_visible()
        contrast(page, '.book-dashboard-ribbon-btn')
        browser.close()


@pytest.mark.parametrize('width,theme,language', [
    (320, 'paper', 'de'), (320, 'night', 'en'), (1440, 'paper', 'en'), (1440, 'night', 'de'),
])
def test_creator_is_readable_without_overflow_at_320_and_1440(action_site, width, theme, language):
    from playwright.sync_api import expect, sync_playwright
    _app, origin, info = action_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
        preferences(context, language=language, theme=theme)
        context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'],
                              'url': origin, 'httpOnly': True}])
        page = context.new_page()
        page.set_default_timeout(30000)
        page.goto(origin + '/srd-creator')
        expect(page.locator('#scMain')).to_be_visible()
        page.locator('#scNewGuided').click()
        expect(page.locator('#scSteps .sc-step').first).to_be_visible()
        contrast(page, '.sc-step, .regelwerk-titlebar h1, .book-dashboard-ribbon-btn')
        assert page.evaluate('document.documentElement.scrollWidth') <= width + 1
        assert page.locator('.book-dashboard-ribbon').count() == 1
        browser.close()


def _contains_id(node, wanted):
    if isinstance(node, dict):
        return node.get('id') == wanted or any(_contains_id(v, wanted) for v in node.values())
    if isinstance(node, list):
        return any(_contains_id(v, wanted) for v in node)
    return False


def test_creator_draft_survives_language_save_and_reload(action_site):
    from playwright.sync_api import expect, sync_playwright
    _app, origin, info = action_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        preferences(context, language='de')
        context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'],
                              'url': origin, 'httpOnly': True}])
        page = context.new_page()
        page.set_default_timeout(30000)
        page.goto(origin + '/srd-creator')
        expect(page.locator('#scMain')).to_be_visible()
        with page.expect_response(lambda r: r.request.method == 'POST' and r.url.rstrip('/').endswith('/drafts')) as made:
            page.locator('#scNewGuided').click()
        payload = made.value.json()
        draft_id = (payload.get('draft') or payload)['id']
        drafts_url = made.value.url
        expect(page.locator('#scSteps .sc-step').first).to_be_visible()

        # Language is changed through the real display dialog, which reloads the page.
        page.locator('#vttDisplayOpen').click()
        page.locator('#vttDisplay-language').select_option('en')
        with page.expect_navigation():
            page.locator('.vtt-display-actions button').last.click()
        expect(page.locator('html')).to_have_attribute('lang', 'en')
        expect(page.locator('#scMain')).to_be_visible()
        listing = page.evaluate(
            '''async (url) => (await fetch(url, {credentials: 'same-origin'})).json()''', drafts_url)
        assert _contains_id(listing, draft_id), listing
        browser.close()
