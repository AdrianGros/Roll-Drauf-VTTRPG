"""Individual duplicate rolls, persistent picks, inline subclass rules and spell order."""
from tests.test_srd_creator_browser import site,wiz,_saved  # noqa:F401
from tests.test_srd_creator_api import data,wizard_state  # noqa:F401


def test_duplicate_rolls_remain_individual_and_persist(wiz,data):
    from playwright.sync_api import expect
    page,origin,app,info=wiz
    page.goto(origin+'/srd-creator');page.locator('#scNewGuided').click();expect(page.locator('#scBuilder')).to_be_visible()
    state=wizard_state(data);state.update(abilityMethod='roll',abilityRolls=[[6,5,4,1],[6,6,3,1],[6,5,3,1],[5,4,3,1],[4,4,2,1],[3,3,2,1]],abilityBase={})
    page.evaluate('(state)=>window.SrdCreator.mutate(s=>{Object.keys(s).forEach(k=>delete s[k]);Object.assign(s,state);})',state)
    page.evaluate("() => window.SrdCreator.goStep('attribute')")
    expect(page.locator('.sc-roll-result')).to_have_count(6)
    expect(page.locator('#scBase-str option:not([value=""])')).to_have_count(6)
    page.locator('#scBase-str').select_option('0');page.locator('#scBase-dex').select_option('1')
    expect(page.locator('.sc-roll-result').nth(0)).to_contain_text('Stärke')
    expect(page.locator('.sc-roll-result').nth(1)).to_contain_text('Geschicklichkeit')
    expect(page.locator('#scBase-con option[value="0"]')).to_be_disabled()
    expect(page.locator('#scBase-con option[value="1"]')).to_be_disabled()
    _saved(page);page.reload()
    expect(page.locator('#scBase-str')).to_have_value('0');expect(page.locator('#scBase-dex')).to_have_value('1')
    page.locator('#scBase-str').select_option('')
    expect(page.locator('.sc-roll-result').nth(1)).to_contain_text('Noch verfügbar')
    expect(page.locator('#scBase-con option[value="1"]')).to_be_enabled()


def test_inline_subclass_and_sort_keep_the_picks_and_origin_draft(wiz,data):
    from playwright.sync_api import expect
    page,origin,app,info=wiz
    page.goto(origin+'/srd-creator');page.locator('#scNewQuick').click();expect(page.locator('#scBuilder')).to_be_visible();state=wizard_state(data)
    page.evaluate('(state)=>window.SrdCreator.mutate(s=>{Object.keys(s).forEach(k=>delete s[k]);Object.assign(s,state);})',state)
    _saved(page)
    preview=page.locator('[data-subclass-preview]').first
    expect(preview.locator('details[data-feature-level="3"]').first).to_be_visible()
    expect(preview.locator('details[data-feature-level="6"]')).to_have_count(0)
    expect(preview).to_contain_text('Spätere Unterklassenmerkmale')
    assert page.locator('a[href="/api/ce/authoring#ce-origins"]').get_attribute('target')=='_blank'
    before=page.evaluate('() => JSON.stringify(window.SrdCreator.app.draft.state)')
    page.locator('#scRefreshOrigins').click();expect(page.locator('[data-subclass-preview]').first).to_be_visible()
    assert before==page.evaluate('() => JSON.stringify(window.SrdCreator.app.draft.state)')
    def order():return page.locator('.sc-choice-list [data-level]').evaluate_all('rows=>rows.map(r=>({level:Number(r.dataset.level),name:r.dataset.name}))')
    for list_ in page.locator('.sc-choice-list:has([data-level])').all():
        levels=list_.locator('[data-level]').evaluate_all('rows=>rows.map(r=>Number(r.dataset.level))');assert levels==sorted(levels)
    checked=page.locator('.sc-choice-list [data-level] input:checked').count()
    page.locator('#scSpellSort').focus();page.locator('#scSpellSort').select_option('name')
    for list_ in page.locator('.sc-choice-list:has([data-level])').all():
        assert list_.evaluate('(n)=>{const names=[...n.children].map(r=>r.dataset.name);return names.every((v,i)=>!i||names[i-1].localeCompare(v,"de")<=0)}')
    assert checked==page.locator('.sc-choice-list [data-level] input:checked').count()
    assert page.locator('#scSpellSort').evaluate('n=>n===document.activeElement')


def test_later_level_up_shows_existing_subclass_feature_and_keeps_spell_choice(wiz,data):
    from playwright.sync_api import expect
    from vtt.extensions import db
    from vtt.models import Character
    from vtt.rules_content.creator_drafts import character_values
    from vtt.rules_content.creator_rules import evaluate
    page,origin,app,info=wiz;state=wizard_state(data)
    with app.app_context():
        char=Character(user_id=info['user_id'],**character_values(data,state,evaluate(data,state),draft_id=1,finalized_at='2026-11-13T12:00:00Z'))
        char.xp=14000;db.session.add(char);db.session.commit();cid=char.id
    page.goto(f'{origin}/character-sheet?id={cid}&mode=edit')
    page.get_by_role('tab',name='Verwaltung',exact=True).click();page.get_by_role('button',name='Stufe 6 aufsteigen',exact=True).click()
    preview=page.locator('#srdWizard [data-subclass-preview]')
    expect(preview.locator('[data-feature-level="6"]').first).to_be_visible()
    expect(preview.locator('[data-feature-level="3"]')).to_have_count(0)
    selectors=page.locator('#srdWizard .srd-prog-filterable select')
    expect(selectors.first).to_be_visible()
    checked=page.locator('#srdWizard .srd-prog-check input:checked').count()
    selectors.first.focus();selectors.first.select_option('name')
    assert checked==page.locator('#srdWizard .srd-prog-check input:checked').count()
    assert selectors.first.evaluate('n=>n===document.activeElement')
