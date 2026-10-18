/* Read-only view of a character that its owner shares by link. No login; the token lives in the URL fragment. */
(function () {
  'use strict';

  const ABIL = [['str', 'Stärke'], ['dex', 'Geschicklichkeit'], ['con', 'Konstitution'], ['int', 'Intelligenz'], ['wis', 'Weisheit'], ['cha', 'Charisma']];
  const PROFICIENCY = { proficient: 'geübt', expertise: 'Expertise' };

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
    root.replaceChildren();
    document.getElementById('ssTitle').textContent = sheet.name;
    document.title = `${sheet.name} · Geteilter Charakter · Roll Drauf VTT`;

    const overview = section('Überblick');
    const classes = sheet.classes.map((c) => `${c.name} ${c.level}`).join(' / ');
    overview.append(el('p', null, [sheet.species, sheet.background, classes, `Stufe ${sheet.level}`].filter(Boolean).join(' · ')));
    overview.append(tags([
      `TP ${sheet.hitPoints.current} / ${sheet.hitPoints.max}`, `RK ${sheet.armorClass}`, `Initiative ${signed(sheet.initiative)}`,
      `Bewegung ${sheet.speedMeters} m`, `Passive Wahrnehmung ${sheet.passivePerception}`, `Übungsbonus ${signed(sheet.proficiencyBonus)}`,
    ]));
    root.append(overview);

    const abilities = section('Attribute und Rettungswürfe');
    const grid = el('div', 'ss-abilities');
    ABIL.forEach(([key, label]) => {
      const ability = sheet.abilities[key];
      const save = sheet.saves[key];
      const box = el('div', 'ss-ability');
      box.append(el('span', 'ss-ability-name', label), el('span', 'ss-ability-mod', signed(ability.modifier)), el('span', 'ss-ability-score', `Wert ${ability.score}`),
        el('span', 'ss-ability-save', `Rettungswurf ${signed(save.bonus)}${save.proficient ? ' (geübt)' : ''}`));
      grid.append(box);
    });
    abilities.append(grid);
    root.append(abilities);

    const skills = section('Fertigkeiten');
    const list = el('ul', 'ss-list');
    Object.values(sheet.skills).forEach((skill) => {
      const li = el('li', skill.proficiency !== 'none' ? 'is-proficient' : '');
      li.append(el('span', null, `${skill.name}${PROFICIENCY[skill.proficiency] ? ` (${PROFICIENCY[skill.proficiency]})` : ''}`), el('span', null, signed(skill.bonus)));
      list.append(li);
    });
    skills.append(list);
    root.append(skills);

    if (sheet.feats.length) {
      const feats = section('Talente');
      feats.append(tags(sheet.feats));
      root.append(feats);
    }

    const casting = Object.values(sheet.spellcasting.classes);
    if (casting.length || sheet.spells.length) {
      const spells = section('Zauberwirken');
      if (casting.length) {
        spells.append(tags(casting.map((c) => `Zauber-SG ${c.saveDc}`).concat(casting.map((c) => `Zauberangriff ${signed(c.attackBonus)}`))));
        const slots = sheet.spellcasting.slots.map((count, index) => (count ? `Grad ${index + 1}: ${count}` : null)).filter(Boolean);
        if (slots.length) spells.append(el('p', null, `Zauberplätze: ${slots.join(' · ')}`));
      }
      if (sheet.spells.length) spells.append(tags(sheet.spells.map((s) => `${s.name}${s.level === 0 ? ' (Zaubertrick)' : ` (Grad ${s.level})`}`)));
      root.append(spells);
    }

    const gear = section('Ausrüstung');
    if (sheet.equipment.length) gear.append(tags(sheet.equipment.map((i) => `${i.name}${i.quantity > 1 ? ` ×${i.quantity}` : ''}${i.equipped ? ' (angelegt)' : ''}`)));
    else gear.append(el('p', null, 'Keine Gegenstände.'));
    const coins = Object.entries(sheet.coins || {}).filter(([, amount]) => amount > 0).map(([code, amount]) => `${amount} ${code}`);
    if (coins.length) gear.append(el('p', null, `Münzen: ${coins.join(', ')}`));
    root.append(gear);

    root.append(el('p', 'ss-banner', 'Dies ist eine schreibgeschützte Ansicht. Notizen, Hintergrund und Besitzerdaten werden nicht geteilt.'));
    root.hidden = false;
  }

  async function start() {
    const status = document.getElementById('ssStatus');
    const token = decodeURIComponent((window.location.hash || '').replace(/^#t=|^#/, ''));
    if (!/^\d{1,9}-[A-Za-z0-9_-]{8,80}$/.test(token)) {
      status.textContent = 'Dieser Link ist nicht (mehr) gültig.';
      return;
    }
    try {
      const response = await fetch(`/api/srd-creator/shared/${encodeURIComponent(token)}`, { credentials: 'omit', referrerPolicy: 'no-referrer' });
      if (!response.ok) throw new Error(String(response.status));
      render(await response.json());
      status.textContent = '';
    } catch (error) {
      status.textContent = 'Dieser Link ist nicht (mehr) gültig.';
    }
  }

  start();
})();
