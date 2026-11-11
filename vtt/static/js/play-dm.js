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
_bindSessionControls() {
            // DM layer only: these buttons exist only in a DM seat.
            document.getElementById("btnInitStack").addEventListener("click", async () => {
                try {
                    await this.api.initSceneStack(this.campaignId, this.sessionId);
                    this._showMessage("Kartenstapel initialisiert.");
                    await this.loadBootstrap();
                } catch (error) {
                    this._showMessage(error.message || "Kartenstapel konnte nicht initialisiert werden.", true);
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
                    const ok = window.confirm("Start-Check hat Warnungen. Trotzdem live starten?");
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
                const ok = window.confirm("Session wirklich beenden?");
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
