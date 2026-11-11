globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/* Browser-local presentation. Only repository-authored, explicitly marked UI is translated. */
(function(){
  'use strict';
  const KEY='vtt.display.v1';
  const defaults={schema:1,theme:'paper',language:'de',unit:'m',accent:'default',stickyPortrait:false};
  const own=(obj,key)=>Object.prototype.hasOwnProperty.call(obj,key);
  function clean(raw){
    raw=raw && typeof raw==='object' && !Array.isArray(raw)?raw:{};
    return {schema:1,theme:['paper','night'].includes(raw.theme)?raw.theme:'paper',language:['de','en'].includes(raw.language)?raw.language:'de',
      unit:['m','ft'].includes(raw.unit)?raw.unit:'m',accent:['default','bronze','teal'].includes(raw.accent)?raw.accent:'default',stickyPortrait:raw.stickyPortrait===true};
  }
  let prefs;
  try{const raw=localStorage.getItem(KEY);prefs=clean(raw?JSON.parse(raw):JSON.parse(localStorage.getItem('vtt.sheet.display.v1') || '{}'));}catch(_){prefs={...defaults};}
  const language=prefs.language; // A language change takes effect on the explicitly requested reload.
  const messages=window.VTTUiMessages || {};
  const bySource=new Map(Object.entries(messages).filter(([,row])=>row.source).map(([key,row])=>[row.source,key]));
  function t(key,parameters={}){
    const row=messages[key];let result=row?(row[language] || row.de):key;
    return String(result).replace(/\{([a-zA-Z0-9_]+)\}/g,(match,name)=>own(parameters,name)?String(parameters[name]):match);
  }
  function literal(source,parameters={}){const key=bySource.get(source);return key?t(key,parameters):String(source).replace(/\{([a-zA-Z0-9_]+)\}/g,(m,name)=>own(parameters,name)?String(parameters[name]):m);}
  function translate(root=document){
    const nodes=[];if(root.nodeType===1)nodes.push(root);
    if(root.querySelectorAll)nodes.push(...root.querySelectorAll('[data-ui-key],[data-ui-title],[data-ui-placeholder],[data-ui-aria-label],[data-ui-alt]'));
    for(const node of nodes){
      if(node.dataset.uiKey && messages[node.dataset.uiKey]){const value=t(node.dataset.uiKey);if(node.textContent!==value)node.textContent=value;}
      for(const attribute of ['title','placeholder','aria-label','alt']){
        const key=node.getAttribute('data-ui-'+attribute);if(key && messages[key])node.setAttribute(attribute,t(key));
      }
    }
  }
  function number(value,maximumFractionDigits=2){return new Intl.NumberFormat(language==='en'?'en-US':'de-DE',{maximumFractionDigits}).format(value);}
  function formatDistance(meters){return `${number(prefs.unit==='ft'?Number(meters)/.3:Number(meters))} ${prefs.unit}`;}
  function luminance(hex){
    if(!/^#[\da-f]{6}$/i.test(hex || ''))return null;
    const values=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);
    return .2126*values[0]+.7152*values[1]+.0722*values[2];
  }
  function contrast(a,b){const x=luminance(a),y=luminance(b);return x===null || y===null?0:(Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
  let branding=null;
  function apply(){
    const root=document.documentElement;root.dataset.vttTheme=prefs.theme;root.dataset.vttAccent=prefs.accent;root.dataset.vttStickyPortrait=String(prefs.stickyPortrait);root.lang=language;
    root.style.colorScheme=prefs.theme==='night'?'dark':'light';
    const night=prefs.theme==='night',paper=night?'#211b28':'#f8f3e9';
    const safe={default:night?'#e4c17f':'#713536',bronze:night?'#e4c17f':'#754c19',teal:night?'#96dac8':'#245b50'};
    const candidate=prefs.accent==='default'?(branding?.primary_color || branding?.accent_color):null;
    const accent=candidate && contrast(candidate,paper)>=4.5?candidate:safe[prefs.accent];
    root.style.setProperty('--ui-accent',accent);
    root.style.setProperty('--ui-action-bg',accent);
    root.style.setProperty('--ui-action-text',contrast(accent,'#ffffff')>=contrast(accent,'#19151d')?'#ffffff':'#19151d');
    if(document.body)document.body.dataset.sheetTheme=prefs.theme;
    for(const [id,value] of [['sfTheme',prefs.theme],['sfUnits',prefs.unit]]){const node=document.getElementById(id);if(node)node.value=value;}
    window.SheetFeedback?.applyDisplay?.({...prefs});
    translate();
    window.dispatchEvent(new CustomEvent('vtt:displaychange',{detail:{...prefs}}));
  }
  function update(changes){
    prefs=clean({...prefs,...changes});
    try{
      localStorage.setItem(KEY,JSON.stringify(prefs));
      const previous=JSON.parse(localStorage.getItem('vtt.sheet.display.v1') || '{}');
      localStorage.setItem('vtt.sheet.display.v1',JSON.stringify({...previous,theme:prefs.theme,unit:prefs.unit}));
    }catch(_){}
    apply();return {...prefs};
  }
  function element(tag,label){const node=document.createElement(tag);if(label!==undefined)node.textContent=literal(label);return node;}
  function open(){
    let dialog=document.getElementById('vttDisplayDialog');if(dialog){dialog.showModal();return;}
    dialog=element('dialog');dialog.id='vttDisplayDialog';dialog.className='vtt-display-dialog';dialog.setAttribute('aria-labelledby','vttDisplayTitle');
    const title=element('h2',globalThis.VTTUi("Ansicht und Sprache"));title.id='vttDisplayTitle';dialog.append(title);
    const values={};
    for(const [key,label,options] of [
      ['theme',globalThis.VTTUi("Darstellung"),[['paper',globalThis.VTTUi("Pergament")],['night',globalThis.VTTUi("Nacht")]]],
      ['language',globalThis.VTTUi("Sprache der Oberfläche"),[['de',globalThis.VTTUi("Deutsch")],['en',globalThis.VTTUi("English")]]],
      ['unit',globalThis.VTTUi("Entfernungen"),[['m',globalThis.VTTUi("Meter")],['ft',globalThis.VTTUi("Feet")]]],
      ['accent',globalThis.VTTUi("Sicherer Farbakzent"),[['default',globalThis.VTTUi("Standard")],['bronze',globalThis.VTTUi("Bronze")],['teal',globalThis.VTTUi("Petrol")]]],
    ]){
      const row=element('label',label),select=element('select');select.id='vttDisplay-'+key;
      for(const [value,text] of options){const option=element('option',text);option.value=value;select.append(option);}
      select.value=prefs[key];values[key]=select;row.append(select);dialog.append(row);
    }
    const portrait=element('label'),check=element('input');check.type='checkbox';check.id='vttDisplay-stickyPortrait';check.checked=prefs.stickyPortrait;portrait.append(check,element('span',globalThis.VTTUi("Porträt beim Scrollen sichtbar halten (große Ansichten)")));dialog.append(portrait);
    dialog.append(element('p',globalThis.VTTUi("UI-Sprache und Anzeigeeinheiten ändern keine Regeltexte, Namen oder gespeicherten Spielwerte. Präferenzen gelten in diesem Browser.")));
    const actions=element('div');actions.className='vtt-display-actions';const cancel=element('button',globalThis.VTTUi("Abbrechen"));cancel.type='button';cancel.addEventListener('click',()=>dialog.close());
    const save=element('button',globalThis.VTTUi("Anwenden"));save.type='button';const explain=element('p');explain.setAttribute('role','status');
    const changed=()=>{const reload=values.language.value!==language;save.textContent=literal(reload?globalThis.VTTUi("Anwenden und Seite neu laden"):globalThis.VTTUi("Anwenden"));explain.textContent=literal(reload?globalThis.VTTUi("Für die neue UI-Sprache wird die Seite neu geladen."):globalThis.VTTUi("Darstellung und Entfernungen werden direkt angepasst."));};
    values.language.addEventListener('change',changed);changed();
    save.addEventListener('click',()=>{const reload=values.language.value!==language;update(Object.fromEntries([...Object.entries(values).map(([key,node])=>[key,node.value]),['stickyPortrait',check.checked]]));dialog.close();if(reload)location.reload();});
    actions.append(cancel,save);dialog.append(explain,actions);dialog.addEventListener('close',()=>dialog.remove());document.body.append(dialog);dialog.showModal();
  }
  // These adapters consume only API diagnostics, never rule/user document fields.
  function apiError(body={}){
    const code=body.error || body.code || '';
    const known={forbidden:'Dafür fehlt dir die Berechtigung.',not_found:'Das wurde nicht gefunden.','not found':'Das wurde nicht gefunden.',
      version_conflict:'Der Eintrag wurde inzwischen geändert. Bitte neu laden.','source-changed':'Der Eintrag wurde inzwischen geändert. Bitte neu laden.',
      table_context_required:'Bitte über den Kampagnen-Hub erneut am Tisch Platz nehmen.',table_context_invalid:'Bitte über den Kampagnen-Hub erneut am Tisch Platz nehmen.',
      invalid_scale:'Maßstab: 0,01 bis 1.000.000 Meter pro Feld, höchstens vier Nachkommastellen, oder unkalibriert.',
      request_in_progress:'Die Aktion wird noch verarbeitet. Bitte kurz warten.',action_catalog_changed:'Die verfügbaren Aktionen haben sich geändert. Bitte neu laden.'};
    if(known[code])return literal(known[code]);
    const detail=body.detail || body.message;
    if(detail && (language==='de' || bySource.has(detail)))return literal(detail);
    return literal('Die Anfrage ist fehlgeschlagen. Bitte versuche es erneut.');
  }
  function report(entry,profile){
    if(language==='de')return entry.message;
    const path=String(entry.path || '');
    const messages={edition:'2024 rules.', 'edition-assumed':'No edition specified; using 2024, as in the editor.',
      'edition-2014':'2014 species are not supported. Create a 2024 revision for this character creator.',
      'edition-unknown':'Unknown rules edition. Select 2024.',formula:'Only a fixed numeric value is supported; remove the formula.',
      'out-of-range':'Use a value greater than 0 and at most 1000.',units:'Only feet (ft) or meters (m) are supported.',
      'walk-missing':'Enter a walking speed in Eagle, for example 30 ft.', 'size-missing':'Add a Size advancement in Eagle.',
      'size-invalid':'Select at least one supported size in the Size advancement.', 'creature-type-missing':'Select a creature type in Eagle, for example Humanoid.',
      'skill-options':'Choose at least two distinct skills from the catalog.', 'action-kind':'Only object-telekinesis (move an unattended object) is supported.',
      'action-activation':'Choose action or bonus-action.', 'action-uses':'Only at-will uses are supported.',
      'name-invalid':'Enter a species name with 1 to 100 characters.', 'not-species':'Select an Eagle Species document.',
      'no-darkvision':'No darkvision.',text:'Description is displayed as plain text; it creates no rules.',
      trait:'Displayed as narrative text without automation.', 'senses-note':'Special senses are displayed as text.',
      coins:'Starting equipment: coin package B, 50 gp.',profile:'Typed, immutable revision: '+(profile?.entry?.name || ''),
      grant:'Applied once from this revision.', 'skill-choice':'Proficiency choice converted; the player chooses a skill.'};
    const fields={'type':'Choose a background or feat in Eagle.','name':'Enter a name with 1 to 100 characters.',
      'supplement.abilities':'Choose exactly three distinct abilities.','supplement.skills':'Choose exactly two distinct skills.',
      'supplement.featId':'Choose an accessible published Origin feat.','supplement.toolId':'Choose a catalog tool or leave it empty.',
      'supplement.category':'Choose Origin feat or General feat.','supplement.minLevel':'Origin feat: level 1. General feat: minimum level 4 to 20.',
      'supplement.prerequisite':'Use a known ability and a minimum score from 3 to 20. Origin feats have no additional prerequisite.',
      'effects':'Remove Active Effects; they are not executed.', 'system.description.value':'Use plain description text without inline rolls or Foundry references (maximum 6000 characters).'};
    if(messages[entry.code])return messages[entry.code];
    if(entry.status==='blocked')return fields[path] || 'Unsupported rule or invalid value. Remove it or use the supported VTT controls.';
    return entry.status==='narrative'?'Displayed as narrative text without automation.':entry.status==='ignored'?'Ignored; no rules effect.':'Converted from the source field.';
  }
  function installEagle(){
    const i18n=window.game?.i18n;if(!i18n || i18n.vttDisplayInstalled)return;
    const original=i18n.localize.bind(i18n),format=i18n.format.bind(i18n);
    i18n.localize=key=>messages[key]?t(key):original(key);
    i18n.format=(key,parameters={})=>messages[key]?t(key,parameters):format(key,parameters);
    i18n.lang=language;i18n.vttDisplayInstalled=true;
  }
  window.VTTI18n={t,literal,translate,error:apiError,report,installEagle,locale:()=>language};
  globalThis.VTTUi=(source,parameters={})=>literal(source,parameters);
  globalThis.VTTUiHTML=source=>literal(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  window.VTTDisplay={get:()=>({...prefs}),update,open,formatDistance,number,contrast};
  apply();
  document.addEventListener('DOMContentLoaded',()=>{
    apply();
    new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes)if(node.nodeType===1)translate(node);}).observe(document.body,{childList:true,subtree:true});
    fetch('/api/theme/settings',{credentials:'include'}).then(response=>response.ok?response.json():null).then(data=>{branding=data?.theme || null;apply();}).catch(()=>{});
  });
  window.addEventListener('storage',event=>{if(event.key===KEY){try{prefs=clean(JSON.parse(event.newValue || '{}'));apply();}catch(_){}}});
})();
