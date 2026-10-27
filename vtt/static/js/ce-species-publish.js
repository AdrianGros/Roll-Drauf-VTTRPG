// Creation Engine companion: make a saved Eagle Species playable (check, VTT supplement, publish).
// Eagle Homebrew itself stays unmodified; this panel only talks to /api/ce/authoring/species/*.
(function () {
  'use strict';

  const API = '/api/ce/authoring';
  const SAMPLE_KEY = 'ce.duckfolk.pending';
  const $ = (id) => document.getElementById(id);
  const state = { species: [], skills: [], worlds: [], checked: null, choiceId: 'skill-choice', actionId: 'telekinesis' };

  async function call(path, method = 'GET', body = null) {
    const options = { method, credentials: 'include', headers: window.Auth.buildHeaders(method, body !== null) };
    if (body !== null) options.body = JSON.stringify(body);
    let response;
    try { response = await fetch(path, options); } catch (error) { return { ok: false, status: 0, data: {} }; }
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, status: response.status, data };
  }

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function world() {
    return ($('ce-world') && $('ce-world').value) || 'personal';
  }

  function supplement() {
    const out = { schema: 'roll-drauf.species-supplement.v1', skillChoices: [], actions: [], traits: [] };
    const options = [...document.querySelectorAll('#ce-species-skills input:checked')].map((box) => box.value);
    if (options.length) {
      out.skillChoices.push({ id: state.choiceId, label: $('ce-species-skill-label').value.trim() || 'Fertigkeitswahl', options });
    }
    if ($('ce-species-action-on').checked) {
      out.actions.push({
        id: state.actionId, name: $('ce-species-action-name').value.trim(), kind: 'object-telekinesis',
        activation: $('ce-species-action-activation').value, uses: 'at-will',
        rangeFeet: Number($('ce-species-action-range').value), maxWeightLb: Number($('ce-species-action-weight').value),
        maxMoveFeet: Number($('ce-species-action-move').value), description: $('ce-species-action-description').value,
      });
    }
    return out;
  }

  function fill(saved) {
    const choice = (saved && saved.skillChoices && saved.skillChoices[0]) || null;
    state.choiceId = choice ? choice.id : 'skill-choice';
    $('ce-species-skill-label').value = choice ? choice.label : '';
    document.querySelectorAll('#ce-species-skills input').forEach((box) => { box.checked = Boolean(choice && choice.options.includes(box.value)); });
    const action = (saved && saved.actions && saved.actions[0]) || null;
    state.actionId = action ? action.id : 'telekinesis';
    $('ce-species-action-on').checked = Boolean(action);
    $('ce-species-action-name').value = action ? action.name : '';
    $('ce-species-action-activation').value = action ? action.activation : 'action';
    $('ce-species-action-range').value = action ? action.rangeFeet : 30;
    $('ce-species-action-weight').value = action ? action.maxWeightLb : 10;
    $('ce-species-action-move').value = action ? action.maxMoveFeet : 30;
    $('ce-species-action-description').value = action ? action.description : '';
  }

  function restoreSample() {
    let pending;
    try { pending = JSON.parse(sessionStorage.getItem(SAMPLE_KEY) || 'null'); } catch (error) { return; }
    if (!pending || pending.world !== world()) return;
    const select = $('ce-species-source');
    if (![...select.options].some((option) => option.value === pending.uuid)) return;
    select.value = pending.uuid;
    fill(pending.supplement);
    $('ce-species-report').replaceChildren(el('p', 'Duckfolk ist als normaler Eagle-Entwurf angelegt. Prüfe die Regeln und wähle, ob du ihn persönlich, für eine Kampagne oder im VTT-Compendium veröffentlichst.', 'ce-species-ok'));
    sessionStorage.removeItem(SAMPLE_KEY);
  }

  async function createSample() {
    const button = $('ce-species-example');
    button.disabled = true;
    try {
      const example = await call('/static/examples/duckfolk-2024.json');
      if (!example.ok || !example.data.source || !example.data.supplement) throw new Error('Das Duckfolk-Beispiel konnte nicht geladen werden.');
      const bytes = new Uint8Array(8);
      window.crypto.getRandomValues(bytes);
      const id = `D${[...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('').slice(0, 15)}`;
      const result = await call(`${API}/request`, 'POST', {
        world: world(), type: 'document.create',
        payload: { target: { world: 'Item' }, id, data: example.data.source },
      });
      if (!result.ok || !result.data.ok) throw new Error(result.data.detail || 'Duckfolk konnte nicht angelegt werden.');
      sessionStorage.setItem(SAMPLE_KEY, JSON.stringify({ world: world(), uuid: `Item.${id}`, supplement: example.data.supplement }));
      window.location.reload();
    } catch (error) {
      $('ce-species-report').replaceChildren(el('p', error.message || 'Duckfolk konnte nicht angelegt werden.', 'ce-species-blocked'));
      button.disabled = false;
    }
  }

  function renderReport(result) {
    const box = $('ce-species-report');
    box.replaceChildren();
    const report = result.report || {};
    box.append(el('p', report.playable ? 'Spielbar: alle Felder sind übernommen oder als Text markiert.' : 'Noch nicht spielbar: Behebe die blockierenden Punkte.',
      report.playable ? 'ce-species-ok' : 'ce-species-blocked'));
    const list = el('ul', '', 'ce-species-entries');
    const labels = { converted: 'übernommen', narrative: 'nur Text', ignored: 'ignoriert', blocked: 'blockiert' };
    (report.entries || []).forEach((entry) => {
      const item = el('li', '', `ce-species-${entry.status}`);
      item.append(el('strong', `${labels[entry.status] || entry.status} · ${entry.path}: `), document.createTextNode(entry.message));
      list.append(item);
    });
    box.append(list);
  }

  async function check() {
    const uuid = $('ce-species-source').value;
    if (!uuid) return;
    const result = await call(`${API}/species/check`, 'POST', { world: world(), uuid, supplement: supplement() });
    if (!result.ok) {
      $('ce-species-report').replaceChildren(el('p', result.data.detail || 'Die Prüfung ist fehlgeschlagen.', 'ce-species-blocked'));
      state.checked = null;
      $('ce-species-publish').disabled = true;
      return;
    }
    state.checked = result.data;
    renderReport(result.data);
    $('ce-species-publish').disabled = !result.data.report.playable;
  }

  async function publish() {
    if (!state.checked) return;
    const result = await call(`${API}/species/publish`, 'POST', {
      world: world(), uuid: $('ce-species-source').value, supplement: supplement(),
      scope: $('ce-species-scope').value, expectedDigest: state.checked.source.digest,
    });
    const box = $('ce-species-report');
    if (result.ok) {
      const revision = result.data.revision;
      box.prepend(el('p', result.data.created ? `Veröffentlicht als Fassung ${revision.revision}. ${revision.scope.kind === 'global' ? 'Alle VTT-Nutzer können sie im Charakter-Ersteller wählen.' : 'Berechtigte Spielerinnen und Spieler finden sie im Charakter-Ersteller.'}`
        : `Unverändert: Fassung ${revision.revision} ist bereits veröffentlicht.`, 'ce-species-ok'));
      await loadGlobal();
    } else {
      if (result.data.report) renderReport(result.data);
      box.prepend(el('p', result.data.detail || 'Veröffentlichen fehlgeschlagen.', 'ce-species-blocked'));
    }
    $('ce-species-publish').disabled = true;
  }

  async function loadGlobal() {
    const list = $('ce-species-global-list');
    if (!list) return;
    const response = await call('/api/srd-creator/species-catalog');
    if (!response.ok) {
      list.replaceChildren(el('li', 'Das VTT-Compendium konnte nicht geladen werden.'));
      return;
    }
    const entries = (response.data.species || []).filter((entry) => entry.origin?.scope?.kind === 'global');
    list.replaceChildren(...entries.map((entry) => {
      const origin = entry.origin;
      const item = el('li');
      item.append(el('strong', entry.name), document.createTextNode(
        ` · 2024 · Fassung ${origin.revision} · von ${origin.author || 'VTT-Nutzer'}`));
      if (origin.description) item.append(el('p', origin.description));
      return item;
    }));
    if (!entries.length) list.replaceChildren(el('li', 'Noch keine VTT-weiten Spezies veröffentlicht.'));
  }

  async function refresh() {
    const listing = await call(`${API}/documents?world=${encodeURIComponent(world())}&documentName=Item`);
    if (!listing.ok) return;
    state.species = [...(listing.data.world || []), ...(listing.data.library || [])].filter((row) => row.type === 'race');
    const select = $('ce-species-source');
    select.replaceChildren(...state.species.map((row) => {
      const option = el('option', `${row.name}${row.pack ? ' (Bibliothek)' : ''}`);
      option.value = row.uuid;
      return option;
    }));
    const scope = $('ce-species-scope');
    scope.replaceChildren(...state.worlds.map((entry) => {
      const option = el('option', entry.kind === 'personal' ? 'Nur für mich' : `Kampagne: ${entry.label}`);
      option.value = entry.id;
      return option;
    }), Object.assign(el('option', 'VTT-Compendium · für alle Nutzer'), { value: 'global' }));
    scope.value = world();
    $('ce-species-empty').hidden = state.species.length > 0;
    await loadSaved();
    restoreSample();
  }

  async function loadSaved() {
    const uuid = $('ce-species-source').value;
    const result = await call(`${API}/species/publications`);
    const saved = (result.data.publications || []).find((row) => row.sourceUuid === uuid);
    fill(saved ? saved.supplement : null);
    state.checked = null;
    $('ce-species-publish').disabled = true;
    $('ce-species-report').replaceChildren();
  }

  async function init() {
    const section = $('ce-species');
    if (!section || !window.Auth) return;
    const enabled = await call(`${API}/species/publications`);
    if (!enabled.ok) return;
    const [worlds, creator] = await Promise.all([call(`${API}/worlds`), call('/api/srd-creator/creator-data')]);
    state.worlds = (worlds.data.worlds || []);
    state.skills = (creator.data.skills || []);
    $('ce-species-skills').replaceChildren(...state.skills.map((skill) => {
      const label = el('label');
      const box = Object.assign(document.createElement('input'), { type: 'checkbox', value: skill.id });
      label.append(box, document.createTextNode(` ${skill.name}`));
      return label;
    }));
    section.hidden = false;
    await loadGlobal();
    $('ce-species-check').addEventListener('click', check);
    $('ce-species-example').addEventListener('click', createSample);
    $('ce-species-publish').addEventListener('click', publish);
    $('ce-species-source').addEventListener('change', loadSaved);
    section.addEventListener('input', (event) => {
      // Publication scope does not change the checked source or supplement.
      if (event.target.id === 'ce-species-scope') return;
      state.checked = null;
      $('ce-species-publish').disabled = true;
    });
    if ($('ce-world')) $('ce-world').addEventListener('change', refresh);
    await refresh();
  }

  document.addEventListener('DOMContentLoaded', init);
}());
