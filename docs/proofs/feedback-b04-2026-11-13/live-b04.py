import json,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';fixture=json.loads((ROOT/'live-credentials.json').read_text());proof={'status':'running','journeys':[],'errors':[]}
def login(context,kind):
 page=context.new_page();page.set_default_timeout(45000);page.on('pageerror',lambda e:proof['errors'].append(str(e)));page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(fixture['users'][kind]['username']);page.locator('#loginPassword').fill(fixture['users'][kind]['password']);page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u);return page
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=login(ctx,'dm')
 try:
  page.goto(ORIGIN+'/characters');page.locator('[data-dashboard-href="/srd-creator"]').click();page.locator('#scNewQuick').click();expect(page.locator('#scBuilder')).to_be_visible()
  page.get_by_role('button',name=re.compile('^Magier')).first.click();page.locator('#scLevel').fill('5');page.locator('#scLevel').press('Tab')
  name=page.evaluate("() => window.SrdCreator.subclassName(window.SrdCreator.L.classes.wizard.subclasses[0])")
  page.get_by_role('button',name=name,exact=True).click();expect(page.locator('[data-subclass-preview] details[data-feature-level="3"]').first).to_be_visible()
  page.get_by_role('button',name='Würfeln (4W6)',exact=True).click();page.locator('#scRollAll').click()
  for i in (1,2):
   for j,value in enumerate([6,5,4,1],1):
    control=page.get_by_label(f'Wurf {i}, Würfel {j}',exact=True);control.fill(str(value));control.press('Tab')
  page.locator('#scBase-str').select_option('0');page.locator('#scBase-dex').select_option('1');expect(page.locator('#scBase-con option[value="0"]')).to_be_disabled();expect(page.locator('#scBase-con option[value="1"]')).to_be_disabled()
  expect(page.locator('#scSave')).to_have_text('Gespeichert');page.reload();expect(page.locator('#scBase-str')).to_have_value('0');expect(page.locator('#scBase-dex')).to_have_value('1')
  before=page.evaluate('() => JSON.stringify(window.SrdCreator.app.draft.state)');page.locator('#scRefreshOrigins').click();expect(page.locator('#scSpellSort')).to_be_visible();assert before==page.evaluate('() => JSON.stringify(window.SrdCreator.app.draft.state)')
  page.locator('#scSpellSort').select_option('name');assert page.locator('a[href="/api/ce/authoring#ce-origins"]').get_attribute('target')=='_blank'
  proof['journeys'].append('DM archive → create hero → compact class facts → subclass rules → duplicate roll assignment → persisted reload → origin refresh → spell sort')
  page.screenshot(path=str(ROOT/'creator-desktop.png'))
  ctx.close();browser.close();browser=p.firefox.launch(headless=True);ctx=browser.new_context(viewport={'width':390,'height':1000},reduced_motion='reduce');page=login(ctx,'player')
  page.goto(ORIGIN+'/characters');page.locator(f'[data-dashboard-href^="/character-sheet?id={fixture["character_id"]}"]').first.click();page.get_by_role('tab',name='Verwaltung',exact=True).click();page.get_by_role('button',name='Stufe 6 aufsteigen',exact=True).click()
  expect(page.locator('#srdWizard [data-feature-level="6"]').first).to_be_visible();expect(page.locator('#srdWizard [data-feature-level="3"]')).to_have_count(0)
  sort=page.locator('#srdWizard .srd-prog-filterable select').first;expect(sort).to_be_visible();sort.focus();sort.select_option('name');assert sort.evaluate('n=>n===document.activeElement');assert page.evaluate('document.documentElement.scrollWidth')<=391
  proof['journeys'].append('Player archive → own sheet → Management → level6: existing subclass new features + spell sorting on mobile Firefox')
  page.screenshot(path=str(ROOT/'levelup-mobile.png'));assert not proof['errors'],proof['errors'];proof['status']='pass'
 except BaseException as error:proof.update(status='fail',failure=str(error));raise
 finally:
  (ROOT/'live-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');ctx.close();browser.close()
