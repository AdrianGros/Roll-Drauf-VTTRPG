globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
(function () {
    'use strict';
    const ui=(source,parameters={})=>window.VTTI18n?.module().literal(source,parameters) ?? globalThis.VTTUi(source,parameters);

    const API = '/api/srd-creator';
    const COMP = '/api/rulesets/srd-5.2.1-de/compendium';
    const ABIL = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
    const labels=(sources)=>Object.defineProperties({},Object.fromEntries(Object.entries(sources).map(([key,source])=>[key,{enumerable:true,get:()=>ui(source)}])));
    const STEPS = [
        ['klasse', "Klasse"], ['herkunft', "Herkunft"], ['attribute', "Attribute"], ['wahlen', "Merkmale und Talente"],
        ['ausruestung', "Ausrüstung"], ['zauber', "Zauber"], ['beschreibung', "Beschreibung"], ['pruefung', "Prüfung"],
    ].map(([id,source])=>Object.defineProperty([id],1,{enumerable:true,get:()=>ui(source)}));
    const SEV_LABEL = labels({error:"Fehler",incomplete:"Offen",warning:"Hinweis",info:"Info"});

    const SC = window.SrdCreator = { API, COMP, ABIL, STEPS, SEV_LABEL, labels, steps: {}, L: {} };
    const app = SC.app = {
        data: null, draft: null, evaluation: null, blockers: [], mode: 'guided', step: 'klasse',
        dirty: false, saving: false, conflict: null, saveTimer: null, extras: { subclasses: null }, campaigns: null,
    };

    // Presentation-only rebuilds retain pending onchange edits until the user really leaves the field.
    const pendingChanges=new WeakSet();
    // ---------------------------------------------------------------- helpers
    function h(tag, attrs, ...kids) {
        const n = document.createElement(tag);
        if (attrs) {
            for (const [k, v] of Object.entries(attrs)) {
                if (v === null || v === undefined) continue;
                if (k === 'class') n.className = v;
                else if (k === 'text') { if(v?.nodeType)n.append(v);else n.textContent=v; }
                else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
                else if (k.startsWith('aria-') || k.startsWith('data-')) n.setAttribute(k, String(v));
                else if (v === false) continue;
                else if (k in n) n[k] = v;
                else n.setAttribute(k, v === true ? '' : v);
            }
        }
        if(attrs?.onchange && !attrs.oninput && ['input','textarea'].includes(tag)){
            n.addEventListener('input',()=>pendingChanges.add(n));
            n.addEventListener('change',()=>pendingChanges.delete(n),true);
            n.addEventListener('blur',()=>{
                if(n.isConnected && pendingChanges.has(n))n.dispatchEvent(new Event('change',{bubbles:true}));
            });
        }
        for (const kid of kids.flat(Infinity)) {
            if (kid === null || kid === undefined || kid === false) continue;
            n.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
        }
        return n;
    }
    const $ = (id) => document.getElementById(id);
    const clone = (v) => JSON.parse(JSON.stringify(v));
    const fmtMeters = (v) => `${String(v).replace('.', ',')} m`;
    const sign = (n) => (n >= 0 ? `+${n}` : `−${Math.abs(n)}`);
    Object.assign(SC, { h, $, clone, fmtMeters, sign });

    function randInt(n) {
        const buf = new Uint32Array(1);
        window.crypto.getRandomValues(buf);
        return buf[0] % n;
    }
    SC.randInt = randInt;
    SC.pick = (list) => list[randInt(list.length)];
    SC.shuffle = (list) => {
        const a = list.slice();
        for (let i = a.length - 1; i > 0; i--) { const j = randInt(i + 1); [a[i], a[j]] = [a[j], a[i]]; }
        return a;
    };

    async function api(path, method = 'GET', body = null, retry = true) {
        const options = { method, credentials: 'include', headers: window.Auth.buildHeaders(method, body !== null) };
        if (body !== null) options.body = JSON.stringify(body);
        let response;
        try { response = await fetch(API + path, options); } catch (error) { return { ok: false, status: 0, data: {} }; }
        if (response.status === 401 && retry) {
            if (await window.Auth.refreshAccessToken()) return api(path, method, body, false);
            window.location.href = '/login.html';
            return { ok: false, status: 401, data: {} };
        }
        const data = await response.json().catch(() => ({}));
        return { ok: response.ok, status: response.status, data, canonicalHash:response.headers.get('X-Creator-Data-SHA256') };
    }
    SC.api = api;

    function setStatus(text) {
        app.statusSource=null;
        const n = $('scStatus');
        n.textContent = text || '';
        n.hidden = !text;
    }

    function setStatusSource(source) { setStatus(ui(source));app.statusSource=source; }

    // ---------------------------------------------------------------- lookups
    function buildLookups(data) {
        const L = SC.L;
        L.classes = Object.fromEntries(data.classes.map((c) => [c.classKey, c]));
        L.species = Object.fromEntries(data.species.map((s) => [s.id, s]));
        L.backgrounds = Object.fromEntries(data.backgrounds.map((b) => [b.id, b]));
        L.feats = Object.fromEntries(data.feats.map((f) => [f.id, f]));
        L.skills = Object.fromEntries(data.skills.map((s) => [s.id, s]));
        L.abilities = Object.fromEntries(data.abilities.map((a) => [a.id, a]));
        L.classOptions = Object.fromEntries(data.classOptions.map((o) => [o.id, o]));
        L.alignments = data.alignments;
        L.weapons = Object.fromEntries(data.equipment.weapons.map((w) => [w.id, w]));
        L.armor = Object.fromEntries(data.equipment.armor.map((a) => [a.id, a]));
        L.items = {};
        [data.equipment.items, data.equipment.weapons, data.equipment.armor].forEach((list) => list.forEach((i) => { L.items[i.id] = i.name; }));
        L.langs = Object.fromEntries(data.languages.map((l) => [l.id, l]));
        SC.buildDisplayIndex?.(data);
    }
    SC.itemName = (id) => SC.L.items[id] || String(id).split('.').pop().replace(/-/g, ' ');
    SC.skillName = (id) => (SC.L.skills[id] ? SC.L.skills[id].name : id);
    SC.abilityName = (id) => (SC.L.abilities[id] ? SC.L.abilities[id].name : id);
    SC.abilityAbbr = (id) => (SC.L.abilities[id] ? SC.L.abilities[id].abbreviation : id);
    SC.subclassName = (id) => (app.extras.subclasses && app.extras.subclasses[id] ? app.extras.subclasses[id].name : String(id).split('subclass-').pop().replace(/-/g, ' '));
    SC.spellName = (id) => (app.data.spells[id] ? app.data.spells[id].name : id);

    async function loadExtras() {
        if (app.extras.subclasses) return;
        app.extras.subclasses = {};
        try {
            const response = await fetch(`${COMP}?type=subclass&limit=200`, { credentials: 'same-origin' });
            if (response.ok) (await response.json()).items.forEach((e) => { app.extras.subclasses[e.id] = e; });
        } catch (error) { /* names fall back to ids */ }
    }

    SC.refreshOrigins = async function () {
        const result = await api('/origin-catalog');
        if (!result.ok) { setStatusSource('Die eigenen Hintergründe konnten nicht aktualisiert werden.'); return; }
        // Retain selected old immutable revisions; the server still validates their access.
        const state = app.draft.state;
        const chosen = new Set([state.background?.id, ...Object.values(state.species?.choices || {}),
            ...(state.advancements || []).map(a => a.featId),
            ...Object.values(state.featureChoices || {}).flatMap(choices => Object.values(choices))]);
        const background = app.data.backgrounds.find(b => b.id === state.background?.id);
        if (background?.featId) chosen.add(background.featId);
        for (const key of ['backgrounds','feats']) {
            const rows = new Map(app.data[key].filter(e => !e.homebrew || chosen.has(e.id)).map(e => [e.id,e]));
            (result.data[key] || []).forEach(e => rows.set(e.id,e));
            app.data[key] = [...rows.values()];
        }
        buildLookups(app.data); renderAll();
    };

    // ---------------------------------------------------------------- detail dialog
    function renderBlock(block) {
        const t = block.type;
        if (t === 'heading') return h(`h${Math.min((block.level || 2) + 1, 6)}`, { text: block.text });
        if (t === 'paragraph') return h('p', { text: block.text });
        if (t === 'ordered-list' || t === 'unordered-list') return h(t === 'ordered-list' ? 'ol' : 'ul', null, (block.items || []).map((i) => h('li', { text: i })));
        if (t === 'definition-list') return h('dl', { class: 'sc-class-facts' }, (block.entries || []).map((e) => [h('dt', { text: e.term }), h('dd', { text: e.definition })]));
        if (t === 'table') {
            return h('div', { class: 'sc-scroll' }, h('table', { class: 'sc-table' },
                block.caption ? h('caption', { text: block.caption }) : null,
                h('thead', null, h('tr', null, (block.columns || []).map((c) => h('th', { scope: 'col', text: c })))),
                h('tbody', null, (block.rows || []).map((r) => h('tr', null, r.map((c) => h('td', { text: c })))))));
        }
        if (t === 'rule-callout' || t === 'page-note' || t === 'original-note') return h('aside', { class: 'sc-detail' }, block.title ? h('strong', { text: block.title }) : null, h('p', { text: block.text }));
        if (t === 'stat-block') return h('section', { class: 'sc-detail' }, h('h3', { text: block.name }), h('dl', { class: 'sc-class-facts' }, (block.entries || []).map((e) => [h('dt', { text: e.label }), h('dd', { text: e.value })])));
        return h('p', { text: '' });
    }
    SC.openEntry = async function (id, fallbackTitle) {
        const dialog = $('scDialog');
        const serial=app.dialogSeq=(app.dialogSeq || 0)+1,localeSeq=app.localeSeq;
        app.dialogEntry={id,fallbackTitle};
        const current=()=>dialog.open && serial===app.dialogSeq && localeSeq===app.localeSeq;
        $('scDialogTitle').removeAttribute('lang');
        $('scDialogTitle').textContent = fallbackTitle || ui("Regeltext");
        const body = $('scDialogBody');
        body.removeAttribute('lang');
        body.textContent = ui("Wird geladen …");
        if (!dialog.open) dialog.showModal();
        const own = [...app.data.backgrounds,...app.data.feats].find(entry=>entry.id===id && entry.homebrew);
        if (own) {
            body.replaceChildren(h('p',{class:'sc-muted',text:ui("Homebrew · Fassung {p0} · {p1}",{p0:(own.origin.revision),p1:(own.origin.author || '')})}),
                h('p',{text:own.description || ''}));
            if (own.mechanics) own.mechanics.forEach(grant=>body.append(h('p',{text:grant.kind==='skill_proficiency' ? ui("Übung: {p0}",{p0:(SC.skillName(grant.skill))}) : `${({initiative_pb:ui('Initiative'),initiative:ui('Initiative'),ac:ui('Rüstungsklasse'),speed_meters:ui('Bewegung (m)'),hp_per_level:ui('Trefferpunkte je Stufe')})[grant.kind] || ui('Regelbeitrag')}: +${grant.kind==='initiative_pb'?ui('Übungsbonus'):grant.value}`})));
            $('scDialogTitle').focus();return;
        }
        let source=SC.entrySource(id);
        const read=async target=>{
            const response=await fetch(`/api/rulesets/srd-5.2.1-${target.locale}/compendium/entry/${encodeURIComponent(target.id)}`,{credentials:'same-origin'});
            if(!response.ok)throw new Error('missing');return response.json();
        };
        try {
            let data;
            try { data=await read(source); } catch(error){
                if(!current())return;
                if(source.locale==='de')throw error;
                source={id,locale:'de',fallback:true};data=await read(source);
            }
            if(!current())return;
            $('scDialogTitle').textContent = data.entity.name;
            $('scDialogTitle').lang=source.locale;
            body.textContent = '';
            body.append(h('p', { class: 'sc-muted' }, ui("SRD 5.2.1 · "), h('a', { href: data.entity.url, target: '_blank', rel: 'noopener' }, ui("Im Regelwerk lesen"))));
            if(source.fallback)body.append(h('p',{class:'sc-muted',text:ui('Dieser Regeltext ist derzeit nur auf Deutsch verfügbar.')}));
            if(source.differences)body.append(h('p',{class:'sc-muted sc-source-difference',text:ui('Die Sprachfassungen unterscheiden sich bei den Komponenten. Für diesen Charakter bleibt die deutsche Regelfassung maßgeblich.')}));
            data.blocks.forEach((b)=>{const node=renderBlock(b);node.lang=source.locale;body.append(node);});
        } catch (error) {
            if(!current())return;
            body.textContent = ui("Der Regeltext konnte nicht geladen werden.");
        }
        if(current())$('scDialogTitle').focus();
    };
    SC.refreshOpenEntry=()=>{if($('scDialog').open && app.dialogEntry)SC.openEntry(app.dialogEntry.id,SC.ruleName(app.dialogEntry.id,app.dialogEntry.fallbackTitle));};
    SC.detailButton = (id, label, name) => h('button', { type: 'button', class: 'sc-btn sc-btn-small', onclick: () => SC.openEntry(id, name) }, label || ui("Regeltext"));

    // ---------------------------------------------------------------- state & saving
    // Callers pass only authored lifecycle literals; they are the catalog sources.
    function setSaveText(text) { app.saveText=text;$('scSave').textContent = ui(text); }

    function applyView(view) {
        app.draft.version = view.draft.version;
        app.draft.name = view.draft.name;
        app.evaluation = view.evaluation;
        app.blockers = view.blockers || [];
    }

    SC.mutate = function (fn, opts = {}) {
        fn(app.draft.state);
        app.dirty = true;
        setSaveText('Ungespeichert …');
        scheduleSave();
        if (opts.render === 'none') renderChrome(); else renderAll();
    };
    SC.touchSave = function () { app.dirty = true; scheduleSave(); };

    function scheduleSave(delay = 400) {
        clearTimeout(app.saveTimer);
        app.saveTimer = setTimeout(runSave, delay);
    }

    async function runSave() {
        if (!app.draft || app.conflict) return;
        if (app.saving) { scheduleSave(300); return; }
        if (!app.dirty) return;
        app.saving = true;
        app.dirty = false;
        setSaveText('Speichert …');
        const res = await api(`/drafts/${app.draft.id}`, 'PUT', { version: app.draft.version, state: app.draft.state, step: app.step });
        app.saving = false;
        if (res.ok) {
            applyView(res.data);
            setSaveText(app.dirty ? 'Ungespeichert …' : 'Gespeichert');
            const a = document.activeElement;
            const typing = a && (a.tagName === 'TEXTAREA' || (a.tagName === 'INPUT' && ['text', 'search', 'number'].includes(a.type)));
            if (!app.dirty && !typing && !app.finalizing && app.draft.status === 'draft') renderAll(); else renderChrome();
            if (SC.onSaved) SC.onSaved();
        } else if (res.status === 409 && res.data.error === 'version_conflict') {
            app.dirty = true;
            showConflict(res.data);
            return;
        } else if (res.status === 422 && res.data.error === 'invalid_state') {
            setSaveText('Eine Eingabe wurde vom Server abgelehnt.');
            app.lastProblems = res.data.problems || [];
            showProblems(app.lastProblems);
            return;
        } else {
            app.dirty = true;
            setSaveText('Speichern fehlgeschlagen – neuer Versuch …');
            scheduleSave(5000);
            return;
        }
        if (app.dirty) scheduleSave(100);
    }

    function showProblems(problems) {
        const box = $('scConflict');
        box.hidden = false;
        box.textContent = '';
        box.append(h('strong', { text: ui("Eine Eingabe ist ungültig und wurde nicht gespeichert: ") }),
            (problems || []).slice(0, 3).map((p) => h('div', { text: `${p.path || ''} ${p.message || ''}` })));
    }

    function showConflict(data) {
        app.conflict = data;
        const box = $('scConflict');
        box.hidden = false;
        box.textContent = '';
        box.append(
            h('p', { text: ui("Dieser Entwurf wurde zwischenzeitlich anderswo geändert (zweiter Tab oder anderes Gerät).") }),
            h('div', { class: 'sc-row' },
                h('button', { type: 'button', class: 'sc-btn', onclick: () => resolveConflict('server') }, ui("Neueste Version laden (meine ungespeicherten Änderungen verwerfen)")),
                h('button', { type: 'button', class: 'sc-btn', onclick: () => resolveConflict('mine') }, ui("Meine Version behalten (überschreibt die andere)"))));
        setSaveText('Konflikt');
    }

    function resolveConflict(choice) {
        const data = app.conflict;
        app.conflict = null;
        $('scConflict').hidden = true;
        if (choice === 'server') {
            app.draft = { ...data.draft };
            app.evaluation = data.evaluation;
            app.blockers = data.blockers || [];
            app.dirty = false;
            setSaveText('Neueste Version geladen');
            renderAll();
        } else {
            app.draft.version = data.draft.version;
            app.dirty = true;
            scheduleSave(0);
        }
    }

    // ---------------------------------------------------------------- findings
    function stepOf(path) {
        const p = String(path || '');
        if (/^(levels|multiclass)/.test(p)) return 'klasse';
        if (/^(species|background)/.test(p)) return 'herkunft';
        if (/^abilit/.test(p)) return 'attribute';
        if (/^(skills|subclasses|featureChoices|advancements)/.test(p)) return 'wahlen';
        if (/^equipment/.test(p)) return 'ausruestung';
        if (/^spells/.test(p)) return 'zauber';
        if (/^identity/.test(p)) return 'beschreibung';
        return 'pruefung';
    }
    SC.allFindings = function () {
        const list = (app.evaluation ? app.evaluation.findings : []).slice();
        app.blockers.forEach((b) => { if (b.code === 'name-missing') list.push(b); });
        return list;
    };
    SC.findingsFor = (stepId) => SC.allFindings().filter((f) => stepOf(f.path) === stepId);

    // Known finding paths that have a dedicated control. The path is only ever compared with
    // the data-focus-path of controls the steps render; it never becomes a selector or code.
    const FOCUS_PATHS = [
        /^advancements\[\d+\]$/,
        /^featureChoices\.[a-z0-9-]+(\.[a-z0-9-]+)?$/,
        /^skills\.multiclass\.[a-z0-9-]+$/,
        /^levels\.[a-z0-9-]+$/,
    ];
    const FOCUSABLE = 'select, input, button, a[href], textarea';
    const knownFocusPath = (path) => typeof path === 'string' && FOCUS_PATHS.some((re) => re.test(path));

    function focusPath(path) {
        if (!knownFocusPath(path)) return false;
        let target = null;
        const level = /^levels\.([a-z0-9-]+)$/.exec(path);
        if (level) {
            const levels = (app.draft && app.draft.state.levels) || [];
            const index = levels.findIndex((l, i) => i > 0 && l.classKey === level[1]);
            target = index > 0 ? $(`scLvlClass${index}`) : null;
        } else {
            target = Array.from(document.querySelectorAll('[data-focus-path]')).find((node) => node.getAttribute('data-focus-path') === path) || null;
        }
        if (!target) return false;
        const inner = target.matches(FOCUSABLE) ? target : (target.querySelector('select') || target.querySelector(FOCUSABLE));
        const node = inner || target;
        if (!inner) node.tabIndex = -1;
        node.focus({ preventScroll: true });
        node.scrollIntoView({ block: 'center' });
        return true;
    }

    // Open the step that owns the finding, then focus the exact control when we know it.
    // An unknown field still lands on the step's content; nothing is written or evaluated here.
    SC.correctFinding = function (finding) {
        const step = stepOf(finding && finding.path);
        if (app.mode === 'guided') goStep(step); else scrollToSection(step);
        return focusPath(finding && finding.path);
    };

    SC.findingList = function (findings) {
        if (!findings.length) return h('p', { class: 'sc-ok-note', text: ui("Hier ist alles in Ordnung.") });
        const order = { error: 0, incomplete: 1, warning: 2, info: 3 };
        return h('ul', { class: 'sc-findings' }, findings.slice().sort((a, b) => order[a.severity] - order[b.severity]).map((f) => {
            const step = stepOf(f.path);
            const stepLabel = (STEPS.find(([id]) => id === step) || [])[1];
            const fixable = f.severity !== 'info' && (step !== 'pruefung' || knownFocusPath(f.path));
            return h('li', { class: 'sc-finding', 'data-sev': f.severity },
                h('span', { class: 'sc-sev', text: SEV_LABEL[f.severity] || f.severity }), f.message,
                f.ref && f.ref.quote ? h('blockquote', null, `Regel: „${f.ref.quote}“`) : null,
                fixable ? h('button', { type: 'button', class: 'sc-btn sc-btn-small sc-finding-fix', 'data-finding-fix': step,
                    onclick: () => SC.correctFinding(f) }, ui("Zur Korrektur: {step}", { step: stepLabel || step })) : null);
        }));
    };

    function renderFindings() {
        document.querySelectorAll('[data-findings-for]').forEach((box) => {
            box.textContent = '';
            const stepId = box.getAttribute('data-findings-for');
            box.append(h('h3', { text: ui("Prüfung") }), SC.findingList(SC.findingsFor(stepId)));
        });
    }

    // ---------------------------------------------------------------- rendering
    function stepsToShow() { return STEPS; }

    function renderStepsNav() {
        const nav = $('scSteps');
        nav.textContent = '';
        stepsToShow().forEach(([id, label]) => {
            const findings = SC.findingsFor(id);
            const errors = findings.filter((f) => f.severity === 'error').length;
            const open = findings.filter((f) => f.severity === 'incomplete').length;
            const badge = errors ? h('span', { class: 'sc-count sc-count-error', text: errors, 'aria-label': ui("{p0} Fehler",{p0:(errors)}) })
                : open ? h('span', { class: 'sc-count', text: open, 'aria-label': `${open} offen` })
                    : (app.evaluation ? h('span', { class: 'sc-count sc-count-ok', text: '✓', 'aria-label': ui("in Ordnung") }) : null);
            nav.append(h('button', {
                type: 'button', class: 'sc-step', 'aria-current': app.mode === 'guided' && app.step === id ? 'step' : null,
                onclick: () => (app.mode === 'guided' ? goStep(id) : scrollToSection(id)),
            }, label, badge));
        });
    }

    function scrollToSection(id) {
        const section = document.getElementById(`scSec-${id}`);
        if (section) { section.scrollIntoView({ behavior: 'smooth', block: 'start' }); section.querySelector('h2').focus(); }
    }

    function renderSummary() {
        const box = $('scSummary');
        const ev = app.evaluation;
        box.textContent = '';
        box.append(h('h2', { text: (app.draft.state.identity && app.draft.state.identity.name) || ui("Unbenannter Charakter") }));
        if (!ev) { box.append(h('p', { class: 'sc-muted', text: ui("Wird berechnet …") })); return; }
        const classLine = ev.classes.length ? ev.classes.map((c) => `${SC.className(c.classKey)} ${c.level}${c.subclass ? ` (${SC.subclassName(c.subclass)})` : ''}`).join(' / ') : ui("Noch keine Klasse");
        const state = app.draft.state;
        const species = state.species && SC.L.species[state.species.id];
        const background = state.background && SC.L.backgrounds[state.background.id];
        box.append(h('p', { class: 'sc-muted', text: [classLine, species && SC.ruleName(species), background && SC.ruleName(background)].filter(Boolean).join(' · ') }));
        const more = h('div', { class: 'sc-summary-more' });
        box.append(h('button', { type: 'button', class: 'sc-btn sc-btn-small sc-summary-toggle', 'aria-expanded': app.summaryOpen ? 'true' : 'false', onclick: () => { app.summaryOpen = !app.summaryOpen; renderSummary(); } }, app.summaryOpen ? ui("Werte ausblenden") : ui("Werte anzeigen")), more);
        box.dataset.collapsed = app.summaryOpen ? 'false' : 'true';
        more.append(h('div', { class: 'sc-abilities' }, ABIL.map((a) => h('div', { class: 'sc-ability' },
            h('span', { text: SC.abilityAbbr(a) }), h('b', { text: ev.abilities[a].score }), h('span', { text: sign(ev.abilities[a].modifier) })))));
        const rows = [
            [ui("Stufe"), ev.level], [ui("Trefferpunkte"), ev.hitPoints.max], [ui("Rüstungsklasse"), ev.armorClass.value],
            [ui("Initiative"), sign(ev.initiative)], [ui("Bewegung"), fmtMeters(ev.speedMeters)], [ui("Übungsbonus"), sign(ev.proficiencyBonus)],
            [ui("Passive Wahrnehmung"), ev.passivePerception],
        ];
        const casting = Object.values(ev.spellcasting.classes)[0];
        if (casting) rows.push([ui("Zauber-SG"), casting.saveDc], [ui("Zauberangriff"), sign(casting.attackBonus)]);
        more.append(h('dl', null, rows.map(([k, v]) => [h('dt', { text: k }), h('dd', { text: v })])));
        const all = SC.allFindings();
        const count = (s) => all.filter((f) => f.severity === s).length;
        box.append(h('p', null,
            count('error') ? h('span', { class: 'sc-tag', text: ui("{p0} Fehler",{p0:(count('error'))}) }) : null,
            count('incomplete') ? h('span', { class: 'sc-tag', text: ui("{p0} offen", { p0: count('incomplete') }) }) : null,
            count('warning') ? h('span', { class: 'sc-tag', text: ui("{p0} Hinweise",{p0:(count('warning'))}) }) : null,
            !count('error') && !count('incomplete') ? h('span', { class: 'sc-ok-note', text: ui("Bereit zum Erstellen") }) : null));
    }

    function renderNav() {
        const index = STEPS.findIndex(([id]) => id === app.step);
        $('scPrev').disabled = index <= 0;
        $('scNext').hidden = index >= STEPS.length - 1;
        $('scNav').hidden = app.mode !== 'guided';
        $('scModeGuided').setAttribute('aria-pressed', String(app.mode === 'guided'));
        $('scModeQuick').setAttribute('aria-pressed', String(app.mode === 'quick'));
        $('scBuilder').classList.toggle('sc-quick', app.mode === 'quick');
    }

    function renderChrome(preserveView = true) {
        const body = $('scStepBody'), view = preserveView ? captureBuilderView(body) : null;
        renderStepsNav();
        renderSummary();
        renderNav();
        renderFindings();
        if (view) restoreBuilderView(body, view);
    }

    function renderBody() {
        const body = $('scStepBody');
        const ids = app.mode === 'guided' ? [app.step] : STEPS.map(([id]) => id);
        body.textContent = '';
        ids.forEach((id) => {
            const def = SC.steps[id];
            const label = STEPS.find(([sid]) => sid === id)[1];
            const section = h('section', { id: `scSec-${id}`, class: 'sc-section', 'aria-labelledby': `scH-${id}` },
                h('h2', { id: `scH-${id}`, tabindex: '-1', text: label }),
                def.render(),
                h('div', { class: 'sc-panel', 'data-findings-for': id }));
            body.append(section);
        });
    }

    // Rebuilds must preserve the reader's working context, including nested book
    // scrollers and open detail groups. A numeric focus index changes when options
    // are inserted and can move focus to an unrelated control.
    function detailKey(detail) {
        const section = detail.closest('.sc-section');
        const summary = detail.querySelector(':scope > summary');
        return `${section?.id || ''}:${summary?.textContent || ''}`;
    }

    function controlKey(node) {
        if (!node) return null;
        const section = node.closest('.sc-section')?.id || '';
        const group = node.closest('[role="group"]')?.getAttribute('aria-label') || '';
        const label = node.dataset.focusKey || node.getAttribute('name') ||
            Array.from(node.labels || []).map(item => item.textContent.trim()).join('|') ||
            node.getAttribute('aria-label') || (node.tagName === 'BUTTON' ? node.textContent.trim() : '');
        return label ? `${section}:${group}:${node.tagName}:${node.type || ''}:${label}` : null;
    }

    function keyedControl(root, key) {
        if (!key) return null;
        const matches = Array.from(root.querySelectorAll('input,select,textarea,button'))
            .filter(node => controlKey(node) === key);
        return matches.length === 1 ? matches[0] : null;
    }

    function captureBuilderView(root) {
        const active = root.contains(document.activeElement) ? document.activeElement : null;
        const path = active?.closest('[data-focus-path]')?.getAttribute('data-focus-path');
        const marker = active?.id ? active : Array.from(root.querySelectorAll('[id]')).find(node => {
            const box = node.getBoundingClientRect();
            return box.top >= 0 && box.top < innerHeight && box.height > 0;
        });
        const scrollers = [];
        for (let node = active || root; node; node = node.parentElement) {
            if (node.scrollHeight > node.clientHeight || node.scrollWidth > node.clientWidth) {
                scrollers.push({node, top: node.scrollTop, left: node.scrollLeft});
            }
        }
        return {id: active?.id, key: controlKey(active), path, tag: active?.tagName, type: active?.type,
            start: active?.selectionStart, end: active?.selectionEnd,
            details: new Map(Array.from(root.querySelectorAll('details')).map(node => [detailKey(node), node.open])),
            scrollers, x: window.scrollX, y: window.scrollY,
            markerId: marker?.id, markerKey: controlKey(active),
            markerTop: (active || marker)?.getBoundingClientRect().top};
    }

    function localeControlKey(node,index,root){
        if(node.id)return 'id:'+node.id;
        const section=node.closest('.sc-section') || root,group=node.closest('[role="group"]');
        const groupIndex=group?Array.from(section.querySelectorAll('[role="group"]')).indexOf(group):-1;
        return node.dataset.focusKey?`${section.id}:${groupIndex}:${node.tagName}:${node.dataset.focusKey}`:`position:${index}:${node.tagName}:${node.type}`;
    }

    function restoreBuilderView(root, view) {
        root.querySelectorAll('details').forEach(node => {
            if (view.details.has(detailKey(node))) node.open = view.details.get(detailKey(node));
        });
        let localeActive=null;
        if(view.localeControls){
            const controls=Array.from(root.querySelectorAll('input,select,textarea,button,a[href]'));
            const byKey=new Map(controls.map((node,index)=>[localeControlKey(node,index,root),node]));
            view.localeControls.forEach((saved)=>{
                const node=byKey.get(saved.key);
                if(!node || node.tagName!==saved.tag || node.type!==saved.type)return;
                if(['INPUT','SELECT','TEXTAREA'].includes(saved.tag) && node.type!=='file')node.value=saved.value;
                if(['checkbox','radio'].includes(node.type))node.checked=saved.checked;
                if(saved.pending)pendingChanges.add(node);
            });
            Array.from(root.querySelectorAll('details')).filter(node=>!node.closest('.srd-rule-preview')).forEach((node,index)=>{if(index<view.localeDetails.length)node.open=view.localeDetails[index];});
            localeActive=byKey.get(view.localeActive);
        }
        let active = view.id ? document.getElementById(view.id) : (localeActive || keyedControl(root, view.key));
        if (!active && view.path) {
            const owner = Array.from(root.querySelectorAll('[data-focus-path]')).find(node => node.getAttribute('data-focus-path') === view.path);
            const controls = owner?.querySelectorAll('input,select,textarea,button');
            active = owner?.matches('input,select,textarea,button') ? owner : controls?.length === 1 ? controls[0] : null;
        }
        if (active && root.contains(active) && active.tagName === view.tag && !active.disabled) {
            active.focus({preventScroll: true});
            if (typeof view.start === 'number' && typeof active.setSelectionRange === 'function') {
                try { active.setSelectionRange(view.start, view.end); } catch (_) { /* non-text input */ }
            }
        }
        for (const row of view.scrollers) if (row.node.isConnected) {
            row.node.scrollTop = row.top; row.node.scrollLeft = row.left;
        }
        window.scrollTo(view.x, view.y);
        const marker = view.markerKey ? keyedControl(root, view.markerKey)
            : view.markerId ? document.getElementById(view.markerId) : null;
        if (marker && Number.isFinite(view.markerTop)) {
            const delta = marker.getBoundingClientRect().top - view.markerTop;
            if (Math.abs(delta) > 1) {
                const nested = view.scrollers.find(row => row.node.isConnected && row.node !== document.documentElement && row.node !== document.body);
                if (nested) nested.node.scrollTop += delta;
                else window.scrollBy(0, delta);
            }
        }
    }

    function renderAll(localeOnly = false) {
        const body = $('scStepBody'), view = captureBuilderView(body);
        const active=localeOnly && body.contains(document.activeElement)?document.activeElement:null;
        // Replacing a focused onchange field can make the browser commit it on blur.
        // A presentation-only rebuild must preserve that pending value without invoking its mutation handler.
        const suppressLocaleCommit=event=>event.stopImmediatePropagation();
        if(active)active.addEventListener('change',suppressLocaleCommit,true);
        try {
            if(localeOnly){
                const controls=Array.from(body.querySelectorAll('input,select,textarea,button,a[href]'));
                view.localeControls=controls.map((node,index)=>({key:localeControlKey(node,index,body),tag:node.tagName,type:node.type,value:node.value,checked:node.checked,pending:pendingChanges.has(node)}));
                view.localeActive=active?localeControlKey(active,controls.indexOf(active),body):null;
                view.localeDetails=Array.from(body.querySelectorAll('details')).filter(node=>!node.closest('.srd-rule-preview')).map(node=>node.open);
            }
            renderBody();
            renderChrome(false);
            restoreBuilderView(body, view);
        } finally {
            if(active)active.removeEventListener('change',suppressLocaleCommit,true);
        }
    }

    SC.renderAll = renderAll;
    SC.renderChrome = renderChrome;

    function goStep(id) {
        app.step = id;
        syncUrl();
        app.dirty = true;
        scheduleSave(800);
        renderAll();
        const heading = $(`scH-${id}`);
        if (heading) { window.scrollTo(0, 0); heading.focus({ preventScroll: true }); }
    }

    function syncUrl() {
        const params = new URLSearchParams();
        if (app.draft) params.set('draft', app.draft.id);
        if (app.mode === 'quick') params.set('modus', 'schnell');
        else if (app.step !== 'klasse') params.set('schritt', app.step);
        history.replaceState(null, '', `${location.pathname}?${params.toString()}`);
        try { localStorage.setItem('srdCreatorMode', app.mode); } catch (error) { /* optional */ }
    }

    // ---------------------------------------------------------------- home / drafts
    function emptyState() {
        return { sources: app.defaultSources, abilityMethod: 'standard-array', levels: [], identity: {} };
    }

    async function createDraft(state, step) {
        const res = await api('/drafts', 'POST', { state, step: step || 'klasse' });
        if (!res.ok) {
            const text = res.data.error === 'draft_limit' ? res.data.message : (res.data.message || 'Der Entwurf konnte nicht angelegt werden.');
            setStatus(text);
            return null;
        }
        return res.data;
    }

    async function openDraft(id, mode, step) {
        setStatusSource("Entwurf wird geladen …");
        const res = await api(`/drafts/${id}`);
        if (!res.ok) {
            setStatusSource("Dieser Entwurf wurde nicht gefunden.");
            showHome();
            return;
        }
        if (res.data.draft.status !== 'draft') {
            setStatusSource("Dieser Entwurf ist bereits abgeschlossen.");
            showHome();
            return;
        }
        app.draft = res.data.draft;
        app.evaluation = res.data.evaluation;
        app.blockers = res.data.blockers || [];
        app.mode = mode || app.mode;
        app.step = STEPS.some(([sid]) => sid === step) ? step : (STEPS.some(([sid]) => sid === app.draft.step) ? app.draft.step : 'klasse');
        app.dirty = false;
        app.conflict = null;
        $('scConflict').hidden = true;
        setStatus('');
        $('scHome').hidden = true;
        $('scBuilder').hidden = false;
        setSaveText('Gespeichert');
        syncUrl();
        renderAll();
        loadExtras().then(() => renderChrome());
    }

    async function startNew(mode, randomLevel) {
        const state = emptyState();
        const view = await createDraft(state, 'klasse');
        if (!view) return;
        app.mode = mode;
        await openDraft(view.draft.id, mode, 'klasse');
        if (randomLevel) {
            await loadExtras();
            SC.randomize(randomLevel);
        }
    }

    async function duplicateDraft(id) {
        const res = await api(`/drafts/${id}`);
        if (!res.ok) return;
        const state = res.data.draft.state;
        state.identity = { ...(state.identity || {}) };
        if (state.identity.name) state.identity.name = `${state.identity.name} (Kopie)`.slice(0, 100);
        const view = await createDraft(state, res.data.draft.step);
        if (view) showHome();
    }

    async function discardDraft(id) {
        if (!window.confirm(ui("Diesen Entwurf wirklich verwerfen?"))) return;
        await api(`/drafts/${id}`, 'DELETE');
        showHome();
    }

    const IMPORT_ERRORS = labels({
        too_large: "Die Datei ist zu groß (höchstens 400 KB).",
        invalid_body: "Die Datei ist keine gültige Charakterdatei.",
        import_invalid: "Die Datei passt nicht zu diesem Regelwerk oder wurde verändert.",
        rate_limited: "Zu viele Importe. Bitte versuche es später erneut.",
    });

    async function importFile(input, message) {
        const file = input.files && input.files[0];
        if (!file) { message.textContent = ui("Bitte wähle zuerst eine Datei."); message.className = 'sc-muted sc-import-error'; return; }
        message.className = 'sc-muted';
        if (file.size > 400000) { message.textContent = IMPORT_ERRORS.too_large; message.className = 'sc-muted sc-import-error'; return; }
        message.textContent = ui("Wird eingelesen …");
        let doc;
        try { doc = JSON.parse(await file.text()); } catch (error) { message.textContent = IMPORT_ERRORS.invalid_body; message.className = 'sc-muted sc-import-error'; return; }
        const res = await api('/characters/import', 'POST', doc);
        if (!res.ok) {
            const detail = res.data && (res.data.problems || res.data.blockers);
            const base = IMPORT_ERRORS[res.data && res.data.error] || (res.status === 429 ? IMPORT_ERRORS.rate_limited : 'Der Import ist fehlgeschlagen.');
            message.textContent = `${res.data && res.data.message && res.data.error === 'import_invalid' ? res.data.message : base}${Array.isArray(detail) && detail.length ? ` (${detail.slice(0, 3).map((d) => (typeof d === 'string' ? d : d.message || d.code || '')).filter(Boolean).join('; ')})` : ''}`;
            message.className = 'sc-muted sc-import-error';
            return;
        }
        message.textContent = ui("Charakter angelegt. Du wirst weitergeleitet …");
        location.href = `/character-sheet?id=${res.data.character.id}`;
    }

    let homeLabels=[];
    function homeLabel(source,parameters={}) {
        const node=document.createTextNode(ui(source,parameters));
        homeLabels.push({node,source,parameters});return node;
    }
    async function showHome() {
        app.draft = null;
        clearTimeout(app.saveTimer);
        $('scBuilder').hidden = true;
        const home = $('scHome');
        home.hidden = false;
        history.replaceState(null, '', location.pathname);
        const res = await api('/drafts');
        const drafts = res.ok ? res.data.drafts : [];
        home.textContent = '';
        homeLabels=[];
        home.append(
            h('div', { class: 'sc-home-card' },
                h('h2', { text: homeLabel("Neuen Charakter beginnen") }),
                h('p', { class: 'sc-muted', text: homeLabel("Du baust auf dem veröffentlichten SRD 5.2.1. Alles wird als Entwurf gespeichert, du kannst jederzeit abbrechen und später weitermachen.") }),
                h('div', { class: 'sc-row' },
                    h('button', { type: 'button', class: 'sc-btn sc-btn-primary', id: 'scNewGuided', onclick: () => startNew('guided') }, homeLabel("Geführt, Schritt für Schritt")),
                    h('button', { type: 'button', class: 'sc-btn', id: 'scNewQuick', onclick: () => startNew('quick') }, homeLabel("Schnellbau (alles auf einer Seite)")),
                    h('button', { type: 'button', class: 'sc-btn', id: 'scNewRandom', onclick: () => startNew('guided', 1) }, homeLabel("Zufallscharakter (Stufe 1)")))),
            h('div', { class: 'sc-home-card' },
                h('h2', { text: homeLabel("Offene Entwürfe") }),
                drafts.length ? h('ul', { class: 'sc-drafts' }, drafts.map((d) => h('li', { class: 'sc-draft' },
                    h('div', null, h('strong', { text: d.name || homeLabel("Unbenannter Charakter") }),
                        h('div', { class: 'sc-muted', text: homeLabel("Zuletzt geändert: {p0}",{p0:(new Date(d.updated_at + 'Z').toLocaleString('de-DE'))}) })),
                    h('div', { class: 'sc-row' },
                        h('button', { type: 'button', class: 'sc-btn sc-btn-small', onclick: () => openDraft(d.id, null, d.step) }, homeLabel("Fortsetzen")),
                        h('button', { type: 'button', class: 'sc-btn sc-btn-small', onclick: () => duplicateDraft(d.id) }, homeLabel("Duplizieren")),
                        h('button', { type: 'button', class: 'sc-btn sc-btn-small sc-btn-danger', onclick: () => discardDraft(d.id) }, homeLabel("Verwerfen"))))))
                    : h('p', { class: 'sc-muted', text: homeLabel("Noch keine Entwürfe.") })),
            h('div', { class: 'sc-home-card', id: 'scImportCard' },
                h('h2', { text: homeLabel("Charakter einlesen") }),
                h('p', { class: 'sc-muted', text: homeLabel("Hier kannst du eine gesicherte Charakterdatei (.rollcharakter.json) einlesen. Es entsteht ein neuer, unabhängiger Charakter für dich.") }),
                h('div', { class: 'sc-row' },
                    h('label', { class: 'sc-import-file' }, h('span', { class: 'sc-muted', text: homeLabel("Datei wählen") }),
                        h('input', { type: 'file', id: 'scImportFile', accept: '.json,application/json' })),
                    h('button', { type: 'button', class: 'sc-btn', id: 'scImportGo', onclick: (event) => importFile($('scImportFile'), $('scImportMessage')) }, homeLabel("Einlesen"))),
                h('p', { class: 'sc-muted', id: 'scImportMessage', role: 'status', 'aria-live': 'polite' })),
            h('p', { class: 'sc-home-links' }, h('a', { href: '/characters', text: homeLabel("Zu meinen Charakteren") })));
        setStatus('');
    }

    // ---------------------------------------------------------------- finalize helpers (used by review step)
    SC.finalize = async function (campaignId) {
        app.finalizing = true;
        try {
            if (app.dirty || app.saving) {
                clearTimeout(app.saveTimer);
                await new Promise((resolve) => { const wait = () => (app.saving ? setTimeout(wait, 100) : resolve()); wait(); });
                if (app.dirty) await runSave();
            }
            const body = { version: app.draft.version };
            if (campaignId) body.campaign_id = Number(campaignId);
            return await api(`/drafts/${app.draft.id}/finalize`, 'POST', body);
        } finally {
            app.finalizing = false;
        }
    };
    SC.loadCampaigns = async function () {
        if (app.campaigns) return app.campaigns;
        app.campaigns = [];
        try {
            const result = await window.Auth.makeAuthRequest('/api/campaigns/mine');
            app.campaigns = (result && result.campaigns) || [];
        } catch (error) { /* optional */ }
        return app.campaigns;
    };
    SC.showHome = showHome;
    SC.openDraft = openDraft;

    // ---------------------------------------------------------------- init
    async function init() {
        const user = await window.Auth.requireAuth();
        if (!user) return;
        const metaRes = await api('/meta');
        // Avoid reusing the pre-display API representation, which lacks its version header.
        const dataRes = await api('/creator-data?displaySchema=1');
        if (!metaRes.ok || !dataRes.ok) {
            setStatusSource("Der Ersteller konnte nicht geladen werden. Bitte lade die Seite neu.");
            return;
        }
        app.data = dataRes.data;
        app.canonicalHash=dataRes.canonicalHash;
        // Published homebrew Species this account may choose; the server re-checks access on every save.
        const catalogRes = await api('/species-catalog');
        if (catalogRes.ok && Array.isArray(catalogRes.data.species) && catalogRes.data.species.length) {
            app.data = { ...app.data, species: [...app.data.species, ...catalogRes.data.species] };
        }
        const originRes = await api('/origin-catalog');
        if (originRes.ok) app.data = {...app.data,
            backgrounds:[...app.data.backgrounds,...(originRes.data.backgrounds || [])],
            feats:[...app.data.feats,...(originRes.data.feats || [])]};
        app.defaultSources = metaRes.data.defaultSources;
        buildLookups(app.data);
        await SC.loadLocale();
        let savedMode = 'guided';
        try { savedMode = localStorage.getItem('srdCreatorMode') || 'guided'; } catch (error) { /* optional */ }
        app.mode = savedMode === 'quick' ? 'quick' : 'guided';

        $('scBackHome').addEventListener('click', async () => { await runSaveNow(); showHome(); });
        $('scModeGuided').addEventListener('click', () => { app.mode = 'guided'; syncUrl(); renderAll(); });
        $('scModeQuick').addEventListener('click', () => { app.mode = 'quick'; syncUrl(); renderAll(); });
        $('scPrev').addEventListener('click', () => { const i = STEPS.findIndex(([id]) => id === app.step); if (i > 0) goStep(STEPS[i - 1][0]); });
        $('scNext').addEventListener('click', () => { const i = STEPS.findIndex(([id]) => id === app.step); if (i < STEPS.length - 1) goStep(STEPS[i + 1][0]); });
        $('scDialogClose').addEventListener('click', () => $('scDialog').close());
        window.addEventListener('beforeunload', (event) => { if (app.dirty || app.saving) { event.preventDefault(); event.returnValue = ''; } });
        document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden' && app.dirty) runSave(); });

        const params = new URLSearchParams(location.search);
        const draftId = Number(params.get('draft'));
        if (draftId) await openDraft(draftId, params.get('modus') === 'schnell' ? 'quick' : (params.get('schritt') ? 'guided' : app.mode), params.get('schritt'));
        else await showHome();
    }

    async function runSaveNow() {
        clearTimeout(app.saveTimer);
        if (app.saving) await new Promise((resolve) => { const wait = () => (app.saving ? setTimeout(wait, 100) : resolve()); wait(); });
        if (app.dirty && !app.conflict) await runSave();
    }
    SC.goStep = goStep;

    let renderedLocale=window.VTTI18n?.contentLocale() || 'de';
    function refreshLocaleNotice(){ $('scLanguageNotice').hidden=renderedLocale!=='en'; }
    refreshLocaleNotice();
    function refreshLocaleView(){
        refreshLocaleNotice();SC.refreshLocaleStatus?.();
        SC.refreshFinalizeLabels?.();
        if(app.statusSource)setStatusSource(app.statusSource);
        for(const {node,source,parameters} of homeLabels)if(node.isConnected)node.data=ui(source,parameters);
        if(app.draft?.status==='draft' && !$('scBuilder').hidden){
            if(app.saveText)setSaveText(app.saveText);
            // Keep campaign choice and the connected async finalize result; translate only its authored labels.
            SC.localeFinalize=$('scFinalize');
            try { renderAll(true); } finally { SC.localeFinalize=null; }
        }
    }
    window.addEventListener('vtt:displaychange',()=>{
        const next=window.VTTI18n.contentLocale();
        if(next===renderedLocale)return;
        renderedLocale=next;
        const ready=app.data?SC.loadLocale():null;
        refreshLocaleView();
        ready?.then(current=>{if(current){refreshLocaleView();SC.refreshOpenEntry?.();}});
    });

    document.addEventListener('DOMContentLoaded', () => {
        // steps/random modules register on window.SrdCreator before DOMContentLoaded fires
        init().catch((error) => { console.error(error); setStatusSource("Der Ersteller konnte nicht gestartet werden."); });
    });
})();
