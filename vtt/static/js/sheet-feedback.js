/* Compose the existing SRD sheet into a compact play surface. Permissions,
 * inventory writes and rolls remain in their existing server-authorized paths. */
(function () {
    'use strict';
    const TABS = [['play', 'Spielen'], ['spells', 'Zauber'], ['inventory', 'Inventar'], ['features', 'Merkmale'], ['manage', 'Verwaltung']];
    let characterId = null;
    let activeTab = 'play';
    let revealSection = () => {};
    let preferences = {};
    try { preferences = JSON.parse(localStorage.getItem('vtt.sheet.display.v1') || '{}') || {}; } catch (_) { /* optional storage */ }
    if (typeof preferences !== 'object' || Array.isArray(preferences)) preferences = {};

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }
    function savePreferences() {
        try { localStorage.setItem('vtt.sheet.display.v1', JSON.stringify(preferences)); } catch (_) { /* display still works */ }
    }
    function select(label, id, options, value, change) {
        const wrap = el('label', 'sf-preference', label);
        const field = el('select');
        field.id = id;
        for (const [key, text] of options) {
            const option = el('option', '', text);
            option.value = key;
            field.append(option);
        }
        field.value = value;
        field.addEventListener('change', () => change(field.value));
        wrap.append(field);
        return wrap;
    }
    function portraits(character) {
        const wrap = el('div', 'sf-portraits');
        for (const [key, label] of [['avatar_url', 'Avatar'], ['token_url', 'Token']]) {
            if (character[key]) {
                const image = el('img', 'sf-portrait');
                image.src = character[key];
                image.alt = `${label} von ${character.name}`;
                image.width = image.height = 56;
                wrap.append(image);
            } else {
                const placeholder = el('span', 'sf-portrait sf-portrait-empty', label);
                wrap.append(placeholder);
            }
        }
        return wrap;
    }
    function spellPanel(detail, data) {
        const box = el('div');
        box.append(el('h3', 'srd-sheet-subtitle', 'Zauberwirken'));
        const filter = el('div', 'sf-spell-filter');
        const rows = [];
        const classes = new Map((data.classes || []).map((entry) => [entry.classKey, entry.name]));
        const memberships = new Map();
        const labels = { cantrips: 'Zaubertrick', spellbook: 'Zauberbuch', known: 'Bekannt', prepared: 'Vorbereitet' };
        for (const [key, lists] of Object.entries(detail.srd?.state?.spells || {})) {
            for (const [list, ids] of Object.entries(lists || {})) {
                if (!labels[list] || !Array.isArray(ids)) continue;
                for (const id of ids) {
                    const record = memberships.get(id) || [];
                    record.push(`${classes.get(key) || key} · ${labels[list]}`);
                    memberships.set(id, record);
                }
            }
        }
        const casting = detail.evaluation?.spellcasting || {};
        for (const [key, info] of Object.entries(casting.classes || {})) {
            box.append(el('p', 'sf-caster', `${classes.get(key) || key}: Zauber-SG ${info.saveDc} · Zauberangriff ${info.attackBonus >= 0 ? '+' : ''}${info.attackBonus}`));
        }
        const slots = (casting.slots || []).flatMap((count, index) => count ? [`Grad ${index + 1}: ${count}`] : []);
        if (casting.pact) slots.push(`Paktmagie: ${casting.pact.slots} Plätze · Grad ${casting.pact.grade}`);
        if (slots.length) box.append(el('p', 'sf-caster', `Zauberplätze · ${slots.join(' · ')}`));
        const grades = [...new Set([...memberships.keys()].map((id) => data.spells[id]?.level).filter(Number.isInteger))].sort((a, b) => a - b);
        let grade = '';
        const search = el('input');
        search.type = 'search';
        search.id = 'sfSpellSearch';
        search.placeholder = 'Zauber suchen';
        const searchLabel = el('label', 'sf-preference', 'Suche');
        searchLabel.append(search);
        const count = el('p', 'sf-count');
        count.setAttribute('role', 'status');
        const apply = () => {
            const term = search.value.trim().toLocaleLowerCase('de');
            for (const row of rows) row.node.hidden = !((grade === '' || String(row.grade) === grade) && row.name.includes(term));
            count.textContent = `${rows.filter((row) => !row.node.hidden).length} von ${rows.length} Zaubern`;
        };
        filter.append(searchLabel, select('Zaubergrad', 'sfSpellGrade', [['', 'Alle Grade'], ...grades.map((g) => [String(g), g === 0 ? 'Zaubertricks' : `${g}. Grad`])], '', (value) => { grade = value; apply(); }));
        search.addEventListener('input', apply);
        box.append(filter, count);
        const list = el('div', 'sf-spell-list');
        for (const [id, groups] of [...memberships].sort(([a], [b]) => (data.spells[a]?.level || 0) - (data.spells[b]?.level || 0) || (data.spells[a]?.name || a).localeCompare(data.spells[b]?.name || b, 'de'))) {
            const spell = data.spells[id];
            const card = el('article', 'sf-spell-card');
            card.append(el('strong', '', spell?.name || id), el('small', '', `${spell?.level === 0 ? 'Zaubertrick' : `${spell?.level ?? '?'}. Grad`}${spell?.ritual ? ' · Ritual' : ''}`), el('small', '', groups.join(' · ')));
            rows.push({ node: card, grade: spell?.level, name: (spell?.name || id).toLocaleLowerCase('de') });
            list.append(card);
        }
        if (!rows.length) list.append(el('p', 'sheet-empty', 'Dieser Charakter hat keine eingetragenen Zauber.'));
        box.append(list);
        apply();
        return box;
    }

    function compose(character, detail, data, nodes) {
        if (characterId !== character.id) { characterId = character.id; activeTab = 'play'; }
        const header = el('div', 'sf-heading');
        const identity = el('div');
        identity.append(el('h3', '', character.name), el('p', '', `${character.class || (detail.evaluation?.classes || []).map((c) => c.name).join(' / ')} · Stufe ${detail.evaluation?.level ?? character.level}`));
        const money = el('p', 'sf-wallet', 'Münzen werden geladen …');
        money.id = 'sfWallet';
        money.setAttribute('role', 'status');
        const loadout = el('p', 'sf-loadout');
        loadout.id = 'sfLoadout';
        identity.append(money, loadout);
        header.append(portraits(character), identity);

        const controls = el('div', 'sf-controls');
        const theme = preferences.theme === 'night' ? 'night' : 'paper';
        document.body.dataset.sheetTheme = theme;
        controls.append(select('Darstellung', 'sfTheme', [['paper', 'Pergament'], ['night', 'Nacht']], theme, (value) => {
            document.body.dataset.sheetTheme = value; preferences.theme = value; savePreferences();
        }));
        const tablist = el('div', 'sf-tabs');
        tablist.setAttribute('role', 'tablist');
        tablist.setAttribute('aria-label', 'Charakterbogenbereiche');
        const panels = new Map();
        const buttons = new Map();
        const show = (key, focus = false) => {
            activeTab = key;
            for (const [id, panel] of panels) {
                const on = id === key;
                panel.hidden = !on;
                buttons.get(id).setAttribute('aria-selected', String(on));
                buttons.get(id).tabIndex = on ? 0 : -1;
            }
            if (focus) buttons.get(key).focus();
        };
        for (const [key, label] of TABS) {
            const button = el('button', 'sf-tab', label);
            button.type = 'button'; button.id = `sfTab-${key}`;
            button.setAttribute('role', 'tab'); button.setAttribute('aria-controls', `sfPanel-${key}`);
            button.addEventListener('click', () => show(key));
            button.addEventListener('keydown', (event) => {
                const index = TABS.findIndex(([id]) => id === key);
                const next = { ArrowRight: (index + 1) % TABS.length, ArrowLeft: (index + TABS.length - 1) % TABS.length, Home: 0, End: TABS.length - 1 }[event.key];
                if (next !== undefined) { event.preventDefault(); show(TABS[next][0], true); }
            });
            const panel = el('section', 'sf-panel'); panel.id = `sfPanel-${key}`;
            panel.setAttribute('role', 'tabpanel'); panel.setAttribute('aria-labelledby', button.id); panel.tabIndex = 0;
            buttons.set(key, button); panels.set(key, panel); tablist.append(button);
        }
        let group = 'play';
        const rollbar = nodes[0];
        for (const node of nodes) {
            if (node === rollbar) continue;
            if (node.id === 'srdSpeciesOrigin') { panels.get('features').append(node); continue; }
            if (node.classList.contains('srd-sheet-subtitle') && node.textContent === 'Zauberwirken') { group = 'discard-spells'; continue; }
            if (node.classList.contains('srd-sheet-subtitle') && node.textContent === 'Talente') group = 'features';
            if (node.id === 'srdProgression' || node.id === 'srdManage' || node.classList.contains('srd-sheet-note') || node.classList.contains('srd-sheet-link')) group = 'manage';
            if (node.id === 'srdInventory') group = 'inventory';
            if (group !== 'discard-spells') panels.get(group).append(node);
        }
        panels.get('spells').append(spellPanel(detail, data));
        for (const id of ['sheetIdentityGrid', 'dndExportSection']) {
            const node = document.getElementById(id);
            if (node) panels.get('manage').append(id === 'sheetIdentityGrid' ? node.closest('.sheet-pane') : node);
        }
        revealSection = (id) => {
            const target = document.getElementById(id);
            for (const [key, panel] of panels) {
                if (target && panel.contains(target)) { show(key); break; }
            }
        };
        const unit = preferences.unit === 'ft' ? 'ft' : 'm';
        const updateDistance = (value) => {
            const meters = detail.evaluation?.speedMeters;
            if (typeof meters !== 'number') return;
            for (const cell of panels.get('play').querySelectorAll('.srd-sheet-cell')) {
                if (cell.querySelector('.srd-sheet-label')?.textContent !== 'Bewegung') continue;
                cell.querySelector('.srd-sheet-value').textContent = `${(value === 'ft' ? Math.round(meters / 0.3 * 100) / 100 : meters).toLocaleString('de-DE')} ${value}`;
            }
        };
        controls.append(select('Entfernungen', 'sfUnits', [['m', 'Meter'], ['ft', 'Feet']], unit, (value) => { preferences.unit = value; savePreferences(); updateDistance(value); }));
        updateDistance(unit);
        show(activeTab);
        return [header, controls, rollbar, tablist, ...panels.values()];
    }
    function updateInventory(payload) {
        const money = document.getElementById('sfWallet');
        if (!money || !payload?.coins) return;
        money.textContent = ['PM', 'GM', 'EM', 'SM', 'KM'].map((code) => `${payload.coins[code] || 0} ${code}`).join(' · ')
            + (payload.seeded ? '' : ' · Startausrüstung noch nicht übernommen');
        const loadout = document.getElementById('sfLoadout');
        if (loadout) {
            const names = (payload.items || []).filter((item) => item.equipped).map((item) => item.name);
            loadout.textContent = names.length ? `Angelegt: ${names.slice(0, 4).join(' · ')}${names.length > 4 ? ` · +${names.length - 4} im Inventar` : ''}` : 'Keine Ausrüstung angelegt';
        }
    }
    window.SheetFeedback = { compose, updateInventory, reveal: (id) => revealSection(id) };
})();
