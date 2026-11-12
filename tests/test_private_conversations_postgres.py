"""Real row-lock contention in a disposable, guarded PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from flask_jwt_extended import create_access_token
from tests.test_session_calendar_postgres import pg_calendar  # noqa:F401
from vtt.extensions import db
from vtt.models import User,Campaign,CampaignMember,Role,PrivateConversation,PrivateMessage
pytestmark=pytest.mark.postgres

@pytest.fixture
def pair_workers(pg_calendar):
    app,_=pg_calendar
    with app.app_context():
        campaign=Campaign.query.one();owner=campaign.owner_id
        peer=User(username='private-peer',email='peer@example.test',role_id=Role.query.first().id,
                  password_hash='test',account_state='active',is_active=True)
        db.session.add(peer);db.session.flush();peer_id=peer.id
        db.session.add(CampaignMember(campaign_id=campaign.id,user_id=peer.id,campaign_role='PLAYER',status='active'));db.session.commit()
        cid=campaign.id;tokens={uid:create_access_token(identity=str(uid)) for uid in (owner,peer_id)}
    def api(uid,path='',body=None):
        with app.test_client() as client:
            client.set_cookie('access_token_cookie',tokens[uid]);return client.post('/api/private-conversations'+path,json=body)
    return app,api,cid,owner,peer_id

def test_opposite_concurrent_pair_creation_and_message_replays(pair_workers):
    app,api,cid,owner,peer=pair_workers;barrier=Barrier(4)
    def open_pair(index):
        actor,target=(owner,peer) if index%2 else (peer,owner);barrier.wait(timeout=10)
        response=api(actor,body={'campaign_id':cid,'recipient_user_id':target});return response.status_code,response.json
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(open_pair,range(4)))
    assert sorted(status for status,_ in results)==[200,200,200,201],results
    ids={row['conversation']['id'] for _,row in results};assert len(ids)==1;conversation=ids.pop()
    body={'content':'same confirmed text','client_event_id':str(uuid4())};barrier=Barrier(4)
    def send(_):
        barrier.wait(timeout=10);response=api(owner,f'/{conversation}/messages',body);return response.status_code,response.json
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(send,range(4)))
    assert sorted(status for status,_ in results)==[200,200,200,201],results
    assert len({row['message']['id'] for _,row in results})==1
    with app.app_context():assert PrivateConversation.query.count()==1 and PrivateMessage.query.count()==1
