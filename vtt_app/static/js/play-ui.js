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
        }

        async init() {
            const params = new URLSearchParams(window.location.search);
            this.campaignId = Number(params.get("campaign_id"));
            this.sessionId = Number(params.get("session_id"));
            if (!Number.isInteger(this.campaignId) || !Number.isInteger(this.sessionId)) {
                this._showMessage("campaign_id and session_id are required.", true);
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
                this._showMessage(error.message || "Bootstrap failed.", true);
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
                    this._showMessage("Scene stack initialized.");
                    await this.loadBootstrap();
                } catch (error) {
                    this._showMessage(error.message || "Scene stack init failed.", true);
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
                    const ok = window.confirm("Ready-check has warnings. Continue start?");
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
                const ok = window.confirm("End this session?");
                if (!ok) return;
                await this._transition("ended", true);
            });

            document.getElementById("btnRoll").addEventListener("click", () => {
                if (this.readOnly || !this.socket) {
                    this._showMessage("Read-only mode: dice roll blocked.", true);
                    return;
                }
                const dice = document.getElementById("diceInput").value.trim() || "1d20";
                this.socket.rollDice(dice, this.user?.username || "player", (result) => {
                    const target = document.getElementById("diceResult");
                    if (result?.error) {
                        target.textContent = `Error: ${result.error}`;
                        return;
                    }
                    const rolls = Array.isArray(result?.rolls) ? result.rolls.join(",") : "-";
                    target.textContent = `${dice} -> ${result.total} (${rolls})`;
                });
            });

            document.getElementById("btnExecuteAction").addEventListener("click", async () => {
                if (this.readOnly) {
                    this._showMessage("Read-only mode: action blocked.", true);
                    return;
                }
                const tokenId = Number(document.getElementById("actionTokenId").value);
                const actionCode = document.getElementById("actionCode").value;
                const targetRaw = document.getElementById("actionTargetTokenId").value;
                const targetTokenId = targetRaw ? Number(targetRaw) : null;

                if (!Number.isInteger(tokenId) || tokenId <= 0) {
                    this._showMessage("Select a valid actor token.", true);
                    return;
                }
                if (!actionCode) {
                    this._showMessage("Select an action first.", true);
                    return;
                }
                if (targetTokenId !== null && (!Number.isInteger(targetTokenId) || targetTokenId <= 0)) {
                    this._showMessage("Invalid target token.", true);
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
                    this._showMessage(`Action executed: ${payload.result.action_code}`);
                } catch (error) {
                    this._showMessage(error.message || "Action failed.", true);
                }
            });
        }

        async _runReadyCheck() {
            try {
                const result = await this.api.readyCheck(this.campaignId, this.sessionId);
                const node = document.getElementById("readyCheckOutput");
                const blockers = Array.isArray(result.blocking_issues) ? result.blocking_issues : [];
                const warnings = Array.isArray(result.warnings) ? result.warnings : [];

                const blockHtml = blockers.length
                    ? blockers.map((issue) => `<div class="ready-block">${escapeHtml(issue)}</div>`).join("")
                    : "<div class='ready-ok'>No blocking issues.</div>";
                const warnHtml = warnings.length
                    ? warnings.map((issue) => `<div class="ready-warn">${escapeHtml(issue)}</div>`).join("")
                    : "<div class='ready-ok'>No warnings.</div>";

                node.innerHTML = `
                    <div><strong>Can Start:</strong> ${result.can_start ? "yes" : "no"}</div>
                    <div style="margin-top:0.45rem;"><strong>Blocking</strong></div>
                    ${blockHtml}
                    <div style="margin-top:0.45rem;"><strong>Warnings</strong></div>
                    ${warnHtml}
                `;

                this._logActivity(`Ready-check executed (can_start=${result.can_start ? "yes" : "no"}).`, "info");
                return result;
            } catch (error) {
                this._showMessage(error.message || "Ready-check failed.", true);
                return null;
            }
        }

        async _transition(targetState, ignoreWarnings = false) {
            try {
                const payload = await this.api.transition(this.campaignId, this.sessionId, targetState, ignoreWarnings);
                this.mode = payload.mode;
                this.readOnly = Boolean(payload.read_only);
                const runtimeStatus = payload.session.runtime_status || payload.session.status;
                this._showMessage(`Session status: ${runtimeStatus}`);
                this._logActivity(`Transition applied: ${runtimeStatus}.`, "info");
                if (this.socket) this.socket.requestState();
                await this.loadBootstrap();
            } catch (error) {
                this._showMessage(error.message || "Transition failed.", true);
            }
        }

        _handleSnapshot(payload) {
            if (!this.bootstrap) return;
            this.bootstrap.state_payload = payload;
            this._renderState();
            this._renderTokenSelectors();
        }

        _handleMode(payload) {
            this.mode = payload?.mode || this.mode;
            this._renderMeta();
        }

        _handleStateChanged(payload) {
            this._showMessage(`State change: ${payload.previous_state} -> ${payload.target_state}`);
            this._logActivity(`State changed to ${payload.target_state}.`, "info");
            this.loadBootstrap();
        }

        _handleAction(payload) {
            const result = payload?.result;
            if (!result) return;
            this._showMessage(`Action event: ${result.action_code}`);
            this._logActivity(`Action event: ${result.action_code}.`, "info");
        }

        _handleDiceBroadcast(payload) {
            const log = document.getElementById("diceLog");
            const line = document.createElement("div");
            line.textContent = `${payload.player || "player"} rolled ${payload.dice}: ${payload.result?.total}`;
            log.prepend(line);
            while (log.children.length > 8) {
                log.removeChild(log.lastChild);
            }
            this._logActivity(`${payload.player || "player"} rolled ${payload.dice}.`, "info");
        }

        _render() {
            this._renderMeta();
            this._renderLayers();
            this._renderActions();
            this._renderState();
            this._renderTokenSelectors();
            this._renderActivity();
        }

        _renderMeta() {
            const campaignName = this.bootstrap?.campaign?.name || `Campaign ${this.campaignId}`;
            const sessionName = this.bootstrap?.session?.name || `Session ${this.sessionId}`;
            const role = this.bootstrap?.session_role || "-";

            document.getElementById("sessionTitle").textContent = `${campaignName} / ${sessionName}`;
            document.getElementById("modeBadge").textContent = this.mode;
            document.getElementById("roleBadge").textContent = role;
            document.getElementById("readOnlyBadge").textContent = this.readOnly ? "read-only" : "interactive";

            const notice = document.getElementById("readOnlyNotice");
            if (this.readOnly) {
                notice.className = "message info";
                notice.textContent = "Read-only mode is active for your current role or session state.";
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
                container.innerHTML = "<div class='muted'>No active scene stack.</div>";
                return;
            }

            container.innerHTML = stack.layers.map((layer) => {
                const isActive = Number(layer.id) === Number(stack.active_layer_id);
                const activateBtn = this.readOnly ? "" : `<button data-layer-id="${layer.id}" class="mini-btn">Activate</button>`;
                const mapName = escapeHtml(layer.campaign_map?.name || `Map ${layer.campaign_map_id}`);
                return `
                    <div class="panel-row ${isActive ? "active-row" : ""}">
                        <div><strong>${escapeHtml(layer.label)}</strong> (${mapName})</div>
                        ${isActive ? "<span>active</span>" : activateBtn}
                    </div>
                `;
            }).join("");

            container.querySelectorAll("button[data-layer-id]").forEach((button) => {
                button.addEventListener("click", async () => {
                    const layerId = Number(button.getAttribute("data-layer-id"));
                    try {
                        await this.api.activateLayer(this.campaignId, this.sessionId, layerId);
                        this._showMessage("Layer activated.");
                        this._logActivity(`Layer ${layerId} activated.`, "info");
                        await this.loadBootstrap();
                    } catch (error) {
                        this._showMessage(error.message || "Layer switch failed.", true);
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
                : "No active map";

            const tokens = statePayload?.tokens || [];
            if (!tokens.length) {
                tokenList.innerHTML = "<div class='muted'>No tokens in current session state.</div>";
            } else {
                tokenList.innerHTML = tokens.map((token) => `
                    <div class="panel-row">
                        <div><strong>${escapeHtml(token.name)}</strong> (${escapeHtml(token.token_type)})</div>
                        <div>HP ${token.hp_current ?? "-"} / ${token.hp_max ?? "-"}, Pos ${token.x},${token.y}</div>
                    </div>
                `).join("");
            }
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
                actorSelect.innerHTML = "<option value=''>No actor token</option>";
                targetSelect.innerHTML = "<option value=''>No target token</option>";
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

            targetSelect.innerHTML = "<option value=''>No target</option>" + tokens
                .map((token) => `<option value="${token.id}">${escapeHtml(`${token.name} (#${token.id})`)}</option>`)
                .join("");
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
                container.innerHTML = "No events yet.";
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
