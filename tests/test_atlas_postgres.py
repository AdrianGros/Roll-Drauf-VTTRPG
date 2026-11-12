"""Actual row-lock contention in the guarded disposable PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from flask_jwt_extended import create_access_token
from tests.test_session_calendar_postgres import pg_calendar  # noqa:F401
from tests.test_mapmaker_library import document
from tests.test_atlas import png
from vtt.extensions import db
from vtt.models import User,Role
from vtt.models.atlas import AtlasWorld,AtlasMap
pytestmark=pytest.mark.postgres

@pytest.fixture
def atlas_pg(pg_calendar,tmp_path):
 app,_=pg_calendar;tokens={}
 with app.app_context():
  app.config.update(LOCAL_STORAGE_PATH=str(tmp_path/'storage'),STORAGE_PROVIDER='local')
  owner=User.query.one();owner.storage_quota_gb=1
  editor=User(username='atlas-editor',email='atlas-editor@example.test',role_id=Role.query.one().id,password_hash='test',is_active=True,account_state='active',storage_quota_gb=1);db.session.add(editor);db.session.commit();oids=(owner.id,editor.id)
  for user in (owner,editor):tokens[user.id]=create_access_token(identity=str(user.id))
 def api(user,path,method='GET',body=None,headers=None):
  with app.test_client() as c:
   c.set_cookie('access_token_cookie',tokens[user]);return c.open(path,method=method,json=body,headers=headers or {})
 owner,editor=oids;created=api(owner,'/api/atlas/worlds','POST',{'title':'Concurrent Atlas'});assert created.status_code==201,created.json;world=created.json
 grant=api(owner,f'/api/atlas/worlds/{world["id"]}/members','PUT',{'revision':world['revision'],'username':'atlas-editor','role':'editor'});assert grant.status_code==200;world=grant.json
 source=api(owner,'/api/assets/mapmaker/projects','POST',{'document':document()},{'X-Mapmaker-Account':str(owner)});assert source.status_code==201;project=source.json['project']
 return app,api,owner,editor,world,project

def test_two_authors_cas_and_raster_lease_have_one_winner(atlas_pg):
 app,api,owner,editor,world,project=atlas_pg;path='/api/atlas/worlds/'+world['id'];barrier=Barrier(2)
 def save(user):
  graph={**world['graph'],'summary':str(user)};barrier.wait(timeout=15);return api(user,path,'PUT',{'revision':world['revision'],'graph':graph}).status_code
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,[owner,editor]))
 assert sorted(results)==[200,409],results
 world=api(owner,path).json;attached=api(owner,path+'/maps','POST',{'revision':world['revision'],'project_id':project['id'],'project_revision':1,'png':png(),'credits':''});assert attached.status_code==201,attached.json
 mp=path+'/maps/'+attached.json['map_id'];tabs={uid:str(uuid4()) for uid in (owner,editor)};barrier=Barrier(2)
 def lease(user):
  barrier.wait(timeout=15);return user,api(user,mp+'/lease','POST',{'tab':tabs[user]}).status_code
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lease,[owner,editor]))
 assert sorted(status for _,status in results)==[200,409],results
 winner=next(user for user,status in results if status==200);loser=editor if winner==owner else owner
 bundle=api(winner,mp).json['bundle'];assert api(loser,mp,'PUT',{'revision':1,'tab':tabs[winner],'bundle':bundle}).status_code==409
 assert api(winner,mp,'PUT',{'revision':1,'tab':tabs[winner],'bundle':bundle}).status_code==200
 world=api(owner,path).json
 assert api(owner,path+'/members','PUT',{'revision':world['revision'],'username':'atlas-editor','role':None}).status_code==200
 assert api(editor,mp,'PUT',{'revision':2,'tab':tabs[editor],'bundle':bundle}).status_code==404

def test_shared_owner_quota_serializes_two_world_attachments(atlas_pg):
 app,api,owner,editor,world,project=atlas_pg;second=api(owner,'/api/atlas/worlds','POST',{'title':'Second world'});assert second.status_code==201
 from vtt.atlas_domain import bundle,encoded
 size=len(encoded(bundle({'document':document(),'png':png(),'credits':''})))
 with app.app_context():
  user=db.session.get(User,owner);user.storage_quota_gb=1;user.storage_used_gb=1-(size+500)/(1024**3);db.session.commit()
 barrier=Barrier(2)
 def attach(w):
  barrier.wait(timeout=15);return api(owner,f'/api/atlas/worlds/{w["id"]}/maps','POST',{'revision':w['revision'],'project_id':project['id'],'project_revision':1,'png':png(),'credits':''}).status_code
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attach,[world,second.json]))
 assert sorted(results)==[201,507],results
 with app.app_context():
  assert AtlasMap.query.count()==1;user=db.session.get(User,owner);assert user.storage_used_gb<=user.storage_quota_gb
