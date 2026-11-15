"""Create only the named, disposable DM/Player campaign for this live acceptance."""
import json, os, secrets, warnings
warnings.filterwarnings('ignore')
from vtt import create_app
from vtt.extensions import db
from vtt.models import User, Role, Campaign, CampaignMember, CampaignMap, GameSession, TokenState
from vtt.play.service import ensure_session_state
from vtt.utils.time import utcnow
path='/tmp/consolidation-layers-live-credentials.json'
assert not os.path.exists(path)
app=create_app('production')
with app.app_context():
    suffix=secrets.token_hex(4); users={}
    for kind,role_name in [('dm','DM'),('player','Player')]:
        password=secrets.token_urlsafe(32)
        user=User(username='layercheck_'+kind+'_'+suffix,email='layercheck_'+kind+'_'+suffix+'@example.invalid',
            role_id=Role.query.filter_by(name=role_name).first().id,is_active=True,email_verified=True,
            profile_tier=kind,active_campaigns_quota=3,storage_quota_gb=1)
        user.set_password(password);db.session.add(user);db.session.flush()
        users[kind]={'id':user.id,'username':user.username,'password':password}
    owner=users['dm']['id'];player=users['player']['id']
    campaign=Campaign(name='Layercheck '+suffix,description='Temporäre technische Live-Abnahme 15.11.',owner_id=owner,status='active',max_players=6)
    db.session.add(campaign);db.session.flush()
    for uid,role in [(owner,'DM'),(player,'Player')]:
        db.session.add(CampaignMember(campaign_id=campaign.id,user_id=uid,campaign_role=role,status='active',joined_at=utcnow(),invited_at=utcnow(),accepted_at=utcnow(),invited_by=owner))
    map_=CampaignMap(campaign_id=campaign.id,name='Layer-Prüfung',width=1200,height=900,grid_size=70,fog_enabled=False,created_by=owner)
    db.session.add(map_);db.session.flush()
    session=GameSession(campaign_id=campaign.id,name='Layer-Live-Abnahme',status='in_progress',map_id=map_.id)
    db.session.add(session);db.session.flush();db.session.commit()
    state=ensure_session_state(campaign,session)
    ids={}
    for name,x,y,visibility,kind,uid in [('Hero',420,420,'public','player',player),('Goblin',140,140,'dm_only','monster',owner),('Goblin 2',210,140,'dm_only','monster',owner)]:
        token=TokenState(session_state_id=state.id,campaign_id=campaign.id,game_session_id=session.id,map_id=map_.id,owner_user_id=uid,name=name,token_type=kind,x=x,y=y,size=1,rotation=0,visibility=visibility,metadata_json={'position_mode':'pixel'},updated_by=owner,version=1)
        db.session.add(token);db.session.flush();ids[name]=token.id
    db.session.commit()
    result={'campaign_id':campaign.id,'session_id':session.id,'session_ids':[session.id],'map_id':map_.id,'user_ids':[owner,player],'users':users,'token_ids':ids}
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:json.dump(result,out)
    print('Scoped layer acceptance fixture created; credentials written privately.')
