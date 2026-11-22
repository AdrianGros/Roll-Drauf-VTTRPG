/* Common projection consumer. No source catalogue or DM editor is loaded here. */
(() => {
    // Use an opaque black SVG for a fail-closed loading surface, never artwork.
    const COVER='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><rect width="1" height="1" fill="black"/></svg>');
    window.PlayFloorView=class {
        constructor(ui){
            this.ui=ui;this.path=`/api/play/campaigns/${ui.campaignId}/sessions/${ui.sessionId}/floors/view`;
            this.notice=document.createElement('p');this.notice.id='floorViewStatus';this.notice.setAttribute('role','status');
            document.getElementById('mapStage')?.append(this.notice);
            this.timer=setInterval(()=>this.refresh(),4000);
            window.addEventListener('pagehide',()=>{this.closed=true;this.sequence=(this.sequence||0)+1;clearInterval(this.timer);});
            this.refresh(true);
        }
        get masked(){return this.enabled!==false&&(!this.ui._composedOperator||Boolean(this.preview));}
        syncMap(map){
            const preview=this.ui.feedback?.previewToken||null;
            if(this.mapId===map?.id&&this.preview===preview)return;
            this.mapId=map?.id;this.preview=preview;this.enabled=null;this.image=null;this.viewKey=null;
            this.sequence=(this.sequence||0)+1;this.paint(COVER);
            queueMicrotask(()=>this.refresh(true));
        }
        background(map){this.syncMap(map);return this.enabled===false?map?.background_url:(this.image||COVER);}
        paint(source){const image=document.getElementById('mapImage');if(image&&source){image.src=source;image.style.display='block';}}
        async refresh(force=false){
            if(this.closed)return;
            const map=this.ui.bootstrap?.state_payload?.active_map;if(!map)return;
            this.syncMap(map);
            const state=`${this.mapId}:${this.preview||''}`;
            if(this.flight===state||(!force&&Date.now()-(this.lastRequest||0)<3500))return;
            const sequence=this.sequence;this.flight=state;this.lastRequest=Date.now();
            const query=new URLSearchParams();if(this.viewKey)query.set('view_key',this.viewKey);if(this.preview)query.set('token_id',this.preview);
            try{
                const result=await Auth.makeAuthRequest(this.path+(query.size?'?'+query:''));
                if(this.closed||sequence!==this.sequence||map.id!==this.ui.bootstrap?.state_payload?.active_map?.id)return;
                if(!result||result.map_id!==map.id)throw new Error('Karte wurde geändert. Sicht wird neu geladen.');
                if(result.enabled){
                    if(!result.unchanged){if(!/^data:image\/png;base64,/.test(result.image||''))throw new Error('Etagenansicht fehlt.');this.image=result.image;}
                    if(!this.image)throw new Error('Etagenansicht fehlt.');
                    this.enabled=true;this.viewKey=result.view_key;this.paint(this.image);
                    this.notice.textContent=result.name||'';
                    if(this.masked){if(this.ui.feedback?.image)this.ui.feedback.image.hidden=true;this.ui._illuminationActive=true;document.querySelectorAll('#visionLayer .fog-cell').forEach(node=>node.style.display='none');}
                }else{
                    this.enabled=false;this.image=null;this.viewKey=null;this.notice.textContent='';
                    this.ui._renderMapCanvas();this.ui.feedback?.scheduleLighting();
                }
            }catch(error){
                if(sequence===this.sequence){this.enabled=null;this.image=null;this.viewKey=null;this.paint(COVER);this.notice.textContent=globalThis.VTTUi?.('Etagenansicht konnte nicht aktualisiert werden. Erneut verbinden.') || 'Etagenansicht konnte nicht aktualisiert werden. Erneut verbinden.';}
            }finally{if(this.flight===state)this.flight=null;}
        }
    };
})();
