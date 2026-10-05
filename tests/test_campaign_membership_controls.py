"""Self-leave and DM removal from the current campaign hub."""
import os
from pathlib import Path

import pytest

from vtt.extensions import db, socketio
from vtt.models import Campaign, CampaignMap, CampaignMember, Character, GameSession, ModerationAction, User
from test_character_campaign_feedback import feedback_app, feedback_site, activate, client_for


def test_leave_revokes_membership_and_preserves_characters_and_other_campaigns(feedback_app):
    app, d = feedback_app; activate(app, d)
    player, dm = [client_for(app, d, who) for who in ['player','dm']]
    cid, uid = d['campaign_id'], d['users']['player']
    with app.app_context():
        db.session.get(Character,d['character_id']).campaign_id=cid
        db.session.add(CampaignMember(campaign_id=d['private_id'],user_id=uid,campaign_role='Player',status='active'))
        db.session.commit()
    response=player.post(f'/api/campaigns/{cid}/leave')
    assert response.status_code==200 and response.json['status']=='left'
    assert player.get(f'/api/campaigns/{cid}').status_code==403
    assert player.get(f'/api/campaigns/{cid}/members').status_code==403
    assert player.get(f'/api/characters/{d["dm_character_id"]}/sheet').status_code==403
    assert player.get('/api/characters/shared').json==[]
    assert player.get(f'/api/characters/{d["character_id"]}/sheet').status_code==200
    assert player.get(f'/api/campaigns/{d["private_id"]}').status_code==200
    assert cid not in [c['id'] for c in player.get('/api/campaigns/mine').json['campaigns']]
    assert uid not in [m['user_id'] for m in dm.get(f'/api/campaigns/{cid}').json['members']]
    assert uid not in [m['user_id'] for m in dm.get(f'/api/campaigns/{cid}/members').json['members']]
    with app.app_context():
        assert db.session.get(Character,d['character_id']).deleted_at is None
        assert CampaignMember.query.filter_by(campaign_id=cid,user_id=uid).one().status=='left'
    # Leaving voluntarily allows a fresh request, but never silently restores access.
    assert player.post(f'/api/campaigns/{cid}/join-requests').status_code==202
    assert player.get(f'/api/campaigns/{cid}').status_code==403


@pytest.mark.parametrize('status',[None,'pending','invited','left','kicked'])
def test_non_active_members_cannot_leave(feedback_app,status):
    app,d=feedback_app
    if status: activate(app,d,status)
    assert client_for(app,d,'player').post(f'/api/campaigns/{d["campaign_id"]}/leave').status_code==403


def test_owner_and_unusable_accounts_cannot_leave(feedback_app):
    app,d=feedback_app;activate(app,d)
    assert client_for(app,d,'dm').post(f'/api/campaigns/{d["campaign_id"]}/leave').status_code==409
    with app.app_context():
        db.session.get(User,d['users']['player']).is_active=False;db.session.commit()
    assert client_for(app,d,'player').post(f'/api/campaigns/{d["campaign_id"]}/leave').status_code in {401,403,404}


def test_kick_uses_existing_permission_and_audit_rules(feedback_app):
    app,d=feedback_app;activate(app,d)
    player,dm=[client_for(app,d,who) for who in ['player','dm']]
    url=f'/api/campaigns/{d["campaign_id"]}/moderation/actions'
    assert player.post(url,json={'action_type':'kick','subject_user_id':d['users']['dm']}).status_code==403
    assert dm.post(url,json={'action_type':'kick','subject_user_id':d['users']['dm']}).status_code==400
    assert dm.post(url,json={'action_type':'kick','subject_user_id':d['users']['player']}).status_code==201
    assert player.get(f'/api/campaigns/{d["campaign_id"]}').status_code==403
    with app.app_context():
        assert CampaignMember.query.filter_by(campaign_id=d['campaign_id'],user_id=d['users']['player']).one().status=='kicked'
        assert ModerationAction.query.filter_by(campaign_id=d['campaign_id'],subject_user_id=d['users']['player'],action_type='kick').count()==1
        assert db.session.get(Character,d['character_id']).deleted_at is None


def add_session(app,d,campaign_id):
    with app.app_context():
        m=CampaignMap(campaign_id=campaign_id,name='Exit map',width=100,height=100,created_by=d['users']['dm'])
        db.session.add(m);db.session.flush()
        s=GameSession(campaign_id=campaign_id,map_id=m.id,name='Exit session',status='in_progress')
        db.session.add(s);db.session.commit();return s.id


@pytest.mark.parametrize('action',['leave','kick'])
def test_leave_and_kick_disconnect_all_campaign_tabs_only(feedback_app,action):
    app,d=feedback_app;activate(app,d)
    cid=d['campaign_id'];sid=add_session(app,d,cid)
    other_sid=add_session(app,d,d['private_id'])
    with app.app_context():
        db.session.add(CampaignMember(campaign_id=d['private_id'],user_id=d['users']['player'],campaign_role='Player',status='active'));db.session.commit()
    player,dm=[client_for(app,d,who) for who in ['player','dm']]
    sockets=[socketio.test_client(app,flask_test_client=player) for _ in range(3)]
    owner_socket=socketio.test_client(app,flask_test_client=dm)
    try:
        for s in sockets[:2]+[owner_socket]:
            s.emit('session:join',{'campaign_id':cid,'session_id':sid});assert any(e['name']=='state:snapshot' for e in s.get_received())
        sockets[2].emit('session:join',{'campaign_id':d['private_id'],'session_id':other_sid});sockets[2].get_received()
        if action=='leave': response=player.post(f'/api/campaigns/{cid}/leave')
        else: response=dm.post(f'/api/campaigns/{cid}/moderation/actions',json={'action_type':'kick','subject_user_id':d['users']['player']})
        assert response.status_code in {200,201}
        assert all(not s.is_connected() for s in sockets[:2])
        assert sockets[2].is_connected() and owner_socket.is_connected()
        rejoin=socketio.test_client(app,flask_test_client=player);sockets.append(rejoin)
        rejoin.emit('session:join',{'campaign_id':cid,'session_id':sid})
        events=rejoin.get_received()
        assert not any(e['name']=='state:snapshot' for e in events)
        assert any(e['name']=='state:error' and e['args'][0]['code']=='forbidden' for e in events)
    finally:
        for s in sockets+[owner_socket]:
            if s.is_connected():s.disconnect()


def test_non_owner_dm_leave_disconnects_moderator_only_socket(feedback_app):
    app,d=feedback_app;activate(app,d)
    with app.app_context():
        CampaignMember.query.filter_by(campaign_id=d['campaign_id'],user_id=d['users']['player']).one().campaign_role='DM';db.session.commit()
    player=client_for(app,d,'player');s=socketio.test_client(app,flask_test_client=player)
    try:
        s.emit('mod:join',{'campaign_id':d['campaign_id']})
        assert any(e['name']=='mod:joined' for e in s.get_received())
        assert player.post(f'/api/campaigns/{d["campaign_id"]}/leave').status_code==200
        assert not s.is_connected()
    finally:
        if s.is_connected():s.disconnect()


@pytest.mark.parametrize('engine',['chromium','firefox'])
@pytest.mark.parametrize('width',[1440,390])
@pytest.mark.parametrize('action',['leave','kick'])
def test_hub_membership_buttons(feedback_app,feedback_site,engine,width,action):
    from playwright.sync_api import sync_playwright,expect
    app,d=feedback_app;activate(app,d)
    origin,_=feedback_site
    with sync_playwright() as p:
        browser=getattr(p,engine).launch(**({'args':['--no-sandbox']} if engine=='chromium' else {}))
        contexts={};errors=[]
        for who in ['dm','player']:
            c=browser.new_context(viewport={'width':width,'height':1000 if width==1440 else 844},has_touch=width==390,reduced_motion='reduce')
            c.add_cookies([{'name':'access_token_cookie','value':d['tokens'][who],'url':origin}])
            page=c.new_page();page.set_default_timeout(8000);page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'{origin}/campaigns?campaign_id={d["campaign_id"]}');contexts[who]=page
        dm,player=contexts['dm'],contexts['player']
        expect(player.get_by_role('button',name='Kampagne verlassen',exact=True)).to_be_visible()
        expect(player.get_by_role('button',name='Spieler entfernen',exact=True)).to_have_count(0)
        expect(dm.get_by_role('button',name='Kampagne verlassen',exact=True)).to_have_count(0)
        expect(dm.locator(f'[data-campaign-member="{d["users"]["dm"]}"] [data-hub-action="kick-player"]')).to_have_count(0)
        actor=player if action=='leave' else dm
        button=actor.get_by_role('button',name='Kampagne verlassen' if action=='leave' else 'Spieler entfernen',exact=True)
        press=lambda:button.tap() if width==390 else button.click()
        actor.once('dialog',lambda dialog:dialog.dismiss());press()
        expect(button).to_be_enabled()
        assert player.context.request.get(f'{origin}/api/campaigns/{d["campaign_id"]}').status==200
        if os.environ.get('VTT_PROOF_DIR'):
            out=Path(os.environ['VTT_PROOF_DIR']);out.mkdir(parents=True,exist_ok=True)
            actor.screenshot(path=str(out/f'{action}-{engine}-{width}.png'))
        actor.once('dialog',lambda dialog:dialog.accept())
        with actor.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/leave' if action=='leave' else '/moderation/actions')) as response:press()
        assert response.value.status==(200 if action=='leave' else 201)
        if action=='leave':expect(actor).to_have_url(origin+'/campaigns')
        else:
            expect(dm.locator('[data-hub-membership-status]')).to_contain_text('wurde aus der Kampagne entfernt')
            expect(dm.locator(f'[data-campaign-member="{d["users"]["player"]}"]')).to_have_count(0)
        assert player.context.request.get(f'{origin}/api/campaigns/{d["campaign_id"]}').status==403
        browser.close();assert errors==[]
