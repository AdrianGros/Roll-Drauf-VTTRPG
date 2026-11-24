"""FV02 view clarity through normal character creation; isolated QA, no final character required."""
import json,os
from pathlib import Path
from playwright.sync_api import expect,sync_playwright

root=Path(os.environ['PROOF_ROOT']);fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de';proof={'status':'running','journeys':[],'real_oauth_tested':False}
expect.set_options(timeout=30000)
def save():(root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')
def snapshot(page):return page.evaluate('() => {const a=SrdCreator.app;return {id:a.draft.id,version:a.draft.version,state:a.draft.state,data:a.data,evaluation:a.evaluation}}')
save()
with sync_playwright() as p:
 for engine,role,width,ui,content,start in [('chromium','dm',1440,'de','en','guided'),('firefox','player',390,'en','de','quick')]:
  browser=getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
  context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
  prefs={'language':ui,'contentLanguage':content,'unit':'ft','theme':'night' if role=='dm' else 'paper'}
  context.add_init_script("if(!localStorage.getItem('vtt.display.v1'))localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps(prefs))+")")
  auth=fixture['users'][role]
  context.add_cookies([{'name':'access_token_cookie','value':auth['token'],'url':origin,'httpOnly':True,'secure':True},{'name':'csrf_access_token','value':auth['csrf'],'url':origin,'secure':True}])
  page=context.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  try:
   page.goto(origin+'/dashboard');group=page.locator('.book-dashboard-ribbon:visible .vtt-nav-play');group.locator('summary').click();group.locator('a[href="/characters"]').click()
   page.get_by_role('button',name='Held anlegen' if ui=='de' else 'Create character',exact=True).click()
   expect(page.locator('#scNewGuided')).to_have_text('Start with guided steps' if content=='en' else 'Mit einzelnen Schritten starten')
   expect(page.locator('#scNewQuick')).to_have_text('Start with the full form' if content=='en' else 'Mit vollständigem Formular starten')
   page.locator('#scNewGuided' if start=='guided' else '#scNewQuick').click()
   expect(page.locator('.sc-section')).to_have_count(1 if start=='guided' else 8)
   page.get_by_role('button',name='Fighter' if content=='en' else 'Kämpfer',exact=False).first.click()
   if start=='guided':page.locator('#scSteps button').nth(1).click()
   page.get_by_role('button',name='Acolyte' if content=='en' else 'Akolyth',exact=False).first.click()
   page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
   before=snapshot(page);assert before['state']['background']['id']=='character-origins.backgrounds.acolyte'
   page.locator('#scModeQuick').click();expect(page.locator('.sc-section')).to_have_count(8)
   expect(page.locator('#scModeQuick')).to_have_attribute('aria-pressed','true');assert snapshot(page)==before
   page.locator('#scModeGuided').click();expect(page.locator('.sc-section')).to_have_count(1)
   expect(page.locator('#scModeGuided')).to_have_attribute('aria-pressed','true');assert snapshot(page)==before
   page.locator('#scModeQuick').click();page.reload();expect(page.locator('.sc-section')).to_have_count(8);assert snapshot(page)==before
   other='de' if content=='en' else 'en';page.locator('#vttDisplayOpen').click();page.locator('#vttDisplay-contentLanguage').select_option(other);page.locator('#vttDisplayApply').click()
   expect(page.locator('#scModeQuick')).to_have_text('Full form' if other=='en' else 'Vollständiges Formular')
   expect(page.locator('#scModeGuided')).to_have_text('Guided steps' if other=='en' else 'Einzelne Schritte')
   expect(page.locator('#scModeHint')).to_contain_text('same draft' if other=='en' else 'denselben Entwurf')
   assert snapshot(page)==before;assert page.evaluate('VTTDisplay.get().unit')=='ft'
   expect(page.locator('html')).to_have_attribute('lang',ui)
   page.evaluate('window.scrollTo(0,0)')
   box=page.locator('.sc-mode').bounding_box();assert box and box['x']>=0 and box['x']+box['width']<=width+1
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
   page.screenshot(path=str(root/f'views-{engine}-{width}-{ui}-{other}.png'));assert not errors,errors
   proof['journeys'].append({'engine':engine,'role':role,'width':width,'ui_language':ui,'initial_rules_language':content,'switched_rules_language':other,'initial_view':start,'normal_characters_navigation':True,'both_start_actions_clear':True,'same_draft_id_version_state_data_evaluation_across_view_switches':True,'selected_background_preserved':True,'quick_view_reload':True,'independent_site_rules_language_and_units':True,'view_controls_fit_and_no_page_overflow':True,'browser_errors':errors});save()
  except Exception as e:
   proof.update(status='failed',error=str(e));page.screenshot(path=str(root/f'failure-{engine}-{width}.png'));save();raise
  finally:context.close();browser.close()
proof['status']='pass';save()
