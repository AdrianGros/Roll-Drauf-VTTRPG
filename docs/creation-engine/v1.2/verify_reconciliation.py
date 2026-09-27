"""Verify retained contract authority and documentation shapes, without importing the app."""
from pathlib import Path
import copy
import hashlib
import json
import re
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT=Path(__file__).resolve().parent
STEM='creation-engine-v1.2'

def read(name): return json.loads((ROOT/name).read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(text, pattern): return [line for line in text.splitlines() if re.match(pattern,line)]
def main():
    source=read(STEM+'-source-manifest.json')
    frozen=[]
    live=[]
    for item in source['inputs']:
        assert sha(ROOT/item['path'])==item['sha256'],item['path']
        frozen.append(item['path'])
        original=Path(item['source_path'])
        historical=item['path'].split('/')[-1] in {'implementation-plan-snapshot.md','context-snapshot.md'} or item.get('status')=='withdrawn_not_authoritative'
        if not historical:
            status='verified_unchanged' if original.exists() and sha(original)==item['sha256'] else ('not_available_on_this_machine' if not original.exists() else 'changed')
            assert status!='changed',f'Active contract drifted: {original}; reconcile before rebuilding.'
            live.append({'path':str(original),'status':status})
    approved=(ROOT/'inputs/approved-spec-v1.1.4.md').read_text()
    spec=(ROOT/(STEM+'.md')).read_text()
    expected=approved[approved.index('## 1. Normative authority'):].rstrip()
    changes=read('approved-body-editorial-changes.json')
    assert len(changes)==3
    for c in changes:
        assert expected.count(c['before'])==1
        expected=expected.replace(c['before'],c['after'])
    actual=spec[spec.index('## 1. Normative authority'):spec.index('## 26. Architecture research')].rstrip()
    assert actual==expected,'Approved body differs beyond the three recorded editorial updates'
    for pattern in [r'\| T\d{2} \|',r'\| CE-[A-Z]+-\d+ \|',r'\| G0-\d{2} \|',r'\| G\d \|']:
        assert rows(actual,pattern)==rows(approved,pattern),pattern
    assert len(rows(actual,r'\| G0-\d{2} \|'))==20
    catalogue=read(STEM+'-acceptance.json')
    assert catalogue['approved_cases']==read('inputs/approved-acceptance-v1.1.4.json')['cases']
    assert [x['id'] for x in catalogue['approved_cases']]==[f'T{i:02}' for i in range(1,57)]
    assert [x['id'] for x in catalogue['proposed_cases']]==[f'T{i:02}' for i in range(57,75)]
    assert len([r for r in catalogue['requirements'] if r['authority']=='approved'])==20
    assert len([r for r in catalogue['requirements'] if r['authority']=='proposed'])==6
    for m in catalogue['withdrawn_id_mapping']:
        assert int(m['reconciled_id'][1:])==int(m['withdrawn_id'].split(':T')[1])+10
    assert [int(n) for n in re.findall(r'^## (\d+)\.',spec,re.M)]==list(range(1,31))
    for prefix,total in [('S',27),('R',31),('C',6)]:
        assert set(re.findall(r'^- ('+prefix+r'\d{2}) —',spec,re.M))=={f'{prefix}{i:02}' for i in range(1,total+1)}
    evidence=read(STEM+'-research-evidence.json')
    sources=dict(re.findall(r'^- (S\d{2}) — \[[^\]]+\]\((https?://[^)]+)\)',spec,re.M))
    assert sources=={x['id']:x['url'] for x in evidence['external_sources']}
    core=read(STEM+'-contracts.schema.json')
    addendum=read('creation-engine-v1.1-registry-a1.schema.json')
    assert (ROOT/(STEM+'-contracts.schema.json')).read_bytes()==(ROOT/'inputs/approved-core-1.1.3.schema.json').read_bytes()
    assert (ROOT/'creation-engine-v1.1-registry-a1.schema.json').read_bytes()==(ROOT/'inputs/approved-registry-a1.schema.json').read_bytes()
    assert (ROOT/'creation-engine-v1.1-registry-addendum-a1.md').read_bytes()==(ROOT/'inputs/approved-registry-a1.md').read_bytes()
    assert core['$id']=='urn:rolldrauf:creation-engine:contracts:1.1.3'
    registry=Registry().with_resources([(s['$id'],Resource.from_contents(s)) for s in (core,addendum)])
    for schema in (core,addendum): Draft202012Validator.check_schema(schema)
    v=Draft202012Validator(core,registry=registry,format_checker=FormatChecker())
    av=Draft202012Validator(addendum,registry=registry,format_checker=FormatChecker())
    def rv(name): return Draft202012Validator({**core,'$ref':'#/$defs/'+name},registry=registry,format_checker=FormatChecker())
    invoke=read('inputs/approved-core-examples-1.1.3.json')['valid_command']
    zero='sha256:'+'0'*64
    context='ctx:'+'A'*43
    common={k:copy.deepcopy(val) for k,val in invoke.items() if k not in {'operation','payload'}}
    resolve={**common,'operation':'ResolveDecision','payload':{'actionId':'action:1','decisionId':'decision:1','expectedDecisionVersion':0,'contextToken':context,'answer':{'kind':'boolean','value':True}}}
    adjust={**common,'operation':'AdjustResource','payload':{'instance':invoke['payload']['actorInstance'],'resourceId':'hp','delta':{'value':{'numerator':-1,'denominator':1},'unit':'unit:hitpoint'},'reason':'Fixture'}}
    commands=[invoke,resolve,adjust]
    for x in commands: v.validate(x)
    a1=read('inputs/approved-registry-a1-verification.json')['examples']
    assert len(a1)==24
    for x in a1.values(): av.validate(x)
    receipt={'commandId':'cmd:1','operationId':'operation:1','requestDigest':zero,'status':'committed','scopeId':'campaign:demo','stateVersion':1,'authorityEpoch':1,'checkpointId':'checkpoint:1','errorCode':None,'eventIds':['event:permitted']}
    decision={'decisionId':'decision:1','actionId':'action:1','checkpointId':'checkpoint:1','questionId':'question:1','questionVersion':1,'answerSchemaDigest':zero,'contextToken':context,'decisionVersion':0,'responderRuleId':'responders:owner','targets':[],'createdAt':'2026-09-25T09:00:00Z','deadline':'2026-09-25T09:02:00Z','windowId':'before-apply','timeoutPolicy':'suspend_mandatory','status':'open','policyId':'policy:private'}
    predicate={'node':'and','args':[{'node':'binding','bindingId':'is_equipped'},{'node':'not','arg':{'node':'manual_toggle','toggleId':'disabled'}}]}
    for name,value in [('PublicReceipt',receipt),('PendingDecision',decision),('Predicate',predicate)]: rv(name).validate(value)
    negative=[]
    def reject(name,value,mutate,validator=v):
        bad=copy.deepcopy(value); mutate(bad)
        assert list(validator.iter_errors(bad)),name
        negative.append(name)
    reject('source_occurrence_required',invoke,lambda x:x['payload'].pop('sourceInstance'))
    reject('bare_actor_id_rejected',invoke,lambda x:x['payload'].update(actorInstanceId=x['payload'].pop('actorInstance')['id']))
    reject('bare_resource_target_rejected',adjust,lambda x:x['payload'].update(instanceId=x['payload'].pop('instance')['id']))
    reject('old_public_context_digest_rejected',resolve,lambda x:x['payload'].update(contextDigest=x['payload'].pop('contextToken')))
    reject('unkeyed_hash_is_not_context_token',resolve,lambda x:x['payload'].update(contextToken=zero))
    reject('public_outcome_digest_rejected',receipt,lambda x:x.update(outcomeDigest=zero),rv('PublicReceipt'))
    reject('omitted_event_count_rejected',receipt,lambda x:x.update(omittedEventCount=2),rv('PublicReceipt'))
    reject('non_utc_deadline_rejected',decision,lambda x:x.update(deadline='2026-09-25T11:02:00+02:00'),rv('PendingDecision'))
    reject('untyped_predicate_rejected',predicate,lambda x:x.update(node='script',script='true'),rv('Predicate'))
    reject('spatial_command_not_registered',invoke,lambda x:x.update(operation='PlacePresence'))
    for x in commands:
        op=x['operation']
        reject(op+':wire_1.2_rejected',x,lambda y:y.update(contractVersion='1.2'))
        reject(op+':principal_spoof_rejected',x,lambda y:y.update(principalId='admin'))
        reject(op+':missing_epoch_rejected',x,lambda y:y.pop('authorityEpoch'))
    for op,x in a1.items():
        reject(op+':extra_payload_field',x,lambda y:y['payload'].update(unregistered=True),av)
        reject(op+':principal_spoof',x,lambda y:y.update(principalId='admin'),av)
        reject(op+':missing_epoch',x,lambda y:y.pop('authorityEpoch'),av)
        reject(op+':withdrawn_version',x,lambda y:y.update(contractVersion='1.2'),av)
    examples={'notice':'Independent synthetic shapes. Hashes/nonces are placeholders, not usable state. No runtime authorization or engine behavior is demonstrated.',
      'wire_version':'1.1.3','core_commands':commands,'registry_commands':a1,'record_shapes':{'PublicReceipt':receipt,'PendingDecision':decision,'Predicate':predicate}}
    (ROOT/(STEM+'-wire-examples.json')).write_text(json.dumps(examples,indent=2)+'\n')
    verification={'scope':'Documentation authority, contract compatibility and schema shapes only; no application imports or engine tests.',
      'active_spec':'1.1.4','active_wire':'1.1.3','active_registry':'A1','project_phase':'G1 Deploy',
      'frozen_inputs_verified':len(frozen),'live_approved_inputs':live,'approved_body_preserved_except_recorded_editorial_changes':True,
      'approved_cases_unchanged':56,'proposed_cases':18,'approved_requirements_unchanged':20,'proposed_requirements':6,
      'g0_closures_retained':20,'gate_assignments_unchanged':True,'numbered_sections':30,'research_sources':27,
      'approved_schemas_and_a1_text_byte_identical':True,'positive_command_shapes':27,'positive_record_shapes':3,
      'negative_shape_checks':negative,'spec_words':len(spec.split()),'spec_sha256':sha(ROOT/(STEM+'.md')),
      'engine_tests_rerun':False,'visual_review':'Pending final PDF build and sampled inspection.'}
    (ROOT/(STEM+'-verification.json')).write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps({k:val for k,val in verification.items() if k not in {'negative_shape_checks','live_approved_inputs'}},indent=2))
    print('Negative shape checks passed:',len(negative))

if __name__=='__main__': main()
