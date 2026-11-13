import base64,calendar,io,json,re
from datetime import date
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from tests.test_presentation_browser import contrast
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de'
f=json.loads((ROOT/'live-credentials.json').read_text())
proof={'status':'running','journeys':[],'checks':{},'errors':[],'avatar_scope':'Own synthetic identity link; CDN thumbnail intercepted. Real Discord OAuth not exercised on production.'}

def login(context,kind):
    page=context.new_page();page.set_default_timeout(45000)
    page.on('pageerror',lambda e:proof['errors'].append(str(e)))
    page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users'][kind]['username'])
    page.locator('#loginPassword').fill(f['users'][kind]['password']);page.locator('#passwordLoginSubmitBtn').click()
    page.wait_for_url(lambda u:'/login' not in u);return page

def settings(page,theme,language):
    previous=page.locator('html').get_attribute('lang')
    page.locator('#vttDisplayOpen').click();page.locator('#vttDisplay-theme').select_option(theme)
    page.locator('#vttDisplay-language').select_option(language)
    if language!=previous:
        with page.expect_navigation(wait_until='load'):page.locator('.vtt-display-actions button').last.click()
    else:page.locator('.vtt-display-actions button').last.click()
    expect(page.locator('html')).to_have_attribute('lang',language)

with sync_playwright() as p:
    chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
    dc=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    pc=firefox.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
    png=io.BytesIO();Image.new('RGB',(2,2),(140,50,60)).save(png,format='PNG')
    avatar_pattern='https://cdn.discordapp.com/avatars/**'
    pc.route(avatar_pattern,lambda route:route.fulfill(status=200,content_type='image/png',body=png.getvalue()))
    try:
        dm=login(dc,'dm');player=login(pc,'player')
        for page,kind,theme,language in [(dm,'dm','paper','de'),(player,'player','night','en')]:
            page.goto(ORIGIN+'/campaigns');settings(page,theme,language)
            own=page.locator('[data-own-calendar]')
            expect(own.locator('.sc-month-grid')).to_be_visible()
            expect(own.locator('.sc-weekday')).to_have_count(7)
            first=date.fromisoformat(own.locator('[data-day]').first.get_attribute('data-day'))
            expect(own.locator('[data-day]')).to_have_count(calendar.monthrange(first.year,first.month)[1])
            assert own.locator('.sc-month-grid').evaluate('e=>e.children.length%7===0')
            assert page.locator('#vttDisplayOpen').evaluate("e=>!e.closest('.book-dashboard-ribbon')")
            gear=page.locator('#vttDisplayOpen').bounding_box();assert gear['x']+gear['width']<=page.viewport_size['width']+1
            if kind=='player':
                expect(page.locator('.vtt-account-avatar')).to_be_visible()
                assert page.locator('.vtt-account-avatar').evaluate('e=>e.naturalWidth')==2
                assert pc.request.get(ORIGIN+'/api/dashboard/navigation').json()['user']['avatar_url'].startswith('https://cdn.discordapp.com/avatars/')
            page.screenshot(path=str(ROOT/(kind+'-calendar.png')),full_page=True)
            proof['journeys'].append(kind+': campaign calendar → full default month → gear settings')
        for page,kind,action in [(dm,'dm','open-session-dm'),(player,'player','open-session')]:
            page.goto(f'{ORIGIN}/campaigns?campaign_id={f["campaign_id"]}')
            page.locator(f'[data-hub-action="{action}"][data-hub-session-id="{f["session_id"]}"]').click()
            page.wait_for_url(lambda u:'/play' in u);expect(page.locator('#tableDockTabs')).to_be_visible()
            for widget in ['layersWidget','turnOrderWidget','tokenWidget']:
                page.locator('#dock-'+widget).click();expect(page.locator('#'+widget)).to_be_visible()
            page.locator('.table-dock-close').click()
            page.locator('#btnChatToggle').click();expect(page.locator('#chatInput')).to_be_visible()
            page.locator('#chatInput').fill('B02 Live '+kind);page.locator('#btnSendChat').click()
            expect(page.locator('#chatLog')).to_contain_text('B02 Live '+kind)
            page.locator('#btnSidebarToggle').click();expect(page.locator('#panel-journal')).to_be_visible()
            if kind=='dm':
                page.locator('#journalSessionControls summary').click();expect(page.locator('#btnInitStack')).to_be_visible()
                contrast(page,'#journalSessionControls summary, #panel-journal button')
            else:
                expect(page.locator('#journalSessionControls,#btnInitStack,#mapScalePanel')).to_have_count(0)
                assert not page.evaluate('() => !!window.PlayDMSurface')
                expect(page.locator('#chatSidebar')).not_to_be_visible()
            page.locator('#btnSidebarClose').click()
            if kind=='dm':page.locator('#btnChatClose').click()
            page.locator('#vttDisplayOpen').click();expect(page.locator('#vttDisplayTitle')).to_have_text('Settings' if kind=='player' else 'Einstellungen')
            page.locator('#vttDisplayDialog').press('Escape')
            page.screenshot(path=str(ROOT/(kind+'-workspace.png')),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth')<=page.viewport_size['width']+1
            proof['journeys'].append(kind+': hub session → three dock tabs → left chat → right journal → visible fullscreen gear')
        expect(dm.locator('#presenceRoster')).to_contain_text(f['users']['player']['username'])
        dm.locator('#btnSidebarToggle').click();dm.locator('.sidebar-tab[data-tab="tools"]').click()
        dm.locator('#diceInput').fill('3d6+2');dm.locator('#btnRoll').click()
        expect(dm.locator('#diceResult')).to_contain_text('Würfel')
        for page in [dm,player]:
            if 'is-open' not in (page.locator('#chatSidebar').get_attribute('class') or ''):page.locator('#btnChatToggle').click()
            expect(page.locator('#chatLog .chat-roll-breakdown')).to_have_count(1)
        proof['checks']['both_clients_see_roll_details']=True
        player.reload();expect(player.locator('#tableDockTabs')).to_be_visible();player.locator('#btnChatToggle').click()
        expect(player.locator('#chatLog')).to_contain_text('B02 Live dm')
        expect(player.locator('#chatLog')).to_contain_text('B02 Live player')
        proof['checks']['chat_persisted_after_reload']=True
        player.goto(ORIGIN+'/characters');expect(player.locator('[data-shared-characters] h2')).to_have_text('Shared campaign characters')
        expect(player.locator('.vtt-account-avatar')).to_be_visible()
        pc.unroute(avatar_pattern);pc.route(avatar_pattern,lambda route:route.fulfill(status=404))
        player.reload();expect(player.locator('.vtt-account-name')).to_have_text(f['users']['player']['username'])
        expect(player.locator('.vtt-account-avatar')).to_have_count(0)
        proof['checks']['optional_avatar_and_error_fallback']=True
        assert not proof['errors'],proof['errors'];proof['status']='pass'
    except BaseException as error:
        proof['status']='fail';proof['failure']=str(error);raise
    finally:
        (ROOT/'live-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
        dc.close();pc.close();chrome.close();firefox.close()
