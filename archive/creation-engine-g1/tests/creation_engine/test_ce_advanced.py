"""Atomic full-document edits retain A1 history, revisions and ownership."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from sqlalchemy.orm import Session

from vtt.creation_engine.canonical import canonical_bytes
from vtt.creation_engine.compiler import homebrew as h
from vtt.creation_engine.compiler import flame, manual, race
from vtt.creation_engine.content import new_id
from vtt.creation_engine.errors import ContractViolation
from vtt.creation_engine.store.advanced import AdvancedService, DocumentInvalid
from vtt.creation_engine.store.authoring_models import CeDraftCommand
from homebrew_examples import examples
from test_ce_content_store import postgres_engine
from test_ce_migration import migration_engine
from test_ce_authoring import authoring_engine, author, submit, wire
from test_ce_authoring_transports import transport

pytestmark = pytest.mark.postgres


def created(a, kind=h.CLASS):
    _, result = submit(a, 'CreateDraft', {'schemaType': kind.to_wire(), 'authoringLocale': 'en'})
    return {**a, 'draft': result['draftId'], 'advanced': AdvancedService(a['service'])}


def payload(a, document, **extra):
    return {'contractVersion': 'advanced-document:1', 'expectedDraftVersion': a['advanced'].read(a['principal'],a['workspace'],a['draft'])['draftVersion'],
            'idempotencyKey':new_id('document'), 'promptLocale':'en','content':document, **extra}


def save(a, body):
    return a['advanced'].save(a['principal'],a['workspace'],a['draft'],body)


@pytest.mark.parametrize('kind,document', examples())
def test_whole_document_is_one_version_and_commits_through_a1(author, kind, document):
    a=created(author,kind)
    result=save(a,payload(a,document))
    assert result['draftVersion']==2 and result['qualityGates']['runtime_ready']==[]
    for mode in ['guided','structured','advanced']:
        assert a['service'].read(a['principal'],a['workspace'],a['draft'],mode=mode)['content']==document
    _, committed=submit(a,'CommitDraftRevision',{'declaredQuality':'runtime_ready','definition':{'kind':'new'}})
    assert committed['revision']['kind']=='revision' and committed['draftVersion']==3
    assert len(a['service'].history(a['principal'],a['workspace'],a['draft']))==2


def test_validate_is_read_only_and_bad_fields_have_paths(author):
    a=created(author); body=payload(a,examples()[0][1]);body.pop('idempotencyKey')
    assert a['advanced'].validate(a['principal'],a['workspace'],a['draft'],body)['valid']
    assert a['advanced'].read(a['principal'],a['workspace'],a['draft'])['draftVersion']==1
    invalid=deepcopy(body);invalid['content']['class']['hitDie']=True
    with pytest.raises(DocumentInvalid) as caught:
        a['advanced'].validate(a['principal'],a['workspace'],a['draft'],invalid)
    assert caught.value.issues[0]['path']=='/class/hitDie'
    invalid=deepcopy(body);invalid['content']['injected']=42
    with pytest.raises(DocumentInvalid):
        a['advanced'].validate(a['principal'],a['workspace'],a['draft'],invalid)
    assert not a['service'].history(a['principal'],a['workspace'],a['draft'])


def test_dependency_change_and_explicit_removal_preserve_old_snapshot(author):
    a=created(author); doc=examples()[0][1]
    save(a,payload(a,doc))
    updated=deepcopy(doc);updated['class']['edition']='dnd5e_2014'
    save(a,payload(a,updated))
    assert a['advanced'].read(a['principal'],a['workspace'],a['draft'])['content']==updated
    save(a,payload(a,{'name':'Incomplete on purpose'}))
    state=a['advanced'].read(a['principal'],a['workspace'],a['draft'])
    assert state['content']=={'name':'Incomplete on purpose'} and state['qualityGates']['runtime_ready']
    submit(a,'RevertDraft',{'toDraftVersion':2})
    assert a['advanced'].read(a['principal'],a['workspace'],a['draft'])['content']==doc


def test_save_is_atomic_retryable_and_checks_current_owner(author):
    a=created(author);body=payload(a,examples()[0][1])
    def crash(point):
        if point=='before_commit':raise RuntimeError('rollback')
    a['service'].fault=crash
    with pytest.raises(RuntimeError):save(a,body)
    assert a['advanced'].read(a['principal'],a['workspace'],a['draft'])['draftVersion']==1
    with Session(a['service'].store.engine) as session:
        assert session.get(CeDraftCommand,(a['draft'],a['principal'],body['idempotencyKey'])) is None
    def lost(point):
        if point=='after_commit':raise RuntimeError('lost')
    a['service'].fault=lost
    with pytest.raises(RuntimeError):save(a,body)
    a['service'].fault=lambda p:None
    assert save(a,body)==save(a,body)
    assert a['advanced'].read(a['principal'],a['workspace'],a['draft'])['draftVersion']==2
    with pytest.raises(ContractViolation,match='IDEMPOTENCY_KEY_REUSE'):
        save(a,{**body,'content':{'name':'Other'}})
    with pytest.raises(ContractViolation,match='NOT_FOUND'):
        a['advanced'].save(1,a['workspace'],a['draft'],body)


def test_competing_document_saves_and_single_answer_share_version_guard(author):
    a=created(author);commands=[payload(a,{'name':name}) for name in ['First','Second']]
    question = h.interview(h.CLASS).by_id['name']
    stale_answer = wire(a, 'RecordDraftDecision', {'question': {'questionId': 'name', 'questionVersion': question.version},
        'answer': question.answer('Single-field edit'), 'promptLocale': 'en'})
    def run(body):
        try:return save(a,body)['draftVersion']
        except ContractViolation as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(map(str,pool.map(run,commands)))==['2','DRAFT_VERSION_CONFLICT']
    with pytest.raises(ContractViolation, match='DRAFT_VERSION_CONFLICT'):
        a['gateway'].submit(a['principal'], canonical_bytes(stale_answer))


def test_http_document_validation_is_private_csrf_protected_and_safe(transport):
    app,_,client,_,csrf,author=transport;a=created(author)
    url=f"/api/ce/authoring/workspaces/{a['workspace']}/drafts/{a['draft']}/document"
    body=payload(a,examples()[0][1]);headers={'X-CSRF-TOKEN':csrf}
    assert client.get('/api/ce/authoring/advanced/workspace').status_code==200
    assert app.test_client().get(url).status_code==401
    assert client.post(url,data=canonical_bytes(body)).status_code==401
    assert client.get(url,headers={'X-CE-View-As':'view:no'}).status_code==403
    bad=deepcopy(body);bad['content']['class']['hitDie']='six'
    response=client.post(url,data=canonical_bytes(bad),headers=headers)
    assert response.status_code==422 and response.json['error']['issues'][0]['path']=='/class/hitDie'
    response=client.post(url,data=canonical_bytes(body),headers=headers)
    assert response.status_code==200 and response.json['draftVersion']==2
    assert response.headers['Cache-Control']=='private, no-store'
    # Raw duplicate properties must not be accepted as a last-value-wins edit.
    assert client.post(url,data=b'{"content":{},"content":{}}',headers=headers).status_code==400
    app.config['CE_AUTHORING']=False
    assert client.get(url).status_code==404


@pytest.mark.parametrize('kind', [flame.ITEM_TYPE, race.RACE_TYPE, *manual.TYPES])
def test_existing_profiles_round_trip_through_document_adapter(author, kind):
    from test_ce_compiler import filled
    from test_ce_race_compiler import fill as fill_race
    from test_ce_manual_compiler import fill as fill_manual
    if kind == flame.ITEM_TYPE:
        guide, state = flame.interview(), filled()
    elif kind == race.RACE_TYPE:
        guide, state = fill_race()
    else:
        guide, state = fill_manual(kind)
    document = guide.values(state)
    a = created(author, kind)
    result = save(a, payload(a, document))
    quality = 'lore_only' if kind == manual.LORE else 'sheet_ready'
    assert result['draftVersion'] == 2 and result['qualityGates'][quality] == []
    assert a['advanced'].read(a['principal'], a['workspace'], a['draft'])['content'] == document
