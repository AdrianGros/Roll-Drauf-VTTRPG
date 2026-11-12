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


CREATOR_CLEAN = '() => !!window.SrdCreator && !SrdCreator.app.dirty && !SrdCreator.app.saving'
TYPED_NAME = 'Speichern bleibt'

# Holds back only the next real PUT /api/srd-creator/drafts/{id}; every other request passes.
GATE_NEXT_DRAFT_PUT = r"""() => {
    const nativeFetch = window.fetch.bind(window);
    window.__draftGate = { armed: true, started: false, release: null };
    window.fetch = (input, options) => {
        const request = typeof input === 'string' ? null : input;
        const url = new URL(request ? request.url : input, location.href);
        const method = String((options && options.method) || (request && request.method) || 'GET').toUpperCase();
        if (window.__draftGate.armed && method === 'PUT' && /^\/api\/srd-creator\/drafts\/\d+$/.test(url.pathname)) {
            window.__draftGate.armed = false;
            window.__draftGate.started = true;
            return new Promise((resolve, reject) => {
                window.__draftGate.release = () => nativeFetch(input, options).then(resolve, reject);
            });
        }
        return nativeFetch(input, options);
    };
}"""


def server_identity_name(page, draft_id):
    data = page.evaluate(
        '''async (id) => (await fetch('/api/srd-creator/drafts/' + id, {credentials: 'same-origin'})).json()''',
        draft_id)
    return ((data['draft'].get('state') or {}).get('identity') or {}).get('name')


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
        expect(page.locator('#scSteps .sc-step').first).to_be_visible()

        # Real description step, then wait until nothing is pending.
        page.locator('#scSteps .sc-step').filter(has_text='Beschreibung').first.click()
        name_input = page.locator('#scId-name')
        expect(name_input).to_be_visible()
        page.wait_for_function(CREATOR_CLEAN)

        # Only the next autosave PUT is held; the type-in below triggers it.
        page.evaluate(GATE_NEXT_DRAFT_PUT)
        dialogs = []

        def on_dialog(dialog):
            dialogs.append(dialog.type)
            dialog.dismiss()
        page.on('dialog', on_dialog)

        name_input.fill(TYPED_NAME)
        page.wait_for_function('() => window.__draftGate.started === true')
        page.wait_for_function('() => SrdCreator.app.saving === true')
        assert server_identity_name(page, draft_id) != TYPED_NAME  # not stored yet

        # Real display dialog, stable accessible name for the apply button (not "last button").
        page.locator('#vttDisplayOpen').click()
        page.locator('#vttDisplay-language').select_option('en')
        page.get_by_role('button', name='Anwenden und Seite neu laden', exact=True).click()
        for _ in range(60):
            if dialogs:
                break
            page.wait_for_timeout(100)
        assert dialogs == ['beforeunload'], dialogs   # the guard fired; the reload was dismissed
        expect(name_input).to_have_value(TYPED_NAME)   # typed value is intact
        assert page.evaluate('() => SrdCreator.app.saving') is True
        page.remove_listener('dialog', on_dialog)

        # Let the held save finish, then the draft is clean and stored on the server.
        page.evaluate('() => window.__draftGate.release()')
        page.wait_for_function(CREATOR_CLEAN)
        assert server_identity_name(page, draft_id) == TYPED_NAME

        # Language reload now proceeds without a guard and restores the draft in English.
        page.reload()
        expect(page.locator('html')).to_have_attribute('lang', 'en')
        expect(page.locator('#scId-name')).to_have_value(TYPED_NAME)
        assert server_identity_name(page, draft_id) == TYPED_NAME

        # Authored description labels and lifecycle status are English; the typed name is verbatim.
        for field_id, label in (('name', 'Name'), ('pronouns', 'Pronouns'), ('age', 'Age'),
                                ('height', 'Height'), ('eyes', 'Eyes'), ('hair', 'Hair'),
                                ('skin', 'Skin'), ('faith', 'Faith'), ('appearance', 'Appearance'),
                                ('traits', 'Personality traits'), ('bonds', 'Bonds'),
                                ('backstory', 'Backstory'), ('notes', 'Notes')):
            expect(page.locator(f'label[for="scId-{field_id}"]')).to_have_text(label)
        expect(page.locator('#scId-alignment option').first).to_have_text('Not specified')
        expect(page.locator('#scSave')).to_have_text('Saved')
        expect(page.locator('#scId-name')).to_have_value(TYPED_NAME)

        # A new edit shows the English lifecycle text while it is pending/saved.
        page.locator('#scId-pronouns').fill('they/them')
        expect(page.locator('#scSave')).to_have_text(re.compile(r'^(Unsaved …|Saving …|Saved)$'))
        page.wait_for_function(CREATOR_CLEAN)
        expect(page.locator('#scSave')).to_have_text('Saved')
        expect(page.locator('#scId-pronouns')).to_have_value('they/them')
        browser.close()
