/* Management of an SRD character sheet: companions plus duplicate, archive and rebuild-as-draft.
 * Relies on the global `auth` of character-sheet.html. */
(function () {
  'use strict';

  const FIELDS = [
    ['name', 'Name', 'text', 60], ['kind', 'Art (z. B. Wolf, Familiar)', 'text', 40], ['speed', 'Bewegung', 'text', 40],
    ['hpCurrent', 'TP aktuell', 'number', 9999], ['hpMax', 'TP max.', 'number', 9999], ['ac', 'RK', 'number', 50],
  ];
  const ERRORS = {
    forbidden: 'Dafür fehlt dir die Berechtigung.',
    in_campaign: 'Nimm den Charakter zuerst aus der Kampagne, bevor du ihn archivierst.',
    draft_limit: 'Es sind höchstens 25 offene Entwürfe möglich. Verwirf zuerst einen Entwurf.',
    too_many_companions: 'Höchstens 20 Begleiter.',
    invalid_companion: 'Ein Begleiter ist unvollständig oder zu lang.',
  };

  let state = null;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function button(text, className, onClick) {
    const node = element('button', className || 'srd-man-btn', text);
    node.type = 'button';
    node.addEventListener('click', onClick);
    return node;
  }

  function base(path) {
    return `/api/srd-creator/characters/${state.character.id}${path}`;
  }

  function failureText(error) {
    return ERRORS[error?.apiError] || error?.message || 'Die Aktion ist fehlgeschlagen.';
  }

  function setStatus(text, isError) {
    const node = document.getElementById('srdManageStatus');
    if (!node) return;
    node.textContent = text || '';
    node.className = `srd-man-status${isError ? ' is-error' : ''}`;
  }

  function blankCompanion() {
    return { id: null, name: '', kind: '', speed: '', hpCurrent: 0, hpMax: 0, ac: 10, attacks: '', notes: '' };
  }

  function companionCard(companion, index) {
    const card = element('div', 'srd-man-card');
    card.dataset.index = String(index);
    const grid = element('div', 'srd-man-grid');
    FIELDS.forEach(([key, labelText, type, limit]) => {
      const field = element('label', 'srd-man-field');
      field.append(element('span', 'srd-man-field-label', labelText));
      const input = element('input', 'srd-man-input');
      input.type = type;
      input.dataset.field = key;
      if (type === 'number') { input.min = '0'; input.max = String(limit); input.step = '1'; } else input.maxLength = limit;
      input.value = companion[key] ?? '';
      input.disabled = !state.canEdit;
      input.addEventListener('input', () => { companion[key] = type === 'number' ? (input.value === '' ? 0 : Number(input.value)) : input.value; });
      field.append(input);
      grid.append(field);
    });
    card.append(grid);
    [['attacks', 'Angriffe', 500], ['notes', 'Notizen', 2000]].forEach(([key, labelText, limit]) => {
      const field = element('label', 'srd-man-field');
      field.append(element('span', 'srd-man-field-label', labelText));
      const area = element('textarea', 'srd-man-input');
      area.rows = 2;
      area.maxLength = limit;
      area.dataset.field = key;
      area.value = companion[key] || '';
      area.disabled = !state.canEdit;
      area.addEventListener('input', () => { companion[key] = area.value; });
      field.append(area);
      card.append(field);
    });
    if (state.canEdit) {
      card.append(button('Begleiter entfernen', 'srd-man-btn srd-man-danger', () => {
        state.companions.splice(index, 1);
        render();
      }));
    }
    return card;
  }

  async function saveCompanions() {
    try {
      const result = await auth.makeAuthRequest(base('/companions'), 'PUT', { companions: state.companions });
      state.companions = result.companions;
      render();
      setStatus('Begleiter gespeichert.', false);
    } catch (error) {
      setStatus(failureText(error), true);
    }
  }

  async function act(path, body, onDone) {
    try {
      const result = await auth.makeAuthRequest(base(path), 'POST', body);
      onDone(result);
    } catch (error) {
      state.confirm = null;
      render();
      setStatus(failureText(error), true);
    }
  }

  function actionBar() {
    const bar = element('div', 'srd-man-actions');
    if (state.confirm) {
      bar.append(element('div', 'srd-man-warn', state.confirm.text));
      const yes = button(state.confirm.yes, 'srd-man-btn srd-man-primary', state.confirm.run);
      yes.id = 'srdManageConfirm';
      bar.append(yes, button('Abbrechen', 'srd-man-btn', () => { state.confirm = null; render(); }));
      return bar;
    }
    const ask = (text, yes, run) => () => { state.confirm = { text, yes, run }; render(); };
    const duplicate = button('Duplizieren', 'srd-man-btn', ask(
      'Eine eigenständige Kopie mit Inventar und Begleitern anlegen? Avatar und Kampagne werden nicht kopiert.',
      'Ja, duplizieren',
      () => act('/duplicate', undefined, (result) => { window.location.href = `/character-sheet?id=${result.character.id}`; }),
    ));
    duplicate.id = 'srdManageDuplicate';
    const archive = button(state.archived ? 'Wiederherstellen' : 'Archivieren', 'srd-man-btn', ask(
      state.archived ? 'Den Charakter wieder in die Liste aufnehmen?' : 'Den Charakter archivieren? Er verschwindet aus der Liste und bleibt im Archiv der Charakterseite erhalten.',
      state.archived ? 'Ja, wiederherstellen' : 'Ja, archivieren',
      () => act('/archive', { archived: !state.archived }, (result) => {
        state.archived = result.archived;
        state.confirm = null;
        if (result.archived) { window.location.href = '/characters'; return; }
        render();
        setStatus('Wiederhergestellt.', false);
      }),
    ));
    archive.id = 'srdManageArchive';
    if (!state.archived && state.inCampaign) {
      archive.disabled = true;
      archive.title = 'Nimm den Charakter zuerst aus der Kampagne.';
    }
    const rebuild = button('Neuaufbau als Entwurf', 'srd-man-btn', ask(
      'Aus diesem Charakter einen Entwurf im Regelwerk-Ersteller anlegen? Der Charakter bleibt unverändert; aus dem Entwurf entsteht ein zweiter Charakter.',
      'Ja, Entwurf anlegen',
      () => act('/to-draft', undefined, (result) => { window.location.href = `/srd-creator?draft=${result.draft.id}`; }),
    ));
    rebuild.id = 'srdManageRebuild';
    bar.append(duplicate, archive, rebuild);
    return bar;
  }

  function render() {
    const root = document.getElementById('srdManage');
    if (!root) return;
    root.replaceChildren();
    root.append(element('div', 'srd-sheet-subtitle', 'Begleiter und Verwaltung'));
    const status = element('div', 'srd-man-status');
    status.id = 'srdManageStatus';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    root.append(status);

    const list = element('div', 'srd-man-list');
    state.companions.forEach((companion, index) => list.append(companionCard(companion, index)));
    if (!state.companions.length) list.append(element('div', 'srd-man-hint', 'Keine Begleiter eingetragen (Tierbegleiter, Vertraute, Beschworene, Gefolge).'));
    root.append(list);
    if (state.canEdit) {
      const row = element('div', 'srd-man-actions');
      const add = button('Begleiter hinzufügen', 'srd-man-btn', () => {
        if (state.companions.length >= state.max) { setStatus(ERRORS.too_many_companions, true); return; }
        state.companions.push(blankCompanion());
        render();
      });
      add.id = 'srdManageAddCompanion';
      const save = button('Begleiter speichern', 'srd-man-btn srd-man-primary', saveCompanions);
      save.id = 'srdManageSaveCompanions';
      row.append(add, save);
      root.append(row);
      root.append(actionBar());
    }
  }

  window.loadSrdManage = async function (character) {
    const root = document.getElementById('srdManage');
    if (!root) return;
    try {
      const result = await auth.makeAuthRequest(`/api/srd-creator/characters/${character.id}/companions`);
      state = { character, companions: result.companions, max: result.maxCompanions, canEdit: result.canEdit, archived: result.archived, inCampaign: result.inCampaign, confirm: null };
      render();
    } catch (error) {
      root.replaceChildren(element('div', 'sheet-empty', 'Begleiter und Verwaltung konnten nicht geladen werden.'));
    }
  };
})();
