(function () {
    const reducedMotion = window.matchMedia
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : { matches: false };
    const PLAY_ENTRY_STORAGE_KEY = "vtt.play.entry-boundary";
    const BOOK_RETURN_STORAGE_KEY = "vtt.book.return-boundary";
    const PLAY_ENTRY_PHASES = new Set(["book-exit", "play-route-entry"]);
    const BOOK_RETURN_PHASES = new Set(["table-exit", "book-route-entry"]);
    const PLAY_RETURN_EXIT_DURATION_MS = 520;
    const BOOK_RETURN_ARRIVAL_DURATION_MS = 680;

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
            this.entryBoundary = null;
            this.entryArrivalTimer = null;
            this.returnBoundary = null;
            this.returnExitTimer = null;
            this.returnTransitionInFlight = false;
            this.activityRows = [];
            this.chatRows = [];
            this.selectedTokenId = null;
            // Playtable-Vordermann 2026-08-25: server-backed combat state
            // ({encounter, participants, events}) for the table.
            this.combat = null;
            this.dragState = null;
            this.panState = null;
            this.mapInteractionsBound = false;
            this.tokenIndex = new Map();
            this.currentTool = "select";
            this.zoomLevel = 100;
            this.activeSidebarTab = "tools";
            // Auto-fit runs once per activated map so the DM's manual zoom
            // choice survives snapshots/re-renders of the same map.
            this.autoFitMapId = null;
            this.pendingTokenPlacement = null;
            this.pendingTokenImage = null;
            this.pendingTokenImageLabel = "";
        }

        async init() {
            const params = new URLSearchParams(window.location.search);
            this.campaignId = Number(params.get("campaign_id"));
            this.sessionId = Number(params.get("session_id"));
            this.user = await this.auth.requireAuth("/login.html");
            if (!this.user) {
                return;
            }

            if (!Number.isInteger(this.campaignId) || this.campaignId <= 0
                || !Number.isInteger(this.sessionId) || this.sessionId <= 0) {
                this._showMissingSessionState();
                return;
            }

            this._consumeEntryBoundary();

            this._bindControls();
            await this.loadBootstrap();
            this._connectSocket();
        }

        _showMissingSessionState() {
            // UI-Regel (Adrian, 2026-08-25): der Spieltisch wird IMMER aus
            // einer aktiven Kampagne heraus geöffnet — ein /play ohne
            // Parameter ist kein Zustand, den man ansieht, sondern eine
            // falsche Adresse.  Keine Sackgassen-Seite, direkt zurück ins
            // Buch zur Kampagnenliste.
            window.location.replace("/campaigns");
        }

        _consumeEntryBoundary() {
            const body = document.body;
            if (!body) {
                return;
            }

            body.dataset.playEntryBoundary = "direct";
            body.dataset.playTransitionStage = "table";
            body.dataset.playEntryPhase = "TABLE_MODE";
            body.dataset.playReturnBoundary = "idle";
            body.dataset.playReturnPhase = "TABLE_MODE";
            delete body.dataset.playEntrySourceRoute;
            delete body.dataset.playReturnTargetRoute;

            let raw = null;
            try {
                raw = window.sessionStorage.getItem(PLAY_ENTRY_STORAGE_KEY);
            } catch (error) {
                console.warn("Failed to read play entry boundary context:", error);
                return;
            }

            if (!raw) {
                return;
            }

            try {
                const boundary = JSON.parse(raw);
                window.sessionStorage.removeItem(PLAY_ENTRY_STORAGE_KEY);
                if (!this._isValidEntryBoundary(boundary)) {
                    return;
                }

                this.entryBoundary = boundary;
                body.dataset.playEntryBoundary = "book-to-table";
                body.dataset.playEntryPhase = String(boundary.phase || "BOOK_TO_TABLE_TRANSITION");
                if (boundary.source_route) {
                    body.dataset.playEntrySourceRoute = String(boundary.source_route);
                }
                this._beginEntryArrival();
            } catch (error) {
                console.warn("Failed to parse play entry boundary context:", error);
                try {
                    window.sessionStorage.removeItem(PLAY_ENTRY_STORAGE_KEY);
                } catch (_cleanupError) {
                    // Swallow cleanup failure and keep direct-entry fallback active.
                }
            }
        }

        _isValidEntryBoundary(boundary) {
            if (!boundary || typeof boundary !== "object") {
                return false;
            }

            const target = boundary.target && typeof boundary.target === "object" ? boundary.target : {};
            const matchesTarget =
                Number(target.campaign_id) === this.campaignId &&
                Number(target.session_id) === this.sessionId;

            if (!matchesTarget) {
                return false;
            }

            if (boundary.kind !== "book-to-table") {
                return false;
            }
            if (boundary.transition_mode !== "BOOK_TO_TABLE_TRANSITION") {
                return false;
            }
            if (boundary.target_mode !== "TABLE_MODE") {
                return false;
            }
            if (target.family !== "play") {
                return false;
            }
            if (!PLAY_ENTRY_PHASES.has(String(boundary.phase || "book-exit"))) {
                return false;
            }

            return true;
        }

        _beginEntryArrival() {
            const body = document.body;
            if (!body || !this.entryBoundary) {
                return;
            }

            body.dataset.playTransitionStage = "arrival";
            window.requestAnimationFrame(() => {
                window.requestAnimationFrame(() => {
                    if (!document.body || document.body.dataset.playEntryBoundary !== "book-to-table") {
                        return;
                    }
                    document.body.dataset.playTransitionStage = "settling";
                });
            });
        }

        _finalizeEntryArrival() {
            const body = document.body;
            if (!body) {
                return;
            }

            if (this.entryArrivalTimer) {
                window.clearTimeout(this.entryArrivalTimer);
            }

            const baseDuration = Number(this.entryBoundary?.arrival_duration_ms) || 720;
            const settleDelay = Math.max(240, Math.min(900, Math.round(baseDuration * 0.72)));
            this.entryArrivalTimer = window.setTimeout(() => {
                if (!document.body) {
                    return;
                }
                document.body.dataset.playTransitionStage = "table";
                document.body.dataset.playEntryPhase = "TABLE_MODE";
                if (this.entryBoundary) {
                    document.body.dataset.playEntryBoundary = "arrived";
                }
            }, settleDelay);
        }

        async loadBootstrap() {
            try {
                const payload = await this.api.bootstrap(this.campaignId, this.sessionId);
                this.bootstrap = payload;
                this.mode = payload.mode || "waiting";
                this.readOnly = Boolean(payload.read_only);
                // Persisted chat history arrives with the bootstrap payload
                // (newest first, same shape the live broadcast uses), so a
                // reload no longer wipes the table conversation.
                if (Array.isArray(payload.chat_history) && !this.chatRows.length) {
                    this.chatRows = payload.chat_history.map((entry) => ({
                        time: String(entry.created_at || entry.timestamp || "").slice(11, 19),
                        user: entry.sender_name || "player",
                        sender_name: entry.sender_name || "player",
                        text: entry.message || entry.content || "",
                        message: entry.message || entry.content || "",
                    }));
                }
                await this._refreshCombatState();
                this._render();
            } catch (error) {
                this._showMessage(error.message || "Startdaten konnten nicht geladen werden.", true);
            } finally {
                this._finalizeEntryArrival();
            }
        }

        async _refreshCombatState() {
            try {
                this.combat = await this.api.combatState(this.campaignId, this.sessionId);
            } catch (error) {
                this.combat = null;
            }
        }

        _combatActive() {
            return this.combat?.encounter?.status === "active";
        }

        _handleCombatState(payload) {
            if (!payload || typeof payload !== "object") return;
            this.combat = payload;
            // Server combat mutates participant tokens (initiative,
            // version) — merge so drag base_versions stay correct.
            const tokens = this.bootstrap?.state_payload?.tokens;
            if (Array.isArray(tokens)) {
                (payload.participants || []).forEach((incoming) => {
                    const existing = tokens.find(
                        (token) => Number(token.id) === Number(incoming.id));
                    if (existing) Object.assign(existing, incoming);
                });
            }
            this._render();
        }

        async _startCombat() {
            try {
                this._handleCombatState(
                    await this.api.combatStart(this.campaignId, this.sessionId, "auto"));
                this._logActivity("Kampf gestartet — Initiative vom Server ausgewürfelt.", "info");
            } catch (error) {
                this._showMessage(error.message || "Kampf konnte nicht gestartet werden.", true);
            }
        }

        async _advanceCombatTurn(allowRetry = true) {
            const baseVersion = Number(this.combat?.encounter?.version || 0);
            try {
                this._handleCombatState(
                    await this.api.combatAdvanceTurn(this.campaignId, this.sessionId, baseVersion));
            } catch (error) {
                // Version conflict (REST response vs. socket event racing the
                // local merge): fetch the fresh encounter once and retry.
                if (allowRetry) {
                    await this._refreshCombatState();
                    return this._advanceCombatTurn(false);
                }
                this._showMessage(error.message || "Zugwechsel fehlgeschlagen.", true);
            }
        }

        async _endCombat(allowRetry = true) {
            const baseVersion = Number(this.combat?.encounter?.version || 0);
            try {
                this._handleCombatState(
                    await this.api.combatEnd(this.campaignId, this.sessionId, baseVersion));
                this._logActivity("Kampf beendet.", "info");
            } catch (error) {
                if (allowRetry) {
                    await this._refreshCombatState();
                    return this._endCombat(false);
                }
                this._showMessage(error.message || "Kampf konnte nicht beendet werden.", true);
            }
        }

        _handlePresence(payload) {
            const roster = document.getElementById("presenceRoster");
            if (!roster) return;
            const users = Array.isArray(payload?.users) ? payload.users : [];
            roster.textContent = users.length
                ? users.map((user) => user.username).join(", ")
                : "–";
        }

        _openSheet(characterId, characterName) {
            if (!characterId) return;
            const drawer = document.getElementById("sheetDrawer");
            const frame = document.getElementById("sheetFrame");
            const title = document.getElementById("sheetDrawerTitle");
            if (!drawer || !frame) return;
            frame.src = `/character-sheet?id=${encodeURIComponent(characterId)}`;
            if (title) {
                title.textContent = characterName
                    ? `Charakterbogen · ${characterName}` : "Charakterbogen";
            }
            drawer.hidden = false;
        }

        _closeSheet() {
            const drawer = document.getElementById("sheetDrawer");
            const frame = document.getElementById("sheetFrame");
            if (!drawer || drawer.hidden) return;
            drawer.hidden = true;
            if (frame) frame.src = "about:blank";
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
                    layersUpdated: () => this.loadBootstrap(),
                    actionExecuted: (payload) => this._handleAction(payload),
                    diceRolled: (payload) => this._handleDiceBroadcast(payload),
                    chatMessageSent: (payload) => this._handleChatBroadcast(payload),
                    externalRoll: (payload) => this._handleExternalRoll(payload),
                    tokenCreated: (payload) => this._handleTokenCreated(payload),
                    tokenUpdated: (payload) => this._handleTokenUpdated(payload),
                    tokenDeleted: (payload) => this._handleTokenDeleted(payload),
                    tokenBatchMoved: (payload) => this._handleTokenBatchMoved(payload),
                    initiativeUpdated: (payload) => this._handleInitiativeUpdated(payload),
                    initiativeTurnChanged: (payload) => this._handleInitiativeTurnChanged(payload),
                    combatState: (payload) => this._handleCombatState(payload),
                    combatEnded: (payload) => this._handleCombatState(payload),
                    presenceUpdate: (payload) => this._handlePresence(payload),
                    tick: () => {},
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
            // Minimal public surface for external-roll adapters (e.g.
            // beyond20-bridge.js): hand a normalized envelope to the table
            // without reaching into runtime internals.
            window.RollDraufTable = {
                sendExternalRoll: (roll) => {
                    if (this.readOnly) return false;
                    if (!this.socket || !this.socket.isConnected) return false;
                    this.socket.sendExternalRoll(roll);
                    return true;
                },
                // HP sync (Beyond20 hp-update et al.): match the external
                // character to a table token BY NAME and patch its HP via
                // the normal token-update path, so every client sees it and
                // the usual ownership/read-only rules apply.
                updateCharacterHp: (update) => {
                    if (this.readOnly || !update) return false;
                    const token = this._findTokenByName(update.name);
                    if (!token || !this._canMoveToken(token)) return false;
                    const patch = {};
                    if (Number.isFinite(update.hp)) patch.hp_current = Math.round(update.hp);
                    if (Number.isFinite(update.maxHp) && update.maxHp > 0) patch.hp_max = Math.round(update.maxHp);
                    if (!Object.keys(patch).length) return false;
                    this._patchToken(token, patch);
                    this._logActivity(`HP-Sync: ${token.name} -> ${patch.hp_current ?? "?"}${patch.hp_max ? ` / ${patch.hp_max}` : ""}.`, "info");
                    return true;
                },
                // Conditions sync (Beyond20 conditions-update): conditions
                // live in metadata_json.conditions (TokenState has no
                // dedicated column) and render as a marker badge + token
                // list line.
                updateCharacterConditions: (update) => {
                    if (this.readOnly || !update) return false;
                    const token = this._findTokenByName(update.name);
                    if (!token || !this._canMoveToken(token)) return false;
                    const conditions = (Array.isArray(update.conditions) ? update.conditions : [])
                        .slice(0, 20)
                        .map((entry) => String(entry).slice(0, 40))
                        .filter(Boolean);
                    const metadataJson = token.metadata_json && typeof token.metadata_json === "object"
                        ? { ...token.metadata_json } : {};
                    const before = JSON.stringify(metadataJson.conditions || []);
                    if (before === JSON.stringify(conditions)) return true;
                    metadataJson.conditions = conditions;
                    this._patchToken(token, { metadata_json: metadataJson });
                    this._logActivity(
                        conditions.length
                            ? `Zustände: ${token.name} -> ${conditions.join(", ")}.`
                            : `Zustände: ${token.name} -> keine.`,
                        "info");
                    return true;
                },
                // Turn tracker sync (Beyond20 update-combat): initiative +
                // current-turn flag for every combatant whose name matches
                // a table token; only changed tokens get patched.
                updateCombatTracker: (combatants) => {
                    if (this.readOnly || !Array.isArray(combatants)) return 0;
                    let patched = 0;
                    for (const combatant of combatants) {
                        const token = this._findTokenByName(combatant?.name);
                        if (!token || !this._canMoveToken(token)) continue;
                        const patch = {};
                        const initiative = Number(combatant.initiative);
                        if (Number.isFinite(initiative) && Number(token.initiative) !== Math.round(initiative)) {
                            patch.initiative = Math.round(initiative);
                        }
                        const isTurn = Boolean(combatant.turn);
                        const hadTurn = Boolean(token.metadata_json?.current_turn);
                        if (isTurn !== hadTurn) {
                            const metadataJson = token.metadata_json && typeof token.metadata_json === "object"
                                ? { ...token.metadata_json } : {};
                            metadataJson.current_turn = isTurn;
                            patch.metadata_json = metadataJson;
                        }
                        if (Object.keys(patch).length) {
                            this._patchToken(token, patch);
                            patched += 1;
                        }
                    }
                    if (patched) {
                        this._logActivity(`Turn-Tracker synchronisiert (${patched} Token).`, "info");
                    }
                    return patched;
                },
            };
            window.dispatchEvent(new CustomEvent("rolldrauf:table-ready"));
            window.addEventListener("beforeunload", () => {
                if (this.entryArrivalTimer) {
                    window.clearTimeout(this.entryArrivalTimer);
                }
                if (this.returnExitTimer) {
                    window.clearTimeout(this.returnExitTimer);
                }
                this.socket.disconnect();
            });
        }

        _normalizeBookReturnTarget(targetHref) {
            if (!targetHref) {
                return null;
            }

            const url = new URL(String(targetHref), window.location.origin);
            const path = url.pathname;
            let routeKey = null;
            if (path === "/dashboard" || path === "/dashboard.html") {
                routeKey = "dashboard";
            } else if (path === "/campaigns" || path === "/campaigns.html") {
                routeKey = "campaigns";
            } else if (path === "/characters" || path === "/characters.html") {
                routeKey = "characters";
            } else if (path === "/character-sheet" || path === "/character-sheet.html") {
                routeKey = "character-sheet";
            }

            if (!routeKey) {
                return null;
            }

            return {
                routeKey,
                href: `${url.pathname}${url.search}`,
            };
        }

        _persistBookReturnBoundary(target) {
            const boundary = {
                kind: "table-to-book",
                from_mode: "TABLE_MODE",
                transition_mode: "TABLE_TO_BOOK_TRANSITION",
                target_mode: "BOOK_MODE",
                source_route: "play",
                source_href: `${window.location.pathname}${window.location.search}`,
                phase: "table-exit",
                campaign_id: this.campaignId,
                session_id: this.sessionId,
                exit_duration_ms: PLAY_RETURN_EXIT_DURATION_MS,
                arrival_duration_ms: BOOK_RETURN_ARRIVAL_DURATION_MS,
                target: {
                    family: "book",
                    route: target.routeKey,
                    href: target.href,
                },
                started_at: new Date().toISOString(),
            };

            try {
                window.sessionStorage.setItem(BOOK_RETURN_STORAGE_KEY, JSON.stringify(boundary));
            } catch (error) {
                console.warn("Failed to persist book return boundary context:", error);
            }

            return boundary;
        }

        _beginReturnTransition(boundary) {
            const body = document.body;
            if (!body || !boundary || this.returnTransitionInFlight) {
                return false;
            }

            this.returnTransitionInFlight = true;
            this.returnBoundary = boundary;

            if (this.entryArrivalTimer) {
                window.clearTimeout(this.entryArrivalTimer);
                this.entryArrivalTimer = null;
            }
            if (this.returnExitTimer) {
                window.clearTimeout(this.returnExitTimer);
                this.returnExitTimer = null;
            }

            body.dataset.playReturnBoundary = "table-to-book";
            body.dataset.playReturnPhase = "TABLE_TO_BOOK_TRANSITION";
            body.dataset.playReturnTargetRoute = String(boundary.target?.route || "campaigns");
            body.dataset.playTransitionStage = "table-exit";

            const navigateToBook = () => {
                boundary.phase = "book-route-entry";
                boundary.table_exit_completed_at = new Date().toISOString();
                try {
                    window.sessionStorage.setItem(BOOK_RETURN_STORAGE_KEY, JSON.stringify(boundary));
                } catch (error) {
                    console.warn("Failed to update book return boundary context:", error);
                }

                if (document.body) {
                    document.body.dataset.playTransitionStage = "book-handoff";
                    document.body.dataset.playReturnBoundary = "handoff";
                    document.body.dataset.playReturnPhase = "BOOK_MODE";
                }
                window.location.href = boundary.target.href;
            };

            const exitDuration = Math.max(
                220,
                Math.min(900, Number(boundary.exit_duration_ms) || PLAY_RETURN_EXIT_DURATION_MS)
            );

            if (reducedMotion.matches) {
                this.returnExitTimer = window.setTimeout(navigateToBook, 64);
                return true;
            }

            window.requestAnimationFrame(() => {
                if (!document.body || document.body.dataset.playReturnBoundary !== "table-to-book") {
                    return;
                }

                this.returnExitTimer = window.setTimeout(() => {
                    navigateToBook();
                }, exitDuration);
            });

            return true;
        }

        returnToBook(targetHref) {
            const target = this._normalizeBookReturnTarget(targetHref);
            if (!target) {
                throw new Error("Invalid book return target");
            }

            const boundary = this._persistBookReturnBoundary(target);
            return this._beginReturnTransition(boundary);
        }

        _bindControls() {
            document.getElementById("btnBack").addEventListener("click", () => {
                this.returnToBook(`/campaigns?campaign_id=${this.campaignId}`);
            });

            document.querySelectorAll("[data-book-return-target]").forEach((node) => {
                node.addEventListener("click", () => {
                    const target = node.getAttribute("data-book-return-target");
                    if (!target) {
                        return;
                    }
                    this.returnToBook(target);
                });
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
                    this._showMessage("Nur-Lesen aktiv: Würfeln ist gesperrt.", true);
                    return;
                }
                const dice = document.getElementById("diceInput").value.trim() || "1d20";
                this.socket.rollDice(dice, this.user?.username || "player", (result) => {
                    const target = document.getElementById("diceResult");
                    if (!result || result.error) {
                        target.textContent = `Fehler: ${result?.error || "keine Antwort vom Server"}`;
                        return;
                    }
                    const rolls = Array.isArray(result.rolls) ? result.rolls.join(",") : "-";
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
                    this._showMessage("Bitte einen gueltigen Token wählen.", true);
                    return;
                }
                if (!actionCode) {
                    this._showMessage("Bitte zuerst eine Aktion wählen.", true);
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
                    this._showMessage(`Aktion ausgeführt: ${payload.result.action_code}`);
                } catch (error) {
                    this._showMessage(error.message || "Aktion fehlgeschlagen.", true);
                }
            });

            this._bindWorkspaceControls();
            this._bindTableActions();
        }

        _bindWorkspaceControls() {
            // M3: the right sidebar (Journal/Chat/Tools/Session) is an overlay
            // toggled on demand now, closed by default, so the map keeps the
            // large majority of the screen instead of a permanently reserved
            // 370px column.
            const sidebar = document.querySelector(".right-sidebar");
            const sidebarToggle = document.getElementById("btnSidebarToggle");
            if (sidebarToggle && sidebar) {
                sidebarToggle.addEventListener("click", () => {
                    sidebar.classList.toggle("is-open");
                });
            }
            const sidebarClose = document.getElementById("btnSidebarClose");
            if (sidebarClose && sidebar) {
                sidebarClose.addEventListener("click", () => {
                    sidebar.classList.remove("is-open");
                });
            }

            document.querySelectorAll(".sidebar-tab:not(.sidebar-close)").forEach((button) => {
                button.addEventListener("click", () => {
                    const tab = button.getAttribute("data-tab") || "tools";
                    this._activateSidebarTab(tab);
                    if (sidebar) {
                        sidebar.classList.add("is-open");
                    }
                });
            });
            this._activateSidebarTab(this.activeSidebarTab);

            document.querySelectorAll(".tool-btn[data-tool]").forEach((button) => {
                button.addEventListener("click", () => {
                    const tool = button.getAttribute("data-tool") || "select";
                    this._setTool(tool);
                    if (tool === "token") {
                        this._openTokenMenu();
                    }
                });
            });

            const zoomOut = document.getElementById("btnZoomOut");
            const zoomIn = document.getElementById("btnZoomIn");
            const zoomReset = document.getElementById("btnZoomReset");
            const zoomFit = document.getElementById("btnZoomFit");
            const zoomRange = document.getElementById("zoomRange");
            if (zoomOut) zoomOut.addEventListener("click", () => this._setZoom(this.zoomLevel - 10));
            if (zoomIn) zoomIn.addEventListener("click", () => this._setZoom(this.zoomLevel + 10));
            if (zoomReset) zoomReset.addEventListener("click", () => this._setZoom(100));
            if (zoomFit) zoomFit.addEventListener("click", () => this._zoomFit());
            if (zoomRange) {
                zoomRange.addEventListener("input", () => {
                    this._setZoom(Number(zoomRange.value || 100));
                });
            }
            this._setZoom(this.zoomLevel);
            this._bindViewportNavigation();
            this._bindWidgetToggles();
            this._setupTableSheet();

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
            // Placing-a-token mode is exclusive: switching tools cancels a
            // half-finished placement instead of leaving the panel orphaned.
            if (toolName !== "token") {
                this._cancelTokenPlacement();
            }
            this.currentTool = toolName;
            document.querySelectorAll(".tool-btn[data-tool]").forEach((button) => {
                const isActive = button.getAttribute("data-tool") === toolName;
                button.classList.toggle("active", isActive);
            });
            const viewport = document.getElementById("mapViewport");
            if (viewport) {
                viewport.classList.toggle("tool-pan", toolName === "pan");
                viewport.classList.toggle("tool-token", toolName === "token");
            }
        }

        _openTokenMenu() {
            const tokenWidget = document.getElementById("tokenWidget");
            if (!tokenWidget) return;

            tokenWidget.classList.remove("collapsed");
            tokenWidget.querySelector(".widget-toggle")?.setAttribute("aria-expanded", "true");

            // On a phone the widgets live inside the table sheet. Opening the
            // Token ribbon action must open that sheet as well, otherwise the
            // upload control exists in the DOM but remains unreachable behind
            // the closed sheet.
            const tableSheet = document.getElementById("tableSheet");
            const tableSheetButton = document.getElementById("btnTableSheet");
            if (tableSheet && tableSheet.hidden && tableSheetButton) {
                tableSheetButton.click();
            }

            const uploadButton = document.getElementById("btnTokenUpload");
            if (uploadButton && !uploadButton.hidden) {
                uploadButton.focus({ preventScroll: true });
            }
        }

        _worldSize() {
            const world = document.getElementById("mapWorld");
            return {
                width: Number(world?.dataset?.mapWidth) || 1800,
                height: Number(world?.dataset?.mapHeight) || 1200,
            };
        }

        // The scroll spacer (#mapExtent) must always be world-size * zoom:
        // scale() alone leaves the layout box unscaled, which made the
        // scrollbars lie in both directions (robot audit 2026-08-23).
        _syncExtent() {
            const extent = document.getElementById("mapExtent");
            if (!extent) return;
            const { width, height } = this._worldSize();
            const scale = this.zoomLevel / 100;
            extent.style.width = `${Math.round(width * scale)}px`;
            extent.style.height = `${Math.round(height * scale)}px`;
        }

        _setZoom(nextZoom, anchor = null) {
            const clamped = Math.max(20, Math.min(300, Math.round(Number(nextZoom) || 100)));
            const viewport = document.getElementById("mapViewport");
            const previousScale = this.zoomLevel / 100;
            const nextScale = clamped / 100;

            // Keep the world point under the anchor (e.g. the mouse wheel
            // cursor) stationary: convert the anchor to world coordinates at
            // the old scale, then scroll so the same world point sits under
            // the anchor again at the new scale.
            let anchorWorld = null;
            if (anchor && viewport) {
                const rect = viewport.getBoundingClientRect();
                const viewX = anchor.clientX - rect.left;
                const viewY = anchor.clientY - rect.top;
                anchorWorld = {
                    viewX,
                    viewY,
                    worldX: (viewport.scrollLeft + viewX) / previousScale,
                    worldY: (viewport.scrollTop + viewY) / previousScale,
                };
            }

            this.zoomLevel = clamped;
            const world = document.getElementById("mapWorld");
            const zoomLabel = document.getElementById("zoomLabel");
            const zoomRange = document.getElementById("zoomRange");
            if (world) world.style.transform = `scale(${nextScale})`;
            this._syncExtent();
            if (zoomLabel) zoomLabel.textContent = `${clamped}%`;
            if (zoomRange) zoomRange.value = String(clamped);

            if (anchorWorld && viewport) {
                viewport.scrollLeft = anchorWorld.worldX * nextScale - anchorWorld.viewX;
                viewport.scrollTop = anchorWorld.worldY * nextScale - anchorWorld.viewY;
            }
        }

        _zoomFit() {
            const viewport = document.getElementById("mapViewport");
            if (!viewport) return;
            const { width, height } = this._worldSize();
            const availableW = Math.max(120, viewport.clientWidth - 48);
            const availableH = Math.max(120, viewport.clientHeight - 48);
            const fit = Math.min(availableW / width, availableH / height) * 100;
            this._setZoom(Math.min(150, fit));
            viewport.scrollLeft = 0;
            viewport.scrollTop = 0;
        }

        _bindViewportNavigation() {
            const viewport = document.getElementById("mapViewport");
            if (!viewport) return;

            // Wheel = zoom to cursor (the standard VTT gesture); plain
            // scrolling of a huge map happens by panning instead.
            viewport.addEventListener("wheel", (event) => {
                event.preventDefault();
                const step = event.deltaY < 0 ? 10 : -10;
                this._setZoom(this.zoomLevel + step, event);
            }, { passive: false });

            // Panning: PAN tool with the left button, or middle button in
            // any tool. Uses scroll offsets, so it composes with zoom.
            viewport.addEventListener("pointerdown", (event) => {
                const isMiddle = event.button === 1;
                const isPanTool = this.currentTool === "pan" && event.button === 0;
                if (!isMiddle && !isPanTool) return;
                if (event.target.closest?.(".floating, .stage-topbar, .token-marker")) return;
                event.preventDefault();
                this.panState = {
                    startX: event.clientX,
                    startY: event.clientY,
                    scrollLeft: viewport.scrollLeft,
                    scrollTop: viewport.scrollTop,
                };
                viewport.classList.add("panning");
            });
            window.addEventListener("pointermove", (event) => {
                if (!this.panState) return;
                viewport.scrollLeft = this.panState.scrollLeft - (event.clientX - this.panState.startX);
                viewport.scrollTop = this.panState.scrollTop - (event.clientY - this.panState.startY);
            });
            window.addEventListener("pointerup", () => {
                if (!this.panState) return;
                this.panState = null;
                viewport.classList.remove("panning");
            });

            // Token placement: with the TOK tool armed, a click on the map
            // (not on an existing marker) opens the small create panel.
            viewport.addEventListener("click", (event) => {
                if (this.currentTool !== "token") return;
                if (event.target.closest?.(".token-marker, .floating, .stage-topbar")) return;
                const world = document.getElementById("mapWorld");
                const worldRect = world?.getBoundingClientRect();
                if (!worldRect) return;
                const scale = this.zoomLevel / 100;
                const worldX = (event.clientX - worldRect.left) / scale;
                const worldY = (event.clientY - worldRect.top) / scale;
                const { width, height } = this._worldSize();
                if (worldX < 0 || worldY < 0 || worldX > width || worldY > height) return;
                this._openTokenCreatePanel(worldX, worldY, event);
            });
        }

        _openTokenCreatePanel(worldX, worldY, clickEvent) {
            if (this.readOnly) {
                this._showMessage("Nur-Lesen aktiv: Tokens können nicht platziert werden.", true);
                return;
            }
            const activeMap = this.bootstrap?.state_payload?.active_map;
            if (!activeMap) {
                this._showMessage("Erst eine Karte aktivieren, dann Tokens platzieren.", true);
                return;
            }
            const gridSize = Math.max(16, Number(activeMap.grid_size) || 70);
            const panel = document.getElementById("tokenCreatePanel");
            const stage = document.querySelector(".stage");
            if (!panel || !stage) return;

            this.pendingTokenPlacement = {
                x: Math.max(0, Math.round(worldX / gridSize) * gridSize),
                y: Math.max(0, Math.round(worldY / gridSize) * gridSize),
            };

            const stageRect = stage.getBoundingClientRect();
            const left = Math.min(stageRect.width - 270, Math.max(8, clickEvent.clientX - stageRect.left + 12));
            const top = Math.min(stageRect.height - 260, Math.max(8, clickEvent.clientY - stageRect.top + 12));
            panel.style.left = `${left}px`;
            panel.style.top = `${top}px`;
            panel.hidden = false;

            const imageLabel = document.getElementById("tokenCreateImageLabel");
            if (imageLabel) {
                imageLabel.textContent = this.pendingTokenImage
                    ? (this.pendingTokenImageLabel || "Bild ausgewählt")
                    : "Bild (optional)...";
            }

            const nameInput = document.getElementById("tokenCreateName");
            if (nameInput) {
                nameInput.value = "";
                nameInput.focus();
            }
            const operator = isOperatorRole(this.bootstrap?.session_role);
            const visibilityRow = document.getElementById("tokenCreateVisibility");
            if (visibilityRow) {
                visibilityRow.style.display = operator ? "" : "none";
            }
            // The server only lets players create player-type tokens they
            // own -- pin the select instead of offering options that would
            // come back as a 403.
            const typeSelect = document.getElementById("tokenCreateType");
            if (typeSelect) {
                if (!operator) {
                    typeSelect.value = "player";
                }
                typeSelect.disabled = !operator;
            }
        }

        _cancelTokenPlacement() {
            this.pendingTokenPlacement = null;
            this.pendingTokenImage = null;
            this.pendingTokenImageLabel = "";
            const imageLabel = document.getElementById("tokenCreateImageLabel");
            if (imageLabel) imageLabel.textContent = "Bild (optional)...";
            const panel = document.getElementById("tokenCreatePanel");
            if (panel) panel.hidden = true;
        }

        async _confirmTokenPlacement() {
            const placement = this.pendingTokenPlacement;
            if (!placement) return;
            const name = String(document.getElementById("tokenCreateName")?.value || "").trim();
            if (!name) {
                this._showMessage("Der Token braucht einen Namen.", true);
                return;
            }
            const tokenType = document.getElementById("tokenCreateType")?.value || "npc";
            const sizeCells = Math.max(1, Math.min(6, Number(document.getElementById("tokenCreateSize")?.value) || 1));
            const visibility = isOperatorRole(this.bootstrap?.session_role)
                ? (document.getElementById("tokenCreateVisibility")?.value || "public")
                : "public";

            const metadataJson = { position_mode: "pixel" };
            if (this.pendingTokenImage) {
                metadataJson.image_url = this.pendingTokenImage;
            }
            const token = {
                name,
                token_type: tokenType,
                x: placement.x,
                y: placement.y,
                size: sizeCells,
                visibility,
                // New tokens always declare their coordinate system so the
                // renderer never has to guess (the old <=300 heuristic).
                metadata_json: metadataJson,
            };
            this._cancelTokenPlacement();
            try {
                if (this.socket && this.socket.isConnected) {
                    this.socket.createToken(token);
                } else {
                    await this.api.createToken(this.campaignId, this.sessionId, token);
                    await this.loadBootstrap();
                }
                this._logActivity(`Token platziert: ${name}.`, "info");
            } catch (error) {
                this._showMessage(error.message || "Token konnte nicht erstellt werden.", true);
            }
        }

        async _deleteSelectedToken() {
            const token = this._findStateToken(this.selectedTokenId);
            if (!token) return;
            if (!window.confirm(`Token "${token.name}" wirklich löschen?`)) return;
            try {
                if (this.socket && this.socket.isConnected) {
                    this.socket.deleteToken(token.id, Number(token.version || 1));
                } else {
                    await this.api.deleteToken(this.campaignId, this.sessionId, token.id, Number(token.version || 1));
                    await this.loadBootstrap();
                }
            } catch (error) {
                this._showMessage(error.message || "Token konnte nicht gelöscht werden.", true);
            }
        }

        async _setSelectedTokenHp() {
            const token = this._findStateToken(this.selectedTokenId);
            if (!token) return;
            const hpCurrentRaw = document.getElementById("tokenHpCurrent")?.value;
            const hpMaxRaw = document.getElementById("tokenHpMax")?.value;
            const patch = {};
            if (hpCurrentRaw !== "" && hpCurrentRaw !== undefined) patch.hp_current = Number(hpCurrentRaw);
            if (hpMaxRaw !== "" && hpMaxRaw !== undefined) patch.hp_max = Number(hpMaxRaw);
            if (!Object.keys(patch).length) return;
            try {
                if (this.socket && this.socket.isConnected) {
                    this.socket.updateToken(token.id, Number(token.version || 1), patch);
                } else {
                    await this.api.updateToken(this.campaignId, this.sessionId, token.id, Number(token.version || 1), patch);
                    await this.loadBootstrap();
                }
            } catch (error) {
                this._showMessage(error.message || "HP konnten nicht gesetzt werden.", true);
            }
        }

        // DM helper: roll a d20 for every token that has no initiative yet,
        // via the normal token-update path so every client's turn-order
        // widget fills in live. Tokens with a value keep it (reroll = clear
        // first, by rolling again after a fresh round is a follow-up).
        async _rollInitiativeForTokens() {
            const tokens = Array.isArray(this.bootstrap?.state_payload?.tokens) ? this.bootstrap.state_payload.tokens : [];
            if (!tokens.length) {
                this._showMessage("Keine Tokens auf der Karte.", true);
                return;
            }
            let rolled = 0;
            for (const token of tokens) {
                const roll = 1 + Math.floor(Math.random() * 20);
                try {
                    if (this.socket && this.socket.isConnected) {
                        this.socket.updateToken(token.id, Number(token.version || 1), { initiative: roll });
                    } else {
                        await this.api.updateToken(this.campaignId, this.sessionId, token.id, Number(token.version || 1), { initiative: roll });
                    }
                    rolled += 1;
                } catch (error) {
                    this._logActivity(`Initiative für ${token.name} fehlgeschlagen.`, "error");
                }
            }
            if (!(this.socket && this.socket.isConnected)) {
                await this.loadBootstrap();
            }
            this._logActivity(`Initiative für ${rolled} Token(s) gewürfelt.`, "info");
        }

        _bindWidgetToggles() {
            document.querySelectorAll(".widget-toggle[data-widget]").forEach((header) => {
                const toggle = () => {
                    const widget = document.getElementById(header.getAttribute("data-widget"));
                    if (!widget) return;
                    const collapsed = widget.classList.toggle("collapsed");
                    header.setAttribute("aria-expanded", String(!collapsed));
                };
                header.addEventListener("click", toggle);
                header.addEventListener("keydown", (event) => {
                    if (event.key !== "Enter" && event.key !== " ") return;
                    event.preventDefault();
                    toggle();
                });
            });
            // The layer panel is the first-run entry point for the table:
            // leave it open so a DM can add the first map without hunting
            // for a collapsed heading. The less frequent widgets remain
            // compact until explicitly opened.
            const layersWidget = document.getElementById("layersWidget");
            const turnWidget = document.getElementById("turnOrderWidget");
            const tokenWidget = document.getElementById("tokenWidget");
            const layersToggle = layersWidget?.querySelector(".widget-toggle");
            if (layersWidget) layersWidget.classList.remove("collapsed");
            if (layersToggle) layersToggle.setAttribute("aria-expanded", "true");
            if (turnWidget) turnWidget.classList.add("collapsed");
            if (tokenWidget) tokenWidget.classList.add("collapsed");
            turnWidget?.querySelector(".widget-toggle")?.setAttribute("aria-expanded", "false");
            tokenWidget?.querySelector(".widget-toggle")?.setAttribute("aria-expanded", "false");
        }

        _setupTableSheet() {
            // GD-Sheet-Muster: unterhalb 1040px wandern die drei Panels in
            // ein Bottom-Sheet, das aus dem Ribbon öffnet; auf dem Desktop
            // bleiben sie schwebende Widgets. IDs bleiben stabil — die
            // Desktop-Robots (fullsession/flows) greifen weiter direkt zu.
            const sheet = document.getElementById("tableSheet");
            const backdrop = document.getElementById("tableSheetBackdrop");
            const btn = document.getElementById("btnTableSheet");
            const body = document.getElementById("tableSheetBody");
            if (!sheet || !btn || !body) return;
            const stage = document.querySelector(".stage");
            const media = window.matchMedia("(max-width: 1040px)");
            const widgetIds = ["layersWidget", "turnOrderWidget", "tokenWidget"];
            const place = () => {
                widgetIds.forEach((id) => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    if (media.matches && el.parentElement !== body) {
                        body.appendChild(el);
                    } else if (!media.matches && el.parentElement === body && stage) {
                        stage.appendChild(el);
                    }
                });
            };
            const setOpen = (open) => {
                sheet.hidden = !open;
                if (backdrop) backdrop.hidden = !open;
                btn.classList.toggle("active", open);
                btn.setAttribute("aria-expanded", String(open));
            };
            btn.addEventListener("click", () => setOpen(sheet.hidden));
            if (backdrop) backdrop.addEventListener("click", () => setOpen(false));
            document.getElementById("btnTableSheetBack")?.addEventListener("click", () => {
                document.getElementById("btnBack")?.click();
            });
            place();
            if (typeof media.addEventListener === "function") {
                media.addEventListener("change", place);
            }
        }

        _bindTableActions() {
            const confirmBtn = document.getElementById("btnTokenCreateConfirm");
            const cancelBtn = document.getElementById("btnTokenCreateCancel");
            if (confirmBtn) confirmBtn.addEventListener("click", () => this._confirmTokenPlacement());
            if (cancelBtn) cancelBtn.addEventListener("click", () => this._cancelTokenPlacement());
            const nameInput = document.getElementById("tokenCreateName");
            if (nameInput) {
                nameInput.addEventListener("keydown", (event) => {
                    if (event.key === "Enter") {
                        event.preventDefault();
                        this._confirmTokenPlacement();
                    } else if (event.key === "Escape") {
                        this._cancelTokenPlacement();
                    }
                });
            }

            const deleteBtn = document.getElementById("btnTokenDelete");
            if (deleteBtn) deleteBtn.addEventListener("click", () => this._deleteSelectedToken());
            const hpBtn = document.getElementById("btnTokenHpSet");
            if (hpBtn) hpBtn.addEventListener("click", () => this._setSelectedTokenHp());

            // Token art: one picker on the create panel (image applied when
            // the token is placed) and one on the selected-token detail
            // (image applied to an existing token).
            const createImageBtn = document.getElementById("btnTokenCreateImage");
            const createImageInput = document.getElementById("tokenCreateImageFile");
            if (createImageBtn && createImageInput) {
                createImageBtn.addEventListener("click", () => createImageInput.click());
                createImageInput.addEventListener("change", async () => {
                    const file = createImageInput.files && createImageInput.files[0];
                    createImageInput.value = "";
                    if (!file) return;
                    const label = document.getElementById("tokenCreateImageLabel");
                    try {
                        if (label) label.textContent = "Lade hoch...";
                        const uploaded = await this._uploadAssetFile(file, "token");
                        this.pendingTokenImage = `/api/assets/${uploaded.asset_id}/preview`;
                        if (label) label.textContent = file.name.slice(0, 24);
                    } catch (error) {
                        this.pendingTokenImage = null;
                        if (label) label.textContent = "Bild (optional)...";
                        this._showMessage(error.message || "Token-Bild-Upload fehlgeschlagen.", true);
                    }
                });
            }
            const setImageBtn = document.getElementById("btnTokenImageSet");
            const setImageInput = document.getElementById("tokenImageFile");
            if (setImageBtn && setImageInput) {
                setImageBtn.addEventListener("click", () => setImageInput.click());
                setImageInput.addEventListener("change", async () => {
                    const file = setImageInput.files && setImageInput.files[0];
                    setImageInput.value = "";
                    const token = this._findStateToken(this.selectedTokenId);
                    if (!file || !token || !this._canMoveToken(token)) return;
                    try {
                        const uploaded = await this._uploadAssetFile(file, "token");
                        const metadataJson = token.metadata_json && typeof token.metadata_json === "object"
                            ? { ...token.metadata_json } : {};
                        metadataJson.image_url = `/api/assets/${uploaded.asset_id}/preview`;
                        this._patchToken(token, { metadata_json: metadataJson });
                        this._logActivity(`Token-Bild gesetzt: ${token.name}.`, "info");
                    } catch (error) {
                        this._showMessage(error.message || "Token-Bild-Upload fehlgeschlagen.", true);
                    }
                });
            }

            // DM shortcut: upload token art before placing the token. The
            // image is kept as pending state, then attached to the next
            // token created through TOK + map click. This removes the old
            // requirement to discover the create panel before a file dialog
            // was available.
            const tokenUploadBtn = document.getElementById("btnTokenUpload");
            const tokenUploadInput = document.getElementById("tokenUploadFile");
            if (tokenUploadBtn && tokenUploadInput) {
                tokenUploadBtn.addEventListener("click", () => tokenUploadInput.click());
                tokenUploadInput.addEventListener("change", async () => {
                    const file = tokenUploadInput.files && tokenUploadInput.files[0];
                    tokenUploadInput.value = "";
                    if (!file) return;
                    const status = document.getElementById("tokenUploadStatus");
                    try {
                        if (status) status.textContent = "Lade hoch...";
                        const uploaded = await this._uploadAssetFile(file, "token");
                        this.pendingTokenImage = `/api/assets/${uploaded.asset_id}/preview`;
                        this.pendingTokenImageLabel = file.name.slice(0, 24);
                        if (status) status.textContent = "Tokenbild geladen – auf die Karte klicken.";
                        this._setTool("token");
                        this._showMessage("Tokenbild geladen. Klicke auf die Karte, um den Token zu platzieren.");
                    } catch (error) {
                        this.pendingTokenImage = null;
                        this.pendingTokenImageLabel = "";
                        if (status) status.textContent = "Upload fehlgeschlagen.";
                        this._showMessage(error.message || "Token-Bild-Upload fehlgeschlagen.", true);
                    }
                });
            }

            const initiativeBtn = document.getElementById("btnRollInitiative");
            if (initiativeBtn) initiativeBtn.addEventListener("click", () => this._rollInitiativeForTokens());

            // Server-Kampf (Playtable-Vordermann 2026-08-25).
            const startCombatBtn = document.getElementById("btnStartCombat");
            if (startCombatBtn) startCombatBtn.addEventListener("click", () => this._startCombat());
            const nextTurnBtn = document.getElementById("btnNextTurn");
            if (nextTurnBtn) nextTurnBtn.addEventListener("click", () => this._advanceCombatTurn());
            const endCombatBtn = document.getElementById("btnEndCombat");
            if (endCombatBtn) endCombatBtn.addEventListener("click", () => this._endCombat());

            // Charakterbogen-Lade.
            const openSheetBtn = document.getElementById("btnOpenSheet");
            if (openSheetBtn) openSheetBtn.addEventListener("click", () => {
                const sheetRow = document.getElementById("sheetButtonRow");
                this._openSheet(sheetRow?.dataset.characterId,
                                sheetRow?.dataset.characterName);
            });
            const closeSheetBtn = document.getElementById("btnCloseSheet");
            if (closeSheetBtn) closeSheetBtn.addEventListener("click", () => this._closeSheet());
            document.addEventListener("keydown", (event) => {
                if (event.key === "Escape") this._closeSheet();
            });

            this._bindMapUpload();
        }

        // Upload a map image straight from the table: asset upload ->
        // CampaignMap create (pixel dims from the upload response) -> scene
        // stack layer -> activate. This is the same three-endpoint
        // choreography the campaign hub uses; before this the play table
        // had no upload path at all (robot audit 2026-08-23).
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

        // One multipart uploader for every table asset (maps, token art).
        async _uploadAssetFile(file, assetType) {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("asset_type", assetType);
            const response = await fetch(`/api/assets/campaigns/${this.campaignId}/upload`, {
                method: "POST",
                credentials: "include",
                headers: Auth.buildHeaders("POST", false),
                body: formData,
            });
            const body = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(body.error || `Upload fehlgeschlagen (HTTP ${response.status})`);
            }
            return body;
        }

        async _uploadMapFromTable(file) {
            const statusNode = document.getElementById("mapUploadStatus");
            const setStatus = (text) => {
                if (statusNode) {
                    statusNode.hidden = !text;
                    statusNode.textContent = text || "";
                }
            };
            const gridSize = Math.max(16, Math.min(300, Number(document.getElementById("mapUploadGridSize")?.value) || 70));

            try {
                setStatus(`Lade ${file.name} hoch...`);
                const uploadBody = await this._uploadAssetFile(file, "map");

                setStatus("Erzeuge Karte...");
                // Eingegebener Seitenname gewinnt gegen den Dateinamen —
                // sonst heißen Karten wie ihre Asset-Hashes.
                const enteredName = document.getElementById("layerAddName")?.value.trim() || "";
                const mapName = (enteredName || file.name.replace(/\.[^.]+$/, "")).slice(0, 120) || "Neue Karte";
                const created = await this.auth.makeAuthRequest(`/api/campaigns/${this.campaignId}/maps`, "POST", {
                    name: mapName,
                    width: Number(uploadBody.width) || 1400,
                    height: Number(uploadBody.height) || 1000,
                    grid_size: gridSize,
                    background_url: `/api/assets/${uploadBody.asset_id}/preview`,
                });

                setStatus("Füge Seite hinzu...");
                const stack = this.bootstrap?.scene_stack;
                if (stack && Array.isArray(stack.layers)) {
                    const layerResult = await this.api.addLayer(this.campaignId, this.sessionId, created.id, mapName);
                    const newLayer = layerResult?.layer || (layerResult?.scene_stack?.layers || []).find(
                        (l) => Number(l.campaign_map_id) === Number(created.id)
                    );
                    if (newLayer?.id) {
                        await this.api.activateLayer(this.campaignId, this.sessionId, newLayer.id);
                    }
                } else {
                    await this.api.initSceneStack(this.campaignId, this.sessionId, [created.id]);
                }

                setStatus("");
                const nameInput = document.getElementById("layerAddName");
                if (nameInput) nameInput.value = "";
                const choice = document.getElementById("layerAddChoice");
                if (choice) choice.hidden = true;
                this._showMessage(`Karte "${mapName}" hochgeladen und aktiviert.`);
                await this.loadBootstrap();
            } catch (error) {
                setStatus("");
                this._showMessage(error.message || "Karten-Upload fehlgeschlagen.", true);
            }
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

                this._logActivity(`Start-Check ausgeführt (startbar=${result.can_start ? "ja" : "nein"}).`, "info");
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
            this._logActivity(`Token gelöscht: #${tokenId}.`, "info");
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

        _handleExternalRoll(payload) {
            const roll = payload?.roll || {};
            const summary = payload?.summary
                || `[${roll.source || "external"}] ${roll.character || payload?.sender_name || "?"}: ${roll.title || roll.formula || "Wurf"}${roll.total != null ? ` = ${roll.total}` : ""}`;
            const log = document.getElementById("diceLog");
            if (log) {
                log.prepend(this._buildExternalRollCard(roll, payload));
                while (log.children.length > 8) {
                    log.removeChild(log.lastChild);
                }
            }
            this._appendChatMessage({
                time: String(payload?.timestamp || new Date().toISOString()).slice(11, 19),
                sender_name: roll.character || payload?.sender_name || "external",
                message: summary,
            });
            this._logActivity(summary, "info");
        }

        // Rich roll card: header (character + title), one row per
        // component roll (label / formula / dice / total), context lines
        // (save DCs etc). Built with DOM nodes + textContent only -- the
        // envelope is server-sanitized, but external strings still never
        // become HTML here.
        _buildExternalRollCard(roll, payload) {
            const card = document.createElement("div");
            const advantage = String(roll.advantage || "normal");
            card.className = `ext-roll-card${advantage === "crit" ? " crit" : ""}${advantage === "fumble" ? " fumble" : ""}`;

            const header = document.createElement("div");
            header.className = "ext-roll-header";
            const who = document.createElement("strong");
            who.textContent = roll.character || payload?.sender_name || "extern";
            header.appendChild(who);
            const title = document.createElement("span");
            title.textContent = ` ${roll.title || roll.formula || "Wurf"}`;
            header.appendChild(title);
            if (advantage === "crit") {
                const badge = document.createElement("span");
                badge.className = "ext-roll-badge";
                badge.textContent = "KRIT!";
                header.appendChild(badge);
            }
            card.appendChild(header);

            const rolls = Array.isArray(roll.rolls) ? roll.rolls : [];
            rolls.slice(0, 8).forEach((entry) => {
                const row = document.createElement("div");
                row.className = `ext-roll-row${entry.kind ? ` kind-${entry.kind}` : ""}`;
                const label = document.createElement("span");
                label.className = "ext-roll-label";
                label.textContent = entry.label || entry.kind || "Wurf";
                row.appendChild(label);
                const detail = document.createElement("span");
                const dice = Array.isArray(entry.dice) && entry.dice.length
                    ? ` [${entry.dice.join(", ")}]` : "";
                detail.textContent = `${entry.formula || ""}${dice}`;
                row.appendChild(detail);
                const total = document.createElement("span");
                total.className = "ext-roll-total";
                total.textContent = entry.total != null ? String(entry.total) : "-";
                row.appendChild(total);
                card.appendChild(row);
            });
            if (!rolls.length && roll.total != null) {
                const row = document.createElement("div");
                row.className = "ext-roll-row";
                row.textContent = `${roll.formula || ""} = ${roll.total}`;
                card.appendChild(row);
            }

            const info = Array.isArray(roll.info) ? roll.info : [];
            info.slice(0, 4).forEach((line) => {
                const infoRow = document.createElement("div");
                infoRow.className = "ext-roll-info";
                infoRow.textContent = line;
                card.appendChild(infoRow);
            });

            const source = document.createElement("div");
            source.className = "ext-roll-source";
            source.textContent = `via ${roll.source || "extern"}${roll.system ? ` · ${roll.system}` : ""}`;
            card.appendChild(source);
            return card;
        }

        _handleDiceBroadcast(payload) {
            const log = document.getElementById("diceLog");
            const line = document.createElement("div");
            line.textContent = `${payload.player || "player"} hat ${payload.dice} gewürfelt: ${payload.result?.total}`;
            log.prepend(line);
            while (log.children.length > 8) {
                log.removeChild(log.lastChild);
            }
            this._logActivity(`${payload.player || "player"} hat ${payload.dice} gewürfelt.`, "info");
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
                notice.textContent = "Nur-Lesen ist aktiv für deine Rolle oder den Session-Status.";
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

        _thumbUrl(campaignMap) {
            // background_url is /api/assets/<id>/preview (see M1 wiring in
            // campaigns.html) - the thumbnail endpoint from M4 lives at the
            // same asset id, so this avoids needing to thread asset_id
            // through CampaignMap just for a preview image.
            const url = campaignMap?.background_url || "";
            return url.includes("/preview") ? url.replace("/preview", "/thumbnail") : url;
        }

        async _renderLayers() {
            const stack = this.bootstrap?.scene_stack;
            const container = document.getElementById("layerList");
            const layers = (stack && Array.isArray(stack.layers)) ? stack.layers.slice().sort((a, b) => a.order_index - b.order_index) : [];

            if (!layers.length) {
                container.innerHTML = "<div class='muted'>Noch keine Seiten. Unten eine Karte hinzufügen.</div>";
            } else {
                container.innerHTML = layers.map((layer, index) => {
                    const isActive = Number(layer.id) === Number(stack.active_layer_id);
                    const mapName = escapeHtml(layer.campaign_map?.name || `Map ${layer.campaign_map_id}`);
                    const thumb = this._thumbUrl(layer.campaign_map);
                    const visIcon = layer.is_player_visible ? "&#128065;" : "&#128683;";
                    const activateControl = isActive
                        ? `<span class="mini-btn" style="opacity:0.7;cursor:default;">aktiv</span>`
                        : `<button data-act="activate" data-layer-id="${layer.id}" class="mini-btn">Aktivieren</button>`;
                    return `
                        <div class="layer-row ${isActive ? "active-row" : ""}" data-layer-id="${layer.id}">
                            ${thumb ? `<img class="layer-thumb" src="${thumb}" alt="">` : `<div class="layer-thumb"></div>`}
                            <div class="layer-info">
                                <input class="layer-label-input" data-act="rename" data-layer-id="${layer.id}" value="${escapeHtml(layer.label)}" ${this.readOnly ? "disabled" : ""}>
                                <div class="layer-map-name">${mapName}</div>
                            </div>
                            <div class="layer-actions">
                                <div class="layer-actions-row">
                                    <button data-act="up" data-layer-id="${layer.id}" class="mini-btn layer-icon-btn" title="Nach oben" ${index === 0 ? "disabled" : ""}>&uarr;</button>
                                    <button data-act="down" data-layer-id="${layer.id}" class="mini-btn layer-icon-btn" title="Nach unten" ${index === layers.length - 1 ? "disabled" : ""}>&darr;</button>
                                    <button data-act="visibility" data-layer-id="${layer.id}" data-current="${layer.is_player_visible}" class="mini-btn layer-icon-btn" title="Spieler-Sichtbarkeit">${visIcon}</button>
                                    <button data-act="delete" data-layer-id="${layer.id}" class="mini-btn layer-icon-btn danger" title="Seite entfernen">&times;</button>
                                </div>
                                ${activateControl}
                            </div>
                        </div>
                    `;
                }).join("");

                if (!this.readOnly) {
                    container.querySelectorAll('[data-act="activate"]').forEach((button) => {
                        button.addEventListener("click", () => this._activateLayer(Number(button.dataset.layerId)));
                    });
                    container.querySelectorAll('[data-act="rename"]').forEach((input) => {
                        input.addEventListener("change", () => this._renameLayer(Number(input.dataset.layerId), input.value));
                    });
                    container.querySelectorAll('[data-act="visibility"]').forEach((button) => {
                        button.addEventListener("click", () => this._toggleLayerVisibility(Number(button.dataset.layerId), button.dataset.current !== "true"));
                    });
                    container.querySelectorAll('[data-act="delete"]').forEach((button) => {
                        button.addEventListener("click", () => this._deleteLayer(Number(button.dataset.layerId)));
                    });
                    container.querySelectorAll('[data-act="up"]:not(:disabled)').forEach((button) => {
                        button.addEventListener("click", () => this._moveLayer(Number(button.dataset.layerId), -1));
                    });
                    container.querySelectorAll('[data-act="down"]:not(:disabled)').forEach((button) => {
                        button.addEventListener("click", () => this._moveLayer(Number(button.dataset.layerId), 1));
                    });
                }
            }

            if (!this.readOnly) {
                await this._renderLayerAddControl(layers);
            }
        }

        async _renderLayerAddControl(existingLayers) {
            // UI-Regel (Adrian, 2026-08-25): „Hinzufügen" ist der eine Weg
            // zu einer neuen Seite.  Klick öffnet die Wahl: neue Karte
            // hochladen ODER eine vorhandene übernehmen — bereits als Seite
            // verwendete Karten werden dabei serverseitig kopiert, es gibt
            // keine „alle Karten sind bereits Seiten"-Sackgasse mehr.
            const addBtn = document.getElementById("layerAddBtn");
            const choice = document.getElementById("layerAddChoice");
            const source = document.getElementById("layerAddSource");
            const copyBtn = document.getElementById("layerAddCopy");
            const uploadBtn = document.getElementById("layerAddUpload");
            const cancelBtn = document.getElementById("layerAddCancel");
            const nameInput = document.getElementById("layerAddName");
            const status = document.getElementById("layerAddStatus");
            if (!addBtn || !choice || !source) return;

            const setStatus = (message) => {
                if (!status) return;
                status.textContent = message || "";
                status.hidden = !message;
            };

            const usedMapIds = new Set(existingLayers.map((l) => Number(l.campaign_map_id)));
            try {
                const maps = await this.api.campaignMaps(this.campaignId);
                // Die Maps-API antwortet {maps: [...]} — das alte nackte
                // Array-Parsing ließ die Auswahl IMMER leer und war die
                // eigentliche Ursache des Sackgassen-Menüs (2026-08-25).
                const rows = Array.isArray(maps) ? maps
                    : (Array.isArray(maps?.maps) ? maps.maps : []);
                source.innerHTML = rows.length
                    ? rows.map((m) => `<option value="${m.id}">${escapeHtml(m.name)}${usedMapIds.has(Number(m.id)) ? " — wird kopiert" : ""}</option>`).join("")
                    : `<option value="">Noch keine Karte — lade eine hoch</option>`;
                if (copyBtn) copyBtn.disabled = rows.length === 0;
                setStatus("");
            } catch (error) {
                source.innerHTML = `<option value="">Karten konnten nicht geladen werden</option>`;
                if (copyBtn) copyBtn.disabled = true;
                setStatus("Karten konnten nicht geladen werden. Prüfe die Verbindung und versuche es erneut.");
            }

            addBtn.onclick = () => {
                choice.hidden = !choice.hidden;
            };
            if (cancelBtn) cancelBtn.onclick = () => {
                choice.hidden = true;
            };
            if (uploadBtn) uploadBtn.onclick = () => {
                document.getElementById("mapUploadFile")?.click();
            };
            if (copyBtn) copyBtn.onclick = async () => {
                const mapId = Number(source.value);
                if (!mapId) return;
                copyBtn.disabled = true;
                try {
                    const label = nameInput?.value.trim() || null;
                    await this.api.addLayer(this.campaignId, this.sessionId, mapId, label, true);
                    this._showMessage("Seite hinzugefügt.");
                    if (nameInput) nameInput.value = "";
                    choice.hidden = true;
                    await this.loadBootstrap();
                } catch (error) {
                    this._showMessage(error.message || "Seite konnte nicht hinzugefügt werden.", true);
                    copyBtn.disabled = false;
                }
            };
        }

        async _activateLayer(layerId) {
            try {
                await this.api.activateLayer(this.campaignId, this.sessionId, layerId);
                this._showMessage("Seite aktiviert - alle Spieler wechseln mit.");
                this._logActivity(`Seite ${layerId} aktiviert.`, "info");
                await this.loadBootstrap();
            } catch (error) {
                this._showMessage(error.message || "Seite konnte nicht gewechselt werden.", true);
            }
        }

        async _renameLayer(layerId, label) {
            const trimmed = String(label || "").trim();
            if (!trimmed) return;
            try {
                await this.api.updateLayer(this.campaignId, this.sessionId, layerId, { label: trimmed });
                await this.loadBootstrap();
            } catch (error) {
                this._showMessage(error.message || "Umbenennen fehlgeschlagen.", true);
            }
        }

        async _toggleLayerVisibility(layerId, nextVisible) {
            try {
                await this.api.updateLayer(this.campaignId, this.sessionId, layerId, { is_player_visible: nextVisible });
                await this.loadBootstrap();
            } catch (error) {
                this._showMessage(error.message || "Sichtbarkeit konnte nicht geaendert werden.", true);
            }
        }

        async _deleteLayer(layerId) {
            if (!window.confirm("Diese Seite aus dem Kartenstapel entfernen?")) return;
            try {
                await this.api.deleteLayer(this.campaignId, this.sessionId, layerId);
                this._showMessage("Seite entfernt.");
                await this.loadBootstrap();
            } catch (error) {
                this._showMessage(error.message || "Seite konnte nicht entfernt werden.", true);
            }
        }

        async _moveLayer(layerId, direction) {
            const stack = this.bootstrap?.scene_stack;
            const layers = (stack && Array.isArray(stack.layers)) ? stack.layers.slice().sort((a, b) => a.order_index - b.order_index) : [];
            const index = layers.findIndex((l) => Number(l.id) === layerId);
            const swapWith = index + direction;
            if (index === -1 || swapWith < 0 || swapWith >= layers.length) return;

            [layers[index].order_index, layers[swapWith].order_index] = [layers[swapWith].order_index, layers[index].order_index];
            const order = layers.map((l) => ({ layer_id: l.id, order_index: l.order_index }));
            try {
                await this.api.reorderLayers(this.campaignId, this.sessionId, order);
                await this.loadBootstrap();
            } catch (error) {
                this._showMessage(error.message || "Reihenfolge konnte nicht geaendert werden.", true);
            }
        }

        _renderState() {
            const statePayload = this.bootstrap?.state_payload;
            const tokenList = document.getElementById("tokenList");
            const activeMap = statePayload?.active_map;
            const pill = document.getElementById("activePagePill");
            const pillName = document.getElementById("activePageName");
            if (pill && pillName) {
                if (activeMap) {
                    // Prefer the active LAYER's human label: map names can be
                    // upload-derived junk (Adrian's live table showed a raw
                    // hash as "Seite:"), while layer labels are typed by the
                    // DM in the add-page flow.
                    const stack = this.bootstrap?.scene_stack;
                    const activeLayer = (stack?.layers || []).find(
                        (layer) => Number(layer.id) === Number(stack?.active_layer_id));
                    pillName.textContent = (activeLayer?.label || "").trim() || activeMap.name;
                    pill.hidden = false;
                } else {
                    pill.hidden = true;
                }
            }

            const operator = isOperatorRole(this.bootstrap?.session_role || "");
            const gridSize = Math.max(16, Number(activeMap?.grid_size) || 70);
            const tokens = this._visibleTokens(statePayload?.tokens || []);
            if (!this._isTokenAvailable(this.selectedTokenId, tokens)) {
                this.selectedTokenId = null;
            }
            if (!tokens.length) {
                tokenList.innerHTML = "<div class='muted'>Keine Tokens. Mit dem TOK-Werkzeug auf die Karte klicken.</div>";
            } else {
                tokenList.innerHTML = tokens.map((token) => {
                    const cell = this._resolveTokenPosition(token, gridSize);
                    const cellX = Math.round(cell.left / gridSize);
                    const cellY = Math.round(cell.top / gridSize);
                    const conditions = Array.isArray(token.metadata_json?.conditions)
                        ? token.metadata_json.conditions : [];
                    const conditionsLine = conditions.length
                        ? `<div class="token-conditions-line">${escapeHtml(conditions.join(", "))}</div>`
                        : "";
                    return `
                    <div class="panel-row ${Number(this.selectedTokenId) === Number(token.id) ? "active-row" : ""}" data-token-id="${token.id}" style="cursor:pointer;display:block;">
                        <div style="display:flex;justify-content:space-between;gap:0.5rem;">
                            <div><strong>${escapeHtml(token.name)}</strong> (${escapeHtml(token.token_type)})</div>
                            <div>HP ${token.hp_current ?? "-"} / ${token.hp_max ?? "-"}, Feld ${cellX},${cellY}</div>
                        </div>
                        ${conditionsLine}
                    </div>
                `;
                }).join("");
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
            const selectedDetail = document.getElementById("tokenSelectionDetail");
            const selectedToken = this._findStateToken(this.selectedTokenId);
            if (selectedSummary) {
                selectedSummary.textContent = selectedToken
                    ? `Ausgewählt: ${selectedToken.name} (#${selectedToken.id})`
                    : "Kein Token ausgewählt.";
            }
            if (selectedDetail) {
                const canEditSelected = selectedToken && this._canMoveToken(selectedToken);
                selectedDetail.hidden = !canEditSelected;
                if (canEditSelected) {
                    const hpCurrent = document.getElementById("tokenHpCurrent");
                    const hpMax = document.getElementById("tokenHpMax");
                    if (hpCurrent) hpCurrent.value = selectedToken.hp_current ?? "";
                    if (hpMax) hpMax.value = selectedToken.hp_max ?? "";
                }
            }

            // DM-only table controls: map upload and initiative rolling.
            const layerAddRow = document.getElementById("layerAddRow");
            if (layerAddRow) layerAddRow.hidden = !operator || this.readOnly;
            if (!operator || this.readOnly) {
                const layerAddChoice = document.getElementById("layerAddChoice");
                if (layerAddChoice) layerAddChoice.hidden = true;
            }
            const initiativeControls = document.getElementById("initiativeControls");
            if (initiativeControls) initiativeControls.hidden = !operator || this.readOnly;
            const combatActive = this._combatActive();
            const startCombatBtn = document.getElementById("btnStartCombat");
            if (startCombatBtn) startCombatBtn.hidden = combatActive;
            const nextTurnBtn = document.getElementById("btnNextTurn");
            if (nextTurnBtn) nextTurnBtn.hidden = !combatActive;
            const endCombatBtn = document.getElementById("btnEndCombat");
            if (endCombatBtn) endCombatBtn.hidden = !combatActive;
            const legacyInitiativeBtn = document.getElementById("btnRollInitiative");
            if (legacyInitiativeBtn) legacyInitiativeBtn.hidden = combatActive;

            // Charakterbogen am Tisch: sichtbar für den Besitzer des
            // ausgewählten Tokens und für Operatoren, sobald ein Charakter
            // verknüpft ist.
            const sheetRow = document.getElementById("sheetButtonRow");
            if (sheetRow) {
                const sheetToken = this._findStateToken(this.selectedTokenId);
                const canOpenSheet = Boolean(sheetToken && sheetToken.character_id
                    && (operator || Number(sheetToken.owner_user_id) === Number(this.user?.id)));
                sheetRow.hidden = !canOpenSheet;
                if (canOpenSheet) {
                    sheetRow.dataset.characterId = String(sheetToken.character_id);
                    sheetRow.dataset.characterName = sheetToken.name || "";
                }
            }
            const tokenToolBtn = document.querySelector('.tool-btn[data-tool="token"]');
            if (tokenToolBtn) tokenToolBtn.style.display = this.readOnly ? "none" : "";
            const tokenUploadRow = document.getElementById("tokenUploadRow");
            if (tokenUploadRow) tokenUploadRow.hidden = !operator || this.readOnly;

            const mapMetaText = document.getElementById("mapMetaText");
            if (mapMetaText) {
                if (!activeMap) {
                    mapMetaText.textContent = "Keine aktive Karte.";
                } else {
                    mapMetaText.textContent = `${activeMap.name} (${activeMap.width}x${activeMap.height}), Grid ${activeMap.grid_size || 70}px`;
                }
            }
        }

        _renderMapCanvas() {
            const statePayload = this.bootstrap?.state_payload || {};
            const activeMap = statePayload.active_map;
            const allTokens = Array.isArray(statePayload.tokens) ? statePayload.tokens : [];
            // dm_only tokens are hidden from non-operator viewers. (The
            // server currently still sends them - server-side filtering is
            // tracked as a follow-up; this at least makes the UI honest.)
            const tokens = this._visibleTokens(allTokens);
            const mapWorld = document.getElementById("mapWorld");
            const mapImage = document.getElementById("mapImage");
            const mapGrid = document.getElementById("mapGridLayer");
            const tokenLayer = document.getElementById("mapTokenLayer");
            if (!mapWorld || !mapImage || !mapGrid || !tokenLayer) return;

            const gridSize = Math.max(16, Number(activeMap?.grid_size) || 70);
            // width/height semantics healed in place: maps made through the
            // upload paths store PIXEL dimensions; older hand-made maps
            // stored GRID-CELL counts (20x15 etc.). Values that small can't
            // be a real pixel surface, so they are treated as cells. The old
            // renderer instead clamped everything to >=900x600, which
            // letterboxed/stretched every map that didn't match (the "scale
            // is bad" bug, robot audit 2026-08-23).
            const rawWidth = Number(activeMap?.width) || 0;
            const rawHeight = Number(activeMap?.height) || 0;
            const width = activeMap
                ? Math.round(rawWidth > 200 ? rawWidth : Math.max(1, rawWidth) * gridSize)
                : 1800;
            const height = activeMap
                ? Math.round(rawHeight > 200 ? rawHeight : Math.max(1, rawHeight) * gridSize)
                : 1200;
            mapWorld.style.width = `${width}px`;
            mapWorld.style.height = `${height}px`;
            mapGrid.style.backgroundSize = `${gridSize}px ${gridSize}px`;
            mapWorld.dataset.gridSize = String(gridSize);
            mapWorld.dataset.mapWidth = String(width);
            mapWorld.dataset.mapHeight = String(height);
            mapWorld.dataset.hasMap = activeMap ? "true" : "false";
            this._syncExtent();

            const emptyState = document.getElementById("mapEmptyState");
            if (emptyState) {
                emptyState.style.display = activeMap ? "none" : "flex";
            }

            if (activeMap?.background_url) {
                if (mapImage.getAttribute("src") !== activeMap.background_url) {
                    mapImage.src = activeMap.background_url;
                }
                mapImage.style.display = "block";
            } else {
                mapImage.removeAttribute("src");
                mapImage.style.display = "none";
            }

            // First render of a newly-activated map: fit it to the screen
            // once, then leave the zoom alone so manual choices stick.
            const activeMapId = activeMap ? Number(activeMap.id) : null;
            if (activeMapId !== null && activeMapId !== this.autoFitMapId) {
                this.autoFitMapId = activeMapId;
                this._zoomFit();
            }

            this.tokenIndex = new Map(allTokens.map((token) => [Number(token.id), token]));
            const initiativeEntries = this._getInitiativeEntries(tokens);
            const currentTurnEntry = initiativeEntries.find((entry) => entry.is_current_turn)
                || initiativeEntries[0] || null;
            const currentTurnTokenId = currentTurnEntry ? Number(currentTurnEntry.id) : null;
            tokenLayer.innerHTML = tokens.map((token) => {
                const position = this._resolveTokenPosition(token, gridSize);
                const pixelSize = this._resolveTokenSize(token, gridSize);
                const rawName = String(token.name || "");
                const label = escapeHtml(rawName);
                const initials = escapeHtml(rawName.trim().slice(0, 2).toUpperCase() || "??");
                const conditions = Array.isArray(token.metadata_json?.conditions)
                    ? token.metadata_json.conditions : [];
                const conditionsBadge = conditions.length
                    ? `<div class="token-conditions" title="${escapeHtml(conditions.join(", "))}">${conditions.length}</div>`
                    : "";
                // Token art (metadata_json.image_url): same-origin asset
                // URLs only -- anything else falls back to initials.
                const rawImageUrl = String(token.metadata_json?.image_url || "");
                const imageUrl = rawImageUrl.startsWith("/api/assets/") ? rawImageUrl : "";
                const face = imageUrl
                    ? `<img class="token-image" src="${escapeHtml(imageUrl)}" alt="">`
                    : "";
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
                        ${face || initials}
                        ${conditionsBadge}
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

            // Active server encounter: render rounds/turns from the combat
            // backend. Hidden participants are already filtered server-side;
            // a hidden active actor arrives as active_token_id = null.
            if (this._combatActive()) {
                const encounter = this.combat.encounter;
                const byId = new Map((this.combat.participants || [])
                    .map((token) => [Number(token.id), token]));
                const order = (encounter.initiative_order || [])
                    .map((tokenId) => byId.get(Number(tokenId)))
                    .filter(Boolean);
                const active = byId.get(Number(encounter.active_token_id)) || null;
                if (summary) {
                    summary.textContent = `Runde ${encounter.round_number} · Am Zug: `
                        + (active ? active.name : "Verdeckter Akteur");
                }
                container.innerHTML = order.length ? order.map((token) => `
                    <div class="turn-item ${Number(token.id) === Number(encounter.active_token_id) ? "is-active" : ""}">
                        <span>${escapeHtml(token.name)}</span>
                        <span class="turn-score">${escapeHtml(token.initiative)}</span>
                    </div>
                `).join("") : "<div class='muted'>Alle Akteure sind verdeckt.</div>";
                return;
            }

            const tokens = this._visibleTokens();
            const entries = this._getInitiativeEntries(tokens);

            if (!entries.length) {
                container.innerHTML = "<div class='muted'>Noch keine Initiative-Werte.</div>";
                if (summary) summary.textContent = "Noch keine Initiative-Werte.";
                return;
            }

            const currentEntry = entries.find((entry) => entry.is_current_turn) || entries[0];
            if (summary) {
                summary.textContent = `Aktuell: ${currentEntry.name} (${currentEntry.initiative})`;
            }

            container.innerHTML = entries.map((token) => {
                const isCurrent = token === currentEntry;
                return `
                <div class="turn-item ${isCurrent ? "current" : ""}">
                    <span>${escapeHtml(token.name)}${isCurrent ? " <strong>• aktuell</strong>" : ""}</span>
                    <span class="turn-score">${escapeHtml(token.initiative)}</span>
                </div>
            `;
            }).join("");
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

        // Every player-facing token surface (map canvas, sidebar list, turn
        // order, action selectors) must share ONE visibility filter --
        // during the fullsession robot build-out the dm_only filter existed
        // only on the canvas, so hidden tokens still leaked through the
        // token list and turn order for players.
        _visibleTokens(tokens = null) {
            let list = Array.isArray(tokens)
                ? tokens
                : Array.isArray(this.bootstrap?.state_payload?.tokens)
                    ? this.bootstrap.state_payload.tokens
                    : [];
            // Tokens belong to a map (token_states.map_id), but the state
            // payload returns every token in the session -- without this
            // filter, tokens placed on map A kept rendering after the DM
            // switched the table to map B (found while building the
            // fullsession robot).
            const activeMapId = Number(this.bootstrap?.state_payload?.active_map?.id);
            if (Number.isInteger(activeMapId) && activeMapId > 0) {
                list = list.filter((token) => Number(token.map_id) === activeMapId);
            }
            if (isOperatorRole(this.bootstrap?.session_role || "")) {
                return list;
            }
            return list.filter((token) => String(token.visibility || "public") !== "dm_only");
        }

        // Shared by every external-sync surface (HP/conditions/combat):
        // external tools identify characters by display name.
        _findTokenByName(rawName) {
            const name = String(rawName || "").trim().toLowerCase();
            if (!name) return null;
            return this._visibleTokens().find(
                (entry) => String(entry.name || "").trim().toLowerCase() === name
            ) || null;
        }

        _patchToken(token, patch) {
            if (this.socket && this.socket.isConnected) {
                this.socket.updateToken(token.id, Number(token.version || 1), patch);
            } else {
                this.api.updateToken(this.campaignId, this.sessionId, token.id, Number(token.version || 1), patch)
                    .then(() => this.loadBootstrap())
                    .catch(() => {});
            }
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
                    // Set by the external turn tracker sync (Beyond20
                    // update-combat); without it the top initiative counts
                    // as "current" like before.
                    is_current_turn: Boolean(token.metadata_json?.current_turn),
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
                const gridSize = Number(document.getElementById("mapWorld")?.dataset?.gridSize || this.bootstrap?.state_payload?.active_map?.grid_size || 70);
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
            const tokens = this._visibleTokens();
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
                    text = "Session läuft: Karte pruefen, Tokens bewegen und Würfeln nutzen.";
                } else if (status === "paused") {
                    text = "Session pausiert: Fortsetzen oder sauber beenden.";
                }
            } else {
                text = "Spieler Schnellstart: 1) Karte ansehen 2) Würfeln testen 3) Eine Aktion ausführen.";
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
