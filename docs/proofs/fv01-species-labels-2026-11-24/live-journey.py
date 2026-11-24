"""Ordinary DM/Player creator navigation, species labels and rules-language acceptance."""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect,sync_playwright

root=Path(os.environ['PROOF_ROOT'])
fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de'
proof=json.loads((root/'live.json').read_text()) if os.environ.get('LIVE_RESUME') else {'origin':origin,'journeys':[],'real_oauth_tested':False}
proof['status']='running';proof.pop('error',None)
expect.set_options(timeout=30000)

def save(): (root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')

def snapshot(page):
    return page.evaluate("() => {const a=SrdCreator.app;return {id:a.draft.id,version:a.draft.version,state:a.draft.state,data:a.data,evaluation:a.evaluation}}")

with sync_playwright() as p:
    for engine,role,width,ui,content,theme in [
        ('chromium','dm',1440,'de','en','night'),('firefox','player',390,'en','de','paper')]:
        if os.environ.get('LIVE_ROLE') and role!=os.environ['LIVE_ROLE']:continue
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
            page.get_by_role('button',name='Fighter' if content=='en' else 'Kämpfer',exact=False).first.click()
            page.get_by_role('button',name='Read class text' if content=='en' else 'Klassentext lesen',exact=True).click()
            expect(page.locator('#scDialogTitle')).to_have_text('Fighter' if content=='en' else 'Kämpfer')
            expect(page.locator('#scDialogTitle')).to_have_attribute('lang',content)
            page.locator('#scDialogClose').click()
            page.locator('#scSteps button').nth(1).click()
            def species(name):
                page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
                button=page.get_by_role('button',name=name,exact=False).first
                button.click();expect(button).to_have_attribute('aria-pressed','true')
                page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
            species('Elf')
            page.locator('#scSpc-lineage').select_option('hochelf')
            expect(page.locator('#scSpc-lineage option:checked')).to_have_text('High Elf' if content=='en' else 'Hochelf')
            if content=='en':
                expect(page.locator('.sc-detail').first).to_contain_text('This rule text is currently available only in German.')
                expect(page.locator('.sc-detail .sc-muted span[lang="de"]')).to_be_visible()
            species('Human' if content=='en' else 'Mensch')
            page.locator('#scSpc-size').select_option('Klein')
            expect(page.locator('#scSpc-size option:checked')).to_have_text('Small' if content=='en' else 'Klein')
            assert page.evaluate('SrdCreator.app.draft.state.species.choices.size')=='Klein'
            species('Goliath')
            page.locator('#scSpc-giant-ancestry').select_option('stone')
            expect(page.locator('#scSpc-giant-ancestry option:checked')).to_have_text('Stone Giant' if content=='en' else 'Steinriese')
            expect(page.locator('.sc-detail').first).to_contain_text('Stone’s Endurance (Stone Giant)' if content=='en' else 'Felsenfestigkeit (Steinriese)')
            species('Dragonborn' if content=='en' else 'Drachenblütiger')
            page.locator('#scSpc-draconic-ancestry').select_option('blau')
            expect(page.locator('#scSpc-draconic-ancestry option:checked')).to_have_text('Blue (Lightning)' if content=='en' else 'Blau (Blitz)')
            expect(page.locator('.sc-detail').first).to_contain_text('Darkvision 18 m' if content=='en' else 'Dunkelsicht 18 m')
            page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
            page.get_by_role('button',name='Read species text' if content=='en' else 'Spezies-Text lesen',exact=True).click()
            expect(page.locator('#scDialog')).to_be_visible()
            expect(page.locator('#scDialogTitle')).to_have_text('Dragonborn' if content=='en' else 'Drachenblütiger')
            expect(page.locator('#scDialogTitle')).to_have_attribute('lang',content)
            page.locator('#scDialogClose').click()
            page.locator('#scSteps button').nth(6).click();page.locator('#scId-name').fill('Charaktere')
            page.locator('#scSteps button').nth(1).click()
            page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
            before=snapshot(page)
            state=before['state']
            assert state['species']=={'id':'character-origins.species.dragonborn','choices':{'draconic-ancestry':'blau'}}
            page.locator('#vttDisplayOpen').click();other='de' if content=='en' else 'en'
            page.locator('#vttDisplay-contentLanguage').select_option(other);page.locator('#vttDisplayApply').click()
            page.wait_for_function("() => ['canonical','ready'].includes(SrdCreator.app.localeState)")
            expect(page.locator('#scSpc-draconic-ancestry option:checked')).to_have_text('Blue (Lightning)' if other=='en' else 'Blau (Blitz)')
            assert snapshot(page)==before
            page.reload()
            expect(page.locator('#scSpc-draconic-ancestry')).to_have_value('blau')
            assert snapshot(page)==before
            assert page.evaluate('VTTDisplay.get().unit')=='ft'
            expect(page.locator('html')).to_have_attribute('lang',ui)
            expect(page.locator('#vttDisplayOpen')).to_have_attribute('aria-label','Einstellungen' if ui=='de' else 'Settings')
            page.screenshot(path=str(root/f'species-{engine}-{width}-{ui}-{other}.png'))
            assert not errors,errors
            proof['journeys'].append({'engine':engine,'role':role,'width':width,'ui_language':ui,'initial_rules_language':content,
                'switched_rules_language':other,'normal_navigation':True,'localized_class_name_and_source':True,
                'localized_species_traits_ancestry_size_damage_labels':True,'canonical_species_ancestry_size_values_preserved':True,
                'draft_id_version_state_data_evaluation_preserved':True,'saved_draft_reload':True,'german_option_description_truthfully_marked':True,
                'name_and_unit_preference_preserved':True,'state_sha256':hashlib.sha256(json.dumps(before['state'],sort_keys=True).encode()).hexdigest(),
                'browser_errors':errors});save()
        except Exception as e:
            proof.update(status='failed',error=str(e));page.screenshot(path=str(root/f'failure-{engine}-{width}.png'));save();raise
        finally:context.close();browser.close()
proof['status']='pass';save()
