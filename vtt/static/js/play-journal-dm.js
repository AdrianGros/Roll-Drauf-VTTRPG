// Loaded only by the independently authorized DM composition.
import { node } from './play-journal.js';
const t=source=>globalThis.VTTUi(source);
async function write(path,method,body) {
    const form=body instanceof FormData;
    const response=await fetch(path,{method,credentials:'include',headers:Auth.buildHeaders(method,!form),body:body===undefined?undefined:form?body:JSON.stringify(body)});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.error||t('Die Änderung konnte nicht gespeichert werden.'));
    return data;
}
export function mount(journal) {
    if(journal.managementBound)return;journal.managementBound=true;
    const file=node('input',{id:'journalUploadFile',type:'file',accept:'image/png,image/jpeg,image/webp,image/gif,application/pdf,text/plain','aria-label':t('Datei auswählen')});
    const type=node('select',{id:'journalUploadType','aria-label':t('Dateityp')});
    for(const [value,label] of [['handout','Handout'],['image','Bild'],['map','Karte'],['token','Token']])type.append(node('option',{value,text:t(label)}));
    const scope=node('select',{id:'journalUploadScope','aria-label':t('Dateibereich')});
    for(const [value,label] of [['session','Diese Sitzung'],['campaign','Kampagne']])scope.append(node('option',{value,text:t(label)}));
    const upload=node('button',{id:'journalUpload',type:'button',text:t('Hochladen')});
    const details=node('details',{id:'journalManageFiles'},node('summary',{text:t('Dateien verwalten')}),node('p',{text:t('Karten, Tokens und Bilder sind für die Gruppe sichtbar. Handouts bleiben bis zur Freigabe verborgen.')}),file,type,scope,upload);
    journal.management.append(details);
    upload.onclick=async()=>{
        const selected=file.files?.[0];if(!selected){journal.setStatus(t('Bitte zuerst eine Datei auswählen.'),true);return;}
        if(selected.size>50*1024*1024){journal.setStatus(t('Datei ist zu groß. Maximum sind 50 MB.'),true);return;}
        upload.disabled=true;
        try {
            const form=new FormData();form.append('file',selected);form.append('asset_type',type.value);
            if(scope.value==='session')form.append('session_id',String(journal.ui.sessionId));
            await write(`/api/assets/campaigns/${journal.ui.campaignId}/upload`,'POST',form);
            file.value='';await journal.refresh();
        } catch(error){journal.setStatus(error.message,true);}
        finally{upload.disabled=false;}
    };
    journal.decorate=(asset,row)=>{
        const name=node('input',{value:asset.filename,maxLength:255,'aria-label':t('Dateibezeichnung')});name.dataset.journalRename='';
        const save=node('button',{type:'button',text:t('Bezeichnung speichern')});save.dataset.journalSave='';
        const remove=node('button',{type:'button',text:t('Löschen')});remove.dataset.journalDelete='';
        const actions=node('div',{className:'button-row'},save);
        const edit=node('details',{},node('summary',{text:t('Bearbeiten')}),name,actions);
        const run=async(button,path,method,body)=>{
            button.disabled=true;
            try{await write(path,method,body);await journal.refresh();}
            catch(error){journal.setStatus(error.message,true);button.disabled=false;}
        };
        save.onclick=()=>run(save,`/api/assets/${asset.id}/metadata`,'PATCH',{filename:name.value});
        if(asset.asset_type==='handout') {
            const reveal=node('button',{type:'button',text:t(asset.is_public?'Vor Spielern verbergen':'Für Spieler freigeben')});reveal.dataset.journalReveal='';
            reveal.onclick=()=>run(reveal,`/api/assets/${asset.id}/visibility`,'PATCH',{is_public:!asset.is_public});actions.append(reveal);
        }
        remove.onclick=()=>{if(window.confirm(t('Diese Datei aus der Bibliothek entfernen?')))run(remove,`/api/assets/${asset.id}/delete`,'DELETE');};
        actions.append(remove);row.append(edit);
    };
}
