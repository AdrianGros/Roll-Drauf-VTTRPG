/**
 * Community API helpers for chat, reports, and moderation.
 */

class CommunityClient {
    constructor(auth) {
        this.auth = auth;
    }

    static _clientEventId() {
        if (window.crypto && window.crypto.randomUUID) {
            return window.crypto.randomUUID();
        }
        return `evt-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
    }

    async loadMessages(campaignId, sessionId, options = {}) {
        const limit = Number.isInteger(options.limit) ? options.limit : 50;
        const beforeId = options.beforeId ? `&before_id=${encodeURIComponent(options.beforeId)}` : "";
        return this.auth.makeAuthRequest(
            `/api/campaigns/${campaignId}/sessions/${sessionId}/chat/messages?limit=${limit}${beforeId}`
        );
    }

    async sendMessage(campaignId, sessionId, content) {
        return this.auth.makeAuthRequest(
            `/api/campaigns/${campaignId}/sessions/${sessionId}/chat/messages`,
            "POST",
            {
                content,
                client_event_id: CommunityClient._clientEventId(),
            }
        );
    }

    async deleteMessage(campaignId, sessionId, messageId) {
        return this.auth.makeAuthRequest(
            `/api/campaigns/${campaignId}/sessions/${sessionId}/chat/messages/${messageId}`,
            "DELETE"
        );
    }

    async reportMessage(campaignId, sessionId, messageId, reasonCode, description = "") {
        return this.auth.makeAuthRequest(
            `/api/campaigns/${campaignId}/sessions/${sessionId}/reports`,
            "POST",
            {
                target_message_id: messageId,
                reason_code: reasonCode,
                description,
            }
        );
    }

    async loadReports(campaignId, options = {}) {
        const params = new URLSearchParams();
        params.set("limit", String(options.limit || 25));
        if (options.status) params.set("status", options.status);
        if (options.priority) params.set("priority", options.priority);
        if (options.cursor) params.set("cursor", String(options.cursor));
        return this.auth.makeAuthRequest(`/api/campaigns/${campaignId}/reports?${params.toString()}`);
    }

    async createModerationAction(campaignId, payload) {
        return this.auth.makeAuthRequest(
            `/api/campaigns/${campaignId}/moderation/actions`,
            "POST",
            payload
        );
    }

    async revokeModerationAction(campaignId, actionId) {
        return this.auth.makeAuthRequest(
            `/api/campaigns/${campaignId}/moderation/actions/${actionId}/revoke`,
            "POST"
        );
    }

    async getVoiceConfig(campaignId, sessionId) {
        return this.auth.makeAuthRequest(
            `/api/campaigns/${campaignId}/sessions/${sessionId}/voice/config`
        );
    }
}
