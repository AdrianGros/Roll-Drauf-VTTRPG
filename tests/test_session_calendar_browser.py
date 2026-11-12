from datetime import datetime, timedelta

import pytest

from tests.test_balu_navigation import balu_site, balu_browser, save_proof


@pytest.mark.parametrize('width', [1440,390])
def test_plan_recurrence_calendar_navigation_and_cancel(balu_browser, width):
    from playwright.sync_api import expect
    page, origin, data=balu_browser
    page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
    page.goto(f"{origin}/campaigns?campaign_id={data['campaign_id']}")
    root=page.locator('[data-session-calendar]')
    expect(root.get_by_role('heading',name='Session-Kalender')).to_be_visible()
    expect(root.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false')
    root.get_by_text('Termin oder Serie planen',exact=True).click()
    root.get_by_label('Session-Name',exact=True).fill('Regelmäßiger Spielabend')
    first=(datetime.now()+timedelta(days=2)).replace(hour=19,minute=30,second=0,microsecond=0)
    root.get_by_label('Erster Termin',exact=True).fill(first.isoformat(timespec='minutes'))
    root.get_by_label('Wiederholung',exact=True).select_option('biweekly')
    root.get_by_label('Letzter Tag der Serie',exact=False).fill((first+timedelta(days=28)).date().isoformat())
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/session-series')) as created:
        root.get_by_role('button',name='Serie speichern',exact=True).click()
    assert created.value.status==201
    expect(root.locator('[data-form-status]')).to_contain_text('Serie gespeichert')
    expect(root.locator('[data-calendar-form]')).to_have_attribute('aria-busy','false')
    expect(root.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false')
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/session-series')) as retry:
        root.get_by_role('button',name='Serie speichern',exact=True).click()
    assert retry.value.status==200
    expect(root.locator('[data-calendar-form]')).to_have_attribute('aria-busy','false')
    expect(root.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false')
    root.get_by_role('button',name='Jahr',exact=True).click()
    expect(root.locator('[data-month]')).to_have_count(12)
    root.locator(f'[data-month="{first:%Y-%m}-01"]').click()
    expect(root.locator('.sc-month-grid')).to_be_visible()
    root.get_by_role('button',name='Woche',exact=True).click()
    expect(root.locator('.sc-week')).to_be_visible()
    root.get_by_role('button',name='Monat',exact=True).click()
    expect(root.locator('.sc-month-grid')).to_be_visible()
    page.once('dialog',lambda dialog:dialog.accept())
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/cancel-appointment')) as cancelled:
        root.get_by_role('button',name='Termin absagen',exact=True).click()
    assert cancelled.value.status==200
    expect(root.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false')
    root.locator('.sc-heading').scroll_into_view_if_needed()
    page.mouse.move(0,0)
    save_proof(page,'session-calendar')
    assert root.evaluate('e=>e.getBoundingClientRect().right')<=width+1
    assert page.evaluate('document.documentElement.scrollWidth')<=width+1
    page.reload()
    expect(root.locator('[data-calendar-content]')).to_have_attribute('aria-busy','false')
    root.get_by_text('Serien verwalten (1)',exact=True).click()
    page.once('dialog',lambda dialog:dialog.accept())
    with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/stop')) as stopped:
        root.get_by_role('button',name='Serie beenden',exact=True).click()
    assert stopped.value.status==200 and stopped.value.json()['cancelled']==2
    expect(root.locator('[data-stop]')).to_have_count(0)
