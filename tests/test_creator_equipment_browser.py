"""Equipment presentation must preserve owned items, selected armor and mastery IDs."""
import json

import pytest
from tests.test_srd_creator_browser import site, wiz


@pytest.mark.parametrize(('ui','content'),[('de','en'),('en','de')])
def test_equipment_and_mastery_locale_switch_preserves_canonical_draft(wiz,ui,content):
    from playwright.sync_api import expect
    page,origin,app,info=wiz
    page.add_init_script("if(!localStorage.getItem('vtt.display.v1'))localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps({'language':ui,'contentLanguage':content,'unit':'ft'}))+")")
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    page.get_by_role('button',name='Fighter' if content=='en' else 'Kämpfer',exact=False).first.click()
    page.locator('#scSteps button').nth(3).click()
    mastery='equipment.coins-and-weapons.weapons-martial-ranged.schwere-armbrust'
    box=page.locator('input[data-focus-key="'+mastery+'"]')
    expect(box.locator('xpath=../..')).to_contain_text('Heavy Crossbow' if content=='en' else 'Schwere Armbrust')
    expect(box.locator('xpath=../..')).to_contain_text('Push' if content=='en' else 'Stoßen')
    box.check()
    page.locator('#scSteps button').nth(4).click()
    page.get_by_role('button',name='Package A' if content=='en' else 'Paket A',exact=False).first.click()
    armor='equipment.armor.armor-heavy.kettenpanzer'
    page.locator('#scArmor').select_option(armor)
    expect(page.locator('#scArmor option:checked')).to_contain_text('Chain Mail (AC 16)' if content=='en' else 'Kettenpanzer (RK 16)')
    expect(page.locator('#scStepBody')).to_contain_text('4 GP' if content=='en' else '4 GM')
    page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
    def snapshot():return page.evaluate("() => {const a=SrdCreator.app;return {state:a.draft.state,data:a.data,evaluation:a.evaluation,id:a.draft.id,version:a.draft.version}}")
    before=snapshot();state=before['state']
    assert state['equipment']['armor']==armor
    assert state['featureChoices']['fighter']['weapon-mastery']==[mastery]
    page.locator('#scArmor').focus()
    other='de' if content=='en' else 'en'
    page.evaluate('(language)=>VTTDisplay.update({contentLanguage:language})',other)
    page.wait_for_function("() => ['canonical','ready'].includes(SrdCreator.app.localeState)")
    expect(page.locator('#scArmor option:checked')).to_contain_text('Chain Mail (AC 16)' if other=='en' else 'Kettenpanzer (RK 16)')
    expect(page.locator('#scArmor')).to_be_focused()
    assert snapshot()==before
    assert page.evaluate('document.documentElement.lang')==ui
    assert page.evaluate('VTTDisplay.get().unit')=='ft'
    if other=='en':
        assert page.evaluate("['EM','GM','KM','PM','SM'].map(SrdCreator.coinAbbr)")==['EP','GP','CP','PP','SP']
        assert page.evaluate("SrdCreator.weaponPropertyName('Geschosse')")=='Ammunition'
    page.reload()
    expect(page.locator('#scArmor')).to_have_value(armor)
    assert snapshot()==before
    page.locator('#scSteps button').nth(3).click()
    expect(page.locator('input[data-focus-key="'+mastery+'"]').first).to_be_checked()
