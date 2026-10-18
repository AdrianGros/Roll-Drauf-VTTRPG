(function () {
    'use strict';

    const RULESET_ID = 'srd-5.2.1-de';
    const API_ROOT = `/api/rulesets/${RULESET_ID}`;
    const article = document.getElementById('regelwerkArticle');
    const toc = document.getElementById('regelwerkToc');
    const searchForm = document.getElementById('regelwerkSearch');
    const searchInput = document.getElementById('regelwerkSearchInput');
    const searchStatus = document.getElementById('regelwerkSearchStatus');
    const searchResults = document.getElementById('regelwerkSearchResults');
    let navigation = null;

    function element(tag, className = '', text = null) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== null) node.textContent = String(text);
        return node;
    }

    async function getJson(url) {
        const response = await fetch(url, { credentials: 'same-origin' });
        if (!response.ok) throw new Error(response.status === 404 ? 'Nicht gefunden.' : 'Inhalt konnte nicht geladen werden.');
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
        throw new Error(`Unbekannter Blocktyp: ${block.type}`);
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

    function renderToc(data) {
        clear(toc);
        toc.appendChild(element('p', 'regelwerk-toc-heading', 'Inhaltsverzeichnis'));
        data.sections.forEach((section) => {
            toc.appendChild(element('p', 'regelwerk-toc-section', section.title));
            section.documents.forEach((documentEntry) => {
                const link = element('a', '', documentEntry.title);
                link.href = documentEntry.url;
                toc.appendChild(link);
            });
        });
        const license = element('a', '', 'Quelle & Lizenz');
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
        if (!entry) throw new Error('Noch kein Regelkapitel verfügbar.');
        const documentData = await getJson(`${API_ROOT}/documents/${encodeURIComponent(entry.documentId)}`);
        clear(article);
        const breadcrumbs = element('p', 'regelwerk-breadcrumbs', documentData.navigationPath.join(' › '));
        article.appendChild(breadcrumbs);
        article.appendChild(element(
            'p',
            'regelwerk-document-meta',
            `SRD 5.2.1 · Seiten ${documentData.sourcePages.join('–')} · ${navigation.status === 'preview' ? 'Vorschau' : navigation.status}`,
        ));
        documentData.blocks.forEach((block) => article.appendChild(renderBlock(block)));
        article.setAttribute('aria-busy', 'false');
        document.title = `${documentData.title} · Regelwerk · Roll Drauf VTT`;
        window.requestAnimationFrame(focusHashTarget);
    }

    async function showLicense() {
        const data = await getJson(`${API_ROOT}/license`);
        clear(article);
        article.appendChild(element('h2', '', 'Quelle & Lizenz'));
        article.appendChild(element('p', 'regelwerk-document-meta', `${data.source.title} · ${data.license.id}`));
        const sourceLink = element('a', '', 'Offizielles deutsches SRD 5.2.1 öffnen');
        sourceLink.href = data.source.url;
        sourceLink.rel = 'noreferrer';
        article.appendChild(sourceLink);
        const licenseLink = element('a', '', 'Creative Commons Namensnennung 4.0');
        licenseLink.href = data.license.url;
        licenseLink.rel = 'license noreferrer';
        const licenseParagraph = element('p');
        licenseParagraph.appendChild(licenseLink);
        article.appendChild(licenseParagraph);
        article.appendChild(element('h3', '', 'Vorgeschriebene Quellenangabe'));
        article.appendChild(element('p', 'regelwerk-license-text', data.attribution));
        article.setAttribute('aria-busy', 'false');
        document.title = 'Quelle & Lizenz · Regelwerk · Roll Drauf VTT';
    }

    async function renderRoute() {
        article.setAttribute('aria-busy', 'true');
        try {
            if (window.location.pathname === '/regelwerk/lizenz') await showLicense();
            else await showDocument();
        } catch (error) {
            clear(article);
            const heading = element('h2', '', 'Regelwerk nicht verfügbar');
            article.appendChild(heading);
            article.appendChild(element('p', 'regelwerk-status', error.message || 'Inhalt konnte nicht geladen werden.'));
            article.setAttribute('aria-busy', 'false');
        }
    }

    async function runSearch(event) {
        event.preventDefault();
        const query = searchInput.value.trim();
        clear(searchResults);
        if (query.length < 2) {
            searchStatus.textContent = 'Bitte mindestens zwei Zeichen eingeben.';
            return;
        }
        searchStatus.textContent = 'Suche läuft …';
        try {
            const data = await getJson(`${API_ROOT}/search?q=${encodeURIComponent(query)}`);
            searchStatus.textContent = data.results.length
                ? `${data.results.length} Treffer gefunden.`
                : 'Keine Treffer gefunden.';
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
            searchStatus.textContent = error.message || 'Suche nicht verfügbar.';
        }
    }

    async function init() {
        try {
            navigation = await getJson(`${API_ROOT}/manifest`);
            const isPreview = navigation.status === 'preview';
            ['regelwerkPreviewBadge', 'regelwerkPreviewNote'].forEach((id) => {
                const node = document.getElementById(id);
                if (node) node.hidden = !isPreview;
            });
            renderToc(navigation);
            await renderRoute();
        } catch (error) {
            clear(article);
            article.appendChild(element('h2', '', 'Regelwerk nicht verfügbar'));
            article.appendChild(element('p', 'regelwerk-status', error.message || 'Inhalt konnte nicht geladen werden.'));
            article.setAttribute('aria-busy', 'false');
        }
    }

    searchForm.addEventListener('submit', runSearch);
    document.getElementById('regelwerkPrint').addEventListener('click', () => window.print());
    window.addEventListener('hashchange', focusHashTarget);
    window.addEventListener('popstate', renderRoute);
    init();
}());
