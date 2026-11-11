import pytest
from tests.play_shared import create_campaign,add_map,create_session,enter_table,add_member
from vtt.extensions import db
from vtt.play.service import ensure_session_state

pytest_plugins=['tests.play_shared']

@pytest.fixture
def scaled_table(play_dm_user,play_player_user,play_player_client,play_dm_client):
    campaign=create_campaign(play_dm_user,'Scale');add_member(campaign,play_player_user)
    map_=add_map(campaign,play_dm_user);session=create_session(campaign,status='in_progress',map_id=map_.id)
    ensure_session_state(campaign,session)
    enter_table(play_player_client,campaign,session)
    enter_table(play_dm_client,campaign,session,'dm')
    return campaign,session,map_,f'/api/play/campaigns/{campaign.id}/sessions/{session.id}/maps/{map_.id}/scale'


def test_dm_scale_cas_and_public_bootstrap_without_pixel_changes(scaled_table,play_dm_client,play_player_client):
    campaign,session,map_,path=scaled_table;old_pixels=map_.grid_size
    assert play_player_client.get(path).json['scale']=={'revision':0,'meters_per_square':None}
    saved=play_dm_client.put(path,json={'revision':0,'meters_per_square':1.5})
    assert saved.status_code==200 and saved.json['scale']=={'revision':1,'meters_per_square':1.5}
    assert play_dm_client.put(path,json={'revision':0,'meters_per_square':3}).status_code==409
    bootstrap=play_player_client.get(f'/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap').json
    assert bootstrap['state_payload']['active_map']['measurement_scale']['meters_per_square']==1.5
    db.session.refresh(map_);assert map_.grid_size==old_pixels
    assert play_dm_client.put(path,json={'revision':1,'meters_per_square':None}).json['scale']=={'revision':2,'meters_per_square':None}


def test_owner_as_player_cannot_calibrate_or_escalate(scaled_table,play_dm_client,play_player_client):
    campaign,session,map_,path=scaled_table
    assert play_player_client.put(path,json={'revision':0,'meters_per_square':1.5}).status_code==403
    enter_table(play_dm_client,campaign,session,'player')
    assert play_dm_client.put(path,json={'revision':0,'meters_per_square':1.5}).status_code==403
    enter_table(play_dm_client,campaign,session,'dm')
    assert play_dm_client.put(path,json={'revision':0,'meters_per_square':1.5}).status_code==200


@pytest.mark.parametrize('value',[0,-1,1000001,1.12345,True,'1.5',float('nan'),float('inf')])
def test_scale_refuses_invalid_numbers(scaled_table,play_dm_client,value):
    *_,path=scaled_table
    assert play_dm_client.put(path,json={'revision':0,'meters_per_square':value}).status_code==422
    assert play_dm_client.get(path).json['scale']['revision']==0


def test_foreign_map_and_no_context_are_refused(scaled_table,play_dm_client,play_dm_user,play_outsider_client):
    campaign,session,map_,path=scaled_table
    foreign=create_campaign(play_dm_user,'Other scale');other_map=add_map(foreign,play_dm_user)
    wrong=path.replace(f'/maps/{map_.id}/',f'/maps/{other_map.id}/')
    assert play_dm_client.put(wrong,json={'revision':0,'meters_per_square':1.5}).status_code==404
    assert play_outsider_client.get(path).status_code==403
    play_dm_client.environ_base.pop('HTTP_X_VTT_CONTEXT');play_dm_client.environ_base.pop('HTTP_X_VTT_TAB')
    assert play_dm_client.put(path,json={'revision':0,'meters_per_square':1.5}).status_code==403
