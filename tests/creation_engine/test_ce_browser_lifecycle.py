"""Real tab loss, held copies and worker-driven timeout/manual UI outcomes."""

from datetime import timedelta

import pytest

from vtt.creation_engine.store.maintenance import tick

from test_ce_authoring_transports import author, authoring_engine, browser, migration_engine, postgres_engine, transport, wait_version
from test_ce_authoring import read
from test_ce_native import fields

expect = pytest.importorskip('playwright.sync_api').expect
pytestmark = pytest.mark.postgres


@pytest.mark.parametrize('committed', [False, True])
def test_closed_tab_reloads_authoritative_draft_without_replaying_uncertain_save(browser, committed):
    page, a = browser
    page.locator('#mode').select_option('structured')
    form = page.locator('form[data-question="item.name"]')
    form.locator('textarea').fill('Saved before tab loss' if committed else 'Only in the lost tab')
    requests = []

    def uncertain(route):
        requests.append(route.request.post_data_json)
        route.fetch()  # Commit on the real server, then lose only its response.
        route.abort('failed')

    if committed:
        page.route('**/api/ce/commands', uncertain)
        form.locator('button[type="submit"]').click()
        expect(page.locator('#retry')).to_be_visible()
        assert read(a)['draftVersion'] == 2
    before = read(a)
    origin = page.url
    context = page.context
    page.close(run_before_unload=False)
    reopened = context.new_page()
    writes = []
    reopened.on('request', lambda request: writes.append(request.post_data_json) if request.url.endswith('/api/ce/commands') else None)
    try:
        reopened.goto(origin)
        wait_version(reopened, before['draftVersion'])
        assert reopened.locator('#retry').is_hidden()
        assert reopened.locator('#discard').is_hidden()
        assert read(a) == before and writes == []
        assert len(requests) == int(committed)
        assert ('Saved before tab loss' in reopened.locator('#draft-info').inner_text()) is committed
        assert 'Only in the lost tab' not in reopened.locator('#editor').inner_text()
    finally:
        reopened.close()


def select_sandbox(page, a):
    page.locator('#locale').select_option('en')
    expect(page.locator('#sb-select')).to_be_enabled()
    page.locator('#sb-select').select_option(a['scope'])
    expect(page.locator('#sb-scope')).to_be_visible()
    expect(page.locator('#sb-item')).to_be_enabled()
    page.locator('#sb-item').select_option(a['item'])
    page.locator('#sb-target').select_option(a['target'])


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
def test_browser_held_copy_equip_decline_accept_and_recovery(browser):
    page, a = browser
    select_sandbox(page, a)
    page.locator('#sb-equip').click()
    expect(page.locator('#sb-equip')).to_be_enabled()
    assert not fields(a, a['item'])['is_equipped']
    expect(page.locator('#sb-hit')).to_be_disabled()
    page.locator('#sb-equip').click()
    expect(page.locator('#sb-hit')).to_be_enabled()
    assert fields(a, a['item'])['is_equipped']
    page.locator('#sb-hit').click()
    page.get_by_role('button', name='No, keep the hit', exact=True).click()
    expect(page.locator('#sb-hit')).to_be_enabled()
    assert fields(a, a['item'])['charges'] == 3
    assert fields(a, a['target'])['hp_current'] == 20
    page.locator('#sb-hit').click()
    page.get_by_role('button', name='Yes, spend charges', exact=True).click()
    expect(page.locator('#sb-hit')).to_be_enabled()
    assert fields(a, a['item'])['charges'] == 2
    assert fields(a, a['target'])['hp_current'] == 14
    page.locator('#sb-recover').click()
    expect(page.locator('#sb-hit')).to_be_enabled()
    assert fields(a, a['item'])['charges'] == 3
    assert fields(a, a['target'])['hp_current'] == 14
    assert a['gateway'].kernel.random.draws == 2


@pytest.mark.parametrize('transport', ['damage-native'], indirect=True)
@pytest.mark.parametrize('clock_anomaly', [False, True])
def test_browser_worker_timeout_or_anomaly_and_manual_completion(browser, clock_anomaly):
    page, a = browser
    select_sandbox(page, a)
    page.locator('#sb-hit').click()
    expect(page.get_by_role('button', name='Yes, spend charges', exact=True)).to_be_enabled()
    with a['gateway'].store.transaction(a['scope']) as tx:
        clock = [tx.now]
    a['gateway'].store.clock = lambda: clock[0]
    for seconds in ([300] if clock_anomaly else [30] * 5):
        clock[0] += timedelta(seconds=seconds)
        tick(a['gateway'])
    page.locator('#sb-refresh').click()
    expect(page.locator('#sb-decisions button')).to_have_count(0)
    if clock_anomaly:
        expect(page.locator('#sb-manual')).to_be_visible()
        expect(page.locator('#sb-resolve')).to_be_disabled()
        assert 'Manual decision required' in page.locator('#sb-state').inner_text()
        page.locator('#sb-outcome').fill('Keep the confirmed hit; no additional flames applied.')
        page.locator('#sb-manual-reason').fill('Resolve the test clock anomaly without another spend.')
        page.locator('#sb-resolve').click()
    expect(page.locator('#sb-hit')).to_be_enabled()
    expect(page.locator('#sb-manual')).to_be_hidden()
    assert fields(a, a['item'])['charges'] == 3
    assert fields(a, a['target'])['hp_current'] == 20
    assert a['gateway'].kernel.random.draws == 0
    with a['gateway'].store.transaction(a['scope']) as tx:
        assert tx.scope.active_action_id is None
