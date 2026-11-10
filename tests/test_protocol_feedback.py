"""Acceptance for the protocol feedback: real journeys, not implementation mirrors."""
import pytest

from tests.test_srd_creator_api import app, client, data, make_draft, wizard_state, BASE  # noqa: F401
from tests.test_srd_creator_browser import wiz, site as creator_site  # noqa: F401


@pytest.mark.parametrize('kind', ['armor', 'shield'])
def test_new_character_cannot_receive_unowned_starting_armor(client, data, kind):
    state = wizard_state(data)
    state['equipment'] = {'classPackage': 'B', 'backgroundPackage': 'B'}
    if kind == 'armor':
        state['equipment']['armor'] = next(a['id'] for a in data['equipment']['armor'] if a['category'] == 'heavy')
    else:
        state['equipment']['shield'] = True
    created = make_draft(client, state)
    assert f'{kind}-not-in-package' in {b['code'] for b in created['blockers']}
    draft = created['draft']
    response = client.post(f"{BASE}/drafts/{draft['id']}/finalize", json={'version': draft['version']})
    assert response.status_code == 422
    assert f'{kind}-not-in-package' in {b['code'] for b in response.get_json()['blockers']}


# The shared creator fixture expects the fixture name `site`.
@pytest.fixture
def site(creator_site):
    return creator_site


def test_roll_assignment_keeps_used_values_visible_and_preserves_duplicates(wiz):
    from playwright.sync_api import expect
    page, origin, _, _ = wiz
    page.goto(origin + '/srd-creator')
    page.locator('#scNewGuided').click()
    page.get_by_role('button', name='Kämpfer', exact=False).first.click()
    page.get_by_role('button', name='Attribute', exact=False).first.click()
    page.evaluate("""() => SrdCreator.mutate(s => {
        s.abilityMethod='roll'; s.abilityBase={};
        s.abilityRolls=[[6,6,6,1],[6,6,6,2],[5,5,5,1],[4,4,4,1],[3,3,3,1],[2,2,2,1]];
    })""")
    page.locator('#scBase-str').select_option('18')
    page.locator('#scBase-dex').select_option('18')
    expect(page.locator('#scBase-con option[value="18"]')).to_be_disabled()
    assert page.locator('#scBase-con option').all_text_contents() == ['–', '18 · 2× gewürfelt · bereits vergeben', '15 · 1× gewürfelt · 1 zuweisbar', '12 · 1× gewürfelt · 1 zuweisbar', '9 · 1× gewürfelt · 1 zuweisbar', '6 · 1× gewürfelt · 1 zuweisbar']
    page.locator('#scBase-str').select_option('')
    expect(page.locator('#scBase-con option[value="18"]')).to_be_enabled()
    page.locator('#scBase-con').select_option('18')
    expect(page.locator('#scBase-dex')).to_have_value('18')


def test_level_features_and_package_changes_explain_ownership(wiz):
    from playwright.sync_api import expect
    page, origin, _, _ = wiz
    page.goto(origin + '/srd-creator')
    page.locator('#scNewGuided').click()
    page.get_by_role('button', name='Kämpfer', exact=False).first.click()
    page.locator('#scLevel').fill('3')
    page.locator('#scLevel').dispatch_event('change')
    expect(page.get_by_role('columnheader', name='Neue Merkmale')).to_be_visible()
    expect(page.locator('.sc-level-features').last).to_contain_text('Klassenstufe 3')
    page.get_by_role('button', name='Ausrüstung', exact=False).first.click()
    page.get_by_role('button', name='Paket A', exact=False).first.click()
    assert page.locator('#scArmor option').count() > 1
    page.locator('#scArmor').select_option(index=1)
    expect(page.locator('#scArmor option:checked')).to_contain_text('Klasse: Kämpfer')
    page.get_by_role('button', name='Paket C', exact=False).first.click()
    expect(page.locator('#scArmor option')).to_have_count(1)
    expect(page.get_by_label('Schild führen (+2 RK)')).to_be_disabled()
    assert page.evaluate('SrdCreator.app.draft.state.equipment.armor || null') is None
