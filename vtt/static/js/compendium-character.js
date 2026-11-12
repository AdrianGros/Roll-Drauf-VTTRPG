/* Typed, owner-scoped catalog actions. Rule source text and character names stay literal. */
const ui=(source,parameters)=>globalThis.VTTUi(source,parameters||{});
const make=(tag,parent,text,attrs={})=>{
    const node=document.createElement(tag);if(text!==null)node.textContent=text;
    for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);
    parent.append(node);return node;
};

export function mountCatalogAction(root,entity) {
    const button=make('button',root,ui('Zum Charakter'),{type:'button',class:'btn btn-secondary',id:'cpCharacterOpen'});
    const dialog=make('dialog',document.body,null,{class:'cp-character-dialog',id:'cpCharacterDialog','aria-labelledby':'cpCharacterTitle'});
    make('h2',dialog,ui('Zum Charakter'),{id:'cpCharacterTitle'});
    make('p',dialog,entity.name);
    const form=make('form',dialog,null),filters=make('div',form,null,{class:'cp-character-fields'});
    const search=make('input',make('label',filters,ui('Eigene Figur suchen')),null,{type:'search',maxlength:100,id:'cpCharacterSearch'});
    const campaign=make('select',make('label',filters,ui('Kampagne')),null,{id:'cpCharacterCampaign','aria-label':ui('Kampagne')});
    campaign.add(new Option(ui('Alle Kampagnen'),''));
    const target=make('select',make('label',filters,ui('Eigener Charakter')),null,{id:'cpCharacterTarget','aria-label':ui('Eigener Charakter'),required:''});
    const more=make('button',filters,ui('Weitere Charaktere'),{type:'button',class:'btn btn-secondary',id:'cpCharacterMore',hidden:''});
    const quantityLabel=make('label',form,ui('Menge'));
    const quantity=make('input',quantityLabel,null,{type:'number',min:1,step:1,value:1,required:'',id:'cpCharacterQuantity'});
    const explanation=make('p',form,'',{class:'cp-character-help',id:'cpCharacterHint'});
    const progress=make('a',form,ui('Fortschritt im Bogen öffnen'),{class:'btn btn-secondary',id:'cpCharacterProgression',hidden:''});
    const status=make('p',dialog,'',{role:'status','aria-live':'polite',id:'cpCharacterStatus'});
    const receipt=make('div',dialog,null,{id:'cpCharacterReceipt'});
    const actions=make('div',form,null,{class:'cp-character-actions'});
    const add=make('button',actions,ui('Zum Inventar hinzufügen'),{type:'submit',class:'btn btn-primary',id:'cpCharacterAdd',disabled:''});
    const close=make('button',actions,ui('Schließen'),{type:'button',class:'btn btn-secondary',id:'cpCharacterClose'});
    let version=0,queryVersion=0,characters=new Map(),cursor=null,supported=false,pending=null,busy=false,loading=false,searchTimer;
    const isProgression=['spell','feat','class','subclass'].includes(entity.type);
    const valid=v=>v===version&&root.isConnected&&dialog.open;
    function controls() {
        const selected=characters.get(Number(target.value));
        for(const field of [search,campaign,target,quantity,more])field.disabled=busy||Boolean(pending);
        more.disabled=busy||Boolean(pending)||loading;
        quantityLabel.hidden=!supported;add.hidden=!supported;add.disabled=busy||loading||!selected;
        add.textContent=pending?ui('Erneut versuchen'):ui('Zum Inventar hinzufügen');
        progress.hidden=!selected||(!supported&&!isProgression);
        if(selected)progress.href=`/character-sheet?id=${selected.id}&section=progression`;
        explanation.textContent=!supported
            ? isProgression?ui('Zauber, Talente und Klassen werden über die geprüften Entscheidungen im Bogen gewählt.'):ui('Dieser Eintrag wird nicht als Inventargegenstand unterstützt.')
            :ui('Der Gegenstand wird mit seinen Regelwerten übernommen. Er wird nicht automatisch angelegt oder gekauft.');
        if(selected?.progression?.canLevelUp)explanation.textContent+=' '+ui('Stufenaufstieg verfügbar: {level} → {target}.',{level:selected.progression.level,target:selected.progression.targetLevel});
    }
    async function load(append=false) {
        if(pending||busy)return;
        loading=true;controls();
        const v=version,qv=++queryVersion;
        const query=new URLSearchParams({entity_id:entity.id,q:search.value.trim()});
        if(campaign.value)query.set('campaign_id',campaign.value);
        if(append&&cursor)query.set('after',cursor);
        status.textContent=ui('Eigene Charaktere werden geladen …');
        try {
            const data=await window.Auth.makeAuthRequest('/api/srd-creator/catalog-targets?'+query);
            if(!valid(v)||qv!==queryVersion||!data)return;
            const previous=target.value;
            if(!append)characters.clear();
            for(const char of data.characters)characters.set(char.id,char);
            target.replaceChildren(new Option(ui('Charakter auswählen'),''));
            for(const char of characters.values())target.add(new Option(char.name+(char.campaign_id?' · '+(char.campaign_name||ui('Frühere Kampagne')):''),String(char.id)));
            target.value=characters.has(Number(previous))?previous:'';
            const selectedCampaign=campaign.value;
            campaign.replaceChildren(new Option(ui('Alle Kampagnen'),''),...data.campaigns.map(c=>new Option(c.name||ui('Frühere Kampagne'),String(c.id))));
            campaign.value=selectedCampaign;cursor=data.next_cursor;more.hidden=!cursor;supported=Boolean(data.item);
            quantity.max=String(data.quantity_limit);
            status.textContent=characters.size?'':cursor?ui('Weitere Charaktere laden, um passende Figuren zu finden.'):ui('Keine passenden eigenen SRD-Charaktere gefunden.');
            controls();
        } catch(error) {if(valid(v)&&qv===queryVersion)status.textContent=error.message||ui('Charaktere konnten nicht geladen werden.');}
        finally {if(valid(v)&&qv===queryVersion){loading=false;controls();}}
    }
    button.onclick=async()=>{
        const user=await window.Auth.requireAuth('/login.html');if(!user)return;
        version++;queryVersion++;pending=null;busy=false;loading=false;characters.clear();target.replaceChildren();campaign.replaceChildren(new Option(ui('Alle Kampagnen'),''));search.value='';cursor=null;more.hidden=true;receipt.replaceChildren();dialog.showModal();controls();await load();search.focus();
    };
    close.onclick=()=>dialog.close();
    dialog.addEventListener('close',()=>{version++;queryVersion++;pending=null;busy=false;clearTimeout(searchTimer);});
    search.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();clearTimeout(searchTimer);load();}};
    const invalidateFilter=()=>{queryVersion++;cursor=null;more.hidden=true;characters.clear();target.replaceChildren();loading=true;controls();};
    search.oninput=()=>{invalidateFilter();clearTimeout(searchTimer);searchTimer=setTimeout(()=>load(),250);};
    campaign.onchange=()=>{invalidateFilter();load();};more.onclick=()=>load(true);target.onchange=controls;
    form.onsubmit=async event=>{
        event.preventDefault();if(busy||loading||!supported)return;
        clearTimeout(searchTimer);queryVersion++;
        const char=characters.get(Number(target.value));if(!char)return;
        if(!pending)pending={character:char.id,body:{entity_id:entity.id,quantity:quantity.valueAsNumber,request_id:crypto.randomUUID()}};
        const action=pending,v=version;busy=true;controls();status.textContent=ui('Übernahme wird gespeichert …');
        try {
            const data=await window.Auth.makeAuthRequest(`/api/srd-creator/characters/${action.character}/catalog-add`,'POST',action.body);
            if(!valid(v)||!data)return;
            const confirmed=data.receipt;
            if(confirmed?.id!==action.body.request_id||confirmed.character_id!==action.character)throw new Error(ui('Die Bestätigung passt nicht zur gewählten Figur. Bitte erneut versuchen.'));
            receipt.replaceChildren();make('p',receipt,ui('{quantity} × {item} für {character} gespeichert.',{quantity:confirmed.quantity,item:confirmed.entity_name,character:confirmed.character_name}));
            make('a',receipt,ui('Inventar im Bogen öffnen'),{class:'btn btn-secondary',href:`/character-sheet?id=${confirmed.character_id}&section=inventory`,id:'cpCharacterSheet'});
            status.textContent=data.table_refresh==='pending'?ui('Gespeichert. Der Tisch konnte nicht aktualisiert werden; lade ihn bei Bedarf neu.'):ui('Übernahme bestätigt.');
            pending=null;
        } catch(error) {
            if(valid(v))status.textContent=(error.message?error.message+' ':'')+ui('Erneut versuchen verwendet dieselbe Übernahme.');
        } finally {if(valid(v)){busy=false;controls();}}
    };
    const hide=()=>{version++;queryVersion++;pending=null;busy=false;characters.clear();target.replaceChildren();receipt.replaceChildren();if(dialog.open)dialog.close();};
    window.addEventListener('pagehide',hide);
    return ()=>{window.removeEventListener('pagehide',hide);version++;queryVersion++;clearTimeout(searchTimer);if(dialog.open)dialog.close();dialog.remove();root.replaceChildren();};
}
