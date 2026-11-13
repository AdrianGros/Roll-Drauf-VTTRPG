"""Real transports: personal actions, Firefox delivery and missed-roll recovery."""

from pathlib import Path
from threading import Thread

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.serving import make_server

from tests.play_shared import add_map, add_member, create_campaign, create_session, create_token
from tests.test_srd_creator_api import wizard_state
from tests.test_srd_sheet import QuietHandler
from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db, socketio
from vtt.models import Character, Role, TableContext, User
from vtt.models.role import init_default_roles
from vtt.play.service import ensure_session_state
from vtt.rules_content.creator_drafts import character_values
from vtt.rules_content.creator_rules import evaluate, load_creator_data


@pytest.fixture
def action_site(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path}/actions.db')
    monkeypatch.setattr(TestingConfig, 'CORS_ORIGINS', '*')
    monkeypatch.setattr(TestingConfig, 'SOCKETIO_ASYNC_MODE', 'threading', raising=False)
    app = create_app('testing')
    with app.app_context():
        db.create_all(); init_default_roles(db.session)
        role = Role.query.filter_by(name='Player').first()
        owner = User(username='action-dm', email='action-dm@example.test', role_id=role.id, is_active=True)
        player = User(username='action-player', email='action-player@example.test', role_id=role.id, is_active=True)
        for user in (owner, player):
            user.set_password('Test-only-123!'); db.session.add(user)
        db.session.commit()
        campaign = create_campaign(owner, 'Hotbar browser')
        add_member(campaign, player)
        map_ = add_map(campaign, owner)
        session = create_session(campaign, status='in_progress', map_id=map_.id)
        other = create_session(campaign, 'Isolated session', status='in_progress', map_id=map_.id)
        data = load_creator_data(); state = wizard_state(data, 'Browser caster')
        char = Character(user_id=player.id, **character_values(data, state, evaluate(data,state), draft_id=1,
                          finalized_at='2026-11-11T08:00:00Z'))
        char.campaign_id = campaign.id
        db.session.add(char);db.session.commit()
        token = create_token(campaign, session, ensure_session_state(campaign,session), player.id)
        token.character_id = char.id;db.session.commit()
        info = {'campaign':campaign.id,'session':session.id,'other_session':other.id,'character':char.id,
                'token':token.id,'player_id':player.id,'player_auth':create_access_token(identity=str(player.id)),
                'dm_auth':create_access_token(identity=str(owner.id))}
    server=make_server('127.0.0.1',0,app,threaded=True,request_handler=QuietHandler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        yield app,f'http://127.0.0.1:{server.server_port}',info
    finally:
        server.shutdown();thread.join(timeout=5);server.server_close()
        with app.app_context():db.session.remove();db.engine.dispose()


@pytest.mark.parametrize('dm_engine', ['firefox','chromium'])
def test_personal_bar_and_firefox_reconnect_delivery(action_site, dm_engine):
    from playwright.sync_api import sync_playwright, expect
    app,origin,info=action_site
    with sync_playwright() as p:
        player_browser=p.firefox.launch(headless=True)
        dm_browser=getattr(p,dm_engine).launch(headless=True,args=['--no-sandbox'] if dm_engine=='chromium' else [])
        player_context=player_browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        dm_context=dm_browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        player_context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        dm_context.add_cookies([{'name':'access_token_cookie','value':info['dm_auth'],'url':origin,'httpOnly':True}])
        player=player_context.new_page();dm=dm_context.new_page();isolated=dm_context.new_page()
        errors=[]
        for page in (player,dm,isolated):
            page.set_default_timeout(30000);page.on('pageerror',lambda error:errors.append(str(error)))
        table=f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}"
        player.goto(table+'&seat=player');dm.goto(table+'&seat=dm')
        isolated.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['other_session']}&seat=dm")
        expect(player.locator('#presenceRoster')).to_contain_text('action-dm',timeout=30000)
        expect(dm.locator('#presenceRoster')).to_contain_text('action-player',timeout=30000)
        player.locator(f".token-marker[data-token-id='{info['token']}']").click()
        expect(player.locator('#personalActionBar')).to_be_visible()
        player.locator('[data-pa-edit]').click()
        expect(player.locator('#personalActionDialog')).to_be_visible()
        player.locator('#paSlot0').select_option('ability:str')
        player.locator('#paSlot1').select_option('weapon_attack:unarmed')
        player.get_by_role('button',name='Speichern',exact=True).click()
        expect(player.locator('#personalActionDialog')).to_have_count(0)
        player.locator('[data-pa-slot="0"]').click()
        expect(dm.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(1)
        expect(player.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(1)
        expect(isolated.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(0)
        # Typing must not trigger another hotbar command.
        player.locator('#btnSidebarToggle').click()
        player.locator('#btnChatToggle').click()
        player.locator('#chatInput').press_sequentially('1234567890')
        player.locator('#chatInput').fill('')
        player.reload()
        expect(player.locator('#presenceRoster')).to_contain_text('action-dm')
        player.locator(f".token-marker[data-token-id='{info['token']}']").click()
        expect(player.locator('[data-pa-slot="0"]')).to_contain_text('Stärke')
        expect(player.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(1)
        # Block reconnect requests, then close the existing transport on the
        # server. The browser's own Socket.IO runtime must recover afterwards.
        player_context.route('**/socket.io/**',lambda route:route.abort())
        with app.app_context():
            context=TableContext.query.filter_by(user_id=info['player_id'],game_session_id=info['session']).filter(TableContext.socket_sid.isnot(None)).order_by(TableContext.id.desc()).first()
            assert context
            eio_sid=socketio.server.manager.eio_sid_from_sid(context.socket_sid,'/')
            socketio.server.eio.disconnect(eio_sid)
        expect(dm.locator('#presenceRoster')).not_to_contain_text('action-player')
        dm.locator('#btnSidebarToggle').click()
        dm.locator('.sidebar-tab[data-tab="tools"]').click()
        dm.locator('#diceInput').fill('1d20+7');dm.locator('#btnRoll').click()
        expect(dm.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(2)
        expect(player.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(1)
        player_context.unroute('**/socket.io/**')
        expect(dm.locator('#presenceRoster')).to_contain_text('action-player',timeout=30000)
        expect(player.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(2)
        ids=player.locator('#chatLog .chat-entry[data-message-id]').evaluate_all('(rows)=>rows.map(row=>row.dataset.messageId)')
        assert len(set(ids))==2
        expect(isolated.locator('#chatLog .chat-entry[data-message-id]')).to_have_count(0)
        assert not errors,errors
        player_context.close();dm_context.close();player_browser.close();dm_browser.close()


@pytest.mark.parametrize('width',[390,320])
def test_mobile_personal_layout_can_be_edited_without_overflow(action_site,width):
    from playwright.sync_api import sync_playwright,expect
    app,origin,info=action_site
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce')
        context.add_cookies([{'name':'access_token_cookie','value':info['player_auth'],'url':origin,'httpOnly':True}])
        page=context.new_page();page.set_default_timeout(30000)
        page.goto(f"{origin}/play?campaign_id={info['campaign']}&session_id={info['session']}&seat=player")
        expect(page.locator('#presenceRoster')).to_contain_text('action-player')
        page.locator(f".token-marker[data-token-id='{info['token']}']").click()
        page.locator('[data-pa-edit]').click()
        page.locator('#paSlot0').select_option('ability:str')
        page.locator('#paSlot1').select_option('weapon_attack:unarmed')
        page.get_by_role('button',name='Platz 2 nach oben',exact=True).click()
        assert page.locator('#paSlot0').input_value()=='weapon_attack:unarmed'
        page.get_by_role('button',name='Speichern',exact=True).click()
        expect(page.locator('#personalActionDialog')).to_have_count(0)
        expect(page.locator('[data-pa-slot="0"]')).to_contain_text('Angriffswurf')
        assert page.evaluate('document.documentElement.scrollWidth')<=width+1
        context.close();browser.close()
