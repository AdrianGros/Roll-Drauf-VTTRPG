(function () {
    'use strict';

    const SC = window.SrdCreator;
    const { h, ABIL, sign, fmtMeters } = SC;
    const app = SC.app;
    const st = () => app.draft.state;
    const ev = () => app.evaluation;

    const CHOICE_LABELS = {
        'primal-order': 'Heilige Rolle', 'divine-order': 'Heilige Rolle', 'fighting-style': 'Kampfstil-Talent',
        'weapon-mastery': 'Waffenbeherrschung', 'eldritch-invocations': 'Schauerliche Anrufungen',
        'thieves-cant-language': 'Zusätzliche Sprache (Diebessprache)', 'deft-explorer-languages': 'Geschickter Erkunder: Sprachen',
        'draconic-ancestry': 'Drakonische Abstammung', lineage: 'Abstammung', 'spellcasting-ability': 'Zauberattribut',
        'keen-senses': 'Scharfe Sinne: Fertigkeit', 'giant-ancestry': 'Abstammung der Riesen', skillful: 'Geschickt: Fertigkeit',
        versatile: 'Vielseitig: Herkunftstalent', size: 'Größe',
    };
    const OPTION_LABELS = { magician: 'Magier', warden: 'Wächter', protector: 'Beschützer', thaumaturge: 'Thaumaturg' };
    const ARMOR_LABELS = { light: 'Leichte Rüstung', medium: 'Mittelschwere Rüstung', heavy: 'Schwere Rüstung', shield: 'Schilde' };
    const label = (id) => CHOICE_LABELS[id] || id.replace(/-/g, ' ');

    // ------------------------------------------------------------ shared widgets
    function field(text, control, id) {
        return h('div', { class: 'sc-field' }, h('label', { for: id, text }), control);
    }
    function select(id, options, value, onchange, placeholder) {
        const node = h('select', { id, onchange: (e) => onchange(e.target.value) },
            placeholder ? h('option', { value: '', text: placeholder }) : null,
            options.map(([v, t]) => h('option', { value: v, text: t })));
        node.value = value == null ? '' : String(value);
        return node;
    }
    function card(title, sub, pressed, onclick, extra) {
        return h('button', { type: 'button', class: 'sc-card', 'aria-pressed': String(!!pressed), onclick },
            h('strong', { text: title }), sub ? h('span', { text: sub }) : null, extra || null);
    }
    function checkRow(text, checked, disabled, onchange, sub, detailId) {
        return h('div', { class: 'sc-check' },
            h('label', { class: 'sc-check-label' }, h('input', { type: 'checkbox', checked, disabled, onchange: (e) => onchange(e.target.checked) }),
                h('span', null, text, sub ? h('small', { text: sub }) : null)),
            detailId ? h('button', { type: 'button', class: 'sc-btn sc-btn-small sc-btn-quiet', onclick: () => SC.openEntry(detailId, text), 'aria-label': `Regeltext zu ${text}` }, '?') : null);
    }
    function countedList(options, selected, max, onchange, group) {
        const full = selected.length >= max;
        return h('div', { class: 'sc-choice-list', role: 'group', 'aria-label': group || null },
            options.map((o) => {
                const on = selected.includes(o.id);
                return checkRow(o.name, on, !on && full, (checked) => {
                    const next = checked ? selected.concat(o.id) : selected.filter((x) => x !== o.id);
                    onchange(next);
                }, o.sub, o.detail);
            }));
    }
    function counter(have, need) {
        return h('p', { class: have === need ? 'sc-ok-note' : 'sc-muted', 'aria-live': 'polite', text: `${have} von ${need} gewählt` });
    }
    const panel = (...kids) => h('div', { class: 'sc-panel' }, ...kids);

    // ------------------------------------------------------------ derived helpers
    function levelsByClass() {
        const out = {};
        (st().levels || []).forEach((l) => { out[l.classKey] = (out[l.classKey] || 0) + 1; });
        return out;
    }
    const classOrder = () => Object.keys(levelsByClass());
    const firstClass = () => ((st().levels || [])[0] || {}).classKey || null;
    const cls = (key) => SC.L.classes[key];
    function choiceNeed(choice, classLevel) {
        if (choice.count != null) return choice.count;
        return (choice.countByLevel && choice.countByLevel[String(classLevel)]) || 0;
    }
    function expectedExpertise() {
        let total = 0;
        const lv = levelsByClass();
        Object.keys(lv).forEach((k) => cls(k).featureChoices.forEach((c) => { if (c.kind === 'expertise' && c.level <= lv[k]) total += c.count || 0; }));
        return total;
    }
    function weaponAllowed(c, w) {
        return c.weaponProficiencies.some((g) => g.category === w.category && (!g.requiresProperty || w.properties.some((p) => g.requiresProperty.includes(p.name))));
    }
    function castingRow(key, classLevel) {
        const sc = cls(key).spellcasting;
        return sc ? sc.levels.find((r) => r.level === classLevel) : null;
    }
    function maxGrade(key, classLevel) {
        const sc = cls(key).spellcasting;
        const row = castingRow(key, classLevel);
        if (!sc || !row) return 0;
        if (sc.kind === 'pact') return row.slotGrade;
        let best = 0;
        row.slots.forEach((n, i) => { if (n) best = i + 1; });
        return best;
    }
    function spellbookSize(key, classLevel) {
        const book = cls(key).spellcasting && cls(key).spellcasting.spellbook;
        return book ? book.startingSpells + book.perLevel * (classLevel - 1) : 0;
    }

    // Keep dependent selections consistent after the level history changed.
    function prune(state, oldFirst) {
        const lv = {};
        (state.levels || []).forEach((l) => { lv[l.classKey] = (lv[l.classKey] || 0) + 1; });
        if (state.advancements) {
            state.advancements = state.advancements.filter((a) => lv[a.classKey] >= a.classLevel && (cls(a.classKey).asiLevels.includes(a.classLevel) || cls(a.classKey).epicBoonLevel === a.classLevel));
        }
        ['subclasses', 'featureChoices', 'spells'].forEach((k) => {
            if (!state[k]) return;
            Object.keys(state[k]).forEach((c) => { if (!lv[c]) delete state[k][c]; });
        });
        if (state.subclasses) Object.keys(state.subclasses).forEach((c) => { if (lv[c] < cls(c).subclassLevels[0]) delete state.subclasses[c]; });
        const first = (state.levels || [])[0] && state.levels[0].classKey;
        if (state.skills) {
            if (first !== oldFirst) state.skills.class = [];
            if (state.skills.multiclass) {
                Object.keys(state.skills.multiclass).forEach((k) => { if (!lv[k] || k === first) delete state.skills.multiclass[k]; });
            }
            if (state.skills.expertise) {
                let need = 0;
                Object.keys(lv).forEach((k) => cls(k).featureChoices.forEach((c) => { if (c.kind === 'expertise' && c.level <= lv[k]) need += c.count || 0; }));
                state.skills.expertise = state.skills.expertise.slice(0, need);
            }
        }
        if (state.featureChoices) {
            Object.keys(state.featureChoices).forEach((k) => {
                cls(k).featureChoices.forEach((c) => {
                    const value = state.featureChoices[k][c.id];
                    if (Array.isArray(value)) state.featureChoices[k][c.id] = value.slice(0, choiceNeed(c, lv[k]));
                    if (c.level > lv[k]) delete state.featureChoices[k][c.id];
                });
            });
        }
        if (state.spells) {
            Object.keys(state.spells).forEach((k) => {
                const row = castingRow(k, lv[k]);
                const sel = state.spells[k];
                if (!row) return;
                const grade = maxGrade(k, lv[k]);
                if (sel.cantrips) sel.cantrips = sel.cantrips.slice(0, row.cantrips);
                if (sel.spellbook) sel.spellbook = sel.spellbook.slice(0, spellbookSize(k, lv[k]));
                if (sel.prepared) {
                    sel.prepared = sel.prepared.filter((s) => app.data.spells[s] && app.data.spells[s].level <= grade && (!sel.spellbook || sel.spellbook.includes(s))).slice(0, row.prepared);
                }
            });
        }
    }

    // ================================================================ KLASSE
    function labelList(items) { return items.filter(Boolean).join(', '); }
    function classPreview(c) {
        const weapons = c.weaponProficiencies.map((g) => (g.category === 'martial' ? 'Kriegswaffen' : 'Einfache Waffen') + (g.requiresProperty ? ` (mit ${g.requiresProperty.join('/')})` : ''));
        return h('div', { class: 'sc-detail' },
            h('h3', { text: c.name }),
            h('dl', null,
                h('dt', { text: 'Trefferwürfel' }), h('dd', { text: `W${c.hitDie}` }),
                h('dt', { text: 'Hauptattribut' }), h('dd', { text: c.primaryAbilities.abilities.map(SC.abilityName).join(c.primaryAbilities.mode === 'any' ? ' oder ' : ' und ') }),
                h('dt', { text: 'Rettungswürfe' }), h('dd', { text: c.savingThrows.map(SC.abilityName).join(', ') }),
                h('dt', { text: 'Rüstungen' }), h('dd', { text: labelList(c.armorProficiencies.map((a) => ARMOR_LABELS[a] || a)) || 'Keine' }),
                h('dt', { text: 'Waffen' }), h('dd', { text: labelList(weapons) }),
                h('dt', { text: 'Fertigkeiten' }), h('dd', { text: `${c.skillChoices.count} aus: ${(c.skillChoices.options ? c.skillChoices.options.map(SC.skillName).join(', ') : 'allen Fertigkeiten')}` }),
                h('dt', { text: 'Zauberwirken' }), h('dd', { text: c.spellcasting ? `Ja (${SC.abilityName(c.spellcasting.ability)})` : 'Nein' }),
                h('dt', { text: 'Merkmale Stufe 1' }), h('dd', { text: c.levels[0].features.map((f) => f.name).join(', ') })),
            SC.detailButton(c.id, 'Klassentext lesen', c.name));
    }

    function setLevelCount(n) {
        const oldFirst = firstClass();
        SC.mutate((state) => {
            state.levels = state.levels || [];
            if (!state.levels.length) return;
            while (state.levels.length < n) state.levels.push({ classKey: state.levels[state.levels.length - 1].classKey, hp: 'fixed' });
            state.levels.length = n;
            prune(state, oldFirst);
        });
    }

    function renderKlasse() {
        const levels = st().levels || [];
        const first = firstClass();
        const wrap = h('div');
        wrap.append(panel(
            h('h3', { text: 'Klasse wählen' }),
            h('div', { class: 'sc-row' },
                h('button', { type: 'button', class: 'sc-btn', id: 'scRandomize', onclick: () => {
                    if (!first || window.confirm('Alle bisherigen Auswahlen werden durch einen Zufallscharakter ersetzt. Fortfahren?')) SC.randomize((st().levels || []).length || 1);
                } }, 'Zufallscharakter würfeln')),
            h('p', { class: 'sc-muted', text: 'Deine erste Klasse bestimmt Rettungswürfe, Rüstungen und Ausgangsausrüstung.' }),
            h('div', { class: 'sc-grid' }, app.data.classes.map((c) => card(c.name, `W${c.hitDie} · ${c.primaryAbilities.abilities.map(SC.abilityAbbr).join(c.primaryAbilities.mode === 'any' ? '/' : '+')}`, first === c.classKey, () => {
                const oldFirst = firstClass();
                SC.mutate((state) => {
                    if (!state.levels || !state.levels.length) state.levels = [{ classKey: c.classKey, hp: 'fixed' }];
                    else state.levels = state.levels.map((l) => (l.classKey === oldFirst ? { ...l, classKey: c.classKey } : l));
                    prune(state, oldFirst);
                });
            }))),
            first ? classPreview(cls(first)) : null));
        if (first) {
            const rows = levels.map((l, i) => {
                const die = cls(l.classKey).hitDie;
                const hpCell = i === 0 ? h('td', { text: `${die} (Maximum)` }) : h('td', null,
                    select(`scHpMode${i}`, [['fixed', `Fest (${die / 2 + 1})`], ['roll', 'Gewürfelt']], l.hp === 'fixed' ? 'fixed' : 'roll', (v) => {
                        SC.mutate((state) => { state.levels[i].hp = v === 'fixed' ? 'fixed' : SC.randInt(die) + 1; });
                    }),
                    l.hp === 'fixed' ? null : [' ', h('input', { type: 'number', min: 1, max: die, value: l.hp, 'aria-label': `Gewürfelter Wert Stufe ${i + 1}`, style: 'width:4.5rem', onchange: (e) => {
                        SC.mutate((state) => { state.levels[i].hp = Math.max(1, Math.min(die, Number(e.target.value) || 1)); });
                    } }), ' ', h('button', { type: 'button', class: 'sc-btn sc-btn-small', onclick: () => SC.mutate((state) => { state.levels[i].hp = SC.randInt(die) + 1; }) }, `W${die} würfeln`)]);
                const classCell = i === 0 ? h('td', { text: cls(l.classKey).name }) : h('td', null, select(`scLvlClass${i}`, app.data.classes.map((c) => [c.classKey, c.name]), l.classKey, (v) => {
                    SC.mutate((state) => { state.levels[i].classKey = v; prune(state, firstClass()); });
                }));
                return h('tr', null, h('td', { text: i + 1 }), classCell, hpCell);
            });
            wrap.append(panel(
                h('h3', { text: 'Stufe und Verlauf' }),
                h('div', { class: 'sc-fields' }, field('Gesamtstufe', h('input', { type: 'number', id: 'scLevel', min: 1, max: app.data.maxLevel, value: levels.length, onchange: (e) => setLevelCount(Math.max(1, Math.min(app.data.maxLevel, Number(e.target.value) || 1))) }), 'scLevel')),
                h('p', { class: 'sc-muted', text: 'Ab Stufe 2 kannst du pro Stufe die Klasse wechseln (Mehrklassigkeit); der Server prüft die Voraussetzungen.' }),
                h('div', { class: 'sc-scroll' }, h('table', { class: 'sc-table' },
                    h('caption', { class: 'sc-muted', text: 'Stufenverlauf' }),
                    h('thead', null, h('tr', null, ['Stufe', 'Klasse', 'Trefferpunkte'].map((t) => h('th', { scope: 'col', text: t })))),
                    h('tbody', null, rows)))));
        }
        return wrap;
    }

    // ================================================================ HERKUNFT
    function speciesChoiceControl(species, choice) {
        const current = ((st().species || {}).choices || {})[choice.id];
        const set = (v) => SC.mutate((state) => {
            state.species = state.species || { id: species.id };
            state.species.choices = state.species.choices || {};
            if (v === '') delete state.species.choices[choice.id]; else state.species.choices[choice.id] = v;
        });
        const id = `scSpc-${choice.id}`;
        let control;
        let note = null;
        if (choice.kind === 'option') {
            const options = choice.options.map((o) => [o.id, o.name + (o.damageType ? ` (${o.damageType})` : '')]);
            control = select(id, options, current, set, 'Bitte wählen');
            const chosen = choice.options.find((o) => o.id === current);
            if (chosen && chosen.description) note = h('p', { class: 'sc-muted', text: chosen.description });
        } else if (choice.kind === 'ability') {
            control = select(id, choice.options.map((a) => [a, SC.abilityName(a)]), current, set, 'Bitte wählen');
        } else if (choice.kind === 'skill') {
            const ids = choice.options || Object.keys(SC.L.skills);
            control = select(id, ids.map((s) => [s, SC.skillName(s)]), current, set, 'Bitte wählen');
        } else if (choice.kind === 'feat-category') {
            control = select(id, app.data.feats.filter((f) => f.category === choice.category).map((f) => [f.id, f.name]), current, set, 'Bitte wählen');
        } else if (choice.kind === 'size') {
            control = select(id, species.sizes.map((s) => [s, s]), current, set, 'Bitte wählen');
        } else {
            control = h('span', { text: 'Nicht unterstützt' });
        }
        return h('div', null, field(choice.label || label(choice.id), control, id), note);
    }

    function homebrewSpeciesDetail(species) {
        const origin = species.origin || {};
        const scope = origin.scope ? `${origin.scope.label}` : '';
        const movement = (origin.movement || []).map((m) => `${m.label} ${m.feet} ft (${fmtMeters(m.meters)})`).join(', ');
        const senses = (origin.senses || []).map((s) => `${s.label} ${s.feet} ft`).join(', ') || 'keine Dunkelsicht';
        return [
            h('p', { class: 'sc-muted', text: `Homebrew · ${scope} · Fassung ${origin.revision || '–'}${origin.author ? ` · von ${origin.author}` : ''}` }),
            h('p', { text: `Bewegung: ${movement} · Sinne: ${senses}` }),
            species.description ? h('p', { class: 'sc-muted', text: species.description }) : null,
            (origin.actions || []).map((a) => h('p', null, h('strong', { text: `${a.name}: ` }), a.summary)),
            (origin.traits || []).map((t) => h('p', null, h('strong', { text: `${t.name}: ` }), t.description)),
        ];
    }

    function backgroundBonusControl(bg) {
        const bonus = (st().background || {}).abilityBonus || {};
        const entries = Object.entries(bonus).filter(([, v]) => v);
        const plusTwo = (entries.find(([, v]) => v === 2) || [])[0] || '';
        const plusOne = entries.filter(([, v]) => v === 1).map(([a]) => a);
        const triple = entries.length === 3 && entries.every(([, v]) => v === 1);
        const mode = triple || (!entries.length && (st().background || {}).bonusMode === 'triple') ? 'triple' : 'split';
        const write = (obj) => SC.mutate((state) => { state.background = state.background || { id: bg.id }; state.background.abilityBonus = obj; });
        const abilityOptions = bg.abilities.map((a) => [a, SC.abilityName(a)]);
        const wrap = h('div', { class: 'sc-panel' }, h('h3', { text: 'Attributsbonus des Hintergrunds' }),
            h('div', { class: 'sc-row', role: 'group', 'aria-label': 'Verteilung' },
                h('button', { type: 'button', class: 'sc-btn sc-btn-toggle', 'aria-pressed': String(mode === 'split'), onclick: () => write({}) }, '+2 und +1'),
                h('button', { type: 'button', class: 'sc-btn sc-btn-toggle', 'aria-pressed': String(mode === 'triple'), onclick: () => write(Object.fromEntries(bg.abilities.map((a) => [a, 1]))) }, 'je +1 auf alle drei')));
        if (mode === 'triple') {
            wrap.append(h('p', { class: 'sc-muted', text: `+1 auf ${bg.abilities.map(SC.abilityName).join(', ')}.` }));
        } else {
            wrap.append(h('div', { class: 'sc-fields' },
                field('+2 auf', select('scBgPlus2', abilityOptions, plusTwo, (v) => {
                    const obj = {};
                    if (v) obj[v] = 2;
                    if (plusOne[0] && plusOne[0] !== v) obj[plusOne[0]] = 1;
                    write(obj);
                }, 'Bitte wählen'), 'scBgPlus2'),
                field('+1 auf', select('scBgPlus1', abilityOptions.filter(([a]) => a !== plusTwo), plusOne[0] || '', (v) => {
                    const obj = {};
                    if (plusTwo) obj[plusTwo] = 2;
                    if (v) obj[v] = 1;
                    write(obj);
                }, 'Bitte wählen'), 'scBgPlus1')));
        }
        return wrap;
    }

    function renderHerkunft() {
        const wrap = h('div');
        const curSpecies = st().species && SC.L.species[st().species.id];
        wrap.append(panel(
            h('h3', { text: 'Spezies' }),
            h('div', { class: 'sc-grid' }, app.data.species.map((s) => card(s.name, `${s.sizes.join('/')} · ${fmtMeters(s.speedMeters)}${s.homebrew ? ` · Homebrew (${(s.origin && s.origin.scope && s.origin.scope.label) || 'veröffentlicht'})` : ''}`, curSpecies && curSpecies.id === s.id, () => {
                SC.mutate((state) => { if (!state.species || state.species.id !== s.id) state.species = { id: s.id, choices: {} }; });
            }))),
            curSpecies ? h('div', { class: 'sc-detail' },
                h('h3', { text: curSpecies.name }),
                h('p', { text: `${curSpecies.creatureType} · Größe ${curSpecies.sizes.join(' oder ')} · Bewegungsrate ${fmtMeters(curSpecies.speedMeters)}${curSpecies.darkvisionMeters ? ` · Dunkelsicht ${curSpecies.darkvisionMeters} m` : ''}` }),
                h('p', null, h('strong', { text: 'Merkmale: ' }), curSpecies.traits.join(', ')),
                curSpecies.homebrew ? homebrewSpeciesDetail(curSpecies) : SC.detailButton(curSpecies.id, 'Spezies-Text lesen', curSpecies.name),
                curSpecies.choices.map((c) => speciesChoiceControl(curSpecies, c))) : null));
        const curBg = st().background && SC.L.backgrounds[st().background.id];
        wrap.append(panel(
            h('h3', { text: 'Hintergrund' }),
            h('div', { class: 'sc-grid' }, app.data.backgrounds.map((b) => card(b.name, `${b.feat} · ${b.skills.map(SC.skillName).join(', ')}`, curBg && curBg.id === b.id, () => {
                SC.mutate((state) => { if (!state.background || state.background.id !== b.id) state.background = { id: b.id, abilityBonus: {} }; });
            }))),
            curBg ? h('div', { class: 'sc-detail' },
                h('h3', { text: curBg.name }),
                h('p', null, h('strong', { text: 'Attribute: ' }), curBg.abilities.map(SC.abilityName).join(', ')),
                h('p', null, h('strong', { text: 'Herkunftstalent: ' }), curBg.feat + (curBg.featChoice ? ` (${curBg.featChoice})` : '')),
                h('p', null, h('strong', { text: 'Fertigkeiten: ' }), curBg.skills.map(SC.skillName).join(', ')),
                h('p', null, h('strong', { text: 'Werkzeug: ' }), SC.itemName(curBg.tool)),
                SC.detailButton(curBg.id, 'Hintergrund-Text lesen', curBg.name),
                curBg.featChoice ? h('p', { class: 'sc-muted', text: 'Die Detailwahl des Herkunftstalents (z. B. die Zauberauswahl) wird noch nicht abgebildet.' }) : null) : null));
        if (curBg) wrap.append(backgroundBonusControl(curBg));
        return wrap;
    }

    // ================================================================ ATTRIBUTE
    function abilityBase() { return st().abilityBase || {}; }
    function setBase(a, value) { SC.mutate((state) => { state.abilityBase = state.abilityBase || {}; state.abilityBase[a] = value; }); }

    function abilitySummaryCell(a) {
        const e = ev() && ev().abilities[a];
        if (!e) return null;
        return h('div', { class: 'sc-muted' },
            e.bonus ? `Basis ${e.base} ${sign(e.bonus)} Boni = ` : null, h('span', { class: 'sc-total' }, `${e.score}`), ` (${sign(e.modifier)})`);
    }

    function methodControls(method) {
        const d = app.data.abilityScoreMethods;
        const base = abilityBase();
        const grid = h('div', { class: 'sc-abil-grid' });
        if (method === 'standard-array') {
            const values = d.standardArray.values;
            ABIL.forEach((a) => {
                const taken = ABIL.filter((o) => o !== a).map((o) => base[o]);
                const options = values.filter((v) => !taken.includes(v) || v === base[a]);
                grid.append(h('div', { class: 'sc-abil' }, h('h4', { text: SC.abilityName(a) }),
                    select(`scBase-${a}`, options.map((v) => [v, v]), base[a], (v) => setBase(a, v === '' ? undefined : Number(v)), '–'), abilitySummaryCell(a)));
            });
        } else if (method === 'point-buy') {
            const costs = d.pointBuy.costs;
            let spent = 0;
            ABIL.forEach((a) => { spent += costs[String(base[a] == null ? 8 : base[a])] || 0; });
            ABIL.forEach((a) => {
                const v = base[a] == null ? 8 : base[a];
                grid.append(h('div', { class: 'sc-abil' }, h('h4', { text: SC.abilityName(a) }),
                    h('div', { class: 'sc-stepper' },
                        h('button', { type: 'button', class: 'sc-btn sc-btn-small', 'aria-label': `${SC.abilityName(a)} senken`, disabled: v <= d.pointBuy.minScore, onclick: () => setBase(a, v - 1) }, '−'),
                        h('output', { 'aria-label': SC.abilityName(a), text: v }),
                        h('button', { type: 'button', class: 'sc-btn sc-btn-small', 'aria-label': `${SC.abilityName(a)} erhöhen`, disabled: v >= d.pointBuy.maxScore || spent - (costs[String(v)] || 0) + (costs[String(v + 1)] || 0) > d.pointBuy.budget, onclick: () => setBase(a, v + 1) }, '+')),
                    abilitySummaryCell(a)));
            });
            grid.prepend(h('p', { class: spent === d.pointBuy.budget ? 'sc-ok-note' : 'sc-muted', role: 'status', text: `${d.pointBuy.budget - spent} von ${d.pointBuy.budget} Punkten übrig`, style: 'grid-column:1/-1' }));
        } else if (method === 'roll') {
            const rolls = st().abilityRolls || [];
            const totals = rolls.length === 6 ? rolls.map((r) => r.reduce((x, y) => x + y, 0) - Math.min(...r)) : [];
            grid.append(h('div', { style: 'grid-column:1/-1' },
                h('div', { class: 'sc-row' },
                    h('button', { type: 'button', class: 'sc-btn sc-btn-primary', id: 'scRollAll', onclick: () => SC.mutate((state) => {
                        state.abilityRolls = Array.from({ length: 6 }, () => Array.from({ length: 4 }, () => SC.randInt(6) + 1));
                        state.abilityBase = {};
                    }) }, rolls.length ? 'Alles neu würfeln' : 'Sechsmal 4W6 würfeln'),
                    h('span', { class: 'sc-muted', text: 'Der niedrigste Würfel jedes Wurfs zählt nicht. Du kannst die Würfel auch von echten Würfeln abtippen.' })),
                rolls.length ? h('div', { class: 'sc-scroll' }, h('table', { class: 'sc-table' },
                    h('caption', { class: 'sc-muted', text: 'Würfelergebnisse' }),
                    h('thead', null, h('tr', null, ['Wurf', 'Würfel', 'Summe'].map((t) => h('th', { scope: 'col', text: t })))),
                    h('tbody', null, rolls.map((r, i) => h('tr', null, h('td', { text: i + 1 }),
                        h('td', null, r.map((die, j) => h('input', { type: 'number', min: 1, max: 6, value: die, style: 'width:3.6rem', 'aria-label': `Wurf ${i + 1}, Würfel ${j + 1}`, onchange: (e) => {
                            SC.mutate((state) => { state.abilityRolls[i][j] = Math.max(1, Math.min(6, Number(e.target.value) || 1)); state.abilityBase = {}; });
                        } }))),
                        h('td', { text: totals[i] })))))) : null));
            if (totals.length) {
                const remaining = totals.slice();
                ABIL.forEach((a) => { const idx = remaining.indexOf(base[a]); if (idx >= 0) remaining.splice(idx, 1); });
                ABIL.forEach((a) => {
                    const pool = remaining.slice();
                    if (base[a] != null) pool.push(base[a]);
                    const options = Array.from(new Set(pool)).sort((x, y) => y - x);
                    grid.append(h('div', { class: 'sc-abil' }, h('h4', { text: SC.abilityName(a) }),
                        select(`scBase-${a}`, options.map((v) => [v, v]), base[a], (v) => setBase(a, v === '' ? undefined : Number(v)), '–'), abilitySummaryCell(a)));
                });
            }
        } else if (method === 'manual') {
            ABIL.forEach((a) => {
                grid.append(h('div', { class: 'sc-abil' }, h('h4', { text: SC.abilityName(a) }),
                    h('input', { type: 'number', id: `scBase-${a}`, min: 1, max: 20, value: base[a] == null ? '' : base[a], 'aria-label': SC.abilityName(a), onchange: (e) => setBase(a, e.target.value === '' ? undefined : Number(e.target.value)) }),
                    abilitySummaryCell(a)));
            });
        }
        return grid;
    }

    function renderAttribute() {
        const method = st().abilityMethod;
        const methods = [['standard-array', 'Standardsatz'], ['point-buy', 'Punktekauf'], ['roll', 'Würfeln (4W6)'], ['manual', 'Manuell']];
        const c = firstClass() && cls(firstClass());
        const wrap = panel(
            h('h3', { text: 'Attributswerte' }),
            h('div', { class: 'sc-row', role: 'group', 'aria-label': 'Methode' }, methods.map(([id, text]) =>
                h('button', { type: 'button', class: 'sc-btn sc-btn-toggle', 'aria-pressed': String(method === id), onclick: () => SC.mutate((state) => {
                    if (state.abilityMethod === id) return;
                    state.abilityMethod = id;
                    state.abilityBase = {};
                    if (id === 'point-buy') ABIL.forEach((a) => { state.abilityBase[a] = 8; });
                    if (id === 'manual') ABIL.forEach((a) => { state.abilityBase[a] = 10; });
                }) }, text))),
            c ? h('p', { class: 'sc-muted', text: `${c.name}: Hauptattribut ${c.primaryAbilities.abilities.map(SC.abilityName).join(c.primaryAbilities.mode === 'any' ? ' oder ' : ' und ')}.` }) : null,
            c && method === 'standard-array' ? h('button', { type: 'button', class: 'sc-btn', id: 'scRecommend', onclick: () => SC.mutate((state) => { state.abilityBase = { ...c.standardAbilityScores }; }) }, `Empfehlung für ${c.name} übernehmen`) : null,
            method ? methodControls(method) : h('p', { class: 'sc-muted', text: 'Wähle zuerst eine Methode.' }),
            h('p', { class: 'sc-muted', text: 'Boni aus Hintergrund und Attributswerterhöhungen werden automatisch addiert.' }));
        return wrap;
    }

    // ================================================================ WAHLEN
    function renderSkills() {
        const first = firstClass();
        if (!first) return panel(h('h3', { text: 'Fertigkeiten' }), h('p', { class: 'sc-muted', text: 'Wähle zuerst eine Klasse.' }));
        const c = cls(first);
        const bg = st().background && SC.L.backgrounds[st().background.id];
        const fromBg = bg ? bg.skills : [];
        const chosen = (st().skills || {}).class || [];
        const set = (key, list) => SC.mutate((state) => { state.skills = state.skills || {}; state.skills[key] = list; });
        const options = SC.util.classSkillOptions(c).map((id) => ({ id, name: SC.skillName(id), sub: fromBg.includes(id) ? 'bereits durch Hintergrund' : null }));
        const wrap = panel(h('h3', { text: `Fertigkeiten (${c.name})` }),
            bg ? h('p', null, h('strong', { text: 'Vom Hintergrund: ' }), fromBg.map(SC.skillName).join(', ')) : h('p', { class: 'sc-muted', text: 'Hintergrund noch nicht gewählt.' }),
            counter(chosen.length, c.skillChoices.count),
            countedList(options, chosen, c.skillChoices.count, (next) => set('class', next), 'Klassenfertigkeiten'));
        classOrder().slice(1).forEach((key) => {
            const grant = cls(key).multiclassGrants.skillChoices;
            if (!grant) return;
            const picked = ((st().skills || {}).multiclass || {})[key] || [];
            const pool = grant.from === 'class' ? SC.util.classSkillOptions(cls(key)) : Object.keys(SC.L.skills);
            const options = pool.map((id) => ({ id, name: SC.skillName(id) }));
            wrap.append(h('h3', { text: `Mehrklassigkeit: ${cls(key).name}` }), counter(picked.length, grant.count),
                countedList(options, picked, grant.count, (next) => SC.mutate((state) => {
                    state.skills = state.skills || {};
                    state.skills.multiclass = { ...(state.skills.multiclass || {}), [key]: next };
                }), `Fertigkeit durch ${cls(key).name}`));
        });
        const need = expectedExpertise();
        if (need) {
            const prof = Object.entries((ev() || { skills: {} }).skills).filter(([, v]) => v.proficiency !== 'none').map(([id, v]) => ({ id, name: v.name }));
            const exp = (st().skills || {}).expertise || [];
            wrap.append(h('h3', { text: 'Expertise' }), counter(exp.length, need), countedList(prof, exp, need, (next) => set('expertise', next), 'Expertise'));
        }
        const other = (st().skills || {}).other || [];
        wrap.append(h('details', null, h('summary', { text: 'Weitere Fertigkeitsübungen (z. B. aus Talenten)' }),
            countedList(Object.values(SC.L.skills).map((s) => ({ id: s.id, name: s.name })), other, 99, (next) => set('other', next), 'Weitere Fertigkeiten')));
        return wrap;
    }

    function renderSubclasses() {
        const lv = levelsByClass();
        const keys = classOrder();
        if (!keys.length) return null;
        return panel(h('h3', { text: 'Unterklassen' }), keys.map((key) => {
            const c = cls(key);
            const unlock = c.subclassLevels[0];
            if (lv[key] < unlock) return h('p', { class: 'sc-muted', text: `${c.name}: Unterklasse ab Stufe ${unlock}.` });
            const cur = (st().subclasses || {})[key];
            return h('div', null, h('h4', { text: c.name }),
                h('div', { class: 'sc-grid' }, c.subclasses.map((id) => card(SC.subclassName(id), null, cur === id, () => SC.mutate((state) => { state.subclasses = state.subclasses || {}; state.subclasses[key] = id; })))),
                cur ? SC.detailButton(cur, 'Unterklassen-Text lesen', SC.subclassName(cur)) : null);
        }));
    }

    function featureChoiceControl(key, choice, classLevel) {
        const value = ((st().featureChoices || {})[key] || {})[choice.id];
        const set = (v) => SC.mutate((state) => {
            state.featureChoices = state.featureChoices || {};
            state.featureChoices[key] = state.featureChoices[key] || {};
            if (v === '' || v == null) delete state.featureChoices[key][choice.id]; else state.featureChoices[key][choice.id] = v;
        });
        const c = cls(key);
        if (choice.kind === 'option') {
            return h('div', null, h('h4', { text: `${label(choice.id)} (ab Stufe ${choice.level})` }),
                h('div', { class: 'sc-grid' }, Object.entries(choice.options).map(([id, rule]) => card(OPTION_LABELS[id] || id, null, value === id, () => set(id),
                    null))),
                value ? SC.detailButton(choice.options[value], 'Regeltext', OPTION_LABELS[value] || value) : null);
        }
        if (choice.kind === 'feat-category') {
            const feats = app.data.feats.filter((f) => f.category.startsWith(choice.category));
            return h('div', null, field(`${label(choice.id)} (${choice.category})`, select(`scFc-${key}-${choice.id}`, feats.map((f) => [f.id, f.name]), value, set, 'Bitte wählen'), `scFc-${key}-${choice.id}`),
                value ? SC.detailButton(value, 'Regeltext', SC.L.feats[value].name) : null);
        }
        const need = choiceNeed(choice, classLevel);
        const picks = Array.isArray(value) ? value : [];
        let options = [];
        if (choice.kind === 'weapon-mastery') {
            options = app.data.equipment.weapons.filter((w) => weaponAllowed(c, w) && (!/-melee$/.test(choice.weapons || '') || w.kind === 'melee')).map((w) => ({ id: w.id, name: w.name, sub: w.mastery }));
        } else if (choice.kind === 'class-option') {
            options = app.data.classOptions.filter((o) => o.classKey === key && o.kind === choice.optionKind && (o.minClassLevel || 1) <= classLevel)
                .map((o) => ({ id: o.id, name: o.name, sub: [o.prerequisite, o.cost].filter(Boolean).join(' · ') || null, detail: o.id }));
        } else if (choice.kind === 'language') {
            options = app.data.languages.filter((l) => !l.automatic).map((l) => ({ id: l.id, name: l.name }));
        }
        const elsewhere = Object.entries((st().featureChoices || {})[key] || {}).filter(([id, v]) => id !== choice.id && Array.isArray(v)).flatMap(([, v]) => v);
        options = options.filter((o) => !elsewhere.includes(o.id));
        return h('div', null, h('h4', { text: label(choice.id) }), counter(picks.length, need),
            countedList(options, picks, need, (next) => set(next), label(choice.id)));
    }

    function renderFeatureChoices() {
        const lv = levelsByClass();
        const blocks = [];
        classOrder().forEach((key) => {
            const list = cls(key).featureChoices.filter((c) => c.kind !== 'expertise' && c.level <= lv[key]);
            if (list.length) blocks.push(h('div', null, h('h3', { text: `${cls(key).name}: Klassenmerkmale` }), list.map((c) => featureChoiceControl(key, c, lv[key]))));
        });
        return blocks.length ? panel(blocks) : null;
    }

    function advancementSlots() {
        const lv = levelsByClass();
        const slots = [];
        classOrder().forEach((key) => {
            const c = cls(key);
            c.asiLevels.concat([c.epicBoonLevel]).forEach((level) => { if (level <= lv[key]) slots.push({ key, level, epic: level === c.epicBoonLevel }); });
        });
        return slots;
    }

    function renderAdvancement(slot) {
        const list = st().advancements || [];
        const idx = list.findIndex((a) => a.classKey === slot.key && a.classLevel === slot.level);
        const adv = idx >= 0 ? list[idx] : null;
        const write = (fn) => SC.mutate((state) => {
            state.advancements = state.advancements || [];
            let entry = state.advancements.find((a) => a.classKey === slot.key && a.classLevel === slot.level);
            if (!entry) { entry = { classKey: slot.key, classLevel: slot.level }; state.advancements.push(entry); }
            fn(entry);
        });
        const idp = `scAdv-${slot.key}-${slot.level}`;
        const kind = adv && adv.kind;
        const wrap = h('div', { class: 'sc-detail' }, h('h4', { text: `${cls(slot.key).name}, Stufe ${slot.level}: ${slot.epic ? 'Epische Gabe' : 'Attributswerterhöhung oder Talent'}` }),
            h('div', { class: 'sc-row', role: 'group', 'aria-label': 'Art' },
                h('button', { type: 'button', class: 'sc-btn sc-btn-toggle', 'aria-pressed': String(kind === 'asi'), onclick: () => write((e) => { e.kind = 'asi'; e.increases = {}; delete e.featId; delete e.increaseAbility; }) }, 'Attributswerterhöhung'),
                h('button', { type: 'button', class: 'sc-btn sc-btn-toggle', 'aria-pressed': String(kind === 'feat'), onclick: () => write((e) => { e.kind = 'feat'; delete e.increases; }) }, slot.epic ? 'Epische Gabe' : 'Talent')));
        if (kind === 'asi') {
            const inc = adv.increases || {};
            const plusTwo = (Object.entries(inc).find(([, v]) => v === 2) || [])[0];
            const ones = Object.entries(inc).filter(([, v]) => v === 1).map(([a]) => a);
            const mode = plusTwo ? 'two' : (ones.length ? 'ones' : (adv.mode || 'two'));
            const setInc = (obj, m) => write((e) => { e.increases = obj; e.mode = m; });
            wrap.append(h('div', { class: 'sc-row' },
                h('button', { type: 'button', class: 'sc-btn sc-btn-small sc-btn-toggle', 'aria-pressed': String(mode === 'two'), onclick: () => setInc({}, 'two') }, '+2 auf ein Attribut'),
                h('button', { type: 'button', class: 'sc-btn sc-btn-small sc-btn-toggle', 'aria-pressed': String(mode === 'ones'), onclick: () => setInc({}, 'ones') }, '+1 auf zwei Attribute')));
            if (mode === 'two') {
                wrap.append(field('+2 auf', select(`${idp}-a`, ABIL.map((a) => [a, SC.abilityName(a)]), plusTwo, (v) => setInc(v ? { [v]: 2 } : {}, 'two'), 'Bitte wählen'), `${idp}-a`));
            } else {
                const mk = (n) => field(`+1 auf (${n + 1})`, select(`${idp}-o${n}`, ABIL.filter((a) => a === ones[n] || !ones.includes(a)).map((a) => [a, SC.abilityName(a)]), ones[n], (v) => {
                    const next = ones.slice();
                    if (v) next[n] = v; else next.splice(n, 1);
                    setInc(Object.fromEntries(next.filter(Boolean).map((a) => [a, 1])), 'ones');
                }, 'Bitte wählen'), `${idp}-o${n}`);
                wrap.append(h('div', { class: 'sc-fields' }, mk(0), mk(1)));
            }
        } else if (kind === 'feat') {
            const category = slot.epic ? 'Epische-Gabe-Talent' : 'Allgemeines Talent';
            const feats = app.data.feats.filter((f) => f.category === category && f.id !== 'feats.descriptions.ability-score-improvement');
            wrap.append(field('Talent', select(`${idp}-f`, feats.map((f) => [f.id, f.name + (f.prerequisite && f.prerequisite.raw ? ` (${f.prerequisite.raw})` : '')]), adv.featId, (v) => write((e) => { e.featId = v || undefined; delete e.increaseAbility; }), 'Bitte wählen'), `${idp}-f`));
            const feat = adv.featId && SC.L.feats[adv.featId];
            if (feat) {
                wrap.append(SC.detailButton(feat.id, 'Talent-Text lesen', feat.name));
                if (feat.abilityIncrease) {
                    const allowed = feat.abilityIncrease.abilities === 'any' ? ABIL : feat.abilityIncrease.abilities;
                    wrap.append(field(`${feat.name}: +1 auf`, select(`${idp}-i`, allowed.map((a) => [a, SC.abilityName(a)]), adv.increaseAbility, (v) => write((e) => { e.increaseAbility = v || undefined; }), 'Bitte wählen'), `${idp}-i`));
                }
            }
        }
        return wrap;
    }

    function renderWahlen() {
        const wrap = h('div');
        wrap.append(renderSkills());
        [renderSubclasses(), renderFeatureChoices()].forEach((n) => { if (n) wrap.append(n); });
        const slots = advancementSlots();
        if (slots.length) wrap.append(panel(h('h3', { text: 'Attributswerterhöhungen und Talente' }), slots.map(renderAdvancement)));
        return wrap;
    }

    // ================================================================ AUSRÜSTUNG
    function packageContents(items) {
        return h('ul', null, items.map((i) => {
            if (i.kind === 'coins') return h('li', { text: `${i.amount} ${i.coin}` });
            if (i.kind === 'choice') return h('li', { text: `${i.quantity}× ${i.category === 'holy-symbol' ? 'Heiliges Symbol (nach Wahl)' : i.category}` });
            return h('li', { text: `${i.quantity}× ${SC.itemName(i.itemId)}${i.variant ? ` (${i.variant})` : ''}` });
        }));
    }
    function packageChooser(title, source, key) {
        const cur = (st().equipment || {})[key];
        const set = (v) => SC.mutate((state) => { state.equipment = state.equipment || {}; state.equipment[key] = v; });
        return h('div', null, h('h4', { text: title }),
            h('div', { class: 'sc-grid' }, ['A', 'B'].map((p) => h('div', null, card(`Paket ${p}`, p === 'B' ? 'Nur Gold' : 'Ausrüstung', cur === p, () => set(p)), packageContents(source[p] || [])))));
    }

    function renderAusruestung() {
        const wrap = h('div');
        const first = firstClass();
        const bg = st().background && SC.L.backgrounds[st().background.id];
        wrap.append(panel(h('h3', { text: 'Ausgangsausrüstung' }),
            first ? packageChooser(`Klasse: ${cls(first).name}`, cls(first).startingEquipment, 'classPackage') : h('p', { class: 'sc-muted', text: 'Wähle zuerst eine Klasse.' }),
            bg ? packageChooser(`Hintergrund: ${bg.name}`, bg.startingEquipment, 'backgroundPackage') : null,
            h('p', { class: 'sc-muted', text: 'Hinweis: Das Inventar wird erst mit dem Charakterbogen aufgebaut; hier hältst du die Wahl der Pakete fest.' })));
        const equip = st().equipment || {};
        const armors = app.data.equipment.armor.filter((a) => a.category !== 'shield');
        const classTrained = (cat) => {
            const lv = levelsByClass();
            return classOrder().some((k, i) => (i === 0 ? cls(k).armorProficiencies.includes(cat) : (cls(k).multiclassGrants.armor || []).includes(cat)));
        };
        const set = (key, value) => SC.mutate((state) => { state.equipment = state.equipment || {}; if (value === '' || value === false) delete state.equipment[key]; else state.equipment[key] = value; });
        wrap.append(panel(h('h3', { text: 'Rüstung und Schild' }),
            h('div', { class: 'sc-fields' },
                field('Getragene Rüstung', select('scArmor', armors.map((a) => [a.id, `${a.name} (RK ${a.base}${a.dex === 'none' ? '' : a.dex === 'capped' ? ` + GES max. ${a.dexCap}` : ' + GES'})${classTrained(a.category) ? '' : ' – ungeübt'}`]), equip.armor, (v) => set('armor', v), 'Keine Rüstung'), 'scArmor')),
            checkRow('Schild führen (+2 RK)', !!equip.shield, false, (checked) => set('shield', checked), classTrained('shield') ? null : 'Du bist mit Schilden nicht vertraut.'),
            ev() ? h('p', null, h('strong', { text: `Rüstungsklasse ${ev().armorClass.value}` }), h('span', { class: 'sc-muted', text: ` · ${ev().armorClass.formula}` })) : null));
        const level = (ev() && ev().level) || 1;
        if (level > 1) {
            const row = app.data.startingEquipmentByLevel.find((r) => level >= r.fromLevel && level <= r.toLevel);
            if (row) wrap.append(panel(h('h3', { text: `Ausrüstung für Stufe ${level}` }), h('p', { text: `Zusätzliches Gold: ${row.baseGold} GM${row.rolledGold ? ` oder gewürfelt (${row.rolledGold.dice}W${row.rolledGold.sides} × ${row.rolledGold.multiplier})` : ''} · Magische Gegenstände: ${row.magicItems}` })));
        }
        return wrap;
    }

    // ================================================================ ZAUBER
    let spellFilter = { text: '', level: '' };

    function spellPicker(key, listName, count, options, max) {
        const sel = ((st().spells || {})[key] || {})[listName] || [];
        const set = (next) => SC.mutate((state) => { state.spells = state.spells || {}; state.spells[key] = state.spells[key] || {}; state.spells[key][listName] = next; });
        const full = sel.length >= max;
        const items = options.map((id) => {
            const s = app.data.spells[id];
            const on = sel.includes(id);
            const row = checkRow(s.name, on, !on && full, (checked) => set(checked ? sel.concat(id) : sel.filter((x) => x !== id)), `${s.level === 0 ? 'Zaubertrick' : `${s.level}. Grad`}${s.ritual ? ' · Ritual' : ''}`, id);
            row.dataset.name = s.name.toLowerCase();
            row.dataset.level = String(s.level);
            return row;
        });
        const list = h('div', { class: 'sc-choice-list', role: 'group', 'aria-label': listName }, items);
        applyFilter(list);
        return h('div', null, counter(sel.length, max), list);
    }
    function applyFilter(list) {
        list.querySelectorAll('[data-name]').forEach((row) => {
            const textOk = !spellFilter.text || row.dataset.name.includes(spellFilter.text);
            const levelOk = spellFilter.level === '' || row.dataset.level === spellFilter.level;
            row.hidden = !(textOk && levelOk);
        });
    }

    function renderZauber() {
        const lv = levelsByClass();
        const casters = classOrder().filter((k) => cls(k).spellcasting);
        if (!casters.length) return panel(h('h3', { text: 'Zauber' }), h('p', { class: 'sc-muted', text: 'Deine gewählten Klassen wirken auf diesen Stufen keine Zauber.' }));
        const wrap = h('div');
        wrap.append(panel(
            h('h3', { text: 'Zauber filtern' }),
            h('div', { class: 'sc-fields' },
                field('Suche', h('input', { type: 'search', id: 'scSpellSearch', value: spellFilter.text, oninput: (e) => { spellFilter.text = e.target.value.toLowerCase(); wrap.querySelectorAll('.sc-choice-list').forEach(applyFilter); } }), 'scSpellSearch'),
                field('Grad', select('scSpellLevel', [['0', 'Zaubertricks'], ...Array.from({ length: 9 }, (_, i) => [String(i + 1), `${i + 1}. Grad`])], spellFilter.level, (v) => { spellFilter.level = v; wrap.querySelectorAll('.sc-choice-list').forEach(applyFilter); }, 'Alle'), 'scSpellLevel')),
            ev() && ev().spellcasting.slots ? h('p', null, h('strong', { text: 'Zauberplätze: ' }), ev().spellcasting.slots.map((n, i) => (n ? `${i + 1}. Grad ×${n}` : null)).filter(Boolean).join(' · ')) : null,
            ev() && ev().spellcasting.pact ? h('p', null, h('strong', { text: 'Paktmagie: ' }), `${ev().spellcasting.pact.slots} Plätze, ${ev().spellcasting.pact.grade}. Grad`) : null));
        casters.forEach((key) => {
            const c = cls(key);
            const row = castingRow(key, lv[key]);
            const info = ev() && ev().spellcasting.classes[key];
            const grade = maxGrade(key, lv[key]);
            const list = app.data.spellLists[key] || [];
            const cantrips = list.filter((id) => app.data.spells[id].level === 0);
            const leveled = list.filter((id) => app.data.spells[id].level >= 1 && app.data.spells[id].level <= grade);
            const book = c.spellcasting.preparation.mode === 'spellbook';
            const sel = (st().spells || {})[key] || {};
            const prepPool = book ? leveled.filter((id) => (sel.spellbook || []).includes(id)) : leveled;
            wrap.append(panel(
                h('h3', { text: `${c.name}: Zauber` }),
                info ? h('p', { class: 'sc-muted', text: `Zauberattribut ${SC.abilityName(info.ability)} · Zauber-SG ${info.saveDc} · Zauberangriff ${sign(info.attackBonus)}` }) : null,
                h('h4', { text: 'Zaubertricks' }), spellPicker(key, 'cantrips', row.cantrips, cantrips, row.cantrips),
                book ? [h('h4', { text: 'Zauberbuch' }), spellPicker(key, 'spellbook', null, leveled, spellbookSize(key, lv[key]))] : null,
                h('h4', { text: book ? 'Vorbereitete Zauber (aus dem Zauberbuch)' : 'Vorbereitete Zauber' }), spellPicker(key, 'prepared', row.prepared, prepPool, row.prepared)));
        });
        wrap.append(h('p', { class: 'sc-muted', text: 'Hinweis: Zauber aus Spezies-Abstammungen (z. B. Elf, Tiefling) werden noch nicht automatisch eingetragen.' }));
        return wrap;
    }

    // ================================================================ BESCHREIBUNG
    function renderBeschreibung() {
        const idn = st().identity || {};
        const setText = (key) => (e) => SC.mutate((state) => { state.identity = state.identity || {}; state.identity[key] = e.target.value; }, { render: 'none' });
        const input = (key, text) => field(text, h('input', { type: 'text', id: `scId-${key}`, maxLength: 100, value: idn[key] || '', oninput: setText(key) }), `scId-${key}`);
        const area = (key, text) => field(text, h('textarea', { id: `scId-${key}`, maxLength: 8000, value: idn[key] || '', oninput: setText(key) }), `scId-${key}`);
        return panel(
            h('h3', { text: 'Wer ist dein Charakter?' }),
            h('div', { class: 'sc-fields' },
                input('name', 'Name'), input('pronouns', 'Pronomen'),
                field('Gesinnung', select('scId-alignment', app.data.alignments.map((a) => [a.id, a.name]), idn.alignment, (v) => SC.mutate((state) => { state.identity = state.identity || {}; if (v) state.identity.alignment = v; else delete state.identity.alignment; }, { render: 'none' }), 'Keine Angabe'), 'scId-alignment'),
                input('age', 'Alter'), input('height', 'Größe'), input('weight', 'Gewicht'), input('eyes', 'Augen'), input('hair', 'Haare'), input('skin', 'Haut'), input('faith', 'Glaube')),
            area('appearance', 'Aussehen'), area('traits', 'Persönlichkeitsmerkmale'), area('ideals', 'Ideale'), area('bonds', 'Bindungen'), area('flaws', 'Makel'), area('backstory', 'Hintergrundgeschichte'), area('notes', 'Notizen'));
    }

    // ================================================================ PRÜFUNG
    const overrideKeys = () => [
        ['hp.max', 'Maximale Trefferpunkte'], ['armorClass', 'Rüstungsklasse'], ['speed', 'Bewegungsrate (m)'], ['initiative', 'Initiative'],
        ['proficiencyBonus', 'Übungsbonus'], ['passivePerception', 'Passive Wahrnehmung'], ['spellSaveDc', 'Zauber-SG'], ['spellAttack', 'Zauberangriff'],
        ...ABIL.map((a) => [`ability.${a}`, `${SC.abilityName(a)} (Wert)`]),
    ];

    function renderOverrides() {
        const ov = st().overrides || {};
        const write = (key, fn) => SC.mutate((state) => {
            state.overrides = state.overrides || {};
            const entry = state.overrides[key] || { set: 0, reason: '' };
            fn(entry);
            if (entry === null) delete state.overrides[key]; else state.overrides[key] = entry;
        });
        const rows = Object.entries(ov).map(([key, spec]) => {
            const name = (overrideKeys().find(([k]) => k === key) || [key, key])[1];
            const applied = ev() && ev().overrides.find((o) => o.key === key);
            return h('tr', null,
                h('td', { text: name }),
                h('td', { text: applied ? applied.computed : '–' }),
                h('td', null, h('input', { type: 'number', step: key === 'speed' ? '0.5' : '1', value: spec.set != null ? spec.set : '', 'aria-label': `${name}: neuer Wert`, onchange: (e) => write(key, (en) => { en.set = Number(e.target.value); delete en.add; }) })),
                h('td', null, h('input', { type: 'text', maxLength: 200, value: spec.reason || '', 'aria-label': `${name}: Begründung`, onchange: (e) => write(key, (en) => { en.reason = e.target.value; }) })),
                h('td', null, h('button', { type: 'button', class: 'sc-btn sc-btn-small sc-btn-danger', onclick: () => SC.mutate((state) => { delete state.overrides[key]; }) }, 'Entfernen')));
        });
        const available = overrideKeys().filter(([k]) => !(k in ov));
        return panel(h('h3', { text: 'Manuelle Überschreibungen' }),
            h('p', { class: 'sc-muted', text: 'Nur für Hausregeln und Sonderfälle. Überschriebene Werte werden im Bogen markiert; die berechneten Werte bleiben nachvollziehbar.' }),
            rows.length ? h('div', { class: 'sc-scroll' }, h('table', { class: 'sc-table' },
                h('thead', null, h('tr', null, ['Wert', 'Berechnet', 'Neuer Wert', 'Begründung', ''].map((t) => h('th', { scope: 'col', text: t })))),
                h('tbody', null, rows))) : null,
            available.length ? h('div', { class: 'sc-row' },
                select('scOvAdd', available, '', (v) => { if (v) write(v, (en) => { en.set = ev() ? currentComputed(v) : 0; en.reason = ''; }); }, 'Überschreibung hinzufügen …')) : null);
    }
    function currentComputed(key) {
        const e = ev();
        const raw = { 'hp.max': e.hitPoints.max, armorClass: e.armorClass.value, speed: e.speedMeters, initiative: e.initiative, proficiencyBonus: e.proficiencyBonus, passivePerception: e.passivePerception };
        if (key in raw) return raw[key];
        if (key.startsWith('ability.')) return e.abilities[key.split('.')[1]].score;
        const casting = Object.values(e.spellcasting.classes)[0];
        return casting ? (key === 'spellSaveDc' ? casting.saveDc : casting.attackBonus) : 0;
    }

    function renderFinalize() {
        const box = h('div', { class: 'sc-panel', id: 'scFinalize' }, h('h3', { text: 'Charakter erstellen' }));
        const blockers = app.blockers || [];
        const name = ((st().identity || {}).name || '').trim();
        box.append(
            field('Name', h('input', { type: 'text', id: 'scFinalName', maxLength: 100, value: name, oninput: (e) => {
                SC.mutate((state) => { state.identity = state.identity || {}; state.identity.name = e.target.value; }, { render: 'none' });
            } }), 'scFinalName'));
        const campaignSelect = h('select', { id: 'scFinalCampaign' }, h('option', { value: '', text: 'Keiner Kampagne zuordnen' }));
        SC.loadCampaigns().then((list) => list.forEach((c) => campaignSelect.append(h('option', { value: c.id, text: c.name || c.title || `Kampagne ${c.id}` }))));
        box.append(field('Kampagne (optional)', campaignSelect, 'scFinalCampaign'));
        const result = h('div', { id: 'scFinalResult', role: 'status', 'aria-live': 'polite' });
        const button = h('button', { type: 'button', class: 'sc-btn sc-btn-primary', id: 'scFinalize-btn', disabled: blockers.length > 0, onclick: async () => {
            button.disabled = true;
            result.textContent = 'Wird erstellt …';
            const res = await SC.finalize(campaignSelect.value || null);
            if (res.ok) {
                result.textContent = '';
                result.append(h('p', { class: 'sc-ok-note', text: `Charakter „${res.data.character.name}“ wurde erstellt.` }),
                    h('div', { class: 'sc-row' },
                        h('a', { class: 'sc-btn sc-btn-primary', href: `/character-sheet?id=${res.data.character.id}`, text: 'Zum Charakterbogen' }),
                        h('a', { class: 'sc-btn', href: '/characters', text: 'Zu meinen Charakteren' }),
                        h('a', { class: 'sc-btn', href: '/srd-creator', text: 'Weiteren Charakter erstellen' })));
                app.draft.status = 'finalized';
            } else {
                button.disabled = false;
                result.textContent = res.data.message || 'Der Charakter konnte nicht erstellt werden.';
                if (res.data.blockers) result.append(SC.findingList(res.data.blockers.map((b) => ({ ...b, severity: b.severity || 'error' }))));
            }
        } }, 'Charakter erstellen');
        box.append(blockers.length ? h('p', { class: 'sc-muted', text: `${blockers.length} offene Punkte verhindern das Erstellen (siehe oben).` }) : h('p', { class: 'sc-ok-note', text: 'Alles vollständig und regelkonform.' }), button, result);
        return box;
    }

    function renderPruefung() {
        const wrap = h('div');
        wrap.append(panel(h('h3', { text: 'Alle Befunde' }), SC.findingList(SC.allFindings())));
        wrap.append(renderOverrides());
        wrap.append(h('div', { class: 'sc-panel' }, h('h3', { text: 'Regelquelle' }), h('p', null, 'SRD 5.2.1 (Deutsch), Lizenz CC BY 4.0. Die Quelle wird mit Version und Prüfsumme am Charakter festgehalten.')));
        wrap.append(renderFinalize());
        return wrap;
    }

    SC.steps = {
        klasse: { render: renderKlasse }, herkunft: { render: renderHerkunft }, attribute: { render: renderAttribute },
        wahlen: { render: renderWahlen }, ausruestung: { render: renderAusruestung }, zauber: { render: renderZauber },
        beschreibung: { render: renderBeschreibung }, pruefung: { render: renderPruefung },
    };
    SC.prune = prune;
    SC.util = { classSkillOptions: (c) => c.skillChoices.options || app.data.skills.map((x) => x.id), castingRow, maxGrade, spellbookSize, choiceNeed, weaponAllowed, expectedExpertise };
    SC.onSaved = function () {
        const button = document.getElementById('scFinalize-btn');
        if (button && !app.finalizing && app.draft.status !== 'finalized') button.disabled = (app.blockers || []).length > 0;
    };
})();
