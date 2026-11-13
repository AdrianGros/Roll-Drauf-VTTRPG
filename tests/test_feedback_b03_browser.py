"""Warm night-book materials and editor presentation, preserving personal accents."""
import pytest
from tests.test_personal_actions_browser import action_site  # noqa: F401
from tests.test_presentation_browser import preferences,contrast


@pytest.mark.parametrize('engine,width,language',[('chromium',1440,'de'),('firefox',390,'en')])
def test_night_materials_red_default_and_editor_controls(action_site,engine,width,language):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=action_site
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        preferences(context,theme='night',language=language,accent='default')
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000);errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(origin+'/characters')
        expect(page.locator('.book-spread-page').first).to_be_visible()
        expect(page.locator('.book-scene-loading')).to_have_count(0)
        assert page.locator('html').evaluate("e=>getComputedStyle(e).getPropertyValue('--ui-accent').trim()")=='#f29a90'
        assert page.locator('.book-spread-page').first.evaluate("e=>getComputedStyle(e).backgroundImage!=='none'")
        contrast(page,'.book-spread-page h1,.book-spread-page h2,.book-spread-page p,.book-dashboard-ribbon-btn')
        page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
        expect(page.locator('#scBuilder')).to_be_visible()
        contrast(page,'.sc-card,.sc-step,.sc-btn')
        page.goto(origin+'/mapmaker');page.wait_for_url(origin+'/static/mapmaker/index.html')
        expect(page.locator('#mapTitle')).to_be_visible()
        page.evaluate('() => window.rdMapmaker.ready')
        page.locator('#newEmpty').click()
        contrast(page,'.mm-top .mm-btn,.vtt-map-nav .book-dashboard-ribbon-btn,.mm-panel label,.mm-tool,.mm-tabs [role=tab],.mm-group-head h2')
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        page.locator('#vttDisplayOpen').click();page.locator('#vttDisplay-accent').select_option('teal')
        page.locator('.vtt-display-actions button').last.click()
        assert page.locator('html').evaluate("e=>getComputedStyle(e).getPropertyValue('--ui-accent').trim()")=='#96dac8'
        assert not errors,errors
        context.close();browser.close()
