// Shared read-only Journal surface. DM management is composed independently.
const uiText = source => globalThis.VTTUi(source);
export function node(tag, props = {}, ...children) {
    const result = document.createElement(tag);
    for (const [key,value] of Object.entries(props)) {
        if (key === 'text') result.textContent = value;
        else if (key in result) result[key] = value;
        else result.setAttribute(key,value);
    }
    result.append(...children);return result;
}
function options(select, entries) {
    for (const [value,label] of entries) select.append(node('option',{value,text:uiText(label)}));
}
export class JournalAssets {
    constructor(ui) {
        this.ui = ui;this.page = 1;this.sequence = 0;
        this.panel = node('section',{id:'journalFilesPanel',className:'panel journal-files'});
        this.search = node('input',{id:'journalAssetSearch',type:'search',maxLength:80,'aria-label':uiText('Dateien durchsuchen')});
        this.type = node('select',{id:'journalAssetType','aria-label':uiText('Dateityp')});
        options(this.type,[['','Alle Typen'],['map','Karten'],['token','Tokens'],['handout','Handouts'],['image','Bilder']]);
        this.scope = node('select',{id:'journalAssetScope','aria-label':uiText('Dateibereich')});
        options(this.scope,[['current','Kampagne und diese Sitzung'],['campaign','Kampagne'],['session','Diese Sitzung']]);
        this.refreshButton = node('button',{id:'journalAssetsRefresh',type:'button',text:uiText('Aktualisieren')});
        this.tokens = node('button',{id:'journalTokens',type:'button',text:uiText('Tokens öffnen')});
        this.status = node('p',{id:'journalAssetsStatus',role:'status','aria-live':'polite'});
        this.list = node('ul',{id:'journalAssetsList',className:'journal-assets'});
        this.previous = node('button',{id:'journalAssetsPrev',type:'button',text:uiText('Zurück')});
        this.next = node('button',{id:'journalAssetsNext',type:'button',text:uiText('Weiter')});
        this.pageLabel = node('span',{});
        this.management = node('div',{id:'journalManagementSlot'});
        this.panel.append(node('h2',{text:uiText('Dateien und Assets')}),node('div',{className:'journal-file-filters'},this.search,this.type,this.scope,this.refreshButton,this.tokens),this.management,this.status,this.list,node('div',{className:'button-row'},this.previous,this.pageLabel,this.next));
        document.getElementById('panel-journal').prepend(this.panel);
        this.search.oninput = () => {clearTimeout(this.timer);this.timer=setTimeout(()=>{this.page=1;this.refresh();},250);};
        for (const field of [this.type,this.scope]) field.onchange = () => {this.page=1;this.refresh();};
        this.refreshButton.onclick = () => this.refresh();
        this.previous.onclick = () => {this.page--;this.refresh();};this.next.onclick = () => {this.page++;this.refresh();};
        this.tokens.onclick = () => {
            document.querySelector('.right-sidebar')?.classList.remove('is-open');document.getElementById('btnSidebarToggle')?.setAttribute('aria-expanded','false');
            ui._revealTokenWidget();
        };
        document.getElementById('btnSidebarToggle').addEventListener('click',()=>this.refresh());
        document.querySelector('[data-tab=journal]')?.addEventListener('click',()=>this.refresh());
        this.preview = node('dialog',{id:'journalAssetPreview',className:'map-library-dialog'});
        this.previewTitle = node('h2',{});this.previewImage = node('img',{alt:''});
        const close = node('button',{type:'button',text:uiText('Schließen')});close.onclick=()=>this.preview.close();
        this.preview.append(this.previewTitle,this.previewImage,close);document.body.append(this.preview);
        this.preview.addEventListener('close',()=>this.previewImage.removeAttribute('src'));
    }
    setStatus(message,error=false) {this.status.textContent=message;this.status.classList.toggle('error',error);}
    async read(path, binary=false, retry=true, signal) {
        const context = window.VTTTableContext?.token;
        // Table media always carries the active seat; never fall back to cookie-only authority.
        if (!context) throw new Error(uiText('Der Tischkontext hat sich geändert. Bitte erneut laden.'));
        let response = await fetch(path,{credentials:'include',headers:Auth.buildHeaders('GET',false),cache:'no-store',signal});
        if (response.status===401 && retry && await Auth.refreshAccessToken?.()) return this.read(path,binary,false,signal);
        if (context !== window.VTTTableContext?.token) {
            // The seat's context was renewed mid-request (e.g. on socket resume): read once more under it.
            if (retry && window.VTTTableContext?.token) return this.read(path,binary,false,signal);
            throw new Error(uiText('Der Tischkontext hat sich geändert. Bitte erneut laden.'));
        }
        if (!response.ok) throw new Error(uiText('Die Datei ist nicht verfügbar oder nicht freigegeben.'));
        return binary ? response.blob() : response.json();
    }
    async refresh() {
        const sequence = ++this.sequence;this.controller?.abort();this.controller=new AbortController();
        this.setStatus(uiText('Dateien werden geladen …'));
        const query = new URLSearchParams({page:String(this.page),per_page:'24',scope:this.scope.value,query:this.search.value});
        if (this.scope.value !== 'campaign') query.set('session_id',String(this.ui.sessionId));
        if (this.type.value) query.set('asset_type',this.type.value);
        try {
            const data=await this.read(`/api/assets/campaigns/${this.ui.campaignId}/library?${query}`,false,true,this.controller.signal);
            if (sequence!==this.sequence) return;
            this.list.replaceChildren();
            for (const asset of data.assets) this.list.append(this.card(asset,sequence));
            this.previous.disabled=data.page<=1;this.next.disabled=!data.has_more;
            this.pageLabel.textContent=globalThis.VTTUi('Seite {p0} von {p1}',{p0:data.page,p1:Math.max(1,Math.ceil(data.total/data.per_page))});
            this.setStatus(data.assets.length?'':uiText('Keine freigegebenen Dateien in diesem Bereich.'));
        } catch (error) {
            if (sequence===this.sequence && error.name!=='AbortError') {this.list.replaceChildren();this.setStatus(error.message,true);}
        }
    }
    card(asset,sequence) {
        const row=node('li',{className:'journal-asset'});row.dataset.assetId=String(asset.id);
        const title=node('strong',{text:asset.filename});const meta=node('p',{className:'muted',text:uiText(asset.session_id?'Diese Sitzung':'Kampagne')});
        const actions=node('div',{className:'button-row'});
        const download=node('button',{type:'button',text:uiText('Herunterladen')});
        download.onclick=async()=>{
            try {
                const blob=await this.read(`/api/assets/${asset.id}/download`,true);
                if(sequence!==this.sequence)return;
                const url=URL.createObjectURL(blob),link=node('a',{href:url,download:asset.filename});document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
            } catch(error){this.setStatus(error.message,true);}
        };
        if (asset.previewable && asset.mime_type.startsWith('image/')) {
            const preview=node('button',{type:'button',text:uiText('Vorschau')});
            preview.onclick=async()=>{
                try {
                    const blob=await this.read(`/api/assets/${asset.id}/preview`,true);
                    const source=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(blob);});
                    if(sequence!==this.sequence)return;
                    this.previewTitle.textContent=asset.filename;this.previewImage.src=source;this.previewImage.alt=asset.filename;this.preview.showModal();
                } catch(error){this.setStatus(error.message,true);}
            };actions.append(preview);
        }
        actions.append(download);row.append(title,meta,actions);
        if(asset.thumbnail_url) {
            const image=node('img',{className:'journal-asset-thumb',alt:'',hidden:true});row.prepend(image);
            this.read(`/api/assets/${asset.id}/thumbnail`,true,true,this.controller.signal).then(blob=>new Promise((resolve,reject)=>{
                const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(blob);
            })).then(source=>{if(sequence===this.sequence && row.isConnected){image.src=source;image.hidden=false;}}).catch(()=>{});
        }
        this.decorate?.(asset,row);
        return row;
    }
}
export async function mount(ui) {
    ui._journalAssets ||= new JournalAssets(ui);
    await ui._bindJournalManagement?.(ui._journalAssets);
    await ui._journalAssets.refresh();
    return ui._journalAssets;
}
