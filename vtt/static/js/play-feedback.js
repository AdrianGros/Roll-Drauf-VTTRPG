/* Shared table presentation. Privileged controls live in the DM-only module. */
(() => {
    const en=()=>document.documentElement.lang.startsWith('en');
    const text=(de,english)=>en()?english:de;
    const el=(tag,value)=>{const node=document.createElement(tag);if(value)node.textContent=value;return node;};
    window.PlayFeedback=class {
        constructor(ui){
            this.ui=ui;this.path=`/api/play/campaigns/${ui.campaignId}/sessions/${ui.sessionId}`;
            this.image=el('img');this.image.id='lightingProjection';this.image.alt='';this.image.hidden=true;
            document.getElementById('mapWorld').append(this.image);
            this.notice=el('p');this.notice.id='initiativePendingNotice';this.notice.setAttribute('role','status');
            document.getElementById('turnOrderWidget').append(this.notice);
            const square=document.querySelector('#measureShape option[value="square"]');if(square){square.removeAttribute('data-ui-key');square.textContent=text('Quadrat · Mittelpunkt zuerst','Square · centre first');}
            const help=el('p',text('Kreis und Quadrat: Mittelpunkt wählen, dann bis zum Rand ziehen.','Circle and square: choose the centre, then move to the edge.'));document.getElementById('measureOptions')?.append(help);
            const snap=document.querySelector('#btnMeasureSnap .tool-label');if(snap)snap.textContent=text('Einrasten','Snap');
            const pan=document.querySelector('[data-tool="pan"]');if(pan){pan.title=text('Verschieben · Leertaste halten · mittlere Maustaste','Pan · hold Space · middle mouse button');}
            document.addEventListener('keydown',event=>{if(event.code==='Space'&&!event.target.closest?.('input,textarea,select,button,a,[contenteditable="true"]')){ui._spacePan=true;event.preventDefault();}});
            document.addEventListener('keyup',event=>{if(event.code==='Space')ui._spacePan=false;});
            window.addEventListener('blur',()=>{ui._spacePan=false;});
            window.addEventListener('pagehide',()=>{clearTimeout(this.timer);this.closed=true;this.sequence=(this.sequence||0)+1;});
            document.getElementById("dock-turnOrderWidget")?.addEventListener("click",()=>this.refreshInitiative(true));
            this.refresh();
        }
        refresh(){
            const map=this.ui.bootstrap?.state_payload?.active_map;
            if(this.mapId!==map?.id){if(this.previewToken)document.getElementById("visionLayer").toggleAttribute("hidden",Boolean(this.markerHiddenBeforePreview));document.querySelectorAll('.token-marker').forEach(marker=>marker.style.visibility='');this.mapId=map?.id;this.previewToken=null;this.sequence=(this.sequence||0)+1;this.image.hidden=true;this.ui._illuminationActive=false;if(map&&!this.ui._composedOperator)this.cover(map);}
            const grid=document.getElementById('mapGridLayer');if(grid)grid.hidden=map?.presentation?.grid_visible===false;
            for(const id of ['btnOwnInitiative','btnSelectedInitiative']){const button=document.getElementById(id);if(!button)continue;const token=this.ui._findStateToken(this.ui.selectedTokenId);button.hidden=!this.ui._composedOperator&&(!token?.character_id||!this.ui._canMoveToken(token));}
            this.scheduleLighting();this.refreshInitiative();
        }
        size(map){const grid=Math.max(16,Number(map.grid_size)||70);return [map.width,map.height].map(value=>Math.round(map.light_rules?.dimensions_mode==='pixel'||value>200?value:Math.max(1,value)*grid));}
        cover(map){
            this.image.src='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><rect width="1" height="1" fill="black"/></svg>');
            const [width,height]=this.size(map);this.image.style.width=width+'px';this.image.style.height=height+'px';this.image.hidden=false;this.ui._illuminationActive=true;
        }
        scheduleLighting(){if(this.closed||this.timer)return;this.timer=setTimeout(()=>{this.timer=null;this.lighting();},800);}
        async lighting(){
            if(this.closed)return;
            if(this.busy){this.scheduleLighting();return;}
            const map=this.ui.bootstrap?.state_payload?.active_map;if(!map)return;
            const sequence=this.sequence=(this.sequence||0)+1,preview=this.previewToken;
            this.busy=true;
            try{
                const result=await Auth.makeAuthRequest(this.path+'/vision/illumination'+(preview?`?token_id=${preview}`:''));
                if(this.closed||sequence!==this.sequence||map.id!==this.ui.bootstrap?.state_payload?.active_map?.id)return;
                if(result.map_id!==map.id){if(!this.ui._composedOperator||preview)this.cover(map);await this.ui.loadBootstrap();return;}
                document.querySelectorAll('.token-marker[data-token-id]').forEach(marker=>{marker.style.visibility=result.preview&&result.visible_token_ids&&!result.visible_token_ids.includes(Number(marker.dataset.tokenId))?'hidden':'';});
                const previouslyActive=this.ui._illuminationActive;
                this.image.hidden=!result.overlay;this.ui._illuminationActive=Boolean(result.overlay);
                if(result.overlay){this.image.src=result.overlay;const [width,height]=this.size(map);this.image.style.width=width+'px';this.image.style.height=height+'px';}
                // Remove the older cell mask once the precise projection is ready.
                document.querySelectorAll('#visionLayer .fog-cell').forEach(node=>{node.style.display=result.overlay?'none':'';});
                if(previouslyActive&&!result.overlay)this.ui._renderVisionLayer();
            }catch(error){if(sequence===this.sequence){if(this.image.hidden&&(!this.ui._composedOperator||preview))this.cover(map);this.ui._showMessage(text('Die Sicht konnte nicht aktualisiert werden. Bitte erneut verbinden.','Vision could not be refreshed. Please reconnect.'),true);}}
            finally{this.busy=false;}
        }
        async refreshInitiative(force=false){
            if(this.closed)return;
            if(this.initiativeBusy){this.initiativeAgain=true;return;}
            if(!force&&Date.now()-(this.lastInitiative||0)<1500)return;
            this.initiativeBusy=true;this.lastInitiative=Date.now();
            try{this.initiative=await Auth.makeAuthRequest(this.path+'/initiative-candidates');
                const pending=this.initiative.candidates.filter(row=>row.status==='pending');
                this.notice.textContent=pending.length?text(`${pending.length} weitere Initiativewürfe warten auf Bestätigung durch die Spielleitung.`,`${pending.length} initiative rerolls await the DM's confirmation.`):'';
                this.ui.feedbackDM?.renderCandidates(this.initiative);
            }catch(error){this.notice.textContent=error.message;}finally{this.initiativeBusy=false;if(this.initiativeAgain){this.initiativeAgain=false;setTimeout(()=>this.refreshInitiative(true),100);}}
        }
        async placeTemplate(x,y){
            const ui=this.ui,row=ui.pendingTokenTemplate,map=ui.bootstrap?.state_payload?.active_map;if(!row||!map||ui.readOnly||this.placing)return;
            this.placing=true;const values=row.values||{},grid=Number(map.grid_size)||70;
            const payload={name:row.name,token_type:ui._composedOperator?(values.token_type||'npc'):'player',size:values.size||1,
                x:Math.max(0,Math.round(x/grid)*grid),y:Math.max(0,Math.round(y/grid)*grid),rotation:values.rotation||0,
                visibility:ui._composedOperator?(ui._activeTokenLayer||'public'):'public',metadata_json:{position_mode:'pixel'}};
            if(values.metadata_json?.image_url)payload.metadata_json.image_url=values.metadata_json.image_url;
            for(const key of ['character_id','hp_max','sight_range'])if(values[key]!=null)payload[key]=values[key];
            if(values.hp_max!=null)payload.hp_current=values.hp_max;
            ui._cancelTokenPlacement();
            try{await ui.api.createToken(ui.campaignId,ui.sessionId,payload);ui._setTool('select');await ui.loadBootstrap();ui._showMessage(text('Token platziert.','Token placed.'));}
            catch(error){ui._showMessage(error.message,true);}finally{this.placing=false;}
        }
        hierarchy(){
            const layers=this.ui.bootstrap?.scene_stack?.layers||[],byId=new Map(layers.map(layer=>[Number(layer.id),layer]));
            const container=document.getElementById('layerList');if(!container)return;
            container.setAttribute('role','group');
            const ordered=[],visited=new Set();
            const visit=(parent,depth,path)=>{for(const layer of layers.filter(row=>(row.parent_layer_id??null)===parent)){if(visited.has(layer.id))continue;visited.add(layer.id);ordered.push(layer);const row=container.querySelector(`.layer-row[data-layer-id="${layer.id}"]`);if(row){row.setAttribute('role','group');row.removeAttribute('aria-selected');row.style.marginInlineStart=`${Math.min(depth,12)*14}px`;row.dataset.depth=depth;const title=row.querySelector('.layer-map-name');if(title&&path.length)title.textContent=path.join(' / ')+' / '+(layer.campaign_map?.name||'');container.append(row);}visit(layer.id,depth+1,[...path,layer.label]);}};
            visit(null,0,[]);
            // Defensive projection fallback if a page disappears between bootstrap and rendering.
            for(const layer of layers)if(!visited.has(layer.id)){const row=container.querySelector(`.layer-row[data-layer-id="${layer.id}"]`);if(row)container.append(row);}
            this.ui.feedbackDM?.renderParents(layers,byId);
        }
    };
})();
