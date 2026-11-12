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
