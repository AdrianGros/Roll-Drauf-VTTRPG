"""Normal campaign-hub journeys on a synthetic large map; no real-user writes."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright,expect
from tests.play_canvas_shared import exercise_camera
expect.set_options(timeout=30000)
root=Path(os.environ['PROOF_ROOT']);fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','journeys':[],'authentication':'isolated synthetic sessions; Discord OAuth not exercised'}
def save():
    (root/'live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
with sync_playwright() as p:
    try:
        for engine,role,width,theme in [('chromium','dm',1440,'paper'),('firefox','player',1440,'night'),('chromium','dm',390,'paper'),('chromium','player',320,'night')]:
            browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else [])
            ctx=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce',has_touch=width<600)
            ctx.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'"+theme+"',language:'de',accent:'default',unit:'m'}))")
            user=fixture['users'][role];ctx.add_cookies([{'name':'access_token_cookie','value':user['token'],'url':origin,'httpOnly':True,'secure':True},{'name':'csrf_access_token','value':user['csrf'],'url':origin,'secure':True}])
            page=ctx.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(origin+f"/campaigns?campaign_id={fixture['campaign_id']}")
            action='open-session-dm' if role=='dm' else 'open-session'
            page.locator(f'[data-hub-action="{action}"][data-hub-session-id="{fixture["session_id"]}"]').click()
            expect(page.locator('body')).to_have_attribute('data-table-seat',role)
            expect(page.locator('html')).to_have_attribute('data-vtt-theme',theme)
            expect(page.locator('#mapWorld')).to_have_attribute('data-map-width','6000')
            def token_state():
                return page.evaluate("async ([c,s])=>(await Auth.makeAuthRequest(`/api/play/campaigns/${c}/sessions/${s}/bootstrap`)).state_payload.tokens.map(t=>[t.id,t.x,t.y,t.version]).sort((a,b)=>a[0]-b[0])",[fixture['campaign_id'],fixture['session_id']])
            before=token_state();camera=exercise_camera(page,ctx.new_cdp_session(page) if width<600 else None)
            assert token_state()==before
            page.locator('#dock-layersWidget').click();rows=page.locator('#layerList .layer-row')
            expect(rows).to_have_count(2)
            for row in rows.all():
                assert row.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                assert row.locator('.layer-title').bounding_box()['width']>=70
            if role=='dm':
                child=rows.nth(1);child.locator('summary').press('Enter')
                expect(child.locator('details')).to_have_attribute('open','')
                child.locator('input').fill('Porta · das Tor zur Unterseite');child.locator('input').press('Tab')
                expect(child.locator('.layer-title')).to_have_text('Porta · das Tor zur Unterseite')
                child.locator('select').select_option(rows.first.get_attribute('data-layer-id'))
                expect(child).to_have_attribute('data-depth','1')
                expect(child.locator('details')).to_have_attribute('open','')
                child.locator('summary').click();child.locator('[data-act=activate]').click()
                expect(child).to_have_class(__import__('re').compile('active-row'))
                rows.first.locator('[data-act=activate]').click();expect(rows.first).to_have_class(__import__('re').compile('active-row'))
                rows.first.locator('summary').click()
                assert rows.first.locator('input').bounding_box()['width']>150
                assert rows.first.locator('select').bounding_box()['width']>150
                page.screenshot(path=str(root/f'scene-options-{role}-{engine}-{width}.png'))
                rows.first.locator('summary').click()
            else:
                expect(page.locator('.scene-options,[data-act=activate]')).to_have_count(0)
                assert not page.evaluate('Boolean(window.PlayFeedbackDM)')
            page.screenshot(path=str(root/f'scenes-{role}-{engine}-{width}.png'))
            assert errors==[],errors
            proof['journeys'].append({'role':role,'engine':engine,'width':width,'theme':theme,'camera':camera,'token_state_unchanged_by_camera':True,'scene_cards_readable':True,'real_scene_rename_parent_and_activation':role=='dm','browser_errors':errors})
            save();browser.close()
        proof['status']='pass';save()
    except Exception as error:
        proof.update(status='failed',error=str(error),browser_errors=errors if 'errors' in locals() else []);save();raise
