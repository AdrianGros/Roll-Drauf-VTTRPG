import json,os,warnings
warnings.filterwarnings('ignore')
from sqlalchemy import delete,or_
from vtt import create_app
from vtt.extensions import db
from vtt.models import User,Campaign
app=create_app('production')
with app.app_context():
    path='/tmp/ui-playtable-live-credentials.json'
    fixture=json.load(open(path));uids=fixture['user_ids'];cid=fixture['campaign_id'];sids=fixture['session_ids']
    users=User.query.filter(User.id.in_(uids)).all()
    assert len(users)==2 and all(u.username.startswith('qa_ui_') for u in users)
    campaign=db.session.get(Campaign,cid)
    assert campaign and campaign.name.startswith('QA UI Playtable ') and campaign.owner_id in uids
    from vtt.models import Asset
    from vtt.storage import get_storage_adapter
    assets=Asset.query.filter_by(campaign_id=cid).all()
    storage=get_storage_adapter()
    removed_files=0
    for asset in assets:
        for key in (asset.storage_key,asset.thumbnail_key):
            if key:
                storage.delete(key);removed_files+=1
    from vtt.models import SceneStack, SessionState, CampaignMap
    stack_ids=[r.id for r in SceneStack.query.filter_by(campaign_id=cid).all()]
    state_ids=[r.id for r in SessionState.query.filter_by(campaign_id=cid).all()]
    SceneStack.query.filter_by(campaign_id=cid).update({"active_layer_id":None},synchronize_session=False)
    db.session.flush()
    map_ids=[r.id for r in CampaignMap.query.filter_by(campaign_id=cid).all()]
    counts={}
    for table in reversed(db.metadata.sorted_tables):
        clauses=[]
        if table.name=='initiative_rounds':clauses.append(table.c.session_id.in_(sids))
        if 'map_id' in table.c:clauses.append(table.c.map_id.in_(map_ids))
        if table.name=='users':clauses.append(table.c.id.in_(uids))
        if table.name=='campaigns':clauses.append(table.c.id==cid)
        if table.name=='game_sessions':clauses.append(table.c.id.in_(sids))
        for name in ('campaign_id',):
            if name in table.c:clauses.append(table.c[name]==cid)
        if 'scene_stack_id' in table.c and stack_ids:clauses.append(table.c.scene_stack_id.in_(stack_ids))
        if 'session_state_id' in table.c and state_ids:clauses.append(table.c.session_state_id.in_(state_ids))
        for name in ('game_session_id',):
            if name in table.c:clauses.append(table.c[name].in_(sids))
        for name in ('user_id','owner_id','owner_user_id','created_by','updated_by','author_user_id','published_by'):
            if name in table.c:clauses.append(table.c[name].in_(uids))
        if clauses:
            n=db.session.execute(delete(table).where(or_(*clauses))).rowcount
            if n:counts[table.name]=n
    db.session.commit();db.session.expire_all()
    assert User.query.filter(User.id.in_(uids)).count()==0 and Campaign.query.filter_by(id=cid).count()==0
    os.unlink(path)
    print(json.dumps({'status':'pass','scope':'only synthetic qa_ui_ users and owned campaign','removed':counts,'container_credentials_removed':True,'synthetic_asset_files_removed':removed_files}))
