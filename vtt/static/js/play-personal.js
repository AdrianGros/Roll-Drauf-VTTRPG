globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Declarative character actions; every save and execution is server-authorized.
class PersonalActionBar {
    constructor(ui) {
        this.ui = ui;
        this.root = document.getElementById('personalActionBar');
        this.characterId = null;
        this.data = null;
        this.busy = false;
        this.active = false;
        this.showGeneric = false;
        this.pending = new Map();
        this.generation = 0;
        this.root.addEventListener('click', (event) => {
            const button = event.target.closest('button');
            if (!button) return;
            if (button.hasAttribute('data-pa-edit')) this.edit();
            else if (button.hasAttribute('data-pa-generic')) {
                this.showGeneric = !this.showGeneric;
                this.ui._renderActionHotbar();
            } else if (button.hasAttribute('data-pa-slot')) this.execute(Number(button.dataset.paSlot));
        });
        this.root.addEventListener('dragstart', (event) => {
            const button = event.target.closest('[data-pa-slot]');
            if (button) event.dataTransfer.setData('application/x-vtt-hotbar-slot', button.dataset.paSlot);
        });
        this.root.addEventListener('dragover', (event) => {
            if (event.target.closest('[data-pa-slot]')) event.preventDefault();
        });
        this.root.addEventListener('drop', async (event) => {
            event.preventDefault();
            const target = event.target.closest('[data-pa-slot]');
            const source = event.dataTransfer.getData('application/x-vtt-hotbar-slot');
            if (!target || !/^\d$/.test(source) || this.busy) return;
            const slots = [...this.data.slots];
            const a = Number(source), b = Number(target.dataset.paSlot);
            [slots[a], slots[b]] = [slots[b], slots[a]];
            await this.save(slots);
        });
        document.addEventListener('keydown', (event) => {
            if (!this.active || !/^[0-9]$/.test(event.key) || event.defaultPrevented) return;
            const target = event.target;
            if (event.ctrlKey || event.altKey || event.metaKey || event.repeat ||
                target?.closest('input,textarea,select,[contenteditable="true"]') ||
                document.querySelector('dialog[open]')) return;
            event.preventDefault();
            this.execute(event.key === '0' ? 9 : Number(event.key) - 1);
        });
    }

    endpoint() {
        return `/api/play/campaigns/${this.ui.campaignId}/sessions/${this.ui.sessionId}/characters/${this.characterId}`;
    }

    update(token, canAct) {
        this.canAct = canAct;
        const id = canAct || token && this.ui._canMoveToken(token) ? Number(token?.character_id) : 0;
        if (!id) {
            this.characterId = null;
            this.active = false;
            this.root.hidden = true;
            delete document.body.dataset.personalHotbar;
            return;
        }
        if (this.characterId !== id) {
            this.characterId = id;
            this.data = null;
            this.active = false;
            this.load();
        }
        this.root.hidden = !this.active;
        if (this.active) document.body.dataset.personalHotbar = 'true';
        else delete document.body.dataset.personalHotbar;
        this.render();
    }

    async load() {
        const generation = ++this.generation;
        try {
            const data = await this.ui.auth.makeAuthRequest(this.endpoint() + '/hotbar');
            if (generation !== this.generation || data.character_id !== this.characterId) return;
            this.data = data;
            this.active = Boolean(data.catalog.actions.length);
            this.ui._renderActionHotbar();
            this.render();
        } catch (error) {
            if (generation === this.generation) this.ui._showMessage(error.message, true);
        }
    }

    text(value) {
        const node = document.createElement('span');
        node.textContent = String(value ?? '');
        return node.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    render() {
        if (!this.characterId) return;
        const catalog = new Map((this.data?.catalog.actions || []).map(action => [action.id, action]));
        const slots = (this.data?.slots || []).map((id, index) => {
            if (!id) return '';
            const action = catalog.get(id);
            const label = action?.label || 'Nicht mehr verfügbar';
            return `<button type="button" draggable="true" data-pa-slot="${index}" title="${this.text(action?.detail || label)}"
                ${!action || this.busy || !this.canAct ? 'disabled' : ''}><kbd>${index === 9 ? 0 : index + 1}</kbd> ${this.text(label)}</button>`;
        }).join('');
        this.root.innerHTML = `<span class="pa-name">${this.text(this.data?.character_name || 'Charakteraktionen')}</span>
            <div class="pa-slots">${slots || `<span>${globalThis.VTTUiHTML("Noch keine Aktion belegt.")}</span>`}</div>
            <button type="button" data-pa-edit ${!this.active || this.busy ? 'disabled' : ''}>${globalThis.VTTUiHTML("Belegen")}</button>
            <button type="button" data-pa-generic aria-expanded="${this.showGeneric}">${globalThis.VTTUiHTML("Allgemeine")}</button>`;
    }

    async save(slots) {
        if (this.busy || !this.data) return false;
        this.busy = true;
        this.render();
        const characterId = this.characterId;
        try {
            const data = await this.ui.auth.makeAuthRequest(this.endpoint() + '/hotbar', 'PUT',
                {revision: this.data.revision, slots});
            if (characterId === this.characterId) this.data = data;
            this.ui._showMessage(globalThis.VTTUi("Persönliche Aktionsleiste gespeichert."));
            return true;
        } catch (error) {
            this.ui._showMessage(error.apiError === 'hotbar_conflict'
                ? globalThis.VTTUi("Die Belegung wurde in einem anderen Tab geändert. Bitte erneut öffnen.") : error.message, true);
            await this.load();
            return false;
        } finally {
            this.busy = false;
            this.render();
        }
    }

    async edit() {
        if (!this.data) return;
        const characterId = this.characterId;
        const existing = document.getElementById('personalActionDialog');
        existing?.remove();
        const dialog = document.createElement('dialog');
        dialog.id = 'personalActionDialog';
        dialog.className = 'pa-dialog';
        dialog.setAttribute('aria-label', 'Persönliche Aktionsleiste belegen');
        dialog.innerHTML = `<h2>${globalThis.VTTUiHTML("Meine Aktionsleiste")}</h2><p>${globalThis.VTTUiHTML("Wähle bis zu zehn Bogenaktionen. Zauber-Ankündigungen verbrauchen keine Plätze und wenden keine Effekte an.")}</p>`;
        const rows = [];
        for (let index = 0; index < 10; index++) {
            const row = document.createElement('div');
            row.className = 'pa-edit-row';
            const label = document.createElement('label');
            label.textContent = globalThis.VTTUi("Platz {p0}",{p0:(index + 1)});
            const select = document.createElement('select');
            select.id = `paSlot${index}`;
            label.htmlFor = select.id;
            select.add(new Option('Leer', ''));
            for (const action of this.data.catalog.actions) select.add(new Option(`${action.label} · ${action.detail}`, action.id));
            select.value = this.data.slots[index] || '';
            row.append(label, select);
            rows.push(select);
            for (const [symbol, delta] of [['↑', -1], ['↓', 1]]) {
                const button = document.createElement('button');
                button.type = 'button'; button.textContent = symbol;
                button.setAttribute('aria-label', `Platz ${index + 1} ${delta < 0 ? 'nach oben' : 'nach unten'}`);
                button.disabled = index + delta < 0 || index + delta >= 10;
                button.addEventListener('click', () => {
                    const other = rows[index + delta];
                    [select.value, other.value] = [other.value, select.value];
                });
                row.append(button);
            }
            dialog.append(row);
        }
        const status = document.createElement('p');
        status.setAttribute('role', 'status');
        dialog.append(status);
        const save = document.createElement('button');
        save.type = 'button'; save.textContent = globalThis.VTTUi("Speichern");
        save.addEventListener('click', async () => {
            save.disabled = true;
            if (this.characterId !== characterId) {
                status.textContent = globalThis.VTTUi("Der ausgewählte Charakter hat sich geändert. Bitte neu öffnen.");
                return;
            }
            const success = await this.save(rows.map(select => select.value || null));
            if (success) dialog.close();
            else status.textContent = globalThis.VTTUi("Nicht gespeichert. Prüfe die Meldung und öffne die aktuelle Belegung neu.");
        });
        const cancel = document.createElement('button');
        cancel.type = 'button'; cancel.textContent = globalThis.VTTUi("Abbrechen");
        cancel.addEventListener('click', () => dialog.close());
        dialog.append(save, cancel);
        dialog.addEventListener('close', () => dialog.remove(), {once: true});
        document.body.append(dialog);
        dialog.showModal();
    }

    async execute(index) {
        const actionId = this.data?.slots[index];
        if (!actionId || !this.canAct || this.busy || !this.ui.socket?.isConnected) return;
        const action = this.data.catalog.actions.find(a => a.id === actionId);
        if (!action) return;
        this.busy = true;
        this.render();
        const pendingKey = `${this.characterId}:${actionId}`;
        const body = this.pending.get(pendingKey) || {
            action_id: actionId, catalog_revision: this.data.catalog.revision,
            request_id: crypto.randomUUID(), mode: document.getElementById('rollMode')?.value || 'normal',
            visibility: document.getElementById('rollVisibility')?.value || 'public'
        };
        this.pending.set(pendingKey, body);
        try {
            const result = await this.ui.auth.makeAuthRequest(this.endpoint() + '/actions/execute', 'POST', body);
            this.pending.delete(pendingKey);
            this.ui._showMessage(result.declared ? `${result.label}. Ressourcen/Effekte am Bogen verwalten.`
                : `${result.label}: ${result.result.total}`);
        } catch (error) {
            if (error.status && error.status < 500 && error.apiError !== 'request_in_progress') this.pending.delete(pendingKey);
            this.ui._showMessage(error.apiError === 'action_catalog_changed'
                ? globalThis.VTTUi("Die Figur hat sich geändert; die Aktionsleiste wird aktualisiert.")
                : globalThis.VTTUi("{p0} Bei fehlender Bestätigung zuerst den Verlauf prüfen.",{p0:(error.message)}), true);
            if (error.apiError === 'action_catalog_changed') await this.load();
            await this.ui.loadBootstrap();
        } finally {
            this.busy = false;
            this.render();
        }
    }
}
window.PersonalActionBar = PersonalActionBar;
