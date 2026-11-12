"""Real DM/Firefox private conversation, acknowledged retry, reload and revocation."""
import json
import pytest
from playwright.sync_api import sync_playwright,expect
from tests.test_personal_actions_browser import action_site  # noqa:F401
from tests.test_presentation_browser import preferences
from vtt.extensions import db
from vtt.models import CampaignMember,PrivateMessage

@pytest.mark.parametrize('width,language,theme',[(1440,'de','paper'),(390,'en','night')])
def test_hub_chat_roundtrip_lost_ack_retry_and_revocation(action_site,width,language,theme):
    app,origin,info=action_site
    with sync_playwright() as p:
        chrome=p.chromium.launch(headless=True,args=['--no-sandbox']);ff=p.firefox.launch(headless=True)
        dc=chrome.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        pc=ff.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
        for context,role in ((dc,'dm'),(pc,'player')):
            preferences(context,theme=theme,language=language)
            context.add_cookies([{'name':'access_token_cookie','value':info[role+'_auth'],'url':origin,'httpOnly':True}])
        dm=dc.new_page();player=pc.new_page();errors=[]
        for page in (dm,player):page.set_default_timeout(30000);page.on('pageerror',lambda error:errors.append(str(error)))
        dm.goto(f"{origin}/campaigns?campaign_id={info['campaign']}")
        member=dm.locator(f'[data-campaign-member="{info["player_id"]}"]')
        expect(member.locator('a[href*="/character-sheet"]')).to_be_visible(timeout=30000)
        member.locator('[data-member-chat]').click()
        expect(dm.locator('#privateMessage')).to_be_visible(timeout=30000)
        cid=int(dm.url.split('id=')[-1])
        expect(dm.locator('a[href="/conversations"]')).to_have_attribute('aria-current','page')
        text='<b>Privat und nur als Text</b>'
        dm.locator('#privateMessage').fill(text);dm.locator('#privateSend').click()
        expect(dm.locator('#conversationHistory p')).to_have_text([text],timeout=30000)
        expect(dm.locator('#conversationHistory b')).to_have_count(0)
        player.goto(origin+'/campaigns');player.locator('a[href="/conversations"]').click()
        player.locator(f'[data-conversation-id="{cid}"]').click()
        expect(player.locator('#conversationHistory p')).to_have_text([text],timeout=30000)
        player.locator('#privateMessage').fill('Firefox antwortet');player.locator('#privateMessage').press('Enter')
        expect(dm.locator('#conversationHistory p')).to_have_text([text,'Firefox antwortet'],timeout=20000)
        player.reload();expect(player.locator('#conversationHistory p')).to_have_text([text,'Firefox antwortet'],timeout=30000)
        # The server commits the first POST, but its response is lost. Hold reads
        # briefly so the deliberate retry exercises the retained UUID itself.
        held=[]
        read_pattern=f'**/api/private-conversations/{cid}?*'
        dm.route(read_pattern,lambda route:held.append(route))
        attempts=[]
        def lose_ack(route):
            attempts.append(route.request.post_data_json)
            if len(attempts)==1:
                response=route.fetch();assert response.status==201;route.abort()
            else:route.continue_()
        dm.route(f'**/api/private-conversations/{cid}/messages',lose_ack)
        dm.locator('#privateMessage').fill('Einmal trotz verlorener Bestätigung');dm.locator('#privateSend').click()
        expect(dm.locator('#conversationStatus')).to_contain_text('Senden fehlgeschlagen' if language=='de' else 'Sending failed',timeout=30000)
        expect(dm.locator('#privateMessage')).to_have_attribute('readonly','')
        with dm.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/messages')) as replay:
            dm.locator('#privateSend').click()
        assert replay.value.status==200 and replay.value.json()['replayed'] is True
        assert len(attempts)==2 and attempts[0]==attempts[1]
        expect(dm.locator('#conversationHistory p')).to_have_count(3)
        for route in held:
            try:route.continue_()
            except Exception:pass
        dm.unroute(read_pattern);dm.unroute(f'**/api/private-conversations/{cid}/messages')
        with app.app_context():
            assert PrivateMessage.query.filter_by(conversation_id=cid).count()==3
            CampaignMember.query.filter_by(campaign_id=info['campaign'],user_id=info['player_id']).one().status='kicked';db.session.commit()
        expect(player.locator('#conversationTitle')).to_have_text('Gespräch nicht verfügbar' if language=='de' else 'Conversation unavailable',timeout=20000)
        expect(player.locator('#conversationHistory li')).to_have_count(0)
        expect(player.locator('#privateMessage')).to_be_hidden()
        dm.reload();expect(dm.locator('#conversationHistory p')).to_have_count(3,timeout=30000)
        expect(dm.locator('#conversationStatus')).to_contain_text('schreibgeschützt' if language=='de' else 'read-only')
        expect(dm.locator('#privateMessage')).to_be_hidden()
        for page in (dm,player):
            assert page.evaluate('document.documentElement.scrollWidth')<=width+1
            assert not page.evaluate('Boolean(window.PlayDMSurface)')
        assert not errors,errors
        chrome.close();ff.close()

def test_switch_ignores_old_reply_and_hidden_page_stops_polling(action_site):
    from vtt.models import Campaign,User,Role,PrivateConversation
    from uuid import uuid4
    app,origin,info=action_site
    with app.app_context():
        owner=db.session.get(Campaign,info['campaign']).owner_id
        peer=User(username='second-peer',email='second-peer@example.test',role_id=Role.query.filter_by(name='Player').one().id,
                  password_hash='unused',is_active=True,account_state='active');db.session.add(peer);db.session.flush()
        db.session.add(CampaignMember(campaign_id=info['campaign'],user_id=peer.id,campaign_role='PLAYER',status='active'))
        ids=[]
        for recipient,text in ((info['player_id'],'First private conversation'),(peer.id,'Second private conversation')):
            low,high=sorted((owner,recipient));c=PrivateConversation(campaign_id=info['campaign'],participant_low_id=low,participant_high_id=high)
            db.session.add(c);db.session.flush();db.session.add(PrivateMessage(conversation_id=c.id,author_user_id=recipient,client_event_id=str(uuid4()),content=text));ids.append(c.id)
        db.session.commit()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':390,'height':1000})
        context.add_cookies([{'name':'access_token_cookie','value':info['dm_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(20000);page.goto(f'{origin}/conversations?id={ids[0]}')
        expect(page.locator('#conversationHistory p')).to_have_text(['First private conversation'])
        held=[]
        def delay(route):held.append((route,route.fetch()))
        page.route(f'**/api/private-conversations/{ids[0]}?after=*',delay)
        with page.expect_request(lambda r:r.method=='GET' and f'/{ids[0]}?after=' in r.url):pass
        page.locator(f'[data-conversation-id="{ids[1]}"]').click()
        expect(page.locator('#conversationHistory p')).to_have_text(['Second private conversation'])
        assert held
        for route,response in held:
            try:route.fulfill(response=response)
            except Exception:pass  # an aborted old request is also correctly discarded
        expect(page.locator('#conversationHistory p')).to_have_text(['Second private conversation'])
        requests=[];page.on('request',lambda r:requests.append(r.url) if f'/private-conversations/{ids[1]}' in r.url else None)
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
        page.wait_for_timeout(5500);assert requests==[]
        with page.expect_request(lambda r:f'/private-conversations/{ids[1]}' in r.url):
            page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))")
        expect(page.locator('#conversationHistory p')).to_have_text(['Second private conversation'])
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
        expect(page.locator('#conversationHistory li')).to_have_count(0)
        expect(page.locator('#privateMessage')).to_be_hidden()
        with page.expect_request(lambda r:f'/private-conversations/{ids[1]}' in r.url):
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        expect(page.locator('#conversationHistory p')).to_have_text(['Second private conversation'])
        browser.close()
