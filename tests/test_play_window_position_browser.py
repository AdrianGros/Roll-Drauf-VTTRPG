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
        first.locator('.play-window-head strong').press('ArrowDown')
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
