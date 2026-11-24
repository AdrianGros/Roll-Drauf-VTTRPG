"""Source identity, cache and immutable-mechanics contracts for the creator display overlay."""
import copy
import json
from pathlib import Path
import shutil

import pytest

from tools.build_creator_locale import ROOT, compile_display
from tests.test_srd_creator_browser import site
from vtt.rules_content import creator_locale
from vtt.rules_content.creator_rules import load_creator_data


def test_reviewed_names_terms_and_source_differences_keep_canonical_data():
    before=copy.deepcopy(load_creator_data())
    value=compile_display()
    assert len(value['names'])==663 and len(value['terms'])==52
    assert len({x['enEntityId'] for x in value['names'].values()})==663
    for key,expected in {
        'spells.a-b.ablenkung':'Mislead',
        'spells.h-l.hypnotisches-muster':'Hypnotic Pattern',
        'classes.warlock.invocation-agonizing-blast':'Agonizing Blast',
        'classes.warlock.invocation-improved-pact-weapon':'Devouring Blade',
        'classes.barbarian.level7-feral-instinct':'Instinctive Pounce',
        'classes.barbarian.level7-wild-instincts':'Feral Instinct',
    }.items():assert value['names'][key]['name']==expected
    assert value['names']['spells.h-l.hypnotisches-muster']['sourceDifferences']['components']['de'].startswith('V, G, M')
    assert value['terms']['abilities:wis']['name']=='Wisdom'
    assert value['terms']['skills:mit-tieren-umgehen']['name']=='Animal Handling'
    assert value['terms']['languages:gebaerden-gemeinsprache']['name']=='Common Sign Language'
    assert value['terms']['alignments:neutral']['name']=='Neutral'
    for entry in value['names'].values():
        if 'featureIds' in entry:assert entry['featureIds'] and all(fid in {n['enEntityId'] for n in value['names'].values()} for fid in entry['featureIds'])
    assert before==load_creator_data()
    assert not {'category','column','kind','classKey'} & set().union(*(row.keys() for row in value['names'].values()))
    generated=json.loads((ROOT/'vtt/rules_content/srd-5.2.1-en/generated/creator-display.json').read_text())
    assert generated==value


def _pinned_tree(tmp_path):
    pins=json.loads((ROOT/'tools/creator_locale/pins.json').read_text())
    for name in [*pins['sourceHashes'],'tools/creator_locale/pins.json','tools/creator_locale/terms.json']:
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    return pins


def test_builder_refuses_source_drift_and_duplicate_identity(tmp_path):
    pins=_pinned_tree(tmp_path)
    pinfile=tmp_path/'tools/creator_locale/pins.json'
    keys=list(pins['entities'])
    pins['entities'][keys[1]]['enEntityId']=pins['entities'][keys[0]]['enEntityId']
    pinfile.write_text(json.dumps(pins))
    with pytest.raises(ValueError,match='Non-bijective|mismatched'):compile_display(tmp_path)
    shutil.copy2(ROOT/'tools/creator_locale/pins.json',pinfile)
    original=json.loads(pinfile.read_text());broken=copy.deepcopy(original)
    del broken['sourceHashes']['vtt/rules_content/srd-5.2.1-en/generated/compendium.json']
    pinfile.write_text(json.dumps(broken))
    with pytest.raises(ValueError,match='both compendia must be pinned'):compile_display(tmp_path)
    pinfile.write_text(json.dumps(original))
    termfile=tmp_path/'tools/creator_locale/terms.json';original_terms=json.loads(termfile.read_text())
    bad_terms=copy.deepcopy(original_terms);bad_terms['terms']['feats:feats.descriptions.skilled']=bad_terms['terms']['abilities:str']
    termfile.write_text(json.dumps(bad_terms))
    with pytest.raises(ValueError,match='Unsupported creator term kind'):compile_display(tmp_path)
    termfile.write_text(json.dumps(original_terms))
    path=tmp_path/'vtt/rules_content/srd-5.2.1-en/generated/compendium.json'
    path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError,match='Reviewed source changed'):compile_display(tmp_path)


def test_display_api_auth_cache_locale_hash_and_unavailable(site,monkeypatch,tmp_path):
    app,origin,info=site
    client=app.test_client();base='/api/srd-creator'
    headers={}
    assert client.get(base+'/creator-display?locale=en').status_code==401
    client.set_cookie('access_token_cookie',info['token'])
    assert client.get(base+'/creator-display?locale=auto',headers=headers).status_code==400
    raw=client.get(base+'/creator-data',headers=headers)
    assert raw.get_json()==load_creator_data()
    response=client.get(base+'/creator-display?locale=en',headers=headers)
    assert response.status_code==200
    assert response.get_json()['canonicalHash']==raw.headers['X-Creator-Data-SHA256']
    assert response.get_json()['locale']=='en'
    assert 'private' in response.headers['Cache-Control'] and 'no-cache' in response.headers['Cache-Control'] and response.headers['ETag']
    assert client.get(base+'/creator-display?locale=en',headers={**headers,'If-None-Match':response.headers['ETag']}).status_code==304
    assert client.get(base+'/creator-display',headers=headers).get_json()['locale']=='de'
    copyfile=tmp_path/'canonical.json';copyfile.write_bytes(creator_locale.CANONICAL_FILE.read_bytes()+b' ')
    try:
        with monkeypatch.context() as m:
            m.setattr(creator_locale,'CANONICAL_FILE',copyfile)
            creator_locale.canonical_data_hash.cache_clear();creator_locale.load_creator_display.cache_clear()
            stale=client.get(base+'/creator-display?locale=en',headers=headers)
            assert stale.status_code==503 and 'no-store' in stale.headers['Cache-Control']
            assert stale.get_json()=={'error':'creator_display_unavailable'}
    finally:
        creator_locale.canonical_data_hash.cache_clear();creator_locale.load_creator_display.cache_clear()
