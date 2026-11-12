globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/* Read-only view of a character that its owner shares by link. No login; the token lives in the URL fragment. */
(function () {
  'use strict';

  const ABIL = [['str', globalThis.VTTUi("Stärke")], ['dex', globalThis.VTTUi("Geschicklichkeit")], ['con', globalThis.VTTUi("Konstitution")], ['int', globalThis.VTTUi("Intelligenz")], ['wis', globalThis.VTTUi("Weisheit")], ['cha', globalThis.VTTUi("Charisma")]];
  const PROFICIENCY = { proficient: globalThis.VTTUi("geübt"), expertise: globalThis.VTTUi("Expertise") };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function signed(value) {
    return value >= 0 ? `+${value}` : `−${Math.abs(value)}`;
  }

  function section(title) {
    const node = el('section', 'ss-section');
    node.append(el('h2', null, title));
    return node;
  }

  function tags(items) {
    const list = el('ul', 'ss-tags');
    items.forEach((text) => list.append(el('li', 'ss-tag', text)));
    return list;
  }

  function render(sheet) {
    const root = document.getElementById('ssSheet');
    if (/^#[0-9a-f]{6}$/i.test(sheet.accent || '')) root.style.setProperty('--ss-accent', sheet.accent);
    root.replaceChildren();
    document.getElementById('ssTitle').textContent = sheet.name;
    document.title = globalThis.VTTUi("{p0} · Geteilter Charakter · Roll Drauf VTT",{p0:(sheet.name)});

    const overview = section(globalThis.VTTUi("Überblick"));
    const classes = sheet.classes.map((c) => `${c.name} ${c.level}`).join(' / ');
    overview.append(el('p', null, [sheet.species, sheet.background, classes, globalThis.VTTUi("Stufe {level}", { level: sheet.level })].filter(Boolean).join(' · ')));
    overview.append(tags([
      globalThis.VTTUi("TP {current} / {max}", { current: sheet.hitPoints.current, max: sheet.hitPoints.max }),
      globalThis.VTTUi("RK {value}", { value: sheet.armorClass }),
      globalThis.VTTUi("Initiative {value}", { value: signed(sheet.initiative) }),
      globalThis.VTTUi("Bewegung {value} m", { value: sheet.speedMeters }),
      globalThis.VTTUi("Passive Wahrnehmung {value}", { value: sheet.passivePerception }),
      globalThis.VTTUi("Übungsbonus {value}", { value: signed(sheet.proficiencyBonus) }),
    ]));
    root.append(overview);

    const abilities = section(globalThis.VTTUi("Attribute und Rettungswürfe"));
    const grid = el('div', 'ss-abilities');
    ABIL.forEach(([key, label]) => {
      const ability = sheet.abilities[key];
      const save = sheet.saves[key];
      const box = el('div', 'ss-ability');
      box.append(el('span', 'ss-ability-name', label), el('span', 'ss-ability-mod', signed(ability.modifier)), el('span', 'ss-ability-score', globalThis.VTTUi("Wert {p0}",{p0:(ability.score)})),
        el('span', 'ss-ability-save', globalThis.VTTUi("Rettungswurf {p0}{p1}",{p0:(signed(save.bonus)),p1:(save.proficient ? globalThis.VTTUi(" (geübt)") : '')})));
      grid.append(box);
    });
    abilities.append(grid);
    root.append(abilities);

    const skills = section(globalThis.VTTUi("Fertigkeiten"));
    const list = el('ul', 'ss-list');
    Object.values(sheet.skills).forEach((skill) => {
      const li = el('li', skill.proficiency !== 'none' ? 'is-proficient' : '');
      li.append(el('span', null, `${skill.name}${PROFICIENCY[skill.proficiency] ? ` (${PROFICIENCY[skill.proficiency]})` : ''}`), el('span', null, signed(skill.bonus)));
      list.append(li);
    });
    skills.append(list);
    root.append(skills);

    if (sheet.feats.length) {
      const feats = section(globalThis.VTTUi("Talente"));
      feats.append(tags(sheet.feats));
      root.append(feats);
    }

    const casting = Object.values(sheet.spellcasting.classes);
    if (casting.length || sheet.spells.length) {
      const spells = section(globalThis.VTTUi("Zauberwirken"));
      if (casting.length) {
        spells.append(tags(casting.map((c) => globalThis.VTTUi("Zauber-SG {value}", { value: c.saveDc })).concat(casting.map((c) => globalThis.VTTUi("Zauberangriff {value}", { value: signed(c.attackBonus) })))));
        const slots = sheet.spellcasting.slots.map((count, index) => (count ? globalThis.VTTUi("Grad {grade}: {count}", { grade: index + 1, count }) : null)).filter(Boolean);
        if (slots.length) spells.append(el('p', null, globalThis.VTTUi("Zauberplätze: {p0}",{p0:(slots.join(' · '))})));
      }
      if (sheet.spells.length) spells.append(tags(sheet.spells.map((s) => `${s.name}${s.level === 0 ? globalThis.VTTUi(" (Zaubertrick)") : globalThis.VTTUi(" (Grad {grade})", { grade: s.level })}`)));
      root.append(spells);
    }

    const gear = section(globalThis.VTTUi("Ausrüstung"));
    if (sheet.equipment.length) gear.append(tags(sheet.equipment.map((i) => `${i.name}${i.quantity > 1 ? ` ×${i.quantity}` : ''}${i.equipped ? globalThis.VTTUi(" (angelegt)") : ''}`)));
    else gear.append(el('p', null, globalThis.VTTUi("Keine Gegenstände.")));
    const coins = Object.entries(sheet.coins || {}).filter(([, amount]) => amount > 0).map(([code, amount]) => `${amount} ${code}`);
    if (coins.length) gear.append(el('p', null, globalThis.VTTUi("Münzen: {p0}",{p0:(coins.join(', '))})));
    root.append(gear);

    root.append(el('p', 'ss-banner', globalThis.VTTUi("Dies ist eine schreibgeschützte Ansicht. Notizen, Hintergrund und Besitzerdaten werden nicht geteilt.")));
    root.hidden = false;
  }

  async function start() {
    const status = document.getElementById('ssStatus');
    const token = decodeURIComponent((window.location.hash || '').replace(/^#t=|^#/, ''));
    if (!/^\d{1,9}-[A-Za-z0-9_-]{8,80}$/.test(token)) {
      status.textContent = globalThis.VTTUi("Dieser Link ist nicht (mehr) gültig.");
      return;
    }
    try {
      const response = await fetch(`/api/srd-creator/shared/${encodeURIComponent(token)}`, { credentials: 'omit', referrerPolicy: 'no-referrer' });
      if (!response.ok) throw new Error(String(response.status));
      render(await response.json());
      status.textContent = '';
    } catch (error) {
      status.textContent = globalThis.VTTUi("Dieser Link ist nicht (mehr) gültig.");
    }
  }

  start();
})();
