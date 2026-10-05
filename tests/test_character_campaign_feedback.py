"""LegendaryRock's character archive, sharing and public-campaign journey."""
from pathlib import Path
from threading import Thread
import os

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.serving import make_server

from vtt import create_app
from vtt.config import TestingConfig
from vtt.extensions import db
from vtt.models import Campaign, CampaignMember, Character, GameSession, Role, SessionCharacterAssignment, User
from test_balu_navigation import QuietHandler


@pytest.fixture
def feedback_app(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path}/feedback.db')
    app = create_app('testing')
    app.config['LOCAL_STORAGE_PATH'] = str(tmp_path / 'assets')
    with app.app_context():
        db.create_all()
        role = Role(name='Player'); db.session.add(role); db.session.flush()
        users = {}
        for name in ['dm', 'player', 'outsider']:
            user = User(username=f'feedback-{name}', email=f'{name}@example.test', role_id=role.id,
                        password_hash='test', is_active=True, account_state='active', profile_tier='player')
            db.session.add(user); db.session.flush(); users[name] = user
        campaign = Campaign(name='Public feedback round', owner_id=users['dm'].id, is_discoverable=True)
        private = Campaign(name='Private feedback round', owner_id=users['dm'].id, is_discoverable=False)
        db.session.add_all([campaign, private]); db.session.flush()
        for c in [campaign, private]:
            db.session.add(CampaignMember(campaign_id=c.id, user_id=users['dm'].id, campaign_role='DM', status='active'))
        own = Character(name='First hero', user_id=users['player'].id)
        other = Character(name='Private hero', user_id=users['outsider'].id)
        dm_char = Character(name='Campaign companion', user_id=users['dm'].id, campaign_id=campaign.id)
        db.session.add_all([own, other, dm_char]); db.session.commit()
        data = {'campaign_id': campaign.id, 'private_id': private.id, 'character_id': own.id,
                'other_character_id': other.id, 'dm_character_id': dm_char.id,
                'users': {name: u.id for name, u in users.items()},
                'tokens': {name: create_access_token(identity=str(u.id)) for name, u in users.items()}}
    yield app, data
    with app.app_context():
        db.session.remove(); db.engine.dispose()


def client_for(app, data, who):
    client = app.test_client()
    client.set_cookie('access_token_cookie', data['tokens'][who])
    return client


def activate(app, data, status='active'):
    with app.app_context():
        member = CampaignMember(campaign_id=data['campaign_id'], user_id=data['users']['player'], campaign_role='Player', status=status)
        db.session.add(member); db.session.commit()


def test_public_join_requires_approval_then_allows_explicit_character_sharing(feedback_app):
    app, d = feedback_app
    player, dm, outsider = [client_for(app, d, name) for name in ['player', 'dm', 'outsider']]
    campaign, char = d['campaign_id'], d['character_id']
    assert player.get(f'/api/characters/{d["dm_character_id"]}/sheet').status_code == 403
    for _ in range(2):
        assert player.post(f'/api/campaigns/{campaign}/join-requests').status_code == 202
    assert player.get(f'/api/campaigns/{campaign}').status_code == 403
    assert player.get('/api/characters/shared').json == []
    assert player.put(f'/api/characters/{char}/campaign', json={'campaign_id': campaign}).status_code == 403
    listing = player.get('/api/campaigns').json
    assert listing[0]['your_membership_status'] == 'pending'
    assert listing[0]['can_request_join'] is False
    assert outsider.post(f'/api/campaigns/{campaign}/join-requests/{d["users"]["player"]}/approve').status_code == 403
    assert dm.post(f'/api/campaigns/{campaign}/join-requests/{d["users"]["player"]}/approve').status_code == 200
    assert player.put(f'/api/characters/{char}/campaign', json={'campaign_id': campaign}).status_code == 200
    assert [c['id'] for c in dm.get('/api/characters/shared').json] == [char]
    assert dm.get(f'/api/characters/{char}/sheet').status_code == 200
    assert outsider.get(f'/api/characters/{char}/sheet').status_code == 403
    assert outsider.get('/api/characters/shared').json == []
    assert char in [c['id'] for c in dm.get(f'/api/campaigns/{campaign}').json['characters']]
    assert player.put(f'/api/characters/{char}/campaign', json={'campaign_id': None}).status_code == 200
    assert dm.get('/api/characters/shared').json == []
    assert dm.get(f'/api/characters/{char}/sheet').status_code == 403


@pytest.mark.parametrize('status', ['pending', 'invited', 'kicked', 'left'])
def test_inactive_members_cannot_share_create_or_read_campaign_characters(feedback_app, status):
    app, d = feedback_app; activate(app, d, status)
    player = client_for(app, d, 'player')
    payload = {'campaign_id': d['campaign_id']}
    assert player.put(f'/api/characters/{d["character_id"]}/campaign', json=payload).status_code == 403
    assert player.post('/api/characters', json={'name': 'Denied', **payload}).status_code == 403
    assert player.get(f'/api/characters/{d["dm_character_id"]}/sheet').status_code == 403
    assert player.get('/api/characters/shared').json == []


@pytest.mark.parametrize('kind,expected', [('private',403), ('full',409), ('paused',409), ('deleted',404), ('kicked',403)])
def test_public_requests_respect_campaign_restrictions(feedback_app, kind, expected):
    app, d = feedback_app
    if kind == 'kicked': activate(app, d, 'kicked')
    with app.app_context():
        campaign = db.session.get(Campaign, d['campaign_id'])
        if kind == 'private': campaign.is_discoverable = False
        if kind == 'full': campaign.max_players = 1
        if kind == 'paused': campaign.status = 'paused'
        if kind == 'deleted':
            from vtt.utils.time import utcnow
            campaign.deleted_at = utcnow()
        db.session.commit()
    player = client_for(app, d, 'player')
    assert player.post(f'/api/campaigns/{d["campaign_id"]}/join-requests').status_code == expected


@pytest.mark.parametrize('value', [0, -1, '1', True, 1.5, {}, []])
def test_character_assignment_rejects_invalid_campaign_ids(feedback_app, value):
    app, d = feedback_app
    player = client_for(app, d, 'player')
    assert player.put(f'/api/characters/{d["character_id"]}/campaign', json={'campaign_id': value}).status_code == 400


def test_only_owner_can_share_and_assignments_survive_rejected_move(feedback_app):
    app, d = feedback_app; activate(app, d)
    player, dm = [client_for(app, d, who) for who in ['player', 'dm']]
    char, campaign = d['character_id'], d['campaign_id']
    assert dm.put(f'/api/characters/{char}/campaign', json={'campaign_id': campaign}).status_code == 403
    assert player.put(f'/api/characters/{char}/campaign', json={'campaign_id': d['private_id']}).status_code == 403
    assert player.put(f'/api/characters/{char}/campaign', json={'campaign_id': campaign}).status_code == 200
    with app.app_context():
        session = GameSession(campaign_id=campaign, name='Roster session'); db.session.add(session); db.session.flush()
        db.session.add(SessionCharacterAssignment(game_session_id=session.id, character_id=char, assigned_by_user_id=d['users']['dm'])); db.session.commit()
    assert player.put(f'/api/characters/{char}/campaign', json={'campaign_id': None}).status_code == 409
    assert player.put(f'/api/characters/{char}/campaign', json={'campaign_id': campaign}).status_code == 200
    assert dm.get(f'/api/characters/{char}/sheet').status_code == 200


def test_deleted_campaign_and_unusable_account_have_no_shared_access(feedback_app):
    app, d = feedback_app; activate(app, d)
    player = client_for(app, d, 'player')
    with app.app_context():
        from vtt.utils.time import utcnow
        db.session.get(Campaign, d['campaign_id']).deleted_at = utcnow(); db.session.commit()
    assert player.get('/api/characters/shared').json == []
    assert player.get(f'/api/characters/{d["dm_character_id"]}/sheet').status_code == 403
    assert player.put(f'/api/characters/{d["character_id"]}/campaign', json={'campaign_id': d['campaign_id']}).status_code == 404
    with app.app_context():
        db.session.get(User, d['users']['player']).is_active = False; db.session.commit()
    assert player.get('/api/characters/shared').status_code in {401,403,404}
    assert player.post(f'/api/campaigns/{d["campaign_id"]}/join-requests').status_code in {401,403,404}


@pytest.fixture
def feedback_site(feedback_app):
    app, d = feedback_app
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try: yield f'http://127.0.0.1:{server.server_port}', d
    finally: server.shutdown(); thread.join(timeout=5); server.server_close()


@pytest.mark.parametrize('engine', ['chromium', 'firefox'])
@pytest.mark.parametrize('width', [1440, 390])
def test_player_dm_journey_in_browser(feedback_site, engine, width):
    from playwright.sync_api import sync_playwright, expect
    origin, d = feedback_site
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(**({'args':['--no-sandbox']} if engine == 'chromium' else {}))
        contexts = {}
        errors = []
        for who in ['dm', 'player']:
            context = browser.new_context(viewport={'width':width,'height':1000 if width == 1440 else 844}, reduced_motion='reduce')
            context.add_cookies([{'name':'access_token_cookie','value':d['tokens'][who],'url':origin}])
            page = context.new_page(); page.set_default_timeout(10000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            contexts[who] = page
        player, dm = contexts['player'], contexts['dm']
        player.goto(origin+'/characters')
        expect(player.get_by_text('First hero', exact=True)).to_be_visible()
        player.get_by_role('button', name='Held anlegen', exact=True).click()
        expect(player.locator('#charModal')).to_be_visible()
        player.locator('#charName').fill('Second hero')
        for selector in ['#charRace','#charFaction','#charClass','#charBackground']:
            player.locator(selector).select_option(index=1)
        player.locator('#nextBtn').click(); player.locator('#nextBtn').click()
        with player.expect_response(lambda r: r.url.endswith('/api/characters') and r.request.method=='POST') as created:
            player.locator('#submitBtn').click()
        assert created.value.status == 201
        second = created.value.json()['id']
        expect(player.locator('#book-dashboard-scene').get_by_text('Second hero',exact=True)).to_be_visible()
        expect(player.get_by_role('button',name='Held anlegen',exact=True)).to_be_visible()
        expect(player.locator('[data-character-campaign]')).to_have_count(2)
        player.locator('.book-dashboard-ribbon [data-dashboard-route="/campaigns"]').click()
        player.get_by_role('button',name='Beitritt anfragen',exact=True).click()
        expect(player.locator('[data-join-status]')).to_contain_text('Beitrittsanfrage gesendet')
        player.reload()
        expect(player.get_by_text('Beitrittsanfrage gesendet. Die Spielleitung muss sie noch bestätigen.',exact=True)).to_be_visible()
        dm.goto(f'{origin}/campaigns?campaign_id={d["campaign_id"]}')
        dm.locator('[data-hub-action="approve-join-request"]').click()
        expect(dm.locator('[data-join-request]')).to_have_count(0)
        player.goto(origin+'/characters')
        form = player.locator(f'[data-character-campaign="{second}"]')
        form.locator('select').select_option(str(d['campaign_id']))
        form.get_by_role('button',name='Zuordnung speichern').click()
        expect(player.locator('#charactersMessageBox')).to_contain_text('mit der Kampagne geteilt')
        dm.goto(f'{origin}/campaigns?campaign_id={d["campaign_id"]}&workspace=1')
        dm.get_by_role('button',name='Charaktere öffnen',exact=True).first.click()
        shared = dm.locator('[data-shared-characters]')
        expect(shared.get_by_text('Second hero',exact=True)).to_be_visible()
        expect(shared.locator('[data-character-campaign]')).to_have_count(0)
        expect(dm.locator('#campaignsClassicTemplate, body > header, body > main, body > footer')).to_have_count(0)
        if os.environ.get('VTT_PROOF_DIR'):
            out=Path(os.environ['VTT_PROOF_DIR']); out.mkdir(parents=True,exist_ok=True)
            dm.screenshot(path=str(out/f'character-sharing-{engine}-{width}.png'))
        shared.get_by_role('button',name='Bogen öffnen',exact=True).click()
        expect(dm).to_have_url(f'{origin}/character-sheet?id={second}')
        expect(dm.locator('#book-dashboard-scene')).to_contain_text('Second hero')
        browser.close()
        assert errors == []


def test_party_stash_cannot_be_moved(feedback_app):
    app, d = feedback_app
    with app.app_context():
        db.session.get(Character, d['dm_character_id']).is_party_stash = True
        db.session.commit()
    dm = client_for(app, d, 'dm')
    assert dm.put(f'/api/characters/{d["dm_character_id"]}/campaign', json={'campaign_id': None}).status_code == 409


def test_sharing_revoked_immediately_when_membership_ends(feedback_app):
    app, d = feedback_app; activate(app, d)
    player = client_for(app, d, 'player')
    assert player.get('/api/characters/shared').json[0]['id'] == d['dm_character_id']
    with app.app_context():
        CampaignMember.query.filter_by(campaign_id=d['campaign_id'],user_id=d['users']['player']).first().status='kicked'
        db.session.commit()
    assert player.get('/api/characters/shared').json == []
    assert player.get(f'/api/characters/{d["dm_character_id"]}/sheet').status_code == 403
