"""Ordinary DM/Player creator navigation, equipment identity and rules-language acceptance."""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import expect,sync_playwright

root=Path(os.environ['PROOF_ROOT'])
fixture=json.loads((root/'private-live-credentials.json').read_text())
origin='https://vtt.roll-drauf.de'
proof={'status':'running','origin':origin,'journeys':[],'real_oauth_tested':False}
expect.set_options(timeout=30000)
mastery='equipment.coins-and-weapons.weapons-martial-ranged.schwere-armbrust'
armor='equipment.armor.armor-heavy.kettenpanzer'

def save(): (root/'live.json').write_text(json.dumps(proof,indent=2)+'\n')

def snapshot(page):
    return page.evaluate("() => {const a=SrdCreator.app;return {id:a.draft.id,version:a.draft.version,state:a.draft.state,data:a.data,evaluation:a.evaluation}}")

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
            page.get_by_role('button',name='Fighter' if content=='en' else 'Kämpfer',exact=False).first.click()
            page.get_by_role('button',name='Read class text' if content=='en' else 'Klassentext lesen',exact=True).click()
            expect(page.locator('#scDialogTitle')).to_have_text('Fighter' if content=='en' else 'Kämpfer')
            expect(page.locator('#scDialogTitle')).to_have_attribute('lang',content)
            page.locator('#scDialogClose').click()
            page.locator('#scSteps button').nth(1).click()
            page.get_by_role('button',name='Acolyte' if content=='en' else 'Akolyth',exact=False).first.click()
            expect(page.locator('#scStepBody')).to_contain_text('Calligrapher’s Supplies' if content=='en' else 'Kalligrafiewerkzeug')
            page.locator('#scSteps button').nth(3).click()
            box=page.locator('input[data-focus-key="'+mastery+'"]')
            expect(box.locator('xpath=../..')).to_contain_text('Heavy Crossbow' if content=='en' else 'Schwere Armbrust')
            expect(box.locator('xpath=../..')).to_contain_text('Push' if content=='en' else 'Stoßen')
            box.check()
            page.locator('#scSteps button').nth(4).click()
            page.get_by_role('button',name='Package A' if content=='en' else 'Paket A',exact=False).first.click()
            page.locator('#scArmor').select_option(armor)
            expect(page.locator('#scArmor option:checked')).to_contain_text('Chain Mail (AC 16)' if content=='en' else 'Kettenpanzer (RK 16)')
            expect(page.locator('#scStepBody')).to_contain_text('4 GP' if content=='en' else '4 GM')
            expect(page.locator('#scStepBody')).to_contain_text('Background: Acolyte' if content=='en' else 'Hintergrund: Akolyth')
            page.locator('#scSteps button').nth(6).click();page.locator('#scId-name').fill('Charaktere')
            page.locator('#scSteps button').nth(4).click()
            page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
            before=snapshot(page)
            state=before['state']
            assert state['equipment']['armor']==armor
            assert state['featureChoices']['fighter']['weapon-mastery']==[mastery]
            page.locator('#vttDisplayOpen').click();other='de' if content=='en' else 'en'
            page.locator('#vttDisplay-contentLanguage').select_option(other);page.locator('#vttDisplayApply').click()
            page.wait_for_function("() => ['canonical','ready'].includes(SrdCreator.app.localeState)")
            expect(page.locator('#scArmor option:checked')).to_contain_text('Chain Mail (AC 16)' if other=='en' else 'Kettenpanzer (RK 16)')
            expect(page.locator('#scStepBody')).to_contain_text('4 GP' if other=='en' else '4 GM')
            assert snapshot(page)==before
            page.locator('#scSteps button').nth(3).click()
            expect(page.locator('input[data-focus-key="'+mastery+'"]').first).to_be_checked()
            page.locator('#scSteps button').nth(4).click()
            page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
            after_navigation=snapshot(page)
            assert {k:v for k,v in after_navigation.items() if k!='version'}=={k:v for k,v in before.items() if k!='version'}
            page.reload()
            expect(page.locator('#scArmor')).to_have_value(armor)
            assert snapshot(page)==after_navigation
            assert page.evaluate('VTTDisplay.get().unit')=='ft'
            expect(page.locator('html')).to_have_attribute('lang',ui)
            expect(page.locator('#vttDisplayOpen')).to_have_attribute('aria-label','Einstellungen' if ui=='de' else 'Settings')
            page.screenshot(path=str(root/f'equipment-{engine}-{width}-{ui}-{other}.png'))
            assert not errors,errors
            proof['journeys'].append({'engine':engine,'role':role,'width':width,'ui_language':ui,'initial_rules_language':content,
                'switched_rules_language':other,'normal_navigation':True,'localized_class_name_and_source':True,
                'localized_tool_mastery_armor_pack_coin_labels':True,'canonical_armor_mastery_ids_preserved':True,
                'draft_id_version_state_data_evaluation_preserved':True,'saved_draft_reload':True,'step_navigation_version_advance':after_navigation['version']-before['version'],
                'name_and_unit_preference_preserved':True,'state_sha256':hashlib.sha256(json.dumps(before['state'],sort_keys=True).encode()).hexdigest(),
                'browser_errors':errors});save()
        except Exception as e:
            proof.update(status='failed',error=str(e));page.screenshot(path=str(root/f'failure-{engine}-{width}.png'));save();raise
        finally:context.close();browser.close()
proof['status']='pass';save()
