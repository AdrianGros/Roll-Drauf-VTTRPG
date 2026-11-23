globalThis.VTTUi ||= (source,parameters={}) => globalThis.VTTI18n?.literal(source,parameters) ?? source.replace(/\{([a-zA-Z0-9_]+)\}/g,(m,k)=>Object.prototype.hasOwnProperty.call(parameters,k)?String(parameters[k]):m);
globalThis.VTTUiHTML ||= source => globalThis.VTTUi(source).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/* Shared VTT ribbon, account memo and own profile entry for book, rules, table, and map pages. */
(function () {
    'use strict';

    const launchKey = 'vtt_open_play_launcher';
    // W01/K36: campaigns, characters and creation share one labelled group; conversations,
    // maps, atlas and the compendium stay direct entries. The rulebook is the compendium's
    // companion entry and opens the matching edition. Every existing direct URL still works.
    const START = ['/dashboard', globalThis.VTTUi("Übersicht")];
    const PLAY_GROUP = [
        ['/campaigns', globalThis.VTTUi("Kampagnen")],
        ['/characters', globalThis.VTTUi("Charaktere")],
        ['/api/ce/authoring', globalThis.VTTUi("Creation Engine")],
    ];
    const DIRECT = [
        ['/conversations', globalThis.VTTUi("Gespräche")],
        ['/mapmaker', globalThis.VTTUi("Karten")],
        ['/atlas', globalThis.VTTUi("Atlas")],
    ];
    const REFERENCE = [
        ['/regelwerk/compendium', globalThis.VTTUi("Compendium")],
        ['/regelwerk', globalThis.VTTUi("Regelwerk")],
    ];
    const routes = [START, ...PLAY_GROUP, ...DIRECT, ...REFERENCE];
    let groupSequence = 0;
    let memoPromise;
    const staticPreview = location.pathname === '/mapmaker/';
    const anonymousMap = location.pathname === '/static/mapmaker/index.html'
        && !/(?:^|;\s*)csrf_access_token=/.test(document.cookie);

    function routeForPath(pathname) {
        if (pathname === '/static/mapmaker/index.html') return '/mapmaker';
        const path = pathname.replace(/\.html$/, '').replace(/\/$/, '');
        if (path === '/mapmaker') return '/mapmaker';
        if (path === '/character-sheet' || path === '/srd-creator') return '/characters';
        if (path.startsWith('/api/ce/authoring')) return '/api/ce/authoring';
        if (path === '/regelwerk/compendium') return path;
        if (path.startsWith('/regelwerk')) return '/regelwerk';
        if (path === '/play') return '/play';
        return routes.some(([href]) => href === path) ? path : '';
    }

    function currentRoute() {
        return routeForPath(location.pathname);
    }

    function updateRouteState(nav) {
        const route = currentRoute();
        nav.querySelectorAll('a.book-dashboard-ribbon-btn').forEach(anchor => {
            const href = anchor.getAttribute('href');
            const target = href ? routeForPath(new URL(href, location.href).pathname) : '';
            const active = Boolean(route) && target === route;
            anchor.classList.toggle('is-active', active);
            if (active) anchor.setAttribute('aria-current', 'page');
            else anchor.removeAttribute('aria-current');
        });
        nav.querySelectorAll('.vtt-nav-group').forEach(group => {
            group.classList.toggle('has-active', Boolean(group.querySelector('a[aria-current="page"]')));
        });
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

        function link([href, label]) {
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
                anchor.classList.add('vtt-nav-sub');
                anchor.setAttribute('aria-disabled', staticPreview || anonymousMap ? 'false' : 'true');
                anchor.hidden = !(staticPreview || anonymousMap);
            }
            return anchor;
        }

        function cluster(entries, label, className, visibleLabel) {
            const group = document.createElement(visibleLabel ? 'details' : 'span');
            group.className = `vtt-nav-group ${className}`;
            if (visibleLabel) {
                const caption = document.createElement('summary');
                caption.className = 'book-dashboard-ribbon-btn';
                caption.id = `vttNavGroup${++groupSequence}`;
                caption.textContent = label;
                group.setAttribute('aria-labelledby', caption.id);
                group.append(caption);
                group.addEventListener('keydown', event => {
                    if (event.key === 'Escape') { group.open = false; caption.focus(); }
                });
            } else {
                group.setAttribute('role', 'group');
                group.setAttribute('aria-label', label);
            }
            const links = document.createElement('span'); links.className = 'vtt-nav-group-links';
            entries.forEach((entry) => links.append(link(entry)));
            group.append(links);
            if (entries.some(([href]) => href === route)) group.classList.add('has-active');
            return group;
        }

        fragment.appendChild(link(START));
        fragment.appendChild(cluster(PLAY_GROUP, globalThis.VTTUi('Spiel & Figuren'), 'vtt-nav-play', true));
        DIRECT.forEach((entry) => fragment.appendChild(link(entry)));
        fragment.appendChild(cluster(REFERENCE, globalThis.VTTUi('Compendium und Regelwerk'), 'vtt-nav-reference', false));

        const display=document.createElement('button');
        display.type='button';display.className='book-dashboard-ribbon-btn vtt-display-open';display.id='vttDisplayOpen';
        display.setAttribute('aria-label',globalThis.VTTUi('Einstellungen'));
        display.title=globalThis.VTTUi('Einstellungen');
        display.setAttribute('aria-haspopup','dialog');
        const gear=document.createElement('span');gear.textContent='⚙';gear.setAttribute('aria-hidden','true');display.appendChild(gear);
        display.addEventListener('click',()=>window.VTTDisplay?.open());

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
        (isPlay ? document.querySelector('.play-status-strip') || accountHost(nav) : accountHost(nav)).appendChild(display);
        nav.dataset.vttMainNav = 'true';
        nav.setAttribute('aria-label', 'VTT-Hauptnavigation');
        if (!staticPreview && !anonymousMap) {
            window.CreationEngineNavigation?.hydrate(nav);
            Promise.resolve(window.RegelwerkNavigation?.hydrate(nav)).then(() => applyContentEdition(nav)).catch(() => {});
        }
    }

    // K34: an explicitly chosen rule-text language opens its own edition from the normal
    // navigation, but only when the server publishes that edition. "auto" keeps the UI language.
    async function applyContentEdition(nav) {
        const display = window.VTTDisplay;
        const preferred = display?.get?.().contentLanguage;
        if (!preferred || preferred === 'auto' || typeof display.editions !== 'function') return;
        const edition = (await display.editions())[preferred];
        if (!edition || !nav.isConnected) return;
        nav.querySelectorAll('a[href^="/regelwerk/compendium"]').forEach((anchor) => {
            anchor.href = `/regelwerk/compendium?locale=${preferred}`;
        });
        nav.querySelectorAll('[data-regelwerk-nav]').forEach((anchor) => {
            anchor.hidden = false;
            anchor.href = edition.readerUrl;
            anchor.setAttribute('aria-disabled', 'false');
        });
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

    async function openOwnProfile() {
        const old = document.getElementById('reviewOwnProfile');
        if (old) { old.showModal(); return; }
        const dialog = document.createElement('dialog');
        dialog.id = 'reviewOwnProfile'; dialog.className = 'review-dialog';
        const title = document.createElement('h2'); title.id = 'reviewOwnProfileTitle'; title.tabIndex = -1;
        title.textContent = VTTUi('Dein Profil'); dialog.setAttribute('aria-labelledby', title.id);
        const content = document.createElement('div'); content.setAttribute('role','status');
        content.textContent = VTTUi('Profil wird geladen …');
        const close = document.createElement('button'); close.type = 'button'; close.textContent = VTTUi('Schließen');
        close.addEventListener('click',()=>dialog.close());
        dialog.append(title,content,close);document.body.append(dialog);dialog.showModal();title.focus();
        dialog.addEventListener('close',()=>dialog.remove(),{once:true});
        try {
            const data = await Auth.makeAuthRequest('/api/review-web/profile');
            if (!dialog.isConnected) return;
            title.textContent = data.username;
            const list = document.createElement('dl'); list.className = 'review-profile-stats';
            for (const [label,key] of [['Charaktere','characters'],['Eigene Kampagnen','owned_campaigns'],['Aktive Mitgliedschaften','memberships']]) {
                const term=document.createElement('dt'),value=document.createElement('dd');
                term.textContent=VTTUi(label);value.textContent=String(data[key] ?? 0);list.append(term,value);
            }
            content.replaceChildren(list);
        } catch (_) { if(dialog.isConnected)content.textContent=VTTUi('Profil konnte nicht geladen werden.'); }
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
        const profile = document.createElement('button');profile.type='button';profile.className='vtt-account-profile';
        profile.textContent=VTTUi('Profil');profile.addEventListener('click',openOwnProfile);
        name.addEventListener('dblclick',openOwnProfile);
        memo.append(name, count, profile, action);

        const data = await getMemo();
        if (!memo.isConnected) return;
        if (!data?.user) {
            name.textContent = globalThis.VTTUi("Gast");
            count.hidden = true;profile.hidden = true;
            action.textContent = globalThis.VTTUi("Anmelden");
            action.dataset.signedOut = 'true';
            return;
        }
        name.textContent = data.user.username || globalThis.VTTUi("Konto");
        if (data.user.avatar_url) {
            const avatar = document.createElement('img');avatar.className='vtt-account-avatar';
            avatar.alt='';avatar.width=32;avatar.height=32;avatar.referrerPolicy='no-referrer';
            avatar.addEventListener('error',()=>avatar.remove(),{once:true});
            avatar.src=data.user.avatar_url;memo.prepend(avatar);
        }
        const total = Number(data.completed_session_count) || 0;
        count.textContent = VTTUi(total===1?'{total} Session gespielt':'{total} Sessions gespielt',{total});
    }

    function scan() {
        document.querySelectorAll('.book-dashboard-ribbon, .vtt-map-nav').forEach((nav) => {
            if (nav.dataset.vttMainNav !== 'true') {
                buildRibbon(nav);
                buildAccount(nav);
            }
            updateRouteState(nav);
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
    window.addEventListener('popstate', scheduleScan);
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
