"""Private pair authorization, immutable payloads, revocation and bounded history."""
from datetime import datetime
from uuid import uuid4
import pytest
from flask_jwt_extended import create_access_token
from tests.test_c06_calendar import world  # noqa:F401
from vtt.extensions import db
from vtt.models import Campaign,CampaignMember,PrivateConversation,PrivateMessage,Role,User

@pytest.fixture
def private(world):
    app,_,_,campaigns,users=world
    client=app.test_client();tokens={k:create_access_token(identity=str(v)) for k,v in users.items()}
    def api(who,method='',path='',body=None):
        client.set_cookie('access_token_cookie',tokens[who]);return client.open('/api/private-conversations'+path,method=method or 'GET',json=body)
    def pair(who=2,recipient=3,campaign='A'):
        return api(who,'POST',body={'campaign_id':campaigns[campaign],'recipient_user_id':users[recipient]})
    yield app,api,pair,campaigns,users

def test_pair_is_private_even_from_campaign_owner_admin_and_other_members(private):
    app,api,pair,c,u=private
    opened=pair();assert opened.status_code==201,opened.json
    cid=opened.json['conversation']['id']
    event={'content':'<script>PRIVATE TEXT</script>','client_event_id':str(uuid4())}
    sent=api(2,'POST',f'/{cid}/messages',event);assert sent.status_code==201
    assert pair(3,2).json['conversation']['id']==cid
    role=Role(name='Admin');db.session.add(role);db.session.flush();db.session.get(User,u[10]).role_id=role.id
    db.session.add(CampaignMember(campaign_id=c['A'],user_id=u[10],campaign_role='DM',status='active'));db.session.commit()
    for who in [1,4,5,6,7,8,9,10]:
        listed=api(who);assert listed.status_code==200 and listed.json['conversations']==[],who
        response=api(who,path=f'/{cid}');assert response.status_code==404 and response.json=={'error':'not found'},who
        assert api(who,'POST',f'/{cid}/messages',event).status_code==404
        assert 'PRIVATE TEXT' not in response.get_data(as_text=True)
        assert response.headers['Cache-Control']=='private, no-store'
    for who in [2,3]:
        response=api(who,path=f'/{cid}');assert response.json['messages'][0]['content']==event['content']
        assert response.json['conversation']['can_send'] is True
    assert PrivateConversation.query.count()==1 and PrivateMessage.query.count()==1

@pytest.mark.parametrize('recipient',[6,7,8,9,10])
def test_no_pair_to_invited_removed_pending_or_outsider(private,recipient):
    _,_,pair,_,_=private
    assert pair(recipient=recipient).status_code==404
    assert PrivateConversation.query.count()==0

def test_current_membership_and_account_checks_precede_read_send_and_replay(private):
    _,api,pair,c,u=private;cid=pair().json['conversation']['id']
    body={'content':'one confirmed message','client_event_id':str(uuid4())}
    first=api(2,'POST',f'/{cid}/messages',body);assert first.status_code==201
    retry=api(2,'POST',f'/{cid}/messages',body);assert retry.status_code==200 and retry.json['message']['id']==first.json['message']['id']
    assert api(2,'POST',f'/{cid}/messages',{**body,'content':'changed'}).status_code==409
    CampaignMember.query.filter_by(campaign_id=c['A'],user_id=u[3]).one().status='left';db.session.commit()
    assert api(3).json['conversations']==[] and api(3,path=f'/{cid}').status_code==404
    assert api(3,'POST',f'/{cid}/messages',body).status_code==404
    remaining=api(2,path=f'/{cid}');assert remaining.status_code==200 and remaining.json['conversation']['can_send'] is False
    assert remaining.json['messages'][0]['content']==body['content']
    assert api(2,'POST',f'/{cid}/messages',body).status_code==409
    db.session.get(User,u[2]).is_active=False;db.session.commit()
    assert api(2,path=f'/{cid}').status_code==404
    assert PrivateMessage.query.count()==1

def test_campaign_scope_self_pair_and_payload_limits(private):
    _,api,pair,c,u=private
    assert pair(2,2).status_code==400
    assert pair(2,3,'B').status_code==404
    cid=pair().json['conversation']['id']
    for body in [{'content':'','client_event_id':str(uuid4())},{'content':' '*10,'client_event_id':str(uuid4())},
                 {'content':'x'*2001,'client_event_id':str(uuid4())},{'content':'\ud800','client_event_id':str(uuid4())},{'content':'x','client_event_id':'bad'},
                 {'content':'x','client_event_id':str(uuid4()),'author_user_id':u[3]},
                 {'content':'x','client_event_id':str(uuid4()),'attachment':'https://example.test'}]:
        assert api(2,'POST',f'/{cid}/messages',body).status_code==400
    assert api(2,'POST',f'/{cid}/messages',{'content':'x'*2000,'client_event_id':str(uuid4())}).status_code==201
    db.session.get(Campaign,c['A']).deleted_at=datetime.utcnow();db.session.commit()
    assert api(2).json['conversations']==[] and api(2,path=f'/{cid}').status_code==404

def test_history_cursors_are_stable_and_never_cross_a_pair(private):
    _,api,pair,_,u=private;cid=pair().json['conversation']['id'];other=pair(2,5).json['conversation']['id']
    for i in range(65):db.session.add(PrivateMessage(conversation_id=cid,author_user_id=u[2],client_event_id=str(uuid4()),content=f'message {i}'))
    db.session.add(PrivateMessage(conversation_id=other,author_user_id=u[5],client_event_id=str(uuid4()),content='other private content'));db.session.commit()
    page=api(2,path=f'/{cid}').json;assert len(page['messages'])==50 and page['more']
    older=api(2,path=f'/{cid}?before={page["oldest_id"]}').json
    assert len(older['messages'])==15 and not older['more']
    assert len({m['id'] for m in page['messages']+older['messages']})==65
    new=api(2,path=f'/{cid}?after={older["newest_id"]}').json
    assert [m['id'] for m in new['messages']]==[m['id'] for m in page['messages']]
    assert all('other private' not in m['content'] for m in new['messages'])
    for query in ['after=-1','before=abc','after=1&before=2','before=0','after=99999999999']:
        assert api(2,path=f'/{cid}?{query}').status_code==400
    assert api(2,path='?cursor=not-a-cursor').status_code==400

def test_pair_owner_and_member_can_talk_without_touching_campaign_or_table_payloads(private,world,monkeypatch):
    from vtt.extensions import socketio
    from vtt.models import ChatMessage
    _,api,pair,c,_=private
    _,campaign_call,_,_,_=world
    emitted=[];monkeypatch.setattr(socketio,'emit',lambda *args,**kwargs:emitted.append((args,kwargs)))
    cid=pair(1,2).json['conversation']['id']
    assert api(1,'POST',f'/{cid}/messages',{'content':'UNIQUE_PRIVATE_BODY','client_event_id':str(uuid4())}).status_code==201
    response=campaign_call(2,'GET',str(c['A']))
    assert response.status_code==200
    assert 'UNIQUE_PRIVATE_BODY' not in response.get_data(as_text=True)
    assert 'private_conversations' not in response.json and ChatMessage.query.count()==0 and emitted==[]

def test_conversation_list_uses_a_bounded_stable_cursor(private):
    _,api,_,_,u=private
    for i in range(29):
        campaign=Campaign(name=f'Own campaign {i}',owner_id=u[1]);db.session.add(campaign);db.session.flush()
        db.session.add(CampaignMember(campaign_id=campaign.id,user_id=u[2],campaign_role='PLAYER',status='active'))
        db.session.add(PrivateConversation(campaign_id=campaign.id,participant_low_id=min(u[1],u[2]),participant_high_id=max(u[1],u[2])))
    db.session.commit()
    first=api(1).json;assert len(first['conversations'])==24 and first['next_cursor']
    second=api(1,path='?cursor='+first['next_cursor']).json;assert len(second['conversations'])==5 and not second['next_cursor']
    assert len({row['id'] for row in first['conversations']+second['conversations']})==29
