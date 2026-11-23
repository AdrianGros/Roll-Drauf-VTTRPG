"""Real grouped commands preserve roles, field drafts and existing handlers."""
import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.test_personal_actions_browser import action_site  # noqa: F401


@pytest.mark.parametrize('engine,role,width,language',[
    ('chromium','dm',1440,'de'),('firefox','dm',390,'en'),('chromium','player',320,'de'),('firefox','owner_player',1024,'en')])
def test_grouped_commands_keep_real_controls_roles_and_drafts(action_site,engine,role,width,language):
    _,origin,info=action_site
    seat='player' if role=='owner_player' else role
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce',has_touch=width<600)
        context.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'night',language:'"+language+"',accent:'default',unit:'m'}))")
        context.add_cookies([{'name':'access_token_cookie','value':info[('dm' if role=='owner_player' else role)+'_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={seat}")
        expect(page.locator('body')).to_have_class(__import__('re').compile('play-tool-groups'))
        dock=page.locator('.play-command-groups');expect(dock.locator('button')).to_have_count(10 if seat=='dm' else 9)
        expect(page.locator('#playToolStatus')).not_to_contain_text('Nur Lesen')
        rows=dock.locator('button').evaluate_all("rows=>rows.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,right:r.right,y:r.y,bottom:r.bottom,height:r.height,icons:e.querySelectorAll('svg').length,labels:e.querySelectorAll('.tool-label').length,font:getComputedStyle(e).fontSize}})")
        assert all(r['x']>=0 and r['right']<=width+1 and r['bottom']<=1000 and r['height']==52 and r['icons']==1 and r['labels']==1 and r['font']=='12px' for r in rows),rows
        page.locator('[data-tool=measure]').click();expect(page.locator('#measureOptions')).to_be_visible()
        assert page.locator('#measureShape').evaluate("e=>{const p=document.createElement('span');p.style.color='var(--ui-panel)';document.body.append(p);const match=getComputedStyle(e).backgroundColor===getComputedStyle(p).color;p.remove();return match;}")
        page.locator('#btnMeasureSnap').click();expect(page.locator('#btnMeasureSnap')).to_have_attribute('aria-pressed','true')
        page.locator('[data-tool=select]').click();expect(page.locator('#measureOptions')).to_be_hidden()
        page.locator('#btnTableMore').click();expect(page.locator('#window-tableMore')).to_be_visible()
        expect(page.locator('#btnSidebarToggle .tool-label')).to_be_visible()
        expect(page.locator('#window-tableMore [data-command=display] .tool-label')).to_be_visible()
        page.locator('#btnSidebarToggle').click();expect(page.locator('#window-tableMore')).to_be_hidden()
        expect(page.locator('#window-panel-journal')).to_be_visible()
        page.locator('#window-panel-journal .play-window-head button').click();page.locator('#btnTableMore').click()
        page.locator('#btnAllTableCommands').click();expect(page.locator('#playCommandSearch')).to_be_focused()
        page.locator('#playCommandSearch').fill('Etagen')
        if seat=='dm':
            expect(page.locator('.play-command-list [data-command=floors]')).to_be_visible()
            expect(page.locator('.play-command-list [data-command=floors] .tool-label')).to_be_visible()
            page.locator('.play-command-list [data-command=floors]').click();expect(page.locator('#window-mapFloors')).to_be_visible()
            page.locator('#window-mapFloors .play-window-head button').click()
            page.locator('#btnMapPresentation').click();expect(page.locator('#window-mapPresentation')).to_be_visible()
            page.locator('#presentationGridSize').fill('88')
            page.locator('#btnTableMore').click();page.locator('#btnAllTableCommands').click();page.locator('#playCommandSearch').fill('Tokens')
            # The original labels remain useful search synonyms.
            page.locator('#playCommandSearch').fill('Figuren' if language=='de' else 'Figures')
            page.locator('.play-command-list [data-command=figures]').click()
            expect(page.locator('#dock-tokenLayersWidget .tool-label')).to_be_visible()
            page.locator('#dock-tokenLayersWidget').click();expect(page.locator('#window-tokenLayersWidget')).to_be_visible()
            expect(page.locator('#presentationGridSize')).to_have_value('88')
            page.locator('#window-tokenLayersWidget .play-window-head button').click()
            page.locator('#window-tokenWidget .play-window-head button').click()
            page.locator('#toolWall').click();expect(page.locator('#playToolStatus')).to_contain_text('Wand' if language=='de' else 'wall')
            expect(page.locator('#window-mapPresentation')).to_be_hidden()
        else:
            expect(page.locator('.play-command-list [data-command=floors]')).to_have_count(0)
            assert page.locator('#btnMapPresentation,#toolWall,#toolLight,#btnMapFloors').count()==0
            assert not page.evaluate('Boolean(window.PlayToolGroupsDM||window.PlayDMSurface||window.PlayFloorDM)')
            assert not page.locator('script[src$="play-tool-groups-dm.js"]').count()
        if os.environ.get('TOOL_GROUP_PROOF_DIR'):
            root=Path(os.environ['TOOL_GROUP_PROOF_DIR']);root.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(root/f'groups-{engine}-{role}-{width}-{language}.png'))
        assert not errors,errors
        browser.close()
