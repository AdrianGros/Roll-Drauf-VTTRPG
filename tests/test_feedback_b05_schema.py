"""New optional path mode and visible nameless labels retain strict document contracts."""
import copy
import pytest
from vtt.mapmaker_document import normalize_document,InvalidDocument


def document(kind,item):
    return {'format':'rd-mapmaker','version':1,'size':{'w':512,'h':512},'meta':{'title':'Feedback'},'sea':{},'layers':[{'id':'l1','name':'Test','kind':kind,'visible':True,'opacity':1,'items':[item]}]}


def test_old_paths_stay_straight_and_only_boolean_curve_mode_is_valid():
    item={'id':'p1','x':20,'y':20,'material':'road','width':12,'points':[{'x':0,'y':0},{'x':100,'y':100}]}
    clean,_=normalize_document(document('paths',item));assert clean['layers'][0]['items'][0]['curve'] is False
    item['curve']=True;clean,_=normalize_document(document('paths',item));assert clean['layers'][0]['items'][0]['curve'] is True
    for bad in ['false',0,1,None,{},[]]:
        item['curve']=bad
        with pytest.raises(InvalidDocument):normalize_document(document('paths',item))


def test_nameless_labels_require_a_visible_pin_or_known_symbol():
    item={'id':'p1','x':20,'y':20,'text':'','style':'town','size':20,'pin':True}
    clean,_=normalize_document(document('labels',item));assert clean['layers'][0]['items'][0]['text']==''
    item['pin']=False
    with pytest.raises(InvalidDocument):normalize_document(document('labels',item))
    item.update(place={'kind':'landmark','lore':''},symbol={'asset':'builtin:mountain','size':32})
    # Catalog identifier may not be invented, even for a nameless symbol.
    item['symbol']['asset']='builtin:does-not-exist'
    with pytest.raises(InvalidDocument):normalize_document(document('labels',item))

from tests.test_mapmaker_library import library,create,document as saved_document,API  # noqa:F401,E402


def test_library_keeps_curve_and_nameless_symbol_without_exposing_private_map(library):
    payload=saved_document()
    payload['layers'][2]['items'][0]['curve']=True
    payload['layers'][3]['items'][0]['text']=''
    project=create(library,payload);owner,headers=library[2][0]
    stored=owner.get(API+'/'+project['id'],headers=headers).get_json()['document']
    assert stored['layers'][2]['items'][0]['curve'] is True
    assert stored['layers'][3]['items'][0]['text']==''
    assert stored['layers'][3]['items'][0]['symbol']['asset']=='builtin:castle'
    outsider,other_headers=library[2][1]
    assert outsider.get(API+'/'+project['id'],headers=other_headers).status_code==404
