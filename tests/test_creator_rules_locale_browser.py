"""FV01 first delivery: module-authored labels follow rules locale without mutating data."""
import json

import pytest

from tests.test_srd_creator_browser import site, wiz


@pytest.mark.parametrize(('ui', 'content', 'resolved'), [
    ('de','de','de'), ('de','en','en'), ('en','de','de'),
    ('en','en','en'), ('de','auto','de'), ('en','auto','en'),
])
def test_creator_authored_labels_use_rules_locale(wiz, ui, content, resolved):
    from playwright.sync_api import expect
    page, origin, app, info = wiz
    page.add_init_script("localStorage.setItem('vtt.display.v1'," + json.dumps(json.dumps({
        'language':ui,'contentLanguage':content,'unit':'ft'})) + ")")
    page.goto(origin+'/srd-creator')
    expect(page.locator('#scNewGuided')).to_have_text('Start with guided steps' if resolved=='en' else 'Mit einzelnen Schritten starten')
    expect(page.locator('h1')).to_have_text('Create character' if resolved=='en' else 'Charakter erstellen')
    expect(page.locator('html')).to_have_attribute('lang',ui)
    expect(page.locator('#scMain')).to_have_attribute('lang',resolved)
    if resolved=='en':
        expect(page.locator('#scLanguageNotice')).to_be_visible()
    else:
        expect(page.locator('#scLanguageNotice')).to_be_hidden()
    # Unscoped authored markers still use site locale, even when inserted after load.
    page.evaluate("""() => {
        const key=Object.keys(VTTUiMessages).find(k=>VTTUiMessages[k].source==='Charaktere');
        const n=document.createElement('span');n.id='siteLocaleProbe';n.dataset.uiKey=key;document.body.append(n);
        const inside=n.cloneNode();inside.id='rulesLocaleProbe';document.querySelector('#scMain').append(inside);
        const user=document.createElement('span');user.id='userTextProbe';user.textContent='Charaktere';document.querySelector('#scMain').append(user);
    }""")
    expect(page.locator('#siteLocaleProbe')).to_have_text('Characters' if ui=='en' else 'Charaktere')
    expect(page.locator('#rulesLocaleProbe')).to_have_text('Characters' if resolved=='en' else 'Charaktere')
    expect(page.locator('#userTextProbe')).to_have_text('Charaktere')
    page.locator('#scNewGuided').click()
    expect(page.locator('#scH-klasse')).to_have_text('Class' if resolved=='en' else 'Klasse')
    expect(page.locator('#scNext')).to_have_text('Next' if resolved=='en' else 'Weiter')
    assert page.evaluate('VTTDisplay.get().unit')=='ft'


def test_live_locale_switch_preserves_home_file_and_dirty_draft(wiz):
    from playwright.sync_api import expect
    page, origin, app, info = wiz
    page.goto(origin+'/srd-creator')
    page.locator('#scNewGuided').wait_for()
    page.locator('#scImportFile').set_input_files({'name':'user.json','mimeType':'application/json','buffer':b'{"name":"Charaktere"}'})
    page.locator('#scImportGo').focus()
    page.evaluate("VTTDisplay.update({contentLanguage:'en'})")
    expect(page.locator('#scNewGuided')).to_have_text('Start with guided steps')
    assert page.locator('#scImportFile').evaluate('(n)=>n.files[0].name')=='user.json'
    expect(page.locator('#scImportGo')).to_be_focused()
    page.locator('#scNewGuided').click()
    page.wait_for_function("() => SrdCreator.app.draft && !SrdCreator.app.saving")
    # Pause autosave to observe dirty state, with user text deliberately matching a catalog source.
    page.evaluate("""() => {
        const SC=SrdCreator;
        SC.app.draft.state.identity={name:'Charaktere',description:'Weiter'};
        SC.app.dirty=true;clearTimeout(SC.app.saveTimer);
        SC.app.step='beschreibung';SC.renderAll();
        window.beforeLocale={state:JSON.stringify(SC.app.draft.state),data:JSON.stringify(SC.app.data),
            id:SC.app.draft.id,version:SC.app.draft.version,dirty:SC.app.dirty};
    }""")
    page.locator('#scId-name').focus()
    page.locator('#scId-name').evaluate('(n)=>n.setSelectionRange(2,5)')
    page.evaluate("VTTDisplay.update({contentLanguage:'de'})")
    expect(page.locator('#scH-beschreibung')).to_have_text('Beschreibung')
    expect(page.locator('#scId-name')).to_be_focused()
    expect(page.locator('#scId-name')).to_have_value('Charaktere')
    assert page.locator('#scId-name').evaluate('(n)=>[n.selectionStart,n.selectionEnd]')==[2,5]
    assert page.evaluate("""() => {
        const a=SrdCreator.app,b=beforeLocale;
        return JSON.stringify(a.draft.state)===b.state && JSON.stringify(a.data)===b.data &&
            a.draft.id===b.id && a.draft.version===b.version && a.dirty===b.dirty && !a.saving;
    }""")
    page.evaluate("VTTDisplay.update({contentLanguage:'en'})")
    expect(page.locator('#scH-beschreibung')).to_have_text('Description')
    expect(page.locator('#scModeQuick')).to_have_text('Full form')
    # Global translation can be called repeatedly without overriding module markers.
    page.evaluate('VTTI18n.translate()')
    expect(page.locator('#scModeGuided')).to_have_text('Guided steps')
    page.evaluate('SrdCreator.app.dirty=false')


def test_rules_locale_switch_preserves_uncommitted_input(wiz):
    from playwright.sync_api import expect
    page, origin, app, info = wiz
    page.goto(origin+'/srd-creator')
    page.locator('#scNewGuided').click()
    page.get_by_role('button',name='Kämpfer',exact=False).first.click()
    expect(page.locator('#scSave')).to_have_text('Gespeichert')
    expect(page.locator('#scLevel')).to_have_value('1')
    page.locator('#scLevel').fill('7')
    # onchange has not fired: preserve this pending number without changing canonical state.
    before=page.evaluate('JSON.stringify(SrdCreator.app.draft.state)')
    page.evaluate("VTTDisplay.update({contentLanguage:'en'})")
    expect(page.locator('#scLevel')).to_have_value('7')
    expect(page.locator('#scLevel')).to_be_focused()
    assert page.evaluate('JSON.stringify(SrdCreator.app.draft.state)')==before
    page.locator('#scLevel').press('Tab')
    page.wait_for_function('() => SrdCreator.app.draft.state.levels.length===7')


def test_rules_locale_switch_preserves_final_campaign_and_pending_result(wiz):
    from playwright.sync_api import expect
    page, origin, app, info = wiz
    page.goto(origin+'/srd-creator')
    page.locator('#scNewRandom').click()
    expect(page.locator('#scBuilder')).to_be_visible()
    expect(page.locator('#scSave')).to_have_text('Gespeichert')
    page.evaluate("SrdCreator.app.campaigns=[{id:991,name:'Charaktere'}];SrdCreator.goStep('pruefung')")
    expect(page.locator('#scFinalCampaign option')).to_have_count(2)
    page.wait_for_function('() => !SrdCreator.app.dirty && !SrdCreator.app.saving')
    page.locator('#scFinalCampaign').select_option('991')
    page.evaluate("VTTDisplay.update({contentLanguage:'en'})")
    expect(page.locator('#scFinalCampaign')).to_have_value('991')
    expect(page.locator('#scFinalCampaign option:checked')).to_have_text('Charaktere')
    expect(page.locator('#scFinalize-btn')).to_have_text('Create character')
    # Hold a simulated server response to exercise the connected asynchronous result node.
    page.evaluate("""() => {SrdCreator.finalize=()=>{
        SrdCreator.app.finalizing=true;
        return new Promise(resolve=>window.finishFinalize=()=>{
            SrdCreator.app.finalizing=false;resolve({ok:false,data:{message:'Server message retained'}});
        });
    }}""")
    page.locator('#scFinalize-btn').click()
    expect(page.locator('#scFinalize-btn')).to_be_disabled()
    page.evaluate("VTTDisplay.update({contentLanguage:'de'})")
    expect(page.locator('#scFinalize-btn')).to_be_disabled()
    expect(page.locator('#scFinalResult')).to_have_text('Wird erstellt …')
    expect(page.locator('#scFinalCampaign')).to_have_value('991')
    page.evaluate('finishFinalize()')
    expect(page.locator('#scFinalResult')).to_have_text('Server message retained')
    page.evaluate("VTTDisplay.update({contentLanguage:'en'})")
    expect(page.locator('#scFinalResult')).to_have_text('Server message retained')
    expect(page.locator('#scFinalize-btn')).to_be_enabled()
