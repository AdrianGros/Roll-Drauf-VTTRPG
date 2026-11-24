"""Real-browser contracts for source-backed names, source dialogs and async locale changes."""
import json

import pytest

from tests.test_srd_creator_browser import site, wiz


def prefs(page,ui='de',content='en'):
    page.add_init_script("localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps({'language':ui,'contentLanguage':content}))+ ")")


def wait_for_held(page,held):
    # Wait for the intercepted real response instead of assuming a network timing.
    for _ in range(100):
        if held:return
        page.wait_for_timeout(50)
    raise AssertionError('Expected the intercepted source request')


@pytest.mark.parametrize(('ui','content','resolved'),[
    ('de','de','de'),('de','en','en'),('en','de','de'),('en','en','en'),('de','auto','de'),('en','auto','en'),
])
def test_creator_source_names_and_details_matrix(wiz,ui,content,resolved):
    from playwright.sync_api import expect
    page,origin,app,info=wiz;prefs(page,ui,content)
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    label='Fighter' if resolved=='en' else 'Kämpfer'
    page.get_by_role('button',name=label,exact=False).first.click()
    expect(page.locator('.sc-detail h3',has_text=label).first).to_be_visible()
    # The source rule entry is reachable through the ordinary class-details control.
    page.get_by_role('button',name='Read class text' if resolved=='en' else 'Klassentext lesen',exact=True).click()
    expect(page.locator('#scDialogTitle')).to_have_text(label)
    expect(page.locator('#scDialogTitle')).to_have_attribute('lang',resolved)
    expect(page.locator('#scDialogBody [lang="'+resolved+'"]').first).to_be_visible()
    assert page.evaluate('document.documentElement.lang')==ui
    assert page.evaluate("SrdCreator.app.data.classes.find(c=>c.classKey==='fighter').name")=='Kämpfer'
    page.locator('#scDialogClose').click()


def test_spell_sort_switch_keeps_checked_ids_data_and_draft(wiz):
    from playwright.sync_api import expect
    page,origin,app,info=wiz
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    page.get_by_role('button',name='Magier',exact=False).first.click()
    page.locator('#scSteps button').nth(5).click()
    boxes=page.locator('[role=group][aria-label=cantrips] input[type=checkbox]')
    boxes.nth(0).check();boxes.nth(2).check()
    page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
    before=page.evaluate("() => {const a=SrdCreator.app;return {state:JSON.stringify(a.draft.state),data:JSON.stringify(a.data),ev:JSON.stringify(a.evaluation),version:a.draft.version,id:a.draft.id,selected:a.draft.state.spells.wizard.cantrips}}")
    focused=page.locator('[role=group][aria-label=cantrips] input:checked').first
    key=focused.get_attribute('data-focus-key');focused.focus()
    page.evaluate("VTTDisplay.update({contentLanguage:'en'})")
    page.wait_for_function("() => SrdCreator.app.localeState==='ready'")
    after=page.evaluate("() => {const a=SrdCreator.app;return {state:JSON.stringify(a.draft.state),data:JSON.stringify(a.data),ev:JSON.stringify(a.evaluation),version:a.draft.version,id:a.draft.id,selected:a.draft.state.spells.wizard.cantrips}}")
    assert after==before
    assert set(page.locator('[role=group][aria-label=cantrips] input:checked').evaluate_all("(ns)=>ns.map(n=>n.closest('[data-canonical-id]').dataset.canonicalId)"))==set(before['selected'])
    expect(page.locator('[role=group][aria-label=cantrips] input[data-focus-key="'+key+'"]').first).to_be_focused()
    page.locator('#scSpellSearch').fill('Mending')
    expect(page.locator('[data-canonical-id="spells.a-b.ausbessern"]')).to_be_visible()
    assert page.evaluate("SrdCreator.skillName('mit-tieren-umgehen')")=='Animal Handling'
    assert page.evaluate("SrdCreator.abilityName('wis')")=='Wisdom'
    assert page.evaluate("SrdCreator.ruleName('classes.warlock.invocation-improved-pact-weapon')")=='Devouring Blade'


def test_overlay_hash_failure_leaves_canonical_creator_usable(wiz):
    from playwright.sync_api import expect
    page,origin,app,info=wiz;prefs(page)
    page.route('**/creator-display?*',lambda route:route.fulfill(json={'schemaVersion':1,'locale':'en','canonicalHash':'0'*64,'names':{},'terms':{}}))
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    expect(page.locator('#scLocaleStatus')).to_contain_text('draft remains editable')
    card=page.get_by_role('button',name='Kämpfer',exact=False).first
    expect(card.locator('bdi')).to_have_attribute('lang','de')
    card.click();page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
    assert page.evaluate("SrdCreator.app.draft.state.levels[0].classKey")=='fighter'


def test_old_overlay_response_cannot_override_new_locale(wiz):
    from playwright.sync_api import expect
    page,origin,app,info=wiz
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    held=[]
    def hold(route):held.append((route,route.fetch()))
    page.route('**/creator-display?*',hold)
    page.evaluate("() => {const original=SrdCreator.loadLocale;SrdCreator.loadLocale=(...args)=>window.lastLocaleLoad=original(...args);VTTDisplay.update({contentLanguage:'en'});window.oldLocaleLoad=window.lastLocaleLoad;}")
    wait_for_held(page,held)
    page.evaluate("VTTDisplay.update({contentLanguage:'de'})")
    route,response=held[0];route.fulfill(response=response)
    assert page.evaluate('oldLocaleLoad') is False
    expect(page.locator('#scH-klasse')).to_have_text('Klasse')
    assert page.evaluate("SrdCreator.app.localeState==='canonical' && SrdCreator.app.display===null")


def test_rule_dialog_request_order_fallback_and_source_difference(wiz):
    from playwright.sync_api import expect
    page,origin,app,info=wiz;prefs(page)
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    held=[]
    def hold(route):held.append((route,route.fetch()))
    page.route('**/srd-5.2.1-en/compendium/entry/*mislead',hold)
    page.evaluate("() => {window.oldEntryLoad=SrdCreator.openEntry('spells.a-b.ablenkung');}")
    wait_for_held(page,held)
    page.evaluate("SrdCreator.openEntry('spells.h-l.hypnotisches-muster')")
    expect(page.locator('#scDialogTitle')).to_have_text('Hypnotic Pattern')
    expect(page.locator('.sc-source-difference')).to_contain_text('German rules source')
    route,response=held[0];route.fulfill(response=response)
    page.evaluate('oldEntryLoad')
    expect(page.locator('#scDialogTitle')).to_have_text('Hypnotic Pattern')
    page.route('**/srd-5.2.1-en/compendium/entry/*mislead',lambda route:route.fulfill(status=503,json={}))
    page.evaluate("SrdCreator.openEntry('spells.a-b.ablenkung')")
    expect(page.locator('#scDialogTitle')).to_have_text('Ablenkung')
    expect(page.locator('#scDialogTitle')).to_have_attribute('lang','de')
    expect(page.locator('#scDialogBody')).to_contain_text('only in German')


@pytest.mark.parametrize('fallback',[False,True])
def test_english_subclass_preview_uses_english_features_or_explicit_fallback(wiz,fallback):
    from playwright.sync_api import expect
    page,origin,app,info=wiz;prefs(page)
    if fallback:
        page.route('**/srd-5.2.1-en/compendium/entry/*wizard-subclass-evoker*',lambda route:route.fulfill(status=503,json={}))
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    page.get_by_role('button',name='Wizard',exact=False).first.click()
    page.locator('#scLevel').fill('3');page.locator('#scLevel').press('Tab')
    page.wait_for_function('() => SrdCreator.app.draft.state.levels.length===3 && !SrdCreator.app.dirty && !SrdCreator.app.saving')
    page.locator('#scSteps button').nth(3).click()
    page.get_by_role('button',name='Evoker',exact=True).click()
    preview=page.locator('.srd-rule-preview')
    expect(preview).to_contain_text('Hervorrufer' if fallback else 'Evocation Savant')
    expect(preview.locator('[lang="'+('de' if fallback else 'en')+'"]').first).to_be_visible()
    if fallback:expect(preview).to_contain_text('only in German')
    assert page.evaluate("SrdCreator.app.draft.state.subclasses.wizard")=='classes.wizard.subclass-evoker'
