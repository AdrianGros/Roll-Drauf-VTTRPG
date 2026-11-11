import copy
import pytest
from tests.test_srd_creator_api import app,client,other,data,make_draft,wizard_state  # noqa: F401
from vtt.extensions import db
from vtt.creation_engine.models import CeEagleDocument
from vtt.models import CeRuleRevision,Character
from vtt.characters import sheet_link,srd_export,origin_catalog
from vtt.rules_content import origin_profiles
from vtt.creation_engine.origins import inspect,SUPPLEMENT_SCHEMA
from vtt.rules_content.creator_rules import evaluate

BASE='/api/ce/authoring/origins'

@pytest.fixture(autouse=True)
def enable_origins(app):
    app.config.update(CE_AUTHORING=True,CE_PLAYABLE_ORIGINS=True)


def supplement(kind='feat'):
    if kind=='feat':return {'schema':SUPPLEMENT_SCHEMA,'category':'origin','minLevel':1,'prerequisite':None,'grants':[{'kind':'initiative_pb'}]}
    return {'schema':SUPPLEMENT_SCHEMA,'abilities':['int','con','wis'],'skills':['arkane-kunde','geschichte'],'toolId':None,'featId':None}


def source(kind='feat'):
    return {'name':'Wachsamer Pfadfinder' if kind=='feat' else 'Pfadwanderer','type':kind,'system':{'source':{'rules':'2024'},'description':{'value':'Eigene Testbeschreibung.'}}}


def document(client,kind='feat'):
    row=CeEagleDocument(scope_kind='personal',scope_id=client.user_id,document_name='Item',document_id='Test'+kind,
        doc_type=kind,name=source(kind)['name'],source=source(kind),created_by=client.user_id,updated_by=client.user_id)
    db.session.add(row);db.session.commit();return row


def publish(client,row,extra=None,scope='personal'):
    body={'world':'personal','uuid':row.uuid,'supplement':extra or supplement(row.doc_type)}
    check=client.post(BASE+'/check',json=body)
    assert check.status_code==200,check.json
    assert check.json['report']['playable'],check.json
    result=client.post(BASE+'/publish',json={**body,'scope':scope,'expectedDigest':check.json['source']['digest'],'expectedProfileDigest':check.json['profileDigest']})
    assert result.status_code in (200,201),result.json
    return result.json,body,check.json


def test_publish_background_creator_pin_rebuild_import_and_source_changes(client,other,data):
    feat=document(client);published,_,_=publish(client,feat)
    fid='homebrew.feat.'+str(published['revision']['id'])
    bg=document(client,'background');extra=supplement('background');extra['featId']=fid
    result,body,checked=publish(client,bg,extra)
    bid='homebrew.background.'+str(result['revision']['id'])
    assert len(client.get('/api/srd-creator/origin-catalog').json['backgrounds'])==1
    assert other.get('/api/srd-creator/origin-catalog').json['backgrounds']==[]
    state=wizard_state(data);state['background']['id']=bid
    draft=make_draft(client,state)['draft']
    finalized=client.post(f"/api/srd-creator/drafts/{draft['id']}/finalize",json={'version':draft['version']})
    assert finalized.status_code==201,finalized.json
    cid=finalized.json['character']['id'];char=db.session.get(Character,cid)
    before=sheet_link.srd_evaluation(char);assert before['initiative']==4
    assert len(origin_profiles.pinned(char.character_data['srd']))==2
    exported=srd_export.export_character(char) if hasattr(srd_export,'export_character') else srd_export.export_document(char)
    # A fresh Eagle edit / publication never changes an existing character pin.
    feat.source={**feat.source,'name':'Pfadfinder neu'};feat.name='Pfadfinder neu';feat.revision+=1;db.session.commit()
    publish(client,feat, {**supplement(),'grants':[{'kind':'initiative','value':9}]})
    assert sheet_link.srd_evaluation(char)['initiative']==before['initiative']
    rebuilt=client.post(f'/api/srd-creator/characters/{cid}/to-draft')
    assert rebuilt.status_code==201,rebuilt.json
    imported,_=srd_export.import_character(exported,user_id=client.user_id)
    assert sheet_link.srd_evaluation(imported)['initiative']==before['initiative']
    with pytest.raises(Exception):srd_export.import_character(exported,user_id=other.user_id)
    assert other.post('/api/srd-creator/evaluate',json={'state':state}).status_code==422
    bad=client.post(BASE+'/publish',json={**body,'scope':'global','expectedDigest':checked['source']['digest'],'expectedProfileDigest':checked['profileDigest']})
    assert bad.status_code==422 and bad.json['error']=='linked-scope'


@pytest.mark.parametrize('mutation',[
    lambda s,x:s.update(effects=[{'changes':[{'key':'system.attributes.ac','value':'99'}]}]),
    lambda s,x:s['system'].update(activities={'attack':{}}),
    lambda s,x:x['grants'].append({'kind':'script','value':'evil()'}),
    lambda s,x:x['grants'].append({'kind':'ac','value':99}),
    lambda s,x:x['grants'].append({'kind':'initiative_pb'}),
    lambda s,x:x['grants'].append({'kind':{}}),
    lambda s,x:x.update(prerequisite={'ability':{},'min':13}),
])
def test_unknown_effects_and_invalid_grants_block_publication(data,mutation):
    s=source();extra=supplement();mutation(s,extra)
    checked=inspect(s,extra,data=data)
    assert checked['playable'] is False and checked['profile'] is None


def test_publication_cas_and_immutable_revisions(client):
    row=document(client);result,body,checked=publish(client,row)
    assert publish(client,row)[0]['created'] is False
    changed=copy.deepcopy(body);changed['supplement']['grants']=[{'kind':'initiative','value':3}]
    response=client.post(BASE+'/publish',json={**changed,'expectedDigest':checked['source']['digest'],'expectedProfileDigest':checked['profileDigest']})
    assert response.status_code==409
    row.source={**row.source,'name':'Neue Quelle'};row.name='Neue Quelle';row.revision+=1;db.session.commit()
    response=client.post(BASE+'/publish',json={**body,'expectedDigest':checked['source']['digest'],'expectedProfileDigest':checked['profileDigest']})
    assert response.status_code==409
    assert CeRuleRevision.query.count()==1


def test_reader_checkpoint_disables_publication_but_keeps_pinned_evaluation(app,client,data):
    from tests.test_origin_profiles import example_pins
    app.config['CE_PLAYABLE_ORIGINS']=False
    assert client.post(BASE+'/check',json={}).status_code==404
    assert client.get('/api/srd-creator/origin-catalog').json['feats']==[]
    state=wizard_state(data);state['background']['id']='homebrew.background.2'
    from vtt.rules_content.species_profiles import rules_data_for_block
    assert evaluate(rules_data_for_block({'state':state,'rulePins':example_pins()}),state)['initiative']==4
