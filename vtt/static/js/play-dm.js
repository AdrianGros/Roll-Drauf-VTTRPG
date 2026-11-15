globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// DM composition and DM-only initializers. Loaded only after authorized bootstrap.
window.PlayDMSurface = {
    compose(ui, fragments) {
        for (const [name, html] of Object.entries(fragments)) {
            const slot = document.querySelector(`[data-dm-slot="${name}"]`);
            if (!slot) continue;
            const template = document.createElement("template");
            template.innerHTML = html;
            if (name === 'session-controls') {
                const details = document.createElement('details');details.id='journalSessionControls';details.className='journal-session-controls';
                const summary = document.createElement('summary');summary.textContent=globalThis.VTTUi('Sitzung verwalten');
                details.append(summary,template.content.cloneNode(true));slot.replaceWith(details);
            } else slot.replaceWith(template.content.cloneNode(true));
        }
        for (const name of Object.keys(this.methods)) ui[name] = this.methods[name].bind(ui);
        window.PlayTokenLayersDM.mount(ui);
    },
    methods: {
async _bindJournalManagement(journal) {
            const { mount } = await import('/static/js/play-journal-dm.js');
            mount(journal);
        },
_refreshMapScale() {
            const map=this.bootstrap?.state_payload?.active_map;
            const input=document.getElementById('mapScaleMeters');if(!input)return;
            for(const id of ['mapScaleMeters','mapScaleSave','mapScaleClear'])document.getElementById(id).disabled=!map;
            if(!map){this._mapScaleMapId=null;this._mapScaleKey=null;input.value='';document.getElementById('mapScaleName').textContent='—';return;}
            const scale=map.measurement_scale || {revision:0,meters_per_square:null};
            const key=`${map.id}:${scale.revision}`;
            if(this._mapScaleKey===key || document.activeElement===input)return;
            this._mapScaleKey=key;this._mapScaleMapId=map.id;this._mapScaleRevision=scale.revision;
            input.value=scale.meters_per_square ?? '';
            document.getElementById('mapScaleName').textContent=map.name;
        },
_bindMapScale() {
            this._refreshMapScale();
            const save=async(clear)=>{
                if(!this._mapScaleMapId)return;
                const input=document.getElementById('mapScaleMeters');const value=clear || input.value.trim()===''?null:Number(input.value);
                try {
                    await Auth.makeAuthRequest(`/api/play/campaigns/${this.campaignId}/sessions/${this.sessionId}/maps/${this._mapScaleMapId}/scale`,
                        'PUT',{revision:this._mapScaleRevision,meters_per_square:value});
                    await this.loadBootstrap();this._refreshMapScale();this._showMessage(globalThis.VTTUi("Kartenmaßstab gespeichert."));
                }catch(error){this._showMessage(error.message || globalThis.VTTUi("Kartenmaßstab konnte nicht gespeichert werden."),true);await this.loadBootstrap();this._refreshMapScale();}
            };
            document.getElementById('mapScaleSave').addEventListener('click',()=>save(false));
            document.getElementById('mapScaleClear').addEventListener('click',()=>save(true));
        },
_bindSessionControls() {
            this._bindMapScale();
            // DM layer only: these buttons exist only in a DM seat.
            document.getElementById("btnInitStack").addEventListener("click", async () => {
                try {
                    await this.api.initSceneStack(this.campaignId, this.sessionId);
                    this._showMessage(globalThis.VTTUi("Kartenstapel initialisiert."));
                    await this.loadBootstrap();
                } catch (error) {
                    this._showMessage(error.message || globalThis.VTTUi("Kartenstapel konnte nicht initialisiert werden."), true);
                }
            });

            document.getElementById("btnReadyCheck").addEventListener("click", async () => {
                await this._runReadyCheck();
            });

            document.getElementById("btnToReady").addEventListener("click", async () => {
                await this._transition("ready");
            });

            document.getElementById("btnStart").addEventListener("click", async () => {
                const report = await this._runReadyCheck();
                if (!report) return;
                if (report.blocking_issues && report.blocking_issues.length) return;
                if (report.warnings && report.warnings.length) {
                    const ok = window.confirm(globalThis.VTTUi("Start-Check hat Warnungen. Trotzdem live starten?"));
                    if (!ok) return;
                }
                await this._transition("in_progress", true);
            });

            document.getElementById("btnPause").addEventListener("click", async () => {
                await this._transition("paused");
            });

            document.getElementById("btnResume").addEventListener("click", async () => {
                await this._transition("in_progress", true);
            });

            document.getElementById("btnEnd").addEventListener("click", async () => {
                const ok = window.confirm(globalThis.VTTUi("Session wirklich beenden?"));
                if (!ok) return;
                await this._transition("ended", true);
            });
        },
_bindVisionViewport() {
            if (this._visionViewportBound) return;
            this._visionViewportBound = true;
            const viewport = document.getElementById('mapViewport');
            if (!viewport) return;
            // S10: light placement -- a single click places a light with
            // sensible defaults; refinement (radius/type/color) happens
            // afterward via the click-to-edit popover, same "place first,
            // refine after" split as everywhere else in this file. Apply
            // decision: no freehand draw-tool UI this slice.
            viewport.addEventListener("click", (event) => {
                if (this.currentTool !== "light") return;
                if (event.target.closest?.(".floating, .stage-topbar, .vision-light-marker, .vision-wall-line")) return;
                const point = this._worldPointFromEvent(event);
                if (!point) return;
                this._placeLight(point.x, point.y);
            });

            // S10: wall placement -- two clicks define a segment (first
            // click arms the draft and shows a rubber-band preview
            // following the pointer, mirroring the measure tool's own
            // preview mechanics; second click commits). Right-click
            // cancels an armed draft instead of placing anything.
            viewport.addEventListener("click", (event) => {
                if (this.currentTool !== "wall") return;
                if (event.target.closest?.(".floating, .stage-topbar, .vision-light-marker, .vision-wall-line")) return;
                const point = this._worldPointFromEvent(event);
                if (!point) return;
                if (!this._wallDraftStart) {
                    this._wallDraftStart = point;
                    this._renderVisionLayer();
                    return;
                }
                this._placeWall(this._wallDraftStart, point);
                this._wallDraftStart = null;
                this._renderVisionLayer();
            });
            viewport.addEventListener("pointermove", (event) => {
                if (this.currentTool !== "wall" || !this._wallDraftStart) return;
                const point = this._worldPointFromEvent(event);
                if (!point) return;
                this._wallDraftPreviewPoint = point;
                this._renderVisionLayer();
            });
            viewport.addEventListener("contextmenu", (event) => {
                if (this.currentTool !== "wall" || !this._wallDraftStart) return;
                event.preventDefault();
                this._wallDraftStart = null;
                this._wallDraftPreviewPoint = null;
                this._renderVisionLayer();
            });

        },
_bindVisionControls() {
            this._bindVisionViewport();
            const visionToggle = document.getElementById("btnVisionToggle");
            if (visionToggle) {
                visionToggle.addEventListener("click", () => {
                    const svg = document.getElementById("visionLayer");
                    if (!svg) return;
                    svg.hidden = !svg.hidden;
                    visionToggle.classList.toggle("active", !svg.hidden);
                    visionToggle.setAttribute("aria-pressed", String(!svg.hidden));
                });
            }

            const wallEditPopover = document.getElementById("wallEditPopover");
            document.getElementById("btnWallEditClose")?.addEventListener("click", () => this._closeWallEditPopover());
            document.getElementById("wallEditSight")?.addEventListener("change", () => this._saveWallEdit());
            document.getElementById("wallEditLight")?.addEventListener("change", () => this._saveWallEdit());
            document.getElementById("btnWallDelete")?.addEventListener("click", () => this._deleteSelectedWall());
            wallEditPopover?.addEventListener("keydown", (event) => {
                if (event.key === "Escape") {
                    event.preventDefault();
                    this._closeWallEditPopover();
                }
            });

            const lightEditPopover = document.getElementById("lightEditPopover");
            document.getElementById("btnLightEditClose")?.addEventListener("click", () => this._closeLightEditPopover());
            document.getElementById("lightEditType")?.addEventListener("change", () => this._saveLightEdit());
            document.getElementById("lightEditBright")?.addEventListener("change", () => this._saveLightEdit());
            document.getElementById("lightEditDim")?.addEventListener("change", () => this._saveLightEdit());
            document.getElementById("lightEditProvidesVision")?.addEventListener("change", () => this._saveLightEdit());
            document.getElementById("btnLightDelete")?.addEventListener("click", () => this._deleteSelectedLight());
            lightEditPopover?.addEventListener("keydown", (event) => {
                if (event.key === "Escape") {
                    event.preventDefault();
                    this._closeLightEditPopover();
                }
            });

            document.getElementById("btnTokenSightRangeSet")?.addEventListener("click", () => this._setSelectedTokenSightRange());

            const visibleTokensPopover = document.getElementById("visibleTokensPopover");
            document.getElementById("btnTokenVisible")?.addEventListener("click", () => this._showVisibleTokensForSelected());
            document.getElementById("btnVisibleTokensClose")?.addEventListener("click", () => { if (visibleTokensPopover) visibleTokensPopover.hidden = true; });
            visibleTokensPopover?.addEventListener("keydown", (event) => {
                if (event.key === "Escape") {
                    event.preventDefault();
                    visibleTokensPopover.hidden = true;
                }
            });

            document.getElementById("btnFogEnabledToggle")?.addEventListener("click", () => this._toggleFogEnabled());
            document.getElementById("btnFogReset")?.addEventListener("click", () => this._resetFogOfWar());

            this._bindFocusTrap(wallEditPopover);
            this._bindFocusTrap(lightEditPopover);
            this._bindFocusTrap(visibleTokensPopover);
        },
async _bindMapLibrary() {
            // DM composition only: this module is never requested for a Player seat.
            const button = document.getElementById("layerAddLibrary");
            if (!button || this._mapLibraryBound) return;
            this._mapLibraryBound = true;
            button.addEventListener("click", async () => {
                try {
                    const module = await import("/static/js/play-map-library.js");
                    module.mount(this).open();
                    const choice = document.getElementById("layerAddChoice");
                    if (choice) choice.hidden = true;
                } catch (error) {
                    this._showMessage(globalThis.VTTUi("Die Kartenbibliothek konnte nicht geladen werden."), true);
                }
            });
        },
_bindTokenClipboard() {
            // DM only: marquee-select tokens with a left drag in the select tool, Ctrl/Cmd+C copies the
            // selection, Ctrl/Cmd+V pastes fresh copies at the pointer with the same layout.
            if (this._tokenClipboardBound) return;
            const viewport = document.getElementById("mapViewport");
            const world = document.getElementById("mapWorld");
            if (!viewport || !world) return;
            this._tokenClipboardBound = true;
            let marquee = null;
            let swallowClick = false;
            const box = (a, b) => ({ x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y) });
            // The selection strip is a sibling over the map. Keep keyboard paste at
            // the pointer even when that strip receives the pointermove event.
            window.addEventListener("pointermove", (event) => {
                const rect = viewport.getBoundingClientRect();
                const overMap = event.clientX >= rect.left && event.clientX < rect.right
                    && event.clientY >= rect.top && event.clientY < rect.bottom;
                this._pasteAnchor = overMap ? this._worldPointFromEvent(event) : null;
            });
            viewport.addEventListener("pointerdown", (event) => {
                if (event.pointerType === "touch" || this._mapTouchGesture || this.currentTool !== "select" || event.button !== 0 || this.readOnly || this._pendingTarget) return;
                if (event.target.closest?.(".token-marker, .floating, .stage-topbar, .vision-light-marker, .vision-wall-line, button, input, select, textarea, a")) return;
                const start = this._worldPointFromEvent(event);
                if (!start) return;
                const element = document.createElement("div");
                element.className = "token-marquee";
                element.hidden = true;
                world.append(element);
                marquee = { start, end: null, element, clientX: event.clientX, clientY: event.clientY, moved: false };
            });
            viewport.addEventListener("vtt:cancel-map-gesture", () => {
                marquee?.element.remove();
                marquee = null;
                swallowClick = false;
            });
            window.addEventListener("pointermove", (event) => {
                if (!marquee) return;
                if (!marquee.moved && Math.hypot(event.clientX - marquee.clientX, event.clientY - marquee.clientY) < 5) return;
                const point = this._worldPointFromEvent(event);
                if (!point) return;
                marquee.moved = true;
                marquee.end = point;
                const r = box(marquee.start, point);
                Object.assign(marquee.element.style, { left: `${r.x}px`, top: `${r.y}px`, width: `${r.w}px`, height: `${r.h}px` });
                marquee.element.hidden = false;
            });
            window.addEventListener("pointerup", () => {
                if (!marquee) return;
                const done = marquee;
                marquee = null;
                done.element.remove();
                if (!done.moved || !done.end) return;
                swallowClick = true;  // the click after a drag must not clear the new selection
                const r = box(done.start, done.end);
                const ids = [...world.querySelectorAll(".token-marker[data-token-id]")].filter((marker) => {
                    const left = Number(marker.dataset.tokenLeft), top = Number(marker.dataset.tokenTop);
                    const size = Number(marker.dataset.tokenSize) || 0;
                    return left < r.x + r.w && left + size > r.x && top < r.y + r.h && top + size > r.y;
                }).map((marker) => Number(marker.dataset.tokenId))
                    .filter((id) => this._isTokenOnActiveLayer(this._findStateToken(id)));
                this._selectToken(ids.length ? ids[0] : null);
                this.selectedTokenIds = ids.length > 1 ? new Set(ids) : null;
                this._syncTokenMarkerSelection();
                if (ids.length > 1) this._showMessage(globalThis.VTTUi("{p0} Tokens ausgewählt. Strg+C kopiert, Strg+V fügt an der Mausposition ein.", { p0: ids.length }));
            });
            viewport.addEventListener("click", (event) => {
                if (!swallowClick) return;
                swallowClick = false;
                event.stopPropagation();
                event.preventDefault();
            }, true);
            document.addEventListener("keydown", (event) => {
                if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey || event.repeat) return;
                const key = event.key.toLowerCase();
                if (key !== "c" && key !== "v") return;
                if (event.target.closest?.("input, textarea, select, [contenteditable]")) return;
                if (key === "c") {
                    // Selected page text keeps the browser's own copy.
                    if (String(window.getSelection?.() || "").trim()) return;
                    if (this._copySelectedTokens()) event.preventDefault();
                } else if (this._tokenClipboard?.items.length) {
                    event.preventDefault();
                    this._pasteTokens();
                }
            });
        },
_copySelectedTokens() {
            const ids = this.selectedTokenIds?.size ? [...this.selectedTokenIds]
                : (this.selectedTokenId != null ? [Number(this.selectedTokenId)] : []);
            const items = [];
            for (const id of ids) {
                const token = this._findStateToken(id);
                const marker = document.querySelector(`.token-marker[data-token-id="${id}"]`);
                if (!token || !marker || !this._isTokenOnActiveLayer(token)) continue;
                items.push({ token, left: Number(marker.dataset.tokenLeft) || 0, top: Number(marker.dataset.tokenTop) || 0 });
            }
            if (!items.length) return false;
            const minLeft = Math.min(...items.map((item) => item.left));
            const minTop = Math.min(...items.map((item) => item.top));
            this._tokenClipboard = {
                pastes: 0,
                origin: { x: minLeft, y: minTop },
                items: items.map(({ token, left, top }) => {
                    // A fresh copy: no conditions, turn marker or character link; full hit points.
                    const copy = {
                        name: token.name,
                        token_type: token.token_type || "npc",
                        size: Math.max(1, Number(token.size) || 1),
                        rotation: Number(token.rotation) || 0,
                        visibility: this._activeTokenLayer,
                        metadata_json: token.metadata_json?.image_url ? { image_url: token.metadata_json.image_url } : {},
                    };
                    if (token.hp_max != null) { copy.hp_max = Number(token.hp_max); copy.hp_current = Number(token.hp_max); }
                    else if (token.hp_current != null) copy.hp_current = Number(token.hp_current);
                    if (copy.token_type === "player" && token.owner_user_id != null) copy.owner_user_id = Number(token.owner_user_id);
                    return { dx: left - minLeft, dy: top - minTop, copy };
                }),
            };
            this._showMessage(globalThis.VTTUi("{p0} Token kopiert. Mit Strg+V an der Mausposition einfügen.", { p0: items.length }));
            this._renderTokenSelection();
            return true;
        },
_nextTokenName(name, taken) {
            // "Goblin" -> "Goblin 2", "Goblin 3": copies stay distinguishable in the turn order.
            const base = String(name || "").trim().replace(/\s+\d+$/, "") || "Token";
            let highest = 0;
            for (const existing of taken) {
                if (existing === base) highest = Math.max(highest, 1);
                const match = existing.startsWith(base + " ") ? /^\d+$/.exec(existing.slice(base.length + 1)) : null;
                if (match) highest = Math.max(highest, Number(match[0]));
            }
            const next = `${base} ${Math.max(2, highest + 1)}`;
            taken.add(next);
            return next;
        },
async _pasteTokens() {
            const clip = this._tokenClipboard;
            if (!clip?.items.length) return;
            if (this.readOnly) {
                this._showMessage(globalThis.VTTUi("Im Nur-Lesen-Modus können keine Tokens eingefügt werden."), true);
                return;
            }
            const grid = Math.max(16, Number(document.getElementById("mapWorld")?.dataset?.gridSize
                || this.bootstrap?.state_payload?.active_map?.grid_size) || 70);
            clip.pastes += 1;
            // At the pointer when it is over the map, otherwise one square further for every paste.
            const anchor = this._pasteAnchor || { x: clip.origin.x + grid * clip.pastes, y: clip.origin.y + grid * clip.pastes };
            const ax = Math.round(anchor.x / grid) * grid;
            const ay = Math.round(anchor.y / grid) * grid;
            const { width, height } = this._worldSize();
            const taken = new Set(this._visibleTokens().map((token) => String(token.name || "")));
            let created = 0;
            try {
                for (const { dx, dy, copy } of clip.items) {
                    const size = copy.size * grid;
                    const token = {
                        ...copy,
                        visibility: this._activeTokenLayer,
                        name: this._nextTokenName(copy.name, taken),
                        x: Math.round(Math.max(0, Math.min(Math.max(0, width - size), ax + dx))),
                        y: Math.round(Math.max(0, Math.min(Math.max(0, height - size), ay + dy))),
                        metadata_json: { ...copy.metadata_json, position_mode: "pixel" },
                    };
                    if (this.socket && this.socket.isConnected) this.socket.createToken(token);
                    else await this.api.createToken(this.campaignId, this.sessionId, token);
                    created += 1;
                }
                if (!(this.socket && this.socket.isConnected)) await this.loadBootstrap();
                this._showMessage(globalThis.VTTUi("{p0} Token eingefügt.", { p0: created }));
            } catch (error) {
                this._showMessage(error.message || globalThis.VTTUi("Eingefügte Tokens konnten nicht erstellt werden."), true);
                await this.loadBootstrap();
            }
        },
_bindMapUpload() {
            // Der Upload wird aus dem Hinzufügen-Dialog heraus gestartet
            // (#layerAddUpload in _renderLayerAddControl); hier hängt nur
            // noch der Datei-Handler am versteckten Input.
            const fileInput = document.getElementById("mapUploadFile");
            if (!fileInput) return;
            fileInput.addEventListener("change", async () => {
                const file = fileInput.files && fileInput.files[0];
                fileInput.value = "";
                if (!file) return;
                await this._uploadMapFromTable(file);
            });
        }
    }
};
