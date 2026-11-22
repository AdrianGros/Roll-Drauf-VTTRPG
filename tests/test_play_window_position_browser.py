"""Movable windows must escape document flow and own their scroll area."""
import os
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from tests.test_personal_actions_browser import action_site  # noqa: F401


@pytest.mark.parametrize('engine,role,width', [('chromium','dm',1440), ('firefox','player',1440), ('chromium','player',390)])
def test_windows_move_independently_and_scroll_inside_their_body(action_site, engine, role, width):
    _, origin, info = action_site
    with sync_playwright() as p:
        browser = getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context = browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
        page.locator('#dock-tokenWidget').click()
        page.locator('#dock-turnOrderWidget').click()
        first=page.locator('#window-tokenWidget');second=page.locator('#window-turnOrderWidget')
        expect(first).to_be_visible();expect(second).to_be_visible()
        assert first.evaluate("e=>getComputedStyle(e).position")=='fixed'
        assert second.evaluate("e=>getComputedStyle(e).position")=='fixed'
        # Bring the target to the front without depending on overlap order.
        page.locator('#dock-tokenWidget').click();page.locator('#dock-tokenWidget').click()
        before=first.bounding_box();other=second.bounding_box()
        heading=first.locator('.play-window-head strong');handle=heading.bounding_box()
        x=handle['x']+20;y=handle['y']+15
        dx=120 if width>600 else 0;dy=90
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y+dy,steps=8);page.mouse.up()
        moved=first.bounding_box()
        assert abs(moved['x']-before['x']-dx)<2
        assert abs(moved['y']-before['y']-dy)<2
        assert second.bounding_box()==other
        # Oversized real content belongs to this body; neither the header nor
        # another window may be pushed into a document-sized stack.
        body=first.locator('.play-window-body')
        body.evaluate("e=>{const content=document.createElement('div');content.style.height='2400px';content.textContent='Scrollable proof';e.append(content)}")
        page.wait_for_function("() => document.querySelector('#window-tokenWidget .play-window-body').scrollHeight>document.querySelector('#window-tokenWidget .play-window-body').clientHeight")
        page_before=page.evaluate('[scrollX,scrollY]')
        area=body.bounding_box();page.mouse.move(area['x']+area['width']/2,area['y']+min(30,area['height']/2));page.mouse.wheel(0,500)
        page.wait_for_function("() => document.querySelector('#window-tokenWidget .play-window-body').scrollTop>100")
        assert page.evaluate('[scrollX,scrollY]')==page_before
        assert second.bounding_box()==other
        assert first.locator('.play-window-head').bounding_box()['y']==moved['y']+1
        assert page.evaluate('document.documentElement.scrollHeight <= innerHeight+1')
        first.locator('.play-window-head button').click();page.locator('#dock-tokenWidget').click()
        restored=first.bounding_box();assert abs(restored['x']-moved['x'])<2 and abs(restored['y']-moved['y'])<2
        page.reload();page.locator('#dock-tokenWidget').click()
        restored=first.bounding_box();assert abs(restored['x']-moved['x'])<2 and abs(restored['y']-moved['y'])<2
        if os.environ.get('VTT_PROOF_DIR'):
            path=Path(os.environ['VTT_PROOF_DIR']);path.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(path/f'windows-{role}-{engine}-{width}.png'))
        assert errors==[],errors
        browser.close()


@pytest.mark.parametrize('engine,theme', [('chromium','night'),('firefox','paper')])
def test_relocated_windows_textboxes_and_menus_follow_the_display_palette(action_site, engine, theme):
    _,origin,info=action_site
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        context.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'"+theme+"',language:'de',accent:'default',unit:'m'}))")
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000)
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player")
        page.locator('#dock-tokenWidget').click()
        page.locator('#btnChatToggle').click()
        page.locator('#btnBack').click()
        expect(page.locator('#appMenu')).to_be_visible()
        # Native colour conversion avoids assuming how the browser serializes CSS variables.
        values=page.evaluate("""() => {
          const css=name=>{const e=document.createElement('span');e.style.color=`var(${name})`;document.body.append(e);const v=getComputedStyle(e).color;e.remove();return v;};
          const specs=[['#window-tokenWidget','--ui-paper'],['#window-panel-chat .panel','--ui-panel'],['#chatInput','--ui-panel'],['#appMenu','--ui-panel'],['#appMenuReturn','--ui-soft']];
          return specs.map(([selector,token])=>{const e=document.querySelector(selector),s=getComputedStyle(e);return {selector,bg:s.backgroundColor,expected:css(token),ink:s.color,expectedInk:css('--ui-ink')};});
        }""")
        for row in values:
            assert row['bg']==row['expected'],row
            assert row['ink']==row['expectedInk'],row
        page.locator('#btnBack').click()
        page.evaluate("VTTDisplay.update({theme:'night',accent:'teal'})")
        assert page.locator('#window-tokenWidget').evaluate("e=>getComputedStyle(e).backgroundColor")=='rgb(28, 28, 28)'
        heading=page.locator('#window-tokenWidget h4').first
        assert heading.evaluate("e=>getComputedStyle(e).color")=='rgb(248, 244, 233)'
        assert heading.evaluate("e=>getComputedStyle(e).backgroundImage")=='none'
        if os.environ.get('VTT_PROOF_DIR'):
            path=Path(os.environ['VTT_PROOF_DIR']);path.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(path/f'windows-colors-{theme}-{engine}.png'))
        browser.close()
