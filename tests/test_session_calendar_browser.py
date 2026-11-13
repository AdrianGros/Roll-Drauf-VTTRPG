"""Actual series planning and cancellation through the shared calendar in both engines."""
from datetime import datetime, timedelta
import pytest
from tests.test_balu_navigation import balu_site, balu_browser, save_proof

@pytest.mark.parametrize('width', [1440,390])
def test_plan_recurrence_calendar_navigation_and_cancel(balu_browser,width):
    from playwright.sync_api import expect
    page,origin,data=balu_browser
    page.set_default_timeout(30000)
    page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
    hub=f"{origin}/campaigns?campaign_id={data['campaign_id']}"
    page.goto(hub)
    planner=page.locator('[data-campaign-planner]')
    expect(planner.locator('[data-polls]')).to_have_attribute('aria-busy','false',timeout=30000)
    planner.locator('[data-tool=series] summary').click()
    form=planner.locator('[data-series-form]')
    form.get_by_label('Session-Name',exact=True).fill('Regelmäßiger Spielabend')
    first=(datetime.now()+timedelta(days=1)).replace(hour=19,minute=30,second=0,microsecond=0)
    form.get_by_label('Erster Termin',exact=True).fill(first.isoformat(timespec='minutes'))
    form.get_by_label('Wiederholung',exact=False).select_option('biweekly')
    form.get_by_label('Letzter Tag der Serie',exact=False).fill((first+timedelta(days=28)).date().isoformat())
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/session-series')) as created:
        form.get_by_role('button',name='Serie speichern',exact=True).click()
    assert created.value.status==201
    body=created.value.request.post_data_json
    expect(planner.locator('[data-planner-status]')).to_contain_text('Serie gespeichert',timeout=30000)
    replay=page.evaluate("async ({path,body})=>await window.Auth.makeAuthRequest(path,'POST',body)",
        {'path':f"/api/campaigns/{data['campaign_id']}/session-series",'body':body})
    assert replay['series']['id']==created.value.json()['series']['id']
    page.goto(origin+'/campaigns')
    own=page.locator('[data-own-calendar]')
    expect(own.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false',timeout=30000)
    own.locator('[data-scope=rolling30]').click()
    events=own.locator('[data-session-id]').filter(has_text='Regelmäßiger Spielabend')
    expect(events).to_have_count(3)
    own.locator('[data-scope=month]').click()
    expect(own.locator('.sc-month-grid')).to_be_visible()
    own.locator('[data-move="1"]').click()
    expect(own.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false',timeout=30000)
    own.locator('[data-today]').click()
    own.locator('[data-scope=rolling30]').click()
    expect(events).to_have_count(3,timeout=30000)
    page.once('dialog',lambda d:d.accept())
    with page.expect_response(lambda r:r.request.method=='POST' and '/session-appointments/' in r.url) as cancelled:
        events.first.locator('[data-cancel]').click()
    assert cancelled.value.status==200
    expect(events.filter(has=page.locator('[data-cancel]'))).to_have_count(2)
    expect(own.locator('[data-status=cancelled]')).to_contain_text('Abgesagt')
    save_proof(page,'session-calendar')
    assert page.evaluate('document.documentElement.scrollWidth')<=width+1
    page.goto(hub)
    expect(planner.locator('[data-polls]')).to_have_attribute('aria-busy','false',timeout=30000)
    planner.locator('[data-tool=stop] summary').click()
    page.once('dialog',lambda d:d.accept())
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/stop')) as stopped:
        planner.locator('[data-stop]').click()
    assert stopped.value.status==200 and stopped.value.json()['cancelled']==2
    expect(planner.locator('[data-stop]')).to_have_count(0,timeout=30000)
