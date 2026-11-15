"""Authenticated live journeys using only the normal campaign/session navigation."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from tests.test_playtable_token_clipboard_browser import client_point

ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de'
f=json.loads((ROOT/'live-credentials.json').read_text())
proof={'status':'running','url':ORIGIN,'journeys':[],'checks':{},'errors':[]}
expect.set_options(timeout=45000)
PROBE='''window.__layerWire=[];window.__layerSockets=[];let factory;
Object.defineProperty(window,'io',{configurable:true,get(){return factory;},set(value){factory=new Proxy(value,{apply(target,self,args){const socket=Reflect.apply(target,self,args);window.__layerSockets.push(socket);socket.onAny((event,...args)=>window.__layerWire.push({event,args}));return socket;}});}});'''

def request(page,path,method='GET',body=None):
    return page.evaluate('''async ([path,method,body])=>{const r=await fetch(path,{method,headers:Auth.buildHeaders(method,true),credentials:'include',...(body?{body:JSON.stringify(body)}:{})});return {status:r.status,data:await r.json()}}''',[path,method,body])

def enter(ctx,kind,mode):
    ctx.add_init_script(PROBE)
    page=ctx.new_page();page.set_default_timeout(45000)
    page.on('pageerror',lambda error:proof['errors'].append(str(error)))
    page.goto(ORIGIN+'/login.html')
    page.locator('#loginUsername').fill(f['users'][kind]['username']);page.locator('#loginPassword').fill(f['users'][kind]['password'])
    page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
    page.goto(f"{ORIGIN}/campaigns?campaign_id={f['campaign_id']}")
    action='open-session-dm' if mode=='dm' else 'open-session'
    page.locator(f'[data-hub-action="{action}"][data-hub-session-id="{f["session_id"]}"]').click()
    page.wait_for_url(lambda u:'/play' in u)
    expect(page.locator('body')).to_have_attribute('data-table-seat',mode)
    expect(page.locator('#mapWorld')).to_have_attribute('data-has-map','true')
    proof['journeys'].append(kind+': Login → Kampagnen → eigener Hub → Sitzung ('+mode+')')
    return page

with sync_playwright() as p:
    chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
    dc=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    pc=firefox.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
    oc=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    player_requests=[]
    pc.on('request',lambda r:player_requests.append(r.url))
    try:
        player=enter(pc,'player','player');dm=enter(dc,'dm','dm')
        expect(dm.locator('#presenceRoster')).to_contain_text(f['users']['player']['username'])
        expect(player.locator('#presenceRoster')).to_contain_text(f['users']['dm']['username'])
        expect(player.locator('.token-marker')).to_have_count(1)
        expect(player.locator('#tokenLayersWidget,#tokenSelectionBar')).to_have_count(0)
        assert not any('play-dm.js' in u or 'play-token-layers-dm' in u for u in player_requests)
        base=f"/api/play/campaigns/{f['campaign_id']}/sessions/{f['session_id']}"
        assert 'Goblin' not in json.dumps(request(player,base+'/bootstrap')['data'])
        assert 'Goblin' not in player.evaluate('JSON.stringify(window.__layerWire)')
        proof['checks']['player_initial_http_socket_and_composition']='pass'
        dm.locator('#dock-tokenLayersWidget').click();dm.locator('[data-token-layer=dm_only]').click()
        expect(player.locator('.token-marker')).to_have_count(1)
        dm.locator('.table-dock-close').click()
        goblins=dm.locator('.token-marker:not(.token-inactive-layer)');goblins.first.click();goblins.nth(1).click(modifiers=['Shift'])
        expect(dm.locator('#tokenSelectionCount')).to_have_text('2 ausgewählt')
        expect(dm.locator('.token-selection-group')).to_have_count(1)
        expect(dm.locator('#tokenSelectionGroups')).to_contain_text('Goblin × 2')
        dm.screenshot(path=str(ROOT/'dm-selection.png'))
        dm.locator('[data-selection-layer=public]').click();expect(player.locator('.token-marker')).to_have_count(3)
        player.screenshot(path=str(ROOT/'player-revealed-firefox-390.png'))
        proof['checks']['group_reveal_to_firefox']='pass'
        dm.locator('.token-marker',has_text='Goblin').first.click();dm.locator('.token-marker',has_text='Goblin 2').click(modifiers=['Shift'])
        dm.locator('[data-selection-layer=dm_only]').click();expect(player.locator('.token-marker')).to_have_count(1)
        player.reload();expect(player.locator('.token-marker')).to_have_count(1)
        expect(player.locator('#presenceRoster')).to_contain_text(f['users']['dm']['username'])
        assert 'Goblin' not in json.dumps(request(player,base+'/bootstrap')['data'])
        assert 'Goblin' not in player.evaluate('JSON.stringify(window.__layerWire)')
        proof['checks']['hide_and_player_reload']='pass'
        dm.locator('[data-tool=token]').click();dm.mouse.click(*client_point(dm,490,280))
        expect(dm.locator('#tokenCreateVisibility')).to_have_value('dm_only')
        dm.locator('#tokenCreateName').fill('Hidden reinforcement');dm.locator('#btnTokenCreateConfirm').click()
        expect(dm.locator('.token-marker')).to_have_count(4);expect(player.locator('.token-marker')).to_have_count(1)
        assert 'Hidden reinforcement' not in player.evaluate('JSON.stringify(window.__layerWire)')
        proof['checks']['hidden_placement_no_player_event_leak']='pass'
        dm.locator('[data-tool=select]').click();dm.locator('.token-marker',has_text='Hidden reinforcement').click();dm.keyboard.press('Control+c')
        dm.locator('#dock-tokenLayersWidget').click();dm.locator('[data-token-layer=public]').click();dm.locator('.table-dock-close').click()
        dm.mouse.move(*client_point(dm,700,280));dm.keyboard.press('Control+v')
        expect(player.locator('.token-marker')).to_have_count(2)
        proof['checks']['clipboard_destination_layer']='pass'
        # The owner enters a separately authorized Player context via its established hub action.
        owner_player=enter(oc,'dm','player')
        expect(owner_player.locator('#presenceRoster')).to_contain_text(f['users']['player']['username'])
        expect(owner_player.locator('.token-marker')).to_have_count(2)
        expect(owner_player.locator('#tokenLayersWidget,#tokenSelectionBar')).to_have_count(0)
        assert request(owner_player,base+'/surface')['status']==403
        token_path=f"/api/campaigns/{f['campaign_id']}/sessions/{f['session_id']}/tokens/{f['token_ids']['Goblin']}"
        result=request(owner_player,token_path,'PUT',{'base_version':3,'patch':{'visibility':'public'}})
        assert result['status']==403,result['status']
        assert 'Goblin' not in json.dumps(request(owner_player,base+'/bootstrap')['data'])
        assert 'Goblin' not in owner_player.evaluate('JSON.stringify(window.__layerWire)')
        proof['checks']['owner_player_cannot_read_surface_or_reveal']='pass'
        dm.reload();expect(dm.locator('body')).to_have_attribute('data-table-seat','dm')
        expect(dm.locator('.token-marker')).to_have_count(5)
        expect(dm.locator('.token-inactive-layer')).to_have_count(3)
        player.reload();expect(player.locator('.token-marker')).to_have_count(2)
        proof['checks']['parallel_tabs_reload_persist_visibility']='pass'
        dm.set_viewport_size({'width':390,'height':844})
        dm.locator('#dock-tokenLayersWidget').click();expect(dm.locator('[data-token-layer=dm_only]')).to_be_visible()
        dm.locator('[data-token-layer=dm_only]').click();expect(dm.locator('[data-token-layer=dm_only]')).to_have_attribute('aria-pressed','true')
        dm.screenshot(path=str(ROOT/'dm-layers-390.png'))
        assert dm.evaluate('document.documentElement.scrollWidth')<=391
        dm.locator('#dock-tokenLayersWidget').focus();dm.keyboard.press('Home');expect(dm.locator('#dock-layersWidget')).to_be_focused()
        dm.keyboard.press('End');expect(dm.locator('#dock-tokenLayersWidget')).to_be_focused()
        proof['checks']['mobile_390_and_keyboard_dock']='pass'
        proof['journeys'].append('DM: Tisch → Layers → DM-Tokenauswahl → gruppierte Freigabe/Rücknahme → Platzierung → Clipboard → erneuter Eintritt; Player und Owner-as-Player parallel')
        assert not proof['errors'],proof['errors']
        proof['status']='pass'
    except BaseException as error:
        proof.update(status='fail',failure=str(error));raise
    finally:
        (ROOT/'live.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
        dc.close();pc.close();oc.close();chrome.close();firefox.close()
