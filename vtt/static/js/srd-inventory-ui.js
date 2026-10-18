/* Inventory, coins, worn armor and weapon attacks of an SRD character sheet.
 * Relies on globals of character-sheet.html: auth, editable, srdCreatorData, appendText, signed, srdRollButton. */
(function () {
  'use strict';

  const COIN_ORDER = ['PM', 'GM', 'EM', 'SM', 'KM'];
  const KIND_LABELS = { weapon: 'Waffe', armor: 'Rüstung', shield: 'Schild', gear: 'Ausrüstung', tool: 'Werkzeug', custom: 'Eigener Gegenstand' };
  const CHOICE_LABELS = {
    'arcane-focus': 'Arkaner Fokus', 'holy-symbol': 'Heiliges Symbol', 'druidic-focus': 'Druidischer Fokus',
    'musical-instrument': 'Musikinstrument', 'tool-choice': 'Handwerkszeug oder Musikinstrument',
  };
  const ERRORS = {
    already_seeded: 'Die Ausgangsausrüstung wurde bereits übernommen.',
    invalid_coins: 'Ungültige Münzmenge.',
    not_enough_coins: 'Du hast nicht genug Münzen dafür.',
    invalid_quantity: 'Die Anzahl muss eine ganze Zahl zwischen 1 und 9999 sein.',
    invalid_name: 'Gib dem Gegenstand einen Namen.',
    invalid_weight: 'Das Gewicht muss zwischen 0 und 1000 kg liegen.',
    inventory_full: 'Das Inventar ist voll.',
    not_wearable: 'Dieser Gegenstand kann nicht angelegt werden.',
    unknown_item: 'Diesen Gegenstand gibt es im Regelwerk nicht.',
    package_missing: 'Wähle für Klasse und Hintergrund jeweils ein Ausrüstungspaket.',
    forbidden: 'Nur die Besitzerin oder der Besitzer ändert das Inventar.',
  };

  let current = null;

  function kg(value) {
    return `${Number(value || 0).toLocaleString('de-DE', { maximumFractionDigits: 2 })} kg`;
  }

  function costText(cp) {
    if (!cp) return '';
    if (cp % 100 === 0) return `${cp / 100} GM`;
    if (cp % 10 === 0) return `${cp / 10} SM`;
    return `${cp} KM`;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function button(text, className, onClick) {
    const node = element('button', className || 'srd-inv-btn', text);
    node.type = 'button';
    node.addEventListener('click', onClick);
    return node;
  }

  function labelled(text, control, className) {
    const wrap = element('label', className || 'srd-inv-field');
    wrap.append(element('span', 'srd-inv-field-label', text), control);
    return wrap;
  }

  function catalogEntries(data) {
    const equipment = data?.equipment || {};
    const out = [];
    (equipment.armor || []).forEach((e) => out.push({ id: e.id, name: e.name, kind: e.category === 'shield' ? 'shield' : 'armor', weightKg: e.weightKg, costCp: e.costCp }));
    (equipment.weapons || []).forEach((e) => out.push({ id: e.id, name: e.name, kind: 'weapon', weightKg: e.weightKg, costCp: e.costCp }));
    (equipment.items || []).forEach((e) => out.push({ id: e.id, name: e.name, kind: e.kind, weightKg: e.weightKg, costCp: e.costCp }));
    return out.sort((a, b) => a.name.localeCompare(b.name, 'de'));
  }

  function failureText(error) {
    return ERRORS[error?.apiError] || error?.message || 'Die Änderung ist fehlgeschlagen.';
  }

  async function request(path, method, body) {
    const base = `/api/srd-creator/characters/${current.character.id}/inventory`;
    return auth.makeAuthRequest(`${base}${path}`, method, body === undefined ? null : body);
  }

  async function change(path, method, body, notice) {
    const status = document.getElementById('srdInvStatus');
    try {
      const payload = await request(path, method, body);
      current.payload = payload;
      current.notice = notice || (payload.notes || []).join(' ') || '';
      current.error = '';
      render();
      current.onChange?.(payload);
    } catch (error) {
      current.error = failureText(error);
      if (status) {
        status.textContent = current.error;
        status.className = 'srd-inv-status is-error';
      }
    }
  }

  function weightBar(weight) {
    const wrap = element('div', 'srd-inv-weight');
    const text = `Tragelast ${kg(weight.carriedKg)} von ${kg(weight.capacityKg)} (${weight.size}) · Heben/Schieben ${kg(weight.liftKg)}`;
    wrap.append(element('div', 'srd-inv-weight-text', text));
    const track = element('div', 'srd-inv-weight-track');
    const fill = element('div', `srd-inv-weight-fill${weight.over ? ' is-over' : ''}`);
    fill.style.width = `${Math.min(100, Math.round((weight.carriedKg / Math.max(weight.capacityKg, 1)) * 100))}%`;
    track.append(fill);
    track.setAttribute('role', 'img');
    track.setAttribute('aria-label', text);
    wrap.append(track);
    if (weight.over) {
      wrap.append(element('div', 'srd-inv-warn', 'Über der Tragkraft: Die Bewegungsrate sinkt auf höchstens 1,5 m.'));
    }
    wrap.append(element('div', 'srd-inv-weight-detail', `Gegenstände ${kg(weight.itemsKg)} · Münzen ${kg(weight.coinsKg)}`));
    return wrap;
  }

  function coinsBlock(payload) {
    const wrap = element('div', 'srd-inv-coins');
    const inputs = {};
    COIN_ORDER.forEach((code) => {
      const input = element('input', 'srd-inv-coin-input');
      input.type = 'number';
      input.min = '0';
      input.step = '1';
      input.value = String(payload.coins[code] || 0);
      input.disabled = !editable;
      input.id = `srdCoin${code}`;
      inputs[code] = input;
      wrap.append(labelled(`${code} · ${payload.coinNames[code] || code}`, input, 'srd-inv-field srd-inv-coin'));
    });
    if (editable) {
      wrap.append(button('Münzen speichern', 'srd-inv-btn', () => {
        const coins = {};
        COIN_ORDER.forEach((code) => { coins[code] = Number(inputs[code].value); });
        change('/coins', 'PUT', { coins }, 'Münzen gespeichert.');
      }));
    }
    return wrap;
  }

  function seedBlock(payload) {
    const wrap = element('div', 'srd-inv-seed');
    wrap.append(element('p', 'srd-sheet-note', 'Die Ausgangsausrüstung aus Klasse und Hintergrund ist noch nicht im Inventar. Wähle jeweils das Paket, das du im Ersteller genommen hast (A: Ausrüstung, B: Gold).'));
    if (!editable) return wrap;
    const selects = {};
    [['classPackage', 'Klassenpaket', payload.packages.class], ['backgroundPackage', 'Hintergrundpaket', payload.packages.background]].forEach(([key, text, preset]) => {
      const select = element('select', 'srd-inv-select');
      select.append(new Option('Bitte wählen', ''));
      select.append(new Option('A · Ausrüstung', 'A'), new Option('B · Gold', 'B'));
      select.value = preset || '';
      selects[key] = select;
      wrap.append(labelled(text, select));
    });
    wrap.append(button('Ausgangsausrüstung übernehmen', 'srd-inv-btn srd-inv-primary', () => {
      const body = {};
      Object.entries(selects).forEach(([key, select]) => { if (select.value) body[key] = select.value; });
      change('/starting-equipment', 'POST', body, 'Ausgangsausrüstung übernommen.');
    }));
    return wrap;
  }

  function pendingBlock(pending) {
    const wrap = element('div', 'srd-inv-pending');
    pending.forEach((entry) => {
      const row = element('div', 'srd-inv-pending-row');
      row.append(element('span', 'srd-inv-pending-label', `Noch zu wählen: ${CHOICE_LABELS[entry.category] || entry.category}${entry.quantity > 1 ? ` (${entry.quantity}×)` : ''}`));
      if (editable) {
        const select = element('select', 'srd-inv-select');
        entry.options.forEach((option) => select.append(new Option(option.name, option.itemId)));
        row.append(select);
        row.append(button('Nehmen', 'srd-inv-btn srd-inv-primary', () => change('', 'POST', { itemId: select.value, quantity: entry.quantity || 1, resolve: entry.id }, 'Gegenstand hinzugefügt.')));
        row.append(button('Verwerfen', 'srd-inv-btn', () => change(`/pending/${encodeURIComponent(entry.id)}`, 'DELETE')));
      }
      wrap.append(row);
    });
    return wrap;
  }

  function attacksBlock(payload) {
    const table = element('div', 'srd-inv-attacks');
    payload.attacks.forEach((attack) => {
      const row = element('div', `srd-inv-attack${attack.equipped ? ' is-equipped' : ''}`);
      row.dataset.attackKey = attack.key;
      const head = element('div', 'srd-inv-attack-head');
      head.append(element('strong', '', attack.name));
      if (!attack.proficient) head.append(element('span', 'srd-sheet-tag', 'ohne Übung'));
      if (attack.mastery) head.append(element('span', `srd-sheet-tag${attack.masteryActive ? ' is-active' : ''}`, `Meisterschaft ${attack.mastery}${attack.masteryActive ? ' (aktiv)' : ''}`));
      row.append(head);
      const rolls = element('div', 'srd-roll-pair');
      rolls.append(srdRollButton(`Angriff ${signed(attack.attackBonus)}`, 'weapon_attack', attack.key, current.character));
      const damageLabel = `Schaden ${attack.damage} ${attack.damageType}`;
      rolls.append(srdRollButton(damageLabel, 'weapon_damage', attack.key, current.character));
      rolls.append(srdRollButton('Kritisch', 'weapon_damage', attack.key, current.character, 'is-crit-btn', { critical: true }));
      if (attack.versatile) {
        rolls.append(srdRollButton(`Zweihändig ${attack.versatile}`, 'weapon_damage', attack.key, current.character, '', { twoHanded: true }));
      }
      row.append(rolls);
      if (attack.properties.length) row.append(element('div', 'srd-inv-meta', attack.properties.join(' · ')));
      table.append(row);
    });
    return table;
  }

  function itemRow(item) {
    const row = element('li', `srd-inv-item${item.equipped ? ' is-equipped' : ''}`);
    row.dataset.inventoryId = String(item.id);
    const main = element('div', 'srd-inv-item-main');
    const title = element('div', 'srd-inv-item-title');
    title.append(element('strong', '', item.name));
    title.append(element('span', 'srd-sheet-tag', KIND_LABELS[item.kind] || item.kind));
    if (item.equipped) title.append(element('span', 'srd-sheet-tag is-active', item.kind === 'weapon' ? 'in der Hand' : 'angelegt'));
    main.append(title);
    const meta = [item.summary, `${kg(item.weightKg)} je Stück`, item.cost ? `Wert ${item.cost}` : ''].filter(Boolean).join(' · ');
    if (meta) main.append(element('div', 'srd-inv-meta', meta));
    if (item.description) main.append(element('div', 'srd-inv-meta', item.description));
    row.append(main);

    const controls = element('div', 'srd-inv-item-controls');
    const quantity = element('input', 'srd-inv-qty');
    quantity.type = 'number';
    quantity.min = '1';
    quantity.max = '9999';
    quantity.step = '1';
    quantity.value = String(item.quantity);
    quantity.disabled = !editable;
    quantity.setAttribute('aria-label', `Anzahl ${item.name}`);
    controls.append(quantity);
    controls.append(element('span', 'srd-inv-total', kg(item.totalKg)));
    if (editable) {
      quantity.addEventListener('change', () => change(`/${item.id}`, 'PATCH', { quantity: Number(quantity.value) }));
      if (['armor', 'shield', 'weapon'].includes(item.kind)) {
        const verb = item.kind === 'weapon' ? ['In die Hand', 'Weglegen'] : ['Anlegen', 'Ablegen'];
        controls.append(button(item.equipped ? verb[1] : verb[0], 'srd-inv-btn', () => change(`/${item.id}`, 'PATCH', { equipped: !item.equipped })));
      }
      controls.append(button('Entfernen', 'srd-inv-btn srd-inv-danger', () => change(`/${item.id}`, 'DELETE', undefined, `${item.name} entfernt.`)));
    }
    row.append(controls);
    return row;
  }

  function addBlock() {
    const wrap = element('div', 'srd-inv-add');
    const search = element('input', 'srd-inv-search');
    search.type = 'search';
    search.id = 'srdInvSearch';
    search.placeholder = 'Gegenstand suchen (z. B. Seil, Langschwert)';
    const results = element('select', 'srd-inv-select');
    results.id = 'srdInvResults';
    results.size = 1;
    const quantity = element('input', 'srd-inv-qty');
    quantity.type = 'number';
    quantity.min = '1';
    quantity.max = '9999';
    quantity.value = '1';
    quantity.id = 'srdInvAddQty';
    const entries = catalogEntries(srdCreatorData);
    function fill() {
      const term = search.value.trim().toLocaleLowerCase('de');
      const matches = entries.filter((entry) => !term || entry.name.toLocaleLowerCase('de').includes(term)).slice(0, 60);
      results.replaceChildren(...matches.map((entry) => {
        const extra = [KIND_LABELS[entry.kind], costText(entry.costCp), entry.weightKg ? kg(entry.weightKg) : ''].filter(Boolean).join(', ');
        return new Option(`${entry.name} (${extra})`, entry.id);
      }));
    }
    search.addEventListener('input', fill);
    fill();
    const row = element('div', 'srd-inv-add-row');
    row.append(labelled('Aus dem Regelwerk', search, 'srd-inv-field srd-inv-grow'), labelled('Treffer', results, 'srd-inv-field srd-inv-grow'), labelled('Anzahl', quantity));
    row.append(button('Hinzufügen', 'srd-inv-btn srd-inv-primary', () => {
      if (!results.value) return;
      change('', 'POST', { itemId: results.value, quantity: Number(quantity.value) }, 'Gegenstand hinzugefügt.');
    }));
    wrap.append(row);

    const name = element('input', 'srd-inv-search');
    name.id = 'srdInvCustomName';
    name.maxLength = 100;
    const weight = element('input', 'srd-inv-qty');
    weight.type = 'number';
    weight.min = '0';
    weight.step = '0.1';
    weight.value = '0';
    weight.id = 'srdInvCustomWeight';
    const customQty = element('input', 'srd-inv-qty');
    customQty.type = 'number';
    customQty.min = '1';
    customQty.value = '1';
    customQty.id = 'srdInvCustomQty';
    const custom = element('div', 'srd-inv-add-row');
    custom.append(labelled('Eigener Gegenstand', name, 'srd-inv-field srd-inv-grow'), labelled('kg je Stück', weight), labelled('Anzahl', customQty));
    custom.append(button('Eigenen anlegen', 'srd-inv-btn', () => {
      change('', 'POST', { custom: { name: name.value, weightKg: Number(weight.value), quantity: Number(customQty.value) } }, 'Eigener Gegenstand angelegt.');
    }));
    wrap.append(custom);
    return wrap;
  }

  function render() {
    const root = document.getElementById('srdInventory');
    if (!root || !current) return;
    const payload = current.payload;
    root.replaceChildren();
    root.append(element('div', 'srd-sheet-subtitle', 'Inventar und Angriffe'));
    const status = element('div', `srd-inv-status${current.error ? ' is-error' : ''}`, current.error || current.notice || '');
    status.id = 'srdInvStatus';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    root.append(status);

    if (!payload.seeded) root.append(seedBlock(payload));
    if (payload.pending.length) root.append(pendingBlock(payload.pending));
    root.append(weightBar(payload.weight));
    payload.findings.forEach((finding) => root.append(element('div', `srd-inv-warn${finding.severity === 'error' ? ' is-error' : ''}`, finding.message)));

    root.append(element('div', 'srd-sheet-subtitle', 'Angriffe'));
    root.append(attacksBlock(payload));

    root.append(element('div', 'srd-sheet-subtitle', 'Münzen'));
    root.append(coinsBlock(payload));

    root.append(element('div', 'srd-sheet-subtitle', `Gegenstände (${payload.items.length})`));
    if (payload.items.length) {
      const list = element('ul', 'srd-inv-items');
      payload.items.forEach((item) => list.append(itemRow(item)));
      root.append(list);
    } else {
      root.append(element('div', 'sheet-empty', 'Noch keine Gegenstände.'));
    }
    if (editable) root.append(addBlock());
  }

  /* Loads the inventory into #srdInventory; `onChange(payload)` lets the sheet refresh derived values like the armor class. */
  window.loadSrdInventory = async function (character, onChange) {
    const root = document.getElementById('srdInventory');
    if (!root) return;
    try {
      const payload = await auth.makeAuthRequest(`/api/srd-creator/characters/${character.id}/inventory`);
      current = { character, payload, onChange, notice: '', error: '' };
      render();
    } catch (error) {
      root.replaceChildren(element('div', 'sheet-empty', 'Das Inventar konnte nicht geladen werden.'));
    }
  };
})();
