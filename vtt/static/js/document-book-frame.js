/* Shared document book frame for the six document surfaces (U01).
   Each template carries the frame markup itself: .dbf-book[data-book-frame][data-book-chapter] with a
   .dbf-spine, the page, and [data-book-running-head] / [data-book-folio] slots. This module only fills
   those slots from one chapter register: running head (chapter and current document), the chapter
   pager and the folio. It never moves, clones or re-renders document content, binds no handlers to it
   and leaves module lifecycles, deep links, polling and editors alone.
   Gated chapters (Creation Engine, Regelwerk) mirror the state of the shared ribbon entries, which
   their own hydrators already resolve; the pager never offers a chapter the ribbon withholds. */
(function () {
    'use strict';

    const CHAPTERS = Object.freeze([
        { key: 'conversations', href: '/conversations', name: 'Gespräche', en: 'Conversations',
            about: ['Briefe und Kampagnenräume', 'Letters and campaign rooms'] },
        { key: 'maps', href: '/mapmaker', name: 'Karten', en: 'Maps', about: ['Kartenwerkstatt', 'Map workshop'] },
        { key: 'atlas', href: '/atlas', name: 'Atlas', en: 'Atlas', about: ['Welten, Karten und Orte', 'Worlds, maps and places'] },
        { key: 'creation', href: '/api/ce/authoring', name: 'Creation Engine', en: 'Creation Engine',
            gate: '[data-creation-engine-nav]', about: ['Homebrew mit Eagle', 'Homebrew with Eagle'] },
        { key: 'rules', href: '/regelwerk', name: 'Regelwerk', en: 'Rulebook',
            gate: '[data-regelwerk-nav]', about: ['Systemreferenzdokument 5.2.1', 'System Reference Document 5.2.1'] },
        { key: 'compendium', href: '/regelwerk/compendium', name: 'Compendium', en: 'Compendium',
            about: ['Zauber, Monster, Gegenstände', 'Spells, monsters, items'] },
    ]);
    const MODES = ['reader', 'workspace', 'studio'];
    const RIBBONS = '.book-dashboard-ribbon, .vtt-map-nav';
    const rendered = new WeakMap();
    const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

    function locale() {
        const value = window.VTTI18n?.locale?.() || document.documentElement.lang || 'de';
        return String(value).slice(0, 2) === 'en' ? 'en' : 'de';
    }

    function fill(text, parameters = {}) {
        return String(text).replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => (own(parameters, name) ? String(parameters[name]) : match));
    }

    // The central catalog wins (VTTUi); until it carries a phrase, English uses the local label.
    function say(source, english, parameters = {}) {
        const local = fill(source, parameters);
        const translated = typeof globalThis.VTTUi === 'function' ? globalThis.VTTUi(source, parameters) : local;
        return locale() === 'en' && translated === local ? fill(english, parameters) : translated;
    }

    const chapterName = (chapter) => say(chapter.name, chapter.en);

    function contentLanguage() {
        const path = window.location.pathname;
        const match = path.match(/^\/regelwerk\/5\.2\.1\/(en|de)(?:\/|$)/);
        const selected = new URLSearchParams(window.location.search).get('locale');
        if (match) return { language: match[1], explicit: true };
        if (path === '/regelwerk/en') return { language: 'en', explicit: true };
        if (path.startsWith('/regelwerk') && ['en', 'de'].includes(selected)) return { language: selected, explicit: true };
        return { language: locale(), explicit: false };
    }

    function localizedHref(chapter, href) {
        if (!href || !['rules', 'compendium'].includes(chapter.key)) return href;
        const content = contentLanguage();
        if (!content.explicit && content.language === 'de') return href;
        if (chapter.key === 'compendium') return `/regelwerk/compendium?locale=${content.language}`;
        return content.language === 'en' ? '/regelwerk/5.2.1/en' : '/regelwerk?locale=de';
    }

    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function ribbonEntry(chapter) {
        for (const nav of document.querySelectorAll(RIBBONS)) {
            const entry = nav.querySelector(chapter.gate);
            if (entry) return entry;
        }
        return null;
    }

    function availability(chapter) {
        if (!chapter.gate) return { available: true, href: localizedHref(chapter, chapter.href) };
        const entry = ribbonEntry(chapter);
        const href = entry?.getAttribute('href');
        if (!entry || entry.hidden || entry.getAttribute('aria-disabled') === 'true' || !href) return { available: false, href: null };
        return { available: true, href: localizedHref(chapter, href) };
    }

    function neighbours(index) {
        const states = CHAPTERS.map(availability);
        const pick = (position) => ({ chapter: CHAPTERS[position], index: position, href: states[position].href });
        let previous = null;
        let next = null;
        for (let position = index - 1; position >= 0 && !previous; position -= 1) if (states[position].available) previous = pick(position);
        for (let position = index + 1; position < CHAPTERS.length && !next; position += 1) if (states[position].available) next = pick(position);
        return { previous, next };
    }

    // The documents set their own titles ("Kampf · Regelwerk · Roll Drauf VTT"); the running head shows
    // the part that names the current document and falls back to the chapter's subtitle.
    function currentTitle(chapter, root) {
        if (root.dataset.bookRunningTitle) return root.dataset.bookRunningTitle;
        const generic = new Set(['roll drauf', 'roll drauf vtt']);
        CHAPTERS.forEach((entry) => [entry.name, entry.en, chapterName(entry)].forEach((name) => generic.add(name.toLowerCase())));
        const parts = document.title.split(/\s+[·–—|]\s+/).map((part) => part.trim())
            .filter((part) => part && !generic.has(part.toLowerCase()));
        return parts.slice(0, 2).join(' · ') || say(chapter.about[0], chapter.about[1]);
    }

    function pagerLink(kind, target) {
        const link = element('a', `dbf-pager-link dbf-pager-${kind}`);
        const name = chapterName(target.chapter);
        link.href = target.href;
        link.rel = kind === 'previous' ? 'prev' : 'next';
        link.dataset.bookPager = kind;
        link.dataset.bookChapter = target.chapter.key;
        link.setAttribute('aria-label', kind === 'previous'
            ? say('Vorheriges Kapitel: {name}', 'Previous chapter: {name}', { name })
            : say('Nächstes Kapitel: {name}', 'Next chapter: {name}', { name }));
        if (window.self !== window.top) link.target = '_top';
        const arrow = element('span', 'dbf-pager-arrow', kind === 'previous' ? '‹' : '›');
        arrow.setAttribute('aria-hidden', 'true');
        const label = element('span', 'dbf-pager-name', name);
        if (kind === 'previous') link.append(arrow, label);
        else link.append(label, arrow);
        return link;
    }

    function pagerGap() {
        const gap = element('span', 'dbf-pager-gap');
        gap.setAttribute('aria-hidden', 'true');
        return gap;
    }

    function stateOf(root) {
        const index = CHAPTERS.findIndex((chapter) => chapter.key === root.dataset.bookChapter);
        if (index < 0) return null;
        const chapter = CHAPTERS[index];
        const { previous, next } = neighbours(index);
        return {
            chapter: chapter.key,
            name: chapterName(chapter),
            mode: MODES.includes(root.dataset.bookFrame) ? root.dataset.bookFrame : 'reader',
            index: index + 1,
            total: CHAPTERS.length,
            title: currentTitle(chapter, root),
            previous: previous && { chapter: previous.chapter.key, href: previous.href },
            next: next && { chapter: next.chapter.key, href: next.href },
            locale: locale(),
        };
    }

    function renderHead(slot, state) {
        const title = element('p', 'dbf-running-title');
        // The document's own h1 and <title> name the page for assistive technology; this line is typography.
        title.setAttribute('aria-hidden', 'true');
        const separator = element('span', 'dbf-running-sep', '·');
        title.append(element('span', 'dbf-running-chapter', state.name), separator, element('span', 'dbf-running-current', state.title));
        const rule = element('span', 'dbf-running-rule');
        rule.setAttribute('aria-hidden', 'true');

        const pager = element('nav', 'dbf-pager');
        pager.setAttribute('aria-label', say('Buchkapitel', 'Book chapters'));
        const lookup = (target) => target && { chapter: CHAPTERS.find((chapter) => chapter.key === target.chapter), href: target.href };
        const folio = element('span', 'dbf-pager-folio');
        const position = say('Kapitel {index} von {total}', 'Chapter {index} of {total}', { index: state.index, total: state.total });
        const spoken = element('span', 'dbf-sr', `${position}: ${state.name}`);
        const shown = element('span', '', `${state.index} / ${state.total}`);
        shown.setAttribute('aria-hidden', 'true');
        folio.append(spoken, shown);
        pager.append(state.previous ? pagerLink('previous', lookup(state.previous)) : pagerGap(), folio,
            state.next ? pagerLink('next', lookup(state.next)) : pagerGap());
        slot.replaceChildren(title, rule, pager);
    }

    function renderFolio(slot, state) {
        slot.setAttribute('aria-hidden', 'true');
        slot.textContent = String(state.index);
    }

    function render(root) {
        const state = stateOf(root);
        if (!state) return null;
        const signature = JSON.stringify(state);
        if (rendered.get(root) !== signature) {
            rendered.set(root, signature);
            root.querySelectorAll('[data-book-running-head]').forEach((slot) => renderHead(slot, state));
            root.querySelectorAll('[data-book-folio]').forEach((slot) => renderFolio(slot, state));
        }
        root.dataset.bookReady = 'true';
        return state;
    }

    // Completes missing frame parts of a template (spine, running-head slot) without touching content.
    function mount(root) {
        if (!root) return null;
        if (root.dataset.bookMounted === 'true') return render(root);
        if (!CHAPTERS.some((chapter) => chapter.key === root.dataset.bookChapter)) return null;
        if (!MODES.includes(root.dataset.bookFrame)) root.dataset.bookFrame = 'reader';
        if (!root.querySelector(':scope > .dbf-spine')) {
            const spine = element('div', 'dbf-spine');
            spine.setAttribute('aria-hidden', 'true');
            root.prepend(spine);
        }
        const page = root.querySelector(':scope > .dbf-page');
        if (page && !root.querySelector('[data-book-running-head]')) {
            const head = element('div', 'dbf-running-head');
            head.dataset.bookRunningHead = '';
            page.prepend(head);
        }
        root.dataset.bookMounted = 'true';
        return render(root);
    }

    let scheduled = false;
    function refresh() {
        if (scheduled) return;
        scheduled = true;
        Promise.resolve().then(() => {
            scheduled = false;
            document.querySelectorAll('.dbf-book[data-book-chapter]').forEach(render);
        });
    }

    function start() {
        document.querySelectorAll('.dbf-book[data-book-chapter]').forEach(mount);
        // Document titles change per rule chapter or entry; ribbon entries are hydrated asynchronously.
        if (document.head) new MutationObserver(refresh).observe(document.head, { subtree: true, childList: true, characterData: true });
        document.querySelectorAll(RIBBONS).forEach((nav) => new MutationObserver(refresh).observe(nav, {
            subtree: true, childList: true, attributes: true, attributeFilter: ['aria-disabled', 'hidden', 'href'],
        }));
        window.addEventListener('vtt:displaychange', refresh);
        window.addEventListener('pageshow', refresh);
    }

    window.VTTBookFrame = {
        chapters: () => CHAPTERS.map((chapter) => ({ key: chapter.key, href: chapter.href, name: chapterName(chapter), gated: Boolean(chapter.gate) })),
        state: (root = document.querySelector('.dbf-book[data-book-chapter]')) => (root ? stateOf(root) : null),
        mount,
        refresh,
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
    else start();
}());
