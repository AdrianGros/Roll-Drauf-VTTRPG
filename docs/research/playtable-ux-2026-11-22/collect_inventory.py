"""Capture the shipped Playtable composition in an isolated SQLite/browser fixture.

This is research instrumentation, never an application module or production test.
No lane environment, account credentials or external network are used.
"""
import io
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tests.test_personal_actions_browser import action_site
from tests.play_shared import add_map, create_token
from vtt.extensions import db
from vtt.models import Campaign, Character, GameSession, SceneLight, SceneWall, User, TokenState
from vtt.play.service import ensure_session_state, init_scene_stack
from sqlalchemy.orm.attributes import flag_modified

OUT = Path(os.environ.get('INVENTORY_OUT', str(Path(__file__).parent / 'evidence')))
OUT.mkdir(parents=True, exist_ok=True)

EXTRACT = r"""() => {
 const control='button,a[href],input,select,textarea,summary,[role=button],[role=menuitem],.token-marker,.turn-item';
 const information='label,legend,h1,h2,h3,h4,p,small,option,[role=status],[role=alert],[data-ui-key],[title],[placeholder],.tool-label,.chip-label,.hint,span,strong,kbd,output,dt,dd,li,div';
 const clean=s=>(s||'').replace(/\s+/g,' ').trim();
 const path=e=>{if(e.id)return '#'+CSS.escape(e.id);const a=[];for(let n=e;n&&n!==document.body;n=n.parentElement){if(n.id){a.unshift('#'+CSS.escape(n.id));break;}const peers=n.parentElement?[...n.parentElement.children].filter(p=>p.tagName===n.tagName):[];a.unshift(n.tagName.toLowerCase()+':nth-of-type('+(peers.indexOf(n)+1)+')');}return a.join(' > ');};
 const region=e=>{
  if(e.closest('.left-toolbar'))return ['B','Unteres Menüband'];
  if(e.closest('#personalActionBar'))return ['P','Persönliche Aktionsleiste über dem Menüband'];
  if(e.closest('#actionHotbar'))return ['A','Generische Aktionsleiste über dem Menüband'];
  const w=e.closest('.play-window');if(w)return ['W',w.id+' · freies Tischfenster'];
  const d=e.closest('dialog,[role=dialog]');if(d)return ['D',(d.id||d.getAttribute('aria-label')||'Dialog')+' · Dialog/Popover'];
  if(e.closest('#appMenu'))return ['M','Tischmenü (unten über Zurück)'];
  if(e.closest('#tokenSelectionBar'))return ['T','Tokenauswahl · schwebende Bearbeitung'];
  if(e.closest('#tokenCreatePanel'))return ['T','Token platzieren · schwebendes Formular'];
  if(e.closest('#measureOptions'))return ['K','Kartenfläche · Messoptionen'];
  if(e.closest('#sheetDrawer'))return ['S','Charakterbogen-Lade · Rahmen (Bogeninhalt eigener Scope)'];
  if(e.closest('.play-status-strip,.stage-topbar,.book-dashboard-meta'))return ['H','Oberer Sitzungs-/Ansichtsbereich'];
  if(e.closest('#mapViewport'))return ['K','Kartenfläche und Etagenhinweis'];
  if(e.closest('.book-dashboard-topbar,.vtt-main-nav'))return ['N','Rahmennavigation (teilweise ausgeblendet)'];
  return ['R','Sonstiger Rahmen oder inaktiver Altcontainer'];
 };
 return [...new Set(document.querySelectorAll(control+','+information))].filter(e=>{
  if(e.closest('script,style,svg'))return false;
  if(e.matches('div,span,strong,li')&&!e.matches(control)&&!clean([...e.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' '))&&!e.matches('[role=status],[role=alert],[id*=Status],[id*=Badge],[id*=Label],#activePageName,#presenceRoster,#floorViewStatus'))return false;
  return true;
 }).map(e=>{
  const style=getComputedStyle(e),r=e.getBoundingClientRect(),shown=Boolean(e.getClientRects().length)&&style.visibility!=='hidden'&&!e.closest('[hidden]');
  const parent=e.closest('button,a[href],label');
  const label=e.labels?.length?[...e.labels].map(n=>clean(n.textContent)).join(' / '):'';
  const direct=clean([...e.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' '));
  const text=clean(e.textContent).slice(0,650);
  const kind=e.matches(control)?'control':'information';
  const [zone,location]=region(e);
  return {tag:e.tagName.toLowerCase(),id:e.id||null,selector:path(e),kind,zone,location,
   text:kind==='control'&&['input','textarea','select'].includes(e.tagName.toLowerCase())?label:text,
   direct_text:direct,label,aria_label:e.getAttribute('aria-label'),title:e.getAttribute('title'),placeholder:e.getAttribute('placeholder'),
   role:e.getAttribute('role'),type:e.getAttribute('type'),ui_key:e.getAttribute('data-ui-key'),
   associated_control:e.getAttribute('for')||(parent&&parent!==e?path(parent):null),
   attributes:Object.fromEntries([...e.attributes].filter(a=>/^data-(tool|tab|pa-|action-code|rect-key)|^aria-(expanded|pressed|selected|controls)$/.test(a.name)).map(a=>[a.name,a.value])),
   classes:e.className||'',visible:shown,in_viewport:shown&&r.right>0&&r.left<innerWidth&&r.bottom>0&&r.top<innerHeight,
   disabled:e.matches(':disabled,[aria-disabled=true]'),rect:shown?{x:+r.x.toFixed(1),y:+r.y.toFixed(1),width:+r.width.toFixed(1),height:+r.height.toFixed(1)}:null,
   style:{font:style.fontFamily,font_size:style.fontSize,height:style.height,padding:style.padding,border_radius:style.borderRadius,background:style.backgroundColor,color:style.color},
   options:e.matches('select')?[...e.options].map(o=>({value:o.value,text:clean(o.textContent)})):undefined};
 });
}"""

with TemporaryDirectory(prefix='playtable-inventory-') as scratch:
    patch = pytest.MonkeyPatch()
    generator = action_site.__wrapped__(Path(scratch), patch)
    app, origin, info = next(generator)
    captures = []
    actions = []
    try:
        with app.app_context():
            campaign=db.session.get(Campaign,info['campaign'])
            session=db.session.get(GameSession,info['session'])
            owner=db.session.get(User,campaign.owner_id)
            first=db.session.get(TokenState,info['token'])
            first.x=140;first.y=140;first.metadata_json={'position_mode':'pixel'}
            character=db.session.get(Character,info['character'])
            character.character_data['srdCompanions']=[dict(id='c12345678',name='Inventar-Wolf',kind='Wolf',speed='12 m',hpMax=20,hpCurrent=13,ac=13,attacks='',notes='')]
            flag_modified(character,'character_data')
            from vtt.models.character_hotbar import CharacterHotbar
            db.session.add(CharacterHotbar(user_id=info['player_id'],character_id=character.id,slots=['ability:str','weapon_attack:unarmed'],revision=1))
            map_id=session.map_id
            session_map=__import__('vtt.models',fromlist=['CampaignMap']).CampaignMap.query.get(map_id)
            session_map.width=1200;session_map.height=900;session_map.name='Die alte Sternwarte'
            other=add_map(campaign,owner,'Kellergewölbe')
            init_scene_stack(campaign,session,owner,[map_id,other.id])
            npc=create_token(campaign,session,ensure_session_state(campaign,session),owner.id,name='Wächter',token_type='monster',x=440,y=280)
            npc.metadata_json={'position_mode':'pixel'};npc.is_loot_source=True
            db.session.add(SceneWall(campaign_map_id=map_id,x0=600,y0=0,x1=600,y1=800,sight='normal',light='normal',created_by=owner.id))
            db.session.add(SceneLight(campaign_map_id=map_id,x=180,y=180,bright_radius=200,dim_radius=300,created_by=owner.id))
            db.session.commit()
            info.update(map_id=map_id,npc_id=npc.id)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            def context(role,width=1440,height=1000,locale='de'):
                ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                ctx.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({schema:1,theme:'night',language:'"+locale+"',accent:'default',unit:'m'}))")
                ctx.add_init_script("""Object.defineProperty(window,'PlayWindows',{configurable:true,set(K){Object.defineProperty(window,'PlayWindows',{value:K,writable:true,configurable:true});const mount=K.prototype.mount;K.prototype.mount=function(){window.__inventoryUI=this.ui;return mount.call(this);};}});""")
                ctx.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
                page=ctx.new_page();page.set_default_timeout(12000)
                page.on('dialog',lambda dialog:dialog.dismiss())
                page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
                expect(page.locator('#btnDiceWindow')).to_be_visible(timeout=30000)
                page.wait_for_function('() => Boolean(window.__inventoryUI?.floorView)')
                page.wait_for_function('() => Boolean(window.__inventoryUI?.socket)')
                page.evaluate('() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                return ctx,page
            def capture(page,state,screenshot=False):
                rows=page.evaluate(EXTRACT)
                captures.append({'state':state,'viewport':page.viewport_size,'seat':page.locator('body').get_attribute('data-table-seat'),'elements':rows})
                if screenshot:page.screenshot(path=str(OUT/(state+'.png')))
                (OUT/'captures.json').write_text(json.dumps(captures,ensure_ascii=False))
            def close(page):
                page.evaluate("""()=>{document.querySelectorAll('dialog[open]').forEach(d=>d.close());const u=window.__inventoryUI;for(const [id,item]of u.windows.items)if(!item.element.hidden)u.windows.close(id);u._setTool('select');u._selectToken(null);for(const id of ['appMenu','tokenCreatePanel','conditionsPopover','lootPopover','wallEditPopover','lightEditPopover','visibleTokensPopover']){const e=document.getElementById(id);if(e)e.hidden=true;}}""")
            def visit(page,name,fn):
                try:
                    close(page);fn();capture(page,name,True);actions.append({'state':name,'status':'captured'})
                except Exception as error:
                    actions.append({'state':name,'status':'not-captured','error':str(error)[:300]})
                    capture(page,name+'-partial')
            ctx,dm=context('dm')
            capture(dm,'dm-desktop-baseline',True)
            def open_window(key):
                dm.evaluate('(key)=>window.__inventoryUI.windows.open(key)',key)
                expect(dm.locator('#window-'+key)).to_be_visible()
            for key in ['layersWidget','turnOrderWidget','tokenWidget','tokenLayersWidget','mapPresentation','mapFloors','panel-chat','panel-tools','panel-journal','beyond20']:
                visit(dm,'dm-window-'+key,lambda key=key:open_window(key))
            visit(dm,'dm-journal-session-controls',lambda:(dm.evaluate("window.__inventoryUI.windows.open('panel-journal')"),dm.locator('#journalSessionControls').evaluate('e=>e.open=true')))
            visit(dm,'dm-app-menu',lambda:dm.locator('#btnBack').click())
            visit(dm,'dm-display-preferences',lambda:dm.evaluate('window.VTTDisplay.open()'))
            visit(dm,'dm-measure-options',lambda:dm.locator('[data-tool=measure]').click())
            def selected():
                dm.locator('[data-tool=select]').click()
                dm.evaluate('(id)=>window.__inventoryUI._selectToken(id)',info['token'])
            visit(dm,'dm-selected-character',selected)
            visit(dm,'dm-conditions',lambda:(selected(),dm.locator('#btnTokenConditions').click(),expect(dm.locator('#conditionsPopover')).to_be_visible()))
            visit(dm,'dm-token-create',lambda:(dm.evaluate('window.__inventoryUI._openTokenCreatePanel(300,240,{clientX:300,clientY:240})'),expect(dm.locator('#tokenCreatePanel')).to_be_visible()))
            visit(dm,'dm-loot',lambda:(dm.evaluate('(id)=>window.__inventoryUI._selectToken(id)',info['npc_id']),dm.locator('#btnTokenLoot').click(),expect(dm.locator('#lootPopover')).to_be_visible()))
            visit(dm,'dm-wall-edit',lambda:dm.evaluate('window.__inventoryUI._openWallEditPopover(1,{clientX:300,clientY:200})'))
            visit(dm,'dm-light-edit',lambda:dm.evaluate('window.__inventoryUI._openLightEditPopover(1,{clientX:300,clientY:200})'))
            visit(dm,'dm-map-library',lambda:(dm.evaluate("async()=>{const {mount}=await import('/static/js/play-map-library.js');await mount(window.__inventoryUI).open();}"),expect(dm.locator('#mapLibraryDialog')).to_be_visible()))
            # Render the existing local floor-card view with synthetic metadata; no upload/network write.
            def floors():
                dm.evaluate("""()=>{const u=window.__inventoryUI;u.floorDM.render({revision:1,enabled:false,active_floor_id:1,width:1200,height:900,limitation:'Etagen ändern nur das Kartenbild. Tokens, Wände, Licht und Nebel bleiben auf einer gemeinsamen 2D-Karte.',floors:[{id:1,name:'Erdgeschoss',reveal_below:false,openings:[]},{id:2,name:'Balkon',reveal_below:true,openings:[{x:80,y:80,width:180,height:180}]}]});u.windows.open('mapFloors');}""")
            visit(dm,'dm-floor-cards-synthetic',floors)
            for width,height in [(1024,768),(390,844)]:
                c,p=context('dm',width,height);capture(p,f'dm-{width}-baseline',True);c.close()
            c,p=context('player')
            capture(p,'player-baseline',True)
            def player_selected():
                p.locator(f'.token-marker[data-token-id="{info["token"]}"]').click()
                expect(p.locator('[data-pa-edit]')).to_be_visible()
            visit(p,'player-personal-actions',player_selected)
            visit(p,'player-action-editor',lambda:(player_selected(),p.locator('[data-pa-edit]').click()))
            visit(p,'player-companions',lambda:(player_selected(),p.locator('[data-pa-companions]').click(),expect(p.locator('#paCompanionSelect')).to_contain_text('Inventar-Wolf')))
            c.close();ctx.close();browser.close()
        (OUT/'capture-coverage.json').write_text(json.dumps({'status':'captured','authentication':'isolated throwaway SQLite accounts; no production sessions','source_revision':'a6abcce9e34b289efb88cb525a0c4c3ae87037e4','instrumentation':'Expose the existing PlayWindows.ui reference; no stylesheet or layout replacement. Floor cards use explicitly synthetic view metadata.','states':actions},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'captures':len(captures),'states_needing_followup':[a['state'] for a in actions if a['status']!='captured']},ensure_ascii=False))
    finally:
        generator.close();patch.undo()
