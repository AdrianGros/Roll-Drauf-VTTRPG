"""Create/remove only named synthetic feedback QA data; credentials stay outside Git."""
import json
import os
import secrets
import sys
import warnings
from datetime import timedelta

warnings.filterwarnings('ignore')
from flask_jwt_extended import create_access_token, decode_token, get_csrf_token
from sqlalchemy import delete, or_

from vtt import create_app
from vtt.extensions import db
from vtt.models import (Campaign, CampaignMap, CampaignMember, CombatEncounter,
                        GameSession, Role, SceneStack, Session, SessionState,
                        TokenState, User)
from vtt.play.service import ensure_session_state, init_scene_stack
from vtt.utils.time import utcnow

PRIVATE = '/tmp/feedback-harness-20261123-credentials.json'
app = create_app('production')


def member(campaign, user, role):
    db.session.add(CampaignMember(campaign_id=campaign.id, user_id=user.id,
        campaign_role=role, status='active', invited_by=campaign.owner_id,
        invited_at=utcnow(), accepted_at=utcnow(), joined_at=utcnow()))


def create():
    assert not os.path.exists(PRIVATE), 'Existing QA manifest must be cleaned up first'
    suffix = secrets.token_hex(5)
    users = []
    for kind, role_name in [('dm', 'DM'), ('player', 'Player')]:
        role = Role.query.filter_by(name=role_name).one()
        user = User(username=f'qa_feedback_{kind}_{suffix}', email=f'qa_feedback_{kind}_{suffix}@example.invalid',
                    role_id=role.id, is_active=True, email_verified=True, profile_tier=kind,
                    active_campaigns_quota=4, storage_quota_gb=1)
        user.set_password(secrets.token_urlsafe(32))
        db.session.add(user)
        db.session.flush()
        users.append(user)
    owner, player = users
    campaigns = []
    for kind in ['Solo scheduled', 'Solo new', 'Roles and camera']:
        campaign = Campaign(name=f'QA Feedback {kind} {suffix}', owner_id=owner.id,
                            description='Temporary isolated technical acceptance', status='active', max_players=6)
        db.session.add(campaign)
        db.session.flush()
        member(campaign, owner, 'DM')
        campaigns.append(campaign)
    solo, new, roles = campaigns
    scheduled = GameSession(campaign_id=solo.id, name='QA ready without map or date', status='ready')
    db.session.add(scheduled)
    member(roles, player, 'Player')
    map_ = CampaignMap(campaign_id=roles.id, name='QA large map', width=6000, height=4000,
                       grid_size=50, created_by=owner.id)
    db.session.add(map_)
    db.session.flush()
    role_session = GameSession(campaign_id=roles.id, name='QA role boundary', status='in_progress', map_id=map_.id)
    db.session.add(role_session)
    db.session.commit()
    init_scene_stack(roles, role_session, owner, [map_.id])
    state = ensure_session_state(roles, role_session)
    db.session.add(TokenState(session_state_id=state.id, campaign_id=roles.id,
        game_session_id=role_session.id, map_id=map_.id, owner_user_id=owner.id,
        name='QA_FEEDBACK_PRIVATE_SENTINEL', token_type='monster', x=140, y=140, size=1,
        visibility='dm_only', metadata_json={'position_mode': 'pixel'}, updated_by=owner.id, version=1))
    result = {'user_ids': [u.id for u in users], 'campaign_ids': [c.id for c in campaigns],
              'solo_campaign_id': solo.id, 'new_campaign_id': new.id, 'roles_campaign_id': roles.id,
              'scheduled_session_id': scheduled.id, 'role_session_id': role_session.id, 'users': {}}
    for kind, user in zip(['dm', 'player'], users):
        token = create_access_token(identity=str(user.id))
        db.session.add(Session(user_id=user.id, token_jti=decode_token(token)['jti'],
                               expires_at=utcnow() + timedelta(hours=1)))
        result['users'][kind] = {'username': user.username, 'token': token, 'csrf': get_csrf_token(token)}
    db.session.commit()
    descriptor = os.open(PRIVATE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(result, stream)
    print(json.dumps({'status': 'created', 'user_ids': result['user_ids'], 'campaign_ids': result['campaign_ids'],
                      'credentials': 'protected manifest only; no tokens in output'}))


def cleanup():
    with open(PRIVATE) as stream:
        fixture = json.load(stream)
    uids, cids = fixture['user_ids'], fixture['campaign_ids']
    users = User.query.filter(User.id.in_(uids)).all()
    campaigns = Campaign.query.filter(Campaign.id.in_(cids)).all()
    assert len(users) == 2 and all(u.username.startswith('qa_feedback_') for u in users)
    assert len(campaigns) == 3 and all(c.name.startswith('QA Feedback ') and c.owner_id in uids for c in campaigns)
    sids = [row.id for row in GameSession.query.filter(GameSession.campaign_id.in_(cids))]
    mids = [row.id for row in CampaignMap.query.filter(CampaignMap.campaign_id.in_(cids))]
    stacks = [row.id for row in SceneStack.query.filter(SceneStack.campaign_id.in_(cids))]
    states = [row.id for row in SessionState.query.filter(SessionState.campaign_id.in_(cids))]
    SceneStack.query.filter(SceneStack.campaign_id.in_(cids)).update({'active_layer_id': None}, synchronize_session=False)
    CombatEncounter.query.filter(CombatEncounter.campaign_id.in_(cids)).update({'active_token_id': None}, synchronize_session=False)
    db.session.flush()
    removed = {}
    for table in reversed(db.metadata.sorted_tables):
        clauses = []
        if table.name == 'users': clauses.append(table.c.id.in_(uids))
        if table.name == 'campaigns': clauses.append(table.c.id.in_(cids))
        if table.name == 'game_sessions': clauses.append(table.c.id.in_(sids))
        if table.name == 'initiative_rounds': clauses.append(table.c.session_id.in_(sids))
        for column, values in [('campaign_id', cids), ('map_id', mids), ('game_session_id', sids),
                               ('scene_stack_id', stacks), ('session_state_id', states)]:
            if column in table.c and values: clauses.append(table.c[column].in_(values))
        for column in ['user_id', 'owner_id', 'owner_user_id', 'created_by', 'updated_by', 'author_user_id', 'published_by']:
            if column in table.c: clauses.append(table.c[column].in_(uids))
        if clauses:
            count = db.session.execute(delete(table).where(or_(*clauses))).rowcount
            if count: removed[table.name] = count
    db.session.commit()
    db.session.expire_all()
    assert User.query.filter(User.id.in_(uids)).count() == 0
    assert Campaign.query.filter(Campaign.id.in_(cids)).count() == 0
    os.unlink(PRIVATE)
    print(json.dumps({'status': 'pass', 'scope': 'only qa_feedback_ users and their three owned QA campaigns',
                      'removed': removed, 'container_credentials_removed': True}))


with app.app_context():
    {'create': create, 'cleanup': cleanup}[sys.argv[1]]()
