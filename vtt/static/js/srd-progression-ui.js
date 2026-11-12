globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/* Level, experience and level-up wizard of an SRD character sheet.
 * Relies on globals of character-sheet.html: auth, srdCreatorData, srdSubclassNames. */
(function () {
  'use strict';

  const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
  const ABILITY_NAMES = { str: globalThis.VTTUi("Stärke"), dex: globalThis.VTTUi("Geschicklichkeit"), con: globalThis.VTTUi("Konstitution"), int: globalThis.VTTUi("Intelligenz"), wis: globalThis.VTTUi("Weisheit"), cha: globalThis.VTTUi("Charisma") };
  const CHOICE_LABELS = {
    'primal-order': globalThis.VTTUi("Heilige Rolle"), 'divine-order': globalThis.VTTUi("Heilige Rolle"), 'fighting-style': globalThis.VTTUi("Kampfstil-Talent"),
    'weapon-mastery': globalThis.VTTUi("Waffenbeherrschung"), 'eldritch-invocations': globalThis.VTTUi("Schauerliche Anrufungen"),
    'thieves-cant-language': globalThis.VTTUi("Zusätzliche Sprache (Diebessprache)"), 'deft-explorer-languages': globalThis.VTTUi("Geschickter Erkunder: Sprachen"),
    'draconic-ancestry': globalThis.VTTUi("Drakonische Abstammung"), lineage: globalThis.VTTUi("Abstammung"), 'spellcasting-ability': globalThis.VTTUi("Zauberattribut"),
    'keen-senses': globalThis.VTTUi("Scharfe Sinne: Fertigkeit"), metamagic: globalThis.VTTUi("Metamagie"),
  };
  const OPTION_LABELS = { magician: globalThis.VTTUi("Magier"), warden: globalThis.VTTUi("Wächter"), protector: globalThis.VTTUi("Beschützer"), thaumaturge: globalThis.VTTUi("Thaumaturg") };
  const ERRORS = {
    forbidden: globalThis.VTTUi("Dafür fehlt dir die Berechtigung."),
    not_ready: globalThis.VTTUi("Für den nächsten Stufenaufstieg fehlen Erfahrungspunkte oder die Freigabe der Spielleitung."),
    max_level: globalThis.VTTUi("Stufe 20 ist bereits erreicht."),
    level_conflict: globalThis.VTTUi("Der Charakter hat sich inzwischen verändert. Lade den Bogen neu."),
    level_up_incomplete: globalThis.VTTUi("Der Stufenaufstieg ist noch nicht vollständig."),
    invalid_xp: globalThis.VTTUi("Erfahrungspunkte müssen eine ganze Zahl sein."),
    invalid_target: globalThis.VTTUi("Die Zielstufe muss zwischen 1 und 20 liegen."),
    invalid_mode: globalThis.VTTUi("Ungültiger Modus."),
    min_level: globalThis.VTTUi("Stufe 1 kann nicht weiter zurückgenommen werden."),
    level_down_incomplete: globalThis.VTTUi("Die Stufe lässt sich nicht sauber zurücknehmen."),
  };

  let current = null;
  let previewToken = 0;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function button(text, className, onClick) {
    const node = element('button', className || 'srd-prog-btn', text);
    node.type = 'button';
    node.addEventListener('click', onClick);
    return node;
  }

  function labelled(text, control) {
    const wrap = element('label', 'srd-prog-field');
    wrap.append(element('span', 'srd-prog-field-label', text), control);
    return wrap;
  }

  function numberText(value) {
    return Number(value || 0).toLocaleString(document.documentElement.lang === 'en' ? 'en-GB' : 'de-DE');
  }

  function failureText(error) {
    return ERRORS[error?.apiError] || error?.message || globalThis.VTTUi('Die Änderung ist fehlgeschlagen.');
  }

  function label(id) {
    return CHOICE_LABELS[id] || String(id).replace(/-/g, ' ');
  }

  function subclassName(id) {
    return (typeof srdSubclassNames !== 'undefined' && srdSubclassNames[id]) || String(id).split('subclass-').pop().replace(/-/g, ' ');
  }

  function classEntry(classKey) {
    return srdCreatorData.classes.find((entry) => entry.classKey === classKey);
  }

  function base(path) {
    return `/api/srd-creator/characters/${current.character.id}${path}`;
  }

  function setStatus(text, isError) {
    const node = document.getElementById('srdProgStatus');
    if (!node) return;
    node.textContent = text || '';
    node.className = `srd-prog-status${isError ? ' is-error' : ''}`;
  }

  // ----------------------------------------------------------------- overview

  function progressBar(status) {
    const wrap = element('div', 'srd-prog-bar');
    let text = globalThis.VTTUi('Stufe {level} · {xp} EP', {level: status.level, xp: numberText(status.xp)});
    let percent = 100;
    if (status.nextLevelXp != null) {
      const span = Math.max(status.nextLevelXp - status.currentLevelXp, 1);
      percent = Math.max(0, Math.min(100, Math.round(((status.xp - status.currentLevelXp) / span) * 100)));
      text += globalThis.VTTUi(" von {p0} bis Stufe {p1}",{p0:(numberText(status.nextLevelXp)),p1:(status.level + 1)});
    }
    if (status.mode === 'milestone') text += globalThis.VTTUi(" · Meilensteine");
    wrap.append(element('div', 'srd-prog-bar-text', text));
    const track = element('div', 'srd-prog-bar-track');
    const fill = element('div', 'srd-prog-bar-fill');
    fill.style.width = `${percent}%`;
    track.append(fill);
    track.setAttribute('role', 'img');
    track.setAttribute('aria-label', text);
    wrap.append(track);
    if (status.canLevelUp) {
      wrap.append(element('div', 'srd-prog-ready', globalThis.VTTUi("Bereit für Stufe {p0}{p1}.",{p0:(status.level + 1),p1:(status.targetLevel > status.level + 1 ? globalThis.VTTUi(' (freigegeben bis Stufe {level})', {level: status.targetLevel}) : '')})));
    } else if (status.mode === 'milestone' && status.level < status.maxLevel) {
      wrap.append(element('div', 'srd-prog-hint', globalThis.VTTUi("Der nächste Stufenaufstieg wird von der Spielleitung freigegeben.")));
    }
    return wrap;
  }

  function manageBlock(payload) {
    const status = payload.status;
    const wrap = element('div', 'srd-prog-manage');
    wrap.append(element('div', 'srd-sheet-subtitle', globalThis.VTTUi("Fortschritt verwalten")));

    const mode = element('select', 'srd-prog-select');
    mode.id = 'srdProgMode';
    [['xp', globalThis.VTTUi("Erfahrungspunkte")], ['milestone', globalThis.VTTUi("Meilensteine")]].forEach(([value, text]) => {
      const option = element('option', null, text);
      option.value = value;
      mode.append(option);
    });
    mode.value = status.mode;
    mode.addEventListener('change', () => save({ mode: mode.value }, 'Modus gespeichert.'));
    wrap.append(labelled(globalThis.VTTUi('Stufenaufstieg nach'), mode));

    if (status.mode === 'xp') {
      const amount = element('input', 'srd-prog-input');
      amount.type = 'number';
      amount.step = '1';
      amount.id = 'srdProgXpAmount';
      amount.placeholder = globalThis.VTTUi("z. B. 300");
      const note = element('input', 'srd-prog-input');
      note.type = 'text';
      note.maxLength = 200;
      note.id = 'srdProgXpNote';
      note.placeholder = globalThis.VTTUi("Notiz (optional)");
      const row = element('div', 'srd-prog-row');
      row.append(labelled(globalThis.VTTUi('EP vergeben (negativ zieht ab)'), amount), labelled(globalThis.VTTUi('Notiz'), note));
      row.append(button(globalThis.VTTUi('EP vergeben'), 'srd-prog-btn srd-prog-primary', () => {
        const value = Number(amount.value);
        if (!amount.value || !Number.isInteger(value)) { setStatus(globalThis.VTTUi("Gib eine ganze Zahl ein."), true); return; }
        save({ addXp: value, note: note.value }, globalThis.VTTUi('{sign}{xp} EP gespeichert.', {sign: value >= 0 ? '+' : '', xp: numberText(value)}));
      }));
      wrap.append(row);
    } else {
      const target = element('select', 'srd-prog-select');
      target.id = 'srdProgTarget';
      for (let level = 1; level <= status.maxLevel; level += 1) {
        const option = element('option', null, globalThis.VTTUi("Stufe {p0}",{p0:(level)}));
        option.value = String(level);
        target.append(option);
      }
      target.value = String(status.milestoneTarget || status.level);
      const row = element('div', 'srd-prog-row');
      row.append(labelled(globalThis.VTTUi('Freigegeben bis'), target));
      row.append(button(globalThis.VTTUi('Freigabe speichern'), 'srd-prog-btn srd-prog-primary', () => save({ milestoneTarget: Number(target.value) }, 'Freigabe gespeichert.')));
      wrap.append(row);
    }
    return wrap;
  }

  function historyBlock(payload) {
    const entries = (payload.history || []).slice().reverse();
    if (!entries.length) return null;
    const details = element('details', 'srd-prog-history');
    details.append(element('summary', null, globalThis.VTTUi("Verlauf ({p0})",{p0:(entries.length)})));
    const list = element('ul', 'srd-prog-history-list');
    entries.forEach((entry) => {
      let text = '';
      if (entry.type === 'xp') text = globalThis.VTTUi("EP {p0} → {p1}",{p0:(numberText(entry.from)),p1:(numberText(entry.to))});
      else if (entry.type === 'mode') text = entry.mode === 'xp' ? globalThis.VTTUi("Modus: Erfahrungspunkte") : globalThis.VTTUi("Modus: Meilensteine");
      else if (entry.type === 'milestone') text = globalThis.VTTUi("Freigabe bis Stufe {p0}",{p0:(entry.target ?? '–')});
      else if (entry.type === 'level-down') text = globalThis.VTTUi("Stufe {p0} → {p1} (zurückgenommen)",{p0:(entry.fromLevel),p1:(entry.toLevel)});
      else if (entry.type === 'level-up') text = globalThis.VTTUi("Stufe {p0} → {p1}{p2}",{p0:(entry.fromLevel),p1:(entry.toLevel),p2:(entry.hpGain != null ? globalThis.VTTUi(' ({sign}{hp} TP)', {sign: entry.hpGain >= 0 ? '+' : '', hp: entry.hpGain}) : '')});
      else if (entry.type === 'handout') text = globalThis.VTTUi("Von der Spielleitung ausgegeben: {p0}",{p0:(entry.label || globalThis.VTTUi('Gegenstand'))});
      else if (entry.type === 'take-back') text = globalThis.VTTUi("Von der Spielleitung zurückgenommen: {p0}",{p0:(entry.label || globalThis.VTTUi('Gegenstand'))});
      else return;
      if (entry.note) text += ` – ${entry.note}`;
      const item = element('li', null, text);
      if (entry.at) item.title = entry.at;
      list.append(item);
    });
    details.append(list);
    return details;
  }

  function levelDownBlock(payload) {
    const last = payload.lastLevel;
    const wrap = element('div', 'srd-prog-down');
    if (!current.confirmDown) {
      const open = button(globalThis.VTTUi('Letzte Stufe rückgängig machen'), 'srd-prog-btn', () => { current.confirmDown = true; render(); });
      open.id = 'srdProgDown';
      wrap.append(open);
      return wrap;
    }
    wrap.append(element('div', 'srd-prog-warn', globalThis.VTTUi("Stufe {p0} ({p1} {p2}) wird zurückgenommen: Trefferpunkte, Wahlen, Zauber und Erfahrung dieser Stufe entfallen. Erfahrungspunkte werden unter die Schwelle der nächsten Stufe gesetzt.",{p0:(payload.status.level),p1:(last.className),p2:(last.classLevel)})));
    const row = element('div', 'srd-prog-row');
    const yes = button(globalThis.VTTUi('Ja, Stufe {level} rückgängig machen', {level: payload.status.level}), 'srd-prog-btn srd-prog-primary', confirmLevelDown);
    yes.id = 'srdProgDownConfirm';
    row.append(yes, button(globalThis.VTTUi('Abbrechen'), 'srd-prog-btn', () => { current.confirmDown = false; render(); }));
    wrap.append(row);
    return wrap;
  }

  // The sheet's local lock / explicit view only ever removes actions; the server stays the authority.
  const locked = () => globalThis.SheetLock?.locked === true;

  async function confirmLevelDown() {
    if (locked()) return;
    try {
      const result = await auth.makeAuthRequest(base('/level-down'), 'POST', { expectedLevel: current.payload.status.level });
      current.confirmDown = false;
      current.wizard = null;
      current.payload = result;
      current.notice = globalThis.VTTUi('Stufe {removed} zurückgenommen, der Charakter ist jetzt Stufe {level}.', {removed: result.removed.totalLevel, level: result.level});
      render();
      current.onChange?.({ reload: true, level: result.level, message: current.notice });
    } catch (error) {
      current.confirmDown = false;
      render();
      setStatus(failureText(error), true);
    }
  }

  async function save(body, notice) {
    if (locked()) return;
    try {
      current.payload = await auth.makeAuthRequest(base('/progression'), 'PUT', body);
      current.notice = notice;
      current.error = '';
      render();
      current.onChange?.({ reload: false, xp: current.payload.status.xp });
    } catch (error) {
      setStatus(failureText(error), true);
    }
  }

  function focusKey() {
    const node = document.activeElement;
    const root = document.getElementById('srdProgression');
    if (!node || !root || !root.contains(node) || node === document.body) return null;
    return { id: node.id, value: node.value, tag: node.tagName, text: node.id ? '' : node.textContent };
  }

  function restoreFocus(key, root) {
    if (!key) return;
    let target = key.id ? document.getElementById(key.id) : null;
    if (!target && key.tag === 'INPUT' && key.value) target = root.querySelector(`input[type="checkbox"][value="${CSS.escape(key.value)}"]`);
    if (!target && key.tag === 'BUTTON' && key.text) target = Array.from(root.querySelectorAll('button')).find((b) => b.textContent === key.text);
    target?.focus({ preventScroll: true });
  }

  function render() {
    const root = document.getElementById('srdProgression');
    if (!root) return;
    const focus = focusKey();
    const payload = current.payload;
    root.replaceChildren();
    root.append(element('div', 'srd-sheet-subtitle', globalThis.VTTUi("Stufe und Erfahrung")));
    const status = element('div', 'srd-prog-status', current.notice || '');
    status.id = 'srdProgStatus';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    root.append(status);
    root.append(progressBar(payload.status));
    const readOnly = locked();
    if (readOnly) {
      current.wizard = null;
      current.confirmDown = false;
    }
    if (!readOnly && payload.canLevelUp && payload.status.canLevelUp) {
      root.append(button(globalThis.VTTUi('Stufe {level} aufsteigen', {level: payload.status.level + 1}), 'srd-prog-btn srd-prog-primary srd-prog-levelup', startWizard));
    }
    if (!readOnly && payload.canLevelDown) root.append(levelDownBlock(payload));
    if (!readOnly && payload.canManage) root.append(manageBlock(payload));
    const history = historyBlock(payload);
    if (history) root.append(history);
    if (current.wizard) root.append(wizardPanel());
    restoreFocus(focus, root);
  }

  // ------------------------------------------------------------------- wizard

  async function startWizard() {
    if (locked()) return;
    const classes = current.evaluation?.classes || [];
    if (!classes.length) return;
    current.wizard = {
      classKey: classes[0].classKey,
      hpMode: 'fixed',
      rolled: '',
      subclass: '',
      advancement: {},
      featureChoices: {},
      expertise: null,
      spells: null,
      multiclassSkills: null,
      result: null,
      error: '',
      busy: false,
    };
    render();
    await refreshPreview(true);
    document.getElementById('srdWizard')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function closeWizard() {
    current.wizard = null;
    previewToken += 1;
    render();
  }

  function payloadFromWizard() {
    const w = current.wizard;
    const need = w.result?.needs;
    const out = { classKey: w.classKey };
    out.hp = w.hpMode === 'fixed' || w.rolled === '' ? 'fixed' : Number(w.rolled);
    if (need?.subclass && w.subclass) out.subclass = w.subclass;
    if (need?.advancement && w.advancement.kind) {
      const adv = { kind: w.advancement.kind };
      if (adv.kind === 'asi') adv.increases = w.advancement.increases || {};
      if (adv.kind === 'feat') {
        if (w.advancement.featId) adv.featId = w.advancement.featId;
        if (w.advancement.increaseAbility) adv.increaseAbility = w.advancement.increaseAbility;
      }
      out.advancement = adv;
    }
    const choices = {};
    (need?.featureChoices || []).forEach((entry) => {
      const value = w.featureChoices[entry.id];
      if (value !== undefined && value !== '' && !(Array.isArray(value) && !value.length)) choices[entry.id] = value;
    });
    if (Object.keys(choices).length) out.featureChoices = choices;
    if (need?.multiclass?.skillChoices && w.multiclassSkills?.length) out.multiclassSkills = w.multiclassSkills;
    if (need?.expertise && w.expertise) out.expertise = w.expertise;
    if (need?.spells && w.spells) out.spells = w.spells;
    return out;
  }

  function seedFromNeeds(w, need) {
    if (need.multiclass?.skillChoices && w.multiclassSkills === null) w.multiclassSkills = need.multiclass.skillChoices.current.slice();
    if (need.expertise && w.expertise === null) w.expertise = need.expertise.current.slice();
    if (need.spells && w.spells === null) {
      w.spells = {
        cantrips: need.spells.cantrips.current.slice(),
        prepared: need.spells.prepared.current.slice(),
      };
      if (need.spells.spellbook) w.spells.spellbook = need.spells.spellbook.current.slice();
    }
    (need.featureChoices || []).forEach((entry) => {
      if (w.featureChoices[entry.id] === undefined) w.featureChoices[entry.id] = entry.kind === 'option' || entry.kind === 'feat-category' ? '' : (entry.current || []).slice();
    });
  }

  async function refreshPreview(first) {
    const w = current.wizard;
    if (!w) return;
    const token = ++previewToken;
    try {
      const result = await auth.makeAuthRequest(base('/level-up/preview'), 'POST', first ? { classKey: w.classKey } : payloadFromWizard());
      if (token !== previewToken || !current.wizard) return;
      w.result = result;
      w.error = '';
      seedFromNeeds(w, result.needs);
      if (first) {
        render();
      } else {
        updateFooter();
      }
    } catch (error) {
      if (token !== previewToken || !current.wizard) return;
      w.error = failureText(error);
      updateFooter();
    }
  }

  function change(mutator, rerender) {
    mutator(current.wizard);
    if (rerender) render();
    refreshPreview(false);
  }

  function chip(text) {
    return element('span', 'srd-prog-chip', text);
  }

  function section(title) {
    const box = element('div', 'srd-prog-step');
    box.append(element('h4', 'srd-prog-step-title', title));
    return box;
  }

  function hpStep(w, need) {
    const box = section(globalThis.VTTUi('Trefferpunkte'));
    const info = `W${need.hp.die} · Konstitutionsmodifikator ${need.hp.conModifier >= 0 ? '+' : ''}${need.hp.conModifier}`;
    box.append(element('p', 'srd-prog-hint', info));
    const group = element('div', 'srd-prog-row');
    group.setAttribute('role', 'group');
    group.setAttribute('aria-label', globalThis.VTTUi('Trefferpunkte'));
    const fixed = button(`Fest: ${need.hp.fixed}`, 'srd-prog-btn srd-prog-toggle', () => change((x) => { x.hpMode = 'fixed'; }, true));
    fixed.setAttribute('aria-pressed', String(w.hpMode === 'fixed'));
    const rolled = button(globalThis.VTTUi('Gewürfelt'), 'srd-prog-btn srd-prog-toggle', () => change((x) => { x.hpMode = 'rolled'; }, true));
    rolled.setAttribute('aria-pressed', String(w.hpMode === 'rolled'));
    group.append(fixed, rolled);
    box.append(group);
    if (w.hpMode === 'rolled') {
      const input = element('input', 'srd-prog-input');
      input.type = 'number';
      input.min = '1';
      input.max = String(need.hp.die);
      input.id = 'srdWizRolled';
      input.value = w.rolled;
      input.addEventListener('input', () => { w.rolled = input.value; refreshPreview(false); });
      box.append(labelled(`Wurf auf dem W${need.hp.die} (1 bis ${need.hp.die})`, input));
    }
    return box;
  }

  function subclassStep(w, need) {
    const box = section(globalThis.VTTUi('Unterklasse'));
    const select = element('select', 'srd-prog-select');
    select.id = 'srdWizSubclass';
    const blank = element('option', null, globalThis.VTTUi("Bitte wählen"));
    blank.value = '';
    select.append(blank);
    need.subclass.options.forEach((id) => {
      const option = element('option', null, subclassName(id));
      option.value = id;
      select.append(option);
    });
    select.value = w.subclass;
    select.addEventListener('change', () => change((x) => { x.subclass = select.value; }, false));
    box.append(labelled(globalThis.VTTUi('Wähle deine Unterklasse'), select));
    return box;
  }

  function advancementStep(w, need) {
    const epic = need.advancement.epicBoon;
    const box = section(epic ? globalThis.VTTUi('Epische Gabe') : globalThis.VTTUi('Attributswerterhöhung oder Talent'));
    const adv = w.advancement;
    const group = element('div', 'srd-prog-row');
    group.setAttribute('role', 'group');
    group.setAttribute('aria-label', globalThis.VTTUi('Art der Verbesserung'));
    const asi = button(globalThis.VTTUi('Attributswerterhöhung'), 'srd-prog-btn srd-prog-toggle', () => change((x) => { x.advancement = { kind: 'asi', mode: 'two', increases: {} }; }, true));
    asi.setAttribute('aria-pressed', String(adv.kind === 'asi'));
    const feat = button(epic ? globalThis.VTTUi('Epische Gabe') : globalThis.VTTUi('Talent'), 'srd-prog-btn srd-prog-toggle', () => change((x) => { x.advancement = { kind: 'feat' }; }, true));
    feat.setAttribute('aria-pressed', String(adv.kind === 'feat'));
    group.append(asi, feat);
    box.append(group);

    const abilityOptions = (allowed, selected, onPick, text, id) => {
      const select = element('select', 'srd-prog-select');
      select.id = id;
      const blank = element('option', null, globalThis.VTTUi("Bitte wählen"));
      blank.value = '';
      select.append(blank);
      allowed.forEach((key) => {
        const option = element('option', null, ABILITY_NAMES[key]);
        option.value = key;
        select.append(option);
      });
      select.value = selected || '';
      select.addEventListener('change', () => onPick(select.value));
      return labelled(text, select);
    };

    if (adv.kind === 'asi') {
      const mode = adv.mode || 'two';
      const modes = element('div', 'srd-prog-row');
      const two = button(globalThis.VTTUi('+2 auf ein Attribut'), 'srd-prog-btn srd-prog-toggle', () => change((x) => { x.advancement = { kind: 'asi', mode: 'two', increases: {} }; }, true));
      two.setAttribute('aria-pressed', String(mode === 'two'));
      const ones = button(globalThis.VTTUi('+1 auf zwei Attribute'), 'srd-prog-btn srd-prog-toggle', () => change((x) => { x.advancement = { kind: 'asi', mode: 'ones', increases: {} }; }, true));
      ones.setAttribute('aria-pressed', String(mode === 'ones'));
      modes.append(two, ones);
      box.append(modes);
      const increases = adv.increases || {};
      if (mode === 'two') {
        const picked = Object.keys(increases)[0];
        box.append(abilityOptions(ABILITIES, picked, (value) => change((x) => { x.advancement.increases = value ? { [value]: 2 } : {}; }, false), '+2 auf', 'srdWizAsiA'));
      } else {
        const picked = Object.keys(increases);
        [0, 1].forEach((n) => {
          const allowed = ABILITIES.filter((key) => key === picked[n] || !picked.includes(key));
          box.append(abilityOptions(allowed, picked[n], (value) => change((x) => {
            const next = picked.slice();
            if (value) next[n] = value; else next.splice(n, 1);
            x.advancement.increases = Object.fromEntries(next.filter(Boolean).map((key) => [key, 1]));
          }, true), `+1 auf (${n + 1})`, `srdWizAsiO${n}`));
        });
      }
    } else if (adv.kind === 'feat') {
      const category = epic ? 'Epische-Gabe-Talent' : 'Allgemeines Talent';
      const feats = srdCreatorData.feats.filter((f) => f.category === category && f.id !== 'feats.descriptions.ability-score-improvement');
      const select = element('select', 'srd-prog-select');
      select.id = 'srdWizFeat';
      const blank = element('option', null, globalThis.VTTUi("Bitte wählen"));
      blank.value = '';
      select.append(blank);
      feats.forEach((f) => {
        const option = element('option', null, f.name + (f.prerequisite?.raw ? ` (${f.prerequisite.raw})` : ''));
        option.value = f.id;
        select.append(option);
      });
      select.value = adv.featId || '';
      select.addEventListener('change', () => change((x) => { x.advancement.featId = select.value || undefined; delete x.advancement.increaseAbility; }, true));
      box.append(labelled(globalThis.VTTUi('Talent'), select));
      const chosen = srdCreatorData.feats.find((f) => f.id === adv.featId);
      if (chosen?.abilityIncrease) {
        const allowed = chosen.abilityIncrease.abilities === 'any' ? ABILITIES : chosen.abilityIncrease.abilities;
        box.append(abilityOptions(allowed, adv.increaseAbility, (value) => change((x) => { x.advancement.increaseAbility = value || undefined; }, false), `${chosen.name}: +1 auf`, 'srdWizFeatAbility'));
      }
    }
    return box;
  }

  function checklist(options, picked, limit, onChange, locked) {
    const wrap = element('div', 'srd-prog-checks');
    options.forEach((entry) => {
      const row = element('label', 'srd-prog-check');
      const box = element('input');
      box.type = 'checkbox';
      box.value = entry.id;
      box.checked = picked.includes(entry.id);
      const isLocked = locked?.includes(entry.id);
      box.disabled = Boolean(isLocked) || (!box.checked && limit != null && picked.length >= limit);
      box.addEventListener('change', () => {
        const next = box.checked ? picked.concat(entry.id) : picked.filter((id) => id !== entry.id);
        onChange(next);
      });
      row.append(box, element('span', null, entry.name));
      if (entry.sub) row.append(element('small', null, entry.sub));
      row.dataset.search = `${entry.name} ${entry.sub || ''}`.toLowerCase();
      wrap.append(row);
    });
    return wrap;
  }

  function counter(have, need) {
    const node = element('div', `srd-prog-counter${have === need ? ' is-done' : ''}`, globalThis.VTTUi("{p0} von {p1} gewählt",{p0:(have),p1:(need)}));
    node.setAttribute('aria-live', 'polite');
    return node;
  }

  function filterable(list) {
    const wrap = element('div', 'srd-prog-filterable');
    if (list.children.length > 12) {
      const search = element('input', 'srd-prog-input');
      search.type = 'search';
      search.placeholder = globalThis.VTTUi("Suchen");
      search.setAttribute('aria-label', globalThis.VTTUi('Liste durchsuchen'));
      search.addEventListener('input', () => {
        const needle = search.value.trim().toLowerCase();
        list.querySelectorAll('.srd-prog-check').forEach((row) => { row.hidden = Boolean(needle) && !row.dataset.search.includes(needle); });
      });
      wrap.append(search);
    }
    wrap.append(list);
    return wrap;
  }

  function weaponAllowed(entry, weapon) {
    return entry.weaponProficiencies.some((g) => g.category === weapon.category && (!g.requiresProperty || weapon.properties.some((p) => g.requiresProperty.includes(p.name))));
  }

  function featureChoiceStep(w, need, pending) {
    const entry = classEntry(w.classKey);
    const definition = entry.featureChoices.find((c) => c.id === pending.id);
    const box = section(`${label(pending.id)}${definition ? ` (${entry.name})` : ''}`);
    const value = w.featureChoices[pending.id];
    if (pending.kind === 'option') {
      const row = element('div', 'srd-prog-row');
      Object.keys(definition.options).forEach((id) => {
        const pick = button(OPTION_LABELS[id] || id.replace(/-/g, ' '), 'srd-prog-btn srd-prog-toggle', () => change((x) => { x.featureChoices[pending.id] = id; }, true));
        pick.setAttribute('aria-pressed', String(value === id));
        row.append(pick);
      });
      box.append(row);
      return box;
    }
    if (pending.kind === 'feat-category') {
      const select = element('select', 'srd-prog-select');
      select.id = `srdWizChoice-${pending.id}`;
      const blank = element('option', null, globalThis.VTTUi("Bitte wählen"));
      blank.value = '';
      select.append(blank);
      srdCreatorData.feats.filter((f) => f.category.startsWith(definition.category)).forEach((f) => {
        const option = element('option', null, f.name);
        option.value = f.id;
        select.append(option);
      });
      select.value = value || '';
      select.addEventListener('change', () => change((x) => { x.featureChoices[pending.id] = select.value; }, false));
      box.append(labelled(definition.category, select));
      return box;
    }
    let options = [];
    const classLevel = need.newClassLevel;
    if (pending.kind === 'weapon-mastery') {
      options = srdCreatorData.equipment.weapons
        .filter((wp) => weaponAllowed(entry, wp) && (!/-melee$/.test(definition.weapons || '') || wp.kind === 'melee'))
        .map((wp) => ({ id: wp.id, name: wp.name, sub: wp.mastery }));
    } else if (pending.kind === 'class-option') {
      options = srdCreatorData.classOptions
        .filter((o) => o.classKey === w.classKey && o.kind === definition.optionKind && (o.minClassLevel || 1) <= classLevel)
        .map((o) => ({ id: o.id, name: o.name, sub: [o.prerequisite, o.cost].filter(Boolean).join(' · ') || null }));
    } else if (pending.kind === 'language') {
      options = srdCreatorData.languages.filter((l) => !l.automatic).map((l) => ({ id: l.id, name: l.name }));
    }
    const elsewhere = Object.entries(w.featureChoices)
      .filter(([id, v]) => id !== pending.id && Array.isArray(v))
      .flatMap(([, v]) => v);
    const locked = need.featureChoices.find((c) => c.id === pending.id)?.current || [];
    options = options.filter((o) => !elsewhere.includes(o.id));
    const picked = Array.isArray(value) ? value : [];
    box.append(counter(picked.length, pending.need));
    box.append(element('p', 'srd-prog-hint', globalThis.VTTUi("Bereits gewählte Einträge bleiben erhalten; wähle zusätzlich die fehlenden.")));
    box.append(filterable(checklist(options, picked, pending.need, (next) => change((x) => { x.featureChoices[pending.id] = next; }, true), locked)));
    return box;
  }

  function multiclassStep(w, need) {
    const info = need.multiclass;
    const box = section(`Mehrklassigkeit: ${need.className}`);
    if (info.grants.source) box.append(element('p', 'srd-prog-hint', info.grants.source));
    if (info.skillChoices) {
      const options = info.skillChoices.options
        ? info.skillChoices.options.map((id) => ({ id, name: current.evaluation?.skills?.[id]?.name || srdCreatorData.skills.find((s) => s.id === id)?.name || id }))
        : srdCreatorData.skills.map((s) => ({ id: s.id, name: s.name }));
      const picked = w.multiclassSkills || [];
      box.append(element('h5', 'srd-prog-sub', globalThis.VTTUi('Fertigkeit')), counter(picked.length, info.skillChoices.count));
      box.append(checklist(options, picked, info.skillChoices.count, (next) => change((x) => { x.multiclassSkills = next; }, true)));
    }
    return box;
  }

  function expertiseStep(w, need) {
    const box = section(globalThis.VTTUi('Expertise'));
    const skills = current.evaluation?.skills || {};
    const gained = w.multiclassSkills || [];
    const pool = Object.entries(skills)
      .filter(([id, row]) => row.proficiency === 'proficient' || row.proficiency === 'expertise' || gained.includes(id))
      .map(([id, row]) => ({ id, name: row.name }));
    const picked = w.expertise || [];
    const total = need.expertise.current.length + need.expertise.add;
    box.append(counter(picked.length, total));
    box.append(checklist(pool, picked, total, (next) => change((x) => { x.expertise = next; }, true), need.expertise.current));
    return box;
  }

  function spellsStep(w, need) {
    const box = section(globalThis.VTTUi('{className}: Zauber', {className: need.className}));
    const spells = need.spells;
    const lists = srdCreatorData.spellLists[w.classKey] || [];
    const meta = srdCreatorData.spells;
    const entryOf = (id) => ({ id, name: meta[id].name, sub: meta[id].level === 0 ? globalThis.VTTUi('Zaubertrick') : globalThis.VTTUi('Grad {level}', {level: meta[id].level}) });
    const cantrips = lists.filter((id) => meta[id].level === 0).map(entryOf);
    const leveled = lists.filter((id) => meta[id].level >= 1 && meta[id].level <= spells.maxGrade).map(entryOf);
    const set = (field, next) => change((x) => { x.spells[field] = next; }, true);

    if (spells.cantrips.count) {
      box.append(element('h5', 'srd-prog-sub', globalThis.VTTUi('Zaubertricks')), counter(w.spells.cantrips.length, spells.cantrips.count));
      box.append(filterable(checklist(cantrips, w.spells.cantrips, spells.cantrips.count, (next) => set('cantrips', next))));
    }
    if (spells.spellbook) {
      box.append(element('h5', 'srd-prog-sub', globalThis.VTTUi('Zauberbuch')), counter(w.spells.spellbook.length, spells.spellbook.count));
      box.append(element('p', 'srd-prog-hint', globalThis.VTTUi("Zauber im Zauberbuch bleiben erhalten.")));
      box.append(filterable(checklist(leveled, w.spells.spellbook, spells.spellbook.count, (next) => change((x) => {
        x.spells.spellbook = next;
        x.spells.prepared = x.spells.prepared.filter((id) => next.includes(id));
      }, true), spells.spellbook.current)));
    }
    if (spells.prepared.count) {
      const pool = spells.spellbook ? leveled.filter((entry) => w.spells.spellbook.includes(entry.id)) : leveled;
      box.append(element('h5', 'srd-prog-sub', spells.spellbook ? globalThis.VTTUi('Vorbereitete Zauber (aus dem Zauberbuch)') : globalThis.VTTUi('Vorbereitete Zauber')), counter(w.spells.prepared.length, spells.prepared.count));
      box.append(filterable(checklist(pool, w.spells.prepared, spells.prepared.count, (next) => set('prepared', next))));
    }
    return box;
  }

  function wizardPanel() {
    const w = current.wizard;
    const panel = element('div', 'srd-prog-wizard');
    panel.id = 'srdWizard';
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', globalThis.VTTUi('Stufenaufstieg'));
    const need = w.result?.needs;
    if (!need) {
      panel.append(element('p', 'srd-prog-hint', w.error || globalThis.VTTUi("Lade Stufenaufstieg…")));
      if (w.error) panel.append(button(globalThis.VTTUi('Schließen'), 'srd-prog-btn', closeWizard));
      return panel;
    }
    const head = element('div', 'srd-prog-wizard-head');
    head.append(element('h3', 'srd-prog-wizard-title', globalThis.VTTUi("Stufe {p0}: {p1} {p2}",{p0:(need.newTotalLevel),p1:(need.className),p2:(need.newClassLevel)})));
    head.append(chip(globalThis.VTTUi('Übungsbonus +{bonus}', {bonus: need.proficiencyBonus})));
    panel.append(head);

    const options = current.payload.multiclassOptions || [];
    if (options.filter((o) => o.eligible).length > 1) {
      const select = element('select', 'srd-prog-select');
      select.id = 'srdWizClass';
      options.forEach((c) => {
        const option = element('option', null, c.owned ? `${c.name} ${c.level}` : globalThis.VTTUi("{p0} (neue Klasse){p1}",{p0:(c.name),p1:(c.eligible ? '' : globalThis.VTTUi(' – nicht verfügbar'))}));
        option.value = c.classKey;
        option.disabled = !c.eligible;
        if (c.reason) option.title = c.reason;
        select.append(option);
      });
      select.value = w.classKey;
      select.addEventListener('change', () => {
        current.wizard = { ...w, classKey: select.value, subclass: '', advancement: {}, featureChoices: {}, expertise: null, spells: null, multiclassSkills: null, result: null };
        render();
        refreshPreview(true);
      });
      panel.append(labelled(globalThis.VTTUi('Klasse'), select));
      const blocked = options.filter((o) => !o.eligible);
      if (blocked.length) {
        const details = element('details', 'srd-prog-history');
        details.append(element('summary', null, globalThis.VTTUi("Nicht verfügbare Klassen ({p0})",{p0:(blocked.length)})));
        const list = element('ul', 'srd-prog-history-list');
        blocked.forEach((o) => list.append(element('li', null, o.reason)));
        details.append(list);
        panel.append(details);
      }
    }

    if (need.features.length) {
      const features = element('div', 'srd-prog-features');
      features.append(element('span', 'srd-prog-field-label', globalThis.VTTUi("Neue Merkmale")));
      need.features.forEach((f) => features.append(chip(f.name)));
      panel.append(features);
    }

    panel.append(hpStep(w, need));
    if (need.multiclass) panel.append(multiclassStep(w, need));
    if (need.subclass) panel.append(subclassStep(w, need));
    if (need.advancement) panel.append(advancementStep(w, need));
    need.featureChoices.forEach((pending) => panel.append(featureChoiceStep(w, need, pending)));
    if (need.expertise && w.expertise) panel.append(expertiseStep(w, need));
    if (need.spells && w.spells) panel.append(spellsStep(w, need));

    const footer = element('div', 'srd-prog-footer');
    footer.id = 'srdWizFooter';
    panel.append(footer);
    queueMicrotask(updateFooter);
    return panel;
  }

  function updateFooter() {
    const footer = document.getElementById('srdWizFooter');
    const w = current?.wizard;
    if (!footer || !w) return;
    footer.replaceChildren();
    if (w.error) footer.append(element('div', 'srd-prog-warn is-error', w.error));
    const result = w.result;
    let ready = false;
    if (result) {
      const blockers = result.blockers || [];
      blockers.forEach((b) => footer.append(element('div', 'srd-prog-warn', b.message)));
      const gain = result.hpGain;
      footer.append(element('div', 'srd-prog-summary', globalThis.VTTUi("Trefferpunkte: {p0} ({p1}{p2}) · Übungsbonus +{p3} · Rüstungsklasse {p4}",{p0:(result.evaluation.hitPoints.max),p1:(gain >= 0 ? '+' : ''),p2:(gain),p3:(result.evaluation.proficiencyBonus),p4:(result.evaluation.armorClass.value)})));
      ready = !blockers.length && !w.error && (w.hpMode === 'fixed' || Number(w.rolled) >= 1) && !w.busy;
    }
    const confirm = button(w.busy ? globalThis.VTTUi('Speichere…') : globalThis.VTTUi('Stufe {level} bestätigen', {level: result?.needs?.newTotalLevel ?? ''}), 'srd-prog-btn srd-prog-primary', confirmLevelUp);
    confirm.id = 'srdWizConfirm';
    confirm.disabled = !ready;
    footer.append(confirm, button(globalThis.VTTUi('Abbrechen'), 'srd-prog-btn', closeWizard));
  }

  async function confirmLevelUp() {
    const w = current.wizard;
    if (!w?.result || locked()) return;
    w.busy = true;
    updateFooter();
    try {
      const body = { ...payloadFromWizard(), expectedLevel: current.payload.status.level };
      const result = await auth.makeAuthRequest(base('/level-up'), 'POST', body);
      current.wizard = null;
      current.payload = result;
      current.notice = globalThis.VTTUi('Aufgestiegen auf Stufe {level} ({sign}{hp} Trefferpunkte).', {level: result.level, sign: result.hpGain >= 0 ? '+' : '', hp: result.hpGain});
      render();
      current.onChange?.({ reload: true, level: result.level, message: current.notice });
    } catch (error) {
      w.busy = false;
      w.error = failureText(error);
      updateFooter();
    }
  }

  /* Loads level/XP into #srdProgression; `onChange({reload})` lets the sheet refresh after the level changed. */
  /* Redraws from the loaded payload after the sheet's lock changed; nothing is fetched or saved. */
  window.renderSrdProgression = () => { if (current?.payload) render(); };

  window.loadSrdProgression = async function (character, evaluation, onChange) {
    const root = document.getElementById('srdProgression');
    if (!root) return;
    try {
      const payload = await auth.makeAuthRequest(`/api/srd-creator/characters/${character.id}/progression`);
      current = { character, evaluation, payload, onChange, notice: '', wizard: null };
      render();
    } catch (error) {
      root.replaceChildren(element('div', 'sheet-empty', globalThis.VTTUi("Stufe und Erfahrung konnten nicht geladen werden.")));
    }
  };
})();
