/* Development-only source inventory; uses Node's existing internal Acorn. */
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const acorn=require('internal/deps/acorn/acorn/dist/acorn');
const root=process.cwd(), collected=new Map();
const files=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const tags=new Set('a aside b button caption code dd details dialog div dl dt em fieldset footer form h1 h2 h3 h4 header i img input label legend li main nav ol option p section select small span strong summary table tbody td textarea th thead tr ul'.split(' '));
const displayProps=new Set(['text','textContent','innerText','title','placeholder','aria-label','ariaLabel','label','message','alt']);
function name(node){return node?.type==='Identifier'?node.name:node?.type==='Literal'?node.value:node?.type==='MemberExpression'?name(node.property):'';}
function human(value){return typeof value==='string' && value.trim() && /[A-Za-zÄÖÜäöüß]/.test(value) && !/^(?:[#./]|https?:|data:|--|[A-Z_]+$)/.test(value.trim()) && value.length<1600 && !/^[a-z0-9_-]+$/.test(value.trim()) && !/^[a-z][A-Za-z0-9]*$/.test(value.trim()) && !/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+$/.test(value.trim());}
function candidate(node,parent,ancestors){
 if(!parent)return false;
 if(['ConditionalExpression','LogicalExpression'].includes(parent.type) || parent.type==='BinaryExpression' && parent.operator==='+'){
  const index=ancestors.lastIndexOf(parent),higher=ancestors.slice(0,index);higher.file=ancestors.file;return candidate(parent,ancestors[index-1],higher);
 }
 if(parent.type==='ReturnStatement'){
  const fn=[...ancestors].reverse().find(n=>['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression','MethodDefinition','Property'].includes(n.type));
  if(fn && /(?:label|display|format|describe|help|summary|status|role)/i.test(name(fn.id || fn.key)))return true;
 }

 if(parent.type==='Property' && parent.value===node && displayProps.has(name(parent.key)))return true;
 if(parent.type==='AssignmentExpression' && parent.right===node && displayProps.has(name(parent.left)))return true;
 if((parent.type==='CallExpression' || parent.type==='NewExpression') && parent.arguments.includes(node)){
  const n=name(parent.callee),i=parent.arguments.indexOf(node),tag=parent.arguments[0]?.value;
  if(['alert','confirm','Error','_showMessage','_logActivity','setStatus','showStatus','showToast','toast','setError','notify','announce','literal','status'].includes(n) && i===0)return true;
  if(['appendText','srdCell'].includes(n) && i===(n==='appendText'?2:0))return true;
  if(['h'].includes(n) && tags.has(tag) && i>=2)return true;
  if(['text'].includes(n) && tags.has(tag) && i===1)return true;
  if(['el','element'].includes(n) && tags.has(tag)){
   const file=ancestors.file;
   const second=['ce-species-publish.js','ce-origin-publish.js','display-preferences.js'].some(p=>file.endsWith(p));
   return i===(second?1:2);
  }
  if(['field','panel','card','select','option','srdTags','srdRollButton','detailButton'].includes(n)){
   if(['field','card','srdRollButton'].includes(n) && i===0)return true;
   if(n==='select' && i===0 && ancestors.file.endsWith('sheet-feedback.js'))return true;
   if(n==='option' && i===1)return true;
   if(n==='detailButton' && i===1)return true;
  }
 }
 const variable=[...ancestors].reverse().find(n=>n.type==='VariableDeclarator');
 if(parent.type==='ArrayExpression' && parent.elements.indexOf(node)===1 && parent.elements[0]?.type==='Literal' && typeof parent.elements[0].value==='string'){
  if(/^(?:[a-z][a-z0-9_-]*|\/[^ ]+)$/.test(parent.elements[0].value))return true;
 }
 if(parent.type==='Property' && parent.value===node && variable && /(?:LABEL|TITLE|HELP|ERROR|TEXT|NAME|ACTIVATION)/i.test(name(variable.id)))return true;
 if(parent.type==='BinaryExpression' && ['===','!==','==','!='].includes(parent.operator)){
  const other=parent.left===node?parent.right:parent.left;
  if(['textContent','innerText'].includes(name(other)))return true;
 }
 return false;
}
function visit(node,parent,ancestors,file,scriptOffset=0){
 if(!node || typeof node!=='object' || !node.type)return;
 ancestors.file=file;
 if((node.type==='Literal' && typeof node.value==='string') || node.type==='TemplateLiteral'){
  const source=node.type==='Literal'?node.value:node.quasis.map((q,i)=>(q.value.cooked || '')+(i<node.expressions.length?`{p${i}}`:'')).join('');
  if(human(source.replace(/\{p\d+\}/g,'')) && !/[<>]/.test(source) && candidate(node,parent,ancestors)){
   const key='u_'+crypto.createHash('sha1').update(source).digest('hex').slice(0,12);
   const item=collected.get(key) || {key,de:source,refs:[]};
   item.refs.push({file,start:node.start+scriptOffset,end:node.end+scriptOffset,line:node.loc.start.line,kind:node.type,
    expressions:node.type==='TemplateLiteral'?node.expressions.map(e=>({start:e.start+scriptOffset,end:e.end+scriptOffset})):[], explicit:parent?.type==='CallExpression' && name(parent.callee)==='literal'});
   collected.set(key,item);
  }else if(/[<>]/.test(source) && (candidate(node,parent,ancestors) || ancestors.some(a=>a.type==='AssignmentExpression' && name(a.left)==='innerHTML') || ancestors.some(a=>/render/i.test(name(a.id || a.key))))){
   const key='html_'+file+'_'+(node.start+scriptOffset);
   collected.set(key,{key,de:source,html:true,refs:[{file,start:node.start+scriptOffset,end:node.end+scriptOffset,line:node.loc.start.line,kind:node.type,
      expressions:node.type==='TemplateLiteral'?node.expressions.map(e=>({start:e.start+scriptOffset,end:e.end+scriptOffset})):[]} ]});
  }
 }
 for(const [key,value] of Object.entries(node)){
  if(['loc','start','end','range'].includes(key))continue;
  if(Array.isArray(value)){for(const child of value)if(child?.type)visit(child,node,[...ancestors,node],file,scriptOffset);}
  else if(value?.type)visit(value,node,[...ancestors,node],file,scriptOffset);
 }
}
for(const file of files){
 const source=fs.readFileSync(path.join(root,file),'utf8');
 const scripts=[];
 if(file.endsWith('.html')){
  const pattern=/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi;let match;
  const masked=source.replace(/<!--[\s\S]*?-->/g,m=>' '.repeat(m.length));
  while((match=pattern.exec(masked))){
   if(/\bsrc\s*=|application\/json/i.test(match[1]) || !match[2].trim())continue;
   if(match[2].includes('{{') || match[2].includes('{%'))continue;
   const offset=match.index+match[0].indexOf('>')+1;scripts.push([source.slice(offset,offset+match[2].length),offset]);
  }
 }else scripts.push([source,0]);
 for(const [script,offset] of scripts){
  try{const ast=acorn.parse(script,{ecmaVersion:'latest',sourceType:'module',locations:true});visit(ast,null,[],file,offset);}
  catch(error){throw new Error(file+': '+error.message);}
 }
}
const originals=new Map();
for(const item of collected.values())for(const ref of item.refs){
 if(!originals.has(ref.file))originals.set(ref.file,fs.readFileSync(path.join(root,ref.file),'utf8'));
 const original=originals.get(ref.file),point=index=>Array.from(original.slice(0,index)).length;
 ref.start=point(ref.start);ref.end=point(ref.end);
 for(const expression of ref.expressions){expression.start=point(expression.start);expression.end=point(expression.end);}
}
process.stdout.write(JSON.stringify([...collected.values()],null,2)+'\n');
