"""Behavioral boundaries for history, settings, lighting and accepted initiative."""
import base64
import io
from uuid import uuid4
import pytest
from PIL import Image
from tests.test_session_feedback import table, base
from tests.test_table_contexts import enter
from tests.play_shared import add_map,create_session
from vtt.extensions import db
from vtt.models import ChatMessage, SceneLight, SceneWall, SceneLayer, CampaignMap
from vtt.models.ui_playtable import InitiativeCandidate

pytest_plugins=['tests.play_shared']


def test_rerolls_wait_for_dm_decision_and_replay_is_not_a_new_candidate(table,play_player_client,play_dm_client):
    campaign,session,member,hero,secret=table
    player=enter(play_player_client,campaign,session);dm=enter(play_dm_client,campaign,session,'dm')
    path=base(table)+'/initiative-candidates'
    first={'token_id':hero.id,'total':12,'event_id':str(uuid4())}
    assert play_player_client.post(path,json=first,headers=player).status_code==200
    second={'token_id':hero.id,'total':22,'event_id':str(uuid4())}
    rolled=play_player_client.post(path,json=second,headers=player);assert rolled.status_code==200
    db.session.refresh(hero);assert hero.initiative==12
    assert play_player_client.post(path,json=second,headers=player).status_code==200
    assert InitiativeCandidate.query.filter_by(token_id=hero.id).count()==2
    result=play_dm_client.get(path,headers=dm).json
    pending=next(r for r in result['candidates'] if r['status']=='pending')
    accept=path+f"/{pending['id']}/accept"
    assert play_player_client.post(accept,json={'revision':result['revision']},headers=player).status_code==403
    owner_player=enter(play_dm_client,campaign,session,'player')
    assert play_dm_client.post(accept,json={'revision':result['revision']},headers=owner_player).status_code==403
    assert play_dm_client.post(accept,json={'revision':0},headers=dm).status_code==409
    accepted=play_dm_client.post(accept,json={'revision':result['revision']},headers=dm)
    assert accepted.status_code==200
    db.session.refresh(hero);assert hero.initiative==22
    revision=play_dm_client.get(path,headers=dm).json['revision']
    assert play_dm_client.post(path+'/reset',json={'revision':revision,'confirm':True},headers=dm).status_code==200
    db.session.refresh(hero);assert hero.initiative is None
    assert play_player_client.put(f'/api/campaigns/{campaign.id}/sessions/{session.id}/tokens/{hero.id}',json={'patch':{'initiative':99}},headers=player).status_code==403


def test_legacy_history_rechecks_membership_and_filters_private_or_moderated_rows(table,play_player_client,play_player_user):
    campaign,session,member,hero,secret=table
    for content,visibility,moderation in [('old public','public','visible'),('secret','gm_only','visible'),('hidden result','blind','visible'),('moderated','public','hidden')]:
        db.session.add(ChatMessage(campaign_id=campaign.id,game_session_id=session.id,
            author_user_id=play_player_user.id,content=content,visibility=visibility,moderation_state=moderation))
    db.session.commit()
    path=f'/api/campaign-rooms/{campaign.id}/history'
    response=play_player_client.get(path)
    assert response.status_code==200
    assert [r['content'] for r in response.json['messages']]==['old public']
    assert response.json['messages'][0]['session_id']==session.id
    assert play_player_client.get(path+'?before=-1').status_code==400
    member.status='left';db.session.commit()
    assert play_player_client.get(path).status_code==404


def test_grid_settings_require_dm_context_and_revision(table,play_player_client,play_dm_client):
    campaign,session,member,hero,secret=table
    player=enter(play_player_client,campaign,session);dm=enter(play_dm_client,campaign,session,'dm')
    path=base(table)+f'/maps/{session.map_id}/presentation'
    body={'revision':0,'grid_size':96,'grid_visible':False,'ambient':30}
    assert play_player_client.put(path,json=body,headers=player).status_code==403
    owner_player=enter(play_dm_client,campaign,session,'player')
    assert play_dm_client.put(path,json=body,headers=owner_player).status_code==403
    response=play_dm_client.put(path,json=body,headers=dm)
    assert response.status_code==200,response.json
    assert response.json['presentation']['grid_visible'] is False
    db.session.refresh(hero);assert hero.x==32 and hero.y==32 and hero.metadata_json['position_mode']=='pixel'
    assert play_dm_client.put(path,json=body,headers=dm).status_code==409
    payload=play_player_client.get(base(table)+'/bootstrap',headers=player).json
    assert payload['state_payload']['active_map']['grid_size']==96
    assert payload['state_payload']['active_map']['presentation']['grid_visible'] is False


def test_campaign_hierarchy_blocks_cycles_and_does_not_expose_hidden_parents(table,play_dm_client,play_dm_user,play_player_client):
    campaign,session,*_=table
    other=add_map(campaign,play_dm_user,'Child page')
    dm=enter(play_dm_client,campaign,session,'dm');player=enter(play_player_client,campaign,session)
    assert play_dm_client.post(base(table)+'/scene-stack/init',json={},headers=dm).status_code in (200,201)
    layers=SceneLayer.query.order_by(SceneLayer.id).all();parent,child=layers[:2]
    parent.is_player_visible=False;child.is_player_visible=True;db.session.commit()
    path=base(table)+f'/scene-stack/layers/{child.id}/parent'
    r=play_dm_client.put(path,json={'revision':0,'parent_layer_id':parent.id},headers=dm)
    assert r.status_code==200,r.json
    bad=base(table)+f'/scene-stack/layers/{parent.id}/parent'
    assert play_dm_client.put(bad,json={'revision':1,'parent_layer_id':child.id},headers=dm).status_code==422
    assert play_player_client.put(path,json={'revision':1,'parent_layer_id':None},headers=player).status_code==403
    visible=play_player_client.get(base(table)+'/bootstrap',headers=player).json['scene_stack']['layers']
    assert len(visible)==1 and visible[0]['id']==child.id and visible[0]['parent_layer_id'] is None
    followup=create_session(campaign,'Later session',status='in_progress',map_id=session.map_id)
    followup_context=enter(play_dm_client,campaign,followup,'dm')
    later=f'/api/play/campaigns/{campaign.id}/sessions/{followup.id}'
    initialized=play_dm_client.post(later+'/scene-stack/init',json={},headers=followup_context)
    assert initialized.status_code==201
    projected=play_dm_client.get(later+'/bootstrap',headers=followup_context).json['scene_stack']['layers']
    projected_by_map={layer['campaign_map_id']:layer for layer in projected}
    assert projected_by_map[child.campaign_map_id]['parent_layer_id']==projected_by_map[parent.campaign_map_id]['id']


def test_lighting_is_a_private_wall_clipped_image_and_preview_does_not_write_fog(table,play_player_client,play_dm_client,play_dm_user):
    campaign,session,member,hero,secret=table
    map_=db.session.get(CampaignMap,session.map_id);map_.width=400;map_.height=300;map_.fog_enabled=True
    hero.x=30;hero.y=50;hero.sight_range=None;hero.metadata_json={"position_mode":"pixel"}
    db.session.add(SceneWall(campaign_map_id=map_.id,x0=90,y0=0,x1=90,y1=100,sight='normal',light='normal',created_by=play_dm_user.id))
    db.session.add(SceneLight(campaign_map_id=map_.id,x=30,y=50,bright_radius=50,dim_radius=150,created_by=play_dm_user.id))
    db.session.commit()
    player=enter(play_player_client,campaign,session);dm=enter(play_dm_client,campaign,session,'dm')
    path=base(table)+'/vision/illumination'
    result=play_player_client.get(path,headers=player)
    assert result.status_code==200,result.json
    assert set(result.json)=={'map_id','presentation','preview','overlay'}
    image=Image.open(io.BytesIO(base64.b64decode(result.json['overlay'].split(',')[1])))
    assert image.getpixel((30,50))[3]<80
    assert image.getpixel((130,50))[3]==255
    assert play_player_client.get(path+f'?token_id={secret.id}',headers=player).status_code==403
    assert play_dm_client.get(path,headers=dm).json['overlay'] is None
    from vtt.models import FogOfWarState
    before=FogOfWarState.query.count()
    preview=play_dm_client.get(path+f'?token_id={hero.id}',headers=dm).json
    assert preview['preview'] is True and secret.id not in preview['visible_token_ids']
    assert FogOfWarState.query.count()==before


def test_new_template_token_preserves_finite_sight_and_rejects_bad_values(table,play_player_client):
    campaign,session,member,hero,secret=table
    context=enter(play_player_client,campaign,session)
    path=f'/api/campaigns/{campaign.id}/sessions/{session.id}/tokens'
    payload={'name':'Finite-sight clone','x':420,'y':420,'token_type':'player','sight_range':120,'metadata_json':{'position_mode':'pixel'}}
    response=play_player_client.post(path,json={'token':payload},headers=context)
    assert response.status_code==201,response.json
    assert response.json['token']['sight_range']==120
    for bad in [-1,True,'120']:
        assert play_player_client.post(path,json={'token':{**payload,'sight_range':bad}},headers=context).status_code==400


def test_darkness_matches_fog_exclusion_and_large_light_radius_is_bounded():
    from types import SimpleNamespace as Row
    from vtt.play.illumination import render_overlay
    from vtt.play.vision import calculate_visible_cells,map_world_size
    wall=Row(x0=70,y0=0,x1=70,y1=100,sight='none',light='normal')
    dark=Row(x=110,y=50,bright_radius=80,dim_radius=80,light_type='darkness',provides_vision=False)
    token=Row(x=20,y=50,sight_range=None)
    overlay=render_overlay(200,100,[wall],[dark],[token],ambient=100,grid_size=10)
    image=Image.open(io.BytesIO(base64.b64decode(overlay.split(',')[1])))
    assert (5,5) not in calculate_visible_cells(20,50,None,[wall],[dark],10)
    assert image.getpixel((50,50))[3]==255
    huge=Row(x=20,y=50,bright_radius=1000000,dim_radius=2000000,light_type='light',provides_vision=True)
    assert len(render_overlay(200,100,[],[huge],[token],ambient=25,grid_size=10))<100000
    assert map_world_size(Row(width=20,height=15,grid_size=70))==(1400,1050)
    assert map_world_size(Row(width=128,height=96,grid_size=96,light_rules={'dimensions_mode':'pixel'}))==(128,96)


def test_walls_work_without_lights_and_disabled_lighting_retains_fog(table,play_player_client,play_dm_client,play_dm_user):
    from vtt.models.ui_playtable import MapViewSettings
    campaign,session,member,hero,secret=table
    map_=db.session.get(CampaignMap,session.map_id);map_.width=400;map_.height=300
    hero.x=30;hero.y=50;hero.metadata_json={'position_mode':'pixel'}
    db.session.add(SceneWall(campaign_map_id=map_.id,x0=90,y0=0,x1=90,y1=300,sight='normal',light='normal',created_by=play_dm_user.id))
    db.session.commit()
    player=enter(play_player_client,campaign,session);dm=enter(play_dm_client,campaign,session,'dm')
    path=base(table)+'/vision/illumination'
    def alpha(result,x,y):
        return Image.open(io.BytesIO(base64.b64decode(result['overlay'].split(',')[1]))).getpixel((x,y))[3]
    result=play_player_client.get(path,headers=player).json
    assert result['overlay'] and alpha(result,130,50)==255
    settings=MapViewSettings(map_id=map_.id,dynamic_lighting=False,grid_visible=True,ambient=25)
    db.session.add(settings);db.session.commit()
    assert play_player_client.get(path,headers=player).json['overlay'] is None
    assert play_dm_client.get(path+f'?token_id={hero.id}',headers=dm).json['overlay'] is None
    map_.fog_enabled=True;db.session.commit()
    for suffix,context,client in [('',player,play_player_client),(f'?token_id={hero.id}',dm,play_dm_client)]:
        result=client.get(path+suffix,headers=context).json
        assert alpha(result,30,50)==0 and alpha(result,130,50)==255
