"""Concurrent table requests must share one bound companion and preserve damage."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from flask_jwt_extended import create_access_token
from tests.test_session_calendar_postgres import pg_calendar  # noqa: F401
from tests.play_shared import add_map, create_session, create_token
from vtt.extensions import db
from vtt.models import Campaign, Character, User, TokenState
from vtt.models.table_companion import TableCompanionBinding
from vtt.play.service import ensure_session_state

pytestmark=pytest.mark.postgres


def test_concurrent_placements_retries_and_damage_share_one_token(pg_calendar):
    app,_=pg_calendar
    with app.app_context():
        campaign=Campaign.query.one();owner=db.session.get(User,campaign.owner_id)
        map_=add_map(campaign,owner);session=create_session(campaign,status='in_progress',map_id=map_.id)
        state=ensure_session_state(campaign,session)
        char=Character(user_id=owner.id,campaign_id=campaign.id,name='Concurrent hero',character_data={'srdCompanions':[dict(id='c12345678',name='Concurrent wolf',kind='Wolf',speed='',hpMax=20,hpCurrent=13,ac=13,attacks='',notes='')]})
        db.session.add(char);db.session.commit()
        parent=create_token(campaign,session,state,owner.id);parent.character_id=char.id;db.session.commit()
        cid,sid,charid,pid,version=campaign.id,session.id,char.id,parent.id,parent.version
        auth=create_access_token(identity=str(owner.id))
    base=f'/api/play/campaigns/{cid}/sessions/{sid}'
    with app.test_client() as client:
        client.set_cookie('access_token_cookie',auth)
        seat=client.post(base+'/contexts',json={'mode':'dm','tab':str(uuid4())})
        assert seat.status_code==201,seat.json
        headers={'X-VTT-Context':seat.json['token'],'X-VTT-Tab':seat.json['tab']}
    path=base+f'/characters/{charid}/companions/c12345678/place'
    def send(body):
        with app.test_client() as client:
            client.set_cookie('access_token_cookie',auth)
            return client.post(path,json=body,headers=headers)
    def contend(bodies):
        barrier=Barrier(len(bodies))
        def apply(body):barrier.wait(timeout=20);return send(body)
        with ThreadPoolExecutor(max_workers=len(bodies)) as pool:return list(pool.map(apply,bodies))
    def payload():return {'parent_token_id':pid,'parent_version':version,'request_id':str(uuid4())}
    results=contend([payload() for _ in range(4)])
    assert [r.status_code for r in results]==[200]*4,[r.json for r in results]
    assert len({r.json['token']['id'] for r in results})==1
    with app.app_context():
        assert TableCompanionBinding.query.count()==1
        binding=TableCompanionBinding.query.one();tid=binding.token_id
        token=db.session.get(TokenState,tid);assert (token.hp_max,token.hp_current)==(20,13)
        token.hp_current=7;token.version+=1;db.session.commit()
    body=payload();results=contend([body]*4)
    assert all(r.status_code in {200,409} for r in results),[r.json for r in results]
    replay=send(body);assert replay.status_code==200
    with app.app_context():
        assert TableCompanionBinding.query.count()==1
        assert db.session.get(TokenState,tid).hp_current==7
        assert TokenState.query.filter_by(game_session_id=sid,character_id=None).count()==1
