"""Build the reconciled reading edition from frozen approved inputs and scoped additions."""
from pathlib import Path
import copy
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'inputs'
STEM = 'creation-engine-v1.2'

def section(text, number):
    return re.search(r'^## '+str(number)+r'\..*?(?=^## |\Z)', text, re.M|re.S).group().rstrip()

def remap(text):
    return re.sub(r'\bT(\d{2})\b', lambda m: f'T{int(m[1])+10:02}' if 47 <= int(m[1]) <= 64 else m[0], text)

def table(text, prefix):
    result=[]
    for line in text.splitlines():
        if re.match(r'\| '+prefix, line):
            result.append([x.strip() for x in line.strip('|').split('|')])
    return result

def ids(text):
    out=set(re.findall(r'\bT\d{2}\b',text))
    for first,last in re.findall(r'T(\d{2})[–-]T(\d{2})',text):
        out.update(f'T{i:02}' for i in range(int(first),int(last)+1))
    return sorted(out)

def main():
    manifest=json.loads((ROOT/(STEM+'-source-manifest.json')).read_text())
    for f in manifest['inputs']:
        assert hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()==f['sha256'], f['path']
    approved=(INPUT/'approved-spec-v1.1.4.md').read_text()
    withdrawn=(INPUT/'withdrawn-v1.2.md').read_text()
    # Preserve the entire approved 1–25 body. Status-bearing editorial sentences are listed explicitly.
    body=approved[approved.index('## 1. Normative authority'):].rstrip()
    replacements=[
      ("This document chooses proposed defaults so the next audit can challenge concrete decisions. Those choices are design proposals within the user's request, not evidence that the team has approved implementation, production risk, or a public launch. Persistence vendor, deployment topology, and UI toolkit are intentionally outside this contract. Their selection MUST satisfy the observable semantics here. No choice of database is allowed to weaken atomicity or authorization.",
       "Current authority: G0 passed for v1.1.4 and G1 implementation was authorized on 24 September 2026. The approved G1 plan supplies the concrete dependency, persistence and integration choices for that slice. Approval does not imply a production cutover or public launch. Choices for other slices remain subject to their own handoff. Their selection MUST satisfy the observable semantics here. No choice of database is allowed to weaken atomicity or authorization."),
      ("The current VTT observations were gathered from a local working tree at HEAD `94ff1b9e9c07e048151469195f262fda1d80536b` with existing uncommitted changes. They are integration constraints to verify again before implementation, not a production inventory.",
       "The historical VTT observations below were gathered at HEAD `94ff1b9e9c07e048151469195f262fda1d80536b`. The approved G1 plan subsequently refreshed the integration inventory, and §30 records the implementation snapshot at reconciliation. These are dated integration observations, not a current production inventory."),
      ("The second adversarial audit (G0) ran on 24 September 2026; v1.1.1 to v1.1.4 adopt all of its closures, and G0 passed on 24 September 2026. Implementation and conformance proof remain subsequent work.",
       "The second adversarial audit (G0) ran on 24 September 2026; v1.1.1 to v1.1.4 adopt all of its closures, and G0 passed that day. G1 implementation is underway; its recorded evidence and remaining work are summarized in §30. This reading edition does not repeat the G0 gate.")]
    for old,new in replacements:
        assert body.count(old)==1, old[:50]
        body=body.replace(old,new)
    (ROOT/'approved-body-editorial-changes.json').write_text(json.dumps([{'before':a,'after':b} for a,b in replacements],indent=2)+'\n')
    header='''# Roll Drauf Creation Engine

## Research and Technical Specification v1.2 — reconciled reading edition

**Date:** 25 September 2026. **Project phase:** G1 Deploy remains authorized. **Active implementation contract:** specification v1.1.4, core wire 1.1.3 and approved registry addendum A1. **Document status:** consolidated approved body plus explicitly scoped research changes; not a replacement implementation authorization or a wire-version upgrade.

This edition corrects the earlier v1.2 rewrite, which was based on v1.1 and omitted approved audit corrections. The earlier rewrite and its seven-command 1.2 schema are withdrawn from authority. Existing implementation continues under its approved contract. G0 remains passed, WP1–WP4 evidence remains valid for its recorded scope, and WP5 can continue without restarting Discover or Apply.

Sections 1–25 preserve the approved v1.1.4 body, apart from three listed editorial updates to historical status/provenance. The existing normative clauses, G0 closures, T01–T56, 20 requirement mappings and gate assignments are retained. Section 26 contains research; §27 relates clean coding to the adopted architecture; §28 records bounded future changes; §29 adds proposed T57–T74 and six proposed requirements; §30 identifies the active contract and next implementation step. Proposal language in §§27–29 does not amend the approved body by proximity.

The accepted single-presence product direction is retained for spatial mechanics. Detailed geometry, commands, lock fields and retry defaults do not silently become G1 requirements. The approved E4 rule still permits ordinary token movement on maps without declared spatial mechanics.

**Companions:** `creation-engine-v1.2-contracts.schema.json` is an exact copy of approved core wire **1.1.3**, despite the reading-edition filename. `creation-engine-v1.1-registry-a1.schema.json` and its approved addendum retain 24 additional commands. Together they define 27 approved command shapes. The acceptance catalogue separates the unchanged 56 approved cases from 18 research proposals. Historical catalogue status is not the live test dashboard; recorded implementation results are in the G1 program and §30.

The creator decides what content means. The platform translates supported intent into explicit definitions; validates, versions, executes, explains, and renders those definitions; and preserves the distinction between creative decisions and technical interpretation.

'''
    research=section(withdrawn,3).split('\n\n',1)[1]
    research=remap(research).replace('§25','§26.1').replace("§26's testable dependency and side-effect contract", "§27's dependency and side-effect guidance")
    research=research.replace('Explicit cost identity and one checkpoint owner; §§7–9, T57', 'Cost identity proposal in §28.2, retaining §§7–9 guarantees; T57')
    research=research.replace('One occurrence-owned presence; §§4, 16, T59', 'Accepted spatial direction and proposal in §28.1; T59')
    research=research.replace('Explicit transaction ownership and persistence tests; §§5, 26, T58, T61', 'Approved checkpoint ownership; proposed extra evidence in §§27, 28.2; T58, T61')
    research=research.replace('Meter compound work and separate retry budgets; §18, T64, T74', 'Approved §18 bounds; separate retry refinement in §28.4; T64, T74')
    research=research.replace('No new runtime/test dependency is selected by this specification.', 'Approved G1 dependency choices remain recorded in its plan.')
    research=research.replace('Hypothesis and Import Linter are optional implementation candidates [S25–S26]; no new runtime/test dependency is selected by this specification.', 'Hypothesis is already approved for G1; Import Linter is an optional enforcement tool [S25–S26].')
    sources='\n'.join(x for x in section(withdrawn,25).splitlines() if re.match(r'- S\d{2} —',x))
    clean=section(withdrawn,26).split('\n\n',1)[1]
    clean=re.sub(r'### 26\.(\d)',r'### 27.\1',clean)
    clean=clean.replace('The initial design proposal is an isolated Creation Engine package inside the existing application, with explicit persistence, transport, and legacy adapters.', 'The approved G1 plan already places the Creation Engine inside the existing application, with explicit persistence, transport, and legacy adapters.')
    clean=clean.replace('This preserves the current integration boundary while making the core independently testable. It is not a selected deployment topology:', 'This preserves the integration boundary and supports independent core testing;')
    clean=clean.replace('Each changed invariant has targeted executable evidence when implementation begins.', 'Each affected invariant needs targeted evidence as the remaining work packages are implemented.')
    clean=clean.replace('within §18', 'within the approved §18 contract (the separate retry proposal is §28.4)')
    clean=clean.replace('Use distinct domain types for Definition/Revision/Instance/Scene/Representation references, Quantity/unit, draft version, scope version, presence version, and worker fence.', 'Use distinct domain types for the approved Definition/Revision/Instance references, Quantity/unit, draft version, scope version, and worker fence. Future spatial work adds its own Scene/Representation references and presence version without changing existing wire types silently.')
    clean=clean.replace('Hypothesis and Import Linter are candidate tools;', 'Hypothesis is approved and already used; Import Linter is optional;')
    spatial=section(withdrawn,16).split('### 16.1 ',1)[1]
    spatial='#### 28.1.1 '+spatial
    spatial=re.sub(r'### 16\.(\d)',r'#### 28.1.\1',spatial)
    spatial=spatial.replace('The selected wire schema includes the following commands in addition to InvokeActivity, ResolveDecision, and AdjustResource.', 'The following are candidate command payloads for future spatial registration. They are absent from the current approved wire schemas; the three core commands and all A1 operations remain unchanged.')
    spatial=spatial.replace('The baseline geometry profile', 'The proposed geometry profile').replace('in the baseline', 'under this proposal').replace('The baseline rejects', 'The proposed model rejects')
    spatial=spatial.replace('Each uses the shared command envelope,', 'The proposal would use the mechanical envelope,')
    spatial=spatial.replace('Presence and scene versions used by pending decisions are recorded;', 'Presence and scene versions used by pending decisions would be recorded internally and bound to the approved opaque contextToken;')
    s7=section(withdrawn,7)
    provenance=s7[s7.index('Internal provenance is a typed'):]
    provenance=provenance.replace('as specified in §18', 'under the proposal in §28.4')
    s18=section(withdrawn,18)
    fuel=s18[s18.index('Each AST literal'):s18.index('Imports reject')].strip()
    proposal_cases=table(section(withdrawn,21),r'T(?:4[7-9]|[56]\d) \|')
    assert len(proposal_cases)==18
    new_rows=[]
    aliases=[]
    for row in proposal_cases:
        old=row[0]; row=[remap(c) for c in row]
        # Preserve approved privacy boundary in new spatial recovery cases too.
        row[2]=row[2].replace('stale digest','stale context token')
        aliases.append({'withdrawn_id':'withdrawn-v1.2:'+old,'reconciled_id':row[0],
                        'research_origin':f'RA{int(old[1:])-46:02}' if int(old[1:])<=56 else None})
        new_rows.append('| '+' | '.join(row)+' |')
    additions=(ROOT/'reconciliation-additions.md').read_text()
    for key,val in {'RESEARCH':research,'SOURCES':sources,'CLEAN':clean,'SPATIAL':spatial,'PROVENANCE':provenance,'FUEL':fuel,'NEW_CASES':'\n'.join(new_rows)}.items():
        additions=additions.replace('{{'+key+'}}',val)
    assert '{{' not in additions
    spec=header+body+'\n\n'+additions
    (ROOT/(STEM+'.md')).write_text(spec)
    baseline=json.loads((INPUT/'approved-acceptance-v1.1.4.json').read_text())
    approved_cases=copy.deepcopy(baseline['cases'])
    proposed=[]
    for row in table(additions,r'T\d{2} \|'):
        proposed.append({'id':row[0],'scenario':row[1],'required_result':row[2],'status':'proposed_not_executed_by_reconciliation'})
    requirements=[]
    for fragment,status in [(body,'approved'),(additions,'proposed')]:
        for row in table(fragment,r'CE-[A-Z]+-\d+ \|'):
            requirements.append({'id':row[0],'contract':row[1],'acceptance_ids':ids(row[2]),'authority':status})
    assert len(requirements)==26 and len(proposed)==18
    assert len({r['id'] for r in requirements})==26
    for case in proposed:
        assert any(case['id'] in r['acceptance_ids'] for r in requirements if r['authority']=='proposed'),case['id']
    result={'documentation_revision':'1.2-reconciled','active_spec_version':'1.1.4','active_wire_version':'1.1.3',
      'execution_claim':'Approved case status is retained verbatim as historical catalogue metadata, not a current dashboard. WP1–WP4 test evidence is recorded separately in the program; no engine tests ran for this reconciliation.',
      'approved_cases':approved_cases,'proposed_cases':proposed,'requirements':requirements,'withdrawn_id_mapping':aliases,
      'active_gate_assignments':'Unchanged approved §22 plus D5 applicability rulings in the G1 approval record.'}
    (ROOT/(STEM+'-acceptance.json')).write_text(json.dumps(result,indent=2)+'\n')
    for src,dst in [('approved-core-1.1.3.schema.json',STEM+'-contracts.schema.json'),
                    ('approved-registry-a1.schema.json','creation-engine-v1.1-registry-a1.schema.json'),
                    ('approved-registry-a1.md','creation-engine-v1.1-registry-addendum-a1.md'),
                    ('approved-registry-a1-verification.json','creation-engine-v1.1-registry-a1-verification.json')]:
        (ROOT/dst).write_bytes((INPUT/src).read_bytes())
    print(json.dumps({'words':len(spec.split()),'approved_cases':len(approved_cases),'proposed_cases':len(proposed),'requirements':len(requirements),'wire_version':'1.1.3'},indent=2))

if __name__=='__main__': main()
