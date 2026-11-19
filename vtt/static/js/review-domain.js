/* Scoped review additions; no table controllers, secret projections or executable content. */
const ui = (de, en) => document.documentElement.lang === 'en' ? en : de;
const node = (tag, parent, text, attrs = {}) => {
    const element = document.createElement(tag);
    if (text !== null) element.textContent = text;
    for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
    parent.append(element); return element;
};
async function request(path, method = 'GET', body, signal, retry = true) {
    const response = await fetch('/api/review-domain' + path, {method, credentials: 'include', signal,
        headers: window.Auth.buildHeaders(method, body !== undefined),
        ...(body === undefined ? {} : {body: JSON.stringify(body)})});
    if (response.status === 401 && retry && await window.Auth.refreshAccessToken()) return request(path, method, body, signal, false);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(response.status === 409
        ? ui('Der Stand hat sich geändert. Bitte aktualisieren und erneut versuchen.', 'The state changed. Refresh and try again.')
        : ui('Die Anfrage konnte nicht ausgeführt werden.', 'The request could not be completed.')); error.status = response.status; throw error; }
    return data;
}

export class ThreadSurface {
    constructor(host) {
        this.host = node('details', host, null, {class: 'private-threads', id: 'conversationThreads', hidden: ''});
        node('summary', this.host, ui('Unterthreads', 'Threads'));
        this.status = node('p', this.host, '', {role: 'status', 'aria-live': 'polite'});
        this.list = node('ul', this.host, null, {id: 'threadList'});
        this.more = node('button', this.host, ui('Weitere Threads', 'More threads'), {type: 'button', class: 'btn btn-secondary', hidden: ''});
        this.more.onclick = () => this.loadList(true);
        this.create = node('form', this.host, null, {id: 'threadCreate'});
        this.titleInput = node('input', node('label', this.create, ui('Threadtitel', 'Thread title')), null,
            {maxlength: 100, required: '', id: 'threadTitle'});
        node('button', this.create, ui('Thread erstellen', 'Create thread'), {type: 'submit', class: 'btn btn-secondary'});
        this.create.onsubmit = event => { event.preventDefault(); this.createThread(); };
        this.panel = node('section', this.host, null, {hidden: '', 'aria-labelledby': 'threadHeading'});
        this.heading = node('h3', this.panel, '', {id: 'threadHeading'});
        this.close = node('button', this.panel, '', {type: 'button', class: 'btn btn-secondary', id: 'threadClose'});
        this.close.onclick = () => this.toggleClosed();
        this.older = node('button', this.panel, ui('Ältere Threadnachrichten', 'Older thread messages'),
            {type: 'button', class: 'btn btn-secondary', hidden: ''});
        this.older.onclick = () => this.readThread(true);
        this.messages = node('ol', this.panel, null, {class: 'private-history', id: 'threadHistory'});
        this.form = node('form', this.panel, null);
        this.input = node('textarea', node('label', this.form, ui('Threadnachricht', 'Thread message')), null,
            {required: '', maxlength: 2000, rows: 3, id: 'threadMessage'});
        this.send = node('button', this.form, ui('Im Thread senden', 'Send in thread'), {type: 'submit', class: 'btn btn-primary'});
        this.form.onsubmit = event => { event.preventDefault(); this.submit(); };
        this.host.ontoggle = () => { if (this.host.open && this.parent) this.loadList(); };
        this.version = 0;
        this.visibility = () => { clearTimeout(this.timer); if (!document.hidden && this.parent && this.host.open) this.refresh(); };
        document.addEventListener('visibilitychange', this.visibility);
    }
    setParent(parent) {
        this.version++; this.controller?.abort(); clearTimeout(this.timer);
        this.controller = new AbortController(); this.parent = parent; this.thread = null; this.pending = null; this.createPending = null;
        this.rows = new Map(); this.input.value = ''; this.titleInput.value = '';
        this.input.readOnly = false; this.sending = false; this.send.disabled = false;
        this.messages.replaceChildren(); this.list.replaceChildren(); this.panel.hidden = true;
        this.create.hidden = true; this.status.textContent = ''; this.host.hidden = !parent; this.more.hidden = true;
        if (parent && this.host.open) this.loadList();
    }
    fail(error, version) {
        if (version !== this.version || error.name === 'AbortError') return;
        if ([401, 403, 404].includes(error.status)) {
            this.setParent(null); this.host.hidden = false;
            this.status.textContent = ui('Dieser Thread ist nicht mehr verfügbar.', 'This thread is no longer available.');
        } else this.status.textContent = error.message;
    }
    async loadList(append = false) {
        const version = this.version, parent = this.parent; if (!parent) return;
        try {
            const query = new URLSearchParams({...parent, ...(append && this.after ? {after: this.after} : {})});
            const data = await request('/threads?' + query, 'GET', undefined, this.controller.signal);
            if (version !== this.version) return;
            if (!append) this.list.replaceChildren();
            for (const thread of data.threads) {
                const button = node('button', node('li', this.list, null), thread.title + (thread.closed ? ui(' (geschlossen)', ' (closed)') : ''),
                    {type: 'button', class: 'btn btn-secondary', 'data-thread-id': thread.id});
                button.onclick = () => { this.thread = thread; this.rows.clear(); this.pending = null; this.input.value = ''; this.input.readOnly = false; this.sending = false; this.send.disabled = false; this.readThread(); };
            }
            this.after = data.next_after; this.more.hidden = !this.after; this.create.hidden = !data.can_create;
            if (!data.threads.length && !append) node('li', this.list, ui('Noch keine Threads.', 'No threads yet.'));
        } catch (error) { this.fail(error, version); }
        finally { if (version === this.version) this.schedule(); }
    }
    async createThread() {
        if (this.creating || !this.parent || !this.titleInput.value.trim()) return;
        const title = this.titleInput.value.trim(), version = this.version;
        if (!this.createPending || this.createPending.title !== title) this.createPending = {...this.parent, title, request_id: crypto.randomUUID()};
        this.creating = true; const button = this.create.querySelector('button'); button.disabled = true;
        try {
            const data = await request('/threads', 'POST', this.createPending, this.controller.signal);
            if (version !== this.version) return;
            this.createPending = null; this.titleInput.value = ''; this.thread = data.thread; this.rows.clear();
            await this.loadList(); await this.readThread();
        } catch (error) { this.fail(error, version); }
        finally { this.creating = false; button.disabled = false; }
    }
    async readThread(older = false) {
        const thread = this.thread, version = this.version; if (!thread) return;
        try {
            const before = older && this.rows.size ? Math.min(...this.rows.keys()) : null;
            const data = await request('/threads/' + thread.id + (before ? '?before=' + before : ''), 'GET', undefined, this.controller.signal);
            if (version !== this.version || thread.id !== this.thread?.id) return;
            this.thread = data.thread; this.panel.hidden = false; this.heading.textContent = data.thread.title;
            this.form.hidden = !data.thread.can_send; this.close.hidden = !data.thread.can_edit;
            this.close.textContent = data.thread.closed ? ui('Thread wieder öffnen', 'Reopen thread') : ui('Thread schließen', 'Close thread');
            if (older || !this.rows.size) this.older.hidden = !data.more;
            for (const message of data.messages) this.rows.set(message.id, message);
            this.renderMessages();
        } catch (error) { this.fail(error, version); }
        finally { if (version === this.version) this.schedule(); }
    }
    renderMessages() {
        this.messages.replaceChildren();
        for (const message of [...this.rows.values()].sort((a, b) => a.id - b.id)) {
            const row = node('li', this.messages, null, {class: 'private-message', 'data-thread-message-id': message.id});
            node('strong', row, message.author_name); node('p', row, message.content);
        }
    }
    schedule() { clearTimeout(this.timer); if (this.parent && this.host.open && !document.hidden) this.timer = setTimeout(() => this.refresh(), 5000); }
    async refresh() { await this.loadList(); if (this.thread) await this.readThread(); else this.schedule(); }
    async submit() {
        if (!this.thread?.can_send || this.sending || !this.input.value.trim()) return;
        const version = this.version, id = this.thread.id;
        if (!this.pending) this.pending = {content: this.input.value, request_id: crypto.randomUUID()};
        this.sending = true; this.send.disabled = true; this.input.readOnly = true;
        try {
            const data = await request('/threads/' + id + '/messages', 'POST', this.pending, this.controller.signal);
            if (version !== this.version || id !== this.thread?.id) return;
            this.rows.set(data.message.id, data.message); this.pending = null; this.input.value = ''; this.renderMessages();
            this.status.textContent = ui('Nachricht gesendet.', 'Message sent.');
        } catch (error) { this.fail(error, version); }
        finally { if (version === this.version && id === this.thread?.id) { this.sending = false; this.send.disabled = false; this.input.readOnly = !!this.pending; } }
    }
    async toggleClosed() {
        const version = this.version; if (!this.thread) return;
        try {
            const data = await request('/threads/' + this.thread.id, 'PUT', {revision: this.thread.revision,
                title: this.thread.title, closed: !this.thread.closed}, this.controller.signal);
            if (version !== this.version) return;
            this.thread = data.thread; await this.readThread(); await this.loadList();
        } catch (error) { this.fail(error, version); }
    }
    destroy() { this.setParent(null); document.removeEventListener('visibilitychange', this.visibility); this.host.remove(); }
}

export async function mountWorldLinks(host, world, {signal, beforeChange = () => {}, afterChange = () => {}} = {}) {
    const section = node('section', host, null, {class: 'atlas-panel', id: 'atlasCampaignLinks'});
    node('h2', section, ui('Verknüpfte Kampagnen', 'Linked campaigns'));
    node('p', section, ui('Eine Verknüpfung vergibt keine Weltfreigaben.', 'Linking does not grant world access.'));
    const status = node('p', section, '', {role: 'status'}), list = node('ul', section, null);
    const data = await request('/worlds/' + world + '/campaigns', 'GET', undefined, signal);
    if (!section.isConnected || signal?.aborted) return;
    const change = async fn => {
        if (section.dataset.busy) return; section.dataset.busy = 'true';
        const fields = section.closest('fieldset'), wasDisabled = fields?.disabled;
        if (fields) fields.disabled = true;
        try { await beforeChange(); await fn(); await afterChange(); }
        catch (error) { if (error.name !== 'AbortError') status.textContent = error.message; }
        finally { if (fields) fields.disabled = wasDisabled; delete section.dataset.busy; }
    };
    for (const link of data.campaigns) {
        const row = node('li', list, null); node('a', row, link.name, {href: link.href});
        if (data.can_manage) {
            const remove = node('button', row, ui('Verknüpfung lösen', 'Unlink'), {type: 'button', class: 'btn btn-secondary', 'data-unlink-campaign': link.campaign_id});
            remove.onclick = () => change(() => request('/worlds/' + world + '/campaigns/' + link.campaign_id, 'DELETE',
                {world_revision: data.world_revision, revision: link.revision}, signal));
        }
    }
    if (!data.can_manage) return;
    const managed = await request('/managed-campaigns', 'GET', undefined, signal);
    if (!section.isConnected || signal?.aborted) return;
    const form = node('form', section, null), select = node('select', node('label', form, ui('Eigene verwaltete Kampagne', 'Your managed campaign')), null,
        {required: '', id: 'atlasLinkCampaign'});
    select.add(new Option(ui('Kampagne wählen', 'Choose campaign'), ''));
    for (const campaign of managed.campaigns.filter(row => !data.campaigns.some(link => link.campaign_id === row.id))) select.add(new Option(campaign.name, String(campaign.id)));
    node('button', form, ui('Kampagne verknüpfen', 'Link campaign'), {type: 'submit', class: 'btn btn-secondary'});
    let pending;
    form.onsubmit = event => { event.preventDefault();
        if (!select.value) return;
        if (!pending || pending.campaign_id !== Number(select.value)) pending = {campaign_id: Number(select.value), world_revision: data.world_revision, request_id: crypto.randomUUID()};
        change(() => request('/worlds/' + world + '/campaigns', 'POST', pending, signal));
    };
}

export async function managedCampaignOptions(select) {
    const data = await request('/managed-campaigns');
    for (const campaign of data.campaigns) select.add(new Option(campaign.name, String(campaign.id)));
}
export async function linkNewWorld(world, campaignId) {
    return request('/worlds/' + world.id + '/campaigns', 'POST', {campaign_id: campaignId, world_revision: world.revision, request_id: crypto.randomUUID()});
}

export async function mountCompanionScaling(host, characterId) {
    if (host.querySelector('[data-companion-scaling]')) return;
    const details = node('details', host, null, {'data-companion-scaling': '', id: 'companionScaling'});
    node('summary', details, ui('Eigene Begleiterregel und Schnellwerte', 'Custom companion rule and quick stats'));
    const status = node('p', details, '', {role: 'status'});
    const controller = new AbortController();
    window.addEventListener('pagehide', () => controller.abort(), {once: true});
    let data;
    async function load() {
        try {
            data = await request('/characters/' + characterId + '/companion-scaling', 'GET', undefined, controller.signal);
            if (!details.isConnected) return;
            for (const old of details.querySelectorAll('[data-scaling-content]')) old.remove();
            const content = node('div', details, null, {'data-scaling-content': ''});
            node('p', content, ui('Diese eigene lineare Regel ist keine automatisch gelieferte Klassenregel.', 'This custom linear rule is not a supplied class rule.'));
            for (const companion of data.companions) {
                const card = node('form', content, null, {'data-scaling-companion': companion.id, class: 'srd-man-card'});
                node('h3', card, companion.name);
                node('p', card, `${ui('TP', 'HP')} ${companion.hpCurrent}/${companion.hpMax} · ${ui('RK', 'AC')} ${companion.ac} · ${companion.speed || ''}`);
                const config = companion.scaling || {enabled: false, base: companion.hpMax, perLevel: 0, perProficiency: 0, label: ''};
                const enabled = node('input', node('label', card, ui('Eigene Skalierung aktiv', 'Enable custom scaling')), null, {type: 'checkbox'}); enabled.checked = config.enabled;
                const inputs = {};
                for (const [key, de, en, max] of [['base', 'Basis-TP', 'Base HP', 9999], ['perLevel', 'TP je Charakterstufe', 'HP per character level', 100], ['perProficiency', 'TP je Übungsbonus', 'HP per proficiency bonus', 100]]) {
                    const input = inputs[key] = node('input', node('label', card, ui(de, en)), null, {type: 'number', min: 0, max, step: 1, required: ''}); input.value = config[key];
                }
                inputs.label = node('input', node('label', card, ui('Bezeichnung der eigenen Regel', 'Custom rule label')), null, {type: 'text', maxlength: 80}); inputs.label.value = config.label;
                const save = node('button', card, ui('Begleiterregel speichern', 'Save companion rule'), {type: 'submit', class: 'btn btn-secondary'});
                const editable = data.can_edit && globalThis.SheetLock?.locked !== true;
                for (const input of card.querySelectorAll('input,button')) input.disabled = !editable;
                card.onsubmit = async event => {
                    event.preventDefault();
                    if (!data.can_edit || globalThis.SheetLock?.locked === true) return;
                    save.disabled = true;
                    try {
                        await request('/characters/' + characterId + '/companion-scaling', 'PUT', {revision: data.revision, companion_id: companion.id,
                            scaling: {enabled: enabled.checked, base: Number(inputs.base.value), perLevel: Number(inputs.perLevel.value),
                                perProficiency: Number(inputs.perProficiency.value), label: inputs.label.value}}, controller.signal);
                        if (!details.isConnected) return;
                        status.textContent = ui('Eigene Regel gespeichert. Schaden bleibt erhalten.', 'Custom rule saved. Damage is preserved.'); await load();
                    } catch (error) { if (error.name !== 'AbortError' && details.isConnected) status.textContent = error.message; }
                    finally { save.disabled = !editable; }
                };
            }
            if (!data.companions.length) node('p', content, ui('Lege zuerst einen Begleiter an und speichere ihn.', 'Create and save a companion first.'));
        } catch (error) { if (error.name !== 'AbortError' && details.isConnected) status.textContent = error.message; }
    }
    details.ontoggle = () => { if (details.open && !data) load(); };
}

// A sheet may rebuild its management subtree after a save or view change.
if (document.querySelector('script[src*="srd-manage-ui.js"]')) {
    const characterId = Number(new URLSearchParams(location.search).get('id'));
    const attach = () => {
        const host = document.getElementById('srdManage');
        if (host && Number.isInteger(characterId) && characterId > 0) mountCompanionScaling(host, characterId);
    };
    const observer = new MutationObserver(attach); observer.observe(document.body, {childList: true, subtree: true}); attach();
    window.addEventListener('pagehide', () => observer.disconnect(), {once: true});
}
