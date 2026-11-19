/* Loaded only with the server-authorized DM composition. */
(() => {
    const el=(tag,text)=>{const node=document.createElement(tag);if(text)node.textContent=text;return node;};
    const button=(text,fn)=>{const node=el('button',text);node.type='button';node.onclick=fn;return node;};
    window.PlayFloorDM=class {
        constructor(ui){
            this.ui=ui;this.base=`/api/play/campaigns/${ui.campaignId}/sessions/${ui.sessionId}/maps/`;
            this.root=el('section');this.root.className='play-floor-editor';
            this.controls=el('fieldset');this.controls.append(el('legend','Private Etagenbilder und Balkonsicht'));
            this.help=el('p');this.help.id='floorLimitation';
            this.status=el('p');this.status.setAttribute('role','status');this.status.id='floorEditorStatus';
            this.enabled=el('input');this.enabled.type='checkbox';this.enabled.id='floorEnabled';
            this.active=el('select');this.active.id='activeFloor';
            const apply=button('Etagenansicht anwenden',()=>this.mutate('', 'PUT',{enabled:this.enabled.checked,active_floor_id:this.active.value?Number(this.active.value):null}));apply.id='applyFloorDeck';
            this.name=el('input');this.name.id='newFloorName';this.name.maxLength=80;this.name.placeholder='z. B. Erdgeschoss';
            this.file=el('input');this.file.id='newFloorFile';this.file.type='file';this.file.accept='image/png';
            this.uploadButton=button('PNG als private Etage hochladen',()=>this.upload());this.uploadButton.id='uploadFloor';
            this.dimensions=el('p');this.list=el('div');this.list.id='floorList';
            this.controls.append(this.help,this.label('Etagenbilder aktivieren',this.enabled),this.label('Aktive Etage',this.active),apply,
                el('h4','Etage hinzufügen'),this.dimensions,this.label('Name',this.name),this.label('PNG-Datei',this.file),this.uploadButton,
                el('h4','Reihenfolge: unten nach oben'),this.list,button('Aktuellen Stand laden',()=>this.load()));
            this.root.append(this.controls,this.status);ui.windows.add('mapFloors','Etagen und Balkonsicht',this.root);
            const trigger=button('Etagen und Balkonsicht',()=>{this.refresh();this.load();ui.windows.toggle('mapFloors');});trigger.id='btnMapFloors';
            ui.feedbackDM.root.append(trigger);ui.windows.items.get('mapFloors').trigger=trigger;this.refresh();
        }
        label(text,input){const label=el('label',text);label.append(input);return label;}
        refresh(){const id=this.ui.bootstrap?.state_payload?.active_map?.id;if(id!==this.mapId){this.mapId=id;this.config=null;this.list.replaceChildren();this.controls.disabled=true;if(id)this.load();}}
        path(suffix=''){return `${this.base}${this.mapId}/floors${suffix}`;}
        async load(){
            const id=this.mapId,sequence=this.sequence=(this.sequence||0)+1;
            try{const data=await Auth.makeAuthRequest(this.path());if(sequence!==this.sequence||id!==this.mapId)return;this.render(data);}
            catch(error){if(id===this.mapId)this.status.textContent=error.message;}
        }
        render(data){
            this.config=data;this.controls.disabled=Boolean(this.ui.readOnly);this.help.textContent=data.limitation;
            this.dimensions.textContent=`PNG: genau ${data.width} × ${data.height} Pixel, höchstens 4 MiB. Maximal 8 Etagen und 16 MiB je Karte. Transparenz und rechteckige Öffnungen zeigen tiefere Bilder nur bei aktivierter Balkonsicht.`;
            this.enabled.checked=data.enabled;this.active.replaceChildren(new Option('Etage wählen',''));
            for(const floor of data.floors)this.active.append(new Option(floor.name,String(floor.id)));
            this.active.value=data.active_floor_id??'';this.list.replaceChildren();
            data.floors.forEach((floor,index)=>{
                const card=el('section');card.className='floor-card';card.dataset.floorId=floor.id;
                const title=el('input');title.value=floor.name;title.maxLength=80;title.setAttribute('aria-label','Etagenname');
                const reveal=el('input');reveal.type='checkbox';reveal.checked=floor.reveal_below;
                const openings=el('div');openings.className='floor-openings';
                const addRect=(rect={x:0,y:0,width:1,height:1})=>{
                    if(openings.children.length>=32)return;
                    const row=el('div');row.className='floor-opening';
                    for(const [key,label]of [['x','X'],['y','Y'],['width','Breite'],['height','Höhe']]){const input=el('input');input.type='number';input.step=1;input.min=key==='width'||key==='height'?1:0;input.max=key==='x'||key==='width'?data.width:data.height;input.value=rect[key];input.dataset.rectKey=key;row.append(this.label(label,input));}
                    row.append(button('Öffnung entfernen',()=>row.remove()));openings.append(row);
                };
                for(const rect of floor.openings)addRect(rect);
                const move=(direction)=>{const ids=data.floors.map(item=>item.id);[ids[index],ids[index+direction]]=[ids[index+direction],ids[index]];this.mutate('','PUT',{floor_ids:ids});};
                const down=button('↓ Tiefer',()=>move(-1));down.disabled=index===0;
                const up=button('↑ Höher',()=>move(1));up.disabled=index===data.floors.length-1;
                const save=button('Etage speichern',()=>{
                    const rects=[...openings.children].map(row=>Object.fromEntries([...row.querySelectorAll('input')].map(input=>[input.dataset.rectKey,Number(input.value)])));
                    this.mutate(`/${floor.id}`,'PUT',{name:title.value,reveal_below:reveal.checked,openings:rects});
                });
                const remove=button('Etage löschen',()=>{if(confirm(`Private Etage „${floor.name}“ löschen?`))this.mutate(`/${floor.id}`,'DELETE',{});});
                card.append(this.label('Name',title),this.label('Balkonsicht: darunterliegende Etagen durch Öffnungen sehen',reveal),down,up,
                    el('p','Öffnungen in Kartenpixeln; X/Y ab der linken oberen Ecke.'),openings,button('Rechteckige Öffnung hinzufügen',()=>addRect()),save,remove);this.list.append(card);
            });
        }
        async mutate(suffix,method,payload){
            if(this.busy||this.ui.readOnly||!this.config)return;
            this.busy=true;this.controls.disabled=true;const id=this.mapId;
            try{const data=await Auth.makeAuthRequest(this.path(suffix),method,{revision:this.config.revision,...payload});if(id===this.mapId){this.render(data);this.status.textContent='Etagen gespeichert.';}this.ui.floorView?.refresh(true);}
            catch(error){if(id===this.mapId){this.status.textContent=error.message;await this.load();}}
            finally{this.busy=false;if(id===this.mapId)this.controls.disabled=Boolean(this.ui.readOnly);}
        }
        async upload(){
            if(this.busy||this.ui.readOnly||!this.config||!this.file.files[0])return;
            const file=this.file.files[0];if(file.size>4*1024*1024){this.status.textContent='PNG darf höchstens 4 MiB groß sein.';return;}
            // Retain the ID for an identical retry after a lost HTTP response.
            const inputKey=JSON.stringify([this.mapId,this.name.value,file.name,file.size,file.lastModified]);
            if(inputKey!==this.uploadKey){this.uploadKey=inputKey;this.requestId=crypto.randomUUID();}
            const form=new FormData();form.set('revision',this.config.revision);form.set('request_id',this.requestId);form.set('name',this.name.value);form.set('file',file);
            this.busy=true;this.controls.disabled=true;const id=this.mapId;
            try{
                const send=()=>fetch(this.path(),{method:'POST',credentials:'include',headers:Auth.buildHeaders('POST',false),body:form});
                let response=await send();if(response.status===401&&await Auth.refreshAccessToken())response=await send();
                const data=await response.json();if(!response.ok)throw new Error(data.error||'PNG konnte nicht hochgeladen werden.');
                if(id===this.mapId){this.render(data);this.file.value='';this.name.value='';this.uploadKey=null;this.status.textContent='Private Etage hochgeladen. Aktivierung und Reihenfolge prüfen.';}
                this.ui.floorView?.refresh(true);
            }catch(error){if(id===this.mapId){this.status.textContent=error.message;await this.load();}}
            finally{this.busy=false;if(id===this.mapId)this.controls.disabled=Boolean(this.ui.readOnly);}
        }
    };
})();
