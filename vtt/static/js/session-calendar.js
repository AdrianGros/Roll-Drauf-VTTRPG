/* C06 calendar: the user's own sessions (all campaigns, identical for DM and Player) and the
   per-campaign planner (series + date polls). Authority is always the server: this module
   only renders what the authenticated API returns and never derives rights or dates itself. */
const ui = (source, parameters = {}) => (globalThis.VTTUi
    ? globalThis.VTTUi(source, parameters)
    : source.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, key) => (key in parameters ? String(parameters[key]) : match)));
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const language = () => (globalThis.VTTI18n?.locale?.() || document.documentElement.lang || 'de');
const intlLocale = () => (language() === 'en' ? 'en-GB' : 'de-DE');
const fail = error => ui(error?.message || 'Die Anfrage ist fehlgeschlagen. Bitte versuche es erneut.');
const api = (path, method = 'GET', payload) => window.Auth.makeAuthRequest(`/api/campaigns/${path}`, method, payload ?? (method === 'GET' ? null : {}));

const parseDay = value => new Date(`${String(value).slice(0, 10)}T12:00:00Z`);
const isoDay = day => day.toISOString().slice(0, 10);
const shiftDays = (value, days) => { const d = parseDay(value); d.setUTCDate(d.getUTCDate() + days); return isoDay(d); };
const shiftMonths = (value, months) => { const d = parseDay(value); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + months); return isoDay(d); };
const dayLabel = (value, options = {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'}) =>
    new Intl.DateTimeFormat(intlLocale(), {...options, timeZone: 'UTC'}).format(parseDay(value));
const zoneName = () => {
    try { const name = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Berlin'; new Intl.DateTimeFormat('en', {timeZone: name}); return name; }
    catch (_error) { return 'Europe/Berlin'; }
};
const todayIn = timezone => new Intl.DateTimeFormat('sv-SE', {timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
const instantLabel = (utcIso, timezone) => new Intl.DateTimeFormat(intlLocale(), {dateStyle: 'full', timeStyle: 'short', timeZone: timezone}).format(new Date(utcIso));

const statusLabel = status => ({
    scheduled: ui('Geplant'), ready: ui('Bereit'), in_progress: ui('Läuft'), paused: ui('Pausiert'),
    completed: ui('Beendet'), ended: ui('Beendet'), cancelled: ui('Abgesagt'),
}[status] || status);
const frequencyLabel = frequency => ({
    once: ui('Einmalig'), weekly: ui('Jede Woche'), biweekly: ui('Alle zwei Wochen'), monthly: ui('Jeden Monat'),
}[frequency] || frequency);

function ensureStylesheet() {
    if (document.querySelector('link[data-session-calendar-css]')) return;
    const css = document.createElement('link');
    css.rel = 'stylesheet'; css.href = '/static/css/session-calendar.css'; css.dataset.sessionCalendarCss = '';
    document.head.append(css);
}

/* ------------------------------------------------------------------ own calendar */

export async function mountOwnCalendar(root, {timezone = zoneName()} = {}) {
    ensureStylesheet();
    root.setAttribute('data-session-calendar', '');
    const state = {scope: 'rolling30', anchor: todayIn(timezone), campaign: '', day: '', entries: [], cursor: null, data: null,
                   version: 0, alertVersion: 0, busy: false, materialized: false};
    root.innerHTML = `
        <div class="sc-heading"><div><span class="book-scene-panel-kicker">${esc(ui('Gemeinsam spielen'))}</span>
            <h2 class="book-scene-panel-title">${esc(ui('Session-Kalender'))}</h2></div>
            <span class="sc-zone" data-zone>${esc(ui('Zeitzone: {zone}', {zone: timezone}))}</span></div>
        <div class="sc-toolbar" role="group" aria-label="${esc(ui('Kalenderansicht'))}">
            <button type="button" class="btn btn-secondary btn-sm" data-scope="rolling30">${esc(ui('30 Tage'))}</button>
            <button type="button" class="btn btn-secondary btn-sm" data-scope="month">${esc(ui('Monat'))}</button>
            <label class="sc-filter">${esc(ui('Kampagne'))}
                <select data-campaign-filter aria-label="${esc(ui('Kampagne filtern'))}"><option value="">${esc(ui('Alle Kampagnen'))}</option></select></label>
            <button type="button" class="btn btn-secondary btn-sm" data-refresh>${esc(ui('Aktualisieren'))}</button>
        </div>
        <div class="sc-navigation"><button type="button" class="btn btn-secondary btn-sm" data-move="-1" aria-label="${esc(ui('Vorheriger Zeitraum'))}">‹</button>
            <h3 data-period aria-live="polite"></h3>
            <button type="button" class="btn btn-secondary btn-sm" data-move="1" aria-label="${esc(ui('Nächster Zeitraum'))}">›</button>
            <button type="button" class="btn btn-secondary btn-sm" data-today>${esc(ui('Heute'))}</button></div>
        <div data-month-grid></div>
        <div data-calendar-content aria-busy="true"></div>
        <p data-calendar-status role="status" aria-live="polite"></p>
        <button type="button" class="btn btn-secondary btn-sm" data-load-more hidden>${esc(ui('Weitere Termine laden'))}</button>
        <section class="sc-alerts" data-calendar-alerts aria-label="${esc(ui('Offene Punkte'))}"></section>`;
    const content = root.querySelector('[data-calendar-content]');
    const status = root.querySelector('[data-calendar-status]');
    const setStatus = (text, error = false) => { status.textContent = text; status.classList.toggle('is-error', error); };

    function eventMarkup(entry) {
        const details = [esc(entry.campaign_name), esc(statusLabel(entry.status)),
            entry.series_id ? esc(ui('Serie')) : '', entry.duration_minutes ? esc(ui('{minutes} Min.', {minutes: entry.duration_minutes})) : '']
            .filter(Boolean).join(' · ');
        return `<li class="sc-event${entry.cancelled ? ' is-cancelled' : ''}" data-session-id="${Number(entry.session_id)}" data-campaign-id="${Number(entry.campaign_id)}" data-status="${esc(entry.status)}">
            <div><time datetime="${esc(entry.local_iso)}">${esc(entry.local_time)}</time> <strong>${esc(entry.session_name)}</strong>
                <small>${details}</small></div>
            <span class="sc-actions"><a class="btn btn-secondary btn-sm" href="${esc(entry.hub_href)}">${esc(ui('Hub öffnen'))}</a>
            ${entry.can_manage && entry.cancellable ? `<button type="button" class="btn btn-secondary btn-sm" data-cancel="${Number(entry.session_id)}" data-campaign="${Number(entry.campaign_id)}">${esc(ui('Termin absagen'))}</button>` : ''}</span></li>`;
    }

    function renderGrid() {
        const box = root.querySelector('[data-month-grid]');
        const data = state.data;
        if (!data || state.scope !== 'month') { box.replaceChildren(); return; }
        const counts = new Map();
        state.entries.filter(e => !e.cancelled).forEach(e => counts.set(e.local_date, (counts.get(e.local_date) || 0) + 1));
        const lead = (parseDay(data.start).getUTCDay() + 6) % 7;
        const total = Math.round((parseDay(data.end) - parseDay(data.start)) / 86400000);
        const weekdays = Array.from({length: 7}, (_, i) => new Intl.DateTimeFormat(intlLocale(), {weekday: 'short', timeZone: 'UTC'}).format(new Date(Date.UTC(2024, 0, 1 + i, 12))));
        box.innerHTML = `<div class="sc-month-grid">${weekdays.map(d => `<span class="sc-weekday">${esc(d)}</span>`).join('')}
            ${Array.from({length: lead}, () => '<span class="sc-blank"></span>').join('')}
            ${Array.from({length: total}, (_, i) => {
                const day = shiftDays(data.start, i), n = counts.get(day) || 0;
                return `<button type="button" class="sc-day${day === todayIn(timezone) ? ' is-today' : ''}${state.day === day ? ' is-selected' : ''}" data-day="${day}"
                    aria-pressed="${state.day === day}" aria-label="${esc(ui('{date}: {count} Termine', {date: dayLabel(day), count: n}))}"><span>${Number(day.slice(8, 10))}</span><small>${n ? `${n} ●` : '&nbsp;'}</small></button>`;
            }).join('')}</div>`;
    }

    function render() {
        const data = state.data;
        root.querySelectorAll('[data-scope]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.scope === state.scope)));
        const last = shiftDays(data.end, -1);
        root.querySelector('[data-period]').textContent = state.scope === 'month'
            ? dayLabel(data.start, {month: 'long', year: 'numeric'}) : `${dayLabel(data.start, {day: 'numeric', month: 'short'})} – ${dayLabel(last, {day: 'numeric', month: 'short', year: 'numeric'})}`;
        const select = root.querySelector('[data-campaign-filter]');
        select.replaceChildren(new Option(ui('Alle Kampagnen'), ''), ...data.campaigns.map(c => new Option(c.name, String(c.id))));
        select.value = data.campaigns.some(c => String(c.id) === state.campaign) ? state.campaign : '';
        renderGrid();
        const shown = state.day ? state.entries.filter(e => e.local_date === state.day) : state.entries;
        const days = [...new Set(shown.map(e => e.local_date))];
        content.innerHTML = days.length ? days.map(day => `<section class="sc-day-block" data-agenda-day="${day}"><h4>${esc(dayLabel(day))}</h4>
            <ul class="sc-agenda">${shown.filter(e => e.local_date === day).map(eventMarkup).join('')}</ul></section>`).join('')
            : `<p class="sc-empty" data-empty>${esc(ui('Keine Session im gewählten Zeitraum.'))}</p>`;
        root.querySelector('[data-load-more]').hidden = !state.cursor;
        const active = state.entries.filter(e => !e.cancelled).length;
        setStatus(`${ui('{count} Termine geladen.', {count: active})} ${state.cursor ? ui('Es gibt weitere Termine in diesem Zeitraum.') : ui('Alle Termine dieses Zeitraums sind geladen.')}`);
    }

    function query(extra = {}) {
        const params = new URLSearchParams({scope: state.scope, anchor: state.anchor, timezone, ...extra});
        if (state.campaign) params.set('campaign_ids', state.campaign);
        return params.toString();
    }

    function renderAlerts(alerts) {
        const box = root.querySelector('[data-calendar-alerts]');
        const missing = alerts.missing_dates, votes = alerts.open_votes;
        const more = text => `<p class="sc-help">${esc(text)}</p>`;
        box.innerHTML = `<h3>${esc(ui('Offene Punkte'))}</h3>
            ${missing.length || votes.length ? '' : `<p class="sc-empty" data-no-alerts>${esc(ui('Keine offenen Punkte.'))}</p>`}
            ${missing.length ? `<h4>${esc(ui('Termin fehlt'))}</h4><ul class="sc-agenda" data-alert-missing>${missing.map(a => `<li class="sc-event" data-alert-session="${Number(a.session_id)}">
                <div><strong>${esc(a.session_name)}</strong><small>${esc(a.campaign_name)}</small></div>
                <a class="btn btn-secondary btn-sm" href="${esc(a.hub_href)}">${esc(ui('Termin planen'))}</a></li>`).join('')}</ul>` : ''}
            ${alerts.missing_dates_more ? more(ui('Weitere Sessions ohne Termin findest du in den Kampagnen-Hubs.')) : ''}
            ${votes.length ? `<h4>${esc(ui('Deine Antwort fehlt'))}</h4><ul class="sc-agenda" data-alert-votes>${votes.map(a => `<li class="sc-event" data-alert-poll="${Number(a.poll_id)}">
                <div><strong>${esc(a.title)}</strong><small>${esc(a.campaign_name)} · ${esc(ui('{answered} von {total} beantwortet', {answered: a.answered, total: a.total}))}</small></div>
                <a class="btn btn-secondary btn-sm" href="${esc(a.hub_href)}">${esc(ui('Abstimmen'))}</a></li>`).join('')}</ul>` : ''}
            ${alerts.open_votes_more ? more(ui('Weitere offene Abstimmungen findest du in den Kampagnen-Hubs.')) : ''}`;
    }

    async function loadAlerts() {
        const version = ++state.alertVersion;
        try {
            const alerts = await api(`my-session-alerts${state.campaign ? `?campaign_ids=${state.campaign}` : ''}`);
            if (root.isConnected && version === state.alertVersion) renderAlerts(alerts);
        } catch (error) {
            if (root.isConnected && version === state.alertVersion) root.querySelector('[data-calendar-alerts]').textContent = fail(error);
        }
    }

    async function load({append = false} = {}) {
        const version = ++state.version;
        content.setAttribute('aria-busy', 'true'); setStatus(ui('Kalender wird geladen …'));
        try {
            let data = await api(`my-session-calendar?${query(append && state.cursor ? {cursor: state.cursor} : {})}`);
            if (!root.isConnected || version !== state.version) return;
            if (data.can_manage_any && !state.materialized && !append) {
                // Explicit bounded POST for DM/Co-DM only; the GET above stays a pure read.
                state.materialized = true;
                try {
                    const result = await api('my-session-calendar/materialize', 'POST', {});
                    if (result.campaigns.some(c => c.created > 0)) data = await api(`my-session-calendar?${query()}`);
                } catch (error) { setStatus(fail(error), true); }
                if (!root.isConnected || version !== state.version) return;
            }
            state.data = data;
            state.entries = append ? state.entries.concat(data.entries) : data.entries;
            state.cursor = data.next_cursor;
            render();
            if (!append) loadAlerts();
        } catch (error) {
            if (!root.isConnected || version !== state.version) return;
            state.data = null; state.cursor = null; content.replaceChildren();
            root.querySelector('[data-month-grid]').replaceChildren();
            setStatus(fail(error), true);
        } finally { if (version === state.version) content.setAttribute('aria-busy', 'false'); }
    }

    root.addEventListener('change', event => {
        if (event.target.matches('[data-campaign-filter]')) { state.campaign = event.target.value; state.day = ''; load(); }
    });
    root.addEventListener('click', async event => {
        const button = event.target.closest('button');
        if (!button || !root.contains(button) || state.busy) return;
        if (button.dataset.day) { state.day = state.day === button.dataset.day ? '' : button.dataset.day; render(); return; }
        if (button.dataset.scope) { state.scope = button.dataset.scope; state.day = ''; await load(); return; }
        if (button.hasAttribute('data-today')) { state.anchor = todayIn(timezone); state.day = ''; await load(); return; }
        if (button.hasAttribute('data-load-more')) { await load({append: true}); return; }
        if (button.hasAttribute('data-refresh')) { state.materialized = false; state.cursor = null; await load(); return; }
        if (button.dataset.move) {
            const previous = state.anchor, move = Number(button.dataset.move);
            state.anchor = state.scope === 'month' ? shiftMonths(state.data?.start || state.anchor, move) : shiftDays(state.data?.start || state.anchor, move * 30);
            state.day = ''; state.cursor = null;
            await load();
            if (!state.data) {
                // Out-of-range or failed navigation: keep the server's message, show the previous period again.
                const message = status.textContent;
                state.anchor = previous;
                await load();
                setStatus(message, true);
            }
            return;
        }
        if (button.dataset.cancel) {
            if (!window.confirm(ui('Nur diesen Termin absagen? Die übrige Serie bleibt bestehen.'))) return;
            state.busy = true; button.disabled = true;
            try { await api(`${Number(button.dataset.campaign)}/session-appointments/${Number(button.dataset.cancel)}/cancel`, 'POST', {}); state.cursor = null; await load(); }
            catch (error) { setStatus(fail(error), true); }
            finally { state.busy = false; if (button.isConnected) button.disabled = false; }
        }
    });
    await load();
}

/* ------------------------------------------------------------------ campaign planner */

export async function mountCampaignPlanner(root, {campaignId, campaignName = '', canManage = false, sessions = [], notice = '', onChanged} = {}) {
    ensureStylesheet();
    root.setAttribute('data-session-calendar', '');
    const timezone = zoneName();
    const state = {polls: [], series: [], busy: false, requestKey: crypto.randomUUID(), digest: null, seriesKey: crypto.randomUUID(), seriesDigest: null, version: 0};
    root.innerHTML = `
        <div class="sc-heading"><div><span class="book-scene-panel-kicker">${esc(ui('Gemeinsam planen'))}</span>
            <h2 class="book-scene-panel-title">${esc(ui('Terminplanung'))}</h2></div>
            <span class="sc-zone">${esc(ui('Zeitzone: {zone}', {zone: timezone}))}</span></div>
        <p data-planner-status role="status" aria-live="polite"></p>
        <div data-polls aria-busy="true"></div>
        ${canManage ? `<div data-manager-tools></div>` : ''}`;
    const status = root.querySelector('[data-planner-status]');
    const setStatus = (text, error = false) => { status.textContent = text; status.classList.toggle('is-error', error); };
    if (notice) setStatus(notice);
    const pollBox = root.querySelector('[data-polls]');

    function pollMarkup(poll) {
        const manager = poll.can_manage && canManage;
        return `<article class="sc-poll" data-poll data-poll-id="${poll.id}" data-revision="${poll.revision}">
            <h3>${esc(poll.title)}</h3>
            <p class="sc-help">${esc(poll.session_name)} · ${esc(ui('{answered} von {total} Terminen beantwortet', {answered: poll.answered, total: poll.total}))}
                ${poll.my_complete ? '' : `<strong data-open-answers>${esc(ui('Deine Antwort fehlt noch.'))}</strong>`}</p>
            <ul class="sc-agenda">${poll.options.map(o => `<li class="sc-event sc-option" data-option-id="${o.id}">
                <div><time datetime="${esc(o.starts_at)}">${esc(instantLabel(o.starts_at, timezone))}</time>
                    <small>${esc(ui('Ja {yes} · Vielleicht {maybe} · Nein {no}', {yes: o.yes, maybe: o.maybe, no: o.no}))}${o.duration_minutes ? ` · ${esc(ui('{minutes} Min.', {minutes: o.duration_minutes}))}` : ''}
                    ${o.mine ? '' : ` · <em>${esc(ui('Antwort fehlt'))}</em>`}</small></div>
                <span class="sc-actions" role="group" aria-label="${esc(ui('Deine Antwort'))}">${[['yes', ui('Ja')], ['maybe', ui('Vielleicht')], ['no', ui('Nein')]].map(([value, label]) =>
                    `<button type="button" class="btn btn-secondary btn-sm" data-vote="${value}" data-option-id="${o.id}" aria-pressed="${o.mine === value}">${esc(label)}</button>`).join('')}
                ${manager ? `<button type="button" class="btn btn-primary btn-sm" data-finalize="${o.id}">${esc(ui('Diesen Termin festlegen'))}</button>` : ''}</span></li>`).join('')}</ul>
            ${manager ? `<details class="sc-participants"><summary>${esc(ui('Antworten der Mitglieder'))}</summary>
                <table><thead><tr><th>${esc(ui('Mitglied'))}</th>${poll.options.map((o, i) => `<th>${i + 1}</th>`).join('')}</tr></thead>
                <tbody>${poll.participants.map(p => `<tr data-participant="${p.user_id}"><th scope="row">${esc(p.username)}</th>${poll.options.map(o => `<td>${esc(p.answers[o.id] ? ({yes: ui('Ja'), maybe: ui('Vielleicht'), no: ui('Nein')})[p.answers[o.id]] : '–')}</td>`).join('')}</tr>`).join('')}</tbody></table></details>
                <button type="button" class="btn btn-secondary btn-sm" data-cancel-poll>${esc(ui('Abstimmung abbrechen'))}</button>` : ''}</article>`;
    }

    function renderPolls() {
        pollBox.innerHTML = state.polls.length ? state.polls.map(pollMarkup).join('')
            : `<p class="sc-empty" data-no-polls>${esc(ui('Keine offene Terminabstimmung.'))}</p>`;
        renderTools();
    }

    function openSessions() {
        const taken = new Set(state.polls.map(p => p.session_id));
        return sessions.filter(s => !s.scheduled_at && !s.started_at && ['scheduled', 'ready'].includes(s.status) && !taken.has(s.id));
    }

    function addOptionRow(list) {
        const row = document.createElement('div');
        row.className = 'sc-option-row';
        row.innerHTML = `<label>${esc(ui('Terminoption'))}<input type="datetime-local" data-option-local required min="${todayIn(timezone)}T00:00"></label>
            <label>${esc(ui('Dauer in Minuten'))}<input type="number" data-option-duration min="1" max="1440" placeholder="${esc(ui('Optional'))}"></label>
            <button type="button" class="btn btn-secondary btn-sm" data-remove-option>${esc(ui('Entfernen'))}</button>`;
        list.append(row);
    }

    function renderTools() {
        const box = root.querySelector('[data-manager-tools]');
        if (!box || box.dataset.ready === 'true' && box.dataset.pollCount === String(state.polls.length) && box.dataset.seriesCount === String(state.series.length)) return;
        // Keep a half-filled form while polls change underneath it.
        const open = new Set([...box.querySelectorAll('details[open]')].map(d => d.dataset.tool));
        const free = openSessions();
        const series = state.series.filter(s => s.frequency !== 'once' && s.status === 'active');
        box.dataset.ready = 'true'; box.dataset.pollCount = String(state.polls.length); box.dataset.seriesCount = String(state.series.length);
        box.innerHTML = `
            <details class="sc-planner" data-tool="poll"${open.has('poll') ? ' open' : ''}><summary>${esc(ui('Terminabstimmung erstellen'))}</summary>
                ${free.length ? `<form data-poll-form>
                    <label class="sc-wide">${esc(ui('Session ohne Termin'))}<select name="session_id" data-poll-session>${free.map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join('')}</select></label>
                    <label class="sc-wide">${esc(ui('Titel der Abstimmung'))}<input name="title" data-poll-title maxlength="100" required value="${esc(ui('Terminabstimmung'))}"></label>
                    <div class="sc-wide" data-option-list></div>
                    <button type="button" class="btn btn-secondary btn-sm sc-wide" data-add-option>${esc(ui('Weitere Option'))}</button>
                    <p class="sc-wide sc-help">${esc(ui('Höchstens 20 verschiedene Optionen, jeweils in der Zukunft und innerhalb der nächsten zwölf Monate. Uhrzeiten gelten in {zone}.', {zone: timezone}))}</p>
                    <button class="btn btn-primary sc-wide" type="submit">${esc(ui('Abstimmung starten'))}</button></form>`
                    : `<p class="sc-help" data-no-open-sessions>${esc(ui('Alle Sessions haben einen Termin oder eine laufende Abstimmung.'))}</p>`}
                <form data-new-session-form class="sc-inline"><label>${esc(ui('Neue Session ohne Termin'))}<input name="name" maxlength="100" required value="${esc(`${campaignName} – ${ui('Sitzung')}`.slice(0, 100))}"></label>
                    <button class="btn btn-secondary btn-sm" type="submit">${esc(ui('Session anlegen'))}</button></form></details>
            <details class="sc-planner" data-tool="series"${open.has('series') ? ' open' : ''}><summary>${esc(ui('Termin oder Serie planen'))}</summary>
                <form data-series-form data-calendar-form aria-busy="false">
                    <label class="sc-wide">${esc(ui('Session-Name'))}<input name="name" maxlength="100" required value="${esc(`${campaignName} – ${ui('Sitzung')}`.slice(0, 100))}"></label>
                    <label>${esc(ui('Erster Termin'))}<input name="first_local" type="datetime-local" required step="60" min="${todayIn(timezone)}T00:00"></label>
                    <label>${esc(ui('Wiederholung'))}<select name="frequency">${['once', 'weekly', 'biweekly', 'monthly'].map(v => `<option value="${v}">${esc(frequencyLabel(v))}</option>`).join('')}</select></label>
                    <label>${esc(ui('Dauer in Minuten'))}<input name="duration_minutes" type="number" min="1" max="1440" placeholder="${esc(ui('Optional'))}"></label>
                    <label>${esc(ui('Letzter Tag der Serie'))}<input name="until" type="date" disabled><small>${esc(ui('Leer lassen: fortlaufend.'))}</small></label>
                    <p class="sc-wide sc-help">${esc(ui('Die Uhrzeit gilt in {zone}, auch nach der Zeitumstellung. Monatlich am gleichen Kalendertag, in kürzeren Monaten am letzten Tag. Eine nicht existierende Uhrzeit im Frühjahr wird abgelehnt; bei doppelten Herbst-Uhrzeiten gilt die erste.', {zone: timezone}))}</p>
                    <button class="btn btn-primary sc-wide" type="submit">${esc(ui('Termin speichern'))}</button></form>
                <button type="button" class="btn btn-secondary btn-sm" data-materialize>${esc(ui('Serientermine bis zu zwölf Monate im Voraus anlegen'))}</button></details>
            ${series.length ? `<details class="sc-series" data-tool="stop"${open.has('stop') ? ' open' : ''}><summary>${esc(ui('Serien verwalten ({count})', {count: series.length}))}</summary><ul class="sc-agenda">${series.map(s => `<li class="sc-event" data-series-id="${s.id}">
                <div><strong>${esc(s.name)}</strong><small>${esc(frequencyLabel(s.frequency))} · ${esc(s.first_local.slice(11, 16))} · ${esc(s.timezone)}${s.until ? ` · ${esc(ui('bis {date}', {date: dayLabel(s.until, {day: 'numeric', month: 'long', year: 'numeric'})}))}` : ` · ${esc(ui('fortlaufend'))}`}</small></div>
                <button type="button" class="btn btn-secondary btn-sm" data-stop="${s.id}">${esc(ui('Serie beenden'))}</button></li>`).join('')}</ul></details>` : ''}`;
        box.querySelectorAll('[data-option-list]').forEach(list => { addOptionRow(list); addOptionRow(list); });
    }

    async function load() {
        const version = ++state.version;
        pollBox.setAttribute('aria-busy', 'true');
        try {
            const [polls, calendar] = await Promise.all([
                api(`${campaignId}/date-polls?status=open`),
                canManage ? api(`${campaignId}/session-calendar?${new URLSearchParams({scope: 'month', anchor: todayIn(timezone), timezone})}`) : Promise.resolve({series: []}),
            ]);
            if (!root.isConnected || version !== state.version) return;
            state.polls = polls.polls; state.series = calendar.series;
            const box = root.querySelector('[data-manager-tools]'); if (box) box.dataset.ready = '';
            renderPolls();
            if (polls.more) setStatus(ui('Es gibt weitere Abstimmungen; hier werden die neuesten angezeigt.'));
        } catch (error) { if (root.isConnected && version === state.version) setStatus(fail(error), true); }
        finally { if (version === state.version) pollBox.setAttribute('aria-busy', 'false'); }
    }

    function replacePoll(updated) {
        state.polls = state.polls.map(p => (p.id === updated.id ? updated : p));
        pollBox.innerHTML = state.polls.map(pollMarkup).join('');
    }

    async function run(action, button) {
        if (state.busy) return;
        state.busy = true; if (button) button.disabled = true;
        try { await action(); }
        catch (error) { setStatus(fail(error), true); }
        finally { state.busy = false; if (button?.isConnected) button.disabled = false; }
    }

    root.addEventListener('click', event => {
        const button = event.target.closest('button');
        if (!button || !root.contains(button)) return;
        const poll = button.closest('[data-poll]');
        if (button.dataset.vote) {
            run(async () => {
                const result = await api(`${campaignId}/date-polls/${poll.dataset.pollId}/options/${button.dataset.optionId}/vote`, 'PUT', {value: button.dataset.vote});
                replacePoll(result.poll); setStatus(ui('Deine Antwort wurde gespeichert.'));
            }, button);
        } else if (button.dataset.finalize) {
            if (!window.confirm(ui('Diesen Termin für die Session festlegen? Die Abstimmung wird danach geschlossen.'))) return;
            run(async () => {
                const result = await api(`${campaignId}/date-polls/${poll.dataset.pollId}/finalize`, 'POST',
                    {expected_revision: Number(poll.dataset.revision), option_id: Number(button.dataset.finalize)});
                const chosen = result.poll.options.find(o => o.id === result.poll.selected_option_id);
                await onChanged?.(ui('Termin festgelegt: {when}', {when: instantLabel(chosen.starts_at, timezone)}));
                if (root.isConnected) { setStatus(ui('Termin festgelegt: {when}', {when: instantLabel(chosen.starts_at, timezone)})); await load(); }
            }, button);
        } else if (button.hasAttribute('data-cancel-poll')) {
            if (!window.confirm(ui('Diese Abstimmung abbrechen? Bereits abgegebene Antworten gehen für den Termin nicht verloren, die Abstimmung wird aber geschlossen.'))) return;
            run(async () => { await api(`${campaignId}/date-polls/${poll.dataset.pollId}/cancel`, 'POST', {expected_revision: Number(poll.dataset.revision)}); setStatus(ui('Abstimmung abgebrochen.')); await load(); }, button);
        } else if (button.hasAttribute('data-add-option')) {
            const list = root.querySelector('[data-option-list]');
            if (list.children.length < 20) addOptionRow(list);
        } else if (button.hasAttribute('data-remove-option')) {
            const list = button.closest('[data-option-list]');
            if (list.children.length > 1) button.closest('.sc-option-row').remove();
        } else if (button.dataset.stop) {
            if (!window.confirm(ui('Serie beenden und alle noch nicht gestarteten zukünftigen Termine absagen? Gespielte Sessions bleiben erhalten.'))) return;
            run(async () => { await api(`${campaignId}/session-series/${Number(button.dataset.stop)}/stop`, 'POST', {}); await onChanged?.(ui('Serie beendet.')); await load(); }, button);
        } else if (button.hasAttribute('data-materialize')) {
            run(async () => {
                const result = await api(`${campaignId}/session-series/materialize`, 'POST', {});
                await onChanged?.(ui('{count} neue Termine angelegt.', {count: result.created}));
            }, button);
        }
    });

    root.addEventListener('change', event => {
        const form = event.target.closest('[data-series-form]');
        if (!form) return;
        const until = form.elements.until;
        until.disabled = form.elements.frequency.value === 'once';
        if (until.disabled) until.value = '';
        until.min = form.elements.first_local.value.slice(0, 10);
        form.querySelector('[type="submit"]').textContent = form.elements.frequency.value === 'once' ? ui('Termin speichern') : ui('Serie speichern');
    });

    root.addEventListener('submit', event => {
        event.preventDefault();
        const form = event.target;
        if (form.matches('[data-poll-form]')) {
            const options = [...form.querySelectorAll('.sc-option-row')].map(row => ({local: row.querySelector('[data-option-local]').value,
                duration_minutes: row.querySelector('[data-option-duration]').value ? Number(row.querySelector('[data-option-duration]').value) : null})).filter(o => o.local);
            const payload = {session_id: Number(form.elements.session_id.value), title: form.elements.title.value.trim(), timezone, options};
            const digest = JSON.stringify(payload);
            if (state.digest !== null && digest !== state.digest) state.requestKey = crypto.randomUUID();
            state.digest = digest;
            run(async () => {
                await api(`${campaignId}/date-polls`, 'POST', {...payload, request_key: state.requestKey});
                state.requestKey = crypto.randomUUID(); state.digest = null;
                setStatus(ui('Abstimmung gestartet. Die Mitglieder sehen sie im Kalender unter „Deine Antwort fehlt“.'));
                await load();
            }, form.querySelector('[type="submit"]'));
        } else if (form.matches('[data-new-session-form]')) {
            run(async () => {
                await api(`${campaignId}/sessions`, 'POST', {name: form.elements.name.value.trim()});
                await onChanged?.(ui('Session angelegt. Jetzt kann eine Terminabstimmung dafür erstellt werden.'));
            }, form.querySelector('[type="submit"]'));
        } else if (form.matches('[data-series-form]')) {
            const frequency = form.elements.frequency.value;
            const payload = {name: form.elements.name.value.trim(), first_local: form.elements.first_local.value, frequency, timezone,
                until: form.elements.until.disabled ? null : form.elements.until.value || null,
                duration_minutes: form.elements.duration_minutes.value ? Number(form.elements.duration_minutes.value) : null};
            const digest = JSON.stringify(payload);
            if (state.seriesDigest !== null && digest !== state.seriesDigest) state.seriesKey = crypto.randomUUID();
            state.seriesDigest = digest;
            form.setAttribute('aria-busy', 'true');
            run(async () => {
                await api(`${campaignId}/session-series`, 'POST', {...payload, request_key: state.seriesKey});
                await onChanged?.(frequency === 'once' ? ui('Termin gespeichert.') : ui('Serie gespeichert. Kommende Termine wurden angelegt.'));
            }, form.querySelector('[type="submit"]')).finally(() => form.setAttribute('aria-busy', 'false'));
        }
    });

    await load();
}
