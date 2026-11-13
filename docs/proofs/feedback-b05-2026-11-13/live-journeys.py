import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from tests.test_mapmaker_browser import Editor,GRASS,CSP_PROBE
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';f=json.loads((ROOT/'live-credentials.json').read_text());proof={'status':'running','journeys':[],'errors':[]};title='Feedback B05 '+f['users']['dm']['username']
def login(context,kind='dm'):
 context.add_init_script(CSP_PROBE)
 page=context.new_page();page.set_default_timeout(45000);page.on('pageerror',lambda e:proof['errors'].append(str(e)));page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users'][kind]['username']);page.locator('#loginPassword').fill(f['users'][kind]['password']);page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u);return page
with sync_playwright() as p:
 chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True);ctx=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');second=firefox.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce')
 try:
  page=login(ctx);page.goto(ORIGIN+'/characters');page.locator('.book-dashboard-ribbon a[href="/mapmaker"]').click();page.wait_for_url(ORIGIN+'/static/mapmaker/index.html');page.wait_for_selector('#app[data-state=ready]');page.locator('#newEmpty').click();page.locator('#mapTitle').fill(title)
  ed=Editor(ctx,page,proof['errors']);ed.tool('stamp');page.locator('.mm-stamp').first.click();ed.click_doc(400,400);ed.click_doc(700,500);ed.tool('select');ed.drag([(250,250),(850,650)]);assert ed.summary()['selectionCount']==2
  count=ed.summary()['historySteps'];ed.drag([(400,400),(500,450)]);assert ed.summary()['historySteps']==count+1;page.locator('#groupDelete').click();assert not ed.summary()['items'];page.locator('#undoVisible').click();assert len(ed.summary()['items'])==2
  page.screenshot(path=str(ROOT/'group-desktop.png'))
  ed.tool('label');page.locator('#labelNamed').uncheck();ed.click_doc(1500,700);assert any(i.get('text')=='' and i.get('pin') for i in ed.summary()['items'])
  ed.tool('path');ed.drag([(1000,400),(1200,650),(1400,400)]);assert any(i.get('curve') for i in ed.summary()['items']);ed.tool('select');page.locator('#pathNodeMode').check()
  ed.tool('tile');page.locator('#tilePack').select_option('kenney-tiny');page.locator('#tileSearch').fill('Gras');page.locator(f'.mm-tile-btn[data-tile="{GRASS}"]').click()
  for x in (325,357,453):ed.click_doc(x,325)
  ed.tool('select');ed.drag([(315,315),(385,355)]);assert ed.summary()['selectionCount']==2
  original=next(l for l in ed.summary()['layers'] if l['kind']=='tiles')['tiles'];ed.drag([(335,335),(431,335)]);assert next(l for l in ed.summary()['layers'] if l['kind']=='tiles')['tiles']==original
  ed.drag([(335,335),(335,399)]);assert {(t['col'],t['row']) for t in next(l for l in ed.summary()['layers'] if l['kind']=='tiles')['tiles']}=={(10,12),(11,12),(14,10)}
  page.locator('#cloudSave').click();expect(page.locator('#cloudStatus')).to_have_text('In Bibliothek gespeichert');proof['journeys'].append('Own Maps: marquee → group move/delete/undo → nameless pin → curved path/node mode → protected tile collision/move → private library save')
  mobile=login(second);mobile.goto(ORIGIN+'/characters');mobile.locator('.book-dashboard-ribbon a[href="/mapmaker"]').click();mobile.wait_for_url(ORIGIN+'/static/mapmaker/index.html');mobile.wait_for_selector('#app[data-state=ready]');row=mobile.locator('#libraryList li').filter(has_text=title);expect(row).to_be_visible();row.locator('.mm-btn-primary').click();expect(mobile.locator('#mapTitle')).to_have_value(title)
  summary=mobile.evaluate('() => window.rdMapmaker.summary()');assert summary['selectionCount']==0;assert any(i.get('curve') for i in summary['items']);assert any(i.get('text')=='' and i.get('pin') for i in summary['items']);assert len(next(l for l in summary['layers'] if l['kind']=='tiles')['tiles'])==3;assert mobile.evaluate('document.documentElement.scrollWidth')<=391
  assert not mobile.evaluate('window.__csp'),mobile.evaluate('window.__csp')
  mobile.screenshot(path=str(ROOT/'restored-mobile.png'));proof['journeys'].append('Same map owner in fresh mobile Firefox: normal Maps library entry → saved map restored, curve/pin/cells retained; selection remains transient')
  # A Player has the same ordinary Maps entry and can create their own map,
  # while the DM account's private map is absent and cannot be fetched.
  player_ctx=chrome.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
  try:
   player=login(player_ctx,'player');player.goto(ORIGIN+'/characters');player.locator('.book-dashboard-ribbon a[href="/mapmaker"]').click();player.wait_for_selector('#app[data-state=ready]');expect(player.locator('#libraryList li').filter(has_text=title)).to_have_count(0)
   owner_maps=ctx.request.get(ORIGIN+'/api/assets/mapmaker/projects');assert owner_maps.ok
   rows=owner_maps.json()['projects'];project=next(r for r in rows if r['title']==title)
   foreign=player_ctx.request.get(ORIGIN+'/api/assets/mapmaker/projects/'+project['id']);assert foreign.status==404
   player.locator('#newEmpty').click();player.locator('#mapTitle').fill('Player B05 '+f['users']['player']['username']);pe=Editor(player_ctx,player,proof['errors']);pe.tool('label');player.locator('#labelNamed').uncheck();pe.click_doc(500,500);player.locator('#cloudSave').click();expect(player.locator('#cloudStatus')).to_have_text('In Bibliothek gespeichert')
   pe.assert_clean()
   proof['journeys'].append('Player normal Maps entry → private DM map absent/404 → own nameless-pin map saved')
  finally:player_ctx.close()
  ed.assert_clean();proof['status']='pass'
 except BaseException as error:proof.update(status='fail',failure=str(error));raise
 finally:
  (ROOT/'live-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');ctx.close();second.close();chrome.close();firefox.close()
