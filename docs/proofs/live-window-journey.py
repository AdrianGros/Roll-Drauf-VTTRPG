"""Normal-role live acceptance using isolated, temporary QA accounts."""
import json
import os
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

root=Path(os.environ['PROOF_ROOT'])
fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','journeys':[],'authentication':'Synthetic QA sessions; Discord OAuth not exercised'}

def save():
    (root/'live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')

with sync_playwright() as p:
    try:
        for engine,role,width in [('chromium','dm',1440),('firefox','player',1440),('chromium','player',390)]:
            browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
            context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce',has_touch=width<600)
            theme='paper' if engine=='firefox' else 'night'
            context.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'"+theme+"',language:'de',accent:'default',unit:'m'}))")
            user=fixture['users'][role]
            context.add_cookies([{'name':'access_token_cookie','value':user['token'],'url':origin,'httpOnly':True,'secure':True},
                                {'name':'csrf_access_token','value':user['csrf'],'url':origin,'secure':True}])
            page=context.new_page();page.set_default_timeout(25000)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('dialog',lambda dialog:dialog.accept() if 'Rastergröße' in dialog.message else dialog.dismiss())
            page.goto(origin+f"/campaigns?campaign_id={fixture['campaign_id']}")
            action='open-session-dm' if role=='dm' else 'open-session'
            page.locator('[data-hub-action="'+action+'"]').first.click()
            expect(page.locator('body')).to_have_attribute('data-table-seat',role)
            expect(page.locator('html')).to_have_attribute('data-vtt-theme',theme)
            dock=page.locator('.play-command-groups button')
            expect(dock).to_have_count(10 if role=='dm' else 9)
            geometry=dock.evaluate_all('rows=>rows.map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,bottom:r.bottom,height:r.height,icons:e.querySelectorAll("svg").length};})')
            assert all(r['left']>=0 and r['right']<=width+1 and r['bottom']<=1000 and r['height']==52 and r['icons']==1 for r in geometry),geometry
            activate=lambda locator:locator.tap() if width<600 else locator.click()
            activate(page.locator('[data-tool=measure]'));activate(page.locator('#btnMeasureSnap'))
            expect(page.locator('#btnMeasureSnap')).to_have_attribute('aria-pressed','true')
            activate(page.locator('[data-tool=select]'))
            activate(page.locator('#btnTableMore'))
            expect(page.locator('#btnSidebarToggle .tool-label')).to_be_visible()
            expect(page.locator('#window-tableMore [data-command=display] .tool-label')).to_be_visible()
            activate(page.locator('#btnAllTableCommands'))
            page.locator('#playCommandSearch').fill('Beyond20')
            expect(page.locator('.play-command-list [data-command=beyond] .tool-label')).to_be_visible()
            activate(page.locator('.play-command-list [data-command=beyond]'))
            expect(page.locator('#window-beyond20')).to_be_visible()
            page.locator('#window-beyond20 .play-window-head button').click()
            if role=='dm':
                page.locator('#btnMapPresentation').click()
                page.locator('#presentationGridSize').fill('80');page.locator('#savePresentationSettings').click()
                expect(page.locator('#window-mapPresentation')).to_contain_text('gespeichert',timeout=30000)
                page.locator('#btnMapFloors').click();expect(page.locator('#window-mapFloors')).to_be_visible()
                page.locator('#window-mapFloors .play-window-head button').click()
                page.locator('#window-mapPresentation .play-window-head button').click()
                page.locator('#dock-tokenWidget').click();expect(page.locator('#dock-tokenLayersWidget .tool-label')).to_be_visible();page.locator('#dock-tokenLayersWidget').click()
                expect(page.locator('#window-tokenLayersWidget')).to_be_visible()
                page.locator('#window-tokenLayersWidget .play-window-head button').click()
                page.locator('#window-tokenWidget .play-window-head button').click()
            else:
                assert not page.evaluate('Boolean(window.PlayToolGroupsDM || window.PlayFloorDM)')
                assert page.locator('#btnMapFloors,#toolWall,#toolLight').count()==0
            page.locator('#dock-tokenWidget').click();page.locator('#dock-turnOrderWidget').click()
            first=page.locator('#window-tokenWidget');second=page.locator('#window-turnOrderWidget')
            expect(first).to_be_visible();expect(second).to_be_visible()
            page.locator('#btnChatToggle').click();page.locator('#btnTableMore').click();page.locator('#btnBack').click()
            palette=page.evaluate("""() => {
              const resolve=token=>{const e=document.createElement('span');e.style.color=`var(${token})`;document.body.append(e);const v=getComputedStyle(e).color;e.remove();return v;};
              return [['#window-tokenWidget','--ui-paper'],['#window-panel-chat .panel','--ui-panel'],['#chatInput','--ui-panel'],['#measureShape','--ui-panel'],['#appMenu','--ui-panel'],['#appMenuReturn','--ui-soft']].map(([selector,token])=>{const s=getComputedStyle(document.querySelector(selector));return {selector,bg:s.backgroundColor,expected:resolve(token),ink:s.color,expectedInk:resolve('--ui-ink')};});
            }""")
            assert all(row['bg']==row['expected'] and row['ink']==row['expectedInk'] for row in palette),palette
            page.locator('#appMenu').press('Escape')
            expect(page.locator('#appMenu')).to_be_hidden();expect(page.locator('#btnTableMore')).to_be_focused()
            page.locator('#window-panel-chat .play-window-head button').click()
            assert first.evaluate("e=>getComputedStyle(e).position")=='fixed'
            assert second.evaluate("e=>getComputedStyle(e).position")=='fixed'
            page.locator('#dock-tokenWidget').click();page.locator('#dock-tokenWidget').click()
            heading=first.locator('.play-window-head strong')
            before=first.bounding_box();other=second.bounding_box();handle=heading.bounding_box()
            x=handle['x']+20;y=handle['y']+15;dx=160 if width>600 else 0;dy=90
            if width<600:
                client=context.new_cdp_session(page)
                client.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
                for step in range(1,9):client.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+dx*step/8,'y':y+dy*step/8}]})
                client.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            else:
                page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y+dy,steps=8);page.mouse.up()
            moved=first.bounding_box()
            assert abs(moved['x']-before['x']-dx)<2 and abs(moved['y']-before['y']-dy)<2,(before,moved)
            assert second.bounding_box()==other
            body=first.locator('.play-window-body')
            body.evaluate("e=>{const content=document.createElement('p');content.style.height='2400px';content.textContent='Temporary scroll acceptance';e.append(content)}")
            page_scroll=page.evaluate('[scrollX,scrollY]');area=body.bounding_box()
            page.mouse.move(area['x']+area['width']/2,area['y']+min(30,area['height']/2));page.mouse.wheel(0,500)
            page.wait_for_function("() => document.querySelector('#window-tokenWidget .play-window-body').scrollTop>100")
            assert page.evaluate('[scrollX,scrollY]')==page_scroll and second.bounding_box()==other
            assert page.evaluate('document.documentElement.scrollHeight<=innerHeight+1')
            first.locator('.play-window-head button').click();page.locator('#dock-tokenWidget').click()
            restored=first.bounding_box();assert abs(restored['x']-moved['x'])<2 and abs(restored['y']-moved['y'])<2
            page.reload();page.locator('#dock-tokenWidget').click()
            restored=first.bounding_box();assert abs(restored['x']-moved['x'])<2 and abs(restored['y']-moved['y'])<2
            if role=='player':assert not page.evaluate('Boolean(window.PlayDMSurface)')
            else:
                page.locator('#btnMapPresentation').click();expect(page.locator('#presentationGridSize')).to_have_value('80')
                page.locator('#window-mapPresentation .play-window-head button').click()
            assert errors==[],errors
            page.screenshot(path=str(root/f'windows-{role}-{engine}-{width}.png'))
            proof['journeys'].append({'role':role,'engine':engine,'width':width,'theme':theme,'palette':palette,'grouped_commands':True,'row_labels_visible':True,'primary_commands':len(geometry),'real_map_setting_save':role=='dm','drag':'touch' if width<600 else 'mouse','before':before,'after':moved,'independent_scroll':True,'restored_after_reload':True})
            save();browser.close()
        proof['status']='pass';save()
    except Exception as error:
        proof['status']='failed';proof['error']=str(error);save();raise
