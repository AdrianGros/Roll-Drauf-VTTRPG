// Loaded only by the server-authorized DM composition. Visibility remains server enforced.
window.PlayTokenLayersDM = {
    mount(ui) {
        for (const [name, method] of Object.entries(this.methods)) ui[name] = method.bind(ui);
        ui._activeTokenLayer = "public";
        ui._dmDockEntries = [["tokenLayersWidget", VTTUi("Layers")]];
        const style = document.createElement("link");
        style.rel = "stylesheet";
        style.href = "/static/css/play-token-layers-dm.css";
        document.head.append(style);
        const widget = document.createElement("section");
        widget.id = "tokenLayersWidget";
        widget.className = "floating token-layers-widget";
        widget.innerHTML = `<h3 class="widget-toggle">${VTTUiHTML("Layers")}</h3>
            <div class="token-layer-choices" role="group" aria-label="${VTTUiHTML("Token-Layer")}">
                <button type="button" class="mini-btn" data-token-layer="public" aria-pressed="true">${VTTUiHTML("Player-Layer")} <span data-layer-count="public">0</span></button>
                <button type="button" class="mini-btn" data-token-layer="dm_only" aria-pressed="false">${VTTUiHTML("Dungeon-Master-Layer")} <span data-layer-count="dm_only">0</span></button>
            </div>
            <p class="muted" id="tokenLayerHint"></p>`;
        const bar = document.createElement("section");
        bar.id = "tokenSelectionBar";
        bar.className = "token-selection-bar";
        bar.hidden = true;
        bar.setAttribute("aria-label", VTTUi("Token-Auswahl"));
        bar.innerHTML = `<strong id="tokenSelectionCount" role="status" aria-live="polite"></strong>
            <div id="tokenSelectionGroups" class="token-selection-groups"></div>
            <div class="token-selection-actions">
                <button type="button" class="mini-btn" data-selection-layer="public">${VTTUiHTML("Spielern zeigen")}</button>
                <button type="button" class="mini-btn" data-selection-layer="dm_only">${VTTUiHTML("Vor Spielern verbergen")}</button>
                <button type="button" class="mini-btn secondary" id="tokenSelectionClear">${VTTUiHTML("Auswahl aufheben")}</button>
            </div>`;
        document.querySelector(".stage").append(widget, bar);
        widget.querySelectorAll("[data-token-layer]").forEach(button => {
            button.addEventListener("click", () => ui._setTokenLayer(button.dataset.tokenLayer));
        });
        bar.querySelectorAll("[data-selection-layer]").forEach(button => {
            button.addEventListener("click", () => ui._moveTokenSelection(button.dataset.selectionLayer));
        });
        document.getElementById("tokenSelectionClear").addEventListener("click", () => ui._selectToken(null));
    },
    methods: {
        _isTokenOnActiveLayer(token) {
            return Boolean(token) && (token.visibility === "dm_only" ? "dm_only" : "public") === this._activeTokenLayer;
        },
        _setTokenLayer(layer) {
            if (!["public", "dm_only"].includes(layer) || this._movingTokenSelection) return;
            this._activeTokenLayer = layer;
            this._cancelTokenPlacement();
            this._selectToken(null, true);
            this._refreshTokenLayerView();
        },
        _toggleTokenGroup(token) {
            if (this._pendingTarget || !this._isTokenOnActiveLayer(token)) return false;
            const ids = this.selectedTokenIds || new Set(this.selectedTokenId == null ? [] : [Number(this.selectedTokenId)]);
            const id = Number(token.id);
            if (ids.has(id)) ids.delete(id); else ids.add(id);
            this.selectedTokenId = ids.size ? [...ids][0] : null;
            this.selectedTokenIds = ids.size > 1 ? ids : null;
            this._renderState();
            this._syncTokenMarkerSelection();
            return true;
        },
        _selectedLayerTokens() {
            const ids = this.selectedTokenIds?.size ? this.selectedTokenIds
                : new Set(this.selectedTokenId == null ? [] : [Number(this.selectedTokenId)]);
            return this._visibleTokens().filter(token => ids.has(Number(token.id)) && this._isTokenOnActiveLayer(token));
        },
        _refreshTokenLayerView() {
            const tokens = this._visibleTokens();
            for (const button of document.querySelectorAll("[data-token-layer]")) {
                button.setAttribute("aria-pressed", String(button.dataset.tokenLayer === this._activeTokenLayer));
                button.disabled = Boolean(this._movingTokenSelection);
            }
            for (const layer of ["public", "dm_only"]) {
                document.querySelector(`[data-layer-count="${layer}"]`).textContent = String(tokens.filter(token => (token.visibility === "dm_only" ? "dm_only" : "public") === layer).length);
            }
            document.getElementById("tokenLayerHint").textContent = this._activeTokenLayer === "dm_only"
                ? VTTUi("Neue Tokens sind nur für die Spielleitung sichtbar. Auswahlrahmen oder Umschalt-Klick wählt mehrere Tokens.")
                : VTTUi("Neue Tokens sind für Spieler sichtbar. Auswahlrahmen oder Umschalt-Klick wählt mehrere Tokens.");
            this._renderTokenSelection();
        },
        _renderTokenSelection() {
            const bar = document.getElementById("tokenSelectionBar");
            if (!bar) return;
            const selected = this._selectedLayerTokens();
            const valid = new Set(selected.map(token => Number(token.id)));
            if (this.selectedTokenIds) this.selectedTokenIds = valid.size > 1 ? valid : null;
            if (!valid.has(Number(this.selectedTokenId))) this.selectedTokenId = selected[0]?.id ?? null;
            bar.hidden = selected.length === 0;
            document.getElementById("tokenSelectionCount").textContent = VTTUi("{count} ausgewählt", { count: selected.length });
            const groups = new Map();
            for (const token of selected) {
                const image = String(token.metadata_json?.image_url || "");
                const name = String(token.name || token.token_type || "Token").trim().replace(/\s+\d+$/, "");
                const key = JSON.stringify([name, token.token_type, image]);
                if (!groups.has(key)) groups.set(key, { name, image, count: 0 });
                groups.get(key).count += 1;
            }
            const container = document.getElementById("tokenSelectionGroups");
            container.replaceChildren();
            for (const group of groups.values()) {
                const chip = document.createElement("div");
                chip.className = "token-selection-group";
                if (group.image.startsWith("/api/assets/")) {
                    const image = document.createElement("img");
                    image.src = group.image;
                    image.alt = "";
                    chip.append(image);
                } else {
                    const face = document.createElement("span");
                    face.className = "token-selection-face";
                    face.textContent = group.name.slice(0, 2).toUpperCase();
                    chip.append(face);
                }
                const label = document.createElement("span");
                label.textContent = `${group.name} × ${group.count}`;
                chip.append(label);
                container.append(chip);
            }
            bar.querySelectorAll("[data-selection-layer]").forEach(button => {
                button.disabled = this.readOnly || Boolean(this._movingTokenSelection) || !selected.some(token => token.visibility !== button.dataset.selectionLayer);
            });
        },
        async _moveTokenSelection(layer) {
            if (this.readOnly || this._movingTokenSelection || !["public", "dm_only"].includes(layer)) return;
            const tokens = this._selectedLayerTokens().filter(token => token.visibility !== layer);
            if (!tokens.length) return;
            this._movingTokenSelection = true;
            this._refreshTokenLayerView();
            let changed = 0;
            let failed = false;
            try {
                for (const token of tokens) {
                    await this.api.updateToken(this.campaignId, this.sessionId, token.id, Number(token.version || 1), { visibility: layer });
                    changed += 1;
                }
            } catch (error) {
                failed = true;
                this._showMessage(VTTUi("{count} Tokens geändert. Nicht alle Änderungen konnten gespeichert werden. Bitte Auswahl erneut prüfen.", { count: changed }), true);
            } finally {
                this._movingTokenSelection = false;
                this._activeTokenLayer = layer;
                this.selectedTokenId = null;
                this.selectedTokenIds = null;
                await this.loadBootstrap();
                this._refreshTokenLayerView();
            }
            if (!failed) this._showMessage(VTTUi("{count} Tokens in den gewählten Layer verschoben.", { count: changed }));
        },
    },
};
