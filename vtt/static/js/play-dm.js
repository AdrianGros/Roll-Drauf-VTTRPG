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
            slot.replaceWith(template.content.cloneNode(true));
        }
        for (const name of Object.keys(this.methods)) ui[name] = this.methods[name].bind(ui);
    },
    methods: {
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
_bindVisionControls() {
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
