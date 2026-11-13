import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from tests.test_presentation_browser import contrast
ROOT=Path('/delivery');ORIGIN='https://vtt.roll-drauf.de';f=json.loads((ROOT/'live-credentials.json').read_text())
proof={'status':'running','journeys':[],'errors':[]}
with sync_playwright() as p:
 for engine,width,kind,language in [('chromium',1440,'dm','de'),('firefox',390,'player','en')]:
  browser=getattr(p,engine).launch(headless=True,args=['--no-sandbox'] if engine=='chromium' else []);context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce');page=context.new_page();page.set_default_timeout(45000);page.on('pageerror',lambda e:proof['errors'].append(str(e)))
  try:
   page.goto(ORIGIN+'/login.html');page.locator('#loginUsername').fill(f['users'][kind]['username']);page.locator('#loginPassword').fill(f['users'][kind]['password']);page.locator('#passwordLoginSubmitBtn').click();page.wait_for_url(lambda u:'/login' not in u)
   page.goto(ORIGIN+'/characters');page.locator('#vttDisplayOpen').click();page.locator('#vttDisplay-theme').select_option('night');page.locator('#vttDisplay-language').select_option(language)
   if language!='de':
    with page.expect_navigation(wait_until='load'):page.locator('.vtt-display-actions button').last.click()
   else:page.locator('.vtt-display-actions button').last.click()
   expect(page.locator('.book-scene-loading')).to_have_count(0);expect(page.locator('.book-spread-page').first).to_be_visible()
   expect(page.locator('.book-spread-page').first).to_have_css('background-color','rgb(43, 34, 29)')
   expect(page.locator('.book-spread-page-title').first).to_have_css('color','rgb(242, 154, 144)')
   assert page.locator('html').evaluate("e=>getComputedStyle(e).getPropertyValue('--ui-accent').trim()")=='#f29a90';contrast(page,'.book-spread-page h1,.book-spread-page h2,.book-spread-page p,.book-dashboard-ribbon-btn')
   page.screenshot(path=str(ROOT/(kind+'-night-book.png')))
   page.locator('.book-dashboard-ribbon [data-dashboard-route="maps"], .book-dashboard-ribbon a[href="/mapmaker"]').first.click();page.wait_for_url(ORIGIN+'/static/mapmaker/index.html');page.evaluate('() => window.rdMapmaker.ready');page.locator('#newEmpty').click()
   contrast(page,'.mm-tool,.mm-tabs [role=tab],.mm-top .mm-btn,.mm-panel label,.mm-group-head h2');page.screenshot(path=str(ROOT/(kind+'-night-editor.png')))
   before=page.evaluate('() => window.rdMapmaker.summary()')
   page.locator('#vttDisplayOpen').click();page.locator('#vttDisplay-theme').select_option('paper');page.locator('.vtt-display-actions button').last.click();assert before==page.evaluate('() => window.rdMapmaker.summary()')
   assert page.evaluate('document.documentElement.scrollWidth')<=width+1
   proof['journeys'].append(f'{kind}/{engine}/{width}: archive → night gear → Maps → editor → paper; map document unchanged')
  except BaseException as error:
   proof.update(status='fail',failure=str(error));(ROOT/'live-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');raise
  finally:context.close();browser.close()
 proof['status']='pass' if not proof['errors'] else 'fail';assert not proof['errors'],proof['errors'];(ROOT/'live-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
