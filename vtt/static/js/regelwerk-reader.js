(function () {
    'use strict';

    const SRD_RULESET_ID = 'srd-5.2.1-de';
    // The SRD is the main book; Roll Drauf's own books live under their readerUrl.
    let book = { rulesetId: SRD_RULESET_ID, kind: 'srd', readerUrl: '/regelwerk' };
    let API_ROOT = `/api/rulesets/${SRD_RULESET_ID}`;
    const article = document.getElementById('regelwerkArticle');
    const toc = document.getElementById('regelwerkToc');
    const searchForm = document.getElementById('regelwerkSearch');
    const searchInput = document.getElementById('regelwerkSearchInput');
    const searchStatus = document.getElementById('regelwerkSearchStatus');
    const searchResults = document.getElementById('regelwerkSearchResults');
    let navigation = null;

    // Explicit UI catalog for authored controls/status/errors only. Rule blocks, book and
    // document titles, search excerpts and facet values are source text; element() below
    // intentionally never translates what it is given.
    const ui = (source, parameters) => globalThis.VTTUi(source, parameters || {});
    class UiMessageError extends Error {}

    function uiErrorText(error) {
        return error instanceof UiMessageError && error.message
            ? error.message
            : ui('Inhalt konnte nicht geladen werden.');
    }

    function element(tag, className = '', text = null) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== null) node.textContent = String(text);
        return node;
    }

    async function getJson(url) {
        const response = await fetch(url, { credentials: 'same-origin' });
        if (!response.ok) {
            throw new UiMessageError(response.status === 404 ? ui('Nicht gefunden.') : ui('Inhalt konnte nicht geladen werden.'));
        }
        return response.json();
    }

    function clear(node) {
        while (node.firstChild) node.removeChild(node.firstChild);
    }

    function setBlockIdentity(node, block) {
        node.id = block.ruleId;
        node.tabIndex = -1;
        return node;
    }

    function renderTable(block) {
        const wrap = setBlockIdentity(element('div', 'regelwerk-table-wrap'), block);
        const table = element('table', 'regelwerk-table');
        table.appendChild(element('caption', '', block.caption));
        const head = element('thead');
        const headRow = element('tr');
        block.columns.forEach((column) => {
            const cell = element('th', '', column);
            cell.scope = 'col';
            headRow.appendChild(cell);
        });
        head.appendChild(headRow);
        table.appendChild(head);
        const body = element('tbody');
        block.rows.forEach((row) => {
            const tr = element('tr');
            row.forEach((value) => tr.appendChild(element('td', '', value)));
            body.appendChild(tr);
        });
        table.appendChild(body);
        wrap.appendChild(table);
        return wrap;
    }

    function renderBlock(block) {
        if (block.type === 'heading') {
            return setBlockIdentity(element(`h${block.level}`, '', block.text), block);
        }
        if (block.type === 'paragraph') {
            return setBlockIdentity(element('p', '', block.text), block);
        }
        if (block.type === 'ordered-list' || block.type === 'unordered-list') {
            const list = setBlockIdentity(element(block.type === 'ordered-list' ? 'ol' : 'ul'), block);
            block.items.forEach((item) => list.appendChild(element('li', '', item)));
            return list;
        }
        if (block.type === 'definition-list') {
            const list = setBlockIdentity(element('dl'), block);
            block.entries.forEach((entry) => {
                list.appendChild(element('dt', '', entry.term));
                list.appendChild(element('dd', '', entry.definition));
            });
            return list;
        }
        if (block.type === 'table') return renderTable(block);
        if (block.type === 'rule-callout' || block.type === 'page-note') {
            const box = setBlockIdentity(element('aside', 'regelwerk-callout'), block);
            if (block.title) box.appendChild(element('strong', 'regelwerk-callout-title', block.title));
            box.appendChild(element('p', '', block.text));
            return box;
        }
        if (block.type === 'stat-block') {
            const box = setBlockIdentity(element('section', 'regelwerk-stat-block'), block);
            box.appendChild(element('h3', 'regelwerk-stat-title', block.name));
            const details = element('dl');
            block.entries.forEach((entry) => {
                details.appendChild(element('dt', '', entry.label));
                details.appendChild(element('dd', '', entry.value));
            });
            box.appendChild(details);
            block.sections.forEach((section) => {
                box.appendChild(element('h4', '', section.title));
                box.appendChild(element('p', '', section.text));
            });
            return box;
        }
        if (block.type === 'original-note') {
            const note = setBlockIdentity(element('aside', 'regelwerk-original-note'), block);
            if (block.title) note.appendChild(element('strong', '', block.title));
            note.appendChild(element('p', '', block.text));
            return note;
        }
        throw new UiMessageError(ui('Unbekannter Blocktyp: {type}', { type: block.type }));
    }

    function focusHashTarget() {
        if (!window.location.hash) return;
        let id;
        try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (_error) { return; }
        const target = document.getElementById(id);
        if (!target) return;
        target.focus({ preventScroll: true });
        target.scrollIntoView({ block: 'start', behavior: 'auto' });
    }

    const RANGE = /^(.+?) ([A-ZÄÖÜ](?:–[A-ZÄÖÜ])?)$/;
    const RULE_GROUPS = { 'magic-items': 'Regeln für magische Gegenstände' };
    const LABELS = {
        'magic-items.intro': 'Überblick',
        'magic-items.az-intro': 'Hinweise zum Katalog',
        'equipment.magic-items': 'Magische Gegenstände (Grundlagen)',
        'monsters.stat-block-overview': 'Übersicht: Wertekästen',
    };

    function tocEntries(section) {
        const items = [];
        const catalogPrefixes = new Set();
        section.documents.forEach((entry) => {
            const match = RANGE.exec(entry.title);
            if (match && entry.title !== `${match[1]} A–Z`) catalogPrefixes.add(match[1]);
        });
        section.documents.forEach((entry) => {
            const family = entry.documentId.split('.')[0];
            const match = RANGE.exec(entry.title);
            let group = null;
            let label = LABELS[entry.documentId] || entry.title;
            if (match && catalogPrefixes.has(match[1]) && entry.title !== `${match[1]} A–Z`) {
                group = `${match[1]} A–Z`;
                label = match[2];
            } else if (entry.documentId === 'magic-items.az-intro') {
                group = 'Magische Gegenstände A–Z';
            } else if (RULE_GROUPS[family] && entry.documentId !== `${family}.intro`) {
                group = RULE_GROUPS[family];
            }
            items.push({ entry, group, label });
        });
        return items;
    }

    function pageRange(pages) {
        const sorted = [...pages].sort((a, b) => a - b);
        if (!sorted.length) return ui('Seiten unbekannt');
        if (sorted.length === 1) return ui('Seite {page}', { page: sorted[0] });
        const consecutive = sorted.every((page, index) => index === 0 || page - sorted[index - 1] === 1);
        return consecutive
            ? ui('Seiten {from}–{to}', { from: sorted[0], to: sorted[sorted.length - 1] })
            : ui('Seiten {pages}', { pages: sorted.join(', ') });
    }

    function renderToc(data) {
        clear(toc);
        toc.appendChild(element('p', 'regelwerk-toc-heading', ui('Inhaltsverzeichnis')));
        const current = selectedDocument();
        const link = (item) => {
            const anchor = element('a', '', item.label);
            anchor.href = item.entry.url;
            if (current && current.documentId === item.entry.documentId) anchor.setAttribute('aria-current', 'page');
            return anchor;
        };
        data.sections.forEach((section) => {
            toc.appendChild(element('p', 'regelwerk-toc-section', section.title));
            const groups = new Map();
            tocEntries(section).forEach((item) => {
                if (!item.group) { toc.appendChild(link(item)); return; }
                if (!groups.has(item.group)) {
                    const details = element('details', 'regelwerk-toc-group');
                    details.appendChild(element('summary', '', item.group));
                    groups.set(item.group, details);
                    toc.appendChild(details);
                }
                const details = groups.get(item.group);
                const anchor = link(item);
                if (anchor.getAttribute('aria-current')) details.open = true;
                details.appendChild(anchor);
            });
        });
        const license = element('a', '', ui('Quelle & Lizenz'));
        license.href = data.licenseUrl;
        toc.appendChild(license);
    }

    function selectedDocument() {
        const parts = window.location.pathname.split('/').filter(Boolean);
        if (parts.length !== 4 || parts[0] !== 'regelwerk') {
            return navigation.sections.flatMap((section) => section.documents)[0] || null;
        }
        const slug = parts[3];
        return navigation.sections.flatMap((section) => section.documents)
            .find((entry) => entry.slug === slug) || null;
    }

    async function showDocument() {
        const entry = selectedDocument();
        if (!entry) throw new UiMessageError(ui('Noch kein Regelkapitel verfügbar.'));
        const documentData = await getJson(`${API_ROOT}/documents/${encodeURIComponent(entry.documentId)}`);
        clear(article);
        const trail = [documentData.navigationPath[0]];
        const sectionEntry = navigation.sections.find((section) => section.title === trail[0]);
        const item = sectionEntry && tocEntries(sectionEntry).find((candidate) => candidate.entry.documentId === entry.documentId);
        if (item && item.group) trail.push(item.group);
        trail.push(item ? item.label : documentData.title);
        const breadcrumbs = element('p', 'regelwerk-breadcrumbs', trail.join(' › '));
        article.appendChild(breadcrumbs);
        const status = navigation.status === 'preview' ? ui('Vorschau') : navigation.status;
        article.appendChild(element(
            'p',
            'regelwerk-document-meta',
            book.kind === 'original'
                ? ui('{title} · eigenes Werk von Roll Drauf · {status}', { title: navigation.title, status })
                : ui('SRD 5.2.1 · {pages} · {status}', { pages: pageRange(documentData.sourcePages), status }),
        ));
        documentData.blocks.forEach((block) => article.appendChild(renderBlock(block)));
        article.setAttribute('aria-busy', 'false');
        document.title = `${documentData.title} · ${book.kind === 'original' ? navigation.title : ui('Regelwerk')} · Roll Drauf VTT`;
        window.requestAnimationFrame(focusHashTarget);
    }

    async function showOwnLicense() {
        const data = await getJson(`${API_ROOT}/license`);
        clear(article);
        article.appendChild(element('h2', '', ui('Quelle & Lizenz')));
        article.appendChild(element('p', 'regelwerk-document-meta', ui('{title} · eigenes Werk von Roll Drauf', { title: data.title })));
        data.attribution.split(/\n\s*\n/).filter((part) => part.trim()).forEach((part) => {
            article.appendChild(element('p', 'regelwerk-license-text', part.trim()));
        });
        const srdLink = element('a', '', ui('Quelle und Lizenz des SRD 5.2.1'));
        srdLink.href = '/regelwerk/lizenz';
        const srdParagraph = element('p');
        srdParagraph.appendChild(srdLink);
        article.appendChild(srdParagraph);
        article.setAttribute('aria-busy', 'false');
        document.title = `${ui('Quelle & Lizenz')} · ${data.title} · Roll Drauf VTT`;
    }

    async function showLicense() {
        if (book.kind === 'original') return showOwnLicense();
        const data = await getJson(`${API_ROOT}/license`);
        clear(article);
        article.appendChild(element('h2', '', ui('Quelle & Lizenz')));
        article.appendChild(element('p', 'regelwerk-document-meta', `${data.source.title} · ${data.license.id}`));
        const sourceLink = element('a', '', ui('Offizielles deutsches SRD 5.2.1 öffnen'));
        sourceLink.href = data.source.url;
        sourceLink.rel = 'noreferrer';
        article.appendChild(sourceLink);
        const licenseLink = element('a', '', ui('Creative Commons Namensnennung 4.0'));
        licenseLink.href = data.license.url;
        licenseLink.rel = 'license noreferrer';
        const licenseParagraph = element('p');
        licenseParagraph.appendChild(licenseLink);
        article.appendChild(licenseParagraph);
        article.appendChild(element('h3', '', ui('Vorgeschriebene Quellenangabe')));
        article.appendChild(element('p', 'regelwerk-license-text', data.attribution));
        article.setAttribute('aria-busy', 'false');
        document.title = `${ui('Quelle & Lizenz')} · ${ui('Regelwerk')} · Roll Drauf VTT`;
    }

    async function renderRoute() {
        article.setAttribute('aria-busy', 'true');
        try {
            if (window.location.pathname === navigation.licenseUrl) await showLicense();
            else await showDocument();
        } catch (error) {
            clear(article);
            const heading = element('h2', '', ui('Regelwerk nicht verfügbar'));
            article.appendChild(heading);
            article.appendChild(element('p', 'regelwerk-status', uiErrorText(error)));
            article.setAttribute('aria-busy', 'false');
        }
    }

    async function runSearch(event) {
        event.preventDefault();
        const query = searchInput.value.trim();
        clear(searchResults);
        if (query.length < 2) {
            searchStatus.textContent = ui('Bitte mindestens zwei Zeichen eingeben.');
            return;
        }
        searchStatus.textContent = ui('Suche läuft …');
        try {
            const data = await getJson(`${API_ROOT}/search?q=${encodeURIComponent(query)}`);
            searchStatus.textContent = data.results.length
                ? ui('{count} Treffer gefunden.', { count: data.results.length })
                : ui('Keine Treffer gefunden.');
            data.results.forEach((result) => {
                const link = element('a', 'regelwerk-search-result');
                link.href = result.url;
                link.appendChild(element('strong', '', result.heading));
                link.appendChild(element('span', '', result.snippet));
                searchResults.appendChild(link);
            });
            const first = searchResults.querySelector('a');
            if (first) first.focus();
        } catch (error) {
            searchStatus.textContent = error instanceof UiMessageError && error.message
                ? error.message
                : ui('Suche nicht verfügbar.');
        }
    }

    function setText(id, text) {
        const node = document.getElementById(id);
        if (node) node.textContent = text;
    }

    function renderBooks(books) {
        const nav = document.getElementById('regelwerkBooks');
        if (!nav) return;
        clear(nav);
        nav.hidden = books.length < 2;
        books.forEach((entry) => {
            const link = element('a', '', entry.status === 'preview' ? ui('{title} · Vorschau', { title: entry.title }) : entry.title);
            link.href = entry.readerUrl;
            if (entry.rulesetId === book.rulesetId) link.setAttribute('aria-current', 'page');
            nav.appendChild(link);
        });
    }

    async function chooseBook() {
        let books = [];
        try {
            books = (await getJson('/api/rulesets')).rulesets || [];
        } catch (_error) {
            return;
        }
        const path = window.location.pathname;
        const own = books.find((entry) => entry.kind === 'original'
            && (path === entry.readerUrl || path.startsWith(`${entry.readerUrl}/`)));
        if (own) {
            book = own;
            API_ROOT = `/api/rulesets/${encodeURIComponent(own.rulesetId)}`;
        }
        renderBooks(books);
    }

    function applyBookChrome() {
        const licenseLink = document.getElementById('regelwerkLicenseLink');
        if (licenseLink) licenseLink.href = navigation.licenseUrl;
        if (book.kind !== 'original') return;
        setText('regelwerkTitle', navigation.title);
        setText('regelwerkSearchLabel', ui('In diesem Buch suchen'));
        setText('regelwerkPreviewNote', ui('{title} ist ein eigenes Erweiterungsbuch von Roll Drauf und entsteht schrittweise. Diese Vorschau enthält erst einen Teil.', { title: navigation.title }));
        setText('regelwerkFooterSource', ui('{title} · eigenes Werk von Roll Drauf · nutzt Regelbegriffe aus dem SRD 5.2.1.', { title: navigation.title }));
        const footerLicense = document.getElementById('regelwerkFooterLicense');
        if (footerLicense) {
            footerLicense.href = navigation.licenseUrl;
            footerLicense.textContent = ui('Quelle & Lizenz');
        }
    }

    async function init() {
        try {
            await chooseBook();
            navigation = await getJson(`${API_ROOT}/manifest`);
            const isPreview = navigation.status === 'preview';
            ['regelwerkPreviewBadge', 'regelwerkPreviewNote'].forEach((id) => {
                const node = document.getElementById(id);
                if (node) node.hidden = !isPreview;
            });
            applyBookChrome();
            renderToc(navigation);
            await renderRoute();
        } catch (error) {
            clear(article);
            article.appendChild(element('h2', '', ui('Regelwerk nicht verfügbar')));
            article.appendChild(element('p', 'regelwerk-status', uiErrorText(error)));
            article.setAttribute('aria-busy', 'false');
        }
    }

    searchForm.addEventListener('submit', runSearch);
    document.getElementById('regelwerkPrint').addEventListener('click', () => window.print());
    window.addEventListener('hashchange', focusHashTarget);
    window.addEventListener('popstate', renderRoute);
    init();
}());
