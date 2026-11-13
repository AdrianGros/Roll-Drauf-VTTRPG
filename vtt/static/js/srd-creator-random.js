(function () {
    'use strict';

    const SC = window.SrdCreator;
    const { ABIL, pick, shuffle, randInt } = SC;
    const app = SC.app;

    const FIRST = ['Aldric', 'Brienne', 'Corvin', 'Dara', 'Elowen', 'Fenris', 'Gisela', 'Hartmut', 'Isolde', 'Jorun', 'Kaelen', 'Liora', 'Mirel', 'Nerys', 'Orin', 'Perrin', 'Quill', 'Runa', 'Sigrun', 'Tamsin', 'Ulfar', 'Vesna', 'Wulf', 'Yrsa', 'Zephyr'];
    const LAST = ['Eichenschild', 'Nebelwanderer', 'Sturmbrecher', 'Silberblatt', 'Aschenhain', 'Dunkelquell', 'Funkenschlag', 'Rabenfeder', 'Steinbrecher', 'Morgenrot', 'Schattenwacht', 'Goldader'];

    function takeUnique(list, count, taken) {
        const out = [];
        shuffle(list).forEach((x) => { if (out.length < count && !taken.includes(x)) out.push(x); });
        return out;
    }

    SC.randomize = function (level) {
        const data = app.data;
        const U = SC.util;
        const L = Math.max(1, Math.min(data.maxLevel, level || 1));
        const c = pick(data.classes);
        const state = {
            sources: app.draft.state.sources, abilityMethod: 'standard-array', abilityBase: { ...c.standardAbilityScores },
            levels: Array.from({ length: L }, () => ({ classKey: c.classKey, hp: 'fixed' })), identity: {}, equipment: { classPackage: 'A', backgroundPackage: 'A' },
        };
        const order = ABIL.slice().sort((a, b) => c.standardAbilityScores[b] - c.standardAbilityScores[a]);

        // species
        const species = pick(data.species);
        state.species = { id: species.id, choices: {} };
        species.choices.forEach((ch) => {
            if (ch.kind === 'option') state.species.choices[ch.id] = pick(ch.options).id;
            else if (ch.kind === 'ability') state.species.choices[ch.id] = pick(ch.options);
            else if (ch.kind === 'skill') state.species.choices[ch.id] = pick(ch.options || data.skills.map((s) => s.id));
            else if (ch.kind === 'feat-category') state.species.choices[ch.id] = pick(data.feats.filter((f) => f.category === ch.category)).id;
            else if (ch.kind === 'size') state.species.choices[ch.id] = pick(species.sizes);
        });

        // background
        const bg = pick(data.backgrounds);
        const ranked = bg.abilities.slice().sort((a, b) => order.indexOf(a) - order.indexOf(b));
        state.background = { id: bg.id, abilityBonus: { [ranked[0]]: 2, [ranked[1]]: 1 } };
        const score = { ...state.abilityBase };
        Object.entries(state.background.abilityBonus).forEach(([a, v]) => { score[a] += v; });

        // skills
        const classSkills = takeUnique(U.classSkillOptions(c), c.skillChoices.count, bg.skills);
        state.skills = { class: classSkills };
        const profs = classSkills.concat(bg.skills);
        state.skills.expertise = [];

        // subclass and feature choices
        state.subclasses = {};
        state.featureChoices = { [c.classKey]: {} };
        const fc = state.featureChoices[c.classKey];
        if (L >= c.subclassLevels[0]) state.subclasses[c.classKey] = pick(c.subclasses);
        let expertiseNeed = 0;
        c.featureChoices.forEach((ch) => {
            if (ch.level > L) return;
            if (ch.kind === 'expertise') { expertiseNeed += ch.count || 0; return; }
            if (ch.kind === 'option') fc[ch.id] = pick(Object.keys(ch.options));
            else if (ch.kind === 'feat-category') fc[ch.id] = pick(data.feats.filter((f) => f.category.startsWith(ch.category))).id;
            else {
                const n = U.choiceNeed(ch, L);
                let pool = [];
                if (ch.kind === 'weapon-mastery') pool = data.equipment.weapons.filter((w) => U.weaponAllowed(c, w) && (!/-melee$/.test(ch.weapons || '') || w.kind === 'melee')).map((w) => w.id);
                // The quick generator chooses independent options. Dependent options remain
                // available through the server-checked manual selection after generation.
                else if (ch.kind === 'class-option') pool = data.classOptions.filter((o) => o.classKey === c.classKey && o.kind === ch.optionKind && (o.minClassLevel || 1) <= L && !o.requirements.optionId && !o.requirements.knownCantrip).map((o) => o.id);
                else if (ch.kind === 'language') pool = data.languages.filter((l) => !l.automatic).map((l) => l.id);
                const used = Object.values(fc).filter(Array.isArray).flat();
                fc[ch.id] = shuffle(pool.filter((id) => !used.includes(id))).slice(0, n);
            }
        });
        if (expertiseNeed) state.skills.expertise = shuffle(profs).slice(0, expertiseNeed);

        // advancements
        state.advancements = [];
        c.asiLevels.concat([c.epicBoonLevel]).forEach((lvl) => {
            if (lvl > L) return;
            if (lvl === c.epicBoonLevel) {
                const boon = pick(data.feats.filter((f) => f.category === 'Epische-Gabe-Talent' && f.abilityIncrease));
                const allowed = boon.abilityIncrease.abilities === 'any' ? ABIL : boon.abilityIncrease.abilities;
                const target = allowed.slice().sort((a, b) => order.indexOf(a) - order.indexOf(b))[0];
                state.advancements.push({ classKey: c.classKey, classLevel: lvl, kind: 'feat', featId: boon.id, increaseAbility: target });
                score[target] += 1;
                return;
            }
            const withRoom = order.filter((a) => score[a] <= 18);
            if (withRoom.length) {
                state.advancements.push({ classKey: c.classKey, classLevel: lvl, kind: 'asi', increases: { [withRoom[0]]: 2 } });
                score[withRoom[0]] += 2;
            } else {
                const ones = order.filter((a) => score[a] <= 19).slice(0, 2);
                state.advancements.push({ classKey: c.classKey, classLevel: lvl, kind: 'asi', increases: Object.fromEntries(ones.map((a) => [a, 1])) });
                ones.forEach((a) => { score[a] += 1; });
            }
        });

        // spells
        state.spells = {};
        if (c.spellcasting) {
            const row = U.castingRow(c.classKey, L);
            const grade = U.maxGrade(c.classKey, L);
            const list = data.spellLists[c.classKey] || [];
            const cantrips = list.filter((id) => data.spells[id].level === 0);
            const leveled = list.filter((id) => data.spells[id].level >= 1 && data.spells[id].level <= grade);
            const entry = { cantrips: shuffle(cantrips).slice(0, row.cantrips) };
            if (c.spellcasting.preparation.mode === 'spellbook') {
                entry.spellbook = shuffle(leveled).slice(0, U.spellbookSize(c.classKey, L));
                entry.prepared = shuffle(entry.spellbook).slice(0, row.prepared);
            } else {
                entry.prepared = shuffle(leveled).slice(0, row.prepared);
            }
            state.spells[c.classKey] = entry;
        }

        // armor
        const owned = SC.startingItems(state);
        const armors = data.equipment.armor.filter((a) => owned.has(a.id) && a.category !== 'shield' && c.armorProficiencies.includes(a.category) && (!a.strengthRequirement || score.str >= a.strengthRequirement))
            .sort((a, b) => b.base - a.base);
        if (armors.length) state.equipment.armor = armors[0].id;
        if (c.armorProficiencies.includes('shield') && data.equipment.armor.some((a) => a.category === 'shield' && owned.has(a.id)) && randInt(2) === 0) state.equipment.shield = true;

        state.identity = {
            name: `${pick(FIRST)} ${pick(LAST)}`,
            alignment: pick(data.alignments).id,
        };
        SC.mutate((current) => {
            Object.keys(current).forEach((k) => delete current[k]);
            Object.assign(current, state);
        });
    };
})();
