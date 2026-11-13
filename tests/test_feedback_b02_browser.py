"""Named workspace drawers, authorized dock, gear and empty monthly calendar."""
import calendar
from datetime import date
import re

import pytest

from tests.test_personal_actions_browser import action_site  # noqa: F401
from tests.test_presentation_browser import preferences, contrast


@pytest.mark.parametrize('role,width,language,theme,engine',[
    ('dm',1440,'de','paper','chromium'),('player',390,'en','night','firefox')])
def test_workspace_drawers_dock_and_settings(action_site,role,width,language,theme,engine):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=action_site
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        preferences(context,language=language,theme=theme)
        context.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000);errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
        expect(page.locator('#tableDockTabs')).to_be_visible()
        expect(page.locator('.right-sidebar [data-tab="session"], .right-sidebar [data-tab="chat"]')).to_have_count(0)
        assert page.locator('#panel-chat').evaluate("e=>e.closest('aside').id")=='chatSidebar'
        for widget in ['layersWidget','turnOrderWidget','tokenWidget']:
            assert page.locator('#'+widget).evaluate("e=>e.closest('#tableSheetBody')!==null")
        page.locator('#dock-turnOrderWidget').click()
        expect(page.locator('#turnOrderWidget')).to_be_visible()
        expect(page.locator('#layersWidget')).not_to_be_visible()
        page.locator('#dock-turnOrderWidget').press('ArrowRight')
        expect(page.locator('#dock-tokenWidget')).to_have_attribute('aria-selected','true')
        expect(page.locator('#tokenWidget')).to_be_visible()
        page.locator('.table-dock-close').click()
        page.locator('#btnChatToggle').click()
        expect(page.locator('#chatInput')).to_be_visible()
        assert page.locator('#chatSidebar').bounding_box()['x']<width/2
        contrast(page,'#chatSidebar h2, #chatSidebar button')
        page.locator('#chatInput').fill('B02 browser roundtrip');page.locator('#btnSendChat').click()
        expect(page.locator('#chatLog')).to_contain_text('B02 browser roundtrip')
        page.locator('#btnSidebarToggle').click()
        expect(page.locator('#panel-journal')).to_be_visible()
        if width<1040:expect(page.locator('#chatSidebar')).not_to_be_visible()
        else:expect(page.locator('#chatSidebar')).to_be_visible()
        journal_box=page.locator('#journalSidebar').bounding_box()
        assert abs(journal_box['x']+journal_box['width']-width)<=1
        if width>=1040:assert journal_box['x']>=width/2-5
        if role=='dm':
            page.locator('#journalSessionControls summary').click()
            expect(page.locator('#btnInitStack')).to_be_visible()
        else:
            expect(page.locator('#journalSessionControls,#btnInitStack,#mapScalePanel')).to_have_count(0)
            assert not page.evaluate('() => !!window.PlayDMSurface')
        page.locator('#btnSidebarClose').click()
        if width>=1040:page.locator('#btnChatClose').click()
        page.locator('#vttDisplayOpen').click()
        expect(page.locator('#vttDisplayTitle')).to_have_text('Settings' if language=='en' else 'Einstellungen')
        page.locator('#vttDisplayDialog').press('Escape')
        gear=page.locator('#vttDisplayOpen').bounding_box()
        assert gear['x']+gear['width']<=width+1
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        page.locator('#btnChatToggle').click()
        expect(page.locator('#chatLog')).to_contain_text('B02 browser roundtrip')
        page.locator('#chatInput').press('Escape')
        expect(page.locator('#chatSidebar')).not_to_be_visible()
        page.locator('#btnChatToggle').click();page.locator('#btnBack').click()
        expect(page.locator('#appMenu')).to_be_visible()
        expect(page.locator('#chatSidebar')).not_to_be_visible()
        expect(page.locator('#btnChatToggle')).to_have_attribute('aria-expanded','false')
        page.locator('#appMenu').press('Escape')
        assert not errors,errors
        context.close();browser.close()


def test_calendar_opens_with_complete_empty_month_and_settings_stay_outside_scroll(action_site):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=action_site
    from vtt.models import DiscordIdentityLink
    from vtt.extensions import db
    with app.app_context():
        link=DiscordIdentityLink(user_id=info['player_id'],discord_user_id='123456789012345678',link_status='linked')
        link.set_avatar_snapshot('a'*32);db.session.add(link);db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        import base64
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aQ3sAAAAASUVORK5CYII=')
        avatar_pattern='https://cdn.discordapp.com/avatars/**'
        context.route(avatar_pattern,lambda route:route.fulfill(status=200,content_type='image/png',body=png))
        page=context.new_page();page.goto(origin+'/campaigns')
        root=page.locator('[data-own-calendar]')
        expect(root.locator('.sc-month-grid')).to_be_visible()
        expect(root.locator('.sc-weekday')).to_have_count(7)
        first=root.locator('[data-day]').first.get_attribute('data-day')
        day=date.fromisoformat(first)
        expect(root.locator('[data-day]')).to_have_count(calendar.monthrange(day.year,day.month)[1])
        count=root.locator('.sc-month-grid').evaluate('e=>e.children.length')
        assert count%7==0
        assert page.locator('#vttDisplayOpen').evaluate("e=>!e.closest('.book-dashboard-ribbon')")
        gear=page.locator('#vttDisplayOpen').bounding_box()
        assert gear['x']+gear['width']<=391
        page.locator('#vttDisplayOpen').click();expect(page.locator('#vttDisplayTitle')).to_have_text('Einstellungen')
        expect(page.locator('.vtt-account-avatar')).to_be_visible()
        expect(page.locator('.vtt-account-name')).to_have_text('action-player')
        context.unroute(avatar_pattern)
        context.route(avatar_pattern,lambda route:route.fulfill(status=404))
        page.reload();expect(page.locator('.vtt-account-name')).to_have_text('action-player')
        expect(page.locator('.vtt-account-avatar')).to_have_count(0)
        context.close();browser.close()
