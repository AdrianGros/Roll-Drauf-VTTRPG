"""Actual private-note and One-Shot journeys through the ordinary campaign calendar."""
from datetime import datetime, timedelta
import os
from pathlib import Path
from threading import Thread

import pytest
from uuid import uuid4
from flask_jwt_extended import create_access_token
from werkzeug.serving import WSGIRequestHandler, make_server

from vtt import create_app
from vtt.calendar_notes import process_due
from vtt.calendar_notes import calendar_notes_bp
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Campaign, GameSession, Role, User
from vtt.models.calendar_note import CalendarNote, CalendarOneShot


class QuietHandler(WSGIRequestHandler):
    def log(self, *_args):
        pass


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path}/browser.db')
    app = create_app('testing')
    if 'calendar_notes' not in app.blueprints:
        app.register_blueprint(calendar_notes_bp)
    with app.app_context():
        db.create_all()
        role = Role(name='Review calendar player'); db.session.add(role); db.session.flush()
        user = User(username='review-calendar', email='review-calendar@example.test', password_hash='x', role_id=role.id,
                    is_active=True, account_state='active', profile_tier='dm', active_campaigns_quota=3)
        db.session.add(user); db.session.flush()
        campaign = Campaign(name='Review calendar group', owner_id=user.id, status='active')
        db.session.add(campaign); db.session.commit()
        token = create_access_token(identity=str(user.id)); uid = user.id; cid = campaign.id
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    yield app, f'http://127.0.0.1:{server.server_port}', token, uid, cid
    server.shutdown(); thread.join(timeout=5); server.server_close()
    with app.app_context():
        db.session.remove(); db.engine.dispose()


@pytest.mark.parametrize('width,theme,language,engine', [(1440, 'paper', 'de', 'firefox'), (390, 'night', 'en', 'chromium')])
def test_private_note_day_dialog_and_real_one_shot(site, width, theme, language, engine):
    from playwright.sync_api import expect, sync_playwright
    expect.set_options(timeout=20000)
    app, origin, token, uid, cid = site
    day = datetime.now().date().isoformat()
    first = (datetime.now() + timedelta(days=2)).replace(hour=19, minute=0, second=0, microsecond=0).isoformat(timespec='minutes')
    with app.app_context():
        now = datetime.now()
        db.session.add(CalendarNote(user_id=uid, request_key=str(uuid4()), input_digest='x' * 64,
            local_date=now.date() - timedelta(days=1), title='Due preparation', body='Private reminder', color='purple',
            reminder_at=now + timedelta(minutes=1), reminder_state='pending', timezone='UTC'))
        db.session.commit()
        assert process_due(now=now + timedelta(minutes=2)) == 1
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, **({'args': ['--no-sandbox']} if engine == 'chromium' else {}))
        context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce', has_touch=width < 500)
        context.add_init_script(f"localStorage.setItem('vtt.display.v1',JSON.stringify({{schema:1,theme:'{theme}',language:'{language}',unit:'m',accent:'default'}}))")
        context.add_cookies([{'name': 'access_token_cookie', 'value': token, 'url': origin, 'httpOnly': True}])
        page = context.new_page(); page.set_default_timeout(20000)
        def proof(label):
            if os.environ.get('VTT_PROOF_DIR'):
                folder = Path(os.environ['VTT_PROOF_DIR']); folder.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(folder / f'calendar-{label}-{width}.png'))
        errors = []; page.on('pageerror', lambda error: errors.append(str(error))); page.on('dialog', lambda dialog: dialog.accept())
        page.goto(origin + '/campaigns')
        calendar = page.locator('[data-own-calendar]')
        expect(calendar.locator('[data-calendar-content]')).to_have_attribute('aria-busy', 'false')
        reminders = calendar.locator('[data-personal-reminders]')
        expect(reminders).to_contain_text('Due preparation')
        page.reload()
        expect(calendar.locator('[data-calendar-content]')).to_have_attribute('aria-busy', 'false')
        expect(reminders).to_contain_text('Due preparation')
        reminders.locator('[data-dismiss]').click()
        expect(reminders).not_to_contain_text('Due preparation')
        button = calendar.locator(f'[data-day="{day}"]')
        button.focus(); button.press('Enter')
        dialog = calendar.locator('[data-calendar-dialog]')
        expect(dialog).to_be_visible()
        form = dialog.locator('[data-note-form]')
        form.locator('[name=title]').fill('Private preparation')
        form.locator('[name=body]').fill('My own calendar note\nSecond line')
        form.locator('[name=color]').select_option('blue')
        # Hold the successful response in the real auth client: Escape while saving
        # must keep the dialog closed when the delayed result eventually arrives.
        page.evaluate("""() => {
            const original = window.Auth.makeAuthRequest;
            window.Auth.makeAuthRequest = async function(path, method, ...tail) {
                const result = await original.call(this, path, method, ...tail);
                if (path === '/api/calendar/notes' && method === 'POST') {
                    window.Auth.makeAuthRequest = original;
                    await new Promise(resolve => { window.releaseCalendarSave = resolve; });
                }
                return result;
            };
        }""")
        form.locator('[type=submit]').click()
        page.wait_for_function("() => typeof window.releaseCalendarSave === 'function'")
        dialog.press('Escape')
        expect(dialog).not_to_be_visible()
        page.evaluate('window.releaseCalendarSave()')
        expect(calendar.locator(f'[data-day="{day}"] [data-color=blue]')).to_be_visible()
        expect(dialog).not_to_be_visible()
        calendar.locator(f'[data-day="{day}"]').click()
        expect(dialog.locator('[data-note]')).to_contain_text('Private preparation')
        assert dialog.locator('[data-note]').get_attribute('data-color') == 'blue'
        proof('note')
        dialog.locator('[data-day-close]').click()
        expect(calendar.locator(f'[data-day="{day}"]')).to_be_focused()
        expect(calendar.locator(f'[data-day="{day}"] [data-color=blue]')).to_be_visible()
        page.reload()
        expect(calendar.locator(f'[data-day="{day}"] [data-color=blue]')).to_be_visible()
        calendar.locator(f'[data-day="{day}"]').click()
        dialog.locator('[data-note-edit]').click()
        form.locator('[name=title]').fill('Edited preparation')
        form.locator('[type=submit]').click()
        expect(dialog.locator('[data-note]')).to_contain_text('Edited preparation')
        dialog.locator('[data-note-delete]').click()
        expect(dialog.locator('[data-note]')).to_have_count(0)
        dialog.locator('[data-day-close]').click()

        calendar.locator('[data-day-mode]').select_option('planning')
        calendar.locator(f'[data-day="{day}"]').click()
        plan = dialog.locator('[data-day-plan]')
        plan.locator('[name=name]').fill('Calendar planned session')
        plan.locator('[name=first_local]').fill(first)
        plan.locator('[name=timezone]').fill('UTC')
        plan.locator('[type=submit]').click()
        expect(dialog).not_to_be_visible()
        with app.app_context():
            assert GameSession.query.filter_by(campaign_id=cid, name='Calendar planned session').count() == 1

        calendar.locator('[data-oneshots]').click()
        shot = dialog.locator('[data-oneshot-form]')
        expect(shot).to_be_visible()
        shot.locator('[name=name]').fill('Browser One-Shot')
        shot.locator('[name=first_local]').fill(first)
        shot.locator('[name=timezone]').fill('UTC')
        shot.locator('[type=submit]').click()
        expect(dialog.get_by_role('link', name='Browser One-Shot')).to_be_visible()
        with app.app_context():
            marker = CalendarOneShot.query.filter_by(user_id=uid).one()
            assert db.session.get(Campaign, marker.campaign_id).name == 'Browser One-Shot'
            assert db.session.get(GameSession, marker.session_id).name == 'Browser One-Shot'
            assert CalendarNote.query.filter_by(user_id=uid, deleted_at=None, reminder_state='dismissed').count() == 1
            assert CalendarNote.query.filter_by(user_id=uid, deleted_at=None).count() == 1
        proof('review')
        dialog.press('Escape')
        expect(calendar.locator('[data-oneshots]')).to_be_focused()
        assert page.evaluate('document.documentElement.scrollWidth') <= width + 1
        assert not errors, errors
        browser.close()
