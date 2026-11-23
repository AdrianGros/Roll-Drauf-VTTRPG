"""A discarded mobile tab must not silently demote the DM to a Player seat."""
from playwright.sync_api import sync_playwright, expect

from tests.test_personal_actions_browser import action_site  # noqa: F401
from vtt.extensions import db
from vtt.models import TableContext


def modes(app, user_id):
    with app.app_context():
        db.session.expire_all()
        return [c.mode for c in TableContext.query.filter_by(user_id=user_id).order_by(TableContext.id)]


def lose_tab_storage(page):
    # What a mobile browser does to a discarded tab: the page and its sessionStorage are gone.
    page.evaluate('() => { sessionStorage.clear(); }')
    page.reload()
    expect(page.locator('#mapWorld')).to_have_attribute('data-has-map', 'true')


def test_dm_seat_survives_a_discarded_tab_and_an_explicit_player_seat_stays(action_site):
    app, origin, info = action_site
    with app.app_context():
        from vtt.models import Campaign
        owner_id = db.session.get(Campaign, info['campaign']).owner_id
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 360, 'height': 780}, is_mobile=True, has_touch=True)
        ctx.add_cookies([{'name': 'access_token_cookie', 'value': info['dm_auth'], 'url': origin, 'httpOnly': True}])
        page = ctx.new_page()
        page.set_default_timeout(30000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=dm")
        expect(page.locator('#dock-tokenLayersWidget')).to_be_attached()
        lose_tab_storage(page)
        expect(page.locator('#dock-tokenLayersWidget')).to_be_attached()
        assert modes(app, owner_id)[-1] == 'dm', modes(app, owner_id)
        # The owner switches to a Player seat on purpose, through the menu: that choice is remembered too.
        page.locator('#btnTableMore').click();page.locator('#btnBack').click()
        with page.expect_navigation():
            page.locator('#appMenuSeat').click()
        expect(page.locator('#mapWorld')).to_have_attribute('data-has-map', 'true')
        expect(page.locator('#dock-tokenLayersWidget')).to_have_count(0)
        lose_tab_storage(page)
        expect(page.locator('#dock-tokenLayersWidget')).to_have_count(0)
        assert modes(app, owner_id)[-1] == 'player'
        assert not errors, errors
        ctx.close()
        browser.close()


def test_a_player_with_a_forged_dm_memory_still_enters_as_player(action_site):
    app, origin, info = action_site
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 360, 'height': 780}, is_mobile=True, has_touch=True)
        ctx.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
        ctx.add_init_script(f"localStorage.setItem('vtt.table.seat.v1.{info['campaign']}.{info['session']}', 'dm')")
        page = ctx.new_page()
        page.set_default_timeout(30000)
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}")
        expect(page.locator('#mapWorld')).to_have_attribute('data-has-map', 'true')
        expect(page.locator('.token-marker')).to_have_count(1)
        expect(page.locator('#dock-tokenLayersWidget')).to_have_count(0)
        assert set(modes(app, info['player_id'])) == {'player'}
        ctx.close()
        browser.close()
