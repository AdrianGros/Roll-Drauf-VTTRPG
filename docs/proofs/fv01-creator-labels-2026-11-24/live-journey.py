"""Normal navigation acceptance for isolated QA accounts; no credentials in evidence."""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root=Path(os.environ['PROOF_ROOT'])
fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','origin':origin,'journeys':[],'real_oauth_tested':False}
expect.set_options(timeout=30000)

def save():
    (root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')

with sync_playwright() as p:
    for engine,role,width,ui,content,theme in [
        ('chromium','dm',1440,'de','en','night'),
        ('firefox','player',390,'en','de','paper'),
    ]:
        browser=getattr(p,engine).launch(headless=True,**({'args':['--no-sandbox']} if engine=='chromium' else {}))
        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        prefs={'language':ui,'contentLanguage':content,'unit':'ft','theme':theme,'accent':'teal'}
        # Initial preferences only; subsequent changes and reload use the actual settings UI/storage.
        context.add_init_script("if(!localStorage.getItem('vtt.display.v1'))localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps(prefs))+")")
        auth=fixture['users'][role]
        context.add_cookies([
            {'name':'access_token_cookie','value':auth['token'],'url':origin,'httpOnly':True,'secure':True},
            {'name':'csrf_access_token','value':auth['csrf'],'url':origin,'secure':True},
        ])
        page=context.new_page();page.set_default_timeout(30000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        try:
            page.goto(origin+'/dashboard')
            group=page.locator('.book-dashboard-ribbon:visible .vtt-nav-play')
            group.locator('summary').click()
            group.locator('a[href="/characters"]').click()
            page.get_by_role('button',name='Held anlegen' if ui=='de' else 'Create character',exact=True).click()
            expect(page.locator('#scNewGuided')).to_have_text('Guided, step by step' if content=='en' else 'Geführt, Schritt für Schritt')
            expect(page.locator('h1')).to_have_text('Create character' if content=='en' else 'Charakter erstellen')
            expect(page.locator('html')).to_have_attribute('lang',ui)
            page.locator('#scNewGuided').click()
            page.get_by_role('button',name='Kämpfer',exact=False).first.click()
            page.locator('#scSteps button').nth(6).click()
            page.locator('#scId-name').fill('Charaktere')
            expect(page.locator('#scSave')).to_have_text('Saved' if content=='en' else 'Gespeichert')
            before=page.evaluate("() => {const a=SrdCreator.app;return {id:a.draft.id,version:a.draft.version,state:JSON.stringify(a.draft.state),data:JSON.stringify(a.data),evaluation:JSON.stringify(a.evaluation)}}")
            # Settings belong to the site UI; changing only rules language does not reload or save the draft.
            page.locator('#vttDisplayOpen').click()
            other='de' if content=='en' else 'en'
            page.locator('#vttDisplay-contentLanguage').select_option(other)
            page.locator('#vttDisplayApply').click()
            expect(page.locator('#scH-beschreibung')).to_have_text('Description' if other=='en' else 'Beschreibung')
            expect(page.locator('#scId-name')).to_have_value('Charaktere')
            after=page.evaluate("() => {const a=SrdCreator.app;return {id:a.draft.id,version:a.draft.version,state:JSON.stringify(a.draft.state),data:JSON.stringify(a.data),evaluation:JSON.stringify(a.evaluation)}}")
            assert after==before,'Language switch changed draft or evaluation'
            page.reload()
            expect(page.locator('#scId-name')).to_have_value('Charaktere')
            reloaded=page.evaluate("() => {const a=SrdCreator.app;return {id:a.draft.id,version:a.draft.version,state:JSON.stringify(a.draft.state),data:JSON.stringify(a.data),evaluation:JSON.stringify(a.evaluation)}}")
            assert reloaded==before,'Reopening changed canonical state'
            assert page.evaluate('VTTDisplay.get().unit')=='ft'
            expect(page.locator('#scMain')).to_have_attribute('lang',other)
            # Confirm the site's settings button remains in the site language after content changes.
            expect(page.locator('#vttDisplayOpen')).to_have_attribute('aria-label','Einstellungen' if ui=='de' else 'Settings')
            page.screenshot(path=str(root/f'creator-{engine}-{width}-{ui}-{other}.png'))
            assert not errors,errors
            proof['journeys'].append({'engine':engine,'role':role,'width':width,'ui_language':ui,
                'initial_rules_language':content,'switched_rules_language':other,'theme':theme,
                'normal_dashboard_characters_creator_navigation':True,'real_settings_change':True,
                'draft_id_version_state_and_evaluation_preserved':True,'reload_existing_draft':True,
                'user_name_unchanged':True,'unit_preference_independent':True,
                'state_sha256':hashlib.sha256(before['state'].encode()).hexdigest(),'browser_errors':errors})
            save()
        except Exception as e:
            proof.update(status='failed',error=str(e));page.screenshot(path=str(root/f'failure-{engine}-{width}.png'));save();raise
        finally:
            context.close();browser.close()
proof['status']='pass';save()
