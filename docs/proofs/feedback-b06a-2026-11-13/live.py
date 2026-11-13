import json,zipfile,io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright,expect
from tests.test_mapmaker_browser import Editor,CSP_PROBE
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';fixture=json.loads((ROOT/'live-credentials.json').read_text());proof={'status':'running','journeys':[],'errors':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
 try:
  for kind in ['dm','player']:
   ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);ctx.add_init_script(CSP_PROBE);page=ctx.new_page();page.set_default_timeout(45000);page.on('pageerror',lambda e:proof['errors'].append(str(e)))
   page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(fixture['users'][kind]['username']);page.locator('#loginPassword').fill(fixture['users'][kind]['password']);page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
   page.goto(ORIGIN+'/characters');page.locator('.book-dashboard-ribbon a[href="/mapmaker"]').click();page.wait_for_selector('#app[data-state=ready]');page.locator('#newEmpty').click();ed=Editor(ctx,page,proof['errors']);ed.drag([(500,500),(700,550)]);ed.menu('Als PNG exportieren')
   with page.expect_download(timeout=60000) as pending:page.locator('#exportBundle').click()
   target=ROOT/(kind+'-export.zip');pending.value.save_as(target)
   with zipfile.ZipFile(target) as archive:
    credits=archive.read('CREDITS.txt').decode();assert 'Rasterquellensammlung' in credits and 'Lynn' in credits
    with Image.open(io.BytesIO(archive.read(next(n for n in archive.namelist() if n.endswith('.png'))))) as image:image.load();assert image.info['Credits']==credits
   ed.assert_clean();proof['journeys'].append(kind+': Archive → Maps → raster gesture → export bundle; artist source collection matches embedded PNG metadata');ctx.close()
  proof['status']='pass'
 except BaseException as error:proof.update(status='fail',failure=str(error));raise
 finally:(ROOT/'live-result.json').write_text(json.dumps(proof,indent=2)+'\n');browser.close()
