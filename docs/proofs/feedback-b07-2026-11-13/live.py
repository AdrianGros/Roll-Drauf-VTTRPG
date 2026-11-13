import json,math
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from tests.test_feedback_b07_browser import click_world,PROBE
from tests.test_presentation_browser import preferences,contrast
expect.set_options(timeout=60000)
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';f=json.loads((ROOT/'live-credentials.json').read_text());proof={'status':'running','journeys':[],'checks':{},'errors':[]}
def login(ctx,role):
 page=ctx.new_page();page.set_default_timeout(60000);page.on('pageerror',lambda e:proof['errors'].append(str(e)));page.on('dialog',lambda d:d.accept())
 page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users'][role]['username']);page.locator('#loginPassword').fill(f['users'][role]['password']);page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
 page.goto(f'{ORIGIN}/campaigns?campaign_id={f["campaign_id"]}');action='open-session-dm' if role=='dm' else 'open-session';page.locator(f'[data-hub-action="{action}"][data-hub-session-id="{f["session_id"]}"]').click();page.wait_for_url(lambda u:'/play' in u);expect(page.locator('#mapWorld')).to_have_attribute('data-has-map','true');return page
def ctx_request(page,path,method='GET',body=None):
 return page.evaluate('''async ([path,method,body])=>{const r=await fetch(path,{method,headers:Auth.buildHeaders(method,true),credentials:'include',...(body?{body:JSON.stringify(body)}:{})});return {status:r.status,data:await r.json()}}''',[path,method,body])
with sync_playwright() as p:
 chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
 try:
  dc=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');pc=firefox.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
  for ctx in [dc,pc]:ctx.add_init_script(PROBE)
  preferences(pc,language='en',theme='night');dm=login(dc,'dm');player=login(pc,'player')
  for page,role in [(dm,'dm'),(player,'player')]:
   page.locator('[data-tool=measure]').click();expect(page.locator('#measureOptions')).to_be_visible();contrast(page,'#measureOptions label,#measureOptions select')
   for shape in ['square','circle','cone']:
    page.locator('#measureShape').select_option(shape);click_world(page,100,150);click_world(page,200,200);expect(page.locator(f'#measureLayer [data-shape={shape}]')).to_have_count(1);expect(page.locator('#tableSheet')).to_be_hidden();page.screenshot(path=str(ROOT/(role+'-'+shape+'.png')));page.keyboard.press('Escape');page.keyboard.press('Escape');expect(page.locator('#measureLayer')).to_be_empty()
   page.locator('[data-tool=select]').click();expect(page.locator('#measureOptions')).to_be_hidden()
   if role=='player':
    assert page.evaluate('window.__dmViewportBindings')==[];expect(page.locator('#toolLight,#toolWall,#wallEditPopover,#lightEditPopover')).to_have_count(0)
   else:assert len(page.evaluate('window.__dmViewportBindings'))==2
   assert page.evaluate('document.documentElement.scrollWidth')<=page.viewport_size['width']+1
   proof['journeys'].append(role+': campaign hub → session → Measure → square/circle/cone → cancel/tool switch; no unexpected token dock; independent authorized surface')
  base=f'/api/play/campaigns/{f["campaign_id"]}/sessions/{f["session_id"]}/vision'
  baseline=ctx_request(player,base+'/fog');assert baseline['status']==200
  before=len(baseline['data']['fog']['visible_cells']) if baseline['data'].get('fog') else 0
  dm.locator('#toolLight').click();click_world(dm,200,200);expect(dm.locator('.vision-light-marker')).to_have_count(1)
  dm.locator('.vision-light-dot').click();dm.locator('#lightEditDim').fill('350');dm.locator('#lightEditDim').press('Tab');expect(dm.locator('.vision-light-dim')).to_have_attribute('r','350');dm.locator('#lightEditBright').fill('300');dm.locator('#lightEditBright').press('Tab');expect(dm.locator('.vision-light-bright')).to_have_attribute('r','300');dm.locator('#btnLightEditClose').click()
  player.wait_for_function('() => document.querySelectorAll(".fog-cell").length>0')
  bright=ctx_request(player,base+'/fog');assert bright['status']==200;bright_count=len(bright['data']['fog']['visible_cells']);assert bright_count>before
  dm.locator('#toolWall').click();click_world(dm,300,100);click_world(dm,300,800);expect(dm.locator('.vision-wall-line')).to_have_count(1)
  def blocked():return len(ctx_request(player,base+'/fog')['data']['fog']['visible_cells'])
  player.wait_for_function('''async ([base,old])=>{const r=await fetch(base+'/fog',{headers:Auth.buildHeaders('GET',false),credentials:'include'});const d=await r.json();return d.fog.visible_cells.length<old}''',arg=[base,bright_count])
  wall_count=blocked();assert wall_count<bright_count
  covered=player.locator('.fog-cell').count();player.reload();expect(player.locator('.fog-cell')).to_have_count(covered);proof['checks']['own_fog_restored_after_reload']=True
  for endpoint in ['walls','lights']:
   assert ctx_request(player,base+'/'+endpoint)['status']==403
  assert ctx_request(player,base+'/lights','POST',{'x':10,'y':10})['status']==403
  assert ctx_request(player,base+'/walls','POST',{'x0':1,'y0':1,'x1':100,'y1':1})['status']==403
  click_world(dm,300,450);dm.locator('#wallEditSight').select_option('none');expect(dm.locator('.vision-wall-line.sight-none')).to_have_count(1);dm.locator('#btnWallEditClose').click();dm.reload();expect(dm.locator('.vision-wall-line.sight-none')).to_have_count(1);expect(dm.locator('.vision-light-bright')).to_have_attribute('r','300')
  click_world(dm,300,450);dm.locator('#btnWallDelete').click();expect(dm.locator('.vision-wall-line')).to_have_count(0);dm.locator('.vision-light-dot').click();dm.locator('#btnLightDelete').click();expect(dm.locator('.vision-light-marker')).to_have_count(0)
  proof['checks'].update(fog_visible_before=before,fog_visible_with_light=bright_count,fog_visible_behind_wall=wall_count,player_geometry_and_write_denials=True)
  proof['journeys'].append('DM light placement → radius edit → Player fog expands; blocking wall → Player visibility contracts → edit sight → reload persists → delete wall/light; Player cannot read raw geometry or write vision')
  assert not proof['errors'],proof['errors'];proof['status']='pass'
 except BaseException as e:
  proof.update(status='fail',failure=str(e))
  for name in ['dm','player']:
   try:locals()[name].screenshot(path=str(ROOT/(name+'-failure.png')))
   except Exception:pass
  raise
 finally:(ROOT/'live-result.json').write_text(json.dumps(proof,indent=2)+'\n');chrome.close();firefox.close()
