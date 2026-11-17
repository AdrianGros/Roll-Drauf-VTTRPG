(() => {
    const t = s => globalThis.VTTUi?.(s) || s;
    const el = (tag, text) => { const e = document.createElement(tag); if (text) e.textContent = t(text); return e; };
    window.PlayTokenLibrary = class {
        constructor(ui) {
            this.ui = ui; this.path = `/api/play/campaigns/${ui.campaignId}/sessions/${ui.sessionId}/token-library`;
            const root = document.getElementById('tokenWidgetBody');
            const heading = el('h4', 'Meine Token-Bibliothek');
            const actions = el('div'); actions.className = 'token-library-actions';
            const save = el('button', 'Auswahl speichern'); save.type = 'button'; save.id = 'btnSaveTokenTemplate';
            const refresh = el('button', 'Aktualisieren'); refresh.type = 'button';
            const place = el('button', document.documentElement.lang.startsWith('en')?'Create new token':'Neuen Token erstellen'); place.type = 'button'; place.id = 'btnPlaceNewToken';
            place.onclick = () => { ui.pendingTokenTemplate = null; ui._setTool('token'); ui.windows.close('tokenWidget'); ui._showMessage(t('Klicke auf die Karte, um einen Token zu platzieren.')); };
            actions.append(place, save, refresh);
            this.status = el('p'); this.status.id = 'tokenLibraryStatus'; this.status.setAttribute('role', 'status');
            this.list = el('ul'); this.list.className = 'token-library-list'; this.list.id = 'tokenLibraryList';
            root.prepend(heading, actions, this.status, this.list);
            save.onclick = async () => {
                const token = ui._findStateToken(ui.selectedTokenId);
                if (!token || !ui._canMoveToken(token)) { this.status.textContent = t('Wähle zuerst einen eigenen Token auf der Karte.'); return; }
                save.disabled = true;
                try { await Auth.makeAuthRequest(this.path, 'POST', {token_id: token.id}); await this.refresh(); this.status.textContent = t('Token gespeichert. Die Vorlage ist auf anderen Karten wiederverwendbar.'); }
                catch (error) { this.status.textContent = error.message; }
                finally { save.disabled = false; }
            };
            refresh.onclick = () => this.refresh();
            this.refresh();
        }
        async refresh() {
            const sequence = this.sequence = (this.sequence || 0) + 1;
            try {
                const data = await Auth.makeAuthRequest(this.path); if (sequence !== this.sequence) return;
                this.list.replaceChildren();
                for (const row of data.templates) this.render(row);
                this.status.textContent = data.templates.length ? '' : t('Noch keine gespeicherten Tokens. Wähle einen eigenen Token und speichere ihn hier.');
            } catch (error) { if (sequence === this.sequence) { this.list.replaceChildren(); this.status.textContent = error.message; } }
        }
        render(row) {
            const item = el('li'); item.className = 'token-library-row'; item.dataset.templateId = row.id;
            const image = row.values.metadata_json?.image_url;
            if (image) { const img = el('img'); img.alt = ''; item.append(img); this.preview(img, image); }
            const title = el('strong'); title.textContent = row.name; item.append(title);
            const actions = el('div'); actions.className = 'token-library-actions';
            const place = el('button', 'Platzieren'); place.type = 'button';
            place.onclick = () => {
                if (this.ui.readOnly) { this.status.textContent = t('Die Sitzung muss zum Platzieren gestartet sein.'); return; }
                this.ui._setTool('token');
                this.ui.pendingTokenTemplate = row;
                this.ui.pendingTokenImage = image || null; this.ui.pendingTokenImageLabel = row.name;
                this.ui.windows.close('tokenWidget');
                this.ui._showMessage(t('Vorlage gewählt. Klicke auf die Karte.'));
            };
            const edit = el('button', 'Bearbeiten'); edit.type = 'button';
            const remove = el('button', 'Entfernen'); remove.type = 'button';
            const form = el('form'); form.hidden = true;
            const label = el('label', 'Name'); const name = el('input'); name.value = row.name; name.maxLength = 120; name.required = true; label.append(name);
            const sizeLabel = el('label', 'Größe in Feldern'); const size = el('input'); size.type = 'number'; size.min = '1'; size.max = '6'; size.value = row.values.size; sizeLabel.append(size);
            const submit = el('button', 'Speichern'); submit.type = 'submit'; form.append(label, sizeLabel, submit);
            edit.onclick = () => { form.hidden = !form.hidden; if (!form.hidden) name.focus(); };
            form.onsubmit = async event => { event.preventDefault(); submit.disabled = true;
                try { await Auth.makeAuthRequest(`${this.path}/${row.id}`, 'PATCH', {name: name.value, size: Number(size.value), revision: row.revision}); await this.refresh(); }
                catch (error) { this.status.textContent = error.message; submit.disabled = false; }
            };
            remove.onclick = async () => {
                if (!window.confirm(t('Diese Tokenvorlage entfernen? Platzierte Tokens bleiben erhalten.'))) return;
                remove.disabled = true;
                try { await Auth.makeAuthRequest(`${this.path}/${row.id}`, 'DELETE', {revision: row.revision}); await this.refresh(); }
                catch (error) { this.status.textContent = error.message; remove.disabled = false; }
            };
            actions.append(place, edit, remove); item.append(actions, form); this.list.append(item);
        }
        async preview(img, url) {
            if (new URL(url, location.origin).origin !== location.origin) { img.referrerPolicy = 'no-referrer'; img.src = url; return; }
            try { const response = await fetch(url, {credentials: 'include', headers: Auth.buildHeaders('GET', false), cache: 'no-store'});
                if (!response.ok || !img.isConnected) return; const objectUrl = URL.createObjectURL(await response.blob());
                if (!img.isConnected) { URL.revokeObjectURL(objectUrl); return; }
                img.onload = img.onerror = () => URL.revokeObjectURL(objectUrl); img.src = objectUrl;
            } catch (_) { /* Initials/name remain usable if art was removed. */ }
        }
    };
})();
