/* Loaded and initialized exclusively after a server-authorized DM composition. */
(() => {
    const text=(de,en)=>document.documentElement.lang.startsWith('en')?en:de;
    const el=(tag,value)=>{const node=document.createElement(tag);if(value)node.textContent=value;return node;};
    const button=(label,action)=>{const node=el('button',label);node.type='button';node.onclick=action;return node;};
    window.PlayFeedbackDM=class {
        constructor(ui){
            this.ui=ui;this.path=ui.feedback.path;
            // Geometry editors share the floating-window layer. Inside the
            // stage's stacking context they would sit below this manager.
            for(const id of ['wallEditPopover','lightEditPopover']){
                const popover=document.getElementById(id);if(!popover)continue;
                document.body.append(popover);ui.windows.native(popover,'.button-row');
            }
            this.root=el('section');this.root.className='play-feedback-form';
            this.grid=el('input');this.grid.type='number';this.grid.min=16;this.grid.max=300;this.grid.id='presentationGridSize';
            this.visible=this.checkbox('presentationGridVisible');this.dynamic=this.checkbox('presentationDynamicLight');this.fog=this.checkbox('presentationFog');
            this.ambient=el('input');this.ambient.id='presentationAmbient';this.ambient.type='number';this.ambient.min=0;this.ambient.max=100;
            this.root.append(this.label(text('Rastergröße (Pixel)','Grid size (pixels)'),this.grid),this.label(text('Raster anzeigen','Show grid'),this.visible),
                this.label(text('Dynamisches Licht','Dynamic lighting'),this.dynamic),this.label(text('Aufklärung speichern','Remember explored areas'),this.fog),
                this.label(text('Umgebungslicht (%)','Ambient light (%)'),this.ambient));
            this.status=el('p');this.status.setAttribute('role','status');
            this.save=button(text('Karteneinstellungen speichern','Save map settings'),()=>this.saveSettings());this.save.id='savePresentationSettings';
            this.preview=el('select');this.preview.id='previewPerspectiveToken';this.preview.append(new Option(text('DM · gesamte Karte','DM · full map'),''));
            this.preview.onchange=()=>{if(this.preview.value&&!ui.feedback.previewToken)ui.feedback.markerHiddenBeforePreview=document.getElementById("visionLayer").hidden;ui.feedback.previewToken=this.preview.value?Number(this.preview.value):null;this.previewStatus.textContent=this.preview.value?text('Spielerperspektive · nur Vorschau','Player perspective · preview only'):text('DM · gesamte Karte','DM · full map');
                document.getElementById('visionLayer').hidden=this.preview.value?true:Boolean(ui.feedback.markerHiddenBeforePreview);ui.feedback.sequence=(ui.feedback.sequence||0)+1;if(this.preview.value)ui.feedback.cover(ui.bootstrap.state_payload.active_map);ui.feedback.scheduleLighting();};
            this.previewStatus=el('p');this.previewStatus.id='previewPerspectiveStatus';
            this.geometry=el('ul');this.geometry.className='play-feedback-list';this.geometry.id='geometryManager';
            const create=el('div');create.append(button(text('Wand zeichnen','Draw wall'),()=>{ui._setTool('wall');ui.windows.close('mapPresentation');}),button(text('Licht setzen','Place light'),()=>{ui._setTool('light');ui.windows.close('mapPresentation');}));
            this.root.append(this.save,this.status,this.label(text('Perspektive','Perspective'),this.preview),this.previewStatus,el('h4',text('Wände und Lichter bearbeiten','Edit walls and lights')),create,this.geometry);
            ui.windows.add('mapPresentation',text('Raster, Licht und Wände','Grid, light and walls'),this.root);
            const trigger=button(text('Raster & Licht','Grid & light'),()=>{this.refresh(true);ui.windows.toggle('mapPresentation');});trigger.id='btnMapPresentation';trigger.className='tool-btn';
            document.querySelector('.table-dock-tabs').append(trigger);ui.windows.items.get('mapPresentation').trigger=trigger;
            const toggle=document.getElementById('btnVisionToggle');if(toggle){toggle.title=text('Wand- und Lichtmarkierungen ein-/ausblenden','Show/hide wall and light markers');const label=toggle.querySelector('.tool-label');if(label){label.removeAttribute('data-ui-key');label.textContent=text('Markierungen','Markers');}}
            this.candidates=el('ul');this.candidates.className='play-feedback-list';this.candidates.id='initiativeCandidates';
            this.reset=button(text('Neue Initiative-Runde','New initiative round'),async()=>{if(!confirm(text('Alle Initiativewerte zurücksetzen und eine neue Sammelrunde beginnen?','Clear all initiative values and begin a new collection round?')))return;
                await this.action('/initiative-candidates/reset',{revision:ui.feedback.initiative?.revision,confirm:true});});this.reset.id='resetInitiativeRound';
            document.getElementById('turnOrderWidget').append(this.candidates,this.reset);this.refresh(true);
        }
        checkbox(id){const input=el('input');input.type='checkbox';input.id=id;return input;}
        label(value,input){const label=el('label',value);label.append(input);return label;}
        refresh(force=false){
            const ui=this.ui,map=ui.bootstrap?.state_payload?.active_map;if(!map)return;
            const key=map.id+':'+(map.presentation?.revision||0);
            if(force||key!==this.key){this.key=key;this.mapId=map.id;this.revision=map.presentation?.revision||0;this.grid.value=map.grid_size||70;this.visible.checked=map.presentation?.grid_visible!==false;this.dynamic.checked=map.presentation?.dynamic_lighting!==false;this.fog.checked=Boolean(map.fog_enabled);this.ambient.value=map.presentation?.ambient??25;}
            const tokens=ui.bootstrap?.state_payload?.tokens||[];
            const tokenKey=JSON.stringify(tokens.map(t=>[t.id,t.name,t.map_id]));
            if(tokenKey!==this.tokenKey){this.tokenKey=tokenKey;const selected=this.preview.value;this.preview.replaceChildren(new Option(text('DM · gesamte Karte','DM · full map'),''));for(const token of tokens.filter(t=>Number(t.map_id)===Number(map.id)))this.preview.append(new Option(token.name,String(token.id)));this.preview.value=selected;if(!this.preview.value&&ui.feedback.previewToken){ui.feedback.previewToken=null;document.getElementById('visionLayer').hidden=Boolean(ui.feedback.markerHiddenBeforePreview);ui.feedback.sequence=(ui.feedback.sequence||0)+1;ui.feedback.scheduleLighting();}}
            const geoKey=JSON.stringify([ui._walls,ui._lights]);
            if(force||geoKey!==this.geoKey){this.geoKey=geoKey;this.geometry.replaceChildren();
                for(const [kind,rows]of [['wall',ui._walls||[]],['light',ui._lights||[]]])for(const row of rows){const item=el('li');item.append(el('span',kind==='wall'?text(`Wand ${row.id} · Sicht: ${row.sight} · Licht: ${row.light}`,`Wall ${row.id} · sight: ${row.sight} · light: ${row.light}`):text(`Licht ${row.id} · ${row.light_type}`,`Light ${row.id} · ${row.light_type}`)));
                    item.append(button(text('Bearbeiten','Edit'),event=>{const rect=this.root.getBoundingClientRect();if(kind==='wall')ui._openWallEditPopover(row.id,{clientX:rect.left,clientY:rect.top+80});else ui._openLightEditPopover(row.id,{clientX:rect.left,clientY:rect.top+80});}));this.geometry.append(item);}
                if(!this.geometry.children.length)this.geometry.append(el('li',text('Noch keine Wände oder Lichter.','No walls or lights yet.')));
            }
        }
        async saveSettings(){const ui=this.ui;this.save.disabled=true;
            const body={revision:this.revision,grid_size:Number(this.grid.value),grid_visible:this.visible.checked,dynamic_lighting:this.dynamic.checked,fog_enabled:this.fog.checked,ambient:Number(this.ambient.value)};
            const path=`${this.path}/maps/${this.mapId}/presentation`;
            try{try{await Auth.makeAuthRequest(path,'PUT',body);}catch(error){if(error.apiError==='fog_reset_confirmation_required'&&confirm(text('Die neue Rastergröße setzt die gespeicherte Aufklärung zurück. Fortfahren?','Changing grid size clears saved exploration. Continue?'))){await Auth.makeAuthRequest(path,'PUT',{...body,confirm_fog_reset:true});}else throw error;}
                await ui.loadBootstrap();this.refresh(true);this.status.textContent=text('Karteneinstellungen gespeichert.','Map settings saved.');}
            catch(error){this.status.textContent=error.message;await ui.loadBootstrap();this.refresh(true);}finally{this.save.disabled=false;}
        }
        renderParents(layers,byId){
            const ui=this.ui;
            for(const layer of layers){const row=document.querySelector(`#layerList .layer-row[data-layer-id="${layer.id}"] .layer-info`);if(!row||row.querySelector('.layer-parent-label'))continue;
                const select=el('select');select.setAttribute('aria-label',text('Übergeordnete Seite','Parent page'));select.append(new Option(text('Oberste Ebene','Top level'),''));
                for(const candidate of layers){let parent=candidate,cycle=false,visited=new Set();while(parent){if(parent.id===layer.id||visited.has(parent.id)){cycle=true;break;}visited.add(parent.id);parent=byId.get(parent.parent_layer_id);}if(!cycle)select.append(new Option(candidate.label,String(candidate.id)));}
                select.value=layer.parent_layer_id??'';select.disabled=ui.readOnly;
                select.onchange=async()=>{select.disabled=true;try{await Auth.makeAuthRequest(`${this.path}/scene-stack/layers/${layer.id}/parent`,'PUT',{parent_layer_id:select.value?Number(select.value):null,revision:ui.bootstrap.scene_stack.hierarchy_revision||0});await ui.loadBootstrap();}catch(error){ui._showMessage(error.message,true);await ui.loadBootstrap();}};
                const label=this.label(text('Unterseite von','Child of'),select);label.className='layer-parent-label';row.append(label);
            }
        }
        renderCandidates(data){this.candidates.replaceChildren();for(const row of data.candidates.filter(c=>c.status==='pending')){const item=el('li',`${row.name}: ${row.total}`);const accept=button(text('Übernehmen','Accept'),()=>this.action(`/initiative-candidates/${row.id}/accept`,{revision:data.revision}));item.append(accept);this.candidates.append(item);}this.reset.disabled=this.ui.readOnly;}
        async action(suffix,body){try{await Auth.makeAuthRequest(this.path+suffix,'POST',body);await this.ui.loadBootstrap();await this.ui.feedback.refreshInitiative(true);}catch(error){this.ui._showMessage(error.message,true);await this.ui.feedback.refreshInitiative(true);}}
    };
})();
