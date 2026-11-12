/* Dedicated authorized Atlas save path; personal library/draft storage is never initialized. */
import {api,make,ui} from '../../js/atlas-common.js';
import {materialize,serialize,validateDocument} from './document.js';
import {creditsForDocument} from './credits.js';
export class AtlasLibrary {
 constructor(editor){this.ed=editor;this.atlas=true;this.accountId=null;this.savedGeneration=-1;this.busy=false;this.tab=crypto.randomUUID();this.controller=new AbortController();this.active=true;const p=new URLSearchParams(location.search);this.world=p.get('atlas_world');this.map=p.get('atlas_map');}
 get path(){return `/worlds/${this.world}/maps/${this.map}`;}
 async initialize(){
  this.ed.drafts=null;const user=await window.Auth.requireAuth('/login.html');if(!user)throw new Error(ui('Bitte erneut anmelden.'));
  for(const id of ['libraryBtn','libraryMenuBtn','newBtn','saveCopyBtn','openBtn','importActionBtn'])document.getElementById(id).hidden=true;
  const actions=document.querySelector('.mm-top-actions');this.note=make('span',actions,'',{class:'mm-status',role:'status',id:'atlasEditorStatus'});make('a',actions,ui('Zurück zum Atlas'),{href:'/atlas?world='+this.world,class:'mm-btn',id:'atlasEditorBack'});
  for(const id of ['cloudSave','cloudSaveMenu']){const button=document.getElementById(id);button.textContent=ui('Atlas-Karte speichern');for(const attr of ['data-ui-key','data-ui-title','data-ui-aria-label'])button.removeAttribute(attr);button.onclick=()=>this.save();}
  await api(this.path+'/lease','POST',{tab:this.tab},this.controller.signal);
  const result=await api(this.path,'GET',undefined,this.controller.signal);if(!this.active)return;
  const validated=validateDocument(result.bundle.document,{knownAssets:this.ed.palette.stamps});await this.ed.palette.ensureDocumentImages(validated);if(!this.active)return;
  this.ed.loadDocument(await materialize(validated));this.ed.mapOpened=true;this.revision=result.map.revision;this.savedGeneration=this.ed.generation;this.accountId=this.world;this.updateStatus();
  this.onVisibility=()=>{clearTimeout(this.timer);if(!document.hidden)this.renew();};document.addEventListener('visibilitychange',this.onVisibility);
  window.addEventListener('pagehide',()=>this.leave());window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});this.timer=setTimeout(()=>this.renew(),45000);
 }
 async renew(){
  if(!this.active||document.hidden)return;clearTimeout(this.timer);const startedRevision=this.revision;
  try{const data=await api(this.path+'/lease','POST',{tab:this.tab},this.controller.signal);if(!this.active)return;if(startedRevision===this.revision&&data.map.revision!==this.revision)throw new Error(ui('Die Karte wurde inzwischen geändert.'));this.lost=false;}
  catch(error){if(this.active&&error.name!=='AbortError'){this.lost=true;this.note.textContent=error.message;}}
  finally{if(this.active){this.updateStatus();this.timer=setTimeout(()=>this.renew(),45000);}}
 }
 updateStatus(){
  const enabled=this.active&&!this.busy&&!this.lost&&this.accountId!==null&&this.ed.mapOpened;
  for(const id of ['cloudSave','cloudSaveMenu'])document.getElementById(id).disabled=!enabled;
  if(this.note&&!this.lost)this.note.textContent=this.busy?ui('Atlas wird gespeichert …'):this.savedGeneration===this.ed.generation?ui('Atlaskarte gespeichert.'):ui('Atlas: Änderungen offen.');
  document.getElementById('cloudStatus').textContent=ui('Atlas – private Bearbeitung');
 }
 async save(){
  if(this.busy||!this.active||this.lost||!this.ed.mapOpened)return false;
  this.ed.commitEdit();if(this.ed.isMutating()){this.ed.ui.toast(ui('Bitte die laufende Zeichenbewegung zuerst beenden.'));return false;}
  this.busy=true;this.updateStatus();const doc=this.ed.doc,generation=this.ed.generation;
  try{
   const document=await serialize(doc,'file');const blob=await this.ed.renderPngBlob(1);if(!this.active||this.ed.doc!==doc)return false;
   const png=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(blob);});
   const result=await api(this.path,'PUT',{revision:this.revision,tab:this.tab,bundle:{document,png,credits:creditsForDocument(doc,this.ed.palette).split('\n\n').slice(1).join('\n\n')}},this.controller.signal);
   if(!this.active)return false;this.revision=result.map.revision;this.savedGeneration=generation;this.ed.ui.toast(ui('Atlaskarte gespeichert.'));return true;
  }catch(error){if(this.active&&error.name!=='AbortError'){if([401,403,404,409].includes(error.status))this.lost=true;this.note.textContent=error.message;this.ed.ui.showError(error.message+' '+ui('Die lokale Karte kann weiterhin als Datei gesichert werden.'));}return false;}
  finally{this.busy=false;if(this.active)this.updateStatus();}
 }
 show(){this.ed.ui.toast(ui('Kartenwechsel und Freigaben erfolgen im Atlas.')) ;}
 close(){}
 detach(){}
 leave(){
  this.active=false;clearTimeout(this.timer);this.controller.abort();document.removeEventListener('visibilitychange',this.onVisibility);
  fetch('/api/atlas'+this.path+'/lease',{method:'DELETE',credentials:'include',keepalive:true,headers:window.Auth.buildHeaders('DELETE',true),body:JSON.stringify({tab:this.tab})}).catch(()=>{});
  this.ed.cancelInteractions();this.ed.landmass?.close();this.ed.history.clear(false);this.ed.doc=null;this.ed.renderer.doc=null;this.ed.engine=null;this.ed.mapOpened=false;this.ed.generation++;
  this.ed.canvas.getContext('2d').clearRect(0,0,this.ed.canvas.width,this.ed.canvas.height);
  cancelAnimationFrame(this.ed.frame);this.ed.frame=0;document.getElementById('app').replaceChildren();
 }
}
