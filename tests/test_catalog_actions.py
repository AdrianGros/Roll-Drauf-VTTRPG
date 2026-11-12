"""Typed owner-only compendium actions, receipt transactions and real progression state."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4
import pytest
from tests.test_srd_creator_api import BASE,_client,app,client,data,finalized,other  # noqa:F401
from tests.test_srd_inventory import DAGGER,PACK
from tests.test_srd_rolls import table
from vtt.characters import srd_inventory,sheet_link
from vtt.extensions import db
from vtt.models import Character,CharacterCatalogReceipt,InventoryItem,Spell
from vtt.utils.time import utcnow

def add(client,cid,entity=DAGGER,quantity=1,request_id=None,**extra):
    return client.post(f'{BASE}/characters/{cid}/catalog-add',json={'entity_id':entity,'quantity':quantity,'request_id':request_id or str(uuid4()),**extra})

def test_confirmed_retry_is_one_action_new_deliberate_key_adds_again(client,data):
    cid=finalized(client,data)['id'];original=deepcopy(db.session.get(Character,cid).character_data);key=str(uuid4())
    first=add(client,cid,quantity=2,request_id=key);assert first.status_code==201,first.json
    replay=add(client,cid,quantity=2,request_id=key);assert replay.status_code==200 and replay.json['replayed']
    assert replay.json['receipt']==first.json['receipt']
    assert add(client,cid,quantity=3,request_id=key).status_code==409
    assert InventoryItem.query.filter_by(character_id=cid).one().quantity==2
    assert CharacterCatalogReceipt.query.filter_by(character_id=cid).count()==1
    assert add(client,cid).status_code==201
    assert InventoryItem.query.filter_by(character_id=cid).one().quantity==3
    assert db.session.get(Character,cid).character_data==original
    assert first.json['receipt']['sheet_href']==f'/character-sheet?id={cid}&section=inventory'
    assert first.headers['Cache-Control']=='private, no-store'

def test_owner_permission_before_replay_even_for_readable_dm_or_player_context(app,client,other,data):
    from tests.play_shared import enter_table
    from vtt.models import Campaign,GameSession
    t=table(app,client,other,data);cid=t['char']['id'];key=str(uuid4())
    assert t['dm'].get(f'/api/characters/{cid}/sheet').status_code==200
    assert add(t['dm'],cid,request_id=key).status_code==403
    assert add(other,cid,request_id=key).status_code==403
    enter_table(client,db.session.get(Campaign,t['campaign']),db.session.get(GameSession,t['session']))
    assert add(client,cid,request_id=key).status_code==201
    assert add(t['dm'],cid,request_id=key).status_code==403
    assert InventoryItem.query.filter_by(character_id=cid).one().quantity==1

def test_invalid_targets_types_quantities_and_fields_are_rejected(client,data):
    cid=finalized(client,data)['id']
    for quantity in [0,-1,True,1.2,'1',srd_inventory.MAX_QUANTITY+1]:assert add(client,cid,quantity=quantity).status_code==422
    assert add(client,cid,entity='spells.a-b.alarm').status_code==422
    assert add(client,cid,entity='unknown').status_code==422
    assert add(client,cid,request_id='bad').status_code==400
    assert add(client,cid,campaign_id=123).status_code==400
    assert add(client,cid,effects={'damage':999}).status_code==400
    plain=client.post('/api/characters',json={'name':'Other system'}).json
    assert add(client,plain['id']).status_code==422
    char=db.session.get(Character,cid);char.character_data={**char.character_data,'lifecycle':{'archivedAt':'2026-11-12T10:00:00Z'}};db.session.commit()
    assert add(client,cid).status_code==409
    char.deleted_at=utcnow();db.session.commit();assert add(client,cid).status_code==404
    assert InventoryItem.query.count()==0 and CharacterCatalogReceipt.query.count()==0 and Spell.query.count()==0

def test_pack_uses_existing_typed_contents_without_auto_equipping_or_charging(client,data):
    cid=finalized(client,data)['id'];char=db.session.get(Character,cid);before=deepcopy(char.character_data)
    response=add(client,cid,entity=PACK,quantity=2);assert response.status_code==201,response.json
    expected={row['itemId']:row['quantity']*2 for row in data['equipment']['packs'][PACK]['contents'] if row.get('kind')=='item'}
    items=srd_inventory.items_of(char)
    assert {srd_inventory._meta(row)['itemId']:row.quantity for row in items}==expected
    assert all(not srd_inventory._meta(row).get('equipped') for row in items)
    assert db.session.get(Character,cid).character_data==before
    assert all(row.weight_per_unit==srd_inventory.catalog()[srd_inventory._meta(row)['itemId']]['weightKg'] for row in items)

def test_mutation_failure_rolls_back_items_and_receipt(client,data,monkeypatch):
    cid=finalized(client,data)['id'];original=srd_inventory.add_catalog_item
    def fail_after_write(*args,**kwargs):
        original(*args,**kwargs);db.session.flush();raise srd_inventory.InventoryError('injected_failure','Transaction interrupted',422)
    monkeypatch.setattr(srd_inventory,'add_catalog_item',fail_after_write)
    assert add(client,cid).status_code==422
    assert InventoryItem.query.count()==0 and CharacterCatalogReceipt.query.count()==0

def test_push_failure_never_repeats_a_committed_addition(client,data,monkeypatch):
    cid=finalized(client,data)['id'];key=str(uuid4())
    def fail(*args,**kwargs):raise RuntimeError('synthetic push failure')
    monkeypatch.setattr(sheet_link,'push_character_to_tokens',fail)
    response=add(client,cid,request_id=key);assert response.status_code==201 and response.json['table_refresh']=='pending'
    retry=add(client,cid,request_id=key);assert retry.status_code==200 and retry.json['receipt']==response.json['receipt']
    assert InventoryItem.query.one().quantity==1 and CharacterCatalogReceipt.query.count()==1

def test_receipt_expiry_is_explicit_and_cleanup_is_only_own_scope(client,other,data):
    cid=finalized(client,data)['id'];key=str(uuid4());assert add(client,cid,request_id=key).status_code==201
    row=CharacterCatalogReceipt.query.one();row.expires_at=utcnow()-timedelta(seconds=1);db.session.commit()
    assert add(other,cid,request_id=key).status_code==403
    assert add(client,cid,request_id=key).status_code==409
    assert InventoryItem.query.one().quantity==1
    assert add(client,cid).status_code==201
    assert CharacterCatalogReceipt.query.count()==1 and InventoryItem.query.one().quantity==2

def test_targets_only_own_eligible_characters_with_filters_and_real_progression(client,other,data):
    own=finalized(client,data);foreign=finalized(other,data)
    hidden=db.session.get(Character,foreign['id']);hidden.name='FOREIGN_SECRET';db.session.commit()
    response=client.get(f'{BASE}/catalog-targets?entity_id={DAGGER}');assert response.status_code==200,response.json
    assert [row['id'] for row in response.json['characters']]==[own['id']]
    assert response.json['item']['id']==DAGGER and not response.json['characters'][0]['progression']['canLevelUp']
    assert 'FOREIGN_SECRET' not in response.get_data(as_text=True)
    assert client.put(f'{BASE}/characters/{own["id"]}/progression',json={'addXp':7500}).status_code==200
    status=client.get(f'{BASE}/catalog-targets?q=Mira').json['characters'][0]['progression']
    assert status['canLevelUp'] and status['targetLevel']==6
    assert client.get(f'{BASE}/catalog-targets?campaign_id=999999').json['characters']==[]
    assert client.get(f'{BASE}/catalog-targets?after=-1').status_code==400
    assert client.get(f'{BASE}/catalog-targets?entity_id=spells.a-b.alarm').json['item'] is None
    assert add(client,own['id'],entity='spells.a-b.alarm').status_code==422
