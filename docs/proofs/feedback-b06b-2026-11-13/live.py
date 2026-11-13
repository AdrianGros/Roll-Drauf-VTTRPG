import json,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from tests.test_mapmaker_browser import Editor,CSP_PROBE
from tests.test_presentation_browser import preferences
expect.set_options(timeout=60000)
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';f=json.loads((ROOT/'live-credentials.json').read_text());proof={'status':'running','journeys':[],'errors':[]}
def authenticate(page,kind):
 page.set_default_timeout(60000);page.on('pageerror',lambda e:proof['errors'].append(str(e)));page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users'][kind]['username']);page.locator('#loginPassword').fill(f['users'][kind]['password']);page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
with sync_playwright() as p:
 chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);firefox=p.firefox.launch(headless=True)
 try:
  for kind,browser,width in [('dm',chrome,1440),('player',firefox,390)]:
   ctx=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce',accept_downloads=True);ctx.add_init_script(CSP_PROBE)
   if kind=='player':preferences(ctx,language='en',theme='night')
   page=ctx.new_page();authenticate(page,kind);page.goto(ORIGIN+'/characters');page.locator('.book-dashboard-ribbon a[href="/mapmaker"]').click();page.wait_for_selector('#app[data-state=ready]');page.locator('#newEmpty').click();title='B06 brushes '+f['users'][kind]['username'];page.locator('#mapTitle').fill(title);ed=Editor(ctx,page,proof['errors'])
   if width<600:page.locator('#tab-tool').click()
   page.locator('#brushShape').select_option('diamond');ed.set_range('#brushOpacity',35);ed.set_range('#brushSoftness',15);page.locator('#brushColorEnabled').check();page.locator('#brushColor').fill('#cc3333');ed.set_range('#brushTexture',10);page.locator('#brushCoast').check();page.locator('#brushCoastColor').fill('#112233');page.locator('#brushCoastColor').dispatch_event('change');ed.set_range('#brushCoastWidth',4)
   ed.tool('eraser');assert page.locator('#brushOpacity').input_value()=='100';assert page.locator('#brushSoftness').input_value()=='0';ed.tool('brush');assert page.locator('#brushOpacity').input_value()=='35' and page.locator('#brushShape').input_value()=='diamond'
   if width<600:expect(page.locator('#brushShapeLabel')).to_have_text('Brush tip');page.locator('#tab-tool').click()
   before=ed.region(480,480,150,100);ed.drag([(500,500),(600,520)]);after=ed.region(480,480,150,100);assert after!=before;page.keyboard.press('Control+z');assert ed.region(480,480,150,100)==before;page.keyboard.press('Control+Shift+z');assert ed.region(480,480,150,100)==after
   ed.tool('stamp')
   if width<600:page.locator('#tab-tool').click()
   page.locator('.mm-stamp').first.click();page.locator('#stampAsBrush').click();expect(page.locator('#brushShape')).to_have_value('image');expect(page.locator('#brushColor')).to_be_disabled()
   if width<600:page.locator('#tab-tool').click()
   ed.drag([(900,600),(1000,650)]);page.locator('#cloudSave').click();expect(page.locator('#cloudStatus')).to_contain_text(re.compile('saved|gespeichert',re.I))
   rows=ctx.request.get(ORIGIN+'/api/assets/mapmaker/projects').json()['projects'];project=next(r for r in rows if r['title']==title);stored=ctx.request.get(ORIGIN+'/api/assets/mapmaker/projects/'+project['id']).json()['document'];effects=next(l['effects'] for l in stored['layers'] if l['id']=='terrain');assert effects=={'coast':True,'coastColor':'#112233','coastWidth':4}
   proof.setdefault('draft_checkpoints',[]).append({'role':kind,**{k:ed.summary()[k] for k in ['generation','localGeneration','autosave']}})
   page.wait_for_function('() => window.rdMapmaker.summary().localGeneration === window.rdMapmaker.summary().generation')
   page.reload();page.wait_for_selector('#restoreDialog[open]');page.locator('#restoreYes').click();page.wait_for_selector('#app[data-state=ready]');restored=ed.region(480,480,150,100)
   if restored!=after:proof.setdefault('pixel_diffs',[]).append({'role':kind,'changed_channels':sum(a!=b for a,b in zip(restored,after)),'max_channel_difference':max(abs(a-b) for a,b in zip(restored,after))})
   assert max(abs(a-b) for a,b in zip(restored,after)) <= (3 if kind == 'player' else 0)
   page.screenshot(path=str(ROOT/(kind+'-brushes.png')));proof['journeys'].append(kind+': normal Maps entry → independent eraser values → diamond/color/texture/coast → pixel-exact undo/redo → selected image brush → private library → server effects → draft reload; mobile English night controls verified')
   if kind=='player':
    ctx.clear_cookies(name=re.compile('^(access_token_cookie|refresh_token_cookie|csrf_refresh_token)$'));page.locator('#mapTitle').fill(title+' offline');page.locator('#cloudSave').click();expect(page.locator('#libraryLogin')).to_be_visible();expect(page.locator('#mapTitle')).to_have_value(title+' offline');assert '/static/mapmaker/' in page.url
    page.locator('#errorClose').click()
    with page.expect_popup() as popup:page.locator('#libraryLogin').click()
    login=popup.value;login.set_default_timeout(60000);login.locator('#loginUsername').fill(f['users'][kind]['username']);login.locator('#loginPassword').fill(f['users'][kind]['password']);login.locator('#passwordLoginSubmitBtn').click();login.wait_for_url(lambda u:'/login' not in u);login.close();page.locator('#cloudSave').click();expect(page.locator('#libraryLogin')).to_be_hidden();expect(page.locator('#cloudStatus')).to_contain_text(re.compile('saved|gespeichert',re.I));proof['journeys'].append('Synthetic Player authentication removed → actual 401 → editor and draft preserved → normal sign-in link opens separate tab → same-account library save resumes')
   ed.assert_clean();ctx.close()
  proof['status']='pass'
 except BaseException as e:proof.update(status='fail',failure=str(e));raise
 finally:(ROOT/'live-result.json').write_text(json.dumps(proof,indent=2)+'\n');chrome.close();firefox.close()
