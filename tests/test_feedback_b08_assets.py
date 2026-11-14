import io
import pytest
from PIL import Image
from tests.play_shared import create_campaign,create_session,add_member,enter_table
from vtt.extensions import db
from vtt.models import Asset,User

pytest_plugins=['tests.play_shared']

def image():
    out=io.BytesIO();Image.new('RGB',(64,64),(130,80,50)).save(out,format='PNG');return out.getvalue()

def upload(client,cid,**fields):
    return client.post(f'/api/assets/campaigns/{cid}/upload',data={'file':(io.BytesIO(image()),'map.png'),'asset_type':'handout',**fields},content_type='multipart/form-data')

@pytest.fixture
def library(play_app,play_dm_user,play_player_user,play_dm_client,tmp_path):
    play_app.config.update(STORAGE_PROVIDER='local',LOCAL_STORAGE_PATH=str(tmp_path/'assets'))
    play_dm_user.storage_quota_gb=1;play_player_user.storage_quota_gb=1;db.session.commit()
    campaign=create_campaign(play_dm_user,'Journal');add_member(campaign,play_player_user)
    session=create_session(campaign,status='in_progress');other=create_session(campaign,'Other',status='in_progress')
    return campaign,session,other

def test_session_upload_private_reveal_rename_and_scoped_media(library,play_dm_client,play_player_client,play_dm_user):
    campaign,session,other=library
    enter_table(play_dm_client,campaign,session,'dm');enter_table(play_player_client,campaign,session,'player')
    saved=upload(play_dm_client,campaign.id,session_id=str(session.id));assert saved.status_code==201,saved.json
    aid=saved.json['asset_id'];asset=db.session.get(Asset,aid);key=asset.storage_key;digest=asset.checksum_md5
    assert asset.session_id==session.id and asset.scope=='session' and not asset.is_public
    for endpoint in ['preview','thumbnail','download','versions']:assert play_player_client.get(f'/api/assets/{aid}/{endpoint}').status_code==403
    assert play_dm_client.patch(f'/api/assets/{aid}/metadata',json={'filename':'Speichern – Übersicht.png'}).status_code==200
    db.session.refresh(asset);assert asset.storage_key==key and asset.checksum_md5==digest
    inline=play_dm_client.get(f'/api/assets/{aid}/preview');assert inline.status_code==200 and "filename*=UTF-8''" in inline.headers['Content-Disposition']
    assert play_dm_client.patch(f'/api/assets/{aid}/visibility',json={'is_public':True}).status_code==200
    own=play_player_client.get(f'/api/assets/campaigns/{campaign.id}/library?scope=current&session_id={session.id}').json
    assert [r['id'] for r in own['assets']]==[aid]
    for endpoint in ['preview','thumbnail','download','versions']:assert play_player_client.get(f'/api/assets/{aid}/{endpoint}').status_code==200
    assert play_dm_client.patch(f'/api/assets/{aid}/visibility',json={'is_public':False}).status_code==200
    assert play_player_client.get(f'/api/assets/{aid}/preview').status_code==403


def test_owner_player_cannot_manage_or_read_hidden_handout(library,play_dm_client):
    campaign,session,other=library;created=upload(play_dm_client,campaign.id);assert created.status_code==201
    aid=created.json['asset_id'];enter_table(play_dm_client,campaign,session,'player')
    assert play_dm_client.patch(f'/api/assets/{aid}/metadata',json={'filename':'No.png'}).status_code==403
    assert play_dm_client.patch(f'/api/assets/{aid}/visibility',json={'is_public':True}).status_code==403
    assert play_dm_client.delete(f'/api/assets/{aid}/delete').status_code==403
    for path in ['preview','thumbnail','download','versions']:assert play_dm_client.get(f'/api/assets/{aid}/{path}').status_code==403
    assert upload(play_dm_client,campaign.id,session_id=str(session.id)).status_code==403


def test_other_session_and_campaign_resources_are_denied(library,play_dm_client,play_dm_user):
    campaign,session,other=library
    result=upload(play_dm_client,campaign.id,session_id=str(other.id));assert result.status_code==201
    aid=result.json['asset_id'];foreign=create_campaign(play_dm_user,'Foreign')
    foreign_asset=upload(play_dm_client,foreign.id,asset_type='image').json['asset_id']
    enter_table(play_dm_client,campaign,session,'dm')
    assert upload(play_dm_client,campaign.id,session_id=str(other.id)).status_code==403
    assert play_dm_client.get(f'/api/assets/campaigns/{campaign.id}/library?scope=current&session_id={other.id}').status_code==403
    assert play_dm_client.get(f'/api/assets/campaigns/{campaign.id}/library').json['assets']==[]
    for asset_id in [aid,foreign_asset]:
        for path in ['preview','thumbnail','download','versions']:assert play_dm_client.get(f'/api/assets/{asset_id}/{path}').status_code==403
        assert play_dm_client.patch(f'/api/assets/{asset_id}/metadata',json={'filename':'No.png'}).status_code==403
        assert play_dm_client.delete(f'/api/assets/{asset_id}/delete').status_code==403


@pytest.mark.parametrize('body',[{'filename':''},{'filename':'x\ny.png'},{'filename':'../file.png'},{'filename':'x.png','storage_key':'foreign'},{'filename':'x'*256}])
def test_invalid_labels_leave_file_unchanged(library,play_dm_client,body):
    campaign,session,other=library;created=upload(play_dm_client,campaign.id);aid=created.json['asset_id']
    assert play_dm_client.patch(f'/api/assets/{aid}/metadata',json=body).status_code==400
    assert db.session.get(Asset,aid).filename=='map.png'


def test_session_bound_refunds_quota_and_creates_no_file(library,play_dm_client,play_dm_user):
    campaign,session,other=library
    for index in range(100):db.session.add(Asset(campaign_id=campaign.id,session_id=session.id,uploaded_by=play_dm_user.id,filename=f'{index}.png',mime_type='image/png',size_bytes=1,asset_type='image',scope='session'))
    db.session.commit();before=db.session.get(User,play_dm_user.id).storage_used_gb
    result=upload(play_dm_client,campaign.id,session_id=str(session.id));assert result.status_code==400 and '100' in result.json['error']
    assert Asset.query.filter_by(session_id=session.id).count()==100
    db.session.expire_all();assert abs((db.session.get(User,play_dm_user.id).storage_used_gb or 0)-(before or 0))<1e-12
