"""Atlas grants, immutable reader boundary, locks/CAS, scoped storage and safe roundtrip."""
import base64
from copy import deepcopy
import io,json,zipfile
from uuid import uuid4
import pytest
from PIL import Image
from tests.test_mapmaker_library import document
from vtt.extensions import db
from vtt.models import User
from vtt.models.atlas import AtlasWorld,AtlasMap,AtlasMember,AtlasPublication
from vtt.storage import get_storage_adapter
pytest_plugins=['tests.play_shared']
BASE='/api/atlas'

def png():
    out=io.BytesIO();Image.new('RGBA',(256,256),(12,80,110,255)).save(out,format='PNG');return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()

def place(name='Port',**over):return dict(id=str(uuid4()),name=name,parent_id=None,map_id=None,x=None,y=None,lore='Public port',private_lore='SECRET-PORT',reader_visible=True,links=[])|over

def grant(c,w,u,role):
    r=c.put(BASE+f'/worlds/{w["id"]}/members',json=dict(revision=w['revision'],username=u.username,role=role));assert r.status_code==200,r.json;return r.json

def graph_save(c,w):
    r=c.put(BASE+f'/worlds/{w["id"]}',json=dict(revision=w['revision'],graph=w['graph']));assert r.status_code==200,r.json;return r.json

def attach(c,w,project):
    r=c.post(BASE+f'/worlds/{w["id"]}/maps',json=dict(revision=w['revision'],project_id=project['id'],project_revision=project['revision'],png=png(),credits='Kenney CC0'));assert r.status_code==201,r.json;return r.json['world'],r.json['map_id']

@pytest.fixture
def atlas(play_app,play_dm_user,play_dm_client,play_player_user,play_player_client,play_codm_user,play_codm_client,tmp_path):
    play_app.config.update(LOCAL_STORAGE_PATH=str(tmp_path/'storage'),STORAGE_PROVIDER='local')
    for user in (play_dm_user,play_player_user,play_codm_user):user.storage_quota_gb=1
    db.session.commit()
    created=play_dm_client.post(BASE+'/worlds',json=dict(title='World'));assert created.status_code==201,created.json
    project=play_dm_client.post('/api/assets/mapmaker/projects',json=dict(document=document()),headers={'X-Mapmaker-Account':str(play_dm_user.id)});assert project.status_code==201,project.json
    return created.json,project.json['project']

def test_world_without_map_roles_and_immutable_reader_projection(atlas,play_dm_client,play_player_user,play_player_client,play_codm_client):
    w,project=atlas;path=BASE+'/worlds/'+w['id']
    assert play_codm_client.get(path).status_code==404  # global DM is unrelated
    w=grant(play_dm_client,w,play_player_user,'reader');w,mid=attach(play_dm_client,w,project)
    w['graph']['private_lore']='SECRET-WORLD';w['graph']['maps'][0]['reader_visible']=True
    shown=place(map_id=mid,x=50,y=60);hidden=place('SECRET-HIDDEN');hidden['reader_visible']=False;shown['links']=[hidden['id']]
    w['graph']['places']=[shown,hidden];w=graph_save(play_dm_client,w)
    for suffix in ('','/preview','/backup',f'/maps/{mid}',f'/maps/{mid}.png'):
        assert play_player_client.get(path+suffix).status_code==404
    assert play_player_client.post(path+'/publish',json=dict(revision=w['revision'],confirm_visible_pixels=True)).status_code==404
    assert play_dm_client.post(path+'/publish',json=dict(revision=w['revision'])).status_code==409
    pub=play_dm_client.post(path+'/publish',json=dict(revision=w['revision'],confirm_visible_pixels=True));assert pub.status_code==201,pub.json
    reader=play_player_client.get(path+'/published');assert reader.status_code==200
    assert 'SECRET' not in reader.text and project['id'] not in reader.text
    assert reader.json['projection']['places'][0]['links']==[]
    image=path+f'/published/maps/{mid}.png?version='+reader.json['publication_id'];old_image=play_player_client.get(image).data
    assert len(old_image)>100 and play_codm_client.get(image).status_code==404
    w=play_dm_client.get(path).json;w['graph']['places'][0]['lore']='New PRIVATE draft';w=graph_save(play_dm_client,w)
    assert play_player_client.get(path+'/published').json==reader.json
    assert play_player_client.get(image).data==old_image
    w=grant(play_dm_client,w,play_player_user,None)
    assert play_player_client.get(path+'/published').status_code==404 and play_player_client.get(image).status_code==404
    assert play_player_client.get(BASE+'/worlds').json['worlds']==[]

def test_graph_validation_cas_scale_links_and_private_ancestors(atlas,play_dm_client):
    w,project=atlas;w,mid=attach(play_dm_client,w,project);path=BASE+'/worlds/'+w['id'];original=deepcopy(w)
    a=place('Continent');b=place('Port');a['parent_id']=b['id'];b['parent_id']=a['id'];w['graph']['places']=[a,b]
    assert play_dm_client.put(path,json=dict(revision=w['revision'],graph=w['graph'])).status_code==400
    a['parent_id']=None;a['reader_visible']=False;b['parent_id']=a['id'];b['map_id']=mid;b['x']=5;b['y']=6
    w=graph_save(play_dm_client,w)
    assert play_dm_client.get(path+'/preview').status_code==409
    w['graph']['places'][0]['reader_visible']=True;w['graph']['maps'][0]['reader_visible']=True;w['graph']['maps'][0]['km_per_pixel']=1.5
    w=graph_save(play_dm_client,w);assert play_dm_client.get(path+'/preview').json['projection']['maps'][0]['km_per_pixel']==1.5
    assert play_dm_client.put(path,json=dict(revision=original['revision'],graph=original['graph'])).status_code==409
    w['graph']['places'][0]['links']=[str(uuid4())]
    assert play_dm_client.put(path,json=dict(revision=w['revision'],graph=w['graph'])).status_code==400
    assert play_dm_client.delete(path+f'/maps/{mid}',json=dict(revision=w['revision'])).status_code==409

def test_two_authors_map_lease_save_revocation_and_original_unchanged(atlas,play_dm_client,play_player_user,play_player_client):
    w,project=atlas;w=grant(play_dm_client,w,play_player_user,'editor');w,mid=attach(play_dm_client,w,project);path=BASE+'/worlds/'+w['id'];mp=path+f'/maps/{mid}';tab=str(uuid4());other=str(uuid4())
    snapshot=play_player_client.get(mp).json;assert snapshot['map']['revision']==1
    assert play_player_client.post(mp+'/lease',json=dict(tab=tab)).status_code==200
    assert play_dm_client.post(mp+'/lease',json=dict(tab=other)).status_code==409
    assert play_player_client.post(mp+'/lease',json=dict(tab=other)).status_code==409
    saved=play_player_client.put(mp,json=dict(tab=tab,revision=1,bundle=snapshot['bundle']));assert saved.status_code==200,saved.json
    assert saved.json['map']['revision']==2
    assert play_player_client.put(mp,json=dict(tab=tab,revision=1,bundle=snapshot['bundle'])).status_code==409
    original=play_dm_client.get('/api/assets/mapmaker/projects/'+project['id']);assert original.json['project']['revision']==1
    w=play_dm_client.get(path).json;w=grant(play_dm_client,w,play_player_user,'reader')
    assert play_player_client.put(mp,json=dict(tab=tab,revision=2,bundle=snapshot['bundle'])).status_code==404
    assert play_dm_client.post(mp+'/lease',json=dict(tab=other)).status_code==200

@pytest.mark.parametrize('format',['json','zip'])
def test_three_map_backup_roundtrip_preserves_ids_graph_assets_without_grants(atlas,play_dm_client,play_player_user,format):
    w,project=atlas;w=grant(play_dm_client,w,play_player_user,'editor');ids=[]
    for _ in range(3):w,mid=attach(play_dm_client,w,project);ids.append(mid)
    p1=place('One');p1.update(map_id=ids[0],x=1,y=2);p2=place('Two');p2.update(parent_id=p1['id'],map_id=ids[1],x=3,y=4,links=[p1['id']]);w['graph']['places']=[p1,p2]
    for row in w['graph']['maps']:row['reader_visible']=True
    w=graph_save(play_dm_client,w);assert play_dm_client.post(BASE+f'/worlds/{w["id"]}/publish',json=dict(revision=w['revision'],confirm_visible_pixels=True)).status_code==201
    w=play_dm_client.get(BASE+'/worlds/'+w['id']).json;export=play_dm_client.get(BASE+f'/worlds/{w["id"]}/backup?format={format}');assert export.status_code==200
    expected_graph=deepcopy(w['graph']);assert play_dm_client.delete(BASE+'/worlds/'+w['id'],json=dict(revision=w['revision'])).status_code==200
    restored=play_dm_client.post(BASE+'/restore',data=export.data,content_type='application/zip' if format=='zip' else 'application/json');assert restored.status_code==201,restored.json
    assert restored.json['id']==w['id'] and restored.json['graph']==expected_graph and restored.json['members']==[]
    assert sorted(row['id'] for row in restored.json['maps'])==sorted(ids)
    for mid in ids:assert play_dm_client.get(BASE+f'/worlds/{w["id"]}/maps/{mid}.png').status_code==200
    again=play_dm_client.post(BASE+'/restore',data=export.data,content_type='application/zip' if format=='zip' else 'application/json');assert again.status_code==409
    overwrite=play_dm_client.post(BASE+'/restore',data=export.data,headers={'X-Atlas-Revision':str(restored.json['revision'])},content_type='application/zip' if format=='zip' else 'application/json');assert overwrite.status_code==200,overwrite.json

def test_quota_storage_failure_compensation_and_malicious_backup(atlas,play_dm_client,play_dm_user,play_app,monkeypatch):
    w,project=atlas;path=BASE+'/worlds/'+w['id'];used=play_dm_user.storage_used_gb
    play_dm_user.storage_quota_gb=0;db.session.commit()
    response=play_dm_client.post(path+'/maps',json=dict(revision=w['revision'],project_id=project['id'],project_revision=1,png=png(),credits=''));assert response.status_code==507
    assert AtlasMap.query.count()==0
    play_dm_user.storage_quota_gb=1;db.session.commit()
    from vtt import atlas as module
    storage=get_storage_adapter()
    class Failing:
        def upload(self,key,payload):storage.upload(key,payload);raise OSError('synthetic failure')
        def delete(self,key):storage.delete(key)
    monkeypatch.setattr(module,'get_storage_adapter',lambda:Failing())
    response=play_dm_client.post(path+'/maps',json=dict(revision=w['revision'],project_id=project['id'],project_revision=1,png=png(),credits=''));assert response.status_code==503
    assert AtlasMap.query.count()==0;db.session.refresh(play_dm_user);assert play_dm_user.storage_used_gb==used
    from pathlib import Path
    assert not list((Path(play_app.config['LOCAL_STORAGE_PATH'])/'users'/str(play_dm_user.id)/'atlas').rglob('*.json'))
    for names in (['../atlas.json'],['atlas.json','atlas.json'],['atlas.json','extra']):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            for name in names:z.writestr(name,'{}')
        assert play_dm_client.post(BASE+'/restore',data=out.getvalue(),content_type='application/zip').status_code==400

def test_unrelated_admin_foreign_restore_and_old_publication_urls_denied(atlas,play_dm_client,play_player_user,play_player_client,play_app):
    from tests.play_shared import login
    from vtt.models import Role
    w,project=atlas;w,mid=attach(play_dm_client,w,project);path=BASE+'/worlds/'+w['id'];w['graph']['maps'][0]['reader_visible']=True;w=graph_save(play_dm_client,w);w=grant(play_dm_client,w,play_player_user,'reader')
    first=play_dm_client.post(path+'/publish',json=dict(revision=w['revision'],confirm_visible_pixels=True));assert first.status_code==201
    old=path+f'/published/maps/{mid}.png?version='+first.json['id'];assert play_player_client.get(old).status_code==200
    admin=User(username='atlas-unrelated-admin',email='atlas-admin@example.test',role_id=Role.query.filter_by(name='Admin').one().id,is_active=True);admin.set_password('Password123!');db.session.add(admin);db.session.commit()
    client=play_app.test_client();login(client,admin.username)
    assert client.get(path).status_code==404 and client.get(path+'/published').status_code==404 and client.get(old).status_code==404
    backup=play_dm_client.get(path+'/backup');assert play_player_client.post(BASE+'/restore',data=backup.data,content_type='application/json',headers={'X-Atlas-Revision':str(first.json['world_revision'])}).status_code==404
    second=play_dm_client.post(path+'/publish',json=dict(revision=first.json['world_revision'],confirm_visible_pixels=True));assert second.status_code==201
    assert play_player_client.get(old).status_code==404
    assert play_player_client.get(path+f'/published/maps/{mid}.png?version='+second.json['id']).status_code==200

def test_expired_lease_can_be_taken_but_old_editor_cannot_save(atlas,play_dm_client,play_player_user,play_player_client):
    from datetime import timedelta
    from vtt.utils.time import utcnow
    w,project=atlas;w=grant(play_dm_client,w,play_player_user,'editor');w,mid=attach(play_dm_client,w,project);mp=BASE+f'/worlds/{w["id"]}/maps/{mid}';a,b=str(uuid4()),str(uuid4())
    assert play_dm_client.post(mp+'/lease',json=dict(tab=a)).status_code==200
    row=db.session.get(AtlasMap,mid);row.lease_expires=utcnow()-timedelta(seconds=1);db.session.commit()
    assert play_player_client.post(mp+'/lease',json=dict(tab=b)).status_code==200
    bundle=play_player_client.get(mp).json['bundle']
    assert play_dm_client.put(mp,json=dict(tab=a,revision=1,bundle=bundle)).status_code==409
    assert play_player_client.put(mp,json=dict(tab=b,revision=1,bundle=bundle)).status_code==200

def test_rejected_png_and_zip_inflation_never_write_or_publish(atlas,play_dm_client,monkeypatch):
    from vtt import atlas_domain as domain
    w,project=atlas;path=BASE+'/worlds/'+w['id']
    for value in ('data:image/svg+xml;base64,PHN2Zz4=',png().replace('base64,','base64,?')):
        response=play_dm_client.post(path+'/maps',json=dict(revision=w['revision'],project_id=project['id'],project_revision=1,png=value,credits=''))
        assert response.status_code==400,response.json
    assert AtlasMap.query.count()==0 and AtlasPublication.query.count()==0
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:archive.writestr('atlas.json','a'*100000)
    monkeypatch.setattr(domain,'MAX_BACKUP',1000)
    assert len(out.getvalue())<1000
    assert play_dm_client.post(BASE+'/restore',data=out.getvalue(),content_type='application/zip').status_code==400

def test_restore_mints_fresh_publication_even_for_modified_own_backup(atlas,play_dm_client,play_player_user,play_player_client):
    w,project=atlas;w,mid=attach(play_dm_client,w,project);path=BASE+'/worlds/'+w['id'];w['graph']['maps'][0]['reader_visible']=True;w=graph_save(play_dm_client,w);w=grant(play_dm_client,w,play_player_user,'reader')
    published=play_dm_client.post(path+'/publish',json=dict(revision=w['revision'],confirm_visible_pixels=True));assert published.status_code==201
    old_id=published.json['id'];backup=play_dm_client.get(path+'/backup').json;backup['publication']['projection']['summary']='Explicitly restored snapshot'
    result=play_dm_client.post(BASE+'/restore',json=backup,headers={'X-Atlas-Revision':str(published.json['world_revision'])});assert result.status_code==200,result.json
    reader=play_player_client.get(path+'/published');assert reader.json['publication_id']!=old_id
    assert reader.json['projection']['summary']=='Explicitly restored snapshot'
    assert play_player_client.get(path+f'/published/maps/{mid}.png?version='+old_id).status_code==404
    assert result.json['graph']==w['graph'] and result.json['members'][0]['username']==play_player_user.username
