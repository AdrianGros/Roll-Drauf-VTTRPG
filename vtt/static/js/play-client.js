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

    addLayer(campaignId, sessionId, campaignMapId, label = null) {
        const body = { campaign_map_id: campaignMapId };
        if (label) body.label = label;
        return this.auth.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/scene-stack/layers`,
            "POST",
            body
        );
    }

    updateLayer(campaignId, sessionId, layerId, patch) {
        return this.auth.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/scene-stack/layers/${layerId}`,
            "PUT",
            patch
        );
    }

    reorderLayers(campaignId, sessionId, order) {
        return this.auth.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/scene-stack/layers/reorder`,
            "PUT",
            { order }
        );
    }

    deleteLayer(campaignId, sessionId, layerId) {
        return this.auth.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/scene-stack/layers/${layerId}`,
            "DELETE"
        );
    }

    campaignMaps(campaignId) {
        return this.auth.makeAuthRequest(`/api/campaigns/${campaignId}/maps`);
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

    updateToken(campaignId, sessionId, tokenId, baseVersion, patch) {
        return this.auth.makeAuthRequest(`/api/campaigns/${campaignId}/sessions/${sessionId}/tokens/${tokenId}`, "PUT", {
            base_version: baseVersion,
            patch: patch && typeof patch === "object" ? patch : {},
        });
    }

    createToken(campaignId, sessionId, token) {
        return this.auth.makeAuthRequest(`/api/campaigns/${campaignId}/sessions/${sessionId}/tokens`, "POST", {
            token: token && typeof token === "object" ? token : {},
        });
    }

    deleteToken(campaignId, sessionId, tokenId, baseVersion) {
        return this.auth.makeAuthRequest(`/api/campaigns/${campaignId}/sessions/${sessionId}/tokens/${tokenId}`, "DELETE", {
            base_version: baseVersion,
        });
    }

    rollInitiative(campaignId, sessionId) {
        return this.auth.makeAuthRequest(`/api/sessions/${sessionId}/initiative/roll`, "POST", {});
    }

    nextTurn(campaignId, sessionId) {
        return this.auth.makeAuthRequest(`/api/sessions/${sessionId}/initiative/next-turn`, "POST", {});
    }
}
