class PlaySocketRuntime {
    constructor({ campaignId, sessionId, handlers = {} }) {
        this.campaignId = Number(campaignId);
        this.sessionId = Number(sessionId);
        this.handlers = handlers;
        this.socket = null;
        this.isConnected = false;
        this.lastEventSeq = 0;
        this.isResyncInFlight = false;
    }

    connect() {
        if (typeof io !== "function") {
            throw new Error("socket.io client not loaded");
        }
        this.socket = io({
            withCredentials: true,
        });

        this.socket.on("connect", () => {
            this.isConnected = true;
            this.socket.emit("session:join", {
                campaign_id: this.campaignId,
                session_id: this.sessionId,
            });
            this._fire("connect");
        });

        this.socket.on("disconnect", () => {
            this.isConnected = false;
            this._fire("disconnect");
        });
        this.socket.on("session:joined", (payload) => {
            this._acceptEventSeq(payload?.event_seq);
            this._fire("joined", payload);
        });
        this.socket.on("state:snapshot", (payload) => {
            this._handleSequencedEvent("state:snapshot", payload, "snapshot", true);
            this.isResyncInFlight = false;
        });
        this.socket.on("play:mode", (payload) => this._handleSequencedEvent("play:mode", payload, "mode"));
        this.socket.on("session:state_changed", (payload) => this._handleSequencedEvent("session:state_changed", payload, "stateChanged"));
        this.socket.on("scene:layer_activated", (payload) => this._handleSequencedEvent("scene:layer_activated", payload, "layerActivated"));
        this.socket.on("action:executed", (payload) => this._handleSequencedEvent("action:executed", payload, "actionExecuted"));
        this.socket.on("dice_rolled", (payload) => this._handleSequencedEvent("dice_rolled", payload, "diceRolled"));
        this.socket.on("chat:message_sent", (payload) => this._handleSequencedEvent("chat:message_sent", payload, "chatMessageSent"));
        this.socket.on("token:created", (payload) => this._handleSequencedEvent("token:created", payload, "tokenCreated"));
        this.socket.on("token:updated", (payload) => this._handleSequencedEvent("token:updated", payload, "tokenUpdated"));
        this.socket.on("token:deleted", (payload) => this._handleSequencedEvent("token:deleted", payload, "tokenDeleted"));
        this.socket.on("token:batch_moved", (payload) => this._handleSequencedEvent("token:batch_moved", payload, "tokenBatchMoved"));
        this.socket.on("initiative:updated", (payload) => this._handleSequencedEvent("initiative:updated", payload, "initiativeUpdated"));
        this.socket.on("initiative:turn_changed", (payload) => this._handleSequencedEvent("initiative:turn_changed", payload, "initiativeTurnChanged"));
        this.socket.on("session:paused", (payload) => this._handleSequencedEvent("session:paused", payload, "sessionPaused"));
        this.socket.on("session:resumed", (payload) => this._handleSequencedEvent("session:resumed", payload, "sessionResumed"));
        this.socket.on("session:ended", (payload) => this._handleSequencedEvent("session:ended", payload, "sessionEnded"));
        this.socket.on("state:conflict", (payload) => this._fire("conflict", payload));
        this.socket.on("state:duplicate", (payload) => this._fire("duplicate", payload));
        this.socket.on("state:error", (payload) => this._fire("error", payload));
    }

    requestState() {
        if (!this.socket) return;
        this.socket.emit("state:request", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
        });
    }

    rollDice(dice, player = "player", callback = null) {
        if (!this.socket) return;
        this.socket.emit(
            "roll_dice",
            {
                campaign_id: this.campaignId,
                session_id: this.sessionId,
                dice,
                player,
            },
            callback
        );
    }

    sendChat(message, senderName, senderId = null) {
        if (!this.socket) return;
        this.socket.emit("chat:message_sent", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
            message,
            sender_id: senderId,
            sender_name: senderName,
        });
    }

    updateToken(tokenId, baseVersion, patch, clientEventId = null) {
        if (!this.socket) return;
        this.socket.emit("token:update", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
            token_id: tokenId,
            base_version: baseVersion,
            patch: patch && typeof patch === "object" ? patch : {},
            client_event_id: clientEventId || this._makeClientEventId("tok"),
        });
    }

    createToken(token, clientEventId = null) {
        if (!this.socket) return;
        this.socket.emit("token:create", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
            token: token && typeof token === "object" ? token : {},
            client_event_id: clientEventId || this._makeClientEventId("tok"),
        });
    }

    deleteToken(tokenId, baseVersion, clientEventId = null) {
        if (!this.socket) return;
        this.socket.emit("token:delete", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
            token_id: tokenId,
            base_version: baseVersion,
            client_event_id: clientEventId || this._makeClientEventId("tok"),
        });
    }

    broadcastInitiativeUpdate() {
        if (!this.socket) return;
        this.socket.emit("initiative:updated", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
        });
    }

    broadcastTurnChanged() {
        if (!this.socket) return;
        this.socket.emit("initiative:turn_changed", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
        });
    }

    disconnect() {
        if (!this.socket) return;
        this.socket.emit("session:leave", {
            campaign_id: this.campaignId,
            session_id: this.sessionId,
        });
        this.socket.disconnect();
        this.socket = null;
        this.isConnected = false;
    }

    _acceptEventSeq(rawSeq) {
        const seq = Number(rawSeq);
        if (!Number.isInteger(seq) || seq <= 0) {
            return;
        }
        if (seq > this.lastEventSeq) {
            this.lastEventSeq = seq;
        }
    }

    _requestResync(reasonPayload = {}) {
        if (!this.socket || this.isResyncInFlight) {
            return;
        }
        this.isResyncInFlight = true;
        this._fire("resyncRequested", reasonPayload);
        this.requestState();
    }

    _handleSequencedEvent(eventName, payload, handlerName, allowGap = false) {
        const seq = Number(payload?.event_seq);
        if (!Number.isInteger(seq) || seq <= 0) {
            this._fire(handlerName, payload);
            return;
        }

        if (seq <= this.lastEventSeq) {
            this._fire("staleEventDropped", {
                event_name: eventName,
                event_seq: seq,
                last_event_seq: this.lastEventSeq,
            });
            return;
        }

        if (!allowGap && this.lastEventSeq > 0 && seq > (this.lastEventSeq + 1)) {
            this._requestResync({
                reason: "sequence_gap",
                event_name: eventName,
                expected_seq: this.lastEventSeq + 1,
                received_seq: seq,
            });
            return;
        }

        this.lastEventSeq = seq;
        this._fire(handlerName, payload);
    }

    _fire(name, payload = null) {
        const handler = this.handlers[name];
        if (typeof handler === "function") {
            handler(payload);
        }
    }

    _makeClientEventId(prefix = "evt") {
        if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
            return `${prefix}-${crypto.randomUUID()}`;
        }
        return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
}
