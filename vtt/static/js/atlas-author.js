/* This module is imported only after the server grants Owner/Editor context. */
import {api,request,make,ui,download,restore} from './atlas-common.js';
import {creditsForDocument} from '../mapmaker/js/credits.js';
import {renderProjection} from './atlas-reader.js';
import {loadSnapshotPalette,snapshotFromProject} from '../mapmaker/js/snapshot.js';

class Author {
 constructor(host,world,place){this.host=host;this.world=world;this.place=place;this.version=0;this.controller=new AbortController();this.dialogs=new Set();this.active=true;}
 async load(){this.data=await api(`/worlds/${this.world}`,'GET',undefined,this.controller.signal);if(!this.active)return;this.graph=structuredClone(this.data.graph);this.savedGraph=JSON.stringify(this.graph);this.render();}
 async run(action){if(this.busy)return;this.busy=true;const v=this.version;this.fields.disabled=true;this.status.textContent=ui('Atlas wird gespeichert …');try{await action();if(this.active&&v===this.version)this.status.textContent=ui('Gespeichert.');}catch(error){if(this.active&&error.name!=='AbortError')this.status.textContent=error.message;for(const dialog of this.dialogs){const status=dialog.querySelector('[role=status]');if(status)status.textContent=error.message;}}finally{this.busy=false;if(this.active)this.fields.disabled=false;}}
 apply(data){this.data=data;this.graph=structuredClone(data.graph);this.savedGraph=JSON.stringify(this.graph);this.render();}
 field(parent,label,value,oninput,{tag='input',id,type='text',max=10000}={}){const node=make(tag,make('label',parent,ui(label)),null,{...(tag==='input'?{type}:{}),...(id?{id}:{}),...(tag!=='select'?{maxlength:max}:{})});if(type==='checkbox')node.checked=value;else node.value=value??'';node.oninput=()=>oninput(type==='checkbox'?node.checked:node.value);return node;}
 button(parent,label,action,id){const button=make('button',parent,ui(label),{type:'button',class:'btn btn-secondary',...(id?{id}:{})});button.onclick=()=>this.run(action);return button;}
 render(){
  this.host.replaceChildren();make('h1',this.host,this.graph.title);this.status=make('p',this.host,'',{role:'status',id:'atlasAuthorStatus'});this.fields=make('fieldset',this.host,null);this.fields.disabled=!!this.busy;
  const actions=make('div',this.fields,null,{class:'atlas-actions'});
  this.button(actions,'Atlas speichern',async()=>this.apply(await api(`/worlds/${this.world}`,'PUT',{revision:this.data.revision,graph:this.graph},this.controller.signal)),'atlasSave');
  this.button(actions,'Aktuellen Stand laden',async()=>{if(JSON.stringify(this.graph)!==this.savedGraph&&!confirm(ui('Ungespeicherte Eingaben verwerfen und den aktuellen Stand laden?')))return;await this.load();},'atlasReload');
  this.button(actions,'Leservorschau',()=>this.preview(),'atlasPreview');
  for(const format of ['json','zip'])this.button(actions,format==='json'?'JSON-Sicherung':'ZIP-Sicherung',async()=>{const response=await request(`/worlds/${this.world}/backup?format=${format}`,'GET',undefined,this.controller.signal);download(await response.blob(),`atlas-${this.world}.${format}`);},'atlasBackup-'+format);
  if(this.data.role==='owner'){
   const file=make('input',make('label',actions,ui('Eigene Welt aus Sicherung wiederherstellen')),null,{type:'file',accept:'.json,.zip',id:'atlasRestore'});
   file.onchange=()=>this.run(async()=>{const selected=file.files[0];if(selected&&confirm(ui('Diese eigene Welt durch die Sicherung ersetzen? Freigaben bleiben erhalten.')))this.apply(await restore(selected,this.data.revision));file.value='';});
   this.button(actions,'Welt löschen',async()=>{if(confirm(ui('Diese Welt und ihre Atlaskarten dauerhaft löschen? Sichere sie bei Bedarf zuerst.'))){await api(`/worlds/${this.world}`,'DELETE',{revision:this.data.revision},this.controller.signal);location.href='/atlas';}},'atlasDelete');
  }
  const meta=make('section',this.fields,null,{class:'atlas-panel'});make('h2',meta,ui('Welt'));
  this.field(meta,'Weltname',this.graph.title,value=>this.graph.title=value,{id:'atlasTitle',max:80});this.field(meta,'Öffentliche Beschreibung',this.graph.summary,value=>this.graph.summary=value,{tag:'textarea',id:'atlasSummary',max:2000});this.field(meta,'Private Welt-Lore',this.graph.private_lore,value=>this.graph.private_lore=value,{tag:'textarea',id:'atlasPrivateLore'});
  const columns=make('div',this.fields,null,{class:'atlas-columns'}),left=make('section',columns,null,{class:'atlas-panel'}),right=make('section',columns,null,{class:'atlas-panel'});
  make('h2',left,ui('Orte'));const select=make('select',left,null,{id:'atlasPlaceSelect','aria-label':ui('Ort auswählen')});select.add(new Option(ui('Ort auswählen'),''));for(const place of this.graph.places)select.add(new Option(place.name,place.id));select.value=this.place||'';select.onchange=()=>{this.place=select.value;this.render();};
  const add=make('button',left,ui('Ort anlegen'),{type:'button',class:'btn btn-secondary',id:'atlasAddPlace'});add.onclick=()=>{const row={id:crypto.randomUUID(),name:ui('Neuer Ort'),parent_id:null,map_id:null,x:null,y:null,lore:'',private_lore:'',reader_visible:false,links:[]};this.graph.places.push(row);this.place=row.id;this.render();};
  const place=this.graph.places.find(row=>row.id===this.place);if(place)this.placeFields(left,place);
  this.mapFields(right,place);this.libraryFields(right);
  if(this.data.role==='owner')this.memberFields();
 }
 placeFields(parent,place){
  const section=make('div',parent,null,{class:'atlas-author-fields'});this.field(section,'Ortsname',place.name,value=>place.name=value,{id:'atlasPlaceName',max:120});
  const select=this.field(section,'Übergeordneter Ort',place.parent_id,value=>place.parent_id=value||null,{tag:'select',id:'atlasParent'});select.add(new Option(ui('Kein übergeordneter Ort'),''));for(const row of this.graph.places.filter(row=>row.id!==place.id))select.add(new Option(row.name,row.id));select.value=place.parent_id||'';
  const map=this.field(section,'Ortskarte',place.map_id,value=>{place.map_id=value||null;place.x=place.y=null;this.render();},{tag:'select',id:'atlasPlaceMap'});map.add(new Option(ui('Ort ohne Karte'),''));for(const row of this.graph.maps)map.add(new Option(row.title,row.id));map.value=place.map_id||'';
  for(const axis of ['x','y']){const input=this.field(section,axis==='x'?'X (Kartenpixel)':'Y (Kartenpixel)',place[axis],value=>place[axis]=value===''?null:Number(value),{type:'number',id:'atlasPlace-'+axis});input.min=0;input.step='any';input.disabled=!place.map_id;}
  this.field(parent,'Veröffentlichbare Orts-Lore',place.lore,value=>place.lore=value,{tag:'textarea',id:'atlasPlaceLore'});this.field(parent,'Private Orts-Lore',place.private_lore,value=>place.private_lore=value,{tag:'textarea',id:'atlasPlacePrivate'});this.field(parent,'Ort für Leser sichtbar',place.reader_visible,value=>place.reader_visible=value,{type:'checkbox',id:'atlasPlaceVisible'});
  const links=this.field(parent,'Verknüpfte Orte',null,()=>place.links=[...links.selectedOptions].map(option=>option.value),{tag:'select',id:'atlasPlaceLinks'});links.multiple=true;links.size=Math.min(5,Math.max(2,this.graph.places.length));for(const row of this.graph.places.filter(row=>row.id!==place.id)){const option=new Option(row.name,row.id);option.selected=place.links.includes(row.id);links.add(option);}
  const remove=make('button',parent,ui('Ort entfernen'),{type:'button',class:'btn btn-secondary',id:'atlasRemovePlace'});remove.onclick=()=>{if(this.graph.places.some(row=>row.parent_id===place.id||row.links.includes(place.id))){this.status.textContent=ui('Löse zuerst übergeordnete Ortsverweise und Verknüpfungen.');return;}this.graph.places=this.graph.places.filter(row=>row.id!==place.id);this.place=null;this.render();};
  make('a',parent,ui('Stabiler Ortslink'),{href:`/atlas?world=${this.world}&place=${place.id}`});
 }
 mapFields(parent,place){
  make('h2',parent,ui('Karten'));const select=make('select',parent,null,{id:'atlasAuthorMap','aria-label':ui('Karte')});for(const row of this.graph.maps)select.add(new Option(row.title,row.id));
  let id=this.currentMap||place?.map_id||this.graph.maps[0]?.id;if(!this.graph.maps.some(row=>row.id===id))id=this.graph.maps[0]?.id;select.value=id||'';this.currentMap=id;select.onchange=()=>{this.currentMap=select.value;this.render();};
  const map=this.graph.maps.find(row=>row.id===id);if(!map){make('p',parent,ui('Eine Welt kann ohne Karte angelegt und genutzt werden.'));return;}
  const info=this.data.maps.find(row=>row.id===id);this.field(parent,'Kartentitel',map.title,value=>map.title=value,{id:'atlasMapTitle',max:80});this.field(parent,'Karte für Leser sichtbar',map.reader_visible,value=>map.reader_visible=value,{type:'checkbox',id:'atlasMapVisible'});
  const scale=this.field(parent,'Kilometer pro Kartenpixel',map.km_per_pixel,value=>map.km_per_pixel=value===''?null:Number(value),{type:'number',id:'atlasMapScale'});scale.min='0.000000001';scale.step='any';
  make('p',parent,ui('Für Ortskoordinaten zuerst einen Ort auswählen und auf die Karte klicken.'));
  const viewport=make('div',parent,null,{class:'atlas-map-viewport'}),image=make('img',viewport,null,{src:`/api/atlas/worlds/${this.world}/maps/${id}.png?revision=${info.revision}`,alt:map.title,id:'atlasAuthorImage'});image.style.width='100%';image.style.height='auto';
  image.onclick=event=>{if(!place)return;const rect=image.getBoundingClientRect();place.map_id=id;place.x=Math.round((event.clientX-rect.left)/rect.width*info.width*100)/100;place.y=Math.round((event.clientY-rect.top)/rect.height*info.height*100)/100;this.render();};
  make('a',parent,ui('Im Karteneditor bearbeiten'),{href:`/static/mapmaker/index.html?atlas_world=${this.world}&atlas_map=${id}`,class:'btn btn-secondary',id:'atlasEditMap'});
  this.button(parent,'Karte aus Atlas entfernen',async()=>{if(JSON.stringify(this.graph)!==this.savedGraph)throw new Error(ui('Bitte zuerst die Atlas-Eingaben speichern.'));this.apply(await api(`/worlds/${this.world}/maps/${id}`,'DELETE',{revision:this.data.revision},this.controller.signal));},'atlasRemoveMap');
 }
 libraryFields(parent){
  const controls=make('div',parent,null,{class:'atlas-actions'}),list=make('select',make('label',controls,ui('Eigene Kartenbibliothek')),null,{id:'atlasLibrarySelect'});for(const project of this.projects||[])list.add(new Option(project.title,project.id));
  this.button(controls,'Bibliothek laden',async()=>{const data=await api(`/api/assets/mapmaker/projects?page=${this.libraryPage||1}`,'GET',undefined,this.controller.signal);this.projects=data.projects;this.libraryMore=data.page*data.pageSize<data.total;this.render();},'atlasLibraryLoad');
  if(this.libraryMore)this.button(controls,'Weitere Bibliothekskarten',async()=>{this.libraryPage=(this.libraryPage||1)+1;const data=await api(`/api/assets/mapmaker/projects?page=${this.libraryPage}`,'GET',undefined,this.controller.signal);this.projects=data.projects;this.libraryMore=data.page*data.pageSize<data.total;this.render();});
  this.button(controls,'Bibliothekskarte als Kopie übernehmen',async()=>{
   if(JSON.stringify(this.graph)!==this.savedGraph)throw new Error(ui('Bitte zuerst die Atlas-Eingaben speichern.'));
   if(!list.value)throw new Error(ui('Bitte eine Bibliothekskarte auswählen.'));
   const v=this.version,source=await api('/api/assets/mapmaker/projects/'+list.value,'GET',undefined,this.controller.signal);this.palettePromise||=loadSnapshotPalette();
   const snapshot=await snapshotFromProject({...source,palette:await this.palettePromise,isCurrent:()=>this.active&&v===this.version});if(!this.active)return;
   const dialog=this.dialog(ui('Kartenkopie übernehmen')),url=URL.createObjectURL(snapshot.blob);make('img',dialog,null,{src:url,alt:snapshot.title,class:'atlas-preview'});make('p',dialog,ui('Diese Kopie bleibt zunächst privat. Das persönliche Original bleibt unabhängig.'));
   const revision=this.data.revision;this.button(dialog,'Kopie in Atlas übernehmen',async()=>{const png=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(snapshot.blob);});const result=await api(`/worlds/${this.world}/maps`,'POST',{revision,project_id:source.project.id,project_revision:source.project.revision,png,credits:creditsForDocument(source.document,await this.palettePromise).split('\n\n').slice(1).join('\n\n')},this.controller.signal);dialog.close();this.currentMap=result.map_id;this.apply(result.world);},'atlasAttachConfirm');dialog.addEventListener('close',()=>URL.revokeObjectURL(url),{once:true});dialog.showModal();
  },'atlasAttach');make('a',parent,ui('Neue Karte in der Kartenwerkstatt anlegen'),{href:'/mapmaker'});
 }
 dialog(title){const dialog=make('dialog',document.body,null,{class:'atlas-dialog atlas-layout','aria-label':title});this.dialogs.add(dialog);make('h2',dialog,title);make('p',dialog,'',{role:'status'});const close=make('button',dialog,ui('Schließen'),{type:'button',class:'btn btn-secondary'});close.onclick=()=>dialog.close();dialog.addEventListener('close',()=>{dialog.remove();this.dialogs.delete(dialog);},{once:true});return dialog;}
 async preview(){
  if(JSON.stringify(this.graph)!==this.savedGraph)throw new Error(ui('Bitte zuerst die Atlas-Eingaben speichern.'));
  const data=await api(`/worlds/${this.world}/preview`,'GET',undefined,this.controller.signal);if(!this.active)return;const dialog=this.dialog(ui('Leservorschau')),host=make('div',dialog,null);const clear=renderProjection(host,{world:this.world,projection:data.projection,imageUrl:id=>`/api/atlas/worlds/${this.world}/maps/${id}.png?revision=${data.revision}`});dialog.addEventListener('close',clear,{once:true});
  if(this.data.role==='owner'){const consent=this.field(dialog,'Alle sichtbaren Kartenpixel und angezeigten Ortsinformationen für die eingeladenen Leser freigeben.',false,()=>{}, {type:'checkbox',id:'atlasPublishConsent'});
   this.button(dialog,'Leserfassung veröffentlichen',async()=>{if(!consent.checked)throw new Error(ui('Bitte die sichtbaren Kartenbilder ausdrücklich freigeben.'));await api(`/worlds/${this.world}/publish`,'POST',{revision:data.revision,confirm_visible_pixels:true},this.controller.signal);dialog.close();await this.load();},'atlasPublish');}
  dialog.showModal();
 }
 memberFields(){const section=make('section',this.fields,null,{class:'atlas-panel'});make('h2',section,ui('Persönliche Freigaben'));make('p',section,ui('Nur diese ausdrücklich eingeladenen VTT-Konten erhalten Zugriff.'));
  const username=this.field(section,'VTT-Benutzername','',()=>{},{id:'atlasMemberName',max:80});const role=this.field(section,'Weltrolle','',()=>{},{tag:'select',id:'atlasMemberRole'});role.add(new Option(ui('Leser'),'reader'));role.add(new Option(ui('Autor'),'editor'));role.add(new Option(ui('Zugriff entfernen'),'remove'));
  this.button(section,'Zugriff speichern',async()=>{if(JSON.stringify(this.graph)!==this.savedGraph)throw new Error(ui('Bitte zuerst die Atlas-Eingaben speichern.'));this.apply(await api(`/worlds/${this.world}/members`,'PUT',{revision:this.data.revision,username:username.value,role:role.value==='remove'?null:role.value},this.controller.signal));},'atlasGrant');
  const list=make('ul',section,null,{id:'atlasMembers'});for(const row of this.data.members)make('li',list,row.username+' · '+ui(row.role==='editor'?'Autor':'Leser'));
 }
 destroy(){this.active=false;this.version++;this.controller.abort();for(const dialog of this.dialogs)dialog.close();this.dialogs.clear();this.graph=null;this.data=null;this.projects=null;this.host.replaceChildren();}
}
export async function mountAuthor(host,world,place){const author=new Author(host,world,place);await author.load();const before=event=>{if(author.active&&JSON.stringify(author.graph)!==author.savedGraph){event.preventDefault();event.returnValue='';}};window.addEventListener('beforeunload',before);const leave=()=>author.destroy();window.addEventListener('pagehide',leave);return ()=>{window.removeEventListener('pagehide',leave);window.removeEventListener('beforeunload',before);author.destroy();};}
