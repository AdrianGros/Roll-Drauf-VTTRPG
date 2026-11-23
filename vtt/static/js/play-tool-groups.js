/* One command inventory over existing authorized controls; no domain writes. */
(() => {
    const t = source => globalThis.VTTUi(source);
    const node = (tag, className, text) => { const e=document.createElement(tag);if(className)e.className=className;if(text)e.textContent=t(text);return e; };
    const visible = e => Boolean(e && e.getClientRects().length && !e.closest('[hidden]'));
    window.PlayToolGroups = class {
        constructor(ui) { this.ui=ui;this.commands=new Map();this.proxies=new Map(); }
        icon(name) {
            const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.classList.add('play-command-icon');
            const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href','/static/icons/play-controls.svg#'+name);svg.append(use);return svg;
        }
        decorate(button,label,icon,description) {
            for(const attr of ['data-ui-key','data-ui-title','data-ui-aria-label'])button.removeAttribute(attr);
            const text=node('span','tool-label',label);button.replaceChildren(this.icon(icon),text);
            button.classList.add('play-command');button.setAttribute('aria-label',t(label));button.title=t(description||label);return button;
        }
        register(id,selector,label,icon,options={}) {
            const source=typeof selector==='string'?document.querySelector(selector):selector;if(!source)return null;
            const command={id,source,label,icon,kind:'window',...options};this.commands.set(id,command);
            source.addEventListener('click',()=>{if(source.closest('#window-tableMore'))this.ui.windows.close('tableMore');},true);
            source.addEventListener('click',()=>queueMicrotask(()=>this.sync()));
            if(options.decorateSource!==false)this.decorate(source,label,icon,command.description);return command;
        }
        renameWindow(id,label) {const item=this.ui.windows.items.get(id);if(!item)return;item.element.setAttribute('aria-label',t(label));item.element.querySelector('.play-window-head strong').textContent=t(label);}
        windowCommand(id,selector,label,icon,windowId,options={}) {return this.register(id,selector,label,icon,{windowId,...options});}
        group(label) {const e=node('div','play-command-group');e.setAttribute('role','group');e.setAttribute('aria-label',t(label));return e;}
        proxy(command) {
            const button=node('button','play-command-row');button.type='button';button.dataset.command=command.id;
            this.decorate(button,command.label,command.icon,command.description);
            button.addEventListener('click',()=>this.execute(command));
            if(!this.proxies.has(command.id))this.proxies.set(command.id,[]);this.proxies.get(command.id).push(button);return button;
        }
        execute(command) {
            if(!this.available(command))return;
            if(!this.ui.windows.items.get('tableCommands').element.hidden)this.ui.windows.close('tableCommands');
            if(!this.ui.windows.items.get('tableMore').element.hidden)this.ui.windows.close('tableMore');
            if(command.windowId && !this.ui.windows.items.get(command.windowId)?.element.hidden)this.ui.windows.open(command.windowId);
            else if(command.run)command.run();else command.source.click();
            this.sync();
        }
        available(command) {return !command.source.disabled && command.source.getAttribute('aria-disabled')!=='true' && (!command.enabled||command.enabled());}
        related(windowId,commands) {
            const panel=node('section','play-related-commands');panel.setAttribute('aria-label',t('Weitere Werkzeuge'));
            for(const command of commands.filter(Boolean)){command.source.classList.add('play-command-row');panel.append(command.source);}
            this.ui.windows.items.get(windowId).element.querySelector('.play-window-body').prepend(panel);
        }
        mount() {
            const ui=this.ui, toolbar=document.querySelector('.left-toolbar');this.toolbar=toolbar;
            const primaryTools=[['select','Auswählen','select'],['pan','Bewegen','pan'],['measure','Messen','measure']].map(([id,label,icon])=>this.register(id,`.left-toolbar [data-tool="${id}"]`,label,icon,{kind:'tool'}));
            const scenes=this.windowCommand('scenes','#dock-layersWidget','Szenen','scenes','layersWidget',{aliases:'Seiten Karten Scenes'});
            const figures=this.windowCommand('figures','#dock-tokenWidget','Figuren','figures','tokenWidget',{aliases:'Tokens Monster Objects NPC'});
            const initiative=this.windowCommand('initiative','#dock-turnOrderWidget','Initiative','initiative','turnOrderWidget');
            const chat=this.windowCommand('chat','#btnChatToggle','Chat','chat','panel-chat');
            const dice=this.windowCommand('dice','#btnDiceWindow','Würfeln','dice','panel-tools');
            const journal=this.windowCommand('journal','#btnSidebarToggle','Journal und Materialien','journal','panel-journal');
            const beyond=this.windowCommand('beyond','#btnBeyond20Setup','Beyond20 einrichten','link','beyond20');
            const menu=this.register('menu','#btnBack','Tischmenü','more',{kind:'menu'});
            const display=this.register('display','#appMenuDisplay','Ansicht und Sprache','settings',{kind:'action',decorateSource:false});
            const reset=this.register('reset','#btnResetWindows','Fenster zurücksetzen','reset',{kind:'action',decorateSource:false});
            const help=this.register('help','#appMenuHelp','Hilfe und Tastenkürzel','help',{kind:'action',decorateSource:false});
            const leave=this.register('leave','#appMenuLeave','Tisch verlassen','leave',{kind:'action',decorateSource:false});leave.source.replaceChildren(document.createTextNode(t('Tisch verlassen')));
            const seat=document.getElementById('appMenuSeat');if(seat)this.register('seat',seat,'Tischplatz wechseln','figures',{kind:'action',decorateSource:false,aliases:'DM Player Spielleitung Spieler'});
            const snap=this.register('snap','#btnMeasureSnap','Am Raster einrasten','grid',{kind:'toggle',enabled:()=>ui.currentTool==='measure'});
            if(snap){snap.source.classList.add('play-command-row');const options=document.getElementById('measureOptions');options.append(snap.source);document.body.append(options);}
            this.renameWindow('layersWidget','Szenen');this.renameWindow('tokenWidget','Figuren');
            const secondary=node('section','play-more-commands');
            this.ui.windows.add('tableMore','Weitere Tischfunktionen',secondary);
            this.more=node('button','tool-btn');this.more.type='button';this.more.id='btnTableMore';this.decorate(this.more,'Mehr','more','Weitere Tischfunktionen');
            this.more.setAttribute('aria-controls','window-tableMore');this.more.setAttribute('aria-expanded','false');this.more.onclick=()=>ui.windows.toggle('tableMore');ui.windows.items.get('tableMore').trigger=this.more;
            const catalog=node('section','play-command-catalog');
            const searchLabel=node('label',null,'Befehl suchen');this.search=node('input');this.search.type='search';this.search.id='playCommandSearch';this.search.autocomplete='off';this.search.placeholder=t('Zum Beispiel Messen, Figuren oder Initiative');searchLabel.htmlFor=this.search.id;
            this.list=node('div','play-command-list');this.result=node('p','muted');this.result.setAttribute('role','status');catalog.append(searchLabel,this.search,this.list,this.result);
            ui.windows.add('tableCommands','Alle Werkzeuge',catalog);
            const all=node('button','play-command-row');all.type='button';all.id='btnAllTableCommands';this.decorate(all,'Alle Werkzeuge','search');all.onclick=()=>{ui.windows.close('tableMore');this.filter();ui.windows.open('tableCommands');this.search.focus();};secondary.append(all);
            if(ui._composedOperator)window.PlayToolGroupsDM.mount(this);
            for(const command of [journal,beyond,menu].filter(Boolean)){command.source.classList.add('play-command-row');secondary.append(command.source);}
            for(const command of [display,reset,help,leave].filter(Boolean))secondary.append(this.proxy(command));
            const tools=this.group('Werkzeug wählen'),windows=this.group('Tischfenster öffnen'),table=this.group('Kommunikation und weitere Funktionen');
            primaryTools.forEach(c=>tools.append(c.source));[scenes,figures,initiative,this.commands.get('map')].filter(Boolean).forEach(c=>windows.append(c.source));[chat,dice].forEach(c=>table.append(c.source));table.append(this.more);
            this.status=node('p','play-tool-status');this.status.id='playToolStatus';this.status.setAttribute('role','status');
            const groups=node('div','play-command-groups table-dock-tabs');groups.id='tableDockTabs';groups.append(tools,windows,table);toolbar.replaceChildren(this.status,groups);toolbar.removeAttribute('data-ui-aria-label');toolbar.setAttribute('aria-label',t('Werkzeuge und Tischfenster'));
            this.list.replaceChildren(...[...this.commands.values()].map(c=>this.proxy(c)));
            this.search.addEventListener('input',()=>this.filter());
            for(const [id,item]of ui.windows.items){item.fallbackTrigger=id==='tokenLayersWidget'?figures.source:this.more;}
            for(const id of ['appMenuLeaveConfirm','appMenuLeaveDialog']){
                const target=id==='appMenuLeaveDialog'?document.querySelector('#appMenuLeaveDialog h3'):document.getElementById(id);
                if(target){target.removeAttribute('data-ui-key');target.replaceChildren(document.createTextNode(t(id==='appMenuLeaveDialog'?'Tisch verlassen?':'Tisch verlassen')));}
            }
            document.body.classList.add('play-tool-groups');this.filter();this.sync();
        }
        filter() {
            const query=this.search.value.trim().toLocaleLowerCase();let count=0;
            for(const command of this.commands.values()){
                const button=this.proxies.get(command.id)?.find(e=>e.parentElement===this.list);if(!button)continue;
                const match=(t(command.label)+' '+command.label+' '+(command.aliases||'')).toLocaleLowerCase().includes(query);
                button.hidden=!match;if(match)count++;
            }
            this.result.textContent=count?globalThis.VTTUi('{count} Befehle',{count}):t('Keine passenden Befehle.');this.sync();
        }
        sync() {
            if(!this.more)return;
            for(const command of this.commands.values()){
                const open=command.windowId?!this.ui.windows.items.get(command.windowId)?.element.hidden:command.source.getAttribute('aria-expanded')==='true';
                if(command.windowId)command.source.setAttribute('aria-expanded',String(open));
                for(const button of this.proxies.get(command.id)||[]){
                    button.disabled=!this.available(command);
                    if(command.kind==='tool')button.setAttribute('aria-pressed',String(this.ui.currentTool===command.id));
                    else if(command.kind==='toggle')button.setAttribute('aria-pressed',command.source.getAttribute('aria-pressed')||'false');
                    else if(command.kind==='window'||command.kind==='menu')button.setAttribute('aria-expanded',String(open));
                }
                if(command.kind==='tool')command.source.setAttribute('aria-pressed',String(this.ui.currentTool===command.id));
            }
            const label=this.commands.get(this.ui.currentTool)?.label || (this.ui.currentTool==='token'?'Figur platzieren':'Auswählen');
            const status=t('Werkzeug')+': '+t(label)+(this.ui.readOnly?' · '+t('Nur Lesen'):'');if(this.status.textContent!==status)this.status.textContent=status;
        }
    };
})();
