/* Personal HTTP-only surface. Never mounts a DM controller or joins a table room. */
const ui = (source, parameters) => globalThis.VTTUi(source, parameters);
const root = document.getElementById('privateConversations');
const make = (tag, parent, text, attrs = {}) => {
    const node = document.createElement(tag); if (text !== null) node.textContent = text;
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    parent.append(node); return node;
};

async function api(path = '', method = 'GET', body, signal, retry = true) {
    const response = await fetch('/api/private-conversations' + path, {
        method, credentials: 'include', signal, headers: window.Auth.buildHeaders(method, body !== undefined),
        ...(body !== undefined ? {body: JSON.stringify(body)} : {}),
    });
    if (response.status === 401 && retry && await window.Auth.refreshAccessToken()) return api(path, method, body, signal, false);
    if (!response.ok) { const error = new Error('conversation request failed'); error.status = response.status; throw error; }
    return response.json();
}

export class ConversationSurface {
    constructor(host) {
        this.host = host; this.version = 0; this.pending = new Map(); this.messages = new Map(); this.listVersion = 0;
        const left = make('section', host, null, {class: 'private-panel'});
        make('h1', left, ui('Gespräche'));
        make('p', left, ui('Beginne ein privates Gespräch über Chat in der Mitgliederliste einer Kampagne.'));
        this.list = make('ul', left, null, {class: 'private-list', id: 'conversationList'});
        this.more = make('button', left, ui('Weitere Gespräche'), {type: 'button', class: 'btn btn-secondary', hidden: ''});
        this.more.onclick = () => this.loadList(true);
        this.right = make('section', host, null, {class: 'private-panel', 'aria-labelledby': 'conversationTitle'});
        this.title = make('h2', this.right, ui('Gespräch auswählen'), {id: 'conversationTitle'});
        this.info = make('p', this.right, '', {class: 'private-status', role: 'status', 'aria-live': 'polite', id: 'conversationStatus'});
        this.older = make('button', this.right, ui('Ältere Nachrichten'), {type: 'button', class: 'btn btn-secondary', hidden: ''});
        this.older.onclick = () => this.read('older');
        this.history = make('ol', this.right, null, {class: 'private-history', id: 'conversationHistory', 'aria-label': ui('Nachrichten')});
        this.form = make('form', this.right, null, {hidden: ''});
        make('label', this.form, ui('Nachricht'), {for: 'privateMessage'});
        this.input = make('textarea', this.form, null, {id: 'privateMessage', maxlength: 2000, rows: 3, required: ''});
        this.send = make('button', this.form, ui('Senden'), {type: 'submit', class: 'btn btn-primary', id: 'privateSend'});
        this.form.onsubmit = event => { event.preventDefault(); this.submit(); };
        this.input.onkeydown = event => {
            if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); this.form.requestSubmit(); }
        };
        document.addEventListener('visibilitychange', () => {
            this.pause(); if (!document.hidden && this.id) this.read('new');
        });
        window.addEventListener('pagehide', () => {
            this.pause(); this.sendAbort?.abort(); this.listAbort?.abort(); this.version++; this.listVersion++;
            this.pending.clear(); this.messages.clear(); this.history.replaceChildren(); this.list.replaceChildren();
            this.input.value = ''; this.form.hidden = true;
        });
        window.addEventListener('pageshow', event => {
            if (event.persisted) { this.loadList(); if (this.id) this.open(this.id); }
        });
    }
    pause() { clearTimeout(this.timer); this.readAbort?.abort(); this.readAbort = null; }
    denied() {
        this.pause(); this.sendAbort?.abort(); this.listAbort?.abort(); this.listVersion++; this.version++; if (this.id) this.pending.delete(this.id);
        this.id = null; this.messages.clear(); this.history.replaceChildren(); this.list.replaceChildren();
        this.form.hidden = true; this.input.value = ''; this.older.hidden = true;
        this.title.textContent = ui('Gespräch nicht verfügbar');
        this.info.textContent = ui('Der Zugriff auf dieses Gespräch ist nicht mehr verfügbar.');
    }
    error(error) {
        if ([401, 403, 404].includes(error.status)) this.denied();
        else this.info.textContent = ui('Die Anfrage ist fehlgeschlagen. Bitte versuche es erneut.');
    }
    async loadList(append = false) {
        this.listAbort?.abort(); const controller = this.listAbort = new AbortController(), version = ++this.listVersion;
        try {
            const data = await api(append && this.cursor ? '?cursor=' + encodeURIComponent(this.cursor) : '', 'GET', undefined, controller.signal);
            if (version !== this.listVersion) return;
            if (!append) this.list.replaceChildren();
            for (const conversation of data.conversations) {
                const row = make('li', this.list, null), button = make('button', row, conversation.partner_name,
                    {type: 'button', 'data-conversation-id': conversation.id, 'aria-current': String(this.id === conversation.id)});
                make('small', button, conversation.campaign_name);
                button.onclick = () => this.open(conversation.id);
            }
            this.cursor = data.next_cursor; this.more.hidden = !this.cursor;
            if (!data.conversations.length && !append) make('li', this.list, ui('Noch keine Gespräche.'));
        } catch (error) { if (error.name !== 'AbortError' && version === this.listVersion) this.error(error); }
    }
    async open(id) {
        this.pause(); this.sendAbort?.abort(); this.version++; this.id = id; this.messages.clear(); this.sending = false;
        this.history.replaceChildren(); this.form.hidden = true; this.title.textContent = ui('Gespräch wird geladen …'); this.info.textContent = '';
        this.input.value = this.pending.get(id)?.content || '';
        history.replaceState(null, '', '/conversations?id=' + id);
        this.list.querySelectorAll('[data-conversation-id]').forEach(button => button.setAttribute('aria-current', String(Number(button.dataset.conversationId) === id)));
        await this.read('initial');
    }
    render() {
        this.history.replaceChildren();
        const locale = document.documentElement.lang === 'en' ? 'en-GB' : 'de-DE';
        for (const message of [...this.messages.values()].sort((a, b) => a.id - b.id)) {
            const item = make('li', this.history, null, {class: 'private-message', 'data-message-id': message.id});
            make('strong', item, message.author_name);
            make('time', item, new Intl.DateTimeFormat(locale, {dateStyle: 'short', timeStyle: 'short'}).format(new Date(message.created_at)), {datetime: message.created_at});
            make('p', item, message.content); // Plain text, including any markup-looking content.
        }
    }
    async read(direction) {
        if (!this.id || document.hidden || this.readAbort) return;
        const id = this.id, version = this.version, controller = this.readAbort = new AbortController(); clearTimeout(this.timer);
        const ids = [...this.messages.keys()], cursor = direction === 'older' && ids.length ? '?before=' + Math.min(...ids)
            : direction === 'new' && ids.length ? '?after=' + Math.max(...ids) : '';
        try {
            const data = await api('/' + id + cursor, 'GET', undefined, controller.signal);
            if (version !== this.version || id !== this.id) return;
            this.title.textContent = `${data.conversation.partner_name} · ${data.conversation.campaign_name}`;
            this.canSend = data.conversation.can_send;
            for (const message of data.messages) {
                this.messages.set(message.id, message);
                const pending = this.pending.get(id);
                if (pending?.client_event_id === message.client_event_id && message.author_user_id === data.conversation.self_user_id) {
                    this.pending.delete(id); this.input.value = ''; this.sending = false;
                    this.info.textContent = ui('Nachricht gesendet.');
                }
            }
            if (direction !== 'new') this.older.hidden = !data.more;
            if (!this.canSend) { this.pending.delete(id); this.input.value = ''; this.info.textContent = ui('Dieses Gespräch ist schreibgeschützt.'); }
            this.form.hidden = !this.canSend; this.input.readOnly = this.pending.has(id); this.send.disabled = this.sending;
            if (data.messages.length) {
                const top = this.history.scrollTop, height = this.history.scrollHeight;
                const atBottom = height - top - this.history.clientHeight < 40;
                this.render();
                this.history.scrollTop = direction === 'older' ? top + this.history.scrollHeight - height
                    : atBottom || direction === 'initial' ? this.history.scrollHeight : top;
            }
        } catch (error) { if (error.name !== 'AbortError' && version === this.version) this.error(error); }
        finally {
            if (this.readAbort === controller) {
                this.readAbort = null;
                if (this.id && !document.hidden) this.timer = setTimeout(() => this.read('new'), 5000);
            }
        }
    }
    async submit() {
        if (!this.id || !this.canSend || this.sending || !this.input.value.trim()) return;
        const id = this.id, version = this.version;
        if (!this.pending.has(id)) this.pending.set(id, {content: this.input.value, client_event_id: crypto.randomUUID()});
        const pending = this.pending.get(id), controller = this.sendAbort = new AbortController();
        this.sending = true; this.send.disabled = true; this.input.readOnly = true; this.info.textContent = ui('Nachricht wird gesendet …');
        try {
            const data = await api('/' + id + '/messages', 'POST', pending, controller.signal);
            if (version !== this.version || id !== this.id) return;
            this.messages.set(data.message.id, data.message); this.pending.delete(id); this.input.value = '';
            this.info.textContent = ui('Nachricht gesendet.'); this.render(); this.history.scrollTop = this.history.scrollHeight;
            this.loadList();
        } catch (error) {
            if (version !== this.version || error.name === 'AbortError') return;
            if ([401, 403, 404].includes(error.status)) this.denied();
            else if (error.status === 409) { this.pending.delete(id); this.form.hidden = true; this.input.value = ''; this.read('new'); }
            else this.info.textContent = ui('Senden fehlgeschlagen. Erneut senden verwendet dieselbe Nachricht.');
        } finally {
            if (version === this.version) { this.sending = false; this.send.disabled = false; this.input.readOnly = this.pending.has(id); }
        }
    }
}

if (root) {
    (async () => {
        const user = await window.Auth.requireAuth('/login.html'); if (!user) return;
        document.title = ui('Gespräche') + ' · Roll Drauf';
        const surface = new ConversationSurface(root); await surface.loadList();
        const query = new URLSearchParams(location.search), id = Number(query.get('id'));
        const campaign = Number(query.get('campaign_id')), recipient = Number(query.get('recipient_user_id'));
        try {
            if (Number.isInteger(id) && id > 0) await surface.open(id);
            else if (Number.isInteger(campaign) && campaign > 0 && Number.isInteger(recipient) && recipient > 0) {
                const result = await api('', 'POST', {campaign_id: campaign, recipient_user_id: recipient});
                await surface.loadList(); await surface.open(result.conversation.id);
            }
        } catch (error) { surface.error(error); }
        finally { root.setAttribute('aria-busy', 'false'); }
    })();
}
