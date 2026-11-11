import copy
import pytest
from vtt.rules_content.creator_rules import evaluate,load_creator_data
from vtt.rules_content.species_profiles import rules_data_for_block
from vtt.rules_content import origin_profiles as profiles
from tests.test_srd_creator_api import wizard_state


def pin(kind,number,entry):
    return {'schema':profiles.PIN_SCHEMA,'revisionId':number,'revision':1,'digest':'a'*64,
            'scope':{'kind':'personal','id':1},'profile':{'schema':profiles.SCHEMA,'kind':kind,'name':entry['name'],'description':'Eigener Test','entry':entry}}


def example_pins():
    feat=pin('feat',1,{'name':'Wachsamer Pfadfinder','category':'Herkunftstalent','repeatable':False,
        'prerequisite':{'minLevel':1,'abilities':None,'requiresFeature':None,'raw':None},'abilityIncrease':None,'choices':[],
        'mechanics':[{'kind':'initiative_pb'},{'kind':'speed_meters','value':1.5},{'kind':'hp_per_level','value':2},{'kind':'skill_proficiency','skill':'athletik'}]})
    bg=pin('background',2,{'name':'Fährtenleser','abilities':['int','con','wis'],'featId':'homebrew.feat.1','feat':'Wachsamer Pfadfinder','featChoice':None,
        'skills':['arkane-kunde','geschichte'],'tool':None,'toolChoice':None,'startingEquipment':{'B':[{'kind':'coins','coin':'GM','amount':50}]}})
    return [feat,bg]


def test_pinned_background_and_feat_change_real_values_once_without_mutating_catalog():
    data=load_creator_data();state=wizard_state(data);baseline=evaluate(data,state)
    pins=example_pins();state['background']['id']='homebrew.background.2'
    block={'state':state,'rulePins':pins};resolved=rules_data_for_block(block,data)
    result=evaluate(resolved,state)
    assert result['initiative']==baseline['initiative']+result['proficiencyBonus']
    assert result['speedMeters']==baseline['speedMeters']+1.5
    assert result['hitPoints']['max']==baseline['hitPoints']['max']+10
    assert result['skills']['athletik']['bonus']==result['abilities']['str']['modifier']+result['proficiencyBonus']
    assert not any(row['id'].startswith('homebrew.') for row in data['feats'])
    assert result['provenance']['initiative']['contributions'][-1]['source']['revision']==1
    cloned=copy.deepcopy(pins);cloned[0]['profile']['entry']['mechanics'][0]={'kind':'initiative','value':9}
    assert evaluate(rules_data_for_block(block,data),state)['initiative']==result['initiative']


@pytest.mark.parametrize('class_key',[row['classKey'] for row in load_creator_data()['classes']])
def test_every_derived_numeric_field_has_reconciled_provenance(class_key):
    data=load_creator_data();state=wizard_state(data)
    state['levels']=[{'classKey':class_key}];state['advancements']=[]
    state['overrides']={'initiative':{'add':2,'reason':'Test'},'hp.max':{'set':42,'reason':'Test'},'ability.int':{'set':18,'reason':'Test'}}
    result=evaluate(data,state);p=result['provenance']
    expected={'hp.max':result['hitPoints']['max'],'armorClass':result['armorClass']['value'],'speed':result['speedMeters'],
        'initiative':result['initiative'],'proficiencyBonus':result['proficiencyBonus'],'passivePerception':result['passivePerception']}
    expected.update({'ability.'+key:row['score'] for key,row in result['abilities'].items()})
    expected.update({'modifier.'+key:row['modifier'] for key,row in result['abilities'].items()})
    expected.update({'save.'+key:row['bonus'] for key,row in result['saves'].items()})
    expected.update({'skill.'+key:row['bonus'] for key,row in result['skills'].items()})
    for key,row in result['spellcasting']['classes'].items():
        expected['spellAttack.'+key]=row['attackBonus'];expected['spellSaveDc.'+key]=row['saveDc']
    assert set(p)==set(expected)
    for key,value in expected.items():
        assert p[key]['total']==pytest.approx(value),key
        assert sum(c['value'] for c in p[key]['contributions'])==pytest.approx(value),key
        assert p[key]['stacking']


def test_unrecognized_feature_selection_cannot_grant_homebrew_bonus():
    data=load_creator_data();state=wizard_state(data);pins=example_pins()[:1]
    state['featureChoices']={'wizard':{'invented-homebrew-choice':'homebrew.feat.1'}}
    before=evaluate(data,state)
    after=evaluate(rules_data_for_block({'rulePins':pins}),state)
    assert after['initiative']==before['initiative']
    assert after['hitPoints']['max']==before['hitPoints']['max']


def test_general_feat_minimum_checked_at_acquisition_and_category():
    data=load_creator_data();state=wizard_state(data);pins=example_pins()[:1]
    entry=pins[0]['profile']['entry'];entry['category']='Allgemeines Talent';entry['prerequisite']['minLevel']=5
    state['advancements']=[{'classKey':'wizard','classLevel':4,'kind':'feat','featId':'homebrew.feat.1'}]
    after=evaluate(rules_data_for_block({'rulePins':pins}),state)
    assert any(f['code']=='homebrew-prerequisite' for f in after['findings'])
    entry['prerequisite']['minLevel']=4
    assert not any(f['code']=='homebrew-prerequisite' for f in evaluate(rules_data_for_block({'rulePins':pins}),state)['findings'])
