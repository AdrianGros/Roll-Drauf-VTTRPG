/* Inline, source-backed subclass features. Only DOM text/structured blocks. */
(function () {
  'use strict';
  const cache = new Map();
  function node(tag, text) { const n = document.createElement(tag); if (text != null) n.textContent = text; return n; }
  function entry(id) {
    const base = '/api/rulesets/srd-5.2.1-de/compendium/entry/';
    const url = base + encodeURIComponent(id);
    if (!cache.has(url)) cache.set(url, fetch(url, {credentials:'same-origin'}).then(r => {
      if (!r.ok) throw new Error('rule unavailable'); return r.json();
    }).catch(error => { cache.delete(url); throw error; }));
    return cache.get(url);
  }
  function block(b) {
    if (b.type === 'heading') return node('h5', b.text);
    if (b.type === 'paragraph') return node('p', b.text);
    if (['ordered-list','unordered-list'].includes(b.type)) {
      const n = node(b.type === 'ordered-list' ? 'ol' : 'ul');
      (b.items || []).forEach(i => n.append(node('li',i))); return n;
    }
    if (b.type === 'definition-list') {
      const n = node('dl'); (b.entries || []).forEach(e => n.append(node('dt',e.term),node('dd',e.definition))); return n;
    }
    if (b.type === 'table') {
      const wrap = node('div'); wrap.style.overflowX = 'auto'; const table = node('table');
      if (b.caption) table.append(node('caption',b.caption));
      const head = node('tr'); (b.columns || []).forEach(c => {const th=node('th',c);th.scope='col';head.append(th);});
      const thead=node('thead');thead.append(head);table.append(thead);const body=node('tbody');
      (b.rows || []).forEach(r => {const tr=node('tr');r.forEach(c => tr.append(node('td',c)));body.append(tr);});
      table.append(body);wrap.append(table);return wrap;
    }
    const n=node('aside');if(b.title)n.append(node('strong',b.title));if(b.text)n.append(node('p',b.text));return n;
  }
  function subclass(id, level, newLevelOnly = false) {
    const wrap=node('section');wrap.className='srd-rule-preview';wrap.dataset.subclassPreview=id;
    wrap.setAttribute('aria-live','polite');wrap.append(node('p',globalThis.VTTUi('Merkmale werden geladen …')));
    (async () => {
      const data=await entry(id);
      const features=await Promise.all((data.entity.features || []).map(entry));
      const reached=features.filter(f => newLevelOnly ? f.entity.level === level : f.entity.level <= level);
      wrap.replaceChildren(node('h4',globalThis.VTTUi('Unterklasse: {name}',{name:data.entity.name})));
      wrap.append(node('p',globalThis.VTTUi('Merkmale bis Klassenstufe {level}',{level})));
      if (!reached.length) wrap.append(node('p',globalThis.VTTUi('Auf dieser Stufe kommen keine neuen Unterklassenmerkmale hinzu.')));
      reached.forEach(f => {
        const detail=node('details');detail.open=true;detail.dataset.featureLevel=f.entity.level;
        detail.append(node('summary',globalThis.VTTUi('Stufe {level}: {name}',{level:f.entity.level,name:f.entity.name})));
        f.blocks.forEach(b => {if(b.ruleId !== f.entity.id)detail.append(block(b));});wrap.append(detail);
      });
      const later=features.filter(f => f.entity.level > level);
      if(later.length){const d=node('details');d.append(node('summary',globalThis.VTTUi('Spätere Unterklassenmerkmale')));
        later.forEach(f => d.append(node('p',globalThis.VTTUi('Stufe {level}: {name}',{level:f.entity.level,name:f.entity.name}))));wrap.append(d);}
    })().catch(() => wrap.replaceChildren(node('p',globalThis.VTTUi('Die Merkmale konnten nicht geladen werden. Öffne den Regeltext oder versuche es erneut.'))));
    return wrap;
  }
  window.SrdRulePreview=Object.freeze({subclass});
})();
