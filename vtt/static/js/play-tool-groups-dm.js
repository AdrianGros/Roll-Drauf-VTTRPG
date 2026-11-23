/* Definitions are mounted only in the server-authorized DM composition. */
window.PlayToolGroupsDM = {
    mount(groups) {
        const ui=groups.ui;
        groups.windowCommand('map','#btnMapPresentation','Karte & Sicht','map','mapPresentation',{aliases:'Raster Licht Wände Perspektive'});
        groups.renameWindow('mapPresentation','Karte & Sicht');
        const layers=groups.windowCommand('token-layers','#dock-tokenLayersWidget','Token-Sichtbarkeit','visibility','tokenLayersWidget',{aliases:'Layers Dungeon Master Player'});
        groups.renameWindow('tokenLayersWidget','Token-Sichtbarkeit');groups.related('tokenWidget',[layers]);
        const placement=document.getElementById('mapGeometryTools');placement.replaceChildren();
        for(const [id,selector,label,icon,kind]of [['wall','#toolWall','Wand zeichnen','wall','tool'],['light','#toolLight','Licht setzen','light','tool'],['markers','#btnVisionToggle','Markierungen','visibility','toggle']]){
            const command=groups.register(id,selector,label,icon,{kind,enabled:()=>Boolean(ui.bootstrap?.state_payload?.active_map)&&(!ui.readOnly||kind==='toggle')});
            command.source.classList.add('play-command-row');placement.append(command.source);
            if(kind==='tool')command.source.addEventListener('click',()=>{if(ui.currentTool===id)ui.windows.close('mapPresentation');});
        }
        groups.windowCommand('floors','#btnMapFloors','Etagen und Balkonsicht','scenes','mapFloors',{aliases:'Balkon Geschosse Etage Floors',enabled:()=>Boolean(ui.bootstrap?.state_payload?.active_map)}).source.classList.add('play-command-row');
        const session=document.createElement('button');session.type='button';session.id='btnTableSessionManagement';
        session.addEventListener('click',()=>{ui.windows.open('panel-journal');document.getElementById('journalSessionControls').open=true;});
        const command=groups.register('session',session,'Sitzung verwalten','settings',{run:()=>session.click(),kind:'action'});
        document.querySelector('#window-tableMore .play-window-body section').append(groups.proxy(command));
    }
};
