(function () {
    'use strict';

    const API = '/api/rulesets/srd-5.2.1-de/compendium';
    const PAGE = 50;
    // Only authored controls, headings and status text go through the explicit UI catalog.
    // Entity names, facet values and rule blocks from the API always stay source text.
    const ui = (source, parameters) => globalThis.VTTUi(source, parameters || {});
    const uiLocale = () => (globalThis.VTTI18n && globalThis.VTTI18n.locale ? globalThis.VTTI18n.locale() : 'de');
    class UiMessageError extends Error {}
    const TYPES = {
        spell: {
            label: 'Zauber',
            columns: [
                ['Name', (e) => e.name, true],
                ['Grad', (e) => (e.level === 0 ? ui('Zaubertrick') : String(e.level))],
                ['Schule', (e) => e.school],
                ['Zeitaufwand', (e) => e.castingTime],
                ['Reichweite', (e) => e.range],
                ['Komp.', (e) => e.components],
                ['Dauer', (e) => e.duration],
                ['Klassen', (e) => e.classes.join(', ')],
            ],
            filters: [
                { key: 'level', label: 'Grad', type: 'select', format: (v) => (v === 0 ? ui('Zaubertrick') : ui('Grad {level}', { level: v })) },
                { key: 'school', label: 'Schule', type: 'select' },
                { key: 'class', facet: 'classes', label: 'Klasse', type: 'select' },
                { key: 'concentration', label: 'Konzentration', type: 'tri' },
                { key: 'ritual', label: 'Ritual', type: 'tri' },
                { key: 'component', label: 'Komponente', type: 'options', options: ['V', 'G', 'M'] },
            ],
            sorts: [['name', 'Name'], ['level', 'Grad']],
        },
        creature: {
            label: 'Kreaturen',
            columns: [
                ['Name', (e) => e.name, true],
                ['HG', (e) => e.challenge],
                ['Größe', (e) => e.size || '–'],
                ['Typ', (e) => (e.subtype ? `${e.creatureType} (${e.subtype})` : e.creatureType)],
                ['RK', (e) => e.armorClass],
                ['TP', (e) => e.hitPoints],
                ['Bewegung', (e) => e.speed],
            ],
            filters: [
                { key: 'creatureType', label: 'Typ', type: 'select' },
                { key: 'size', label: 'Größe', type: 'select' },
                { key: 'origin', label: 'Herkunft', type: 'select', format: (v) => (v === 'animal' ? ui('Tiere') : ui('Monster')) },
                { key: 'cr_min', label: 'HG von', type: 'text', size: 4 },
                { key: 'cr_max', label: 'HG bis', type: 'text', size: 4 },
                { key: 'legendary', label: 'Legendär', type: 'tri' },
            ],
            sorts: [['name', 'Name'], ['cr', 'Herausforderungsgrad']],
        },
        'magic-item': {
            label: 'Magische Gegenstände',
            columns: [
                ['Name', (e) => e.name, true],
                ['Art', (e) => e.category],
                ['Seltenheit', (e) => e.rarity],
                ['Einstimmung', (e) => (e.attunement ? ui('ja') : ui('nein'))],
                ['Details', (e) => e.detail],
            ],
            filters: [
                { key: 'category', label: 'Art', type: 'select' },
                { key: 'rarity', label: 'Seltenheit', type: 'select' },
                { key: 'attunement', label: 'Einstimmung', type: 'tri' },
            ],
            sorts: [['name', 'Name'], ['rarity', 'Seltenheit']],
        },
        feat: {
            label: 'Talente',
            columns: [
                ['Name', (e) => e.name, true],
                ['Kategorie', (e) => e.category],
                ['Voraussetzung', (e) => e.prerequisite || '–'],
                ['Kurztext', (e) => e.summary],
            ],
            filters: [{ key: 'category', label: 'Kategorie', type: 'select' }],
            sorts: [['name', 'Name']],
        },
        weapon: {
            label: 'Waffen',
            columns: [
                ['Name', (e) => e.name, true],
                ['Klasse', (e) => `${e.weaponClass}, ${e.weaponKind}`],
                ['Schaden', (e) => e.damage],
                ['Eigenschaften', (e) => e.properties],
                ['Beherrschung', (e) => e.mastery],
                ['Gewicht', (e) => e.weight],
                ['Kosten', (e) => e.cost],
            ],
            filters: [
                { key: 'weaponClass', label: 'Waffenklasse', type: 'select' },
                { key: 'weaponKind', label: 'Art', type: 'select' },
                { key: 'mastery', label: 'Beherrschung', type: 'select' },
            ],
            sorts: [['name', 'Name']],
        },
        armor: {
            label: 'Rüstungen',
            columns: [
                ['Name', (e) => e.name, true],
                ['Kategorie', (e) => e.armorCategory],
                ['RK', (e) => e.armorClass],
                ['Stärke', (e) => e.strength],
                ['Heimlichkeit', (e) => e.stealth],
                ['Gewicht', (e) => e.weight],
                ['Kosten', (e) => e.cost],
            ],
            filters: [{ key: 'armorCategory', label: 'Kategorie', type: 'select' }],
            sorts: [['name', 'Name']],
        },
        class: {
            label: 'Klassen',
            columns: [
                ['Name', (e) => e.name, true],
                ['Trefferwürfel', (e) => ui('W{die}', { die: e.hitDie })],
                ['Hauptattribut', (e) => e.primaryAbility],
                ['Rettungswürfe', (e) => e.savingThrows.join(', ')],
                ['Zauberwirker', (e) => (e.spellcaster ? ui('ja') : ui('nein'))],
                ['Rüstungen', (e) => e.armorTraining],
            ],
            filters: [
                { key: 'primaryAbility', label: 'Hauptattribut', type: 'select' },
                { key: 'hitDie', label: 'Trefferwürfel', type: 'select', format: (v) => ui('W{die}', { die: v }) },
                { key: 'spellcaster', label: 'Zauberwirker', type: 'tri' },
            ],
            sorts: [['name', 'Name']],
        },
        subclass: {
            label: 'Unterklassen',
            columns: [
                ['Name', (e) => e.name, true],
                ['Klasse', (e) => e.className],
                ['Leitspruch', (e) => e.motto],
            ],
            filters: [{ key: 'className', label: 'Klasse', type: 'select' }],
            sorts: [['name', 'Name']],
        },
        'class-feature': {
            label: 'Klassenmerkmale',
            columns: [
                ['Name', (e) => e.name, true],
                ['Klasse', (e) => e.className],
                ['Stufe', (e) => e.level],
                ['Unterklasse', (e) => e.subclass || '–'],
                ['Kurztext', (e) => e.summary],
            ],
            filters: [
                { key: 'className', label: 'Klasse', type: 'select' },
                { key: 'level', label: 'Stufe', type: 'select', format: (v) => ui('Stufe {level}', { level: v }) },
                { key: 'subclass', label: 'Unterklasse', type: 'select' },
            ],
            sorts: [['name', 'Name'], ['level', 'Stufe']],
        },
        'class-option': {
            label: 'Klassenoptionen',
            columns: [
                ['Name', (e) => e.name, true],
                ['Klasse', (e) => e.className],
                ['Art', (e) => e.optionKind],
                ['Voraussetzung', (e) => e.prerequisite || '–'],
                ['Kurztext', (e) => e.summary],
            ],
            filters: [
                { key: 'className', label: 'Klasse', type: 'select' },
                { key: 'optionKind', label: 'Art', type: 'select' },
            ],
            sorts: [['name', 'Name']],
        },
        species: {
            label: 'Spezies',
            columns: [
                ['Name', (e) => e.name, true],
                ['Typ', (e) => e.creatureType],
                ['Größe', (e) => e.sizeText],
                ['Bewegungsrate', (e) => e.speed],
                ['Dunkelsicht', (e) => (e.darkvision ? `${e.darkvision} m` : '–')],
                ['Merkmale', (e) => e.traits.join(', ')],
            ],
            filters: [
                { key: 'creatureType', label: 'Typ', type: 'select' },
                { key: 'sizes', label: 'Größe', type: 'select' },
            ],
            sorts: [['name', 'Name']],
        },
        background: {
            label: 'Hintergründe',
            columns: [
                ['Name', (e) => e.name, true],
                ['Attributswerte', (e) => e.abilities.join(', ')],
                ['Talent', (e) => (e.featChoice ? `${e.feat} (${e.featChoice})` : e.feat)],
                ['Fertigkeiten', (e) => e.skills.join(', ')],
                ['Werkzeug', (e) => e.tool || '–'],
            ],
            filters: [{ key: 'feat', label: 'Talent', type: 'select' }],
            sorts: [['name', 'Name']],
        },
        gear: {
            label: 'Ausrüstung',
            columns: [
                ['Name', (e) => e.name, true],
                ['Kategorie', (e) => e.category],
                ['Gewicht', (e) => e.weight],
                ['Kosten', (e) => e.cost],
                ['Kurztext', (e) => e.summary],
            ],
            filters: [{ key: 'category', label: 'Kategorie', type: 'select' }],
            sorts: [['name', 'Name']],
        },
        tool: {
            label: 'Werkzeuge',
            columns: [
                ['Name', (e) => e.name, true],
                ['Kategorie', (e) => e.category],
                ['Attribut', (e) => e.ability],
                ['Gewicht', (e) => e.weight],
                ['Kosten', (e) => e.cost],
            ],
            filters: [
                { key: 'category', label: 'Kategorie', type: 'select' },
                { key: 'ability', label: 'Attribut', type: 'select' },
            ],
            sorts: [['name', 'Name']],
        },
        mount: {
            label: 'Reittiere',
            columns: [
                ['Name', (e) => e.name, true],
                ['Traglast', (e) => e.carryingCapacity],
                ['Kosten', (e) => e.cost],
            ],
            filters: [],
            sorts: [['name', 'Name']],
        },
        vehicle: {
            label: 'Fahrzeuge',
            columns: [
                ['Name', (e) => e.name, true],
                ['Bewegungsrate', (e) => e.speed],
                ['Besatzung', (e) => e.crew],
                ['Passagiere', (e) => e.passengers],
                ['Fracht (t)', (e) => e.cargoTons],
                ['RK', (e) => e.armorClass],
                ['TP', (e) => e.hitPoints],
                ['Kosten', (e) => e.cost],
            ],
            filters: [],
            sorts: [['name', 'Name']],
        },
        service: {
            label: 'Dienstleistungen',
            columns: [
                ['Name', (e) => e.name, true],
                ['Kategorie', (e) => e.category],
                ['Kosten', (e) => e.cost],
                ['Kurztext', (e) => e.summary],
            ],
            filters: [{ key: 'category', label: 'Kategorie', type: 'select' }],
            sorts: [['name', 'Name']],
        },
        glossary: {
            label: 'Regelbegriffe',
            columns: [
                ['Name', (e) => e.name, true],
                ['Kategorie', (e) => e.category],
                ['Kurztext', (e) => e.summary],
            ],
            filters: [{ key: 'category', label: 'Kategorie', type: 'select' }],
            sorts: [['name', 'Name']],
        },
    };

    const els = {
        form: document.getElementById('compendiumForm'),
        type: document.getElementById('cpType'),
        q: document.getElementById('cpQ'),
        filters: document.getElementById('cpFilters'),
        sort: document.getElementById('cpSort'),
        reset: document.getElementById('cpReset'),
        status: document.getElementById('cpStatus'),
        table: document.getElementById('cpTable'),
        caption: document.getElementById('cpCaption'),
        head: document.getElementById('cpHead'),
        body: document.getElementById('cpBody'),
        more: document.getElementById('cpMore'),
        results: document.getElementById('compendiumResults'),
        list: document.getElementById('cpList'),
        detail: document.getElementById('cpDetail'),
        detailBack: document.getElementById('cpDetailBack'),
        detailTitle: document.getElementById('cpDetailTitle'),
        detailMeta: document.getElementById('cpDetailMeta'),
        detailBody: document.getElementById('cpDetailBody'),
    };
    const ENTRY_API = `${API}/entry/`;

    let facets = {};
    let offset = 0;
    let timer = null;
    let requestId = 0;
    let typeRequestId = 0;
    let switchingType = false;

    function node(tag, text, className) {
        const n = document.createElement(tag);
        if (text !== undefined && text !== null) n.textContent = String(text);
        if (className) n.className = className;
        return n;
    }

    function field(labelText, control, id) {
        const wrap = node('div', null, 'compendium-field');
        const label = node('label', labelText);
        label.htmlFor = id;
        control.id = id;
        wrap.appendChild(label);
        wrap.appendChild(control);
        return wrap;
    }

    function select(options, includeAny = true) {
        const s = document.createElement('select');
        if (includeAny) s.appendChild(new Option(ui('Alle'), ''));
        options.forEach(([value, label]) => s.appendChild(new Option(label, value)));
        return s;
    }

    function buildFilters(typeKey) {
        els.filters.textContent = '';
        TYPES[typeKey].filters.forEach((spec) => {
            const id = `cpf-${spec.key}`;
            let control;
            if (spec.type === 'select') {
                const values = facets[spec.facet || spec.key] || [];
                control = select(values.map((v) => [String(v), spec.format ? spec.format(v) : String(v)]));
            } else if (spec.type === 'tri') {
                control = select([['true', ui('Ja')], ['false', ui('Nein')]]);
            } else if (spec.type === 'options') {
                control = select(spec.options.map((v) => [v, v]));
            } else {
                control = document.createElement('input');
                control.type = 'text';
                control.size = spec.size || 6;
                control.maxLength = 8;
            }
            control.name = spec.key;
            control.dataset.filter = spec.key;
            els.filters.appendChild(field(ui(spec.label), control, id));
        });
        els.sort.textContent = '';
        TYPES[typeKey].sorts.forEach(([value, label]) => els.sort.appendChild(new Option(ui(label), value)));
    }

    function currentParams() {
        const params = new URLSearchParams();
        params.set('type', els.type.value);
        if (els.q.value.trim()) params.set('q', els.q.value.trim());
        els.filters.querySelectorAll('[data-filter]').forEach((control) => {
            if (control.value) params.set(control.dataset.filter, control.value);
        });
        if (els.sort.value && els.sort.value !== 'name') params.set('sort', els.sort.value);
        return params;
    }

    function syncUrl(params) {
        try {
            window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
        } catch (error) { /* url sync is optional */ }
    }

    function renderHead(typeKey) {
        els.head.textContent = '';
        const tr = document.createElement('tr');
        TYPES[typeKey].columns.forEach(([title]) => {
            const th = node('th', ui(title));
            th.scope = 'col';
            tr.appendChild(th);
        });
        els.head.appendChild(tr);
    }

    function renderRows(typeKey, items) {
        items.forEach((entity) => {
            const tr = document.createElement('tr');
            TYPES[typeKey].columns.forEach(([, getter, isName]) => {
                const td = document.createElement('td');
                const value = getter(entity);
                if (isName) {
                    const a = node('a', value);
                    a.href = entity.url;
                    a.addEventListener('click', (event) => {
                        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
                        event.preventDefault();
                        openDetail(entity.id, 'push').catch(showError);
                    });
                    td.appendChild(a);
                } else {
                    td.textContent = value === null || value === undefined ? '–' : String(value);
                }
                tr.appendChild(td);
            });
            els.body.appendChild(tr);
        });
    }

    function renderTableBlock(block) {
        const wrap = node('div', null, 'regelwerk-table-wrap');
        const table = document.createElement('table');
        table.className = 'regelwerk-table';
        if (block.caption) table.appendChild(node('caption', block.caption));
        const head = document.createElement('tr');
        block.columns.forEach((column) => {
            const th = node('th', column);
            th.scope = 'col';
            head.appendChild(th);
        });
        const thead = document.createElement('thead');
        thead.appendChild(head);
        table.appendChild(thead);
        const tbody = document.createElement('tbody');
        block.rows.forEach((row) => {
            const tr = document.createElement('tr');
            row.forEach((value) => tr.appendChild(node('td', value)));
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        wrap.appendChild(table);
        return wrap;
    }

    function renderBlock(block) {
        if (block.type === 'heading') return node(`h${Math.min(block.level + 1, 6)}`, block.text);
        if (block.type === 'paragraph') return node('p', block.text);
        if (block.type === 'ordered-list' || block.type === 'unordered-list') {
            const list = document.createElement(block.type === 'ordered-list' ? 'ol' : 'ul');
            block.items.forEach((item) => list.appendChild(node('li', item)));
            return list;
        }
        if (block.type === 'definition-list') {
            const list = document.createElement('dl');
            block.entries.forEach((entry) => {
                list.appendChild(node('dt', entry.term));
                list.appendChild(node('dd', entry.definition));
            });
            return list;
        }
        if (block.type === 'table') return renderTableBlock(block);
        if (block.type === 'rule-callout' || block.type === 'page-note' || block.type === 'original-note') {
            const box = node('aside', null, block.type === 'original-note' ? 'regelwerk-original-note' : 'regelwerk-callout');
            if (block.title) box.appendChild(node('strong', block.title, 'regelwerk-callout-title'));
            box.appendChild(node('p', block.text));
            return box;
        }
        if (block.type === 'stat-block') {
            const box = node('section', null, 'regelwerk-stat-block');
            box.appendChild(node('h3', block.name, 'regelwerk-stat-title'));
            const details = document.createElement('dl');
            block.entries.forEach((entry) => {
                details.appendChild(node('dt', entry.label));
                details.appendChild(node('dd', entry.value));
            });
            box.appendChild(details);
            block.sections.forEach((section) => {
                box.appendChild(node('h4', section.title));
                box.appendChild(node('p', section.text));
            });
            return box;
        }
        return node('p', ui('Blocktyp {type} wird nicht angezeigt.', { type: block.type }));
    }

    function pageText(pages) {
        if (!pages || !pages.length) return '';
        return pages.length === 1
            ? ui('S. {page}', { page: pages[0] })
            : ui('S. {from}–{to}', { from: pages[0], to: pages[pages.length - 1] });
    }

    let detailPushed = false;
    let characterActionCleanup = null;
    let detailVersion = 0;

    function hideDetail() {
        detailVersion++; characterActionCleanup?.(); characterActionCleanup = null;
        els.detail.hidden = true;
        els.list.hidden = false;
    }

    async function openDetail(id, historyMode) {
        window.clearTimeout(timer); requestId++;
        els.results.setAttribute('aria-busy', 'false');
        const version = ++detailVersion;
        characterActionCleanup?.(); characterActionCleanup = null;
        const response = await fetch(ENTRY_API + encodeURIComponent(id), { credentials: 'same-origin' });
        if (!response.ok) throw new UiMessageError(ui('Eintrag nicht gefunden.'));
        const data = await response.json();
        if (version !== detailVersion) return;
        const entity = data.entity;
        els.detailTitle.textContent = entity.name;
        els.detailMeta.textContent = '';
        const label = TYPES[entity.type] ? ui(TYPES[entity.type].label) : entity.type;
        const pages = pageText(entity.sourcePages);
        els.detailMeta.appendChild(node('span', `${label} · SRD 5.2.1${pages ? `, ${pages}` : ''} · `));
        const link = node('a', ui('Im Regelwerk lesen'));
        link.href = entity.url;
        els.detailMeta.appendChild(link);
        els.detailBody.textContent = '';
        const actionRoot = node('div'); actionRoot.className = 'cp-character-actions-entry';
        els.detailBody.appendChild(actionRoot);
        import('/static/js/compendium-character.js').then(({mountCatalogAction}) => {
            if (version === detailVersion && actionRoot.isConnected) characterActionCleanup = mountCatalogAction(actionRoot, entity);
        }).catch(() => { if (version === detailVersion) actionRoot.textContent = ui('Charakteraktion konnte nicht geladen werden.'); });
        data.blocks.forEach((block) => els.detailBody.appendChild(renderBlock(block)));
        els.list.hidden = true;
        els.detail.hidden = false;
        if (historyMode) {
            const params = currentParams();
            params.set('entry', id);
            try {
                const url = `${window.location.pathname}?${params.toString()}`;
                if (historyMode === 'push') {
                    window.history.pushState(null, '', url);
                    detailPushed = true;
                } else {
                    window.history.replaceState(null, '', url);
                }
            } catch (error) { /* url sync is optional */ }
        }
        els.detailTitle.focus();
        els.detail.scrollIntoView({ block: 'start' });
    }

    function closeDetail() {
        if (detailPushed) {
            window.history.back();
            return;
        }
        hideDetail();
        syncUrl(currentParams());
    }

    window.addEventListener('popstate', () => {
        const entry = new URLSearchParams(window.location.search).get('entry');
        detailPushed = false;
        if (entry) openDetail(entry, null).catch(showError);
        else hideDetail();
    });

    async function load(append) {
        if (switchingType) return;
        const mine = ++requestId;
        const params = currentParams();
        if (!append) {
            offset = 0;
            els.table.hidden = true; els.more.hidden = true;
            hideDetail();
            syncUrl(params);
        }
        params.set('limit', String(PAGE));
        params.set('offset', String(offset));
        els.results.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(`${API}?${params.toString()}`, { credentials: 'same-origin' });
            const data = await response.json();
            if (mine !== requestId) return;
            if (!response.ok) {
                // Server diagnostics are German; keep them only in the German UI.
                throw new UiMessageError(uiLocale() === 'de' && data.error ? data.error : ui('Anfrage fehlgeschlagen.'));
            }
            const typeKey = data.type;
            const typeLabel = ui(TYPES[typeKey].label);
            if (!append) {
                els.body.textContent = '';
                renderHead(typeKey);
                els.caption.textContent = `${typeLabel} (${data.total})`;
            }
            renderRows(typeKey, data.items);
            offset += data.items.length;
            els.table.hidden = data.total === 0;
            els.more.hidden = offset >= data.total;
            els.status.textContent = data.total === 0
                ? ui('Keine Treffer für diese Filter.')
                : ui('{shown} von {total} {label} angezeigt.', { shown: offset, total: data.total, label: typeLabel });
        } catch (error) {
            if (mine === requestId) showError(error);
        } finally {
            if (mine === requestId) els.results.setAttribute('aria-busy', 'false');
        }
    }

    async function switchType(typeKey, preset) {
        const mine = ++typeRequestId;
        switchingType = true;
        window.clearTimeout(timer); requestId++;
        els.table.hidden = true; els.more.hidden = true;
        els.results.setAttribute('aria-busy', 'true');
        els.type.value = typeKey;
        try {
            const response = await fetch(`${API}?type=${encodeURIComponent(typeKey)}&limit=1`, { credentials: 'same-origin' });
            if (!response.ok) throw new UiMessageError(ui('Compendium nicht verfügbar.'));
            const data = await response.json();
            if (mine !== typeRequestId) return false;
            facets = data.facets;
            buildFilters(typeKey);
            if (preset) {
                els.q.value = preset.get('q') || '';
                els.filters.querySelectorAll('[data-filter]').forEach((control) => {
                    control.value = preset.get(control.dataset.filter) || '';
                });
                els.sort.value = preset.get('sort') || 'name';
            }
            switchingType = false;
            await load(false);
            return mine === typeRequestId;
        } catch (error) {
            if (mine === typeRequestId) {
                switchingType = false; els.results.setAttribute('aria-busy', 'false'); throw error;
            }
            return false;
        }
    }

    function debounce() {
        window.clearTimeout(timer);
        requestId++;
        els.table.hidden = true; els.more.hidden = true;
        els.results.setAttribute('aria-busy', 'true');
        timer = window.setTimeout(() => load(false), 200);
    }

    async function init() {
        Object.entries(TYPES).forEach(([key, spec]) => els.type.appendChild(new Option(ui(spec.label), key)));
        const preset = new URLSearchParams(window.location.search);
        const typeKey = TYPES[preset.get('type')] ? preset.get('type') : 'spell';
        els.type.addEventListener('change', () => switchType(els.type.value, null).catch(showError));
        els.q.addEventListener('input', debounce);
        els.filters.addEventListener('input', debounce);
        els.filters.addEventListener('change', debounce);
        els.sort.addEventListener('change', () => load(false));
        els.more.addEventListener('click', () => load(true));
        els.reset.addEventListener('click', () => switchType(els.type.value, null).catch(showError));
        els.form.addEventListener('submit', (event) => event.preventDefault());
        els.detailBack.addEventListener('click', closeDetail);
        try {
            const currentType = await switchType(typeKey, preset);
            if (currentType && preset.get('entry')) await openDetail(preset.get('entry'), 'replace');
        } catch (error) {
            showError(error);
        }
    }

    function showError(error) {
        // Only our own localized messages are shown; raw browser/JSON errors are not.
        els.status.textContent = error instanceof UiMessageError && error.message
            ? error.message
            : ui('Compendium nicht verfügbar.');
        els.results.setAttribute('aria-busy', 'false');
    }

    init();
}());
