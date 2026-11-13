import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
expect.set_options(timeout=60000)
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';f=json.loads((ROOT/'live-credentials.json').read_text());proof={'status':'running','journeys':[],'errors':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=ctx.new_page();page.set_default_timeout(60000);page.on('pageerror',lambda e:proof['errors'].append(str(e)))
 try:
  page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users']['dm']['username']);page.locator('#loginPassword').fill(f['users']['dm']['password']);page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
  page.goto(ORIGIN+'/characters');page.locator('a[href="/atlas"]').click();page.locator('#atlasNewTitle').fill('B06 credits compatibility');page.locator('#atlasCreate').click();expect(page.locator('#atlasTitle')).to_be_visible();world=page.url.split('world=')[-1]
  page.locator('#atlasLibraryLoad').click();expect(page.locator('#atlasLibrarySelect option')).to_have_count(1);page.locator('#atlasAttach').click();expect(page.locator('#atlasAttachConfirm')).to_be_visible();page.locator('#atlasAttachConfirm').click();expect(page.locator('#atlasAuthorMap option')).to_have_count(1);mid=page.locator('#atlasAuthorMap').input_value()
  page.locator('#atlasEditMap').click();expect(page.locator('#app')).to_have_attribute('data-state','ready',timeout=60000);page.locator('#mapTitle').fill('B06 credits retained');page.locator('#cloudSave').click();expect(page.locator('#atlasEditorStatus')).to_have_text('Atlaskarte gespeichert.',timeout=60000)
  source=ctx.request.get(ORIGIN+f'/api/atlas/worlds/{world}/maps/{mid}').json();assert len(source['bundle']['credits'])>20000
  page.locator('#atlasEditorBack').click();expect(page.locator('#atlasTitle')).to_be_visible();page.locator('#atlasMapVisible').check();page.locator('#atlasSave').click();expect(page.locator('#atlasAuthorStatus')).to_have_text('Gespeichert.');page.locator('#atlasPreview').click();page.locator('#atlasPublishConsent').check();page.locator('#atlasPublish').click();expect(page.locator('dialog.atlas-dialog')).to_have_count(0)
  response=ctx.request.get(ORIGIN+f'/api/atlas/worlds/{world}/backup?format=json');assert response.ok;backup=response.json();(ROOT/'backup-shape.json').write_text(json.dumps({'keys':list(backup),'credit_length':len(source['bundle']['credits'])}))
  page.screenshot(path=str(ROOT/'atlas-credits.png'));assert not proof['errors'];proof['journeys'].append('Archive → Atlas → own library map copy → editor save with full 20k+ credits → return → explicit publication → backup');proof['status']='pass'
 except BaseException as e:proof.update(status='fail',failure=str(e));raise
 finally:(ROOT/'live-result.json').write_text(json.dumps(proof,indent=2)+'\n');ctx.close();browser.close()
