"""Normal UI journeys for movable windows, tokens, initiative and shared rooms."""
import os
import base64
from pathlib import Path
import pytest
from tests.test_personal_actions_browser import action_site


def dismiss_windows(page):
    for _ in range(12):
        if not page.locator('.play-window:visible').count():
            return
        page.keyboard.press('Escape')


@pytest.mark.parametrize('role,width,engine', [('player',1440,'chromium'), ('dm',390,'chromium'), ('player',390,'firefox')])
def test_windows_restore_and_token_menu_upload_and_library(action_site, role, width, engine):
    from playwright.sync_api import sync_playwright, expect
    app, origin, info = action_site
    from vtt.extensions import db
    from vtt.models import User, Campaign
    with app.app_context():
        for user_id in [info['player_id'], db.session.get(Campaign, info['campaign']).owner_id]:
            db.session.get(User, user_id).storage_quota_gb = 1
        db.session.commit()
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(headless=True, args=['--no-sandbox'] if engine == 'chromium' else [])
        context = browser.new_context(viewport={'width':width, 'height':1000}, reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(15000);errors=[]
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat={role}")
        expect(page.locator('#dock-tokenWidget')).to_be_visible()
        expect(page.locator('.tool-btn[data-tool="token"]')).to_have_count(0)
        page.locator('#dock-tokenWidget').click()
        window=page.locator('#window-tokenWidget');expect(window).to_be_visible()
        expect(page.locator('#btnTokenUpload')).to_be_visible()
        page.locator('#dock-turnOrderWidget').click()
        expect(page.locator('#window-turnOrderWidget')).to_be_visible()
        expect(window).to_be_visible()
        page.keyboard.press('Escape')
        head=window.locator('.play-window-head strong');box=head.bounding_box()
        page.mouse.move(box['x']+20,box['y']+15);page.mouse.down()
        page.mouse.move(min(width-100,box['x']+90),box['y']+145,steps=8);page.mouse.up()
        moved=window.bounding_box()
        window.locator('.play-window-head button').click();page.locator('#dock-tokenWidget').click()
        again=window.bounding_box();assert abs(again['x']-moved['x'])<2 and abs(again['y']-moved['y'])<2
        page.reload();page.locator('#dock-tokenWidget').click();again=window.bounding_box()
        assert abs(again['x']-moved['x'])<2 and abs(again['y']-moved['y'])<2, page.evaluate("Object.fromEntries(Object.entries(localStorage).filter(([key])=>key.startsWith('vtt:windows:')))")
        dismiss_windows(page)
        page.locator(f".token-marker[data-token-id='{info['token']}']").click()
        expect(window).to_be_visible()
        if role == 'player' and width == 1440:
            png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aQ3sAAAAASUVORK5CYII=')
            page.locator('#tokenImageFile').set_input_files({'name':'token.png','mimeType':'image/png','buffer':png})
            expect(page.locator('#activityLog')).to_contain_text('Token-Bild gesetzt')
        page.locator('#btnSaveTokenTemplate').click()
        expect(page.locator('#tokenLibraryList [data-template-id]')).to_have_count(1)
        item=page.locator('#tokenLibraryList [data-template-id]')
        item.get_by_role('button',name='Bearbeiten',exact=True).click()
        item.locator('input').first.fill('Reusable browser token')
        item.get_by_role('button',name='Speichern',exact=True).click()
        expect(item).to_contain_text('Reusable browser token')
        item.get_by_role('button',name='Platzieren',exact=True).click()
        expect(window).not_to_be_visible()
        viewport=page.locator('#mapViewport').bounding_box(); world=page.locator('#mapWorld').bounding_box()
        page.mouse.click(max(viewport['x']+20,world['x']+min(200,world['width']-25)),max(viewport['y']+20,world['y']+min(160,world['height']-25)))
        try:
            expect(page.locator('#tokenCreatePanel')).to_be_visible()
        except AssertionError:
            page.screenshot(path='/app/docs/proofs/session-feedback-2026-11-16/debug-placement.png')
            raise
        expect(page.locator('#tokenCreateName')).to_have_value('Reusable browser token')
        page.locator('#btnTokenCreateConfirm').click()
        expect(page.locator('.token-marker')).to_have_count(2)
        if role == 'player' and width == 1440:
            page.locator('#dock-tokenWidget').click()
            page.locator('#tokenUploadFile').set_input_files({'name':'direct-token.png','mimeType':'image/png','buffer':png})
            expect(page.locator('#tokenUploadStatus')).to_contain_text('Tokenbild geladen')
            page.locator('#btnPlaceNewToken').click()
            world = page.locator('#mapWorld').bounding_box()
            page.mouse.click(world['x']+300,world['y']+200)
            expect(page.locator('#tokenCreateImageLabel')).to_contain_text('direct-token.png')
            page.locator('#tokenCreateName').fill('Direct menu upload')
            page.locator('#btnTokenCreateConfirm').click()
            expect(page.locator('.token-marker')).to_have_count(3)
        page.locator('#btnBeyond20Setup').click();expect(page.locator('#window-beyond20')).to_be_visible()
        expect(page.frame_locator('#window-beyond20 iframe').locator('#beyond20CopyBtn')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth')<=width
        if role=='player':
            assert not page.evaluate('Boolean(window.PlayDMSurface)')
            expect(page.locator('#tokenLayersWidget,#btnStartCombat')).to_have_count(0)
        destination=Path(os.environ.get('VTT_SESSION_FEEDBACK_SHOTS','/tmp/session-feedback-shots'));destination.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(destination/f'{role}-{engine}-{width}.png'))
        assert not errors,errors
        context.close();browser.close()


def test_selected_beyond20_initiative_and_campaign_room_reach_conversations(action_site):
    from playwright.sync_api import sync_playwright, expect
    from vtt.extensions import db
    from vtt.models import TokenState
    app,origin,info=action_site
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(15000);errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player")
        page.locator(f".token-marker[data-token-id='{info['token']}']").click()
        page.evaluate("""() => document.dispatchEvent(new CustomEvent('Beyond20_RenderedRoll',{detail:[{
            title:'Initiative', character:'Browser caster', request:{type:'initiative',character:{name:'Browser caster'}},
            attack_rolls:[{formula:'1d20+3',total:2,discarded:true,parts:[]},{formula:'1d20+3',total:18,discarded:false,parts:[]}]
        }]}))""")
        expect(page.locator('#tokenList')).to_contain_text('Hero')
        expect(page.locator('#beyond20Status')).to_contain_text('Wurf an dieser Sitzung angekommen')
        with app.app_context():
            assert db.session.get(TokenState,info['token']).initiative==18
        dismiss_windows(page)
        page.locator('#btnChatToggle').click();page.locator('#chatInput').fill('Same campaign conversation')
        page.locator('#btnSendChat').click();expect(page.locator('#campaignRoomLog')).to_contain_text('Same campaign conversation')
        conversation=context.new_page();conversation.goto(origin+f"/conversations?campaign_id={info['campaign']}")
        expect(conversation.locator('#conversationHistory')).to_contain_text('Same campaign conversation')
        expect(conversation.locator('[data-room-id]')).to_have_count(1)
        conversation.locator('#privateMessage').fill('Reply from conversations');conversation.locator('#privateSend').click()
        expect(page.locator('#campaignRoomLog')).to_contain_text('Reply from conversations',timeout=10000)
        assert not errors,errors
        context.close();browser.close()
