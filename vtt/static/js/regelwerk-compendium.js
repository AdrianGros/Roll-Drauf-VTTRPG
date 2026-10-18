(function () {
    'use strict';

    const API = '/api/rulesets/srd-5.2.1-de/compendium';
    const PAGE = 50;
    const TYPES = {
        spell: {
            label: 'Zauber',
            columns: [
                ['Name', (e) => e.name, true],
                ['Grad', (e) => (e.level === 0 ? 'Zaubertrick' : String(e.level))],
                ['Schule', (e) => e.school],
                ['Zeitaufwand', (e) => e.castingTime],
                ['Reichweite', (e) => e.range],
                ['Komp.', (e) => e.components],
                ['Dauer', (e) => e.duration],
                ['Klassen', (e) => e.classes.join(', ')],
            ],
            filters: [
                { key: 'level', label: 'Grad', type: 'select', format: (v) => (v === 0 ? 'Zaubertrick' : `Grad ${v}`) },
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
                { key: 'origin', label: 'Herkunft', type: 'select', format: (v) => (v === 'animal' ? 'Tiere' : 'Monster') },
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
                ['Einstimmung', (e) => (e.attunement ? 'ja' : 'nein')],
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
    };

    let facets = {};
    let offset = 0;
    let timer = null;
    let requestId = 0;

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
        if (includeAny) s.appendChild(new Option('Alle', ''));
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
                control = select([['true', 'Ja'], ['false', 'Nein']]);
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
            els.filters.appendChild(field(spec.label, control, id));
        });
        els.sort.textContent = '';
        TYPES[typeKey].sorts.forEach(([value, label]) => els.sort.appendChild(new Option(label, value)));
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
            const th = node('th', title);
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
                    td.appendChild(a);
                } else {
                    td.textContent = value === null || value === undefined ? '–' : String(value);
                }
                tr.appendChild(td);
            });
            els.body.appendChild(tr);
        });
    }

    async function load(append) {
        const mine = ++requestId;
        const params = currentParams();
        if (!append) {
            offset = 0;
            syncUrl(params);
        }
        params.set('limit', String(PAGE));
        params.set('offset', String(offset));
        els.results.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(`${API}?${params.toString()}`, { credentials: 'same-origin' });
            const data = await response.json();
            if (mine !== requestId) return;
            if (!response.ok) throw new Error(data.error || 'Anfrage fehlgeschlagen.');
            const typeKey = data.type;
            if (!append) {
                els.body.textContent = '';
                renderHead(typeKey);
                els.caption.textContent = `${TYPES[typeKey].label} (${data.total})`;
            }
            renderRows(typeKey, data.items);
            offset += data.items.length;
            els.table.hidden = data.total === 0;
            els.more.hidden = offset >= data.total;
            els.status.textContent = data.total === 0
                ? 'Keine Treffer für diese Filter.'
                : `${offset} von ${data.total} ${TYPES[typeKey].label} angezeigt.`;
        } catch (error) {
            els.status.textContent = error.message || 'Compendium nicht verfügbar.';
        } finally {
            if (mine === requestId) els.results.setAttribute('aria-busy', 'false');
        }
    }

    async function switchType(typeKey, preset) {
        els.type.value = typeKey;
        const response = await fetch(`${API}?type=${encodeURIComponent(typeKey)}&limit=1`, { credentials: 'same-origin' });
        if (!response.ok) throw new Error('Compendium nicht verfügbar.');
        facets = (await response.json()).facets;
        buildFilters(typeKey);
        if (preset) {
            els.q.value = preset.get('q') || '';
            els.filters.querySelectorAll('[data-filter]').forEach((control) => {
                control.value = preset.get(control.dataset.filter) || '';
            });
            els.sort.value = preset.get('sort') || 'name';
        }
        return load(false);
    }

    function debounce() {
        window.clearTimeout(timer);
        timer = window.setTimeout(() => load(false), 200);
    }

    async function init() {
        Object.entries(TYPES).forEach(([key, spec]) => els.type.appendChild(new Option(spec.label, key)));
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
        try {
            await switchType(typeKey, preset);
        } catch (error) {
            showError(error);
        }
    }

    function showError(error) {
        els.status.textContent = error.message || 'Compendium nicht verfügbar.';
        els.results.setAttribute('aria-busy', 'false');
    }

    init();
}());
