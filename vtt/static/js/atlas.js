import {api,make,ui,restore} from './atlas-common.js';
const root=document.getElementById('atlasRoot');let cleanup,controller=new AbortController();
async function boot(){
 const user=await window.Auth.requireAuth('/login.html');if(!user)return;
 const params=new URLSearchParams(location.search),world=params.get('world');root.replaceChildren();
 if(world){
  const context=await api(`/worlds/${encodeURIComponent(world)}/context`,'GET',undefined,controller.signal);
  const back=make('a',root,ui('Alle Welten'),{href:'/atlas',class:'btn btn-secondary'}),host=make('div',root,null);
  if(context.role==='reader'){const {mountReader}=await import('./atlas-reader.js');cleanup=await mountReader(host,world,params.get('place'));}
  else{const {mountAuthor}=await import('./atlas-author.js');cleanup=await mountAuthor(host,world,params.get('place'));}
  return;
 }
 make('h1',root,ui('Atlas'));make('p',root,ui('Eigene Welten und ausdrücklich mit dir geteilte Leserfassungen.'));
 const form=make('form',root,null,{class:'atlas-actions'}),name=make('input',make('label',form,ui('Neue Welt')),null,{required:'',maxlength:80,id:'atlasNewTitle'});
 make('button',form,ui('Welt anlegen'),{type:'submit',class:'btn btn-primary',id:'atlasCreate'});const status=make('p',root,'',{role:'status',id:'atlasStatus'});
 form.onsubmit=async event=>{event.preventDefault();form.querySelector('button').disabled=true;try{const data=await api('/worlds','POST',{title:name.value});location.href='/atlas?world='+data.id;}catch(error){status.textContent=error.message;form.querySelector('button').disabled=false;}};
 const input=make('input',make('label',root,ui('Sicherung importieren (JSON oder ZIP)')),null,{type:'file',accept:'.json,.zip',id:'atlasImport'});
 input.onchange=async()=>{if(!input.files[0])return;input.disabled=true;try{const data=await restore(input.files[0]);location.href='/atlas?world='+data.id;}catch(error){status.textContent=error.message;}finally{input.disabled=false;input.value='';}};
 const list=make('ul',root,null,{class:'atlas-world-list',id:'atlasWorlds'}),more=make('button',root,ui('Weitere Welten'),{type:'button',class:'btn btn-secondary',hidden:''});let cursor;
 async function load(){const data=await api('/worlds'+(cursor?'?after='+cursor:''),'GET',undefined,controller.signal);for(const world of data.worlds){const row=make('li',list,null);make('a',row,world.title||ui('Noch nicht veröffentlicht'),{href:'/atlas?world='+world.id});make('span',row,' · '+ui(world.role==='owner'?'Besitzer':world.role==='editor'?'Autor':'Leser'));}cursor=data.next_cursor;more.hidden=!cursor;}
 more.onclick=()=>load().catch(error=>status.textContent=error.message);await load();
}
window.addEventListener('pagehide',()=>{controller.abort();cleanup?.();root.replaceChildren();});window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
boot().catch(error=>{if(error.name!=='AbortError'){root.replaceChildren();make('p',root,error.message,{role:'alert'});}});
