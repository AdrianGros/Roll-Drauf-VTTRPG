"""Fresh campaign entry must not depend on a table context from an earlier visit."""

import re
import time

import pytest

from tests.play_shared import create_campaign, create_session
from tests.test_srd_sheet import site  # noqa: F401
from vtt.extensions import db
from vtt.models import GameSession, User


@pytest.mark.parametrize("engine,width,new_session,entry_context,fail_first_start", [
    ("chromium", 390, False, None, False),
    ("firefox", 1440, False, None, False),
    ("chromium", 1440, True, None, False),
    ("chromium", 1440, False, "player", False),
    ("chromium", 1440, False, "other_session", False),
    ("chromium", 1440, True, None, True),
])
def test_solo_dm_starts_from_hub_without_map_or_existing_context(
        site, engine, width, new_session, entry_context, fail_first_start):
    from playwright.sync_api import expect, sync_playwright

    app, origin, info = site
    with app.app_context():
        owner = db.session.get(User, info["user_id"])
        campaign = create_campaign(owner, "Fresh solo campaign")
        campaign_id = campaign.id
        other_id = create_session(campaign, "Unused table context").id if entry_context == "other_session" else None
        session_id = None
        if not new_session:
            session_id = create_session(campaign, "Prepared without map or date").id

    with sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch(headless=True,
            **({"args": ["--no-sandbox"]} if engine == "chromium" else {}))
        context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        context.add_cookies([{"name": "access_token_cookie", "value": info["token"],
                             "url": origin, "httpOnly": True}])
        page = context.new_page()
        page.set_default_timeout(15000)
        errors, starts, creates = [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def record(request):
            if request.method != "POST":
                return
            if request.url.endswith("/start"):
                starts.append(request.url)
            if request.url == f"{origin}/api/campaigns/{campaign_id}/sessions":
                creates.append(request.url)

        page.on("request", record)

        failed = False

        def latency(route):
            nonlocal failed
            if route.request.method == "POST" and (route.request.url.endswith("/start")
                    or route.request.url == f"{origin}/api/campaigns/{campaign_id}/sessions"):
                time.sleep(0.25)
                if fail_first_start and not failed and route.request.url.endswith("/start"):
                    failed = True
                    route.fulfill(status=503, json={"error": "Start temporarily unavailable"})
                    return
            route.continue_()

        page.route("**/api/**", latency)
        page.goto(f"{origin}/campaigns?campaign_id={campaign_id}")
        action = "new-session" if new_session else "start-session"
        button = page.locator(f'[data-hub-action="{action}"]').first
        expect(button).to_be_visible()
        if entry_context:
            page.evaluate('''async ({campaign, session, mode}) => {
                await Auth.ensureTableContext(campaign, session, mode, true);
            }''', {"campaign": campaign_id, "session": other_id or session_id,
                   "mode": "player" if entry_context == "player" else "dm"})
        button.scroll_into_view_if_needed()
        box = button.bounding_box()
        page.mouse.dblclick(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, delay=40)
        if fail_first_start:
            retry = page.locator('[data-hub-action="start-session"]')
            expect(retry).to_be_enabled(timeout=20000)
            with app.app_context():
                assert GameSession.query.filter_by(campaign_id=campaign_id).count() == 1
            retry.click()
        expect(page).to_have_url(re.compile(r"/play\?"))
        expect(page.locator("body")).to_have_attribute("data-table-seat", "dm", timeout=20000)
        expect(page.locator("#btnInitStack")).to_have_count(1)
        assert len(starts) == 1 + int(fail_first_start), starts
        assert len(creates) == int(new_session), creates
        with app.app_context():
            sessions = GameSession.query.filter_by(campaign_id=campaign_id).all()
            assert len(sessions) == 1 + int(other_id is not None)
            started = [session for session in sessions if session.status == "in_progress"]
            assert len(started) == 1
            assert started[0].started_at is not None
            assert started[0].map_id is None and started[0].scheduled_at is None
        page.reload()
        expect(page.locator("body")).to_have_attribute("data-table-seat", "dm", timeout=20000)
        assert not errors, errors
        browser.close()
