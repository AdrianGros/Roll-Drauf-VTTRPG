class PlayClient {
    constructor(auth) {
        this.auth = auth;
    }

    bootstrap(campaignId, sessionId) {
        return this.auth.makeAuthRequest(`/api/play/campaigns/${campaignId}/sessions/${sessionId}/bootstrap`);
    }

    readyCheck(campaignId, sessionId) {
        return this.auth.makeAuthRequest(`/api/play/campaigns/${campaignId}/sessions/${sessionId}/ready-check`);
    }

    initSceneStack(campaignId, sessionId, mapIds = null) {
        const body = Array.isArray(mapIds) && mapIds.length ? { map_ids: mapIds } : {};
        return this.auth.makeAuthRequest(`/api/play/campaigns/${campaignId}/sessions/${sessionId}/scene-stack/init`, "POST", body);
    }

    activateLayer(campaignId, sessionId, layerId) {
        return this.auth.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/scene-stack/layers/${layerId}/activate`,
            "POST",
            {}
        );
    }

    transition(campaignId, sessionId, targetState, ignoreWarnings = false) {
        return this.auth.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/transition`,
            "POST",
            {
                target_state: targetState,
                ignore_warnings: Boolean(ignoreWarnings),
            }
        );
    }

    executeAction(campaignId, sessionId, tokenId, actionCode, targetTokenId = null, payload = {}) {
        const body = {
            token_id: tokenId,
            action_code: actionCode,
            payload: payload && typeof payload === "object" ? payload : {},
        };
        if (targetTokenId !== null && targetTokenId !== undefined && targetTokenId !== "") {
            body.target_token_id = targetTokenId;
        }
        return this.auth.makeAuthRequest(`/api/play/campaigns/${campaignId}/sessions/${sessionId}/actions/execute`, "POST", body);
    }
}
