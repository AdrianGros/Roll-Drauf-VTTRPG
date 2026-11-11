/* Typed Background/Feat companion in the existing Eagle workspace. */
(function () {
  'use strict';
  const API='/api/ce/authoring', SCHEMA='roll-drauf.origin-supplement.v1';
  const $=(id)=>document.getElementById(id);
  const state={data:null,worlds:[],document:null,checked:null,dirty:false};
  const world=()=>$('ce-world')?.value || 'personal';
  const text=(tag,value)=>Object.assign(document.createElement(tag),{textContent:value});
  async function call(path,method='GET',body=null) {
    const response=await fetch(path,{method,credentials:'include',headers:Auth.buildHeaders(method,body!==null),...(body===null?{}:{body:JSON.stringify(body)})});
    const data=await response.json().catch(()=>({}));
    if(!response.ok || data.ok===false) throw new Error(data.detail || data.message || 'Die Anfrage konnte nicht abgeschlossen werden.');
    return data;
  }
  function option(value,label){return Object.assign(text('option',label),{value});}
  function choices(root,rows){
    $(root).replaceChildren(...rows.map(row=>{
      const label=text('label','');const box=Object.assign(document.createElement('input'),{type:'checkbox',value:row.id});
      label.append(box,document.createTextNode(' '+row.name));return label;
    }));
  }
  const checked=(id)=>[...$(id).querySelectorAll('input:checked')].map(node=>node.value);
  function markDirty(){state.dirty=true;state.checked=null;$('ce-origin-publish').disabled=true;}
  function report(result){
    const box=$('ce-origin-report');box.replaceChildren();
    box.append(text('strong',result.report.playable?'Spielbar: Quelle und Zusatz können veröffentlicht werden.':'Noch nicht spielbar: Bitte die markierten Punkte beheben.'));
    const list=text('ul','');
    for(const entry of result.report.entries){const row=text('li',entry.message);row.dataset.status=entry.status;list.append(row);}
    box.append(list);
    if(result.profile){
      const profile=result.profile,entry=profile.entry,preview=text('section','');preview.className='ce-origin-preview';
      preview.append(text('h3',entry.name),text('p',profile.description));
      if(profile.kind==='background')preview.append(text('p','Attribute: '+entry.abilities.map(id=>state.data.abilities.find(a=>a.id===id)?.name || id).join(', ')),text('p','Herkunftstalent: '+entry.feat),text('p','Startausrüstung: 50 GM (Paket B).'));
      else for(const grant of entry.mechanics)preview.append(text('p',grantLabel(grant)));
      box.append(preview);
    }
  }
  function grantLabel(grant){
    if(grant.kind==='skill_proficiency')return 'Übung: '+(state.data.skills.find(s=>s.id===grant.skill)?.name || grant.skill);
    if(grant.kind==='initiative_pb')return 'Initiative: +Übungsbonus';
    const names={ac:'Rüstungsklasse',initiative:'Initiative',speed_meters:'Bewegung (m)',hp_per_level:'Trefferpunkte je Stufe'};
    return (names[grant.kind] || grant.kind)+': +'+grant.value;
  }
  function supplement(){
    if(state.document?.type==='background')return {schema:SCHEMA,abilities:checked('ce-origin-abilities'),skills:checked('ce-origin-bg-skills'),toolId:$('ce-origin-tool').value || null,featId:$('ce-origin-feat').value || null};
    const grants=checked('ce-origin-feat-skills').map(skill=>({kind:'skill_proficiency',skill}));
    for(const [kind,id] of [['ac','ac'],['initiative','initiative'],['speed_meters','speed'],['hp_per_level','hp']]){
      const value=Number($('ce-origin-'+id).value);if(value)grants.push({kind,value});
    }
    if($('ce-origin-initiative-pb').checked)grants.push({kind:'initiative_pb'});
    const ability=$('ce-origin-prerequisite').value;
    return {schema:SCHEMA,category:$('ce-origin-category').value,minLevel:Number($('ce-origin-level').value),
      prerequisite:ability?{ability,min:Number($('ce-origin-min-score').value)}:null,grants};
  }
  function fill(extra){
    const background=state.document?.type==='background';
    $('ce-origin-background-fields').hidden=!background;$('ce-origin-feat-fields').hidden=background;
    const saved=extra || (background?{abilities:['int','con','wis'],skills:[],toolId:null,featId:null}:{category:'origin',minLevel:1,prerequisite:null,grants:[]});
    if(background){
      for(const [id,key] of [['ce-origin-abilities','abilities'],['ce-origin-bg-skills','skills']])for(const box of $(id).querySelectorAll('input'))box.checked=(saved[key] || []).includes(box.value);
      $('ce-origin-tool').value=saved.toolId || '';$('ce-origin-feat').value=saved.featId || '';
    }else{
      $('ce-origin-category').value=saved.category || 'origin';$('ce-origin-level').value=saved.minLevel || 1;
      $('ce-origin-prerequisite').value=saved.prerequisite?.ability || '';$('ce-origin-min-score').value=saved.prerequisite?.min || 13;
      const grants=saved.grants || [];
      for(const box of $('ce-origin-feat-skills').querySelectorAll('input'))box.checked=grants.some(g=>g.kind==='skill_proficiency' && g.skill===box.value);
      for(const [kind,id] of [['ac','ac'],['initiative','initiative'],['speed_meters','speed'],['hp_per_level','hp']])$('ce-origin-'+id).value=grants.find(g=>g.kind===kind)?.value || 0;
      $('ce-origin-initiative-pb').checked=grants.some(g=>g.kind==='initiative_pb');
    }
  }
  async function refreshFeats(){
    const catalog=await call('/api/srd-creator/origin-catalog');
    const feats=[...state.data.feats,...catalog.feats].filter(row=>row.category==='Herkunftstalent');
    const previous=$('ce-origin-feat').value;
    $('ce-origin-feat').replaceChildren(option('','Bitte wählen'),...feats.map(row=>option(row.id,row.name+(row.origin?' · Fassung '+row.origin.revision:''))));
    $('ce-origin-feat').value=previous;
  }
  async function loadSource(){
    const uuid=$('ce-origin-source').value;state.checked=null;$('ce-origin-publish').disabled=true;
    $('ce-origin-report').replaceChildren();$('ce-origin-form').hidden=!uuid;
    if(!uuid){state.document=null;return;}
    const {document}=await call(`${API}/document?world=${encodeURIComponent(world())}&uuid=${encodeURIComponent(uuid)}`);
    if(!document)throw new Error('Quelle nicht mehr verfügbar.');
    state.document=document;
    $('ce-origin-name').value=document.source.name;
    // Show plain text; preserve the original description unless explicitly edited.
    const parser=new DOMParser().parseFromString(document.source.system?.description?.value || '', 'text/html');
    state.descriptionText=parser.body.textContent || '';$('ce-origin-description').value=state.descriptionText;
    await refreshFeats();fill(document.source.flags?.rollDraufOrigins?.supplement);
    state.dirty=false;
  }
  async function refresh(selected){
    const listing=await call(`${API}/documents?world=${encodeURIComponent(world())}&documentName=Item`);
    const rows=[...(listing.world || []),...(listing.library || [])].filter(row=>['feat','background'].includes(row.type));
    const previous=selected || $('ce-origin-source').value;
    $('ce-origin-source').replaceChildren(option('','Quelle auswählen'),...rows.map(row=>option(row.uuid,`${row.name} · ${row.type==='feat'?'Merkmal':'Hintergrund'}${row.pack?' · Bibliothek':''}`)));
    if(rows.some(row=>row.uuid===previous))$('ce-origin-source').value=previous;
    $('ce-origin-scope').replaceChildren(...state.worlds.map(row=>option(row.id,row.kind==='personal'?'Nur für mich':'Kampagne: '+row.label)),option('global','VTT-Compendium · alle angemeldeten Nutzer'));
    $('ce-origin-scope').value=world();await loadSource();
  }
  async function save(){
    const document=state.document;if(!document)throw new Error('Zuerst eine Quelle wählen.');
    // Obtain the same canonical digest used by check/publish; source revision CAS
    // below also catches an edit made while these requests were in flight.
    const body={world:world(),uuid:document.uuid,supplement:supplement()};
    const current=await call(`${API}/origins/check`,'POST',body);
    if(current.source.revision!==document.revision)throw new Error('Quelle inzwischen geändert. Bitte neu laden.');
    const changes={...body,expectedDigest:current.source.digest,expectedRevision:document.revision};
    if($('ce-origin-name').value!==document.source.name)changes.name=$('ce-origin-name').value;
    if($('ce-origin-description').value!==state.descriptionText)changes.description=$('ce-origin-description').value;
    const result=await call(`${API}/origins/draft`,'PUT',changes);
    state.document=result.document;state.descriptionText=$('ce-origin-description').value;state.dirty=false;
    $('ce-origin-report').replaceChildren(text('p','Entwurf gespeichert · Revision '+result.document.revision));
  }
  async function check(){
    await save();
    const result=await call(`${API}/origins/check`,'POST',{world:world(),uuid:state.document.uuid,supplement:supplement()});
    state.checked=result;report(result);$('ce-origin-publish').disabled=!result.report.playable;
  }
  async function publish(){
    if(!state.checked || state.dirty)return;
    const result=await call(`${API}/origins/publish`,'POST',{world:world(),uuid:state.document.uuid,supplement:supplement(),scope:$('ce-origin-scope').value,
      expectedDigest:state.checked.source.digest,expectedProfileDigest:state.checked.profileDigest});
    $('ce-origin-report').prepend(text('p',`Veröffentlicht · Fassung ${result.revision.revision}. Berechtigte Nutzer finden sie im Charakter-Ersteller.`));
    $('ce-origin-publish').disabled=true;await refreshFeats();
  }
  async function create(kind){
    const id='O'+crypto.randomUUID().replaceAll('-','').slice(0,20);
    const source={name:kind==='feat'?'Wachsamer Pfadfinder':'Pfadwanderer',type:kind,
      system:{source:{rules:'2024'},description:{value:'Eigener Entwurf. Beschreibung und Regeln vor Veröffentlichung anpassen.'}},
      flags:{rollDraufOrigins:{supplement:kind==='feat'?{schema:SCHEMA,category:'origin',minLevel:1,prerequisite:null,grants:[{kind:'initiative_pb'}]}:
        {schema:SCHEMA,abilities:['int','con','wis'],skills:['arkane-kunde','geschichte'],toolId:null,featId:state.data.feats.find(f=>f.category==='Herkunftstalent')?.id}}}};
    await call(`${API}/request`,'POST',{world:world(),type:'document.create',payload:{target:{world:'Item'},id,data:source}});
    sessionStorage.setItem('ce.origin.pending',JSON.stringify({world:world(),uuid:'Item.'+id}));
    state.dirty=false;location.hash='ce-origins';location.reload();
  }
  function run(button,fn){button.addEventListener('click',async()=>{
    button.disabled=true;
    try{await fn();}catch(error){$('ce-origin-report').replaceChildren(text('p',error.message));}
    finally{button.disabled=button.id==='ce-origin-publish';}
  });}
  async function init(){
    const section=$('ce-origins');if(!section || !window.Auth)return;
    const catalog=await call('/api/srd-creator/origin-catalog');if(!catalog.enabled)return;
    const [data,worlds]=await Promise.all([call('/api/srd-creator/creator-data'),call(`${API}/worlds`)]);state.data=data;state.worlds=worlds.worlds || [];
    choices('ce-origin-abilities',data.abilities);choices('ce-origin-bg-skills',data.skills);choices('ce-origin-feat-skills',data.skills);
    $('ce-origin-prerequisite').replaceChildren(option('','Keine'),...data.abilities.map(row=>option(row.id,row.name)));
    const tools=data.equipment.items.filter(row=>row.id.startsWith('equipment.tools.'));
    $('ce-origin-tool').replaceChildren(option('','Kein Werkzeug'),...tools.map(row=>option(row.id,row.name)));
    let pending;try{pending=JSON.parse(sessionStorage.getItem('ce.origin.pending') || 'null');}catch(_){}
    await refresh(pending?.world===world()?pending.uuid:null);sessionStorage.removeItem('ce.origin.pending');
    for(const [id,fn] of [['save',save],['check',check],['publish',publish],['refresh',()=>refresh()],['new-feat',()=>create('feat')],['new-background',()=>create('background')]])run($('ce-origin-'+id),fn);
    $('ce-origin-source').addEventListener('change',()=>loadSource().catch(error=>$('ce-origin-report').replaceChildren(text('p',error.message))));
    $('ce-world').addEventListener('change',()=>refresh().catch(error=>$('ce-origin-report').replaceChildren(text('p',error.message))));
    $('ce-origin-form').addEventListener('input',markDirty);
    $('ce-origin-category').addEventListener('change',()=>{$('ce-origin-level').value=$('ce-origin-category').value==='origin'?1:4;markDirty();});
    window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue='';}});
    section.hidden=false;section.dataset.ready='true';
    if(location.hash==='#ce-origins')section.scrollIntoView();
  }
  document.addEventListener('DOMContentLoaded',()=>init().catch(error=>{const section=$('ce-origins');if(section)section.hidden=false;$('ce-origin-report')?.replaceChildren(text('p',error.message));}));
})();
