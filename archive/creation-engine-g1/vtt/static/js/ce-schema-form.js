/* Explicit, schema-owned inputs for nested homebrew questions. */
(() => {
  'use strict';
  const absent = Symbol('unanswered');
  let identity = 0;
  const strings = {
    en: {choose:'Choose…',add:'Add entry',remove:'Remove',none:'None',addField:'Add a field',yes:'Yes',no:'No',missing:'Complete this field',variant:'Choose a form',empty:'No entries selected',required:'Required',optional:'Optional',entries:'entries'},
    de: {choose:'Auswählen…',add:'Eintrag hinzufügen',remove:'Entfernen',none:'Keine',addField:'Feld hinzufügen',yes:'Ja',no:'Nein',missing:'Dieses Feld ausfüllen',variant:'Form auswählen',empty:'Keine Einträge ausgewählt',required:'Pflichtfeld',optional:'Optional',entries:'Einträge'},
    fr: {choose:'Choisir…',add:'Ajouter une entrée',remove:'Retirer',none:'Aucun',addField:'Ajouter un champ',yes:'Oui',no:'Non',missing:'Complétez ce champ',variant:'Choisir une forme',empty:'Aucune entrée sélectionnée',required:'Obligatoire',optional:'Facultatif',entries:'entrées'}
  };
  const labels = {
    en: {levels:'Levels',level:'Level',hpGain:'Hit points gained',features:'Features',id:'Identifier',name:'Name',description:'Description',grants:'Grants',choices:'Choices',modifiers:'Stat modifiers',proficiencies:'Proficiency keys',resistances:'Resistances',resources:'Resources',spells:'Known spell keys',count:'Count',options:'Options',maximum:'Maximum',recovery:'Recovery',resource:'Resource key',amount:'Amount',kind:'Kind',ability:'Casting ability',saveAbility:'Target save ability',halfOnSave:'Half damage on a successful save',dice:'Dice',sides:'Sides',bonus:'Bonus',damageType:'Damage type',stat:'Stat',dicePerLevel:'Extra dice per spell level',costPerLevel:'Extra cost per spell level',str:'Strength',dex:'Dexterity',con:'Constitution',int:'Intelligence',wis:'Wisdom',cha:'Charisma',ac:'Armour class',speed:'Speed (feet)',hpMax:'Maximum hit points',automatic:'Automatic',attack:'Attack roll',save:'Saving throw',damage:'Damage',healing:'Healing',modifier:'Temporary modifier',short_rest:'Short rest',long_rest:'Long rest',manual:'Manual',action:'Action',bonus_action:'Bonus action',reaction:'Reaction',self:'Self',single:'Single target'},
    de: {levels:'Stufen',level:'Stufe',hpGain:'Gewonnene Trefferpunkte',features:'Merkmale',id:'Kennung',name:'Name',description:'Beschreibung',grants:'Gewährte Regeln',choices:'Auswahlmöglichkeiten',modifiers:'Wertänderungen',proficiencies:'Übungskennungen',resistances:'Resistenzen',resources:'Ressourcen',spells:'Bekannte Zauberkennungen',count:'Anzahl',options:'Optionen',maximum:'Maximum',recovery:'Erholung',resource:'Ressourcenkennung',amount:'Menge',kind:'Art',ability:'Zauberattribut',saveAbility:'Rettungsattribut des Ziels',halfOnSave:'Halber Schaden bei erfolgreichem Rettungswurf',dice:'Würfel',sides:'Seiten',bonus:'Bonus',damageType:'Schadensart',stat:'Wert',dicePerLevel:'Zusatzwürfel pro Zaubergrad',costPerLevel:'Zusatzkosten pro Zaubergrad',str:'Stärke',dex:'Geschicklichkeit',con:'Konstitution',int:'Intelligenz',wis:'Weisheit',cha:'Charisma',ac:'Rüstungsklasse',speed:'Bewegung (Fuß)',hpMax:'Maximale Trefferpunkte',automatic:'Automatisch',attack:'Angriffswurf',save:'Rettungswurf',damage:'Schaden',healing:'Heilung',modifier:'Vorübergehende Wertänderung',short_rest:'Kurze Rast',long_rest:'Lange Rast',manual:'Manuell',action:'Aktion',bonus_action:'Bonusaktion',reaction:'Reaktion',self:'Selbst',single:'Ein Ziel'},
    fr: {levels:'Niveaux',level:'Niveau',hpGain:'Points de vie gagnés',features:'Capacités',id:'Identifiant',name:'Nom',description:'Description',grants:'Règles accordées',choices:'Choix',modifiers:'Modificateurs',proficiencies:'Clés de maîtrise',resistances:'Résistances',resources:'Ressources',spells:'Clés des sorts connus',count:'Nombre',options:'Options',maximum:'Maximum',recovery:'Récupération',resource:'Clé de ressource',amount:'Quantité',kind:'Type',ability:'Caractéristique magique',saveAbility:'Sauvegarde de la cible',halfOnSave:'Demi-dégâts si la sauvegarde réussit',dice:'Dés',sides:'Faces',bonus:'Bonus',damageType:'Type de dégâts',stat:'Valeur',dicePerLevel:'Dés supplémentaires par niveau',costPerLevel:'Coût supplémentaire par niveau',str:'Force',dex:'Dextérité',con:'Constitution',int:'Intelligence',wis:'Sagesse',cha:'Charisme',ac:'Classe d’armure',speed:'Vitesse (pieds)',hpMax:'Points de vie maximum',automatic:'Automatique',attack:'Jet d’attaque',save:'Jet de sauvegarde',damage:'Dégâts',healing:'Soins',modifier:'Modificateur temporaire',short_rest:'Repos court',long_rest:'Repos long',manual:'Manuel',action:'Action',bonus_action:'Action bonus',reaction:'Réaction',self:'Soi-même',single:'Une cible'}
  };
  Object.values(labels).forEach(values=>Object.assign(values,{dnd5e_2014:'D&D 5e (2014)',dnd5e_2024:'D&D 5e (2024)'}));
  function node(tag, text, parent) { const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(parent)parent.append(n);return n; }
  function mount(parent, schema, initial, {locale='en',label='',path=''}={}) {
    const text=strings[locale]||strings.en;
    const name=key=>(labels[locale]||labels.en)[key]||String(key).replace(/([a-z])([A-Z])/g,'$1 $2').replaceAll('_',' ');
    const changed=()=>parent.dispatchEvent(new Event('input',{bubbles:true}));
    function fail(field, title) { const error=new Error(text.missing+': '+title);error.field=field;throw error; }
    function matches(s,v) {
      if('const' in s)return v===s.const;
      if(s.enum)return s.enum.includes(v);
      if(s.type==='null')return v===null;
      if(s.type==='object')return !!v&&typeof v==='object'&&!Array.isArray(v)&&Object.entries(s.properties||{}).every(([k,p])=>!('const' in p)||v[k]===p.const);
      if(s.type==='integer')return Number.isInteger(v);
      return typeof v===s.type;
    }
    function render(host,s,value,title,at) {
      const box=node('div',undefined,host);box.className='ce-schema-node';box.dataset.path=at;
      const button=(caption,action)=>{const b=node('button',caption,box);b.type='button';b.dataset.action=action;return b;};
      const select=(caption)=>{const l=node('label',undefined,box);node('span',caption,l);const n=node('select',undefined,l);n.id='ce-value-'+(++identity);n.dataset.value='';const placeholder=node('option',text.choose,n);placeholder.value='';return n;};
      if('const' in s){node('p',title+': '+name(s.const),box);return ()=>s.const;}
      if(s.oneOf){
        const choose=select(title+' · '+text.variant);choose.required=true;
        s.oneOf.forEach((branch,i)=>{const key=branch.properties?.kind?.const??(branch.type==='null'?text.none:branch.type||String(i+1));const o=node('option',name(key),choose);o.value=String(i);});
        const branches=new Map();
        function show(){
          for(const [i,b] of branches){b.host.hidden=String(i)!==choose.value;if(b.host.hidden)b.host.dataset.ceInactive='';else delete b.host.dataset.ceInactive;}
          if(choose.value!==''&&!branches.has(Number(choose.value))){const i=Number(choose.value),section=node('div',undefined,box);branches.set(i,{host:section,read:render(section,s.oneOf[i],matches(s.oneOf[i],value)?value:undefined,title,at+'/variant'+i)});}
        }
        const selected=value===undefined?-1:s.oneOf.findIndex(branch=>matches(branch,value));choose.value=selected<0?'':String(selected);show();
        choose.onchange=()=>{show();changed();};
        return ()=>{if(choose.value==='')fail(choose,title);return branches.get(Number(choose.value)).read();};
      }
      if(s.type==='null'){node('p',text.none,box);return ()=>null;}
      if(s.type==='object'){
        const heading=node('h4',title,box);heading.tabIndex=-1;
        const fields=node('div',undefined,box),readers=new Map(),properties=s.properties||{},required=new Set(s.required||[]);
        let explicit=value!==undefined;
        function add(key){
          const field=node('div',undefined,fields);field.className='ce-schema-property';
          const read=render(field,properties[key],value?.[key],name(key),at+'/'+key);readers.set(key,{read,field});
          if(!required.has(key)){const remove=node('button',text.remove+' · '+name(key),field);remove.type='button';remove.dataset.action='remove-field';remove.onclick=()=>{field.remove();readers.delete(key);refresh();changed();};}
        }
        Object.keys(properties).filter(key=>required.has(key)||value&&Object.hasOwn(value,key)).forEach(add);
        const optional=Object.keys(properties).filter(key=>!required.has(key));
        let choose,addButton;
        function refresh(){if(!choose)return;const selected=choose.value;choose.replaceChildren();const o=node('option',text.choose,choose);o.value='';optional.filter(k=>!readers.has(k)).forEach(k=>{const o=node('option',name(k),choose);o.value=k;});choose.value=selected;addButton.dataset.unavailable=String(readers.size===Object.keys(properties).length);}
        if(optional.length){choose=select(text.addField);delete choose.dataset.value;choose.dataset.optional='';addButton=button(text.addField,'add-field');addButton.onclick=()=>{if(!choose.value){choose.focus();return;}add(choose.value);explicit=true;refresh();changed();};refresh();}
        if(!required.size){const empty=button(text.none,'none');empty.onclick=()=>{for(const {field} of readers.values())field.remove();readers.clear();explicit=true;refresh();changed();};}
        return ()=>{const result={};for(const [key,{read}] of readers){const v=read();if(v!==absent)result[key]=v;else if(required.has(key))fail(heading,name(key));}if(!Object.keys(result).length&&!explicit)fail(heading,title);return result;};
      }
      if(s.type==='array'){
        const heading=node('h4',title,box);heading.tabIndex=-1;const count=node('p',undefined,box),list=node('div',undefined,box);let rows=[],explicit=Array.isArray(value),serial=0;
        function add(item){const row=node('section',undefined,list);row.className='ce-schema-entry';const caption=node('h5',undefined,row);const read=render(row,s.items,item,title+' '+(rows.length+1),at+'/'+serial++);const remove=node('button',text.remove,row);remove.type='button';remove.dataset.action='remove';const entry={row,caption,read};rows.push(entry);remove.onclick=()=>{rows=rows.filter(x=>x!==entry);row.remove();explicit=true;refresh();changed();};}
        (value||[]).forEach(add);
        const addButton=button(text.add+' · '+title,'add');addButton.onclick=()=>{if(rows.length>=(s.maxItems??Infinity))return;add(undefined);explicit=true;refresh();changed();rows.at(-1).row.querySelector('input,textarea,select,button')?.focus();};
        if(!s.minItems){const empty=button(text.none,'none');empty.onclick=()=>{rows.forEach(r=>r.row.remove());rows=[];explicit=true;refresh();changed();};}
        function refresh(){count.textContent=rows.length?`${rows.length} ${text.entries}`:explicit?text.none:text.empty;rows.forEach((r,i)=>r.caption.textContent=title+' '+(i+1));addButton.dataset.unavailable=String(rows.length>=(s.maxItems??Infinity));}refresh();
        return ()=>{if(!explicit||rows.length<(s.minItems||0))fail(heading,title);return rows.map(r=>{const v=r.read();if(v===absent)fail(r.caption,title);return v;});};
      }
      if(s.enum||s.type==='boolean'){
        const entries=s.enum||[true,false],input=select(title);input.required=true;
        entries.forEach((v,i)=>{const option=node('option',typeof v==='boolean'?(v?text.yes:text.no):name(v),input);option.value=String(i);});
        input.value=value===undefined?'':String(entries.indexOf(value));
        return ()=>input.value===''?absent:entries[Number(input.value)];
      }
      const label=node('label',undefined,box);node('span',title,label);
      const input=node(s.type==='string'&&(s.maxLength||0)>200?'textarea':'input',undefined,label);input.dataset.value='';input.id='ce-value-'+(++identity);
      if(input.tagName==='INPUT')input.type=s.type==='integer'?'number':'text';
      input.required=s.type==='integer'||Boolean(s.minLength||s.pattern);
      if(s.type==='integer'){input.step='1';if(s.minimum!==undefined)input.min=s.minimum;if(s.maximum!==undefined)input.max=s.maximum;}
      if(s.maxLength)input.maxLength=s.maxLength;if(s.minLength)input.minLength=s.minLength;
      if(s.pattern)input.dataset.pattern=s.pattern;
      if(value!==undefined)input.value=String(value);
      return ()=>{if(input.value===''){if(s.type==='string'&&!s.minLength&&!s.pattern)return '';return absent;}if(s.type==='integer'){const n=Number(input.value);if(!Number.isSafeInteger(n))fail(input,title);return n;}if(s.pattern&&!new RegExp(s.pattern).test(input.value))fail(input,title);return input.value;};
    }
    const read=render(parent,schema,initial,label,path);
    return ()=>{const value=read();if(value===absent)fail(parent.querySelector('[data-value]'),label);return value;};
  }
  function preview(parent,value,locale='en') {
    const names=labels[locale]||labels.en,words=strings[locale]||strings.en;
    if(value===null){node('span',words.none,parent);return;}
    if(typeof value!=='object'){node('span',typeof value==='boolean'?(value?words.yes:words.no):names[value]||String(value),parent);return;}
    if(!Object.keys(value).length){node('span',words.none,parent);return;}
    const list=node(Array.isArray(value)?'ol':'dl',undefined,parent);
    Object.entries(value).forEach(([key,v])=>{if(Array.isArray(value))preview(node('li',undefined,list),v,locale);else{node('dt',names[key]||key,list);preview(node('dd',undefined,list),v,locale);}});
  }
  window.CESchemaForm={mount,preview};
})();
