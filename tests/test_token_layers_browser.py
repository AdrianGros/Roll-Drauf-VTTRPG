"""Real DM layer selection, grouped visibility changes and isolated Player delivery."""
import pytest
from playwright.sync_api import sync_playwright, expect

from tests.play_shared import create_token
from tests.test_personal_actions_browser import action_site  # noqa: F401
from tests.test_playtable_token_clipboard_browser import client_point
from vtt.extensions import db
from vtt.models import Campaign, GameSession
from vtt.play.service import ensure_session_state


@pytest.mark.parametrize('engine', ['chromium', 'firefox'])
def test_dm_layers_group_reveal_hide_create_and_player_isolation(action_site, engine):
    app, origin, info = action_site
    with app.app_context():
        campaign = db.session.get(Campaign, info['campaign'])
        session = db.session.get(GameSession, info['session'])
        for name, x in [('Goblin', 140), ('Goblin 2', 210)]:
            token = create_token(campaign, session, ensure_session_state(campaign, session), campaign.owner_id,
                                 name=name, token_type='monster', x=x, y=140)
            token.metadata_json = {'position_mode': 'pixel'}
            token.visibility = 'dm_only'
        db.session.commit()
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, args=['--no-sandbox'] if engine == 'chromium' else [])
        dm_context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        player_context = browser.new_context(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
        dm_context.add_cookies([{'name': 'access_token_cookie', 'value': info['dm_auth'], 'url': origin, 'httpOnly': True}])
        player_context.add_cookies([{'name': 'access_token_cookie', 'value': info['player_auth'], 'url': origin, 'httpOnly': True}])
        dm, player = dm_context.new_page(), player_context.new_page()
        errors = []
        requests = []
        for page in (dm, player):
            page.set_default_timeout(30000)
            page.on('pageerror', lambda error: errors.append(str(error)))
        player.on('request', lambda request: requests.append(request.url))
        table = f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}"
        player.goto(table + '&seat=player')
        dm.goto(table + '&seat=dm')
        # A rendered bootstrap is earlier than the socket room join. Wait for both peers
        # before asserting delivery of a mutation made by the other browser.
        expect(dm.locator('#presenceRoster')).to_contain_text('action-player')
        expect(player.locator('#presenceRoster')).to_contain_text('action-dm')
        expect(dm.locator('.token-marker')).to_have_count(3)
        expect(player.locator('.token-marker')).to_have_count(1)
        expect(player.locator('#tokenLayersWidget, #tokenSelectionBar')).to_have_count(0)
        assert not any('play-dm.js' in url or 'play-token-layers-dm' in url for url in requests)
        expect(dm.locator('.token-inactive-layer')).to_have_count(2)
        if not dm.locator('#window-tokenWidget').is_visible(): dm.locator('#dock-tokenWidget').click()
        dm.locator('#dock-tokenLayersWidget').click()
        dm.locator('[data-token-layer=dm_only]').click()
        expect(dm.locator('[data-token-layer=dm_only]')).to_have_attribute('aria-pressed', 'true')
        dm.locator('#tokenCreatePanel').wait_for(state='hidden')
        while dm.locator('.play-window:visible').count(): dm.keyboard.press('Escape')
        goblins = dm.locator('.token-marker:not(.token-inactive-layer)')
        goblins.first.click()
        while dm.locator('.play-window:visible').count(): dm.keyboard.press('Escape')
        goblins.nth(1).click(modifiers=['Shift'])
        expect(dm.locator('#tokenSelectionCount')).to_have_text('2 ausgewählt')
        expect(dm.locator('.token-selection-group')).to_have_count(1)
        expect(dm.locator('#tokenSelectionGroups')).to_have_text('GOGoblin × 2')
        expect(dm.locator('.token-marker.selected')).to_have_count(2)
        dm.locator('[data-selection-layer=public]').click()
        expect(player.locator('.token-marker')).to_have_count(3)
        expect(dm.locator('#tokenSelectionBar')).to_be_hidden()
        # The move chooses the destination layer, allowing a deliberate selection to hide again.
        while dm.locator('.play-window:visible').count(): dm.keyboard.press('Escape')
        dm.locator('.token-marker', has_text='Goblin').first.click()
        while dm.locator('.play-window:visible').count(): dm.keyboard.press('Escape')
        dm.locator('.token-marker', has_text='Goblin 2').click(modifiers=['Shift'])
        dm.locator('[data-selection-layer=dm_only]').click()
        expect(player.locator('.token-marker')).to_have_count(1)
        player.reload()
        expect(player.locator('.token-marker')).to_have_count(1)
        # Reload resumes/rotates the context after initial painting; wait for that
        # asynchronous join before issuing an independent HTTP probe.
        expect(player.locator('#presenceRoster')).to_contain_text('action-dm')
        payload = player.evaluate('''async ({c,s}) => JSON.stringify(await Auth.makeAuthRequest(`/api/play/campaigns/${c}/sessions/${s}/bootstrap`))''', {'c': info['campaign'], 's': info['session']})
        assert 'Goblin' not in payload
        # Normal placement starts in the active hidden layer and remains hidden across reload.
        dm.locator('#dock-tokenWidget').click()
        dm.locator('#btnPlaceNewToken').click()
        dm.mouse.click(*client_point(dm, 490, 280))
        expect(dm.locator('#tokenCreatePanel')).to_be_visible()
        expect(dm.locator('#tokenCreateVisibility')).to_have_value('dm_only')
        dm.locator('#tokenCreateName').fill('Hidden reinforcement')
        dm.locator('#btnTokenCreateConfirm').click()
        expect(dm.locator('.token-marker')).to_have_count(4)
        expect(player.locator('.token-marker')).to_have_count(1)
        # Clipboard pastes into the currently selected layer, even after copying elsewhere.
        dm.locator('[data-tool=select]').click()
        while dm.locator('.play-window:visible').count(): dm.keyboard.press('Escape')
        dm.locator('.token-marker', has_text='Hidden reinforcement').click()
        dm.keyboard.press('Control+c')
        if not dm.locator('#window-tokenWidget').is_visible(): dm.locator('#dock-tokenWidget').click()
        dm.locator('#dock-tokenLayersWidget').click()
        dm.locator('[data-token-layer=public]').click()
        expect(dm.locator('#tokenSelectionBar')).to_be_hidden()
        dm.keyboard.press('Escape')
        dm.mouse.move(*client_point(dm, 700, 280))
        dm.keyboard.press('Control+v')
        expect(player.locator('.token-marker')).to_have_count(2)
        dm.reload()
        expect(dm.locator('.token-marker')).to_have_count(5)
        expect(dm.locator('.token-inactive-layer')).to_have_count(3)
        # Same owner in a separate Player tab never gains the layer surface or hidden state.
        restricted = dm_context.new_page()
        restricted.goto(table + '&seat=player')
        expect(restricted.locator('body')).to_have_attribute('data-table-seat', 'player')
        expect(restricted.locator('#tokenLayersWidget, #tokenSelectionBar')).to_have_count(0)
        expect(restricted.locator('.token-marker')).to_have_count(2)
        dm.reload()
        expect(dm.locator('body')).to_have_attribute('data-table-seat', 'dm')
        expect(dm.locator('.token-marker')).to_have_count(5)
        assert not errors, errors
        browser.close()
