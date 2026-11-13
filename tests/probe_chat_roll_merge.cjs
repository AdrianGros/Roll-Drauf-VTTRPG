// Execute the actual runtime methods with controlled arrival order, not a rewritten merge.
const fs=require('node:fs'),assert=require('node:assert/strict');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const source=fs.readFileSync('vtt/static/js/play-ui.js','utf8');
const ast=acorn.parse(source,{ecmaVersion:'latest'});
const methods={};
function walk(node){
  if(!node||typeof node!=='object')return;
  if(node.type==='MethodDefinition'&&['_appendChatMessage','_mergeChatHistory'].includes(node.key.name))
    methods[node.key.name]=eval('(function '+source.slice(node.value.start,node.value.end)+')');
  for(const value of Object.values(node))if(Array.isArray(value))value.forEach(walk);else if(value&&typeof value==='object')walk(value);
}
walk(ast);
globalThis.VTTUi=s=>s;
const plain={message_id:7,created_at:'2026-11-13T10:00:00Z',sender_name:'Peer',message:'2 + 5 + 4 = 11'};
const roll={message_id:7,sender_name:'Peer',message:'Peer hat 3d6 gewürfelt: 11',rollBreakdown:'Würfel: 2 + 5 + 4'};
for(const order of ['history-first','event-first']){
  const ui={chatRows:[],renders:0,_renderChat(){this.renders++;},...methods};
  if(order==='history-first'){ui._mergeChatHistory([plain]);ui._appendChatMessage(roll);}
  else{ui._appendChatMessage(roll);ui._mergeChatHistory([plain]);}
  ui._appendChatMessage(roll);ui._mergeChatHistory([plain]);
  assert.equal(ui.chatRows.length,1,order);
  assert.equal(ui.chatRows[0].rollBreakdown,roll.rollBreakdown,order);
  ui._appendChatMessage({message_id:7,rollHidden:true,message:'hidden'});
  assert.equal(ui.chatRows.length,1);
  assert.equal(ui.chatRows[0].rollBreakdown,null);
  assert.equal(ui.chatRows[0].text,'Jemand würfelt verdeckt.');
  ui._appendChatMessage(roll);
  ui._mergeChatHistory([{...plain,hidden:true}]);
  assert.equal(ui.chatRows[0].rollHidden,true);
  assert.ok(!ui.chatRows[0].rollBreakdown);
}
process.stdout.write(JSON.stringify({status:'pass',orders:['history-first','event-first'],deduplicated:true,hidden_details_removed:true})+'\n');
