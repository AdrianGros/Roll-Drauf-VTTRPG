"""Remove only rows/files downstream of two verified synthetic QA users."""
import json
import os
import warnings
warnings.filterwarnings('ignore')
from sqlalchemy import and_,delete,or_,select
from vtt import create_app
from vtt.extensions import db
from vtt.models import User,Campaign,SceneStack,CombatEncounter
from vtt.endpoints.mapmaker import adapter

app=create_app('production')
with app.app_context():
    path='/tmp/review-web-live-credentials-20261122.json'
    fixture=json.load(open(path));uids=fixture['user_ids']
    users=User.query.filter(User.id.in_(uids)).all()
    assert len(uids)==len(users)==2 and all(user.username.startswith('qa_ui_') for user in users)
    campaigns=Campaign.query.filter(Campaign.owner_id.in_(uids)).all()
    assert campaigns and all(campaign.name.startswith('QA') for campaign in campaigns)
    cids=[campaign.id for campaign in campaigns]
    SceneStack.query.filter(SceneStack.campaign_id.in_(cids)).update({'active_layer_id':None},synchronize_session=False)
    CombatEncounter.query.filter(CombatEncounter.campaign_id.in_(cids)).update({'active_token_id':None},synchronize_session=False)
    db.session.flush()
    tables=list(db.metadata.sorted_tables)
    selected={};seen={}
    def remember(table,rows):
        target=selected.setdefault(table.name,[]);keys=seen.setdefault(table.name,set());changed=False
        for row in rows:
            key=tuple(row[column.name] for column in table.primary_key.columns)
            if key in keys:continue
            keys.add(key);target.append(row);changed=True
        return changed
    user_table=db.metadata.tables['users']
    remember(user_table,db.session.execute(select(user_table).where(user_table.c.id.in_(uids))).mappings().all())
    # Follow only child foreign keys. An existing parent such as a Role/Guild is
    # never selected merely because a QA child refers to it.
    while True:
        changed=False
        for table in tables:
            if table.name=='users':continue
            conditions=[]
            for constraint in table.foreign_key_constraints:
                elements=list(constraint.elements)
                if not elements:continue
                for parent in selected.get(elements[0].column.table.name,[]):
                    if all(parent[element.column.name] is not None for element in elements):
                        conditions.append(and_(*[element.parent==parent[element.column.name] for element in elements]))
            if conditions:
                changed=remember(table,db.session.execute(select(table).where(or_(*conditions))).mappings().all()) or changed
        if not changed:break
    # Release every private object belonging to those selected resources.
    files=0
    for name in ['assets','mapmaker_projects','atlas_maps','atlas_publications','map_floor_images']:
        for row in selected.get(name,[]):
            storage=adapter(row.get('storage_provider'))
            for field in ['storage_key','thumbnail_key']:
                if row.get(field):storage.delete(row[field]);files+=1
    removed={}
    for table in reversed(tables):
        rows=selected.get(table.name,[])
        if not rows:continue
        conditions=[and_(*[column==row[column.name] for column in table.primary_key.columns]) for row in rows]
        removed[table.name]=db.session.execute(delete(table).where(or_(*conditions))).rowcount
    db.session.commit()
    assert User.query.filter(User.id.in_(uids)).count()==0
    assert Campaign.query.filter(Campaign.owner_id.in_(uids)).count()==0
    os.unlink(path)
    print(json.dumps({'status':'pass','scope':'downstream of two verified qa_ui_ users only','removed':removed,'private_files_removed':files,'container_credentials_removed':True}))
