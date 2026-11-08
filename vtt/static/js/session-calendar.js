/* Campaign calendar: authenticated data, local dates, and explicit series actions. */
const labels = {once: 'Einmalig', weekly: 'Jede Woche', biweekly: 'Alle zwei Wochen', monthly: 'Jeden Monat'};
const statuses = {scheduled: 'Geplant', ready: 'Bereit', in_progress: 'Läuft', paused: 'Pausiert', completed: 'Beendet', ended: 'Beendet', cancelled: 'Abgesagt'};
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const dateOf = value => new Date(`${value.slice(0, 10)}T12:00:00Z`);
const iso = day => day.toISOString().slice(0, 10);
const addDays = (value, days) => { const d = dateOf(value); d.setUTCDate(d.getUTCDate() + days); return iso(d); };
const dateLabel = value => dateOf(value).toLocaleDateString('de-DE', {day:'numeric', month:'long', year:'numeric', timeZone:'UTC'});
const todayIn = timezone => new Intl.DateTimeFormat('sv-SE', {timeZone:timezone, year:'numeric', month:'2-digit', day:'2-digit'}).format(new Date());

export async function mountSessionCalendar(root, {campaignId, canManage, campaignName, onChanged}) {
    if (!document.querySelector('link[data-session-calendar-css]')) {
        const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = '/static/css/session-calendar.css';
        css.dataset.sessionCalendarCss = ''; document.head.append(css);
    }
    const tz = 'Europe/Berlin';
    const state = {scope:'month', anchor:todayIn(tz), data:null, version:0, busy:false, requestKey:crypto.randomUUID(), inputDigest:null};
    root.innerHTML = `
        <div class="sc-heading"><div><span class="book-scene-panel-kicker">Gemeinsam spielen</span><h2 class="book-scene-panel-title">Session-Kalender</h2></div>
            <span class="sc-zone">Europe/Berlin</span></div>
        <div class="sc-toolbar" aria-label="Kalenderansicht">${[['week','Woche'],['month','Monat'],['year','Jahr']].map(([scope, text]) => `<button type="button" class="btn btn-secondary btn-sm" data-scope="${scope}" aria-pressed="${scope === state.scope}">${text}</button>`).join('')}</div>
        <div class="sc-navigation"><button type="button" class="btn btn-secondary btn-sm" data-move="-1" aria-label="Vorheriger Zeitraum">‹</button>
            <h3 data-period aria-live="polite"></h3><button type="button" class="btn btn-secondary btn-sm" data-move="1" aria-label="Nächster Zeitraum">›</button>
            <button type="button" class="btn btn-secondary btn-sm" data-today>Heute</button></div>
        <div data-calendar-content aria-busy="true"></div>
        <p data-calendar-status role="status" aria-live="polite"></p>
        ${canManage ? `
        <details class="sc-planner"><summary>Termin oder Serie planen</summary>
            <form data-calendar-form aria-busy="false">
                <label class="sc-wide">Session-Name<input name="name" maxlength="100" required value="${escape(`${campaignName} – Sitzung`.slice(0,100))}"></label>
                <label>Erster Termin<input name="first_local" type="datetime-local" required step="60"></label>
                <label>Wiederholung<select name="frequency" aria-label="Wiederholung">${Object.entries(labels).map(([value, text]) => `<option value="${value}">${text}</option>`).join('')}</select></label>
                <label>Dauer in Minuten<input name="duration_minutes" type="number" min="1" max="1440" placeholder="Optional"></label>
                <label>Letzter Tag der Serie<input name="until" type="date" disabled><small>Leer lassen: fortlaufend.</small></label>
                <p class="sc-wide sc-preview" data-recurrence-preview>Ein einzelner Termin.</p>
                <p class="sc-wide sc-help">Uhrzeit in Europe/Berlin, auch nach der Zeitumstellung. Monatlich am gleichen Kalendertag, in kürzeren Monaten am letzten Tag. Eine nicht existierende Uhrzeit im Frühjahr wird vorgerückt; bei doppelten Herbst-Uhrzeiten gilt die erste.</p>
                <button class="btn btn-primary sc-wide" type="submit">Termin speichern</button>
                <p class="sc-wide" data-form-status role="status" aria-live="polite"></p>
            </form>
        </details><div data-calendar-series></div>` : ''}`;
    const content = root.querySelector('[data-calendar-content]');
    const status = root.querySelector('[data-calendar-status]');
    const setStatus = (text, error=false) => { status.textContent = text; status.classList.toggle('is-error', error); };
    const request = (path, method='GET', payload) => window.Auth.makeAuthRequest(`/api/campaigns/${campaignId}/${path}`, method, payload);
    const refreshSummary = async () => {
        try { await onChanged?.(); }
        catch (_error) { setStatus('Terminplan gespeichert. Bitte die Seite neu laden, um die Session-Vorbereitung zu aktualisieren.', true); }
    };

    function eventMarkup(entry) {
        return `<li class="sc-event ${entry.status === 'cancelled' ? 'is-cancelled' : ''}">
            <div><time datetime="${escape(entry.scheduled_at)}">${escape(entry.local_time)}</time> <strong>${escape(entry.name)}</strong>
            <small>${escape(statuses[entry.status] || entry.status)}${entry.series_id && state.data.series.find(s => s.id === entry.series_id)?.frequency !== 'once' ? ' · Serie' : ''}${entry.duration_minutes ? ` · ${entry.duration_minutes} Min.` : ''}</small></div>
            ${canManage && entry.cancellable ? `<button type="button" class="btn btn-secondary btn-sm" data-cancel="${entry.id}">Termin absagen</button>` : ''}</li>`;
    }

    function agenda(day) {
        const entries = state.data.entries.filter(e => e.date === day);
        const target = root.querySelector('[data-day-agenda]');
        if (target) target.innerHTML = `<h4>${escape(dateLabel(day))}</h4><ul class="sc-agenda">${entries.map(eventMarkup).join('') || '<li>Keine Session an diesem Tag.</li>'}</ul>`;
    }

    function render() {
        const data = state.data;
        root.querySelectorAll('[data-scope]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.scope === state.scope)));
        const start = dateOf(data.start);
        root.querySelector('[data-period]').textContent = state.scope === 'year' ? String(start.getUTCFullYear())
            : state.scope === 'month' ? start.toLocaleDateString('de-DE', {month:'long', year:'numeric', timeZone:'UTC'})
            : `${dateLabel(data.start)} – ${dateLabel(addDays(data.end, -1))}`;
        const grouped = new Map();
        data.entries.forEach(e => { if (!grouped.has(e.date)) grouped.set(e.date, []); grouped.get(e.date).push(e); });
        if (state.scope === 'year') {
            content.innerHTML = `<div class="sc-year">${Array.from({length:12}, (_, i) => {
                const month = `${data.start.slice(0,4)}-${String(i+1).padStart(2,'0')}`;
                const entries = data.entries.filter(e => e.date.startsWith(month) && e.status !== 'cancelled');
                return `<button type="button" class="sc-month" data-month="${month}-01"><strong>${dateOf(`${month}-01`).toLocaleDateString('de-DE',{month:'long',timeZone:'UTC'})}</strong><span>${entries.length} ${entries.length === 1 ? 'Termin' : 'Termine'}</span></button>`;
            }).join('')}</div>`;
        } else if (state.scope === 'week') {
            content.innerHTML = `<div class="sc-week">${Array.from({length:7}, (_, i) => {
                const day = addDays(data.start, i);
                return `<section><h4>${escape(dateOf(day).toLocaleDateString('de-DE', {weekday:'long', day:'numeric', month:'short', timeZone:'UTC'}))}</h4><ul class="sc-agenda">${(grouped.get(day) || []).map(eventMarkup).join('') || '<li class="sc-empty">Keine Session</li>'}</ul></section>`;
            }).join('')}</div>`;
        } else {
            const before = (start.getUTCDay() + 6) % 7;
            const first = addDays(data.start, -before);
            const days = Math.round((dateOf(data.end) - start) / 86400000);
            const cells = Math.ceil((before + days) / 7) * 7;
            content.innerHTML = `<div class="sc-month-grid">${['Mo','Di','Mi','Do','Fr','Sa','So'].map(d => `<span class="sc-weekday">${d}</span>`).join('')}
                ${Array.from({length:cells}, (_, i) => {
                    const day = addDays(first, i), entries = grouped.get(day) || [];
                    const active = entries.filter(e => e.status !== 'cancelled');
                    const outside = day < data.start || day >= data.end;
                    return `<button type="button" class="sc-day${outside ? ' is-outside' : ''}${day === todayIn(tz) ? ' is-today' : ''}" data-day="${day}" ${outside ? 'disabled' : ''}
                        aria-label="${escape(dateLabel(day))}: ${active.length} Termine"><span>${dateOf(day).getUTCDate()}</span>
                        <small>${active.length ? `${active.length} ●` : entries.length ? '–' : '&nbsp;'}</small></button>`;
                }).join('')}</div><div data-day-agenda></div>`;
            agenda(grouped.has(state.anchor) ? state.anchor : (data.entries.find(e => e.status !== 'cancelled')?.date || data.start));
        }
        const seriesBox = root.querySelector('[data-calendar-series]');
        if (seriesBox) {
            const series = data.series.filter(s => s.frequency !== 'once' && s.status === 'active');
            seriesBox.innerHTML = series.length ? `<details class="sc-series"><summary>Serien verwalten (${series.length})</summary><ul class="sc-agenda">${series.map(s => `<li class="sc-event"><div><strong>${escape(s.name)}</strong><small>${escape(labels[s.frequency])} · ${escape(s.first_local.slice(11,16))} · ${escape(s.timezone)}${s.until ? ` · bis ${escape(dateLabel(s.until))}` : ' · fortlaufend'}</small></div><button class="btn btn-secondary btn-sm" type="button" data-stop="${s.id}">Serie beenden</button></li>`).join('')}</ul></details>` : '';
        }
    }

    async function load() {
        const version = ++state.version;
        content.setAttribute('aria-busy', 'true'); setStatus('Kalender wird geladen …');
        try {
            const data = await request(`session-calendar?${new URLSearchParams({scope:state.scope, anchor:state.anchor, timezone:tz})}`);
            if (!root.isConnected || version !== state.version) return;
            state.data = data; render();
            const count = data.entries.filter(e => e.status !== 'cancelled').length;
            setStatus(`${count} ${count === 1 ? 'Termin' : 'Termine'} im ausgewählten Zeitraum.`);
        } catch (error) {
            if (!root.isConnected || version !== state.version) return;
            state.data = null; content.replaceChildren();
            root.querySelector('[data-calendar-series]')?.replaceChildren();
            setStatus(error.message || 'Kalender konnte nicht geladen werden.', true);
        } finally { if (version === state.version) content.setAttribute('aria-busy', 'false'); }
    }

    root.addEventListener('click', async event => {
        const button = event.target.closest('button');
        if (!button || !root.contains(button) || state.busy) return;
        if (button.dataset.day) { state.anchor = button.dataset.day; agenda(button.dataset.day); return; }
        if (button.dataset.month) { state.anchor = button.dataset.month; state.scope = 'month'; await load(); return; }
        if (button.dataset.scope) { state.scope = button.dataset.scope; await load(); return; }
        if (button.hasAttribute('data-today')) { state.anchor = todayIn(tz); await load(); return; }
        if (button.dataset.move) {
            const d = dateOf(state.data?.start || state.anchor), move = Number(button.dataset.move);
            if (state.scope === 'year') d.setUTCFullYear(d.getUTCFullYear() + move);
            else if (state.scope === 'month') { d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + move); }
            else d.setUTCDate(d.getUTCDate() + move * 7);
            state.anchor = iso(d); await load(); return;
        }
        const stop = button.dataset.stop, cancel = button.dataset.cancel;
        if (!stop && !cancel) return;
        const question = stop ? 'Serie beenden und alle noch nicht gestarteten zukünftigen Termine absagen? Gespielte Sessions bleiben erhalten.' : 'Nur diesen Termin absagen? Die übrige Serie bleibt bestehen.';
        if (!window.confirm(question)) return;
        state.busy = true; button.disabled = true;
        try {
            await request(stop ? `session-series/${stop}/stop` : `sessions/${cancel}/cancel-appointment`, 'POST', {});
            await load();
            await refreshSummary();
        } catch (error) { setStatus(error.message || 'Absage konnte nicht bestätigt werden.', true); }
        finally { state.busy = false; if (button.isConnected) button.disabled = false; }
    });

    const form = root.querySelector('[data-calendar-form]');
    if (form) {
        const first = form.elements.first_local, until = form.elements.until, frequency = form.elements.frequency;
        first.min = `${todayIn(tz)}T00:00`;
        const updatePreview = () => {
            until.disabled = frequency.value === 'once'; until.min = first.value.slice(0,10);
            const at = first.value ? `${dateLabel(first.value)} um ${first.value.slice(11,16)} Uhr` : 'dem gewählten Starttermin';
            form.querySelector('[data-recurrence-preview]').textContent = `${labels[frequency.value]} ab ${at}${!until.disabled && until.value ? `, bis einschließlich ${dateLabel(until.value)}` : frequency.value !== 'once' ? ', bis du die Serie beendest' : ''}.`;
            form.querySelector('[type="submit"]').textContent = frequency.value === 'once' ? 'Termin speichern' : 'Serie speichern';
        };
        form.addEventListener('input', updatePreview);
        form.addEventListener('submit', async event => {
            event.preventDefault(); if (state.busy) return;
            const payload = {name:form.elements.name.value.trim(), first_local:first.value, frequency:frequency.value, timezone:tz,
                until:until.disabled ? null : until.value || null, duration_minutes:form.elements.duration_minutes.value ? Number(form.elements.duration_minutes.value) : null};
            const digest = JSON.stringify(payload);
            if (state.inputDigest !== null && digest !== state.inputDigest) state.requestKey = crypto.randomUUID();
            state.inputDigest = digest; payload.request_key = state.requestKey;
            const button = form.querySelector('[type="submit"]'), message = form.querySelector('[data-form-status]');
            state.busy = true; button.disabled = true; form.setAttribute('aria-busy', 'true'); message.textContent = 'Terminplan wird gespeichert …';
            try {
                await request('session-series', 'POST', payload);
                state.anchor = first.value.slice(0,10);
                message.textContent = frequency.value === 'once' ? 'Termin gespeichert.' : 'Serie gespeichert. Kommende Termine werden automatisch angelegt.';
                await load();
                await refreshSummary();
            } catch (error) { message.textContent = error.message || 'Speichern nicht bestätigt. Erneut speichern erzeugt keinen doppelten Termin.'; }
            finally { state.busy = false; button.disabled = false; form.setAttribute('aria-busy', 'false'); }
        });
    }
    await load();
}
