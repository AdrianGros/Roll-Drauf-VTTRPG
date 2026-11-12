"""Independent topology/digest contracts and asynchronous worker lifecycle."""
import json
from pathlib import Path
import subprocess
import pytest
NODE='/usr/local/lib/python3.12/site-packages/playwright/driver/node'
ROOT=Path(__file__).resolve().parents[1]
def node(code):
    result=subprocess.run([NODE,'--input-type=module','-e',code],cwd=ROOT,text=True,capture_output=True,timeout=20)
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout)

def test_versioned_masks_are_exact_connected_bounded_and_seeded():
    result=node('''
import {generateLandmass,normalizeLandmass} from './vtt/static/mapmaker/js/landmass.js';
import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
const vectors=[[1337,'island',45,60,128,{w:2400,h:1600}],[0,'continent',80,0,512,{w:4096,h:4096}],[4294967295,'island',10,100,256,{w:256,h:4096}]];
const out=[];
for(const [seed,form,land,roughness,resolution,size] of vectors){
 const input={seed,form,land,roughness,resolution}, start=performance.now(),{parameters:p,mask}=generateLandmass(input,size);
 const hash=createHash('sha256').update(mask).digest('hex');
 assert.equal(hash,createHash('sha256').update(generateLandmass(input,size).mask).digest('hex'));
 assert.equal(mask.reduce((a,b)=>a+b,0),p.target);assert.ok(mask.length<=262144);
 const seen=new Set(),todo=[mask.findIndex(v=>v===1)];seen.add(todo[0]);
 for(let i=0;i<todo.length;i++){const v=todo[i],x=v%p.w,y=Math.floor(v/p.w);
  if(form==='island')assert.ok(x>=p.margin&&x<p.w-p.margin&&y>=p.margin&&y<p.h-p.margin);
  for(const next of [x>0?v-1:-1,x<p.w-1?v+1:-1,y>0?v-p.w:-1,y<p.h-1?v+p.w:-1])
   if(next>=0&&mask[next]&&!seen.has(next)){seen.add(next);todo.push(next)}
 }assert.equal(seen.size,p.target);
 if(seed<4294967295)assert.notEqual(hash,createHash('sha256').update(generateLandmass({...input,seed:seed+1},size).mask).digest('hex'));
 out.push({hash,ms:performance.now()-start});
}
for(const invalid of [{seed:-1},{seed:4294967296},{seed:1.1},{land:9},{land:81},{roughness:101},{resolution:1024},{form:'other'}])
 assert.throws(()=>normalizeLandmass({seed:0,form:'island',land:45,roughness:50,resolution:128,...invalid},{w:256,h:256}));
assert.throws(()=>normalizeLandmass({seed:0,form:'island',land:80,roughness:50,resolution:128},{w:256,h:4096}));
console.log(JSON.stringify(out));
''')
    assert [r['hash'] for r in result]==['3dca249bb7a1f3a509eb10f296b8b41c6ff59c5e345f5552d21c6b5a659419c5','f1140119501b1f283b1037147aeecb1321deac315b78a04f158e6bc33d43216b','77b8b25c7ad36a659457af608a5660935b9d93535d2ebaa4b25d601a9b44f90d']

def test_job_cancel_stale_reply_timeout_and_recovery():
    assert node('''
import {LandmassJob} from './vtt/static/mapmaker/js/landmass-dialog.js';import assert from 'node:assert/strict';
const workers=[],factory=()=>{const worker={terminated:false,terminate(){this.terminated=true},postMessage(data){this.data=data}};workers.push(worker);return worker};
const job=new LandmassJob(factory,20),first=job.run({},{}),cancelled=assert.rejects(first,/cancelled/);job.cancel();await cancelled;
assert.ok(workers[0].terminated);const second=job.run({},{});
workers[0].onmessage({data:{id:workers[0].data.id,mask:'stale'}});assert.ok(job.current);
workers[1].onmessage({data:{id:workers[1].data.id,mask:'fresh'}});assert.equal((await second).mask,'fresh');assert.ok(workers[1].terminated);
await assert.rejects(job.run({},{}),/timeout/);assert.ok(workers[2].terminated);
const recovery=job.run({},{});workers[3].onmessage({data:{id:workers[3].data.id,error:'parameters'}});await assert.rejects(recovery,/parameters/);assert.equal(job.current,null);
console.log(JSON.stringify({pass:true}));
''')=={'pass':True}
