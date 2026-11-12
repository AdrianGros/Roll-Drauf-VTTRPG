globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/* Shared VTT ribbon and account memo for book, rules, table, and map pages. */
(function () {
    'use strict';

    const launchKey = 'vtt_open_play_launcher';
    const routes = [
        ['/dashboard', globalThis.VTTUi("Übersicht")],
        ['/campaigns', globalThis.VTTUi("Kampagnen")],
        ['/characters', globalThis.VTTUi("Charaktere")],
        ['/conversations', globalThis.VTTUi("Gespräche")],
        ['/mapmaker', globalThis.VTTUi("Karten")],
        ['/api/ce/authoring', globalThis.VTTUi("Creation Engine")],
        ['/regelwerk', globalThis.VTTUi("Regelwerk")],
        ['/regelwerk/compendium', globalThis.VTTUi("Compendium")],
    ];
    let memoPromise;
    const staticPreview = location.pathname === '/mapmaker/';
    const anonymousMap = location.pathname === '/static/mapmaker/index.html'
        && !/(?:^|;\s*)csrf_access_token=/.test(document.cookie);

    function currentRoute() {
        const path = location.pathname;
        if (path === '/static/mapmaker/index.html' || path === '/mapmaker') return '/mapmaker';
        if (path === '/character-sheet' || path === '/srd-creator') return '/characters';
        if (path.startsWith('/api/ce/authoring')) return '/api/ce/authoring';
        if (path === '/regelwerk/compendium') return path;
        if (path.startsWith('/regelwerk')) return '/regelwerk';
        if (path === '/play') return '/play';
        return routes.some(([href]) => href === path) ? path : '';
    }

    function getMemo() {
        if (staticPreview || anonymousMap) return Promise.resolve(null);
        if (!memoPromise) {
            memoPromise = (async () => {
                const request = () => fetch('/api/dashboard/navigation', { credentials: 'include' });
                try {
                    let response = await request();
                    if (response.status === 401 && window.Auth?.refreshAccessToken) {
                        if (await window.Auth.refreshAccessToken()) response = await request();
                    }
                    return response.ok ? response.json() : null;
                } catch (_) {
                    return null;
                }
            })();
        }
        return memoPromise;
    }

    function openPlay() {
        if (currentRoute() === '/play') return;
        if (currentRoute() === '/dashboard' && window.BookScene?.openPlayLaunch && document.querySelector('.book-dashboard-page')) {
            window.BookScene.openPlayLaunch();
            return;
        }
        try { sessionStorage.setItem(launchKey, '1'); } catch (_) { /* storage can be disabled */ }
        location.href = '/dashboard';
    }

    function buildRibbon(nav) {
        if (nav.dataset.vttMainNav === 'true') return;
        const route = currentRoute();
        const isBook = Boolean(nav.closest('.book-dashboard-page')) && ['/dashboard', '/campaigns', '/characters'].includes(route);
        const isPlay = route === '/play';
        const isCe = document.body.classList.contains('ce-authoring');
        const extras = Array.from(nav.querySelectorAll('#return-character, [href="/api/ce/authoring/advanced"]'));
        const fragment = document.createDocumentFragment();

        routes.forEach(([href, label]) => {
            const anchor = document.createElement('a');
            anchor.className = 'book-dashboard-ribbon-btn';
            anchor.textContent = label;
            anchor.href = href;
            if (route === href) {
                anchor.classList.add('is-active');
                anchor.setAttribute('aria-current', 'page');
            }
            if (isBook && ['/dashboard', '/campaigns', '/characters'].includes(href)) anchor.dataset.dashboardRoute = href;
            if (isPlay) anchor.dataset.bookReturnTarget = href;
            if (isCe) anchor.dataset.ceNav = '';
            if (document.body.classList.contains('ce-advanced')) anchor.dataset.nav = '';
            if (href === '/api/ce/authoring') {
                anchor.dataset.creationEngineNav = '';
                anchor.setAttribute('aria-disabled', 'true');
                anchor.addEventListener('click', (event) => {
                    if (anchor.getAttribute('aria-disabled') === 'true') event.preventDefault();
                });
                if (location.pathname === '/character-sheet') {
                    const characterId = Number(new URLSearchParams(location.search).get('id'));
                    if (Number.isInteger(characterId) && characterId > 0) anchor.dataset.creationEngineCharacterId = String(characterId);
                }
            }
            if (href === '/regelwerk') {
                anchor.dataset.regelwerkNav = '';
                anchor.setAttribute('aria-disabled', staticPreview || anonymousMap ? 'false' : 'true');
                anchor.hidden = !(staticPreview || anonymousMap);
            }
            fragment.appendChild(anchor);
        });

        const display=document.createElement('button');
        display.type='button';display.className='book-dashboard-ribbon-btn vtt-display-open';display.id='vttDisplayOpen';
        display.textContent=globalThis.VTTUi("Ansicht und Sprache");display.addEventListener('click',()=>window.VTTDisplay?.open());
        fragment.appendChild(display);

        const play = document.createElement('button');
        play.type = 'button';
        play.className = 'book-dashboard-ribbon-btn';
        play.textContent = globalThis.VTTUi("Spieltisch");
        if (isPlay) {
            play.classList.add('is-active');
            play.setAttribute('aria-current', 'page');
        } else {
            play.addEventListener('click', openPlay);
        }
        fragment.appendChild(play);
        extras.forEach((node) => fragment.appendChild(node));
        nav.replaceChildren(fragment);
        nav.dataset.vttMainNav = 'true';
        nav.setAttribute('aria-label', 'VTT-Hauptnavigation');
        if (!staticPreview && !anonymousMap) {
            window.CreationEngineNavigation?.hydrate(nav);
            window.RegelwerkNavigation?.hydrate(nav);
        }
    }

    function accountHost(nav) {
        const topbar = nav.closest('.book-dashboard-topbar');
        if (topbar) return topbar;
        const header = nav.closest('.regelwerk-site-header, .ce-page > header');
        if (header) {
            if (!nav.parentElement.classList.contains('vtt-main-topbar')) {
                const wrap = document.createElement('div');
                wrap.className = 'vtt-main-topbar';
                nav.parentNode.insertBefore(wrap, nav);
                wrap.appendChild(nav);
            }
            return nav.parentElement;
        }
        if (nav.closest('.mm-app')) return nav.parentElement;
        return nav.parentElement;
    }

    async function buildAccount(nav) {
        const host = accountHost(nav);
        if (host.querySelector('.vtt-account-memo')) return;
        const crest = host.querySelector('.book-dashboard-crest');
        const memo = document.createElement('div');
        memo.className = 'vtt-account-memo';
        memo.setAttribute('aria-label', VTTUi('Konto und gespielte Sessions'));
        const name = crest || document.createElement('strong');
        name.className = 'vtt-account-name';
        if (!crest) name.textContent = globalThis.VTTUi("Konto");
        const count = document.createElement('span');
        count.className = 'vtt-account-count';
        count.textContent = globalThis.VTTUi("Sessions …");
        const action = document.createElement('button');
        action.type = 'button';
        action.className = 'vtt-account-action';
        action.textContent = globalThis.VTTUi("Abmelden");
        action.addEventListener('click', () => {
            if (action.dataset.signedOut === 'true') location.href = '/login.html';
            else window.Auth?.logout?.();
        });
        if (crest) crest.replaceWith(memo);
        else host.appendChild(memo);
        memo.append(name, count, action);

        const data = await getMemo();
        if (!memo.isConnected) return;
        if (!data?.user) {
            name.textContent = globalThis.VTTUi("Gast");
            count.hidden = true;
            action.textContent = globalThis.VTTUi("Anmelden");
            action.dataset.signedOut = 'true';
            return;
        }
        name.textContent = data.user.username || globalThis.VTTUi("Konto");
        const total = Number(data.completed_session_count) || 0;
        count.textContent = VTTUi(total===1?'{total} Session gespielt':'{total} Sessions gespielt',{total});
    }

    function scan() {
        document.querySelectorAll('.book-dashboard-ribbon, .vtt-map-nav').forEach((nav) => {
            if (nav.dataset.vttMainNav === 'true') return;
            buildRibbon(nav);
            buildAccount(nav);
        });
        if (currentRoute() === '/dashboard' && document.querySelector('.book-dashboard-page')) {
            let pending = false;
            try { pending = sessionStorage.getItem(launchKey) === '1'; } catch (_) { /* disabled */ }
            if (pending && window.BookScene?.openPlayLaunch) {
                try { sessionStorage.removeItem(launchKey); } catch (_) { /* disabled */ }
                window.BookScene.openPlayLaunch();
            }
        }
    }

    let scheduled = false;
    function scheduleScan() {
        if (scheduled) return;
        scheduled = true;
        queueMicrotask(() => { scheduled = false; scan(); });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scan, { once: true });
    else scan();
    new MutationObserver(scheduleScan).observe(document.documentElement, { childList: true, subtree: true });
    window.VTTMainNav = { scan };
    if (currentRoute() === '/mapmaker' && !staticPreview && !anonymousMap) {
        ['creation-engine-nav.js', 'regelwerk-navigation.js'].forEach((file) => {
            const script = document.createElement('script');
            script.src = `../js/${file}`;
            document.head.appendChild(script);
        });
    }
}());
