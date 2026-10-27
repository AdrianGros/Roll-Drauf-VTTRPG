/* Party overview of a campaign: values of every hero, DM tools (group awards, campaign rules, item handouts). */
(function () {
  'use strict';

  const API = '/api/srd-creator';
  const ABIL = [['str', 'STÄ'], ['dex', 'GES'], ['con', 'KON'], ['int', 'INT'], ['wis', 'WEI'], ['cha', 'CHA']];
  const COINS = ['PM', 'GM', 'EM', 'SM', 'KM'];
  const ERRORS = {
    forbidden: 'Dafür fehlt dir die Berechtigung.',
    not_found: 'Diese Kampagne gibt es nicht oder du bist kein Mitglied.',
    invalid_xp: 'Gib ganze Erfahrungspunkte zwischen 1 und 1.000.000 an.',
    invalid_methods: 'Wähle mindestens eine Methode aus.',
    not_handed_out: 'Nur ausgegebene Gegenstände kannst du zurücknehmen.',
    inventory_full: 'Das Inventar ist voll.',
    not_srd: 'Dieser Charakter hat kein Regelwerk-Inventar.',
  };

  const state = { campaignId: null, data: null, selected: new Set(), handout: null };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function btn(text, className, onClick) {
    const node = el('button', className || 'sp-btn', text);
    node.type = 'button';
    node.addEventListener('click', onClick);
    return node;
  }

  function failure(error) {
    return ERRORS[error?.apiError] || error?.message || 'Die Aktion ist fehlgeschlagen.';
  }

  function say(text, isError) {
    const node = document.getElementById('spStatus');
    node.textContent = text || '';
    node.classList.toggle('is-error', Boolean(isError));
  }

  function field(labelText, input) {
    const wrap = el('label', 'sp-field');
    wrap.append(el('span', 'sp-field-label', labelText), input);
    return wrap;
  }

  function input(type, id, attrs) {
    const node = el('input', 'sp-input');
    node.type = type;
    if (id) node.id = id;
    Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  // ------------------------------------------------------------------ cards

  function stat(label, value) {
    const box = el('div', 'sp-stat');
    box.append(el('span', 'sp-stat-label', label), el('span', 'sp-stat-value', value === null || value === undefined ? '–' : String(value)));
    return box;
  }

  function signed(value) {
    return value >= 0 ? `+${value}` : `−${Math.abs(value)}`;
  }

  function card(row, isDm) {
    const node = el('article', 'sp-card');
    node.dataset.characterId = String(row.id);
    if (row.accent) node.style.setProperty('--sp-accent', row.accent);
    const head = el('div', 'sp-card-head');
    const title = el('h2', 'sp-card-title');
    const link = el('a', 'sp-card-link', row.name);
    link.href = row.href;
    title.append(link);
    head.append(title);
    if (isDm && row.srd) {
      const pick = el('label', 'sp-pick');
      const box = el('input');
      box.type = 'checkbox';
      box.checked = state.selected.has(row.id);
      box.setAttribute('aria-label', `${row.name} auswählen`);
      box.addEventListener('change', () => { if (box.checked) state.selected.add(row.id); else state.selected.delete(row.id); });
      pick.append(box, el('span', 'sp-pick-text', 'Auswählen'));
      head.append(pick);
    }
    node.append(head);
    const sub = [row.species, row.className && `${row.className} ${row.level}`, row.owner].filter(Boolean).join(' · ');
    node.append(el('p', 'sp-card-sub', sub));

    const hpMax = Math.max(1, row.hpMax || 1);
    const percent = Math.max(0, Math.min(100, Math.round(((row.hpCurrent || 0) / hpMax) * 100)));
    const hp = el('div', 'sp-hp');
    hp.setAttribute('role', 'img');
    hp.setAttribute('aria-label', `Trefferpunkte ${row.hpCurrent} von ${row.hpMax}`);
    const fill = el('div', 'sp-hp-fill');
    fill.style.width = `${percent}%`;
    if (percent <= 25) fill.classList.add('is-low');
    hp.append(fill);
    node.append(hp, el('p', 'sp-hp-text', `TP ${row.hpCurrent} / ${row.hpMax}`));

    const stats = el('div', 'sp-stats');
    stats.append(stat('RK', row.ac));
    if (row.srd) {
      stats.append(
        stat('Init.', signed(row.initiative)),
        stat('Bew. (m)', row.speedMeters),
        stat('Passive Wahrn.', row.passivePerception),
        stat('Zauber-SG', row.spellSaveDc),
      );
    }
    node.append(stats);

    if (row.origin) {
      // Pinned homebrew Species: what the table needs to know, as text (authored content is never HTML).
      const origin = row.origin;
      const movement = (origin.movement || []).map((m) => `${m.label} ${m.feet} ft`).join(', ');
      const senses = (origin.senses || []).map((s) => `${s.label} ${s.feet} ft`).join(', ') || 'keine Dunkelsicht';
      const box = el('div', 'sp-origin');
      box.append(el('p', 'sp-card-sub', `${origin.name} (Homebrew, Fassung ${origin.revision}) · ${origin.creatureType?.label || ''} · ${(origin.sizes || []).map((s) => s.label).join('/')}`));
      box.append(el('p', 'sp-card-sub', `Bewegung: ${movement} · Sinne: ${senses}`));
      (origin.actions || []).forEach((action) => {
        const details = el('details', 'sp-origin-action');
        details.append(el('summary', '', `${action.name} · ${action.rangeFeet} ft · ${action.maxWeightLb} lb`),
          el('p', 'sp-card-sub', action.summary));
        box.append(details);
      });
      node.append(box);
    }

    if (row.abilities) {
      const abilities = el('div', 'sp-abilities');
      ABIL.forEach(([key, label]) => {
        const box = el('div', 'sp-ability');
        box.append(el('span', 'sp-ability-label', label), el('span', 'sp-ability-score', String(row.abilities[key])));
        abilities.append(box);
      });
      node.append(abilities);
    }

    const conditions = el('ul', 'sp-conditions');
    conditions.setAttribute('aria-label', 'Zustände');
    if (row.conditions.length) row.conditions.forEach((c) => conditions.append(el('li', 'sp-condition', c.label)));
    else conditions.append(el('li', 'sp-condition is-none', 'Keine Zustände'));
    node.append(conditions);

    if (!row.srd) node.append(el('p', 'sp-note', 'Charakter ohne Regelwerk-Bogen: nur Grundwerte.'));
    if (row.progress) {
      const p = row.progress;
      const line = p.mode === 'milestone'
        ? `Meilenstein-Modus${p.canLevelUp ? ` · Freigabe bis Stufe ${p.targetLevel}` : ''}`
        : `${p.xp} EP${p.nextLevelXp ? ` / ${p.nextLevelXp}` : ''}${p.canLevelUp ? ` · Stufe ${p.targetLevel} möglich` : ''}`;
      const progress = el('p', `sp-progress${p.canLevelUp ? ' is-ready' : ''}`, line);
      node.append(progress);
      const actions = el('div', 'sp-card-actions');
      actions.append(btn('Gegenstand ausgeben', 'sp-btn', () => openHandout(row)));
      node.append(actions);
    }
    return node;
  }

  function renderParty() {
    const root = document.getElementById('spParty');
    root.replaceChildren();
    const { characters, isDm } = state.data;
    if (!characters.length) {
      root.append(el('p', 'sp-empty', 'In dieser Kampagne ist noch kein Charakter eingetragen. Ordne Charaktere auf der Charakterseite einer Kampagne zu.'));
    } else {
      const grid = el('div', 'sp-grid');
      characters.forEach((row) => grid.append(card(row, isDm)));
      root.append(grid);
    }
    root.hidden = false;
  }

  // ------------------------------------------------------------------ DM tools

  async function request(path, method, body) {
    return window.Auth.makeAuthRequest(`${API}${path}`, method, body);
  }

  function scopeIds() {
    const scope = document.getElementById('spScope').value;
    if (scope === 'all') return undefined;
    return Array.from(state.selected);
  }

  async function award(payload, doneText) {
    const ids = scopeIds();
    if (ids && !ids.length) { say('Wähle zuerst Charaktere aus oder vergib an alle.', true); return; }
    try {
      const result = await request(`/campaigns/${state.campaignId}/award`, 'POST', { ...payload, ...(ids ? { characterIds: ids } : {}) });
      state.data.characters = result.characters;
      renderParty();
      say(`${doneText} ${result.changed.length} Charakter${result.changed.length === 1 ? '' : 'e'} geändert.`, false);
    } catch (error) {
      say(failure(error), true);
    }
  }

  function awardSection() {
    const box = el('section', 'sp-panel');
    box.append(el('h2', 'sp-panel-title', 'Erfahrung und Meilensteine'));
    const row = el('div', 'sp-form-row');
    const scope = el('select', 'sp-input');
    scope.id = 'spScope';
    [['all', 'Alle Charaktere mit Regelwerk-Bogen'], ['selected', 'Nur ausgewählte Charaktere']].forEach(([value, text]) => {
      const option = el('option', null, text);
      option.value = value;
      scope.append(option);
    });
    row.append(field('Wer', scope));
    const xp = input('number', 'spXp', { min: '1', max: '1000000', step: '1', inputmode: 'numeric' });
    row.append(field('Erfahrungspunkte', xp));
    const note = input('text', 'spNote', { maxlength: '200' });
    row.append(field('Notiz (erscheint im Verlauf)', note));
    box.append(row);
    const actions = el('div', 'sp-form-row');
    const give = btn('EP vergeben', 'sp-btn sp-primary', () => {
      const value = Number(xp.value);
      if (!Number.isInteger(value) || value < 1) { say(ERRORS.invalid_xp, true); return; }
      award({ addXp: value, note: note.value }, 'EP vergeben:');
    });
    give.id = 'spGiveXp';
    const level = input('number', 'spMilestone', { min: '1', max: '20', step: '1', inputmode: 'numeric' });
    const milestone = btn('Zielstufe freigeben', 'sp-btn', () => {
      const value = Number(level.value);
      if (!Number.isInteger(value) || value < 1 || value > 20) { say('Die Zielstufe liegt zwischen 1 und 20.', true); return; }
      award({ milestoneTarget: value, note: note.value }, 'Zielstufe gesetzt:');
    });
    milestone.id = 'spGiveMilestone';
    actions.append(give, field('Zielstufe (Meilenstein-Modus)', level), milestone);
    box.append(actions);
    box.append(el('p', 'sp-hint', 'Die Spieler lösen den Aufstieg selbst auf ihrem Bogen aus; die Spielleitung gibt nur frei.'));
    return box;
  }

  function rulesSection() {
    const box = el('section', 'sp-panel');
    box.append(el('h2', 'sp-panel-title', 'Regeln der Kampagne'));
    const fieldset = el('fieldset', 'sp-fieldset');
    fieldset.append(el('legend', 'sp-legend', 'Erlaubte Methoden für die Attributswerte'));
    const allowed = new Set(state.data.rules.attributeMethods);
    state.data.rules.allMethods.forEach((method) => {
      const label = el('label', 'sp-check');
      const box2 = el('input');
      box2.type = 'checkbox';
      box2.value = method.id;
      box2.checked = allowed.has(method.id);
      label.append(box2, el('span', null, method.label));
      fieldset.append(label);
    });
    box.append(fieldset);
    const save = btn('Regeln speichern', 'sp-btn sp-primary', async () => {
      const methods = Array.from(fieldset.querySelectorAll('input:checked')).map((node) => node.value);
      if (!methods.length) { say(ERRORS.invalid_methods, true); return; }
      try {
        state.data.rules = await request(`/campaigns/${state.campaignId}/rules`, 'PUT', { attributeMethods: methods });
        say('Regeln gespeichert.', false);
      } catch (error) {
        say(failure(error), true);
      }
    });
    save.id = 'spSaveRules';
    box.append(save);
    box.append(el('p', 'sp-hint', 'Gilt, wenn ein Charakter dieser Kampagne zugeordnet wird oder beim Abschluss im Ersteller. Bereits zugeordnete Charaktere bleiben unverändert.'));
    return box;
  }

  function renderDm() {
    const root = document.getElementById('spDm');
    root.replaceChildren();
    if (!state.data.isDm) { root.hidden = true; return; }
    root.append(el('h2', 'sp-dm-title', 'Werkzeuge der Spielleitung'), awardSection(), rulesSection());
    root.hidden = false;
  }

  // ------------------------------------------------------------------ handout dialog

  function dialog() {
    return document.getElementById('spDialog');
  }

  function closeDialog() {
    const node = dialog();
    if (node.open) node.close();
  }

  async function openHandout(row) {
    state.handout = { row, kind: 'gear', results: [], inventory: null, message: '' };
    document.getElementById('spDialogTitle').textContent = `Gegenstand ausgeben an ${row.name}`;
    try {
      state.handout.inventory = await window.Auth.makeAuthRequest(`${API}/characters/${row.id}/inventory`);
    } catch (error) {
      say(failure(error), true);
      return;
    }
    renderHandout();
    if (!dialog().open) dialog().showModal();
    document.getElementById('spDialogTitle').focus();
    search();
  }

  async function search() {
    const h = state.handout;
    if (!h || h.kind === 'coins') return;
    const query = document.getElementById('spSearch')?.value || '';
    try {
      const result = await window.Auth.makeAuthRequest(`${API}/handout/items?kind=${h.kind}&q=${encodeURIComponent(query)}`);
      h.results = result.items;
    } catch (error) {
      h.results = [];
      h.message = failure(error);
    }
    renderHandout(true);
  }

  async function give(body, doneText) {
    const h = state.handout;
    try {
      h.inventory = await window.Auth.makeAuthRequest(`${API}/characters/${h.row.id}/handout`, 'POST', body);
      h.message = doneText;
    } catch (error) {
      h.message = failure(error);
    }
    renderHandout(true);
  }

  async function takeBack(item) {
    const h = state.handout;
    try {
      h.inventory = await window.Auth.makeAuthRequest(`${API}/characters/${h.row.id}/handout/${item.id}`, 'DELETE');
      h.message = `${item.name} zurückgenommen.`;
    } catch (error) {
      h.message = failure(error);
    }
    renderHandout(true);
  }

  function renderHandout(keepFocus) {
    const h = state.handout;
    const body = document.getElementById('spDialogBody');
    const previous = document.activeElement?.id;
    const previousQuery = document.getElementById('spSearch')?.value || '';
    body.replaceChildren();
    const message = el('p', 'sp-dialog-message', h.message);
    message.id = 'spHandoutMessage';
    message.setAttribute('role', 'status');
    body.append(message);

    const kinds = el('div', 'sp-kinds');
    kinds.setAttribute('role', 'group');
    kinds.setAttribute('aria-label', 'Art');
    [['gear', 'Ausrüstung'], ['magic', 'Magischer Gegenstand'], ['coins', 'Münzen']].forEach(([kind, text]) => {
      const tab = btn(text, `sp-btn${h.kind === kind ? ' sp-primary' : ''}`, () => { h.kind = kind; h.message = ''; h.results = []; renderHandout(); search(); });
      tab.setAttribute('aria-pressed', h.kind === kind ? 'true' : 'false');
      tab.dataset.kind = kind;
      kinds.append(tab);
    });
    body.append(kinds);

    if (h.kind === 'coins') {
      const grid = el('div', 'sp-coins');
      const inputs = {};
      COINS.forEach((code) => {
        const node = input('number', `spCoin${code}`, { step: '1', inputmode: 'numeric' });
        inputs[code] = node;
        grid.append(field(`${h.inventory.coinNames?.[code] || code} (${code}, jetzt ${h.inventory.coins?.[code] ?? 0})`, node));
      });
      body.append(grid);
      const button = btn('Münzen ausgeben', 'sp-btn sp-primary', () => {
        const coins = {};
        COINS.forEach((code) => { const value = inputs[code].value; if (value !== '') coins[code] = Number(value); });
        if (!Object.keys(coins).length) { h.message = 'Gib mindestens eine Münzmenge an.'; renderHandout(); return; }
        give({ coins }, 'Münzen ausgegeben.');
      });
      button.id = 'spGiveCoins';
      body.append(button, el('p', 'sp-hint', 'Negative Zahlen nehmen Münzen ab.'));
    } else {
      const searchBox = input('search', 'spSearch', { placeholder: 'Name suchen', 'aria-label': 'Name suchen', maxlength: '100' });
      searchBox.value = previousQuery;
      let timer = null;
      searchBox.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(search, 200); });
      const quantity = input('number', 'spQty', { min: '1', max: '999', step: '1', value: '1' });
      const row = el('div', 'sp-form-row');
      row.append(field('Suche', searchBox), field('Anzahl', quantity));
      body.append(row);
      const list = el('ul', 'sp-results');
      list.id = 'spResults';
      if (!h.results.length) list.append(el('li', 'sp-result is-empty', 'Keine Treffer.'));
      h.results.forEach((item) => {
        const li = el('li', 'sp-result');
        const text = el('span', 'sp-result-text');
        text.append(el('strong', null, item.name), el('span', 'sp-result-sub', item.summary || ''));
        li.append(text, btn('Ausgeben', 'sp-btn', () => give({ kind: h.kind, itemId: item.id, quantity: Number(quantity.value) || 1 }, `${item.name} ausgegeben.`)));
        li.dataset.itemName = item.name;
        list.append(li);
      });
      body.append(list);
      if (h.kind === 'magic') body.append(el('p', 'sp-hint', 'Beschreibung aus dem Regelwerk (SRD 5.2.1, CC BY 4.0); Tabellen und Werte stehen im Compendium.'));
    }

    const given = (h.inventory.items || []).filter((item) => item.handedOut);
    const section = el('div', 'sp-given');
    section.append(el('h3', 'sp-given-title', 'Von der Spielleitung ausgegeben'));
    if (!given.length) section.append(el('p', 'sp-hint', 'Noch nichts ausgegeben.'));
    given.forEach((item) => {
      const li = el('div', 'sp-given-row');
      li.append(el('span', null, `${item.name}${item.quantity > 1 ? ` ×${item.quantity}` : ''}`), btn('Zurücknehmen', 'sp-btn sp-danger', () => takeBack(item)));
      section.append(li);
    });
    body.append(section);
    if (keepFocus && previous) document.getElementById(previous)?.focus();
  }

  // ------------------------------------------------------------------ start

  async function start() {
    const user = await window.Auth.requireAuth();
    if (!user) return;
    const raw = new URLSearchParams(window.location.search).get('campaign');
    state.campaignId = /^\d{1,9}$/.test(raw || '') ? Number(raw) : null;
    if (!state.campaignId) { say('Es wurde keine Kampagne angegeben. Öffne die Gruppenübersicht über die Kampagnenliste.', true); return; }
    document.getElementById('spDialogClose').addEventListener('click', closeDialog);
    try {
      state.data = await request(`/campaigns/${state.campaignId}/party`, 'GET');
    } catch (error) {
      say(failure(error), true);
      return;
    }
    document.getElementById('spTitle').textContent = `Gruppenübersicht · ${state.data.campaign.name}`;
    document.title = `Gruppenübersicht · ${state.data.campaign.name} · Roll Drauf VTT`;
    document.getElementById('spKicker').textContent = state.data.isDm ? 'Roll Drauf VTT · Spielleitung' : 'Roll Drauf VTT · Mitglied';
    say('', false);
    renderParty();
    renderDm();
  }

  start();
})();
