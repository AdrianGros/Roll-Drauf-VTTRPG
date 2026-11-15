"""DM marquee selection and Ctrl+C / Ctrl+V of tokens on the play table, through real input."""
from playwright.sync_api import sync_playwright, expect

from tests.play_shared import create_token
from tests.test_personal_actions_browser import action_site  # noqa: F401
from vtt.extensions import db
from vtt.models import Campaign, GameSession, TokenState
from vtt.play.service import ensure_session_state


def client_point(page, x, y):
    box = page.locator('#mapWorld').bounding_box()
    width = float(page.locator('#mapWorld').get_attribute('data-map-width'))
    height = float(page.locator('#mapWorld').get_attribute('data-map-height'))
    return box['x'] + x * box['width'] / width, box['y'] + y * box['height'] / height


def world_point(page, client_x, client_y):
    box = page.locator('#mapWorld').bounding_box()
    width = float(page.locator('#mapWorld').get_attribute('data-map-width'))
    return (client_x - box['x']) * width / box['width'], (client_y - box['y']) * width / box['width']


def tokens(app, info):
    with app.app_context():
        db.session.expire_all()
        return TokenState.query.filter_by(game_session_id=info['session']).order_by(TokenState.id).all()


def test_dm_marquee_copy_and_paste_tokens_at_the_pointer(action_site):
    app, origin, info = action_site
    with app.app_context():
        campaign = db.session.get(Campaign, info['campaign'])
        session = db.session.get(GameSession, info['session'])
        state = ensure_session_state(campaign, session)
        for name, x in (('Goblin', 140), ('Goblin 2', 210)):
            token = create_token(campaign, session, state, campaign.owner_id, name=name, token_type='monster', x=x, y=140)
            token.metadata_json = {'position_mode': 'pixel', 'image_url': '/static/icons/icon-maps-compass.svg',
                                   'conditions': ['poisoned']}
            token.hp_max, token.hp_current = 7, 2
        db.session.commit()
    before = {t.id for t in tokens(app, info)}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        ctx.add_cookies([{'name': 'access_token_cookie', 'value': info['dm_auth'], 'url': origin, 'httpOnly': True}])
        page = ctx.new_page()
        page.set_default_timeout(30000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=dm")
        expect(page.locator('#mapWorld')).to_have_attribute('data-has-map', 'true')
        expect(page.locator('.token-marker')).to_have_count(3)
        # Bootstrap painting precedes context renewal and the initial socket snapshot.
        # Wait for room entry before measuring markers that the snapshot replaces.
        expect(page.locator('#presenceRoster')).to_contain_text('action-dm')
        page.locator('[data-tool=select]').click()
        first = page.locator('.token-marker', has_text='Goblin').first
        first.scroll_into_view_if_needed()
        a = first.bounding_box()
        b = page.locator('.token-marker').nth(2).bounding_box()
        # Marquee around both goblins only (the player's hero sits elsewhere), dragged from the
        # lower right to the upper left; a partly covered token counts as selected.
        page.mouse.move(b['x'] + b['width'] + 12, b['y'] + b['height'] + 12)
        page.mouse.down()
        page.mouse.move(b['x'], b['y'], steps=4)
        page.mouse.move(max(2, a['x'] + 4), a['y'] - 12, steps=4)
        page.mouse.up()
        expect(page.locator('.token-marker.selected')).to_have_count(2)
        page.keyboard.press('Control+c')
        target = (max(40, a['x'] + 40), a['y'] + 200)
        page.mouse.move(*target)
        page.keyboard.press('Control+v')
        expect(page.locator('.token-marker')).to_have_count(5)
        created = [t for t in tokens(app, info) if t.id not in before]
        assert len(created) == 2
        names = sorted(t.name for t in created)
        assert names == ['Goblin 3', 'Goblin 4'], names
        grid = int(page.locator('#mapWorld').get_attribute('data-grid-size') or 70)
        lefts = sorted(t.x for t in created)
        # Same layout as the originals (70 px apart), snapped to the grid at the pointer.
        assert lefts[1] - lefts[0] == 70 and all(t.y == created[0].y for t in created)
        # The group snaps to the grid; tokens keep their original spacing inside it.
        assert min(lefts) % grid == 0 and created[0].y % grid == 0
        pointer = world_point(page, *target)
        assert abs(min(lefts) - pointer[0]) <= grid and abs(created[0].y - pointer[1]) <= grid
        for t in created:
            assert t.token_type == 'monster' and t.hp_max == 7 and t.hp_current == 7
            assert t.metadata_json == {'image_url': '/static/icons/icon-maps-compass.svg', 'position_mode': 'pixel'}
            assert t.character_id is None
        # A second paste lands at the pointer again with the next numbers.
        page.mouse.move(a['x'] + 260, a['y'] + 120)
        page.keyboard.press('Control+v')
        expect(page.locator('.token-marker')).to_have_count(7)
        assert sorted(t.name for t in tokens(app, info) if t.id not in before)[-2:] == ['Goblin 5', 'Goblin 6']
        # A single clicked token copies too; Ctrl+V while typing in chat leaves tokens alone.
        page.locator('.token-marker', has_text='Goblin 3').first.click()
        page.keyboard.press('Control+c')
        page.locator('#btnChatToggle').click()
        page.locator('#chatInput').fill('kein Token')
        page.locator('#chatInput').press('Control+v')
        page.wait_for_timeout(500)
        expect(page.locator('.token-marker')).to_have_count(7)
        assert not errors, errors
        ctx.close()
        browser.close()


def test_player_surface_has_no_token_clipboard(action_site):
    app, origin, info = action_site
    before = len(tokens(app, info))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        ctx.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
        page = ctx.new_page()
        page.set_default_timeout(30000)
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player")
        expect(page.locator('.token-marker')).to_have_count(1)
        page.locator('.token-marker').first.click()
        page.keyboard.press('Control+c')
        page.mouse.move(*client_point(page, 420, 420))
        page.keyboard.press('Control+v')
        page.wait_for_timeout(800)
        assert len(tokens(app, info)) == before
        assert page.evaluate('() => typeof window.PlayDMSurface') == 'undefined'
        ctx.close()
        browser.close()
