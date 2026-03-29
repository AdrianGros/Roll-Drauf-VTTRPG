(function () {
    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function normalizeRole(rawRole) {
        return String(rawRole || "").trim().toUpperCase();
    }

    function isOperatorRole(rawRole) {
        const role = normalizeRole(rawRole);
        return role === "DM" || role === "CO_DM";
    }

    class PlayRuntimeUI {
        constructor() {
            this.auth = new Auth();
            this.api = new PlayClient(this.auth);
            this.socket = null;
            this.campaignId = null;
            this.sessionId = null;
            this.user = null;
            this.bootstrap = null;
            this.mode = "waiting";
            this.readOnly = true;
            this.activityRows = [];
            this.chatRows = [];
            this.selectedTokenId = null;
            this.dragState = null;
            this.mapInteractionsBound = false;
            this.tokenIndex = new Map();
            this.currentTool = "select";
            this.zoomLevel = 100;
            this.activeSidebarTab = "tools";
        }

        async init() {
            const params = new URLSearchParams(window.location.search);
            this.campaignId = Number(params.get("campaign_id"));
            this.sessionId = Number(params.get("session_id"));
            if (!Number.isInteger(this.campaignId) || !Number.isInteger(this.sessionId)) {
                this._showMessage("campaign_id und session_id werden benoetigt.", true);
                return;
            }

            this.user = await this.auth.requireAuth("/login.html");
            if (!this.user) {
                return;
            }

            this._bindControls();
            await this.loadBootstrap();
            this._connectSocket();
        }

        async loadBootstrap() {
            try {
                const payload = await this.api.bootstrap(this.campaignId, this.sessionId);
                this.bootstrap = payload;
                this.mode = payload.mode || "waiting";
                this.readOnly = Boolean(payload.read_only);
                this._render();
            } catch (error) {
                this._showMessage(error.message || "Startdaten konnten nicht geladen werden.", true);
            }
        }

        _connectSocket() {
            this.socket = new PlaySocketRuntime({
                campaignId: this.campaignId,
                sessionId: this.sessionId,
                handlers: {
                    snapshot: (payload) => this._handleSnapshot(payload),
                    mode: (payload) => this._handleMode(payload),
                    stateChanged: (payload) => this._handleStateChanged(payload),
                    layerActivated: () => this.loadBootstrap(),
                    actionExecuted: (payload) => this._handleAction(payload),
                    diceRolled: (payload) => this._handleDiceBroadcast(payload),
                    chatMessageSent: (payload) => this._handleChatBroadcast(payload),
                    tokenCreated: (payload) => this._handleTokenCreated(payload),
                    tokenUpdated: (payload) => this._handleTokenUpdated(payload),
                    tokenDeleted: (payload) => this._handleTokenDeleted(payload),
                    tokenBatchMoved: (payload) => this._handleTokenBatchMoved(payload),
                    initiativeUpdated: (payload) => this._handleInitiativeUpdated(payload),
                    initiativeTurnChanged: (payload) => this._handleInitiativeTurnChanged(payload),
                    sessionPaused: (payload) => this._handleLifecycleBroadcast("paused", payload),
                    sessionResumed: (payload) => this._handleLifecycleBroadcast("resumed", payload),
                    sessionEnded: (payload) => this._handleLifecycleBroadcast("ended", payload),
                    conflict: (payload) => this._handleSocketConflict(payload),
                    duplicate: (payload) => this._logActivity(`Doppelte Socket-Aktion erkannt: ${payload?.client_event_id || "unknown"}.`, "info"),
                    resyncRequested: (payload) => this._logActivity(`Resync requested (${payload?.reason || "unknown"}).`, "info"),
                    staleEventDropped: (payload) =>
                        this._logActivity(
                            `Dropped stale event ${payload?.event_name || "unknown"} seq=${payload?.event_seq || "?"}.`,
                            "info"
                        ),
                    error: (payload) => this._showMessage(payload?.message || "Socket error", true),
                },
            });
            this.socket.connect();
            window.addEventListener("beforeunload", () => this.socket.disconnect());
        }

        _bindControls() {
            document.getElementById("btnBack").addEventListener("click", () => {
                window.location.href = `/campaigns?campaign_id=${this.campaignId}`;
            });

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

            document.getElementById("btnRoll").addEventListener("click", () => {
                if (this.readOnly || !this.socket) {
                    this._showMessage("Nur-Lesen aktiv: Wuerfeln ist gesperrt.", true);
                    return;
                }
                const dice = document.getElementById("diceInput").value.trim() || "1d20";
                this.socket.rollDice(dice, this.user?.username || "player", (result) => {
                    const target = document.getElementById("diceResult");
                    if (result?.error) {
                        target.textContent = `Fehler: ${result.error}`;
                        return;
                    }
                    const rolls = Array.isArray(result?.rolls) ? result.rolls.join(",") : "-";
                    target.textContent = `${dice} -> ${result.total} (${rolls})`;
                });
            });

            const btnClearSelection = document.getElementById("btnClearSelection");
            if (btnClearSelection) {
                btnClearSelection.addEventListener("click", () => {
                    this.selectedTokenId = null;
                    this._renderMapCanvas();
                    this._renderTokenSelectors();
                });
            }

            document.getElementById("btnExecuteAction").addEventListener("click", async () => {
                if (this.readOnly) {
                    this._showMessage("Nur-Lesen aktiv: Aktion ist gesperrt.", true);
                    return;
                }
                const tokenId = Number(document.getElementById("actionTokenId").value);
                const actionCode = document.getElementById("actionCode").value;
                const targetRaw = document.getElementById("actionTargetTokenId").value;
                const targetTokenId = targetRaw ? Number(targetRaw) : null;

                if (!Number.isInteger(tokenId) || tokenId <= 0) {
                    this._showMessage("Bitte einen gueltigen Token waehlen.", true);
                    return;
                }
                if (!actionCode) {
                    this._showMessage("Bitte zuerst eine Aktion waehlen.", true);
                    return;
                }
                if (targetTokenId !== null && (!Number.isInteger(targetTokenId) || targetTokenId <= 0)) {
                    this._showMessage("Ungueltiger Ziel-Token.", true);
                    return;
                }
                try {
                    const payload = await this.api.executeAction(
                        this.campaignId,
                        this.sessionId,
                        tokenId,
                        actionCode,
                        targetTokenId
                    );
                    this._showMessage(`Aktion ausgefuehrt: ${payload.result.action_code}`);
                } catch (error) {
                    this._showMessage(error.message || "Aktion fehlgeschlagen.", true);
                }
            });

            this._bindWorkspaceControls();
        }

        _bindWorkspaceControls() {
            document.querySelectorAll(".sidebar-tab").forEach((button) => {
                button.addEventListener("click", () => {
                    const tab = button.getAttribute("data-tab") || "tools";
                    this._activateSidebarTab(tab);
                });
            });
            this._activateSidebarTab(this.activeSidebarTab);

            document.querySelectorAll(".tool-btn[data-tool]").forEach((button) => {
                button.addEventListener("click", () => {
                    const tool = button.getAttribute("data-tool") || "select";
                    this._setTool(tool);
                });
            });

            const zoomOut = document.getElementById("btnZoomOut");
            const zoomIn = document.getElementById("btnZoomIn");
            const zoomReset = document.getElementById("btnZoomReset");
            const zoomRange = document.getElementById("zoomRange");
            if (zoomOut) zoomOut.addEventListener("click", () => this._setZoom(this.zoomLevel - 10));
            if (zoomIn) zoomIn.addEventListener("click", () => this._setZoom(this.zoomLevel + 10));
            if (zoomReset) zoomReset.addEventListener("click", () => this._setZoom(100));
            if (zoomRange) {
                zoomRange.addEventListener("input", () => {
                    this._setZoom(Number(zoomRange.value || 100));
                });
            }
            this._setZoom(this.zoomLevel);

            const sendChat = () => {
                const input = document.getElementById("chatInput");
                if (!input) return;
                const text = String(input.value || "").trim();
                if (!text) return;
                const useSocket = Boolean(this.socket && this.socket.isConnected);
                if (useSocket) {
                    this.socket.sendChat(text, this.user?.username || "player", this.user?.id || null);
                } else {
                    const time = new Date().toISOString().slice(11, 19);
                    this._appendChatMessage({
                        time,
                        sender_name: this.user?.username || "player",
                        message: text,
                    });
                    this._logActivity(`Chat: ${text}`, "info");
                }
                input.value = "";
            };

            const btnSendChat = document.getElementById("btnSendChat");
            if (btnSendChat) btnSendChat.addEventListener("click", sendChat);
            const chatInput = document.getElementById("chatInput");
            if (chatInput) {
                chatInput.addEventListener("keydown", (event) => {
                    if (event.key === "Enter") {
                        event.preventDefault();
                        sendChat();
                    }
                });
            }
        }

        _activateSidebarTab(tabName) {
            this.activeSidebarTab = tabName;
            document.querySelectorAll(".sidebar-tab").forEach((button) => {
                const isActive = button.getAttribute("data-tab") === tabName;
                button.classList.toggle("active", isActive);
            });
            document.querySelectorAll(".tab-panel").forEach((panel) => {
                const isActive = panel.id === `panel-${tabName}`;
                panel.classList.toggle("active", isActive);
            });
        }

        _setTool(toolName) {
            this.currentTool = toolName;
            document.querySelectorAll(".tool-btn[data-tool]").forEach((button) => {
                const isActive = button.getAttribute("data-tool") === toolName;
                button.classList.toggle("active", isActive);
            });
            this._logActivity(`Werkzeug gewechselt: ${toolName}`, "info");
        }

        _setZoom(nextZoom) {
            const clamped = Math.max(50, Math.min(200, Math.round(Number(nextZoom) || 100)));
            this.zoomLevel = clamped;
            const world = document.getElementById("mapWorld");
            const zoomLabel = document.getElementById("zoomLabel");
            const zoomRange = document.getElementById("zoomRange");
            if (world) world.style.transform = `scale(${clamped / 100})`;
            if (zoomLabel) zoomLabel.textContent = `${clamped}%`;
            if (zoomRange) zoomRange.value = String(clamped);
        }

        async _runReadyCheck() {
            try {
                const result = await this.api.readyCheck(this.campaignId, this.sessionId);
                const node = document.getElementById("readyCheckOutput");
                const blockers = Array.isArray(result.blocking_issues) ? result.blocking_issues : [];
                const warnings = Array.isArray(result.warnings) ? result.warnings : [];

                const blockHtml = blockers.length
                    ? blockers.map((issue) => `<div class="ready-block">${escapeHtml(issue)}</div>`).join("")
                    : "<div class='ready-ok'>Keine Blocker.</div>";
                const warnHtml = warnings.length
                    ? warnings.map((issue) => `<div class="ready-warn">${escapeHtml(issue)}</div>`).join("")
                    : "<div class='ready-ok'>Keine Warnungen.</div>";

                node.innerHTML = `
                    <div><strong>Kann starten:</strong> ${result.can_start ? "ja" : "nein"}</div>
                    <div style="margin-top:0.45rem;"><strong>Blocker</strong></div>
                    ${blockHtml}
                    <div style="margin-top:0.45rem;"><strong>Warnungen</strong></div>
                    ${warnHtml}
                `;

                this._logActivity(`Start-Check ausgefuehrt (startbar=${result.can_start ? "ja" : "nein"}).`, "info");
                return result;
            } catch (error) {
                this._showMessage(error.message || "Start-Check fehlgeschlagen.", true);
                return null;
            }
        }

        async _transition(targetState, ignoreWarnings = false) {
            try {
                const payload = await this.api.transition(this.campaignId, this.sessionId, targetState, ignoreWarnings);
                this.mode = payload.mode;
                this.readOnly = Boolean(payload.read_only);
                const runtimeStatus = payload.session.runtime_status || payload.session.status;
                this._showMessage(`Session-Status: ${runtimeStatus}`);
                this._logActivity(`Statuswechsel angewendet: ${runtimeStatus}.`, "info");
                if (this.socket) this.socket.requestState();
                await this.loadBootstrap();
            } catch (error) {
                this._showMessage(error.message || "Statuswechsel fehlgeschlagen.", true);
            }
        }

        _handleSnapshot(payload) {
            if (!this.bootstrap) return;
            this.bootstrap.state_payload = payload;
            this._renderState();
            this._renderMapCanvas();
            this._renderTurnOrder();
            this._renderTokenSelectors();
            this._renderChat();
        }

        _handleMode(payload) {
            this.mode = payload?.mode || this.mode;
            this._renderMeta();
        }

        _handleStateChanged(payload) {
            this._showMessage(`Statuswechsel: ${payload.previous_state} -> ${payload.target_state}`);
            this._logActivity(`Status geaendert zu ${payload.target_state}.`, "info");
            this.loadBootstrap();
        }

        _handleAction(payload) {
            const result = payload?.result;
            if (!result) return;
            this._showMessage(`Aktions-Event: ${result.action_code}`);
            this._logActivity(`Aktions-Event: ${result.action_code}.`, "info");
        }

        _handleChatBroadcast(payload) {
            this._appendChatMessage({
                time: String(payload?.timestamp || new Date().toISOString()).slice(11, 19),
                sender_name: payload?.sender_name || payload?.sender || "player",
                message: payload?.message || "",
            });
            this._logActivity(`Chat von ${payload?.sender_name || "player"} empfangen.`, "info");
        }

        _handleTokenCreated(payload) {
            const token = payload?.token;
            if (!token) return;
            this._upsertStateToken(token);
            this._renderState();
            this._renderMapCanvas();
            this._renderTurnOrder();
            this._renderTokenSelectors();
            this._logActivity(`Token erstellt: ${token.name}.`, "info");
        }

        _handleTokenUpdated(payload) {
            const token = payload?.token;
            if (!token) return;
            this._upsertStateToken(token);
            this._renderState();
            this._renderMapCanvas();
            this._renderTurnOrder();
            this._renderTokenSelectors();
            this._logActivity(`Token aktualisiert: ${token.name}.`, "info");
        }

        _handleTokenDeleted(payload) {
            const tokenId = Number(payload?.token_id);
            if (!Number.isInteger(tokenId)) return;
            this._removeStateToken(tokenId);
            if (Number(this.selectedTokenId) === tokenId) {
                this.selectedTokenId = null;
            }
            this._renderState();
            this._renderMapCanvas();
            this._renderTurnOrder();
            this._renderTokenSelectors();
            this._logActivity(`Token geloescht: #${tokenId}.`, "info");
        }

        _handleTokenBatchMoved(payload) {
            const moves = Array.isArray(payload?.moves) ? payload.moves : [];
            if (!moves.length) return;
            for (const move of moves) {
                const token = this._findStateToken(move.token_id);
                if (token) {
                    const nextX = Number(move.x);
                    const nextY = Number(move.y);
                    if (Number.isFinite(nextX)) token.x = nextX;
                    if (Number.isFinite(nextY)) token.y = nextY;
                }
            }
            this._renderMapCanvas();
            this._renderState();
            this._renderTokenSelectors();
            this._logActivity(`Tokenbewegung synchronisiert (${moves.length}).`, "info");
        }

        _handleInitiativeUpdated(payload) {
            const initiative = Array.isArray(payload?.initiative) ? payload.initiative : [];
            this.bootstrap = this.bootstrap || {};
            this.bootstrap.state_payload = this.bootstrap.state_payload || {};
            this.bootstrap.state_payload.initiative = initiative;
            this._renderTurnOrder();
            this._logActivity("Initiative aktualisiert.", "info");
        }

        _handleInitiativeTurnChanged(payload) {
            const currentTurn = payload?.current_turn || null;
            this.bootstrap = this.bootstrap || {};
            this.bootstrap.state_payload = this.bootstrap.state_payload || {};
            this.bootstrap.state_payload.current_turn = currentTurn;
            this._renderTurnOrder();
            this._logActivity("Turn Order weiterschaltet.", "info");
        }

        _handleLifecycleBroadcast(stateName, payload) {
            const session = payload?.session;
            if (session) {
                this.bootstrap = this.bootstrap || {};
                this.bootstrap.session = session;
                this.mode = payload?.mode || this.mode;
                this.readOnly = Boolean(payload?.read_only ?? this.readOnly);
                this._renderMeta();
                this._renderFirstSteps();
            }
            this._logActivity(`Session-Status: ${stateName}.`, "info");
        }

        _handleSocketConflict(payload) {
            const tokenId = payload?.token_id || payload?.character_id || "unknown";
            this._showMessage(`Konflikt bei Token ${tokenId}. Bitte Ansicht neu laden.`, true);
            this._logActivity("Socket-Konflikt erkannt, Ansicht wird neu synchronisiert.", "error");
            this.loadBootstrap();
        }

        _handleDiceBroadcast(payload) {
            const log = document.getElementById("diceLog");
            const line = document.createElement("div");
            line.textContent = `${payload.player || "player"} hat ${payload.dice} gewuerfelt: ${payload.result?.total}`;
            log.prepend(line);
            while (log.children.length > 8) {
                log.removeChild(log.lastChild);
            }
            this._logActivity(`${payload.player || "player"} hat ${payload.dice} gewuerfelt.`, "info");
        }

        _render() {
            this._renderMeta();
            this._renderLayers();
            this._renderActions();
            this._renderState();
            this._renderMapCanvas();
            this._renderTurnOrder();
            this._renderTokenSelectors();
            this._renderChat();
            this._renderActivity();
            this._renderFirstSteps();
        }

        _renderMeta() {
            const campaignName = this.bootstrap?.campaign?.name || `Campaign ${this.campaignId}`;
            const sessionName = this.bootstrap?.session?.name || `Session ${this.sessionId}`;
            const role = this.bootstrap?.session_role || "-";

            document.getElementById("sessionTitle").textContent = `${campaignName} / ${sessionName}`;
            document.getElementById("modeBadge").textContent = this.mode;
            document.getElementById("roleBadge").textContent = role;
            document.getElementById("readOnlyBadge").textContent = this.readOnly ? "nur lesen" : "interaktiv";
            const statusPill = document.getElementById("sessionStatusPill");
            if (statusPill) {
                statusPill.textContent = String(this.bootstrap?.session?.runtime_status || this.bootstrap?.session?.status || "-");
            }

            const notice = document.getElementById("readOnlyNotice");
            if (this.readOnly) {
                notice.className = "message info";
                notice.textContent = "Nur-Lesen ist aktiv fuer deine Rolle oder den Session-Status.";
            } else {
                notice.className = "message";
                notice.textContent = "";
            }

            this._syncControlState();
        }

        _syncControlState() {
            const role = this.bootstrap?.session_role || "";
            const sessionStatus = String(this.bootstrap?.session?.runtime_status || this.bootstrap?.session?.status || "scheduled");
            const canOperate = isOperatorRole(role);

            const btnInitStack = document.getElementById("btnInitStack");
            const btnReadyCheck = document.getElementById("btnReadyCheck");
            const btnToReady = document.getElementById("btnToReady");
            const btnStart = document.getElementById("btnStart");
            const btnPause = document.getElementById("btnPause");
            const btnResume = document.getElementById("btnResume");
            const btnEnd = document.getElementById("btnEnd");
            const btnExecute = document.getElementById("btnExecuteAction");
            const btnRoll = document.getElementById("btnRoll");

            btnInitStack.disabled = !canOperate || sessionStatus === "ended";
            btnReadyCheck.disabled = !canOperate || sessionStatus === "ended";
            btnToReady.disabled = !canOperate || sessionStatus !== "scheduled";
            btnStart.disabled = !canOperate || sessionStatus !== "ready";
            btnPause.disabled = !canOperate || sessionStatus !== "in_progress";
            btnResume.disabled = !canOperate || sessionStatus !== "paused";
            btnEnd.disabled = !canOperate || !(sessionStatus === "in_progress" || sessionStatus === "paused");

            btnExecute.disabled = this.readOnly || this.mode !== "live";
            btnRoll.disabled = this.readOnly || this.mode === "ended";
        }

        _renderLayers() {
            const stack = this.bootstrap?.scene_stack;
            const container = document.getElementById("layerList");
            if (!stack || !Array.isArray(stack.layers) || stack.layers.length === 0) {
                container.innerHTML = "<div class='muted'>Noch kein aktiver Kartenstapel.</div>";
                return;
            }

            container.innerHTML = stack.layers.map((layer) => {
                const isActive = Number(layer.id) === Number(stack.active_layer_id);
                const activateBtn = this.readOnly ? "" : `<button data-layer-id="${layer.id}" class="mini-btn">Aktivieren</button>`;
                const mapName = escapeHtml(layer.campaign_map?.name || `Map ${layer.campaign_map_id}`);
                return `
                    <div class="panel-row ${isActive ? "active-row" : ""}">
                        <div><strong>${escapeHtml(layer.label)}</strong> (${mapName})</div>
                        ${isActive ? "<span>aktiv</span>" : activateBtn}
                    </div>
                `;
            }).join("");

            container.querySelectorAll("button[data-layer-id]").forEach((button) => {
                button.addEventListener("click", async () => {
                    const layerId = Number(button.getAttribute("data-layer-id"));
                    try {
                        await this.api.activateLayer(this.campaignId, this.sessionId, layerId);
                        this._showMessage("Kartenebene aktiviert.");
                        this._logActivity(`Kartenebene ${layerId} aktiviert.`, "info");
                        await this.loadBootstrap();
                    } catch (error) {
                        this._showMessage(error.message || "Kartenebene konnte nicht gewechselt werden.", true);
                    }
                });
            });
        }

        _renderState() {
            const statePayload = this.bootstrap?.state_payload;
            const tokenList = document.getElementById("tokenList");
            const activeMap = statePayload?.active_map;
            document.getElementById("activeMapText").textContent = activeMap
                ? `${activeMap.name} (#${activeMap.id})`
                : "Keine aktive Karte";

            const tokens = statePayload?.tokens || [];
            if (!this._isTokenAvailable(this.selectedTokenId, tokens)) {
                this.selectedTokenId = null;
            }
            if (!tokens.length) {
                tokenList.innerHTML = "<div class='muted'>Keine Tokens im aktuellen Session-Status.</div>";
            } else {
                tokenList.innerHTML = tokens.map((token) => `
                    <div class="panel-row ${Number(this.selectedTokenId) === Number(token.id) ? "active-row" : ""}" data-token-id="${token.id}" style="cursor:pointer;">
                        <div><strong>${escapeHtml(token.name)}</strong> (${escapeHtml(token.token_type)})</div>
                        <div>HP ${token.hp_current ?? "-"} / ${token.hp_max ?? "-"}, Pos ${token.x},${token.y}</div>
                    </div>
                `).join("");
                tokenList.querySelectorAll(".panel-row[data-token-id]").forEach((row) => {
                    row.addEventListener("click", () => {
                        const tokenId = Number(row.getAttribute("data-token-id"));
                        if (Number.isInteger(tokenId)) {
                            this._selectToken(tokenId);
                        }
                    });
                });
            }

            const selectedSummary = document.getElementById("tokenSelectionSummary");
            const selectedToken = this._findStateToken(this.selectedTokenId);
            if (selectedSummary) {
                selectedSummary.textContent = selectedToken
                    ? `Ausgewaehlt: ${selectedToken.name} (#${selectedToken.id})`
                    : "Kein Token ausgewaehlt.";
            }

            const mapMetaText = document.getElementById("mapMetaText");
            if (mapMetaText) {
                if (!activeMap) {
                    mapMetaText.textContent = "Keine aktive Karte.";
                } else {
                    mapMetaText.textContent = `${activeMap.name} (${activeMap.width}x${activeMap.height}), Grid ${activeMap.grid_size || 32}px`;
                }
            }
        }

        _renderMapCanvas() {
            const statePayload = this.bootstrap?.state_payload || {};
            const activeMap = statePayload.active_map;
            const tokens = Array.isArray(statePayload.tokens) ? statePayload.tokens : [];
            const mapWorld = document.getElementById("mapWorld");
            const mapImage = document.getElementById("mapImage");
            const mapGrid = document.getElementById("mapGridLayer");
            const tokenLayer = document.getElementById("mapTokenLayer");
            if (!mapWorld || !mapImage || !mapGrid || !tokenLayer) return;

            const gridSize = Math.max(16, Number(activeMap?.grid_size) || 32);
            const width = Math.max(900, Number(activeMap?.width) || 1800);
            const height = Math.max(600, Number(activeMap?.height) || 1200);
            mapWorld.style.width = `${width}px`;
            mapWorld.style.height = `${height}px`;
            mapGrid.style.backgroundSize = `${gridSize}px ${gridSize}px`;
            mapWorld.dataset.gridSize = String(gridSize);
            mapWorld.dataset.mapWidth = String(width);
            mapWorld.dataset.mapHeight = String(height);
            mapWorld.dataset.hasMap = activeMap ? "true" : "false";

            const emptyState = document.getElementById("mapEmptyState");
            if (emptyState) {
                emptyState.style.display = activeMap ? "none" : "flex";
            }

            if (activeMap?.background_url) {
                mapImage.src = activeMap.background_url;
                mapImage.style.display = "block";
            } else {
                mapImage.removeAttribute("src");
                mapImage.style.display = "none";
            }

            this.tokenIndex = new Map(tokens.map((token) => [Number(token.id), token]));
            const initiativeEntries = this._getInitiativeEntries(tokens);
            const currentTurnTokenId = initiativeEntries.length ? Number(initiativeEntries[0].id) : null;
            tokenLayer.innerHTML = tokens.map((token) => {
                const position = this._resolveTokenPosition(token, gridSize);
                const pixelSize = this._resolveTokenSize(token, gridSize);
                const rawName = String(token.name || "");
                const label = escapeHtml(rawName);
                const initials = escapeHtml(rawName.trim().slice(0, 2).toUpperCase() || "??");
                const colorByType = {
                    player: "#8cc0ff",
                    npc: "#ffd27d",
                    monster: "#ff8e8e",
                    object: "#98d6b4",
                };
                const color = colorByType[String(token.token_type || "player").toLowerCase()] || "#8cc0ff";
                const selected = Number(this.selectedTokenId) === Number(token.id);
                const isCurrentTurn = currentTurnTokenId !== null && Number(token.id) === currentTurnTokenId;
                const canMove = this._canMoveToken(token);

                return `
                    <div
                        class="token-marker ${selected ? "selected" : ""} ${isCurrentTurn ? "current-turn" : ""} ${canMove ? "draggable" : ""}"
                        data-token-id="${token.id}"
                        data-token-version="${token.version ?? 1}"
                        data-token-left="${position.left}"
                        data-token-top="${position.top}"
                        data-token-size="${pixelSize}"
                        style="left:${position.left}px;top:${position.top}px;width:${pixelSize}px;height:${pixelSize}px;background:${color};"
                        title="${label}"
                    >
                        ${initials}
                        <div class="token-label">${label}</div>
                    </div>
                `;
            }).join("");
            this._bindMapInteractions();
        }

        _renderTurnOrder() {
            const container = document.getElementById("turnOrderList");
            const summary = document.getElementById("turnOrderSummary");
            if (!container) return;
            const tokens = Array.isArray(this.bootstrap?.state_payload?.tokens) ? this.bootstrap.state_payload.tokens : [];
            const entries = this._getInitiativeEntries(tokens);

            if (!entries.length) {
                container.innerHTML = "<div class='muted'>Noch keine Initiative-Werte.</div>";
                if (summary) summary.textContent = "Noch keine Initiative-Werte.";
                return;
            }

            const currentEntry = entries[0];
            if (summary) {
                summary.textContent = `Aktuell: ${currentEntry.name} (${currentEntry.initiative})`;
            }

            container.innerHTML = entries.map((token, index) => `
                <div class="turn-item ${index === 0 ? "current" : ""}">
                    <span>${escapeHtml(token.name)}${index === 0 ? " <strong>• aktuell</strong>" : ""}</span>
                    <span class="turn-score">${escapeHtml(token.initiative)}</span>
                </div>
            `).join("");
        }

        _renderChat() {
            const container = document.getElementById("chatLog");
            if (!container) return;
            if (!this.chatRows.length) {
                container.innerHTML = "Noch keine Chat-Nachrichten.";
                return;
            }
            container.innerHTML = this.chatRows.map((entry) => `
                <div class="chat-entry">
                    <div class="chat-meta">[${escapeHtml(entry.time)}] ${escapeHtml(entry.user || entry.sender_name || "player")}</div>
                    <div>${escapeHtml(entry.text || entry.message || "")}</div>
                </div>
            `).join("");
        }

        _appendChatMessage(entry) {
            const normalized = {
                time: String(entry?.time || new Date().toISOString()).slice(11, 19),
                user: entry?.user || entry?.sender_name || "player",
                sender_name: entry?.sender_name || entry?.user || "player",
                text: entry?.text || entry?.message || "",
                message: entry?.message || entry?.text || "",
            };
            this.chatRows.unshift(normalized);
            if (this.chatRows.length > 50) {
                this.chatRows = this.chatRows.slice(0, 50);
            }
            this._renderChat();
        }

        _findStateToken(tokenId, tokens = null) {
            const searchId = Number(tokenId);
            if (!Number.isInteger(searchId)) return null;
            const list = Array.isArray(tokens)
                ? tokens
                : Array.isArray(this.bootstrap?.state_payload?.tokens)
                    ? this.bootstrap.state_payload.tokens
                    : [];
            return list.find((token) => Number(token.id) === searchId) || null;
        }

        _upsertStateToken(token) {
            if (!token) return;
            this.bootstrap = this.bootstrap || {};
            this.bootstrap.state_payload = this.bootstrap.state_payload || {};
            const tokens = Array.isArray(this.bootstrap.state_payload.tokens) ? this.bootstrap.state_payload.tokens.slice() : [];
            const tokenId = Number(token.id);
            const index = tokens.findIndex((entry) => Number(entry.id) === tokenId);
            if (index >= 0) {
                tokens[index] = { ...tokens[index], ...token };
            } else {
                tokens.push(token);
            }
            this.bootstrap.state_payload.tokens = tokens;
            this.tokenIndex.set(tokenId, this._findStateToken(tokenId, tokens));
        }

        _removeStateToken(tokenId) {
            const searchId = Number(tokenId);
            this.bootstrap = this.bootstrap || {};
            this.bootstrap.state_payload = this.bootstrap.state_payload || {};
            const tokens = Array.isArray(this.bootstrap.state_payload.tokens) ? this.bootstrap.state_payload.tokens : [];
            this.bootstrap.state_payload.tokens = tokens.filter((entry) => Number(entry.id) !== searchId);
            this.tokenIndex.delete(searchId);
        }

        _isTokenAvailable(tokenId, tokens = null) {
            return Boolean(this._findStateToken(tokenId, tokens));
        }

        _canMoveToken(token) {
            if (!token) return false;
            if (this.readOnly) return false;
            if (isOperatorRole(this.bootstrap?.session_role || "")) return true;
            return Number(token.owner_user_id) === Number(this.user?.id);
        }

        _getInitiativeEntries(tokens = []) {
            const explicit = Array.isArray(this.bootstrap?.state_payload?.initiative) ? this.bootstrap.state_payload.initiative : [];
            if (explicit.length) {
                return explicit
                    .map((entry) => ({
                        id: Number(entry.character_id ?? entry.token_id ?? entry.id),
                        name: entry.character_name || entry.name || `#${entry.id}`,
                        initiative: Number(entry.initiative_roll ?? entry.initiative ?? 0),
                        is_current_turn: Boolean(entry.is_current_turn),
                    }))
                    .sort((a, b) => {
                        if (a.is_current_turn !== b.is_current_turn) return a.is_current_turn ? -1 : 1;
                        return Number(b.initiative) - Number(a.initiative);
                    });
            }

            return tokens
                .filter((token) => token && token.initiative !== null && token.initiative !== undefined && token.initiative !== "")
                .map((token) => ({
                    id: Number(token.id),
                    name: token.name,
                    initiative: Number(token.initiative),
                    is_current_turn: false,
                }))
                .sort((a, b) => Number(b.initiative) - Number(a.initiative) || Number(a.id) - Number(b.id));
        }

        _resolveTokenPosition(token, gridSize) {
            const rawX = Number(token?.x) || 0;
            const rawY = Number(token?.y) || 0;
            const positionMode = String(token?.metadata_json?.position_mode || "").trim().toLowerCase();
            const useGridCoordinates = positionMode === "grid" || (!positionMode && Math.abs(rawX) <= 300 && Math.abs(rawY) <= 300);
            return {
                left: useGridCoordinates ? rawX * gridSize : rawX,
                top: useGridCoordinates ? rawY * gridSize : rawY,
            };
        }

        _resolveTokenSize(token, gridSize) {
            const rawSize = Number(token?.size) || 1;
            if (rawSize <= 12) {
                return Math.max(gridSize, rawSize * gridSize);
            }
            return rawSize;
        }

        _selectToken(tokenId, repaintMap = false) {
            const searchId = Number(tokenId);
            if (!Number.isInteger(searchId)) {
                this.selectedTokenId = null;
            } else {
                this.selectedTokenId = searchId;
            }
            const token = this._findStateToken(this.selectedTokenId);
            const actorSelect = document.getElementById("actionTokenId");
            if (actorSelect && token) {
                actorSelect.value = String(token.id);
            }
            this._renderState();
            this._syncTokenMarkerSelection();
            if (repaintMap) {
                this._renderMapCanvas();
            }
        }

        _syncTokenMarkerSelection() {
            const markers = document.querySelectorAll(".token-marker[data-token-id]");
            markers.forEach((marker) => {
                const tokenId = Number(marker.getAttribute("data-token-id"));
                marker.classList.toggle("selected", Number(this.selectedTokenId) === tokenId);
            });
        }

        _bindMapInteractions() {
            const tokenLayer = document.getElementById("mapTokenLayer");
            if (!tokenLayer || this.mapInteractionsBound) return;

            tokenLayer.addEventListener("pointerdown", (event) => {
                const marker = event.target.closest?.(".token-marker");
                if (!marker) {
                    return;
                }
                const tokenId = Number(marker.getAttribute("data-token-id"));
                const token = this._findStateToken(tokenId);
                if (!token) return;

                this._selectToken(tokenId, false);
                const canMove = this._canMoveToken(token);
                if (!canMove || !this.socket) {
                    return;
                }

                event.preventDefault();
                event.stopPropagation();

                const baseLeft = Number(marker.getAttribute("data-token-left")) || 0;
                const baseTop = Number(marker.getAttribute("data-token-top")) || 0;
                const baseVersion = Number(marker.getAttribute("data-token-version")) || Number(token.version || 1);
                const gridSize = Number(document.getElementById("mapWorld")?.dataset?.gridSize || this.bootstrap?.state_payload?.active_map?.grid_size || 32);
                const world = document.getElementById("mapWorld");
                const scale = this.zoomLevel / 100;
                const worldRect = world?.getBoundingClientRect();

                if (!worldRect) return;

                const pointerX = (event.clientX - worldRect.left) / scale;
                const pointerY = (event.clientY - worldRect.top) / scale;
                const dragOffsetX = pointerX - baseLeft;
                const dragOffsetY = pointerY - baseTop;

                marker.classList.add("dragging");
                this.dragState = {
                    tokenId,
                    baseVersion,
                    baseLeft,
                    baseTop,
                    dragOffsetX,
                    dragOffsetY,
                    gridSize: Math.max(16, Number(gridSize) || 32),
                    marker,
                    moved: false,
                    pointerId: event.pointerId,
                };
                if (marker.setPointerCapture) {
                    try {
                        marker.setPointerCapture(event.pointerId);
                    } catch (_error) {
                        /* ignore pointer capture errors */
                    }
                }
            });

            tokenLayer.addEventListener("click", (event) => {
                const marker = event.target.closest?.(".token-marker");
                if (!marker) {
                    this._selectToken(null);
                }
            });

            window.addEventListener("pointermove", (event) => {
                if (!this.dragState) return;
                const world = document.getElementById("mapWorld");
                const worldRect = world?.getBoundingClientRect();
                if (!worldRect) return;
                const scale = this.zoomLevel / 100;
                const contentX = (event.clientX - worldRect.left) / scale;
                const contentY = (event.clientY - worldRect.top) / scale;
                const rawLeft = contentX - this.dragState.dragOffsetX;
                const rawTop = contentY - this.dragState.dragOffsetY;
                const snappedLeft = Math.max(0, Math.round(rawLeft / this.dragState.gridSize) * this.dragState.gridSize);
                const snappedTop = Math.max(0, Math.round(rawTop / this.dragState.gridSize) * this.dragState.gridSize);

                this.dragState.marker.style.left = `${snappedLeft}px`;
                this.dragState.marker.style.top = `${snappedTop}px`;
                this.dragState.marker.dataset.tokenLeft = String(snappedLeft);
                this.dragState.marker.dataset.tokenTop = String(snappedTop);
                this.dragState.moved = true;
            });

            window.addEventListener("pointerup", async () => {
                if (!this.dragState) return;
                const drag = this.dragState;
                this.dragState = null;
                drag.marker.classList.remove("dragging");
                const finalLeft = Number(drag.marker.dataset.tokenLeft || drag.baseLeft);
                const finalTop = Number(drag.marker.dataset.tokenTop || drag.baseTop);
                const token = this._findStateToken(drag.tokenId);
                if (!token || !drag.moved || (finalLeft === drag.baseLeft && finalTop === drag.baseTop)) {
                    return;
                }

                try {
                    const useSocket = Boolean(this.socket && this.socket.isConnected);
                    const metadataJson = token?.metadata_json && typeof token.metadata_json === "object" ? { ...token.metadata_json } : {};
                    metadataJson.position_mode = "pixel";
                    const patch = { x: finalLeft, y: finalTop, metadata_json: metadataJson };
                    if (useSocket) {
                        this.socket.updateToken(drag.tokenId, drag.baseVersion, patch);
                    } else {
                        await this.api.updateToken(this.campaignId, this.sessionId, drag.tokenId, drag.baseVersion, patch);
                        await this.loadBootstrap();
                        this._logActivity(`Token bewegt: ${token.name}.`, "info");
                    }
                } catch (error) {
                    drag.marker.style.left = `${drag.baseLeft}px`;
                    drag.marker.style.top = `${drag.baseTop}px`;
                    this._showMessage(error.message || "Token konnte nicht bewegt werden.", true);
                    await this.loadBootstrap();
                }
            });

            this.mapInteractionsBound = true;
        }

        _renderActions() {
            const select = document.getElementById("actionCode");
            const catalog = this.bootstrap?.action_catalog || [];
            select.innerHTML = catalog.map((entry) => `
                <option value="${escapeHtml(entry.code)}">${escapeHtml(entry.name)} (${escapeHtml(entry.category)})</option>
            `).join("");
        }

        _renderTokenSelectors() {
            const actorSelect = document.getElementById("actionTokenId");
            const targetSelect = document.getElementById("actionTargetTokenId");
            const tokens = Array.isArray(this.bootstrap?.state_payload?.tokens) ? this.bootstrap.state_payload.tokens : [];
            const myUserId = Number(this.user?.id);

            if (!tokens.length) {
                actorSelect.innerHTML = "<option value=''>Kein Actor-Token</option>";
                targetSelect.innerHTML = "<option value=''>Kein Ziel-Token</option>";
                return;
            }

            const actorOptions = [];
            const fallbackOptions = [];
            for (const token of tokens) {
                const label = `${token.name} (#${token.id})`;
                const optionHtml = `<option value="${token.id}">${escapeHtml(label)}</option>`;
                if (Number(token.owner_user_id) === myUserId) {
                    actorOptions.push(optionHtml);
                } else {
                    fallbackOptions.push(optionHtml);
                }
            }
            actorSelect.innerHTML = actorOptions.concat(fallbackOptions).join("");

            targetSelect.innerHTML = "<option value=''>Kein Ziel</option>" + tokens
                .map((token) => `<option value="${token.id}">${escapeHtml(`${token.name} (#${token.id})`)}</option>`)
                .join("");

            if (this.selectedTokenId && this._isTokenAvailable(this.selectedTokenId, tokens)) {
                actorSelect.value = String(this.selectedTokenId);
            }
        }

        _renderFirstSteps() {
            const box = document.getElementById("firstStepsNotice");
            if (!box) return;
            const role = normalizeRole(this.bootstrap?.session_role || "");
            const status = String(this.bootstrap?.session?.runtime_status || this.bootstrap?.session?.status || "scheduled");

            let text = "";
            if (isOperatorRole(role)) {
                if (status === "scheduled") {
                    text = "DM Schnellstart: 1) Start-Check 2) Bereit setzen 3) Live starten.";
                } else if (status === "ready") {
                    text = "Session ist bereit. Mit 'Live starten' beginnt die Runde.";
                } else if (status === "in_progress") {
                    text = "Session laeuft: Karte pruefen, Tokens bewegen und Wuerfeln nutzen.";
                } else if (status === "paused") {
                    text = "Session pausiert: Fortsetzen oder sauber beenden.";
                }
            } else {
                text = "Spieler Schnellstart: 1) Karte ansehen 2) Wuerfeln testen 3) Eine Aktion ausfuehren.";
            }

            if (!text) {
                box.className = "message";
                box.textContent = "";
                return;
            }
            box.className = "message info";
            box.textContent = text;
        }

        _showMessage(text, isError = false) {
            const box = document.getElementById("msg");
            box.className = isError ? "message error" : "message success";
            box.textContent = text;
            this._logActivity(text, isError ? "error" : "success");
            window.setTimeout(() => {
                box.className = "message";
                box.textContent = "";
            }, 3500);
        }

        _logActivity(text, level = "info") {
            const time = new Date().toISOString().slice(11, 19);
            this.activityRows.unshift({ time, text: String(text || ""), level });
            if (this.activityRows.length > 20) {
                this.activityRows = this.activityRows.slice(0, 20);
            }
            this._renderActivity();
        }

        _renderActivity() {
            const container = document.getElementById("activityLog");
            if (!container) return;
            if (!this.activityRows.length) {
                container.innerHTML = "Noch keine Ereignisse.";
                return;
            }
            container.innerHTML = this.activityRows
                .map((row) => `<div class="activity-line">[${escapeHtml(row.time)}] ${escapeHtml(row.text)}</div>`)
                .join("");
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const ui = new PlayRuntimeUI();
        ui.init();
    });
})();
