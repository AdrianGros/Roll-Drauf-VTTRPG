/* FV15: campaign-quota requests and owner/admin review inside the own profile dialog.
 * Every response is checked against the account the profile was opened for, and every
 * mutation carries X-Quota-Account so the server rejects a switched session. Authored
 * reasons and notes are always set with textContent and are never translated. */
(function () {
    'use strict';

    const API = '/api/campaign-quota';
    const ui = (source, parameters) => globalThis.VTTUi(source, parameters);
    const STATUS = {
        pending: 'Anfrage offen',
        approved: 'Anfrage genehmigt',
        rejected: 'Anfrage abgelehnt',
        cancelled: 'Anfrage zurückgezogen',
    };
    const CONFLICT = 'Die Anfrage oder das Limit hat sich inzwischen geändert. Es wurde nichts gespeichert. Bitte neu laden.';
    const SWITCHED = 'Das angemeldete Konto hat sich geändert. Bitte öffne dein Profil neu.';
    const ERRORS = {
        account_mismatch: SWITCHED,
        authentication_required: 'Bitte melde dich erneut an.',
        forbidden: 'Dafür fehlt dir die Berechtigung.',
        invalid_desired_total: 'Bitte eine ganze Zahl über deinem aktuellen Limit eingeben.',
        desired_total_not_above_current: 'Bitte eine ganze Zahl über deinem aktuellen Limit eingeben.',
        invalid_reason: 'Bitte eine Begründung mit höchstens 500 Zeichen angeben.',
        invalid_quota_request: 'Die Anfrage ist fehlgeschlagen. Bitte versuche es erneut.',
        pending_request_exists: 'Du hast bereits eine offene Anfrage.',
        request_rate_limited: 'Höchstens 5 Anfragen in 24 Stunden. Bitte versuche es später erneut.',
        creator_role_required: 'Anfragen sind nur für Konten möglich, die Kampagnen erstellen dürfen.',
        quota_unassigned: 'Deinem Konto ist kein Kampagnenlimit zugewiesen; eine Anfrage ist deshalb nicht möglich.',
        quota_not_positive: 'Dein Kampagnenlimit ist nicht positiv; eine Anfrage ist deshalb nicht möglich.',
        quota_at_maximum: 'Dein Kampagnenlimit hat bereits den höchstmöglichen Wert.',
        request_not_found: 'Diese Anfrage wurde nicht gefunden.',
        request_not_pending: CONFLICT,
        quota_changed: CONFLICT,
        quota_not_finite: CONFLICT,
        approved_total_not_above_current: 'Das neue Gesamtlimit muss über dem aktuellen Limit liegen.',
        approved_total_below_active: 'Das neue Gesamtlimit darf nicht unter der Zahl aktiver Kampagnen liegen.',
        invalid_approved_total: 'Bitte ein ganzzahliges neues Gesamtlimit eingeben.',
        invalid_reviewer_note: 'Die Notiz darf höchstens 500 Zeichen haben.',
    };
    const STALE = new Set(['request_not_pending', 'quota_changed', 'quota_not_finite']);

    function message(error) {
        return ui(ERRORS[error?.code] || 'Die Anfrage ist fehlgeschlagen. Bitte versuche es erneut.');
    }

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function when(iso) {
        if (!iso) return '';
        const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z');
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleString(globalThis.VTTI18n?.locale?.() === 'en' ? 'en-GB' : 'de-DE',
            { dateStyle: 'medium', timeStyle: 'short' });
    }

    function quotaText(quota) {
        if (!quota?.assigned) return ui('nicht zugewiesen');
        return quota.current === null ? ui('ungültig') : String(quota.current);
    }

    function ensureStyles() {
        if (document.querySelector('link[data-campaign-quota-css]')) return;
        const link = document.createElement('link');
        link.rel = 'stylesheet'; link.href = '/static/css/campaign-quota.css';
        link.dataset.campaignQuotaCss = '';
        document.head.appendChild(link);
    }

    // Own fetch instead of Auth.makeAuthRequest: it needs the account header, must never
    // carry a table context, and must not redirect away from an open profile on 401.
    async function api(path, accountId, method = 'GET', body = null, retry = true) {
        const headers = window.Auth.buildHeaders(method, body !== null);
        delete headers['X-VTT-Context']; delete headers['X-VTT-Tab'];
        if (method !== 'GET') headers['X-Quota-Account'] = String(accountId);
        const response = await fetch(API + path, {
            method, credentials: 'include', cache: 'no-store', headers,
            body: body === null ? undefined : JSON.stringify(body),
        });
        if (response.status === 401 && retry && await window.Auth.refreshAccessToken()) {
            return api(path, accountId, method, body, false);
        }
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const error = new Error(data.error || 'request_failed');
            error.code = data.error || 'request_failed'; error.status = response.status; error.data = data;
            throw error;
        }
        if (data.accountId !== accountId) {
            const error = new Error('account_mismatch'); error.code = 'account_mismatch';
            throw error;
        }
        return data;
    }

    function mount(host, accountId) {
        if (!host || !Number.isInteger(accountId) || !window.Auth?.buildHeaders) return;
        ensureStyles();
        const state = { host, accountId, data: null, reviewOpen: false, reviewView: 'pending', sequence: 0 };
        host.setAttribute('aria-labelledby', `cqTitle${accountId}`);
        host.replaceChildren(el('p', 'cq-muted', ui('Kampagnenlimit wird geladen …')));
        host.hidden = false;
        load(state);
    }

    function live(state) {
        return state.host.isConnected;
    }

    function switched(state) {
        const note = el('p', 'cq-status cq-error', ui(SWITCHED));
        note.setAttribute('role', 'alert');
        state.host.replaceChildren(note);
    }

    async function load(state, notice) {
        const sequence = ++state.sequence;
        try {
            const data = await api('/requests', state.accountId);
            if (!live(state) || sequence !== state.sequence) return;
            state.data = data;
            render(state, notice);
        } catch (error) {
            if (!live(state) || sequence !== state.sequence) return;
            if (error.code === 'account_mismatch') { switched(state); return; }
            // Only the quota panel is removed; the profile counts above stay intact.
            state.host.remove();
        }
    }

    function render(state, notice) {
        const { data, accountId } = state;
        const title = el('h3', 'cq-title', ui('Kampagnenlimit'));
        title.id = `cqTitle${accountId}`;
        const facts = el('div', 'cq-facts');
        for (const [label, value] of [
            ['Aktuelles Limit', quotaText(data.quota)],
            ['Aktive Kampagnen', String(data.quota?.active_count ?? 0)],
        ]) {
            const row = el('p', 'cq-fact');
            row.append(el('span', 'cq-fact-label', ui(label)), el('span', 'cq-fact-value', value));
            facts.append(row);
        }
        const status = el('p', 'cq-status');
        status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
        if (notice) status.textContent = notice;
        const parts = [title, facts, status];
        const pending = data.requests.find((row) => row.status === 'pending');
        if (data.eligible && !pending) parts.push(requestForm(state, status));
        else if (!data.eligible) parts.push(el('p', 'cq-muted', ui(ERRORS[data.ineligible_reason] || ERRORS.creator_role_required)));
        if (data.requests.length) parts.push(history(state, status));
        if (data.can_review) parts.push(reviewEntry(state));
        state.host.replaceChildren(...parts);
    }

    function field(labelText, control, id) {
        const wrap = el('p', 'cq-field');
        const label = el('label', '', ui(labelText));
        control.id = id; label.htmlFor = id;
        wrap.append(label, control);
        return wrap;
    }

    function requestForm(state, status) {
        const { data, accountId } = state;
        const form = el('form', 'cq-form');
        form.noValidate = true;
        const total = document.createElement('input');
        total.type = 'number'; total.inputMode = 'numeric'; total.step = '1'; total.required = true;
        total.min = String(data.quota.current + 1); total.max = String(data.limits.max_total);
        const reason = document.createElement('textarea');
        reason.required = true; reason.maxLength = data.limits.text_max; reason.rows = 3;
        const hint = el('p', 'cq-muted', ui('Eine Anfrage ändert dein Limit nicht. Ein Owner oder Admin prüft sie und legt das Gesamtlimit selbst fest.'));
        const used = el('p', 'cq-muted', ui('{used} von {limit} Anfragen in den letzten 24 Stunden', { used: data.limits.used_24h, limit: data.limits.per_24h }));
        const submit = el('button', 'cq-primary', ui('Anfrage senden'));
        submit.type = 'submit';
        form.append(
            el('h4', 'cq-subtitle', ui('Höheres Limit anfragen')),
            field('Gewünschtes Gesamtlimit', total, `cqDesired${accountId}`),
            field('Begründung', reason, `cqReason${accountId}`),
            hint, used, submit,
        );
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            const desired = Number(total.value);
            if (!/^\d+$/.test(total.value.trim()) || !Number.isSafeInteger(desired) || desired <= data.quota.current || desired > data.limits.max_total) {
                status.textContent = message({ code: 'invalid_desired_total' }); total.focus(); return;
            }
            if (!reason.value.trim() || reason.value.length > data.limits.text_max) {
                status.textContent = message({ code: 'invalid_reason' }); reason.focus(); return;
            }
            if (!live(state)) return;
            submit.disabled = true;
            try {
                await api('/requests', accountId, 'POST', { desired_total: desired, reason: reason.value });
                if (live(state)) load(state, ui('Anfrage gesendet. Dein Limit bleibt unverändert, bis ein Owner oder Admin entscheidet.'));
            } catch (error) {
                if (!live(state)) return;
                if (error.code === 'account_mismatch') { switched(state); return; }
                submit.disabled = false;
                status.textContent = message(error);
            }
        });
        return form;
    }

    function history(state, status) {
        const wrap = el('section', 'cq-history');
        wrap.append(el('h4', 'cq-subtitle', ui('Deine Anfragen')));
        const list = el('ul', 'cq-list');
        for (const row of state.data.requests) {
            const item = el('li', `cq-item cq-${row.status}`);
            item.append(
                el('p', 'cq-item-head', `${ui(STATUS[row.status] || row.status)} · ${when(row.created_at)}`),
                el('p', '', ui('Gewünscht: {desired} (Limit bei Anfrage: {submitted})', { desired: row.desired_total, submitted: row.submitted_quota })),
                el('p', 'cq-literal', row.reason),
            );
            if (row.status === 'approved') item.append(el('p', '', ui('Neues Gesamtlimit: {total}', { total: row.approved_total })));
            if (row.reviewer_note) {
                const note = el('p', 'cq-note');
                note.append(el('span', 'cq-fact-label', ui('Notiz der Prüfung:')), document.createTextNode(' '), el('span', 'cq-literal', row.reviewer_note));
                item.append(note);
            }
            if (row.status === 'pending') {
                const cancel = el('button', '', ui('Anfrage zurückziehen'));
                cancel.type = 'button';
                cancel.addEventListener('click', async () => {
                    if (!live(state)) return;
                    cancel.disabled = true;
                    try {
                        await api(`/requests/${row.id}/cancel`, state.accountId, 'POST', {});
                        if (live(state)) load(state, ui('Anfrage zurückgezogen. Dein Limit ist unverändert.'));
                    } catch (error) {
                        if (!live(state)) return;
                        if (error.code === 'account_mismatch') { switched(state); return; }
                        status.textContent = message(error);
                        if (STALE.has(error.code) || error.status === 404) load(state, message(error));
                        else cancel.disabled = false;
                    }
                });
                item.append(cancel);
            }
            list.append(item);
        }
        wrap.append(list);
        return wrap;
    }

    // ----- owner/admin review: shown only when the server reports the capability -----

    function reviewEntry(state) {
        const wrap = el('section', 'cq-review');
        const toggle = el('button', '', ui('Anfragen prüfen'));
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', String(state.reviewOpen));
        const body = el('div', 'cq-review-body');
        body.id = `cqReview${state.accountId}`;
        toggle.setAttribute('aria-controls', body.id);
        body.hidden = !state.reviewOpen;
        toggle.addEventListener('click', () => {
            state.reviewOpen = !state.reviewOpen;
            toggle.setAttribute('aria-expanded', String(state.reviewOpen));
            body.hidden = !state.reviewOpen;
            if (state.reviewOpen) loadReview(state, body);
        });
        wrap.append(toggle, body);
        if (state.reviewOpen) loadReview(state, body);
        return wrap;
    }

    async function loadReview(state, body, notice) {
        const sequence = state.reviewSequence = (state.reviewSequence || 0) + 1;
        body.replaceChildren(el('p', 'cq-muted', ui('Anfragen werden geladen …')));
        try {
            const data = await api(`/review-requests?view=${state.reviewView}`, state.accountId);
            if (!live(state) || !body.isConnected || sequence !== state.reviewSequence) return;
            renderReview(state, body, data, notice);
        } catch (error) {
            if (!live(state) || !body.isConnected || sequence !== state.reviewSequence) return;
            if (error.code === 'account_mismatch') { switched(state); return; }
            const failure = el('p', 'cq-status cq-error', message(error));
            failure.setAttribute('role', 'alert');
            body.replaceChildren(failure);
        }
    }

    function renderReview(state, body, data, notice) {
        const controls = el('div', 'cq-review-controls');
        const view = document.createElement('select');
        for (const [value, label] of [['pending', 'Offene Anfragen'], ['closed', 'Abgeschlossene Anfragen']]) {
            const option = el('option', '', ui(label)); option.value = value; view.append(option);
        }
        view.value = data.view;
        view.addEventListener('change', () => { state.reviewView = view.value; loadReview(state, body); });
        const refresh = el('button', '', ui('Liste neu laden'));
        refresh.type = 'button';
        refresh.addEventListener('click', () => loadReview(state, body));
        controls.append(field('Ansicht', view, `cqReviewView${state.accountId}`), refresh);
        const status = el('p', 'cq-status');
        status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
        if (notice) status.textContent = notice;
        const parts = [controls, status];
        if (!data.entries.length) {
            parts.push(el('p', 'cq-muted', ui(data.view === 'pending' ? 'Keine offenen Anfragen.' : 'Keine abgeschlossenen Anfragen.')));
        } else {
            const list = el('ul', 'cq-list');
            data.entries.forEach((entry) => list.append(reviewItem(state, body, entry, status)));
            parts.push(list);
        }
        if (!data.complete) parts.push(el('p', 'cq-muted', ui('Es werden höchstens {limit} Anfragen angezeigt.', { limit: data.limit })));
        body.replaceChildren(...parts);
    }

    function reviewItem(state, body, entry, status) {
        const item = el('li', `cq-item cq-${entry.status}`);
        item.append(
            el('p', 'cq-item-head', `${entry.requester.username} · ${ui(STATUS[entry.status] || entry.status)} · ${when(entry.created_at)}`),
            el('p', '', ui('Gewünscht: {desired} · Limit bei Anfrage: {submitted} · Aktuelles Limit: {current} · Aktive Kampagnen: {active}', {
                desired: entry.desired_total, submitted: entry.submitted_quota,
                current: quotaText(entry.live), active: entry.live.active_count,
            })),
            el('p', 'cq-literal', entry.reason),
        );
        if (entry.status === 'approved') item.append(el('p', '', ui('Neues Gesamtlimit: {total}', { total: entry.approved_total })));
        if (entry.reviewer_note) item.append(el('p', 'cq-literal cq-note', entry.reviewer_note));
        if (entry.status === 'pending') item.append(decisionForm(state, body, entry, status));
        return item;
    }

    function decisionForm(state, body, entry, status) {
        const form = el('form', 'cq-form cq-decision');
        form.noValidate = true;
        const prefix = `cqDecision${state.accountId}-${entry.id}`;
        // Deliberately empty: the reviewer types the final total; nothing is copied from the request.
        const total = document.createElement('input');
        total.type = 'number'; total.inputMode = 'numeric'; total.step = '1';
        if (entry.live.current !== null) total.min = String(Math.max(entry.live.current + 1, entry.live.active_count));
        total.max = '2147483647';
        const note = document.createElement('textarea');
        note.maxLength = 500; note.rows = 2;
        const actions = el('p', 'cq-actions');
        const approve = el('button', 'cq-primary', ui('Genehmigen …'));
        approve.type = 'button';
        const reject = el('button', '', ui('Ablehnen'));
        reject.type = 'button';
        actions.append(approve, reject);
        const confirmRow = el('p', 'cq-actions cq-confirm');
        confirmRow.hidden = true;
        const confirmText = el('span', 'cq-confirm-text');
        const confirm = el('button', 'cq-primary', ui('Gesamtlimit bestätigen'));
        confirm.type = 'button';
        const back = el('button', '', ui('Zurück zur Eingabe'));
        back.type = 'button';
        confirmRow.append(confirmText, confirm, back);
        form.append(
            field('Neues Gesamtlimit (manuell festlegen)', total, `${prefix}-total`),
            field('Notiz (optional, für die anfragende Person sichtbar)', note, `${prefix}-note`),
            actions, confirmRow,
        );
        form.addEventListener('submit', (event) => event.preventDefault());
        const all = [total, note, approve, reject, confirm, back];
        const lock = (locked) => all.forEach((node) => { node.disabled = locked; });

        async function send(decision, approvedTotal) {
            if (!live(state) || !body.isConnected) return;
            lock(true);
            const payload = { decision, expected_current_quota: entry.live.assigned ? entry.live.current : null };
            if (decision === 'approve') payload.approved_total = approvedTotal;
            if (note.value.trim()) payload.reviewer_note = note.value;
            try {
                await api(`/review-requests/${entry.id}/decision`, state.accountId, 'POST', payload);
                if (!live(state)) return;
                const done = decision === 'approve'
                    ? ui('Genehmigt: {user} hat jetzt ein Gesamtlimit von {total}.', { user: entry.requester.username, total: approvedTotal })
                    : ui('Abgelehnt: Das Limit von {user} bleibt unverändert.', { user: entry.requester.username });
                loadReview(state, body, done);
                if (entry.requester.id === state.accountId) load(state);
            } catch (error) {
                if (!live(state) || !body.isConnected) return;
                if (error.code === 'account_mismatch') { switched(state); return; }
                status.textContent = message(error);
                if (STALE.has(error.code) || error.status === 404) {
                    // Stale: never replay the decision; keep this entry locked until a fresh list loads.
                    confirmRow.hidden = true;
                    const again = el('button', '', ui('Liste neu laden'));
                    again.type = 'button';
                    again.addEventListener('click', () => loadReview(state, body));
                    form.append(el('p', 'cq-error', ui(CONFLICT)), again);
                } else {
                    lock(false);
                    confirmRow.hidden = true; actions.hidden = false;
                }
            }
        }

        approve.addEventListener('click', () => {
            const value = total.value.trim();
            const chosen = Number(value);
            const current = entry.live.current;
            if (!/^\d+$/.test(value) || !Number.isSafeInteger(chosen) || chosen > 2147483647) {
                status.textContent = message({ code: 'invalid_approved_total' }); total.focus(); return;
            }
            if (current === null || chosen <= current) {
                status.textContent = message({ code: 'approved_total_not_above_current' }); total.focus(); return;
            }
            if (chosen < entry.live.active_count) {
                status.textContent = message({ code: 'approved_total_below_active' }); total.focus(); return;
            }
            confirmText.textContent = ui('Limit von {user} von {current} auf {total} setzen?', { user: entry.requester.username, current, total: chosen });
            confirm.dataset.total = String(chosen);
            actions.hidden = true; confirmRow.hidden = false; total.disabled = true;
            confirm.focus();
        });
        back.addEventListener('click', () => {
            confirmRow.hidden = true; actions.hidden = false; total.disabled = false; total.focus();
        });
        confirm.addEventListener('click', () => send('approve', Number(confirm.dataset.total)));
        reject.addEventListener('click', () => send('reject'));
        return form;
    }

    window.VTTCampaignQuota = { mount };
}());
