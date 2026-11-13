import json,copy
from vtt.rules_content.creator_rules import evaluate,load_creator_data
from vtt.characters.srd_progression import needs,build_state
from tests.test_srd_progression import level_one_state,payload_from_needs
from vtt.rules_content.creator_drafts import finalize_blockers
D=load_creator_data();s=level_one_state(D,'warlock')
for level in range(2,6):
 ev=evaluate(D,s);need=needs(D,s,ev,'warlock');payload=payload_from_needs(D,need,ev,s);s=build_state(D,s,payload)
prefix='classes.warlock.invocation-';base=['armor-of-shadows','eldritch-mind','devils-sight','fiendish-vigor','ascendant-step'];out=[]
for name,ids in [('valid_control',base),('eldritch_smite_without_pact',base[:-1]+['eldritch-smite']),('eldritch_smite_with_pact',base[:3]+['pact-of-the-blade','eldritch-smite'])]:
 state=copy.deepcopy(s);state['featureChoices']['warlock']['eldritch-invocations']=[prefix+i for i in ids];ev=evaluate(D,state)
 blockers=finalize_blockers(ev,state)
 out.append({'case':name,'class_level':ev['level'],'invocations':ids,'valid':ev['valid'],'complete':ev['complete'],'blockers':blockers,'feature_findings':[f for f in ev['findings'] if f.get('path','').startswith('featureChoices')],'all_finding_codes':[f['code'] for f in ev['findings']]})
print(json.dumps({'scope':'Pure evaluator and progression-state builders only; no DB, browser or production writes','cases':out},ensure_ascii=False,indent=2))
