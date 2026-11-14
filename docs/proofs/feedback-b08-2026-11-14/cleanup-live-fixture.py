import json,os,warnings
warnings.filterwarnings('ignore')
from sqlalchemy import delete,or_,select
from vtt import create_app
from vtt.extensions import db
from vtt.models import User,Campaign,Character,Asset
from vtt.models.mapmaker_project import MapmakerProject
from vtt.models.scene_stack import SceneStack
from vtt.storage import get_storage_adapter
app=create_app('production')
with app.app_context():
    path='/tmp/feedback-b08-live-credentials.json'
    fixture=json.load(open(path));uids=fixture['user_ids'];cid=fixture['campaign_id'];sids=fixture['session_ids']
    users=User.query.filter(User.id.in_(uids)).all()
    assert len(users)==len(uids) and len(uids) in (2,3) and all(u.username.startswith('feedback_b08_') for u in users)
    campaign=db.session.get(Campaign,cid)
    assert campaign and campaign.name.startswith('Feedback-B08 ') and campaign.owner_id in uids
    from vtt.models import ModerationAction,ModerationReport
    # The moderation models form a DDL dependency cycle, so their generic
    # sorted-table order is not a valid delete order. This fixture created only
    # its own explicit kick, never a report or another moderator's action.
    assert ModerationReport.query.filter_by(campaign_id=cid).count()==0
    actions=ModerationAction.query.filter_by(campaign_id=cid).all()
    assert all(a.actor_user_id in uids and a.subject_user_id in uids and a.source_report_id is None for a in actions)
    db.session.execute(delete(ModerationAction).where(ModerationAction.campaign_id==cid))
    storage=get_storage_adapter(); removed_keys=0
    from vtt.models.atlas import AtlasWorld,AtlasMap,AtlasPublication
    worlds=AtlasWorld.query.filter(AtlasWorld.owner_id.in_(uids)).all();world_ids=[world.id for world in worlds];world_owners={world.id:world.owner_id for world in worlds}
    for model in (AtlasMap,AtlasPublication):
        for row in model.query.filter(model.world_id.in_(world_ids)).all():
            assert row.storage_key.startswith(f'users/{world_owners[row.world_id]}/atlas/{row.world_id}/')
            storage.delete(row.storage_key);assert not storage.exists(row.storage_key);removed_keys+=1
    for character in Character.query.filter(Character.user_id.in_(uids)).all():
        for field in ('avatar_storage_key','token_storage_key'):
            key=getattr(character,field,None)
            if key:
                assert key.startswith(f'uploads/users/{character.user_id}/characters/{character.id}/')
                storage.delete(key);assert not storage.exists(key);removed_keys+=1
    for project in MapmakerProject.query.filter(MapmakerProject.owner_id.in_(uids)).all():
        key=project.storage_key
        assert key.startswith(f'users/{project.owner_id}/mapmaker/{project.id}/')
        storage.delete(key);assert not storage.exists(key);removed_keys+=1
    for asset in Asset.query.filter_by(campaign_id=cid).all():
        assert asset.uploaded_by in uids
        for key in (asset.storage_key,asset.thumbnail_key):
            if key:
                assert key.startswith(f'campaigns/{cid}/assets/')
                storage.delete(key);assert not storage.exists(key);removed_keys+=1
    scoped={}
    for table_name, fk_name, values in [('session_series','campaign_id',[cid]),('session_date_polls','campaign_id',[cid]),('session_date_options','poll_id',None)]:
        table=db.metadata.tables.get(table_name)
        if table is not None:
            values=scoped.get('session_date_polls',[]) if values is None else values
            scoped[table_name]=list(db.session.execute(select(table.c.id).where(table.c[fk_name].in_(values))).scalars())
    stack_ids=[row.id for row in SceneStack.query.filter_by(campaign_id=cid).all()]
    character_ids=[row.id for row in Character.query.filter(Character.user_id.in_(uids)).all()]
    counts={}
    for table in reversed(db.metadata.sorted_tables):
        clauses=[]
        if table.name=='users':clauses.append(table.c.id.in_(uids))
        if table.name=='campaigns':clauses.append(table.c.id==cid)
        if table.name=='game_sessions':clauses.append(table.c.id.in_(sids))
        for name in ('campaign_id',):
            if name in table.c:clauses.append(table.c[name]==cid)
        if 'world_id' in table.c and world_ids:clauses.append(table.c.world_id.in_(world_ids))
        if 'character_id' in table.c and character_ids:clauses.append(table.c.character_id.in_(character_ids))
        if 'scene_stack_id' in table.c and stack_ids:clauses.append(table.c.scene_stack_id.in_(stack_ids))
        for name in ('game_session_id',):
            if name in table.c:clauses.append(table.c[name].in_(sids))
        for name in ('user_id','owner_id','created_by','updated_by','author_user_id','published_by'):
            if name in table.c:clauses.append(table.c[name].in_(uids))
        for column,parent in [('series_id','session_series'),('poll_id','session_date_polls'),('option_id','session_date_options')]:
            if column in table.c and scoped.get(parent):clauses.append(table.c[column].in_(scoped[parent]))
        if clauses:
            n=db.session.execute(delete(table).where(or_(*clauses))).rowcount
            if n:counts[table.name]=n
    db.session.commit();db.session.expire_all()
    assert User.query.filter(User.id.in_(uids)).count()==0 and Campaign.query.filter_by(id=cid).count()==0
    os.unlink(path)
    print(json.dumps({'status':'pass','scope':'only synthetic feedback_b08 users and owned campaign','removed':counts,'identity_storage_removed':removed_keys,'container_credentials_removed':True}))
