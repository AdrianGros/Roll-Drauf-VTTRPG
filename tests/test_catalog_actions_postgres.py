"""Old/new writers contend on real Character locks in an isolated PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from flask_jwt_extended import create_access_token
from tests.test_session_calendar_postgres import pg_calendar  # noqa:F401
from tests.test_srd_creator_api import wizard_state
from tests.test_srd_inventory import DAGGER
from vtt.characters import srd_inventory
from vtt.extensions import db
from vtt.models import Campaign,CampaignMap,CampaignMember,Character,CharacterCatalogReceipt,GameSession,InventoryItem,Role,TokenLoot,User
from vtt.play.service import ensure_session_state
from vtt.rules_content.creator_drafts import character_values
from vtt.rules_content.creator_rules import evaluate,load_creator_data
pytestmark=pytest.mark.postgres

@pytest.fixture
def writers(pg_calendar):
    app,_=pg_calendar
    with app.app_context():
        campaign=Campaign.query.one();owner=campaign.owner_id
        player=User(username='catalog-owner',email='catalog-owner@example.test',role_id=Role.query.first().id,password_hash='test',is_active=True,account_state='active')
        db.session.add(player);db.session.flush();pid=player.id
        db.session.add(CampaignMember(campaign_id=campaign.id,user_id=pid,campaign_role='PLAYER',status='active'))
        data=load_creator_data();state=wizard_state(data,'Concurrent catalog figure')
        char=Character(user_id=pid,campaign_id=campaign.id,**character_values(data,state,evaluate(data,state),draft_id=1,finalized_at='2026-11-12T10:00:00Z'))
        db.session.add(char);db.session.commit();char_id=char.id;cid=campaign.id
        tokens={uid:create_access_token(identity=str(uid)) for uid in (owner,pid)}
    def api(uid,path,method='POST',body=None,headers=None):
        with app.test_client() as client:
            client.set_cookie('access_token_cookie',tokens[uid]);return client.open(path,method=method,json=body,headers=headers or {})
    return app,api,cid,owner,pid,char_id

def test_catalog_old_inventory_and_dm_handout_quantities_are_not_lost(writers):
    app,api,_,dm,player,char=writers;barrier=Barrier(9);base=f'/api/srd-creator/characters/{char}'
    def save(i):
        barrier.wait(timeout=15)
        if i%3==0:return api(player,base+'/catalog-add',body={'entity_id':DAGGER,'quantity':1,'request_id':str(uuid4())}).status_code
        if i%3==1:return api(player,base+'/inventory',body={'itemId':DAGGER,'quantity':1}).status_code
        return api(dm,base+'/handout',body={'kind':'gear','itemId':DAGGER,'quantity':1}).status_code
    with ThreadPoolExecutor(max_workers=9) as pool:statuses=list(pool.map(save,range(9)))
    assert sorted(statuses)==[200]*6+[201]*3,statuses
    with app.app_context():assert InventoryItem.query.filter_by(character_id=char).one().quantity==9
    key=str(uuid4());barrier=Barrier(4)
    def replay(_):
        barrier.wait(timeout=10)
        response=api(player,base+'/catalog-add',body={'entity_id':DAGGER,'quantity':1,'request_id':key})
        return response.status_code,response.json
    with ThreadPoolExecutor(max_workers=4) as pool:responses=list(pool.map(replay,range(4)))
    assert sorted(status for status,_ in responses)==[200,200,200,201]
    assert len({r['receipt']['id'] for _,r in responses})==1
    with app.app_context():
        assert InventoryItem.query.filter_by(character_id=char).one().quantity==10
        assert CharacterCatalogReceipt.query.filter_by(character_id=char).count()==4

def test_coins_and_progression_json_writers_preserve_each_other(writers):
    app,api,_,dm,player,char=writers;barrier=Barrier(2);base=f'/api/srd-creator/characters/{char}'
    def save(index):
        barrier.wait(timeout=10)
        return api(player if index==0 else dm,base+('/inventory/coins' if index==0 else '/progression'),method='PUT',
                   body={'delta':{'GM':1}} if index==0 else {'addXp':1000}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(save,range(2)))
    assert statuses==[200,200],statuses
    with app.app_context():
        row=db.session.get(Character,char);assert row.xp==7500
        assert srd_inventory.inventory_state(row)['coins']['GM']==1

def test_table_loot_and_catalog_add_share_the_recipient_lock(writers):
    from tests.play_shared import create_token
    app,api,cid,dm,player,char=writers
    with app.app_context():
        campaign=db.session.get(Campaign,cid)
        map_=CampaignMap(campaign_id=cid,name='Concurrent loot map',width=1000,height=1000,grid_size=50,created_by=dm)
        db.session.add(map_);db.session.flush()
        session=GameSession(campaign_id=cid,name='Live loot',status='in_progress',map_id=map_.id);db.session.add(session);db.session.flush()
        state=ensure_session_state(campaign,session)
        chest=create_token(campaign,session,state,dm,name='Chest',token_type='npc');chest.is_loot_source=True
        db.session.add(chest);db.session.flush()
        loot=TokenLoot(token_id=chest.id,name='Dolch',item_type='weapon',quantity=10,weight_per_unit=.5,cost='2 GM',effects={})
        db.session.add(loot);srd_inventory.add_catalog_item(db.session.get(Character,char),DAGGER,1);db.session.commit()
        sid=session.id;chest_id=chest.id;loot_id=loot.id
    context=api(player,f'/api/play/campaigns/{cid}/sessions/{sid}/contexts',body={'mode':'player','tab':'catalog-concurrent-loot-tab'})
    assert context.status_code==201,context.json
    headers={'X-VTT-Context':context.json['token'],'X-VTT-Tab':'catalog-concurrent-loot-tab'};barrier=Barrier(2)
    def save(index):
        barrier.wait(timeout=10)
        if index==0:return api(player,f'/api/srd-creator/characters/{char}/catalog-add',body={'entity_id':DAGGER,'quantity':1,'request_id':str(uuid4())})
        return api(player,f'/api/play/campaigns/{cid}/sessions/{sid}/loot/transfer',body={'idempotency_key':str(uuid4()),'source_token_id':chest_id,
            'recipient_character_id':char,'items':[{'token_loot_id':loot_id,'quantity':2}]},headers=headers)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(save,range(2)))
    assert all(r.status_code in (200,201) for r in responses),[(r.status_code,r.json) for r in responses]
    with app.app_context():
        assert InventoryItem.query.filter_by(character_id=char).one().quantity==4
        assert db.session.get(TokenLoot,loot_id).quantity==8
