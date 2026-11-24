"""Authenticated, ordinary creator entry with source names/details and saved spell identity."""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect,sync_playwright

root=Path(os.environ['PROOF_ROOT'])
fixture=json.loads((root/'private-live-credentials.json').read_text())
repo=Path(__file__).resolve().parents[3]
expected=json.loads((repo/'vtt/rules_content/srd-5.2.1-en/generated/creator-display.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','origin':origin,'journeys':[],'real_oauth_tested':False}
expect.set_options(timeout=30000)

def save(): (root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')

def snapshot(page):
    return page.evaluate("() => {const a=SrdCreator.app;return {id:a.draft.id,version:a.draft.version,state:JSON.stringify(a.draft.state),data:JSON.stringify(a.data),evaluation:JSON.stringify(a.evaluation),selected:a.draft.state.spells.wizard.cantrips}}")

with sync_playwright() as p:
    for engine,role,width,ui,content,theme in [
        ('chromium','dm',1440,'de','en','night'),('firefox','player',390,'en','de','paper')]:
        browser=getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        prefs={'language':ui,'contentLanguage':content,'unit':'ft','theme':theme,'accent':'teal'}
        context.add_init_script("if(!localStorage.getItem('vtt.display.v1'))localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps(prefs))+")")
        auth=fixture['users'][role]
        context.add_cookies([{'name':'access_token_cookie','value':auth['token'],'url':origin,'httpOnly':True,'secure':True},
                            {'name':'csrf_access_token','value':auth['csrf'],'url':origin,'secure':True}])
        page=context.new_page();page.set_default_timeout(30000);errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(origin+'/dashboard')
            group=page.locator('.book-dashboard-ribbon:visible .vtt-nav-play')
            group.locator('summary').click();group.locator('a[href="/characters"]').click()
            page.get_by_role('button',name='Held anlegen' if ui=='de' else 'Create character',exact=True).click()
            page.locator('#scNewGuided').click()
            page.get_by_role('button',name='Wizard' if content=='en' else 'Magier',exact=False).first.click()
            page.get_by_role('button',name='Read class text' if content=='en' else 'Klassentext lesen',exact=True).click()
            expect(page.locator('#scDialogTitle')).to_have_text('Wizard' if content=='en' else 'Magier')
            expect(page.locator('#scDialogTitle')).to_have_attribute('lang',content)
            page.locator('#scDialogClose').click()
            page.locator('#scSteps button').nth(5).click()
            boxes=page.locator('[role=group][aria-label=cantrips] input[type=checkbox]')
            boxes.nth(0).check();boxes.nth(2).check()
            page.locator('#scSteps button').nth(6).click();page.locator('#scId-name').fill('Charaktere')
            page.locator('#scSteps button').nth(5).click()
            page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
            before=snapshot(page)
            assert len(before['selected'])==2
            page.locator('#vttDisplayOpen').click();other='de' if content=='en' else 'en'
            page.locator('#vttDisplay-contentLanguage').select_option(other);page.locator('#vttDisplayApply').click()
            page.wait_for_function("() => ['canonical','ready'].includes(SrdCreator.app.localeState)")
            assert snapshot(page)==before
            assert set(page.locator('[role=group][aria-label=cantrips] input:checked').evaluate_all("(ns)=>ns.map(n=>n.closest('[data-canonical-id]').dataset.canonicalId)"))==set(before['selected'])
            sid=before['selected'][0]
            page.locator('[data-canonical-id="'+sid+'"] button').first.click()
            title=expected['names'][sid]['name'] if other=='en' else json.loads(before['data'])['spells'][sid]['name']
            expect(page.locator('#scDialogTitle')).to_have_text(title)
            expect(page.locator('#scDialogTitle')).to_have_attribute('lang',other)
            page.locator('#scDialogClose').click()
            page.reload()
            expect(page.locator('[role=group][aria-label=cantrips] input:checked')).to_have_count(2)
            assert snapshot(page)==before
            assert page.evaluate('VTTDisplay.get().unit')=='ft'
            expect(page.locator('html')).to_have_attribute('lang',ui)
            expect(page.locator('#vttDisplayOpen')).to_have_attribute('aria-label','Einstellungen' if ui=='de' else 'Settings')
            page.screenshot(path=str(root/f'content-{engine}-{width}-{ui}-{other}.png'))
            assert not errors,errors
            proof['journeys'].append({'engine':engine,'role':role,'width':width,'ui_language':ui,'initial_rules_language':content,
                'switched_rules_language':other,'normal_navigation':True,'localized_class_name_and_source':True,
                'localized_spell_source':True,'selected_canonical_spell_ids_preserved':True,
                'draft_id_version_state_data_evaluation_preserved':True,'saved_draft_reload':True,
                'name_and_unit_preference_preserved':True,'state_sha256':hashlib.sha256(before['state'].encode()).hexdigest(),
                'browser_errors':errors});save()
        except Exception as e:
            proof.update(status='failed',error=str(e));page.screenshot(path=str(root/f'failure-{engine}-{width}.png'));save();raise
        finally:context.close();browser.close()
proof['status']='pass';save()
