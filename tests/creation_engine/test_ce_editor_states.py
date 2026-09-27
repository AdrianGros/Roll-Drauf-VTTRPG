"""VD slice 2: concurrent browser saves, deliberate recovery, focus and copy identity."""

import json
import os
from pathlib import Path

import pytest

expect = pytest.importorskip('playwright.sync_api').expect

from test_ce_authoring_transports import (
    author, authoring_engine, browser, migration_engine, postgres_engine,
    read, transport, wait_version,
)

pytestmark = pytest.mark.postgres


def form(page, question):
    return page.locator(f'form[data-question="{question}"]')


def switch(page, control, value):
    page.locator('#' + control).select_option(value)
    expect(page.locator('#' + control)).to_be_enabled()


def press(page, selector):
    """Activate via the keyboard; focus moves are asserted after the action."""
    control = page.locator(selector)
    expect(control).to_be_visible()
    expect(control).to_be_enabled()
    control.focus()
    page.keyboard.press('Enter')


def other_tab(page, mode='structured'):
    other = page.context.new_page()
    other.goto(page.url)
    expect(other.locator('#mode')).to_be_enabled()
    switch(other, 'mode', mode)
    return other


@pytest.mark.parametrize('locale', ['de', 'en', 'fr'])
def test_browser_conflict_retains_exact_input_and_requires_review_and_new_save(browser, tmp_path, locale):
    page, context = browser
    switch(page, 'locale', locale)
    switch(page, 'mode', 'advanced')
    other = other_tab(page)
    raw = '  "Local <img src=x onerror=alert(1)> answer"  '
    form(page, 'item.name').locator('textarea').fill(raw)
    commands = []
    page.on('request', lambda request: commands.append(request.post_data_json) if request.url.endswith('/api/ce/commands') else None)
    form(other, 'item.name').locator('textarea').fill('Saved by the other tab')
    press(other, 'form[data-question="item.name"] button[type="submit"]')
    wait_version(other, 2)
    press(page, 'form[data-question="item.name"] button[type="submit"]')
    expect(page.locator('#conflict-heading')).to_be_focused()
    assert page.locator('#conflict-local').inner_text() == raw
    assert page.locator('#conflict-local img').count() == 0
    assert form(page, 'item.name').locator('textarea').input_value() == raw
    assert page.locator('#retry').is_hidden() and page.locator('#conflict-edit').is_hidden()
    assert page.locator('#reload').is_disabled()
    press(page, '#conflict-refresh')
    expect(page.locator('#conflict-current')).to_be_focused()
    assert 'Saved by the other tab' in page.locator('#conflict-current').inner_text()
    assert len(commands) == 1 and read(context)['draftVersion'] == 2
    artifact = Path(os.environ.get('CE_TEST_ARTIFACT_DIR', tmp_path)); artifact.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(artifact / f'conflict-{locale}-phone.png'), full_page=True)
    press(page, '#conflict-edit')
    expect(form(page, 'item.name').locator('textarea')).to_be_focused()
    assert form(page, 'item.name').locator('textarea').input_value() == raw
    assert len(commands) == 1 and read(context)['content']['name'] == 'Saved by the other tab'
    press(page, 'form[data-question="item.name"] button[type="submit"]')
    wait_version(page, 3)
    assert read(context)['content']['name'] == json.loads(raw)
    assert len(commands) == 2 and commands[0]['idempotencyKey'] != commands[1]['idempotencyKey']
    assert [command['expectedDraftVersion'] for command in commands] == [1, 2]
    assert commands[0]['payload'] == commands[1]['payload']
    expect(form(page, 'flame.behavior').locator('textarea')).to_be_focused()
    other.close()


def test_browser_conflict_refresh_failure_and_second_race_keep_the_answer(browser):
    page, context = browser
    other = other_tab(page)
    # Guided mode only shows the next question; recovery exposes the retained answer explicitly.
    form(page, 'flame.behavior').locator('select').select_option('damage')
    form(other, 'flame.behavior').locator('select').select_option('visual')
    press(other, 'form[data-question="flame.behavior"] button[type="submit"]'); wait_version(other, 2)
    press(page, 'form[data-question="flame.behavior"] button[type="submit"]')
    expect(page.locator('#conflict-heading')).to_be_focused()
    failed_url = '**/drafts/*?locale=*&mode=*'
    page.route(failed_url, lambda route: route.abort('failed'))
    press(page, '#conflict-refresh')
    expect(page.locator('#status')).to_contain_text('konnte nicht geladen')
    assert page.locator('#conflict-local').inner_text() == 'damage'
    assert page.locator('#conflict-edit').is_hidden()
    assert page.locator('#conflict-current').inner_text() == 'Noch nicht geladen.'
    page.unroute(failed_url)
    press(page, '#conflict-refresh'); expect(page.locator('#conflict-current')).to_be_focused()
    press(page, '#conflict-edit')
    assert page.locator('#mode').input_value() == 'structured'
    expect(form(page, 'flame.behavior').locator('select')).to_be_focused()
    form(other, 'item.name').locator('textarea').fill('Another intervening save')
    press(other, 'form[data-question="item.name"] button[type="submit"]'); wait_version(other, 3)
    press(page, 'form[data-question="flame.behavior"] button[type="submit"]')
    expect(page.locator('#conflict-heading')).to_be_focused()
    assert page.locator('#conflict-local').inner_text() == 'damage'
    press(page, '#conflict-refresh'); expect(page.locator('#conflict-current')).to_be_focused()
    press(page, '#conflict-edit')
    press(page, 'form[data-question="flame.behavior"] button[type="submit"]'); wait_version(page, 4)
    assert read(context)['content']['flames']['behavior'] == 'damage'
    assert read(context)['content']['name'] == 'Another intervening save'
    other.close()


def test_browser_conflict_cannot_restore_a_question_hidden_by_changed_behavior(browser):
    page, context = browser
    press(page, '#damage-preset'); press(page, '#apply-preset'); wait_version(page, 2)
    switch(page, 'mode', 'structured')
    other = other_tab(page)
    damage = form(page, 'flame.damage')
    damage.locator('input').first.fill('7')
    form(other, 'flame.behavior').locator('select').select_option('visual')
    press(other, 'form[data-question="flame.behavior"] button[type="submit"]'); wait_version(other, 3)
    press(page, 'form[data-question="flame.damage"] button[type="submit"]')
    expect(page.locator('#conflict-heading')).to_be_focused()
    press(page, '#conflict-refresh'); expect(page.locator('#conflict-current')).to_be_focused()
    assert page.locator('#conflict-local').inner_text() == '7\n6'
    assert page.locator('#conflict-edit').is_hidden()
    assert 'jetzt nicht verfügbar' in page.locator('#conflict-note').inner_text()
    assert 'damage' not in read(context)['content']['flames']
    press(page, '#conflict-discard')
    expect(page.locator('#conflict')).to_be_hidden()
    wait_version(page, 3)
    assert form(page, 'flame.damage').count() == 0
    expect(form(page, 'flame.timing').locator('select')).to_be_focused()
    other.close()


@pytest.mark.parametrize('refresh_first', [False, True])
def test_browser_conflicting_preset_is_never_reapplied_by_refresh_or_discard(browser, refresh_first):
    page, context = browser
    other = other_tab(page)
    press(page, '#damage-preset')
    expect(page.locator('#apply-preset')).to_be_focused()
    form(other, 'item.name').locator('textarea').fill('Keep this saved name')
    press(other, 'form[data-question="item.name"] button[type="submit"]'); wait_version(other, 2)
    press(page, '#apply-preset')
    expect(page.locator('#conflict-heading')).to_be_focused()
    assert page.locator('#conflict-local').inner_text() == 'Diese Antworten übernehmen'
    if refresh_first:
        press(page, '#conflict-refresh'); expect(page.locator('#conflict-current')).to_be_focused()
        assert page.locator('#conflict-edit').is_hidden()
        assert 'Keep this saved name' in page.locator('#conflict-current').inner_text()
    press(page, '#conflict-discard'); wait_version(page, 2)
    expect(page.locator('#conflict')).to_be_hidden()
    assert read(context)['content']['name'] == 'Keep this saved name'
    assert 'flames' not in read(context)['content']
    expect(form(page, 'flame.behavior').locator('select')).to_be_focused()
    other.close()


def test_browser_validation_focus_and_view_changes_preserve_input(browser):
    page, context = browser
    for locale in ['en', 'fr', 'de']:
        switch(page, 'locale', locale); expect(page.locator('#locale')).to_be_focused()
    for mode in ['structured', 'advanced', 'guided']:
        switch(page, 'mode', mode); expect(page.locator('#mode')).to_be_focused()
    assert read(context)['draftVersion'] == 1
    press(page, '#visual-preset'); expect(page.locator('#apply-preset')).to_be_focused()
    press(page, '#apply-preset'); wait_version(page, 2)
    expect(form(page, 'item.prose').locator('textarea')).to_be_focused()
    press(page, 'form[data-question="item.prose"] button[type="button"]'); wait_version(page, 3)
    expect(page.locator('#questions-complete')).to_be_focused()
    switch(page, 'mode', 'advanced')
    name = form(page, 'item.name').locator('textarea')
    name.fill('unfinished JSON')
    press(page, 'form[data-question="item.name"] button[type="submit"]')
    expect(name).to_be_focused()
    assert name.get_attribute('aria-invalid') == 'true'
    error_id = name.get_attribute('aria-describedby').split()[-1]
    assert page.locator('[id="' + error_id + '"]').inner_text().startswith('Gib gültiges JSON')
    assert name.input_value() == 'unfinished JSON' and read(context)['draftVersion'] == 3
    # Syntactically valid JSON, rejected by the actual server's typed schema.
    name.fill('42')
    press(page, 'form[data-question="item.name"] button[type="submit"]')
    expect(name).to_be_focused()
    assert name.input_value() == '42' and name.get_attribute('aria-invalid') == 'true'
    assert read(context)['draftVersion'] == 3 and page.locator('#retry').is_hidden()
    press(page, '#discard'); expect(name).to_be_focused()
    assert name.input_value() != '42' and name.get_attribute('aria-invalid') is None
    switch(page, 'mode', 'structured')
    capacity = form(page, 'flame.maximum').locator('input')
    capacity.fill('')
    press(page, 'form[data-question="flame.maximum"] button[type="submit"]')
    expect(capacity).to_be_focused()
    assert capacity.get_attribute('aria-invalid') == 'true' and read(context)['draftVersion'] == 3
    press(page, '#discard')


def test_browser_tab_order_and_native_select_arrows_reach_the_next_question(browser):
    page, context = browser
    page.keyboard.press('Tab')
    expect(page.locator('.ce-skip')).to_be_focused()
    page.keyboard.press('Enter')
    expect(page.locator('#main')).to_be_focused()
    page.keyboard.press('Tab')
    expect(page.locator('#locale')).to_be_focused()
    page.keyboard.press('ArrowDown')
    expect(page.locator('#locale')).to_have_value('en')
    expect(page.locator('#locale')).to_be_enabled()
    expect(page.locator('#locale')).to_be_focused()
    page.keyboard.press('Tab')
    expect(page.locator('#mode')).to_be_focused()
    page.keyboard.press('ArrowDown')
    expect(page.locator('#mode')).to_have_value('structured')
    expect(page.locator('#mode')).to_be_enabled()
    expect(page.locator('#mode')).to_be_focused()
    for selector in ['#drafts', '#new-type', '#new', '#reload', 'form[data-question="item.name"] textarea']:
        page.keyboard.press('Tab'); expect(page.locator(selector)).to_be_focused()
        if selector == '#new-type':
            page.keyboard.press('ArrowDown')
            expect(page.locator(selector)).to_have_value('g1.authored-manual-conditional')
            expect(page.locator('#new')).to_have_text('Create content')
            page.keyboard.press('ArrowUp')
            expect(page.locator(selector)).to_have_value('g1.authored-magic-item')
            assert read(context)['draftVersion'] == 1
    page.keyboard.type('Keyboard item')
    page.keyboard.press('ArrowLeft')
    assert form(page, 'item.name').locator('textarea').evaluate('(n) => n.selectionStart') == 12
    page.keyboard.press('Tab')
    expect(form(page, 'item.name').locator('button[type="submit"]')).to_be_focused()
    page.keyboard.press('Shift+Tab')
    expect(form(page, 'item.name').locator('textarea')).to_be_focused()
    page.keyboard.press('Tab'); page.keyboard.press('Enter'); wait_version(page, 2)
    expect(form(page, 'flame.behavior').locator('select')).to_be_focused()
    page.keyboard.press('ArrowDown')
    expect(form(page, 'flame.behavior').locator('select')).to_have_value('visual')
    page.keyboard.press('Tab')
    expect(form(page, 'flame.behavior').locator('button[type="submit"]')).to_be_focused()
    page.keyboard.press('Shift+Tab')
    expect(form(page, 'flame.behavior').locator('select')).to_be_focused()
    page.keyboard.press('Tab'); page.keyboard.press('Enter'); wait_version(page, 3)
    expect(form(page, 'flame.timing').locator('select')).to_be_focused()
    assert read(context)['content']['flames']['behavior'] == 'visual'


@pytest.mark.parametrize('transport', ['native'], indirect=True)
def test_browser_same_named_copies_keep_identity_and_selected_resources(browser, tmp_path):
    page, context = browser
    press(page, '#visual-preset'); press(page, '#apply-preset'); wait_version(page, 2)
    switch(page, 'claim', 'runtime_ready')
    press(page, '#commit'); wait_version(page, 3)
    page.locator('#sb-revisions input').focus(); page.keyboard.press('Space')
    press(page, '#sb-create'); expect(page.locator('#sb-state')).to_be_focused()
    switch(page, 'sb-revision', page.locator('#sb-revision option').nth(1).get_attribute('value'))
    page.locator('#sb-reason').fill('Two identical copies, independent resources')
    for count in [2, 3]:
        press(page, '#sb-instantiate')
        expect(page.locator('#sb-item option')).to_have_count(count)
        expect(page.locator('#sb-state')).to_be_focused()
    options = page.locator('#sb-item option').evaluate_all('(nodes) => nodes.filter(n => n.value).map(n => [n.value, n.textContent])')
    assert len({label for _, label in options}) == 2
    first, second = [value for value, _ in options]
    switch(page, 'sb-item', second)
    press(page, '#sb-activate'); expect(page.locator('#sb-state')).to_be_focused()
    rows = {value: page.locator(f'[data-instance="{value}"]').inner_text() for value, _ in options}
    assert '3/3' in rows[first] and '2/3' in rows[second]
    assert all(label in rows[value] for value, label in options)
    assert page.locator('#sb-item').input_value() == second
    press(page, '#sb-refresh'); expect(page.locator('#sb-refresh')).to_be_focused()
    assert page.locator('#sb-item option').evaluate_all('(nodes) => nodes.filter(n => n.value).map(n => [n.value, n.textContent])') == options
    scope = page.locator('#sb-select').input_value()
    page.reload(); expect(page.locator('#mode')).to_be_enabled()
    switch(page, 'sb-select', scope)
    expect(page.locator('#sb-item option')).to_have_count(3)
    assert page.locator('#sb-item option').evaluate_all('(nodes) => nodes.filter(n => n.value).map(n => [n.value, n.textContent])') == options
    switch(page, 'sb-item', second)
    press(page, '#sb-recover'); expect(page.locator('#sb-state')).to_be_focused()
    summary = context['gateway'].kernel.native.summary(context['gateway'], context['principal'], scope)
    assert all(instance['fields']['charges'] == 3 for instance in summary['instances'])
    artifact = Path(os.environ.get('CE_TEST_ARTIFACT_DIR', tmp_path)); artifact.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(artifact / 'same-named-copies-phone.png'), full_page=True)


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
def test_browser_keyboard_damage_choice_focus_and_same_named_actor_labels(browser):
    page, context = browser
    switch(page, 'sb-select', context['scope'])
    expect(page.locator('#sb-scope')).to_be_visible()
    labels = page.locator('#sb-target option').evaluate_all('(nodes) => nodes.filter(n => n.value).map(n => n.textContent)')
    assert len(labels) == 2 and len(set(labels)) == 2
    switch(page, 'sb-item', context['item']); switch(page, 'sb-target', context['target'])
    press(page, '#sb-hit')
    expect(page.locator('#sb-decisions button').first).to_be_focused()
    page.keyboard.press('Tab')
    expect(page.locator('#sb-decisions button').nth(1)).to_be_focused()
    page.keyboard.press('Enter')
    expect(page.locator('#sb-state')).to_be_focused()
    assert page.locator('#sb-decisions button').count() == 0
    assert context['gateway'].kernel.random.draws == 0
    assert page.locator('#sb-instances li').filter(has_text='20/30').count() == 2
