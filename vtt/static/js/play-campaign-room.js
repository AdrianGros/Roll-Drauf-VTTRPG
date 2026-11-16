/* Normal text is campaign-wide; dice/hidden events stay on their session seam. */
(() => {
    window.PlayCampaignRoom = class {
        constructor(ui) {
            this.ui = ui; this.seen = new Set(); this.after = 0; this.path = `/api/campaign-rooms/${ui.campaignId}`;
            this.log = document.createElement('div'); this.log.id = 'campaignRoomLog'; this.log.setAttribute('role', 'log');
            document.getElementById('chatLog').before(this.log);
            const link = document.createElement('a'); link.id = 'campaignConversationLink'; link.href = `/conversations?campaign_id=${ui.campaignId}`;
            link.textContent = globalThis.VTTUi('Kampagnenchat in Gespräche öffnen'); link.target = '_blank'; link.rel = 'noopener';
            this.log.before(link);
            const status = document.createElement('p'); status.id = 'campaignRoomStatus'; status.setAttribute('role', 'status'); this.log.before(status); this.status = status;
            const send = () => this.send();
            document.getElementById('btnSendChat').addEventListener('click', send);
            document.getElementById('chatInput').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
            document.addEventListener('visibilitychange', () => { if (!document.hidden) this.poll(); });
            window.addEventListener('pagehide', () => { this.stopped = true; clearTimeout(this.timer); this.pending = null; this.log.replaceChildren(); });
            this.poll();
        }
        append(message) {
            if (this.seen.has(message.id)) return; this.seen.add(message.id); this.after = Math.max(this.after, message.id);
            const row = document.createElement('div'); row.className = 'chat-entry'; row.dataset.roomMessageId = message.id;
            const author = document.createElement('strong'); author.textContent = message.author_name + ': ';
            const content = document.createElement('span'); content.textContent = message.content; row.append(author, content); this.log.append(row);
            while (this.log.children.length > 100) this.log.firstElementChild.remove();
            this.log.scrollTop = this.log.scrollHeight;
        }
        async poll() {
            clearTimeout(this.timer); if (this.stopped || document.hidden || this.polling) return; this.polling = true;
            try { const result = await Auth.makeAuthRequest(this.path + (this.after ? `?after=${this.after}` : ''));
                for (const message of result.messages) this.append(message); this.status.textContent = '';
            } catch (error) { this.log.replaceChildren(); this.seen.clear(); this.after = 0; this.status.textContent = error.message; }
            finally { this.polling = false; if (!this.stopped) this.timer = setTimeout(() => this.poll(), 3000); }
        }
        async send() {
            const input = document.getElementById('chatInput'), button = document.getElementById('btnSendChat');
            if (this.sending || (!this.pending && !input.value.trim())) return;
            if (!this.pending) this.pending = {content: input.value.trim(), client_event_id: crypto.randomUUID()};
            this.sending = true; button.disabled = true; input.readOnly = true;
            try { const result = await Auth.makeAuthRequest(this.path, 'POST', this.pending); this.append(result.message);
                this.pending = null; input.value = ''; this.status.textContent = globalThis.VTTUi('Nachricht gesendet.');
            } catch (error) { this.status.textContent = error.message + ' · ' + globalThis.VTTUi('Erneut senden verwendet dieselbe Nachricht.'); }
            finally { this.sending = false; button.disabled = false; input.readOnly = !!this.pending; }
        }
    };
})();
