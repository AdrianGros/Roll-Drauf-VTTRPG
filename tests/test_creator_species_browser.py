"""Scoped species labels preserve canonical selections and literal homebrew content."""
import json
import pytest
from tests.test_srd_creator_browser import site, wiz


def snapshot(page):
    return page.evaluate("() => {const a=SrdCreator.app;return {data:a.data,state:a.draft.state,evaluation:a.evaluation,id:a.draft.id,version:a.draft.version}}")


@pytest.mark.parametrize(('ui','content'),[('de','en'),('en','de')])
def test_species_selection_locale_switch_and_reload_preserve_draft(wiz,ui,content):
    from playwright.sync_api import expect
    page,origin,app,info=wiz
    page.add_init_script("if(!localStorage.getItem('vtt.display.v1'))localStorage.setItem('vtt.display.v1',"+json.dumps(json.dumps({'language':ui,'contentLanguage':content,'unit':'ft'}))+")")
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click()
    page.locator('#scSteps button').nth(1).click()
    page.get_by_role('button',name='Dragonborn' if content=='en' else 'Drachenblütiger',exact=False).first.click()
    control=page.locator('#scSpc-draconic-ancestry');control.select_option('blau')
    expect(control.locator('option:checked')).to_have_text('Blue (Lightning)' if content=='en' else 'Blau (Blitz)')
    expect(control.locator('option:checked')).to_have_attribute('lang',content)
    expect(page.locator('.sc-detail').first).to_contain_text('Humanoid · Size Medium' if content=='en' else 'Humanoide · Größe Mittelgroß')
    expect(page.locator('.sc-detail').first).to_contain_text('Darkvision 18 m' if content=='en' else 'Dunkelsicht 18 m')
    page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
    before=snapshot(page);other='de' if content=='en' else 'en';control.focus()
    page.evaluate('(language)=>VTTDisplay.update({contentLanguage:language})',other)
    page.wait_for_function("() => ['canonical','ready'].includes(SrdCreator.app.localeState)")
    expect(control.locator('option:checked')).to_have_text('Blue (Lightning)' if other=='en' else 'Blau (Blitz)')
    expect(control).to_be_focused();assert snapshot(page)==before
    page.reload();expect(control).to_have_value('blau');assert snapshot(page)==before
    assert page.evaluate('document.documentElement.lang')==ui
    assert page.evaluate('VTTDisplay.get().unit')=='ft'
    page.get_by_role('button',name='Human' if other=='en' else 'Mensch',exact=False).first.click()
    page.locator('#scSpc-size').select_option('Klein')
    expect(page.locator('#scSpc-size option:checked')).to_have_text('Small' if other=='en' else 'Klein')
    assert page.evaluate('SrdCreator.app.draft.state.species.choices.size')=='Klein'


def test_all_species_option_groups_and_traits_and_homebrew_stay_literal(wiz):
    from playwright.sync_api import expect
    page,origin,app,info=wiz;page.set_viewport_size({'width':390,'height':1000})
    page.add_init_script("localStorage.setItem('vtt.display.v1',JSON.stringify({language:'de',contentLanguage:'en'}))")
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click();page.locator('#scSteps button').nth(1).click()
    cases=[
        ('Dragonborn','Breath Weapon','draconic-ancestry',['Blue (Lightning)','Bronze (Lightning)','Gold (Fire)','Green (Poison)','Copper (Acid)','Brass (Fire)','Red (Fire)','Black (Acid)','Silver (Cold)','White (Cold)']),
        ('Elf','Fey Ancestry','lineage',['Drow','High Elf','Wood Elf']),
        ('Gnome','Gnomish Cunning','lineage',['Rock Gnome','Forest Gnome']),
        ('Goliath','Stone’s Endurance (Stone Giant)','giant-ancestry',['Frost Giant','Stone Giant','Fire Giant','Hill Giant','Storm Giant','Cloud Giant']),
        ('Halfling','Luck',None,[]),('Human','Resourceful',None,[]),('Orc','Relentless Endurance',None,[]),
        ('Tiefling','Fiendish Legacy','lineage',['Abyssal','Chthonic','Infernal']),('Dwarf','Stonecunning',None,[]),
    ]
    for name,trait,choice,options in cases:
        page.get_by_role('button',name=name,exact=False).first.click()
        expect(page.locator('.sc-detail').first).to_contain_text(trait)
        if choice:
            assert page.locator('#scSpc-'+choice+' option').all_text_contents()[1:]==options
            if name in ['Elf','Tiefling']:
                page.locator('#scSpc-'+choice).select_option(index=1)
                expect(page.locator('.sc-detail').first).to_contain_text('This rule text is currently available only in German.')
                expect(page.locator('.sc-detail .sc-muted span[lang="de"]')).to_be_visible()
    # A test-owned homebrew record deliberately reuses canonical IDs/text: every authored field stays literal.
    assert page.evaluate("""() => {
        const SC=SrdCreator,s={...SC.L.species['character-origins.species.elf'],homebrew:true};
        return SC.ruleName(s)===s.name && SC.speciesTraitName(s,'Dunkelsicht')==='Dunkelsicht' &&
            SC.speciesOptionName(s,{id:'lineage'},{id:'hochelf',name:'Charaktere'})==='Charaktere' &&
            SC.speciesSizeName(s,'Klein')==='Klein' && SC.speciesCreatureTypeName(s)==='Humanoide' &&
            SC.speciesDamageTypeName(s,'Gift')==='Gift' && SC.speciesLabelsLocale(s)===undefined;
    }""")
