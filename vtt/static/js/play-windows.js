/* Existing authorized content, one instance per movable window. */
(() => {
    const t = (s) => globalThis.VTTUi?.(s) || s;
    const node = (tag, text, cls) => { const e = document.createElement(tag); if (text) e.textContent = t(text); if (cls) e.className = cls; return e; };
    window.PlayWindows = class {
        constructor(ui) {
            this.ui = ui; this.items = new Map(); this.z = 60;
            this.prefix = `vtt:windows:${ui.user?.id}:${ui.campaignId}:${ui._composedOperator ? 'dm' : 'player'}:`;
        }
        mount() {
            document.body.classList.add('play-free-windows');
            const launchers = node('div', '', 'table-dock-tabs'); launchers.id = 'tableDockTabs';
            launchers.setAttribute('role', 'toolbar'); launchers.setAttribute('aria-label', t('Tischfenster'));
            const entries = [['layersWidget', 'Seiten'], ['turnOrderWidget', 'Initiative'], ['tokenWidget', 'Tokens'], ...(this.ui._dmDockEntries || [])];
            for (const [id, title] of entries) {
                const content = document.getElementById(id); if (!content) continue;
                content.hidden = false; content.classList.remove('collapsed');
                const oldHeading = content.querySelector('.widget-toggle'); if (oldHeading) oldHeading.hidden = true;
                this.add(id, title, content);
                const button = node('button', '', 'tool-btn'); const label = node('span', title, 'tool-label'); button.append(label); button.type = 'button'; button.id = 'dock-' + id;
                button.setAttribute('aria-controls', 'window-' + id); button.setAttribute('aria-expanded', 'false');
                button.onclick = () => this.toggle(id); launchers.append(button);
                this.items.get(id).trigger = button;
            }
            document.querySelector('.left-toolbar').prepend(launchers);
            document.body.append(document.querySelector('.left-toolbar'), document.getElementById('personalActionBar'), document.getElementById('actionHotbar'));
            const toolbar = document.querySelector('.left-toolbar'), personal = document.getElementById('personalActionBar');
            const size = () => {
                document.documentElement.style.setProperty('--play-toolbar-height', Math.ceil(toolbar.getBoundingClientRect().height) + 'px');
                document.documentElement.style.setProperty('--play-personal-height', Math.ceil(personal.getBoundingClientRect().height) + 'px');
                document.documentElement.style.setProperty('--play-action-height', Math.ceil(document.getElementById('actionHotbar').getBoundingClientRect().height) + 'px');
                if(this.ui.toolGroups)requestAnimationFrame(()=>this.reclamp());
            };
            this.barObserver = new ResizeObserver(size); this.barObserver.observe(toolbar); this.barObserver.observe(personal); this.barObserver.observe(document.getElementById('actionHotbar')); size();
            for (const [id, title, trigger] of [['panel-chat', 'Chat', 'btnChatToggle'], ['panel-journal', 'Journal', 'btnSidebarToggle']]) {
                this.add(id, title, document.getElementById(id));
                const button = document.getElementById(trigger); this.items.get(id).trigger = button;
                button.setAttribute('aria-controls', 'window-' + id);
                button.addEventListener('click', () => this.toggle(id));
            }
            this.add('panel-tools', 'Würfel und Werkzeuge', document.getElementById('panel-tools'));
            const tools = node('button', 'Würfeln', 'tool-btn'); tools.id = 'btnDiceWindow'; tools.type = 'button';
            tools.onclick = () => this.toggle('panel-tools');
            document.getElementById('btnSidebarToggle').before(tools);
            this.items.get('panel-tools').trigger = tools;
            const beyond = node('button', 'Beyond20', 'tool-btn'); beyond.id = 'btnBeyond20Setup'; beyond.type = 'button';
            const help = node('section');
            const link = node('a', 'Anleitung in neuem Tab öffnen'); link.href = '/beyond20.html'; link.target = '_blank'; link.rel = 'noopener';
            const frame = node('iframe'); frame.src = '/beyond20.html?compact=1'; frame.title = t('Beyond20 einrichten'); frame.className = 'beyond-setup-frame';
            help.append(link, frame); this.add('beyond20', 'Beyond20 einrichten', help);
            beyond.onclick = () => this.toggle('beyond20'); tools.after(beyond);
            const reset = node('button', 'Fenster zurücksetzen'); reset.id = 'btnResetWindows'; reset.type = 'button';
            reset.onclick = () => { try { Object.keys(localStorage).filter(key => key.startsWith(this.prefix)).forEach(key => localStorage.removeItem(key)); } catch (_) {} for (const [id, item] of this.items) { try { localStorage.removeItem(this.prefix + id); } catch (_) {} this.position(item.element, id, true); } };
            reset.className = 'app-menu-item'; reset.setAttribute('role','menuitem'); document.getElementById('appMenuDisplay').after(reset);
            this.native(document.getElementById('sheetDrawer'), '.sheet-drawer-head');
            this.native(document.getElementById('appMenu'), '#appMenuStatus');
            if (this.ui._composedOperator) this.native(document.getElementById('tokenSelectionBar'), '#tokenSelectionCount');
            this.native(document.getElementById('tokenCreatePanel'), 'h3');
            // Settings and action/library dialogs can be constructed lazily.
            this.observer = new MutationObserver(records => {
                for (const record of records) {
                    if (record.type === 'attributes') {
                        const e = record.target;
                        if (e.dataset.movable && !e.hidden && (!e.matches('dialog') || e.open)) { e.style.zIndex = String(++this.z); this.position(e, e.id); }
                    }
                }
                document.querySelectorAll('dialog:not([data-movable])').forEach(e => this.native(e, 'h2,h3,header'));
            });
            this.observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['open', 'hidden']});
            document.querySelectorAll('dialog').forEach(e => this.native(e, 'h2,h3,header'));
            window.addEventListener('pagehide', () => { for (const [id,item] of this.items) if (!item.element.hidden) this.save(item.element,id); });
            window.addEventListener('resize', () => this.reclamp());
            document.addEventListener('fullscreenchange', () => this.reclamp());
            document.addEventListener('keydown', event => {
                if(event.target.closest?.('#appMenu'))return;
                if (event.key !== 'Escape' || document.querySelector('dialog[open]') || !this.top()) return;
                const item = event.target.closest?.('.play-window') || this.top().element;
                const key = [...this.items].find(([, value]) => value.element === item)?.[0];
                if (key) { event.preventDefault(); event.stopImmediatePropagation(); this.close(key); }
            }, true);
        }
        add(id, title, content) {
            if (!content) return;
            const element = node('section', '', 'play-window'); element.id = 'window-' + id; element.hidden = true;
            element.setAttribute('role', 'region'); element.setAttribute('aria-label', t(title));
            const header = node('header', '', 'play-window-head'); const heading = node('strong', title);
            heading.tabIndex = 0; heading.title = t('Mit der Maus oder den Pfeiltasten verschieben');
            const close = node('button', '×'); close.type = 'button'; close.setAttribute('aria-label', t('Fenster schließen'));
            close.onclick = () => this.close(id); header.append(heading, close);
            const body = node('div', '', 'play-window-body'); body.append(content); element.append(header, body);
            document.body.append(element); content.classList.add('active');
            this.items.set(id, {element}); this.drag(element, header, id);
            element.addEventListener('pointerdown', () => { element.style.zIndex = String(++this.z); });
            heading.onkeydown = event => {
                const delta = {ArrowLeft: [-16, 0], ArrowRight: [16, 0], ArrowUp: [0, -16], ArrowDown: [0, 16]}[event.key];
                if (!delta) return; event.preventDefault(); const r = element.getBoundingClientRect();
                this.apply(element, r.left + delta[0], r.top + delta[1]); this.save(element, id);
            };
        }
        top() { return [...this.items.values()].filter(i => !i.element.hidden).sort((a, b) => Number(b.element.style.zIndex) - Number(a.element.style.zIndex))[0]; }
        open(id) {
            const item = this.items.get(id); if (!item) return;
            item.element.hidden = false; item.element.style.zIndex = String(++this.z); this.position(item.element, id);
            item.trigger?.setAttribute('aria-expanded', 'true');
            item.element.querySelector('.play-window-head strong')?.focus({preventScroll: true});
            if (id === 'tokenWidget') this.ui.tokenLibrary?.refresh();
            this.ui.toolGroups?.sync();
        }
        close(id) { const item = this.items.get(id); if (!item) return; this.save(item.element, id); item.element.hidden = true; item.trigger?.setAttribute('aria-expanded', 'false'); const trigger=item.trigger?.getClientRects().length?item.trigger:item.fallbackTrigger;trigger?.focus({preventScroll: true});this.ui.toolGroups?.sync(); }
        toggle(id) { const item = this.items.get(id); if (item) item.element.hidden ? this.open(id) : this.close(id); }
        position(element, id, reset = false) {
            if (!element || element.hidden || element.matches('dialog:not([open])')) return;
            let point;
            if (!reset) { try { point = JSON.parse(localStorage.getItem(this.prefix + id)); } catch (_) {} }
            const index = Math.max(0, [...this.items.keys()].indexOf(id));
            const current = element.getBoundingClientRect(); const native = !element.classList.contains('play-window');
            const reserve = Math.ceil(document.querySelector('.left-toolbar')?.getBoundingClientRect().height || 64) + 24
                + Math.ceil(document.getElementById('personalActionBar')?.getBoundingClientRect().height || 0)
                + Math.ceil(document.getElementById('actionHotbar')?.getBoundingClientRect().height || 0);
            const nativeTop = id === 'tokenSelectionBar' ? Math.max(48, innerHeight - reserve - current.height - 16) : current.top;
            this.apply(element, Number.isFinite(point?.left) ? point.left : native && !reset ? current.left : 86 + index % 3 * 35,
                       Number.isFinite(point?.top) ? point.top : native && !reset ? nativeTop : 72 + index % 4 * 30);
        }
        apply(element, left, top) {
            const r = element.getBoundingClientRect();
            const x = Math.max(6, Math.min(Math.max(6, innerWidth - r.width - 6), left));
            const reserve = Math.ceil(document.querySelector('.left-toolbar')?.getBoundingClientRect().height || 64) + 24
                + Math.ceil(document.getElementById('personalActionBar')?.getBoundingClientRect().height || 0)
                + Math.ceil(document.getElementById('actionHotbar')?.getBoundingClientRect().height || 0);
            const y = Math.max(48, Math.min(Math.max(48, innerHeight - reserve - 44), top));
            Object.assign(element.style, {left: x + 'px', top: y + 'px', right: 'auto', bottom: 'auto', margin: '0', maxHeight: Math.max(56, innerHeight - y - reserve) + 'px'});
        }
        save(element, id) { const r = element.getBoundingClientRect(); try { localStorage.setItem(this.prefix + id, JSON.stringify({left: r.left, top: r.top})); } catch (_) {} }
        reclamp() { for (const item of this.items.values()) if (!item.element.hidden) { const r = item.element.getBoundingClientRect(); this.apply(item.element, r.left, r.top); } document.querySelectorAll('[data-movable]:not([hidden])').forEach(e => { if (e.matches('dialog:not([open])')) return; const r = e.getBoundingClientRect(); this.apply(e, r.left, r.top); }); }
        native(element, selector) {
            if (!element || element.dataset.movable) return;
            const header = element.querySelector(selector); if (!header) return;
            if (['tokenCreatePanel','appMenu','tokenSelectionBar'].includes(element.id)) document.body.append(element);
            element.dataset.movable = 'true'; this.drag(element, header, element.id);
            element.addEventListener('pointerdown', () => { element.style.zIndex = String(++this.z); });
        }
        drag(element, header, id) {
            header.classList.add('play-drag-handle');
            header.addEventListener('pointerdown', event => {
                if (event.button !== 0 || event.target.closest('button,a,input,select,textarea')) return;
                event.preventDefault(); event.stopPropagation();
                const r = element.getBoundingClientRect(); const dx = event.clientX - r.left, dy = event.clientY - r.top;
                header.setPointerCapture(event.pointerId);
                const move = e => { if (e.pointerId === event.pointerId) { e.preventDefault(); this.apply(element, e.clientX - dx, e.clientY - dy); this.save(element, id); } };
                const end = e => { if (e.pointerId !== event.pointerId) return; this.save(element, id);
                    window.removeEventListener('pointermove', move, true); window.removeEventListener('pointerup', end, true); window.removeEventListener('pointercancel', end, true);
                    try { header.releasePointerCapture(event.pointerId); } catch (_) {}
                };
                window.addEventListener('pointermove', move, true); window.addEventListener('pointerup', end, true); window.addEventListener('pointercancel', end, true);
            });
        }
    };
})();
