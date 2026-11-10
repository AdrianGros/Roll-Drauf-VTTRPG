/**
 * BookScene v2
 * Persistent spellbook scene for login, auth chapters, dashboard, campaigns,
 * characters, and the character-sheet focus route.
 *
 * The public interface is deliberately small: create(), open(), pageTurn(),
 * and the protected-route bootstrap helpers. Rendering, focus containment,
 * and transition fallback stay behind that seam so every caller gets the same
 * settled state.
 */

(function () {
    'use strict';

    const reducedMotion = window.matchMedia
        ? window.matchMedia('(prefers-reduced-motion: reduce)')
        : { matches: false, addEventListener: null, removeEventListener: null };

    const routeMeta = {
        login: { prev: null, next: 'signup', chapter: 'Schwelle', section: 'Eintritt', folio: ['0', '0'] },
        signup: { prev: 'login', next: 'register', chapter: 'Novizen', section: 'Registrierung', folio: ['I', 'II'] },
        register: { prev: 'signup', next: 'dashboard', chapter: 'Schlüssel', section: 'Zugang', folio: ['III', 'IV'] },
        dashboard: { prev: 'login', next: 'campaigns', chapter: 'Kompendium', section: 'Übersicht', folio: ['1', '2'] },
        campaigns: { prev: 'dashboard', next: 'characters', chapter: 'Chroniken', section: 'Kampagnen', folio: ['3', '4'] },
        characters: { prev: 'campaigns', next: null, chapter: 'Helden', section: 'Charaktere', folio: ['5', '6'] },
        'character-sheet': { prev: 'characters', next: null, chapter: 'Helden', section: 'Heldenbogen', folio: ['7', '8'] },
    };
    const routeOrder = ['login', 'signup', 'register', 'dashboard', 'campaigns', 'characters', 'character-sheet'];

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function buildIntentHref(path, params = {}) {
        const href = new URL(path, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value === null || value === undefined || value === '') {
                return;
            }
            href.searchParams.set(key, String(value));
        });
        return `${href.pathname}${href.search}`;
    }

    // Campaign details render in the book. Preparation opens its dedicated
    // BookScene document so its map, asset and roster handlers are present.
    function campaignHubDetailKeyForHref(href) {
        if (!href) {
            return null;
        }
        let url;
        try {
            url = new URL(href, window.location.origin);
        } catch (_error) {
            return null;
        }
        if (url.pathname !== '/campaigns' || url.searchParams.get('workspace') === '1') {
            return null;
        }
        const campaignId = Number(url.searchParams.get('campaign_id'));
        if (!Number.isInteger(campaignId) || campaignId <= 0) {
            return null;
        }
        return `campaign:${campaignId}`;
    }

    function findFocusedCampaignSession(sessions) {
        const list = Array.isArray(sessions) ? sessions : [];
        const active = list.find((session) => {
            const status = String(session?.runtime_status || session?.session_state || session?.status || '').trim().toLowerCase();
            return status === 'in_progress' || status === 'active';
        });
        return active || list[0] || null;
    }

    function buildHubActionButton(label, hubAction, opts = {}) {
        const classes = ['btn', opts.primary === false ? 'btn-secondary' : 'btn-primary', 'book-scene-action-btn'];
        const disabled = opts.disabled ? ' disabled' : '';
        const sessionAttr = Number.isInteger(opts.sessionId) && opts.sessionId > 0
            ? ` data-hub-session-id="${opts.sessionId}"`
            : '';
        return `<button type="button" class="${classes.join(' ')}" data-hub-action="${escapeHtml(hubAction)}"${sessionAttr}${disabled}>${escapeHtml(label)}</button>`;
    }

    function normalizePath(path) {
        if (!path) {
            return '/login';
        }

        const [pathname] = String(path).split('?');
        if (pathname === '/') {
            return '/dashboard';
        }
        if (pathname === '/login' || pathname === '/login.html') {
            return '/login';
        }
        if (pathname === '/signup' || pathname === '/signup.html') {
            return '/signup';
        }
        if (pathname === '/register' || pathname === '/register.html') {
            return '/register';
        }
        if (pathname === '/dashboard' || pathname === '/dashboard.html') {
            return '/dashboard';
        }
        if (pathname === '/campaigns' || pathname === '/campaigns.html') {
            return '/campaigns';
        }
        if (pathname === '/characters' || pathname === '/characters.html') {
            return '/characters';
        }
        if (pathname === '/character-sheet' || pathname === '/character-sheet.html') {
            return '/character-sheet';
        }
        return pathname;
    }

    function routeKeyForPath(path) {
        const normalized = normalizePath(path);
        if (normalized === '/login') return 'login';
        if (normalized === '/signup') return 'signup';
        if (normalized === '/register') return 'register';
        if (normalized === '/dashboard') return 'dashboard';
        if (normalized === '/campaigns') return 'campaigns';
        if (normalized === '/characters') return 'characters';
        if (normalized === '/character-sheet') return 'character-sheet';
        return 'dashboard';
    }

    function routePathForKey(key) {
        if (key === 'login') return '/login';
        if (key === 'signup') return '/signup';
        if (key === 'register') return '/register';
        if (key === 'dashboard') return '/dashboard';
        if (key === 'campaigns') return '/campaigns';
        if (key === 'characters') return '/characters';
        if (key === 'character-sheet') return '/character-sheet';
        return '/dashboard';
    }

    function routeHref(path) {
        const normalized = normalizePath(path);
        if (normalized === '/login') return '/login.html';
        if (normalized === '/signup') return '/signup.html';
        if (normalized === '/register') return '/register.html';
        if (normalized === '/dashboard') return '/dashboard';
        if (normalized === '/campaigns') return '/campaigns';
        if (normalized === '/characters') return '/characters';
        if (normalized === '/character-sheet') return '/character-sheet';
        return path;
    }

    function historyHrefForRoute(routeKey) {
        const href = routeHref(routePathForKey(routeKey));
        if (routeKey !== 'character-sheet') {
            return href;
        }

        const params = new URLSearchParams(window.location.search);
        const nextParams = new URLSearchParams();
        const characterId = params.get('id');
        const mode = params.get('mode');

        if (characterId) {
            nextParams.set('id', characterId);
        }
        if (mode) {
            nextParams.set('mode', mode);
        }

        const query = nextParams.toString();
        return query ? `${href}?${query}` : href;
    }

    const PLAY_ENTRY_STORAGE_KEY = 'vtt.play.entry-boundary';
    const BOOK_RETURN_STORAGE_KEY = 'vtt.book.return-boundary';
    const PLAY_EXIT_DURATION_MS = 560;
    const PLAY_ARRIVAL_DURATION_MS = 720;

    function buildPlayHref(campaignId, sessionId, seat = null) {
        const params = new URLSearchParams({
            campaign_id: String(campaignId),
            session_id: String(sessionId),
        });
        // Tischplatz: the table asks the server for this seat on arrival.
        if (seat === 'dm' || seat === 'player') {
            params.set('seat', seat);
        }
        return `/play?${params.toString()}`;
    }

    function persistPlayHandoff(handoff) {
        try {
            window.sessionStorage.setItem(PLAY_ENTRY_STORAGE_KEY, JSON.stringify(handoff));
        } catch (error) {
            console.warn('Failed to persist play handoff context:', error);
        }
    }

    function clearBookReturnBoundary() {
        try {
            window.sessionStorage.removeItem(BOOK_RETURN_STORAGE_KEY);
        } catch (error) {
            console.warn('Failed to clear book return boundary context:', error);
        }
    }

    window.BookScene = {
        isOpened: false,
        currentPage: 'login',
        currentView: 'login',
        sceneUser: null,
        sceneSnapshot: null,
        dashboardNotice: null,
        sceneBuiltRoute: null,
        transitionInFlight: false,
        loginBookResizeObserver: null,
        navigationMap: {
            login: { prev: null, next: '/dashboard' },
            signup: { prev: '/login', next: '/register' },
            register: { prev: '/signup', next: '/dashboard' },
            dashboard: { prev: '/login', next: '/campaigns' },
            campaigns: { prev: '/dashboard', next: '/characters' },
            characters: { prev: '/campaigns', next: null },
            'character-sheet': { prev: '/characters', next: null },
        },

        create() {
            // Bind-once guard. This was previously keyed on the wrapper
            // existing in the DOM, which conflated two different things:
            // "the markup is present" and "this scene object is wired up".
            // Since 2026-08-25 login.html ships the wrapper server-rendered
            // (so the user's first paint is the finished book instead of
            // watching JS build it), so the markup existing must NOT skip
            // binding — only a prior create() call may.
            if (this.sceneCreated) {
                this.syncMotionPreference();
                return;
            }
            this.sceneCreated = true;

            const bookHTML = `
                <div id="book-scene-wrapper" class="book-scene-wrapper" role="region" aria-label="Buchoberfläche">
                    <div class="book-scene-backdrop" aria-hidden="true"></div>
                    <div class="book-scene-stage">
                        <div id="book" class="book-scene-book" role="doc-cover" aria-label="Interactive spellbook">
                            <div class="book-element book-cover is-open" aria-hidden="true"></div>
                            <div class="book-element book-pages" role="doc-pagebreak" aria-label="Buchseiten"></div>
                            <div class="book-element book-back" role="doc-cover" aria-label="Buchrückseite"></div>
                            <div class="book-shell-page-stack book-shell-page-stack--left" aria-hidden="true"></div>
                            <div class="book-shell-page-stack book-shell-page-stack--right" aria-hidden="true"></div>
                            <div class="book-shell-spine" aria-hidden="true">
                                <div class="book-shell-spine-core"></div>
                            </div>
                            <div id="book-scene-turn-leaf" class="book-scene-turn-leaf" hidden aria-hidden="true">
                                <div id="book-scene-turn-shadow" class="book-scene-turn-shadow"></div>
                                <div id="book-scene-turn-sheet" class="book-scene-turn-sheet">
                                    <div class="book-scene-turn-face book-scene-turn-face--front">
                                        <div id="book-scene-turn-front" class="book-scene-turn-content"></div>
                                    </div>
                                    <div class="book-scene-turn-face book-scene-turn-face--back">
                                        <div id="book-scene-turn-back" class="book-scene-turn-content"></div>
                                    </div>
                                </div>
                            </div>
                            <div id="book-dashboard-scene" class="book-dashboard-scene" hidden aria-hidden="true"></div>
                        </div>
                    </div>
                </div>
            `;

            // The book is always shown open (owner decision 2026-11-08): no
            // closed entry cover and no click to enter. The class is set
            // before the markup lands so the closed state is never painted.
            document.body.classList.add('book-scene-open');
            if (!document.getElementById('book-scene-wrapper')) {
                document.body.insertAdjacentHTML('afterbegin', bookHTML);
            }

            if (!document.querySelector('.bookmark')) {
                document.body.insertAdjacentHTML('beforeend', '<div class="bookmark login"></div>');
            }

            const loginContent = document.getElementById('login-content');
            const book = document.getElementById('book');
            if (loginContent && book && loginContent.parentElement !== book) {
                book.appendChild(loginContent);
            }

            this.sceneSurface = document.getElementById('book-dashboard-scene');
            this.dashboardScene = this.sceneSurface;
            this.book = book;
            this.sceneBackdrop = document.querySelector('.book-scene-backdrop');
            this.bookCover = document.querySelector('.book-cover');
            this.bookPages = document.querySelector('.book-pages');
            this.bookBack = document.querySelector('.book-back');
            this.loginContent = loginContent;
            this.loginSpread = loginContent ? loginContent.querySelector('.login-book-spread') : null;
            this.loginLeftPage = loginContent ? loginContent.querySelector('.login-book-page--left') : null;
            this.loginRightPage = loginContent ? loginContent.querySelector('.login-book-page--right') : null;
            this.loginWelcomePage = loginContent ? loginContent.querySelector('#loginWelcomePage') : null;
            this.turnLeaf = document.getElementById('book-scene-turn-leaf');
            this.turnSheet = document.getElementById('book-scene-turn-sheet');
            this.turnShadow = document.getElementById('book-scene-turn-shadow');
            this.turnFront = document.getElementById('book-scene-turn-front');
            this.turnBack = document.getElementById('book-scene-turn-back');

            if (this.loginContent && typeof window.ResizeObserver === 'function') {
                this.loginBookResizeObserver = new window.ResizeObserver(() => {
                    this.syncLoginBookHeight();
                });
                this.loginBookResizeObserver.observe(this.loginContent);
            }
            window.addEventListener('resize', () => this.syncLoginBookHeight());

            this.applyOpenedBookState();

            this.syncMotionPreference();
            if (reducedMotion.addEventListener) {
                reducedMotion.addEventListener('change', () => this.syncMotionPreference());
            }

            // Keep keyboard focus in the readable part of the page. The
            // dashboard is intentionally taller than a phone viewport, so a
            // focus event must be allowed to scroll before the next capture.
            document.addEventListener('focusin', (event) => {
                const node = event.target;
                if (!node || !this.sceneSurface || !this.sceneSurface.contains(node)) {
                    return;
                }
                window.requestAnimationFrame(() => {
                    const rect = node.getBoundingClientRect();
                    const topbar = this.sceneSurface.querySelector('.book-dashboard-topbar');
                    const topbarBottom = topbar ? topbar.getBoundingClientRect().bottom : 0;
                    if (rect.top < topbarBottom + 12 || rect.bottom > window.innerHeight - 12) {
                        node.scrollIntoView({ behavior: 'auto', block: 'center', inline: 'nearest' });
                    }
                });
            });

            document.addEventListener('keydown', (event) => {
                if (!this.isOpened || this.transitionInFlight) {
                    return;
                }

                const activeElement = document.activeElement;
                if (activeElement) {
                    const tag = activeElement.tagName;
                    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
                        return;
                    }
                }

                const current = this.navigationMap[this.currentPage] || null;
                if (!current) {
                    return;
                }

                if (event.key === 'ArrowLeft' && current.prev) {
                    event.preventDefault();
                    this.pageTurn(current.prev);
                } else if (event.key === 'ArrowRight' && current.next) {
                    event.preventDefault();
                    this.pageTurn(current.next);
                }
            });

            this.updateCurrentPage();
            this.setSceneState('login');
            this.ensureDashboardScene();
        },

        syncMotionPreference() {
            document.body.classList.toggle('has-reduced-motion', Boolean(reducedMotion.matches));
        },

        syncLoginBookHeight() {
            if (!this.book || !this.loginContent || !document.body.classList.contains('book-login-open')) {
                return;
            }

            // The login spread is absolutely positioned inside the 3D shell,
            // so its form content cannot contribute to #book's auto height.
            // Measure the real spread and let the shell/background layers use
            // that height instead of the cover's aspect-ratio height.
            const contentHeight = Math.ceil(Math.max(
                this.loginContent.scrollHeight,
                this.loginContent.getBoundingClientRect().height,
            ));
            if (!contentHeight) {
                return;
            }

            this.book.style.aspectRatio = 'auto';
            this.book.style.height = `${contentHeight}px`;
        },

        resetLoginBookHeight() {
            if (!this.book) {
                return;
            }
            this.book.style.removeProperty('height');
            this.book.style.removeProperty('aspect-ratio');
        },

        setSceneState(state) {
            document.body.dataset.bookSceneState = state;
            document.body.classList.toggle('is-book-scene-login', state === 'login');
            document.body.classList.toggle('is-book-scene-dashboard', state === 'dashboard');
            document.body.classList.toggle('is-book-scene-transition', state === 'transition');
            document.body.classList.toggle('is-book-scene-opening', state === 'opening');
            document.body.classList.toggle('is-book-scene-play-transition', state === 'play-transition');
            document.body.classList.toggle('is-book-scene-return-transition', state === 'return-transition');
        },

        getRouteMeta(routeKey) {
            return routeMeta[routeKey] || routeMeta.dashboard;
        },

        getTurnDirection(fromRoute, toRoute) {
            const fromIndex = routeOrder.indexOf(fromRoute);
            const toIndex = routeOrder.indexOf(toRoute);
            if (fromIndex === -1 || toIndex === -1) {
                return 1;
            }
            return toIndex >= fromIndex ? 1 : -1;
        },

        getSpreadTitle(routeKey) {
            if (routeKey === 'login') return 'Buchzugang';
            if (routeKey === 'signup') return 'Registrierung';
            if (routeKey === 'register') return 'Einladung';
            if (routeKey === 'dashboard') return 'Übersicht';
            if (routeKey === 'campaigns') return 'Kampagnen';
            if (routeKey === 'characters') return 'Charaktere';
            if (routeKey === 'character-sheet') return 'Charakterbogen';
            return 'Buch';
        },

        getSpreadCopy(routeKey, side = 'front') {
            if (routeKey === 'login' && side === 'front') {
                return 'Der Buchzugang öffnet ruhig, bevor das erste Kapitel sichtbar wird.';
            }
            if (routeKey === 'signup') {
                return side === 'back'
                        ? 'Die Registrierung bleibt im selben Buch und führt klar durch die Kontoanlage.'
                    : 'Das nächste Blatt erklärt die Registrierung, ohne den Buchrahmen zu verlassen.';
            }
            if (routeKey === 'register') {
                return side === 'back'
                        ? 'Die Einladungsseite bleibt im selben Buch, damit der erste geschützte Abschnitt direkt folgen kann.'
                    : 'Das Einladungs-Kapitel setzt die Anmeldung auf derselben Seite fort.';
            }
            if (routeKey === 'dashboard') {
                return side === 'back'
                    ? 'Das Dashboard ist der Startpunkt für Kampagnen, Charaktere und den nächsten Weg in die Session-Vorbereitung.'
                    : 'Das Dashboard öffnet die stabile Vorbereitungsroute vor dem Tisch.';
            }
            if (routeKey === 'campaigns') {
                return side === 'back'
                    ? 'In Kampagnen legst du neue Runden an, öffnest den Hub und gehst weiter in Session-Prep.'
                    : 'Kampagnen ist der direkte Weg von der Übersicht in Hub, Session-Prep und Play.';
            }
            if (routeKey === 'characters') {
                return side === 'back'
                    ? 'Im Charakterarchiv legst du Helden an, pflegst Avatar und Token und öffnest den Bogen für den Feinschliff.'
                    : 'Charaktere ist der Ort für Heldenanlage, Identität und den Rückweg in die Session-Vorbereitung.';
            }
            if (routeKey === 'character-sheet') {
                return side === 'back'
                    ? 'Der Charakterbogen bleibt im selben Buch und zoomt tiefer in eine einzelne Figur.'
                    : 'Der Bogen ist der nächste fokussierte Schritt innerhalb des Buches.';
            }
            return 'Das nächste Blatt führt innerhalb desselben Buches weiter.';
        },

        buildTurnFaceMarkup(routeKey, side = 'front') {
            const meta = this.getRouteMeta(routeKey);
            const kicker = side === 'back'
                ? `${meta.chapter} verso`
                : `${meta.chapter} folio`;

            return `
                <div class="book-scene-turn-kicker">${escapeHtml(kicker)}</div>
                <h2 class="book-scene-turn-title">${escapeHtml(this.getSpreadTitle(routeKey))}</h2>
                <p class="book-scene-turn-copy">${escapeHtml(this.getSpreadCopy(routeKey, side))}</p>
            `;
        },

        getExternalTemplateId(routeKey) {
            if (routeKey === 'signup') return 'signupSceneTemplate';
            if (routeKey === 'register') return 'registerSceneTemplate';
            if (routeKey === 'character-sheet') return 'characterSheetSceneTemplate';
            return null;
        },

        runRouteInitializer(routeKey) {
            const initializers = window.BookSceneRouteInit || null;
            const initializer = initializers && typeof initializers[routeKey] === 'function'
                ? initializers[routeKey]
                : null;

            if (initializer) {
                initializer();
            }
        },

        prepareTurnLeaf(fromRoute, toRoute) {
            if (!this.turnLeaf || !this.turnSheet || !this.turnFront || !this.turnBack) {
                return;
            }

            const frontMarkup = fromRoute === 'login' && this.loginWelcomePage
                ? this.loginWelcomePage.innerHTML
                : this.buildTurnFaceMarkup(fromRoute, 'front');
            const backMarkup = this.buildTurnFaceMarkup(toRoute, 'back');

            this.turnFront.innerHTML = frontMarkup;
            this.turnBack.innerHTML = backMarkup;
            this.turnLeaf.hidden = false;
            this.turnLeaf.setAttribute('aria-hidden', 'false');
            this.turnLeaf.classList.add('is-visible');

            this.turnLeaf.style.opacity = '1';
            this.turnLeaf.style.transform = 'translateX(0)';
            this.turnSheet.style.transform = 'rotateY(0deg)';
            this.turnSheet.style.transformOrigin = 'left center';
            if (this.turnShadow) {
                this.turnShadow.style.opacity = '0';
            }
        },

        hideTurnLeaf() {
            if (!this.turnLeaf) {
                return;
            }

            this.turnLeaf.classList.remove('is-visible');
            this.turnLeaf.setAttribute('aria-hidden', 'true');
            this.turnLeaf.hidden = true;

            this.turnLeaf.style.removeProperty('transform');
            this.turnLeaf.style.removeProperty('opacity');
            this.turnSheet.style.removeProperty('transform');
            this.turnSheet.style.removeProperty('transform-origin');
            if (this.turnShadow) {
                this.turnShadow.style.removeProperty('opacity');
            }
        },

        buildRibbon(routeKey) {
            const routes = [
                { href: '/dashboard', label: this.content('ribbon.nav_dashboard', 'Übersicht') },
                { href: '/campaigns', label: this.content('ribbon.nav_campaigns', 'Kampagnen') },
                { href: '/characters', label: this.content('ribbon.nav_characters', 'Charaktere') },
            ];

            return routes.map((route) => {
                const activeRouteKey = routeKey === 'character-sheet' ? 'characters' : routeKey;
                const active = routeKeyForPath(route.href) === activeRouteKey ? ' is-active' : '';
                return `<button type="button" class="book-dashboard-ribbon-btn${active}" data-dashboard-route="${route.href}">${escapeHtml(route.label)}</button>`;
            }).join('')
                + '<a class="book-dashboard-ribbon-btn" data-creation-engine-nav aria-disabled="true" tabindex="0">Creation Engine · wird geprüft</a>'
                + '<a class="book-dashboard-ribbon-btn" data-regelwerk-nav hidden aria-disabled="true" tabindex="0">Regelwerk · Vorschau</a>'
                + `<button type="button" class="book-dashboard-ribbon-btn book-dashboard-ribbon-btn--play" data-dashboard-action="play-launch">${escapeHtml(this.content('ribbon.play_button', '▶ Spieltisch'))}</button>`
                + `<button type="button" class="book-dashboard-ribbon-btn" data-dashboard-action="logout">${escapeHtml(this.content('ribbon.logout_button', 'Abmelden'))}</button>`;
        },

        buildCampaignPreview(campaigns) {
            if (!Array.isArray(campaigns) || campaigns.length === 0) {
                return `
                    <div class="book-dashboard-preview-empty">
                        Noch keine Kampagnen. Lege die erste Runde an.
                    </div>
                `;
            }

            return `
                <div class="book-dashboard-preview-list">
                    ${campaigns.slice(0, 3).map((campaign) => `
                        <div class="book-dashboard-preview-item">
                            <span class="book-dashboard-preview-name">${escapeHtml(campaign.name || 'Unbenannte Kampagne')}</span>
                                <span class="book-dashboard-preview-meta">${escapeHtml(campaign.status || 'aktiv')} · ${Number(campaign.member_count || 0)} Mitglieder</span>
                        </div>
                    `).join('')}
                </div>
            `;
        },

        buildCharacterPreview(characters) {
            if (!Array.isArray(characters) || characters.length === 0) {
                return `
                    <div class="book-dashboard-preview-empty">
                        Noch keine Charaktere. Lege den ersten Helden an.
                    </div>
                `;
            }

            return `
                <div class="book-dashboard-preview-list">
                    ${characters.slice(0, 3).map((character) => `
                        <div class="book-dashboard-preview-item">
                            <span class="book-dashboard-preview-name">${escapeHtml(character.name || 'Unbekannt')}</span>
                            <span class="book-dashboard-preview-meta">Stufe ${Number(character.level || 1)} ${escapeHtml(character.class || 'Abenteurer')} · ${escapeHtml(character.race || 'Volk offen')}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        },

        buildStatStrip(items) {
            return `
                <div class="book-scene-stat-strip">
                    ${items.map((item) => `
                        <div class="book-scene-stat">
                            <span class="book-scene-stat-value">${escapeHtml(item.value)}</span>
                            <span class="book-scene-stat-label">${escapeHtml(item.label)}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        },

        buildActionButtons(actions = [], className = '') {
            if (!Array.isArray(actions) || actions.length === 0) {
                return '';
            }

            return `
                <div class="book-scene-action-row${className ? ` ${className}` : ''}">
                    ${actions.map((action) => {
                        const isPrimary = Boolean(action.primary);
                        // F1/C1: a campaign-hub href stays in the book - see
                        // campaignHubDetailKeyForHref above.
                        const detailKey = campaignHubDetailKeyForHref(action.href);
                        const detailTarget = detailKey ? ` data-dashboard-detail="${escapeHtml(detailKey)}"` : '';
                        const directHref = !detailKey && action.href ? ` data-dashboard-href="${escapeHtml(action.href)}"` : '';
                        const sceneRoute = action.route ? ` data-dashboard-route="${escapeHtml(action.route)}"` : '';
                        const sectionTarget = action.section ? ` data-dashboard-section="${escapeHtml(action.section)}"` : '';
                        const disabled = action.disabled ? ' disabled' : '';
                        return `<button type="button" class="btn ${isPrimary ? 'btn-primary' : 'btn-secondary'} book-scene-action-btn"${directHref}${detailTarget}${sceneRoute}${sectionTarget}${disabled}>${escapeHtml(action.label || 'Weiter')}</button>`;
                    }).join('')}
                </div>
            `;
        },

        buildCampaignLedger(campaigns) {
            if (!Array.isArray(campaigns) || campaigns.length === 0) {
                return `
                    <div class="book-scene-ledger-item is-empty">
                        <div>Noch keine Kampagne angelegt. Starte hier mit deiner ersten Runde und ihrer Vorbereitung.</div>
                        ${this.buildActionButtons([
                            {
                                label: 'Erste Kampagne anlegen',
                                href: buildIntentHref('/campaigns', { intent: 'create' }),
                                primary: true,
                            },
                        ], 'book-scene-action-row--inline')}
                    </div>
                `;
            }

            // Desktop-Audit D01/D02/A2: Mitglieder bekommen den Hub (und die
            // ganze Zeile als Klickziel — der Eintrag war ein toter Klick);
            // Nicht-Mitglieder bekommen hier die Beitreten-Affordance, die in
            // der Buch-Ansicht komplett fehlte (F4-Loch). Der garantierte
            // 403-Hub-Link für Nicht-Mitglieder (D07/B1) entfällt damit.
            return `
                <div data-campaign-list>
                <label class="book-scene-campaign-search">Kampagnen suchen
                    <input type="search" data-campaign-search placeholder="Name oder Beschreibung" autocomplete="off">
                </label>
                <div class="book-scene-campaign-pages" aria-label="Kampagnenseiten">
                    <button type="button" class="btn btn-secondary" data-campaign-prev>Vorherige</button>
                    <span data-campaign-count role="status" aria-live="polite"></span>
                    <button type="button" class="btn btn-secondary" data-campaign-next>Nächste</button>
                </div>
                <div class="book-scene-ledger">
                    ${campaigns.map((campaign) => {
                        // F1/C1 (interim slice): this used to be a hard
                        // data-dashboard-href navigation straight into the
                        const hubHref = buildIntentHref('/campaigns', { campaign_id: campaign.id });
                        const isMember = Boolean(campaign.is_member);
                        const rowAttrs = isMember
                            ? ` data-dashboard-detail="${campaignHubDetailKeyForHref(hubHref)}" role="link" tabindex="0" data-testid="campaign-ledger-item"`
                            : ' data-testid="campaign-ledger-item"';
                        const actions = isMember
                            ? this.buildActionButtons([
                                {
                                    label: Number(campaign.session_count || 0) > 0 ? 'Hub und Vorbereitung' : 'Hub öffnen',
                                    href: hubHref,
                                    primary: true,
                                },
                                { label: 'Gruppenübersicht', href: `/party?campaign=${Number(campaign.id)}` },
                            ], 'book-scene-action-row--inline')
                            : `
                                <div class="book-scene-join" data-campaign-id="${Number(campaign.id)}">
                                    ${campaign.your_membership_status === 'pending'
                                        ? '<p role="status">Beitrittsanfrage gesendet. Die Spielleitung muss sie noch bestätigen.</p>'
                                        : campaign.can_request_join ? `
                                            <p>Diese Runde sucht Spieler. Die Spielleitung bestätigt deinen Beitritt.</p>
                                            <button type="button" class="btn btn-primary book-scene-action-btn" data-dashboard-action="request-campaign-join">Beitritt anfragen</button>
                                        ` : '<p>Für diese Runde ist derzeit keine neue öffentliche Beitrittsanfrage möglich.</p>'}
                                    <div class="book-scene-ledger-meta">Einladung von der Spielleitung? Öffne ihren Einladungslink — oder löse den Code hier ein:</div>
                                    <div class="book-scene-join-row">
                                        <input type="text" data-join-input placeholder="Einladungscode" aria-label="Einladungscode" data-testid="join-code-input">
                                        <button type="button" class="btn btn-primary book-scene-action-btn" data-dashboard-action="join-campaign" data-testid="join-code-submit">Beitreten</button>
                                    </div>
                                    <div class="book-scene-ledger-meta" data-join-status role="status" hidden></div>
                                </div>
                            `;
                        return `
                        <div class="book-scene-ledger-item"${rowAttrs}>
                            <div class="book-scene-ledger-head">
                                <strong>${escapeHtml(campaign.name || 'Unbenannte Kampagne')}</strong>
                                <span>${escapeHtml(campaign.status || 'active')}</span>
                            </div>
                            <div class="book-scene-ledger-meta">${Number(campaign.member_count || 0)} Mitglieder · ${campaign.is_owner ? 'Eigene Kampagne' : 'Geteilte Kampagne'}</div>
                            ${Number(campaign.pending_join_request_count || 0) > 0 ? `
                                <div class="book-scene-ledger-meta"><strong>${Number(campaign.pending_join_request_count)} Beitrittsanfrage${Number(campaign.pending_join_request_count) === 1 ? '' : 'n'}</strong> ${Number(campaign.pending_join_request_count) === 1 ? 'wartet' : 'warten'} auf Bestätigung</div>
                            ` : ''}
                            <div class="book-scene-ledger-copy">${escapeHtml(campaign.description || 'Bereit für Vorbereitung, Charaktere und Karte vor dem Spielabend.')}</div>
                            ${actions}
                        </div>
                        `;
                    }).join('')}
                </div>
                </div>
            `;
        },

        buildCharacterManageActions(character, mode) {
            if (character.system_id !== 'srd_5_2_1_de') {
                return '';
            }
            const id = Number(character.id);
            const button = (action, label) => `<button type="button" class="btn btn-secondary book-scene-action-btn" data-character-action="${action}" data-character-id="${id}" data-character-name="${escapeHtml(character.name || '')}">${label}</button>`;
            const buttons = mode === 'archived'
                ? [button('restore', 'Wiederherstellen'), button('delete', 'Endgültig löschen')]
                : [button('duplicate', 'Duplizieren'), button('archive', 'Archivieren')];
            return `<div class="book-scene-action-row book-scene-action-row--inline">${buttons.join('')}</div>`;
        },

        buildArchivedCharacters(archived) {
            if (!Array.isArray(archived) || archived.length === 0) {
                return '';
            }
            return `
                <details class="book-scene-panel" data-archived-characters>
                    <summary class="book-scene-panel-title">Archiv (${archived.length})</summary>
                    <p>Archivierte Helden sind aus der Liste ausgeblendet. Wiederherstellen holt sie zurück, endgültiges Löschen entfernt sie.</p>
                    ${this.buildCharacterLedger(archived, null, 'archived')}
                </details>
            `;
        },

        buildOpenDrafts(drafts) {
            if (!Array.isArray(drafts) || drafts.length === 0) {
                return '';
            }
            return `
                <section class="book-scene-panel" data-open-drafts>
                    <h2 class="book-scene-panel-title">Offene Entwürfe (${drafts.length})</h2>
                    <div class="book-scene-ledger">
                        ${drafts.map((draft) => `
                            <div class="book-scene-ledger-item">
                                <div class="book-scene-ledger-head">
                                    <strong>${escapeHtml(draft.name || 'Unbenannter Entwurf')}</strong>
                                </div>
                                <div class="book-scene-ledger-meta">Zuletzt bearbeitet: ${escapeHtml(draft.updated_at ? new Date(draft.updated_at).toLocaleString('de-DE') : '–')}</div>
                                <div class="book-scene-action-row book-scene-action-row--inline">
                                    <a class="btn btn-primary book-scene-action-btn" data-draft-continue="${Number(draft.id)}" href="/srd-creator?draft=${Number(draft.id)}">Weiterführen</a>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </section>
            `;
        },

        buildCharacterLedger(characters, campaigns = null, mode = 'active') {
            if (!Array.isArray(characters) || characters.length === 0) {
                return `
                    <div class="book-scene-ledger-item is-empty">
                        <div>Noch kein Held im Archiv. Lege hier den ersten Charakter an und führe ihn danach über Bogen und Kampagne in die Vorbereitung.</div>
                    </div>
                `;
            }

            return `
                <div class="book-scene-ledger">
                    ${characters.map((character) => `
                        <div class="book-scene-ledger-item">
                            <div class="book-scene-ledger-head">
                                <strong>${escapeHtml(character.name || 'Unbekannt')}</strong>
                                <span>Stufe ${Number(character.level || 1)}</span>
                            </div>
                            <div class="book-scene-ledger-meta">${escapeHtml(character.class || 'Abenteurer')} · ${escapeHtml(character.race || 'Volk offen')}</div>
                            ${character.owner_username ? `<div class="book-scene-ledger-meta">${escapeHtml(character.owner_username)} · ${escapeHtml(character.campaign_name || '')}</div>` : ''}
                            <div class="book-scene-ledger-copy">${escapeHtml(character.background || 'Bereit für Bogen, Identität und die spätere Zuweisung in eine Runde.')}</div>
                            ${this.buildActionButtons([
                                {
                                    label: 'Bogen öffnen',
                                    href: buildIntentHref('/character-sheet', { id: character.id }),
                                    primary: true,
                                },
                                character.campaign_id
                                    ? {
                                        label: 'Kampagnen-Kontext',
                                        href: buildIntentHref('/campaigns', { campaign_id: character.campaign_id }),
                                    }
                                    : {
                                        label: 'Kampagnen öffnen',
                                        href: buildIntentHref('/campaigns', {}),
                                    },
                            ], 'book-scene-action-row--inline')}
                            ${Array.isArray(campaigns) || mode === 'archived' ? this.buildCharacterManageActions(character, mode) : ''}
                            ${Array.isArray(campaigns) && !character.is_party_stash ? `
                                <form data-character-campaign="${Number(character.id)}" class="book-scene-panel">
                                    <label for="characterCampaign_${Number(character.id)}">Mit einer Kampagne teilen</label>
                                    <select id="characterCampaign_${Number(character.id)}" aria-label="Kampagne für ${escapeHtml(character.name)}" style="width:100%;min-width:0">
                                        <option value="">Nur für mich</option>
                                        ${character.campaign_id && !campaigns.some(c => Number(c.id) === Number(character.campaign_id))
                                            ? `<option value="${Number(character.campaign_id)}" selected>Bisherige Kampagne (kein aktiver Zugang)</option>` : ''}
                                        ${campaigns.map(c => `<option value="${Number(c.id)}"${Number(c.id) === Number(character.campaign_id) ? ' selected' : ''}>${escapeHtml(c.name)}</option>`).join('')}
                                    </select>
                                    <p>Mitglieder der gewählten Kampagne können diesen Charakter im Archiv, im Bogen und in der Vorbereitung sehen.</p>
                                    <button class="btn btn-secondary" type="submit">Zuordnung speichern</button>
                                    <p data-character-campaign-status role="status" hidden></p>
                                </form>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        },

        buildDashboardHero(snapshot = null) {
            const homeState = snapshot?.home_state || {};
            const primaryAction = snapshot?.primary_action || {
                label: 'Kampagnen öffnen',
                href: '/campaigns',
            };
            const secondaryAction = snapshot?.secondary_action || {
                label: 'Charaktere öffnen',
                href: '/characters',
            };
            const overviewScopeNote = snapshot?.overview_scope?.note
                || this.content('home.overview_scope_default', 'Diese Übersicht zeigt deinen VTT-Stand: Kampagnen, Charaktere, Sitzungen und Vorbereitung.');

            return `
                <section class="book-home-hero book-ribbon-card">
                    <div class="book-ribbon-marker" aria-hidden="true"></div>
                    <div class="book-home-hero-kicker">${escapeHtml(this.content('home.hero_kicker', 'Lesebändchen'))}</div>
                    <h2 class="book-home-hero-title">${escapeHtml(this.content('home.hero_title', 'Weiterlesen'))}</h2>
                    ${homeState.summary ? `<p class="book-home-hero-copy">${escapeHtml(homeState.summary)}</p>` : ''}
                    ${this.buildActionButtons([
                        {
                            label: primaryAction.label || 'Weiter',
                            href: primaryAction.href || '/campaigns',
                            primary: true,
                        },
                        {
                            label: secondaryAction.label || 'Charaktere öffnen',
                            href: secondaryAction.href || '/characters',
                        },
                    ], 'book-scene-action-row--inline')}
                    <div class="book-home-hero-note">
                        <strong>${escapeHtml(this.content('home.overview_scope_label', 'Bereich:'))}</strong> ${escapeHtml(overviewScopeNote)}
                    </div>
                    ${this.dashboardNotice ? `<div class="book-home-hero-notice">${escapeHtml(this.dashboardNotice)}</div>` : ''}
                </section>
            `;
        },

        buildDashboardToc(snapshot = null) {
            const homeState = snapshot?.home_state || {};

            // The contents list is the dashboard's compact route map. Keep it
            // separate from the hero so the book spread can place each block
            // on the page marked by the visual audit.
            const tocRows = [
                { numeral: 'II', label: this.content('home.nav_campaigns', 'Kampagnen'),
                  count: Number(homeState.campaign_count || 0), href: '/campaigns' },
                { numeral: 'III', label: this.content('home.nav_characters', 'Charaktere'),
                  count: Number(homeState.character_count || 0), href: '/characters' },
                { numeral: 'IV', label: this.content('home.nav_play', 'Spieltisch'),
                  count: Number(homeState.session_count || 0), href: null,
                  action: 'play-launch',
                  countLabel: this.content('home.toc_sessions', '{count} Sitzungen',
                                           { count: Number(homeState.session_count || 0) }) },
            ];

            return `
                <nav class="book-toc" aria-label="Inhaltsverzeichnis">
                    <div class="book-toc-kicker">${escapeHtml(this.content('home.toc_kicker', 'Inhaltsverzeichnis'))}</div>
                    ${tocRows.map((row) => `
                        <a class="book-toc-row" href="${row.href || '#'}" ${row.action ? `data-dashboard-action="${row.action}"` : `data-book-route="${row.href}"`}>
                            <span class="book-toc-numeral">${row.numeral}</span>
                            <span class="book-toc-label">${escapeHtml(row.label)}</span>
                            <span class="book-toc-leader" aria-hidden="true"></span>
                            <span class="book-toc-count">${escapeHtml(row.countLabel || String(row.count))}</span>
                        </a>
                    `).join('')}
                    <a class="book-toc-row" data-creation-engine-nav aria-disabled="true" tabindex="0">Creation Engine · wird geprüft</a>
                    <a class="book-toc-row" data-regelwerk-nav hidden aria-disabled="true" tabindex="0">Regelwerk · Vorschau</a>
                </nav>
                ${homeState.authoring_available === true ? `
                    <div class="book-scene-panel">
                        <a class="btn btn-secondary book-scene-action-btn" href="/api/ce/authoring" data-testid="authoring-entry">${escapeHtml(this.content('home.create_content', 'Inhalte erstellen'))}</a>
                        <p>${escapeHtml(this.content('home.create_content_help', 'Eigene Völker, Merkmale und weitere Inhalte entwerfen und privat ausprobieren.'))}</p>
                    </div>
                ` : ''}
            `;
        },

        buildDashboardFeed(snapshot = null) {
            const feedItems = Array.isArray(snapshot?.feed_preview) ? snapshot.feed_preview : [];

            if (feedItems.length === 0) {
                return '';
            }

            return `
                <section class="book-home-feed">
                    ${feedItems.map((item) => `
                        <article class="book-home-feed-item" data-dashboard-section-target="${escapeHtml(item.section || 'campaigns')}">
                            <div class="book-home-feed-kicker">${escapeHtml(item.kicker || 'Chronik')}</div>
                            <h3 class="book-home-feed-title">${escapeHtml(item.title || 'Eintrag')}</h3>
                            ${item.meta ? `<div class="book-home-feed-meta">${escapeHtml(item.meta)}</div>` : ''}
                            <p class="book-home-feed-copy">${escapeHtml(item.copy || '')}</p>
                            ${(item.action_href || item.action_section)
                                ? `
                                <div class="book-home-feed-actions">
                                    <button
                                        type="button"
                                        class="btn btn-secondary book-scene-action-btn"
                                        ${item.action_href ? `data-dashboard-href="${escapeHtml(item.action_href)}"` : ''}
                                        ${item.action_section ? `data-dashboard-section="${escapeHtml(item.action_section)}"` : ''}
                                    >
                                        ${escapeHtml(item.action_label || 'Weiter')}
                                    </button>
                                </div>
                            `
                                : ''
                            }
                        </article>
                    `).join('')}
                </section>
            `;
        },

        buildPageShell(routeKey, user, options) {
            const displayName = options.loading ? '' : escapeHtml(user?.username || 'Donut');
            const chips = Array.isArray(options.chips) ? options.chips : [];
            const leftTitle = escapeHtml(options.title || 'Übersicht');
            const leftCopy = escapeHtml(options.copy || '');
            const leftEyebrow = escapeHtml(options.eyebrow || '');
            const rightTitle = escapeHtml(options.rightTitle || 'Marginalia');
            const rightCopy = escapeHtml(options.rightCopy || '');
            const rightEyebrow = escapeHtml(options.rightEyebrow || 'Reader Notes');

            return `
                <div class="book-dashboard-camera">
                    <section class="book-dashboard-page" data-book-route="${routeKey}" role="region" aria-label="${leftTitle} page">
                        <div class="book-dashboard-topbar">
                            <div class="book-dashboard-ribbon" role="navigation" aria-label="Buchnavigation">
                                ${this.buildRibbon(routeKey)}
                            </div>
                            <div class="book-dashboard-crest" aria-label="Current reader">${displayName}</div>
                        </div>

                        ${options.showRunningHead !== false ? `
                            <div class="book-running-head" aria-hidden="true">
                                <span class="book-running-head-place">${escapeHtml(options.runningHead || leftTitle)}</span>
                                <span class="book-running-head-rule"></span>
                            </div>
                        ` : ''}

                        <div class="book-spread-shell">
                            <article class="book-spread-page book-spread-page--left">
                                <header class="book-spread-page-header">
                                    <p class="book-spread-page-kicker">${leftEyebrow}</p>
                                    <h1 class="book-spread-page-title">${leftTitle}</h1>
                                    ${leftCopy ? `<p class="book-spread-page-copy">${leftCopy}</p>` : ''}
                                </header>
                                <div class="book-spread-page-body">
                                    ${options.leftPage || ''}
                                </div>
                                <span class="book-page-folio book-page-folio--left" aria-hidden="true">
                                    ${escapeHtml((options.folio && options.folio[0]) || '')}
                                </span>
                            </article>

                            <div aria-hidden="true"></div>

                            <article class="book-spread-page book-spread-page--right">
                                ${options.showRightHeader !== false ? `
                                    <header class="book-spread-page-header">
                                        <p class="book-spread-page-kicker">${rightEyebrow}</p>
                                        <h2 class="book-spread-page-title">${rightTitle}</h2>
                                        ${rightCopy ? `<p class="book-spread-page-copy">${rightCopy}</p>` : ''}
                                    </header>
                                    <div class="book-spread-page-meta">
                                        ${chips.map((chip) => `<span class="book-dashboard-chip">${escapeHtml(chip)}</span>`).join('')}
                                    </div>
                                ` : ''}
                                <div class="book-spread-page-body">
                                    ${options.rightPage || ''}
                                </div>
                                <span class="book-page-folio book-page-folio--right" aria-hidden="true">
                                    ${escapeHtml((options.folio && options.folio[1]) || '')}
                                </span>
                            </article>
                        </div>

                        ${options.footer ? `
                            <section class="book-spread-footer">
                                ${options.footer}
                            </section>
                        ` : ''}

                    </section>
                </div>
            `;
        },

        buildDashboardMarkup(user, snapshot = null) {
            const scene = routeMeta.dashboard || {};
            return this.buildPageShell('dashboard', user, {
                showRunningHead: false,
                showRightHeader: false,
                folio: scene.folio,
                eyebrow: this.content('shell.left_eyebrow', 'Kapitel I'),
                title: this.content('shell.left_title', 'Übersicht'),
                copy: '',
                chips: [],
                leftPage: `
                    <div class="book-home-stack">
                        ${this.buildDashboardToc(snapshot)}
                    </div>
                `,
                rightPage: `
                    <div class="book-home-stack">
                        ${this.buildDashboardHero(snapshot)}
                        ${this.buildDashboardFeed(snapshot)}
                    </div>
                `,
            });
        },

        buildCampaignsMarkup(user, snapshot = null) {
            const campaigns = snapshot?.campaigns || [];
            const ownedCount = campaigns.filter((campaign) => Boolean(campaign.is_owner)).length;
            const joinedCount = campaigns.filter((campaign) => Boolean(campaign.is_member) && !campaign.is_owner).length;
            const activeCount = campaigns.filter((campaign) => String(campaign.status || '').toLowerCase() === 'active').length;

            return this.buildPageShell('campaigns', user, {
                eyebrow: 'Kapitel II',
                title: 'Kampagnen',
                showRunningHead: false,
                copy: '',
                showRightHeader: false,
                chips: [`${campaigns.length} Kampagnen`, `${ownedCount} Eigene`, `${joinedCount} Beigetreten`, `${activeCount} Aktiv`],
                leftPage: `
                    ${this.buildStatStrip([
                        { value: String(campaigns.length), label: 'Kampagnen' },
                        { value: String(activeCount), label: 'Aktive Runden' },
                        { value: String(ownedCount), label: 'Eigene Kampagnen' },
                    ])}
                    <section class="book-scene-panel">
                        <span class="book-scene-panel-kicker">Kampagnenliste</span>
                        <h2 class="book-scene-panel-title">Meine Kampagnen</h2>
                        <p class="book-scene-panel-copy">Öffne von hier aus bestehende Kampagnen oder starte eine neue. Der produktive Weg danach bleibt derselbe: Hub, Session-Prep und erst dann Play.</p>
                        ${this.buildActionButtons([
                            {
                                label: 'Neue Kampagne anlegen',
                                href: buildIntentHref('/campaigns', { intent: 'create' }),
                                primary: true,
                            },
                        ])}
                        ${this.buildCampaignLedger(campaigns)}
                    </section>
                `,
                rightPage: `
                    <section class="book-spread-footer">
                        <div class="book-dashboard-widget-header">
                            <h2>Kampagnen-Werkzeuge</h2>
                            <span class="book-dashboard-widget-tag">Hub, Vorbereitung, Karten, Assets</span>
                        </div>
                        <p class="book-dashboard-widget-copy">
                            Die wichtigsten Folgeflächen sind bereits nutzbar und hängen am Kampagnen-Hub: Session-Prep, Karten, Assets und die nächsten Schritte Richtung Play.
                        </p>
                        <div class="book-scene-widget-stack">
                            <div class="book-scene-widget-card">
                                <span>Einladungen</span>
                                <small>Mitspieler aufnehmen und Kampagnen sauber für die gemeinsame Vorbereitung öffnen.</small>
                            </div>
                            <div class="book-scene-widget-card">
                                <span>Session-Prep</span>
                                <small>Sessionstatus lesen, Charaktere zuweisen und entscheiden, ob Start, Fortsetzen oder Warten dran ist.</small>
                            </div>
                            <div class="book-scene-widget-card">
                                <span>Karten</span>
                                <small>Session-Karte setzen und den Kartenkontext für die nächste Runde vorbereiten.</small>
                            </div>
                            <div class="book-scene-widget-card">
                                <span>Assets</span>
                                <small>Sessionbezogene Assets öffnen, Upload vorbereiten und den Vorbereitungsstand vor dem Spielabend prüfen.</small>
                            </div>
                        </div>
                    </section>
                `,
            });
        },

        // Campaign overview and session entry use the shared book shell.
        // Detailed preparation is another book page with the same navigation.
        buildCampaignHubDetailMarkup(user, data) {
            const campaign = data?.campaign || {};
            const members = Array.isArray(data?.members) ? data.members : [];
            const sessions = Array.isArray(data?.sessions) ? data.sessions : [];
            const maps = Array.isArray(data?.maps) ? data.maps : [];
            const characters = Array.isArray(data?.characters) ? data.characters : [];
            const assignments = Array.isArray(data?.session_character_assignments) ? data.session_character_assignments : [];

            const canManage = Boolean(campaign.is_owner) || campaign.your_role === 'DM' || campaign.your_role === 'CO_DM';
            // Keep the existing moderation policy: campaign owner or DM.
            const canKick = Boolean(campaign.is_owner) || campaign.your_role === 'DM';
            const canLeave = Boolean(campaign.is_member) && !campaign.is_owner;
            const campaignCharacterCount = characters.filter((character) => Number(character.campaign_id) === Number(campaign.id)).length;
            const focusedSession = findFocusedCampaignSession(sessions);
            const campaignStatus = campaign.status || 'active';
            const campaignStatusTone = campaignStatus === 'active' ? 'live' : (campaignStatus === 'paused' ? 'paused' : '');

            // Pending join requests get their own review panel below, not
            // the general member ledger - they aren't members yet.
            const settledMembers = members.filter((member) => ['active', 'invited'].includes(member.status));
            const pendingMembers = members.filter((member) => member.status === 'pending');

            const memberRows = settledMembers.length
                ? settledMembers.map((member) => `
                    <div class="book-scene-ledger-item" data-campaign-member="${Number(member.user_id)}">
                        <div class="book-scene-ledger-head">
                            <strong>${escapeHtml(member.username || 'Unbekannt')}</strong>
                            <span>${escapeHtml(member.campaign_role || 'Spieler')}</span>
                        </div>
                        <div class="book-scene-ledger-meta">${escapeHtml(member.status || 'active')}</div>
                        ${canKick && member.status === 'active'
                            && Number(member.user_id) !== Number(campaign.owner_id)
                            && Number(member.user_id) !== Number(user?.id)
                            && ['PLAYER', 'OBSERVER'].includes(String(member.campaign_role || '').toUpperCase())
                            ? `<button type="button" class="btn btn-primary book-scene-action-btn" data-hub-action="kick-player" data-member-id="${Number(member.user_id)}" data-member-name="${escapeHtml(member.username || 'Spieler')}">Spieler entfernen</button>` : ''}
                    </div>
                `).join('')
                : '<div class="book-scene-ledger-item is-empty">Noch keine Mitglieder.</div>';

            let sessionSummary;
            let sessionActions;
            if (!focusedSession) {
                sessionSummary = `<p class="book-scene-panel-copy">Noch keine Session angelegt. ${canManage ? 'Lege die erste Session an und starte direkt in die Vorbereitung.' : 'Die Spielleitung hat noch keine Session eröffnet.'}</p>`;
                sessionActions = canManage
                    ? buildHubActionButton('Session erstellen & zu Play', 'new-session', { primary: true })
                    : buildHubActionButton('Wartet auf DM', 'noop', { disabled: true, primary: false });
            } else {
                const phase = this.getPlayLaunchSessionPhase(focusedSession);
                const activeMap = maps.find((map) => Number(map.id) === Number(focusedSession.map_id)) || null;
                const assignedCount = assignments.filter((assignment) => Number(assignment.session_id) === Number(focusedSession.id)).length;

                // buildStatStrip's tiles are sized/typeset for short numbers
                // (every other caller passes one) - a session name or map
                // name has no such length guarantee, so this uses the
                // ledger-head/meta pairing instead (same as buildCampaignLedger
                // above: title + status pill, then a plain wrapping meta
                // line), which is already built to hold arbitrary text.
                sessionSummary = `
                    <div class="book-scene-ledger-head">
                        <strong>${escapeHtml(focusedSession.name || 'Session')}</strong>
                        <span class="play-launch-status-dot is-${escapeHtml(phase.tone)}">${escapeHtml(phase.label)}</span>
                    </div>
                    <div class="book-scene-ledger-meta">Aktive Karte: ${escapeHtml(activeMap ? activeMap.name : 'Keine')} · Zugewiesene Helden: ${assignedCount}</div>
                `;

                if ((phase.tone === 'live' || phase.tone === 'paused') && canManage) {
                    // Tischplatz: the Spielleitung picks a seat; "Als Spieler"
                    // gives exactly a player's view and rights at this table.
                    const label = phase.tone === 'live' ? 'Als Spielleitung an den Tisch' : 'Als Spielleitung fortsetzen';
                    sessionActions = buildHubActionButton(label, 'open-session-dm', { primary: true, sessionId: Number(focusedSession.id) })
                        + buildHubActionButton('Als Spieler an den Tisch', 'open-session-player', { primary: false, sessionId: Number(focusedSession.id) });
                } else if (phase.tone === 'live' || phase.tone === 'paused') {
                    const label = phase.tone === 'live' ? 'Zu Play' : 'Fortsetzen';
                    sessionActions = buildHubActionButton(label, 'open-session', { primary: true, sessionId: Number(focusedSession.id) });
                } else if ((phase.tone === 'scheduled' || phase.tone === 'ready') && canManage) {
                    sessionActions = buildHubActionButton('Session starten', 'start-session', { primary: true, sessionId: Number(focusedSession.id) });
                } else if (phase.tone === 'scheduled' || phase.tone === 'ready') {
                    sessionActions = buildHubActionButton('Wartet auf DM', 'noop', { disabled: true, primary: false });
                } else if (canManage) {
                    sessionActions = buildHubActionButton('Nächste Session anlegen', 'new-session', { primary: true });
                } else {
                    sessionActions = buildHubActionButton('Abgeschlossen', 'noop', { disabled: true, primary: false });
                }
            }

            const inviteSection = canManage ? `
                <section class="book-scene-panel" id="campaignHubInvite">
                    <span class="book-scene-panel-kicker">Spieler einladen</span>
                    <h2 class="book-scene-panel-title">Einladen</h2>
                    <p class="book-scene-panel-copy">Ein Link für bis zu 5 Beitritte - schick ihn an alle, die mitspielen sollen. Jede Anfrage darüber musst du unten bestätigen, bevor die Person Zugriff bekommt.</p>
                    <div class="book-scene-action-row book-scene-action-row--inline">
                        <button type="button" class="btn btn-primary book-scene-action-btn" data-hub-action="generate-invite" data-testid="hub-invite-create">Einladungslink erzeugen</button>
                    </div>
                    <div class="play-launch-status" data-hub-invite-status role="status" hidden></div>
                    <div data-hub-invite-link-box data-testid="hub-invite-link-box">
                        <div class="book-scene-ledger-item is-empty">Lädt …</div>
                    </div>
                </section>

                <section class="book-scene-panel" id="campaignHubJoinRequests">
                    <span class="book-scene-panel-kicker">Beitrittsanfragen</span>
                    <h2 class="book-scene-panel-title">Warten auf Bestätigung</h2>
                    <div class="book-scene-ledger" data-hub-join-requests data-testid="hub-join-requests">
                        ${pendingMembers.length
                            ? pendingMembers.map((member) => `
                                <div class="book-scene-ledger-item" data-join-request data-user-id="${Number(member.user_id)}">
                                    <div class="book-scene-ledger-head">
                                        <strong>${escapeHtml(member.username || 'Unbekannt')}</strong>
                                        <span>wartet</span>
                                    </div>
                                    <div class="book-scene-action-row book-scene-action-row--inline">
                                        <button type="button" class="btn btn-primary book-scene-action-btn" data-hub-action="approve-join-request" data-testid="hub-join-request-approve">Annehmen</button>
                                        <button type="button" class="btn btn-secondary book-scene-action-btn" data-hub-action="deny-join-request" data-testid="hub-join-request-deny">Ablehnen</button>
                                    </div>
                                </div>
                            `).join('')
                            : '<div class="book-scene-ledger-item is-empty">Keine offenen Beitrittsanfragen.</div>'}
                    </div>
                </section>
            ` : '';

            return this.buildPageShell('campaigns', user, {
                eyebrow: 'Kapitel II',
                title: campaign.name || 'Kampagnen-Hub',
                showRunningHead: false,
                copy: '',
                showRightHeader: false,
                leftPage: `
                    ${this.buildActionButtons([{ label: 'Zur Kampagnenliste', route: '/campaigns' }])}
                    ${this.buildStatStrip([
                        { value: String(members.length), label: 'Mitglieder' },
                        { value: String(sessions.length), label: 'Sessions' },
                        { value: String(campaignCharacterCount), label: 'Kampagnen-Helden' },
                    ])}
                    ${inviteSection}
                    <section class="book-scene-panel">
                        <div class="book-scene-ledger-head">
                            <span class="book-scene-panel-kicker">Kampagnen-Hub</span>
                            <span class="play-launch-status-dot${campaignStatusTone ? ` is-${escapeHtml(campaignStatusTone)}` : ''}">${escapeHtml(campaignStatus)}</span>
                        </div>
                        <h2 class="book-scene-panel-title">Übersicht</h2>
                        <p class="book-scene-panel-copy">${escapeHtml(campaign.description || 'Noch keine Beschreibung hinterlegt.')}</p>
                        <div class="book-scene-ledger">${memberRows}</div>
                        ${canLeave ? '<div class="book-scene-action-row"><button type="button" class="btn btn-primary book-scene-action-btn" data-hub-action="leave-campaign">Kampagne verlassen</button></div>' : ''}
                        <p data-hub-membership-status role="status" aria-live="polite" hidden></p>
                    </section>
                `,
                rightPage: `
                    <section class="book-scene-panel" id="campaignHubSessionPrep">
                        <span class="book-scene-panel-kicker">Vor dem Spielabend</span>
                        <h2 class="book-scene-panel-title">Session-Vorbereitung</h2>
                        ${sessionSummary}
                        <div class="book-scene-action-row book-scene-action-row--inline">${sessionActions}</div>
                        <div class="play-launch-status" data-hub-status role="status" hidden></div>
                        ${canManage ? this.buildActionButtons([{
                            label: 'Karten und Besetzung vorbereiten',
                            href: buildIntentHref('/campaigns', { campaign_id: campaign.id, workspace: 1 }),
                        }]) : ''}
                    </section>
                `,
            });
        },

        setCampaignHubStatus(message, isError = false) {
            const node = this.sceneSurface ? this.sceneSurface.querySelector('[data-hub-status]') : null;
            if (!node) {
                return;
            }
            if (!message) {
                node.hidden = true;
                return;
            }
            node.hidden = false;
            node.textContent = message;
            node.classList.toggle('is-error', Boolean(isError));
        },

        async startCampaignHubSession(campaignId, sessionId) {
            this.setCampaignHubStatus('Session wird gestartet …');
            try {
                await window.Auth.makeAuthRequest(`/api/sessions/${sessionId}/start`, 'POST');
                this.enterPlay({ campaignId, sessionId, sourceRoute: 'campaigns', seat: 'dm' });
            } catch (error) {
                this.setCampaignHubStatus(error.message || 'Session konnte nicht gestartet werden.', true);
            }
        },

        async createCampaignHubSession(campaignId) {
            this.setCampaignHubStatus('Neue Session wird angelegt …');
            try {
                const session = await window.Auth.makeAuthRequest(`/api/campaigns/${campaignId}/sessions`, 'POST', {
                    name: 'Session ' + new Date().toLocaleDateString('de-DE'),
                });
                await window.Auth.makeAuthRequest(`/api/sessions/${session.id}/start`, 'POST');
                this.enterPlay({ campaignId, sessionId: session.id, sourceRoute: 'campaigns', seat: 'dm' });
            } catch (error) {
                this.setCampaignHubStatus(error.message || 'Session konnte nicht erstellt werden.', true);
            }
        },

        setCampaignHubInviteStatus(message, isError = false) {
            const node = this.sceneSurface ? this.sceneSurface.querySelector('[data-hub-invite-status]') : null;
            if (!node) {
                return;
            }
            node.hidden = !message;
            node.textContent = message || '';
            node.classList.toggle('is-error', Boolean(isError));
        },

        async generateCampaignHubInvite(campaignId) {
            this.setCampaignHubInviteStatus('Einladungslink wird erzeugt …');
            try {
                await window.Auth.makeAuthRequest(`/api/campaigns/${campaignId}/invite`, 'POST', {});
                this.setCampaignHubInviteStatus('');
                await this.loadCampaignHubInvites(campaignId);
            } catch (error) {
                this.setCampaignHubInviteStatus(error.message || 'Einladungslink konnte nicht erzeugt werden.', true);
            }
        },

        // Fetches this campaign's current invite link (GET /invites) and
        // (re)renders it - called once when the hub opens, so a link
        // generated before a reload is still there, and again after
        // generating a new one instead of only flashing it transiently.
        async loadCampaignHubInvites(campaignId) {
            const section = this.sceneSurface ? this.sceneSurface.querySelector('#campaignHubInvite') : null;
            const box = section ? section.querySelector('[data-hub-invite-link-box]') : null;
            if (!box || !window.Auth || typeof window.Auth.makeAuthRequest !== 'function') {
                return;
            }
            try {
                const data = await window.Auth.makeAuthRequest(`/api/campaigns/${campaignId}/invites`);
                const link = data?.invite_link || null;
                box.innerHTML = link
                    ? `
                        <div class="book-scene-ledger-item">
                            <div class="book-scene-ledger-head">
                                <strong>Einladungslink</strong>
                                <span>${Number(link.use_count)}/${Number(link.max_uses)} genutzt</span>
                            </div>
                            <div class="book-scene-invite-row">
                                <input type="text" readonly data-hub-invite-link-field
                                    aria-label="Einladungslink"
                                    value="${escapeHtml(`${window.location.origin}/invite/${link.invite_token}`)}">
                                <button type="button" class="btn btn-secondary book-scene-action-btn" data-hub-action="copy-invite-link">Kopieren</button>
                            </div>
                        </div>
                    `
                    : '<div class="book-scene-ledger-item is-empty">Noch kein Einladungslink erzeugt.</div>';
            } catch (error) {
                box.innerHTML = '<div class="book-scene-ledger-item is-empty">Einladungslink konnte nicht geladen werden.</div>';
            }
        },

        async decideCampaignHubJoinRequest(campaignId, userId, decision) {
            this.setCampaignHubInviteStatus(decision === 'approve' ? 'Anfrage wird angenommen …' : 'Anfrage wird abgelehnt …');
            try {
                await window.Auth.makeAuthRequest(
                    `/api/campaigns/${campaignId}/join-requests/${userId}/${decision}`, 'POST');
                // Membership, member count, and the invite link's use count
                // all shift together - a full hub reload keeps them in sync
                // instead of patching each piece by hand (and replaces this
                // status message along with everything else).
                await this.renderCampaignHubDetail(campaignId);
            } catch (error) {
                this.setCampaignHubInviteStatus(error.message || 'Aktion fehlgeschlagen.', true);
            }
        },

        async changeCampaignMembership(campaignId, button) {
            const leave = button.dataset.hubAction === 'leave-campaign';
            const name = button.dataset.memberName || 'Spieler';
            const prompt = leave
                ? 'Diese Kampagne wirklich verlassen? Dein Zugang zur Runde endet sofort.'
                : `${name} wirklich aus dieser Kampagne entfernen? Der Zugang zur Runde endet sofort.`;
            if (!window.confirm(prompt)) return;
            const status = this.sceneSurface.querySelector('[data-hub-membership-status]');
            const say = (message) => {
                if (status) { status.hidden = false; status.textContent = message; }
            };
            button.disabled = true;
            say(leave ? 'Kampagne wird verlassen …' : 'Spieler wird entfernt …');
            try {
                if (leave) {
                    await window.Auth.makeAuthRequest(`/api/campaigns/${campaignId}/leave`, 'POST');
                    // Load a fresh document so no departed campaign state stays open.
                    window.location.href = '/campaigns';
                } else {
                    await window.Auth.makeAuthRequest(`/api/campaigns/${campaignId}/moderation/actions`, 'POST', {
                        action_type: 'kick', subject_user_id: Number(button.dataset.memberId),
                    });
                    if (!button.isConnected) return;
                    await this.renderCampaignHubDetail(campaignId);
                    const updated = this.sceneSurface.querySelector('[data-hub-membership-status]');
                    if (updated) { updated.hidden = false; updated.textContent = `${name} wurde aus der Kampagne entfernt.`; }
                }
            } catch (error) {
                say(error.message || 'Aktion fehlgeschlagen. Bitte versuche es erneut.');
                button.disabled = false;
            }
        },

        async copyInviteLinkField(field, button) {
            if (!field || !field.value) {
                return;
            }
            let copied = false;
            try {
                await navigator.clipboard.writeText(field.value);
                copied = true;
            } catch (error) {
                field.focus();
                field.select();
                copied = Boolean(document.execCommand && document.execCommand('copy'));
            }
            if (button) {
                const label = button.textContent;
                button.textContent = copied ? 'Kopiert ✓' : 'Manuell kopieren (Strg+C)';
                window.setTimeout(() => { button.textContent = label; }, 2000);
            }
        },

        bindCampaignHubDetailActions(campaignId) {
            if (!this.sceneSurface) {
                return;
            }
            this.sceneSurface.querySelectorAll('[data-hub-action="leave-campaign"], [data-hub-action="kick-player"]').forEach((button) => {
                button.addEventListener('click', () => this.changeCampaignMembership(campaignId, button));
            });
            this.sceneSurface.querySelectorAll('[data-hub-action="open-session"]').forEach((node) => {
                node.addEventListener('click', () => {
                    const sessionId = Number(node.getAttribute('data-hub-session-id'));
                    this.enterPlay({ campaignId, sessionId, sourceRoute: 'campaigns' });
                });
            });
            [['open-session-dm', 'dm'], ['open-session-player', 'player']].forEach(([hubAction, seat]) => {
                this.sceneSurface.querySelectorAll(`[data-hub-action="${hubAction}"]`).forEach((node) => {
                    node.addEventListener('click', () => {
                        const sessionId = Number(node.getAttribute('data-hub-session-id'));
                        this.enterPlay({ campaignId, sessionId, sourceRoute: 'campaigns', seat });
                    });
                });
            });
            this.sceneSurface.querySelectorAll('[data-hub-action="start-session"]').forEach((node) => {
                node.addEventListener('click', () => {
                    const sessionId = Number(node.getAttribute('data-hub-session-id'));
                    this.startCampaignHubSession(campaignId, sessionId);
                });
            });
            this.sceneSurface.querySelectorAll('[data-hub-action="new-session"]').forEach((node) => {
                node.addEventListener('click', () => {
                    this.createCampaignHubSession(campaignId);
                });
            });
            this.sceneSurface.querySelectorAll('[data-hub-action="generate-invite"]').forEach((node) => {
                node.addEventListener('click', () => {
                    this.generateCampaignHubInvite(campaignId);
                });
            });
            // The invite link box renders async (loadCampaignHubInvites), so
            // its copy button doesn't exist yet at bind time - delegate from
            // the static box container instead of binding it directly.
            this.sceneSurface.querySelectorAll('[data-hub-invite-link-box]').forEach((node) => {
                node.addEventListener('click', (event) => {
                    const button = event.target.closest('[data-hub-action="copy-invite-link"]');
                    if (!button) {
                        return;
                    }
                    const row = button.closest('.book-scene-ledger-item');
                    const field = row ? row.querySelector('[data-hub-invite-link-field]') : null;
                    this.copyInviteLinkField(field, button);
                });
            });
            this.sceneSurface.querySelectorAll('[data-hub-action="approve-join-request"], [data-hub-action="deny-join-request"]').forEach((node) => {
                node.addEventListener('click', () => {
                    const row = node.closest('[data-join-request]');
                    const userId = row ? Number(row.getAttribute('data-user-id')) : null;
                    if (!userId) {
                        return;
                    }
                    const decision = node.getAttribute('data-hub-action') === 'approve-join-request' ? 'approve' : 'deny';
                    this.decideCampaignHubJoinRequest(campaignId, userId, decision);
                });
            });
        },

        async renderCampaignHubDetail(campaignId) {
            const id = Number(campaignId);
            if (!this.sceneSurface || !Number.isInteger(id) || id <= 0) {
                return;
            }

            const renderVersion = this.sceneRenderVersion = (this.sceneRenderVersion || 0) + 1;

            this.currentView = 'campaigns';
            this.currentPage = 'campaigns';
            document.body.dataset.bookSceneRoute = 'campaigns';
            this.updateBookmarkPosition('/campaigns');
            window.history.replaceState({ book_scene: 'campaigns' }, '', `/campaigns?campaign_id=${id}`);
            this.sceneSurface.dataset.bookRoute = 'campaigns';
            this.sceneSurface.innerHTML = this.buildPageShell('campaigns', this.sceneUser, {
                eyebrow: 'Kapitel II',
                title: 'Kampagnen-Hub',
                showRunningHead: false,
                copy: '',
                showRightHeader: false,
                leftPage: '<p class="book-scene-panel-copy">Hub wird geladen …</p>',
            });
            this.bindSceneNavigation();

            if (!window.Auth || typeof window.Auth.makeAuthRequest !== 'function') {
                return;
            }

            try {
                const data = await window.Auth.makeAuthRequest(`/api/campaigns/${id}`);
                if (!data || this.sceneRenderVersion !== renderVersion) {
                    return;
                }
                this.sceneSurface.innerHTML = this.buildCampaignHubDetailMarkup(this.sceneUser, data);
                this.bindSceneNavigation();
                this.bindCampaignHubDetailActions(id);
                this.loadCampaignHubInvites(id);
            } catch (error) {
                if (this.sceneRenderVersion !== renderVersion) return;
                this.sceneSurface.innerHTML = this.buildPageShell('campaigns', this.sceneUser, {
                    eyebrow: 'Kapitel II',
                    title: 'Kampagnen-Hub',
                    showRunningHead: false,
                    copy: '',
                    showRightHeader: false,
                    leftPage: `
                        <p class="book-scene-panel-copy">${escapeHtml(error?.message || 'Kampagnen-Hub konnte nicht geladen werden.')}</p>
                        ${this.buildActionButtons([{ label: 'Zur Kampagnenliste', route: '/campaigns', primary: true }])}
                    `,
                });
                this.bindSceneNavigation();
            }
        },

        buildCharactersMarkup(user, snapshot = null) {
            const characters = snapshot?.characters || [];
            const campaigns = (snapshot?.campaigns || []).filter(campaign => campaign.is_member);
            const sharedCharacters = snapshot?.shared_characters || [];
            const distinctClasses = new Set(characters.map((character) => character.class).filter(Boolean)).size;
            const highestLevel = characters.reduce((highest, character) => Math.max(highest, Number(character.level || 1)), 1);

            return this.buildPageShell('characters', user, {
                eyebrow: 'Kapitel III',
                title: 'Charaktere',
                showRunningHead: false,
                copy: '',
                rightEyebrow: 'Nächste Schritte',
                rightTitle: 'Helden vorbereiten',
                rightCopy: '',
                chips: [`${characters.length} Helden`, `${distinctClasses} Klassen`, `Höchstes Level ${highestLevel}`],
                rightPage: `
                    <div id="charactersMessageBox" class="book-scene-note" role="status" hidden></div>
                    <div id="charactersJourneyNote" class="book-scene-note" hidden></div>
                    <section class="book-scene-panel">
                        <p>Übernimm einen exportierten Roll-Drauf-Light- oder D&amp;D-5e-Charakter in dein Archiv.</p>
                        ${this.buildActionButtons([
                            { label: 'Charakter importieren', href: buildIntentHref('/characters', { intent: 'import' }), primary: true },
                        ])}
                        <p class="book-form-banner is-success" data-character-import-status role="status" aria-live="polite" hidden></p>
                    </section>
                    <section class="book-scene-panel" data-shared-characters>
                        <h2 class="book-scene-panel-title">Charaktere deiner Runden</h2>
                        ${snapshot?.shared_characters_error
                            ? '<p role="status">Geteilte Charaktere konnten nicht geladen werden. Bitte lade die Seite erneut.</p>'
                            : sharedCharacters.length ? this.buildCharacterLedger(sharedCharacters)
                            : '<p>Noch keine geteilten Charaktere. Andere Mitglieder können ihre Helden über die Kampagnen-Zuordnung in ihrem Archiv mit deiner Runde teilen.</p>'}
                    </section>
                `,
                leftPage: `
                    ${this.buildStatStrip([
                        { value: String(characters.length), label: 'Charaktere' },
                        { value: String(distinctClasses), label: 'Klassen' },
                        { value: String(highestLevel), label: 'Höchstes Level' },
                    ])}
                    <section class="book-scene-panel">
                        <span class="book-scene-panel-kicker">Archiv</span>
                        <h2 class="book-scene-panel-title">Heldenarchiv</h2>
                        ${this.buildActionButtons([
                            { label: 'Held anlegen', href: '/srd-creator', primary: true },
                        ])}
                        ${this.buildCharacterLedger(characters, campaigns)}
                    </section>
                    ${this.buildOpenDrafts(snapshot?.drafts)}
                    ${this.buildArchivedCharacters(snapshot?.archived_characters)}
                `,
            });
        },

        buildRouteMarkup(routeKey, user, snapshot) {
            if (routeKey === 'campaigns') {
                return this.buildCampaignsMarkup(user, snapshot);
            }
            if (routeKey === 'characters') {
                return this.buildCharactersMarkup(user, snapshot);
            }
            return this.buildDashboardMarkup(user, snapshot);
        },

        bindSceneNavigation() {
            if (!this.sceneSurface) {
                return;
            }

            this.sceneSurface.querySelectorAll('[data-campaign-list]').forEach((list) => {
                if (list.dataset.bound === 'true') return;
                list.dataset.bound = 'true';
                const rows = [...list.querySelectorAll('[data-testid="campaign-ledger-item"]')];
                const search = list.querySelector('[data-campaign-search]');
                const previous = list.querySelector('[data-campaign-prev]');
                const next = list.querySelector('[data-campaign-next]');
                const count = list.querySelector('[data-campaign-count]');
                const searchable = new Map(rows.map((row) => [row, [row.querySelector('.book-scene-ledger-head strong')?.textContent, row.querySelector('.book-scene-ledger-copy')?.textContent].join(' ').toLocaleLowerCase('de')]));
                let page = 0;
                const refresh = () => {
                    const term = search.value.trim().toLocaleLowerCase('de');
                    const matches = rows.filter((row) => searchable.get(row).includes(term));
                    page = Math.max(0, Math.min(page, Math.ceil(matches.length / 5) - 1));
                    const visible = new Set(matches.slice(page * 5, page * 5 + 5));
                    rows.forEach((row) => { row.hidden = !visible.has(row); });
                    previous.disabled = page === 0;
                    next.disabled = (page + 1) * 5 >= matches.length;
                    count.textContent = matches.length ? `${page * 5 + 1}–${Math.min((page + 1) * 5, matches.length)} von ${matches.length} Kampagnen` : 'Keine passende Kampagne';
                };
                search.addEventListener('input', () => { page = 0; refresh(); });
                previous.addEventListener('click', () => { page--; refresh(); });
                next.addEventListener('click', () => { page++; refresh(); });
                refresh();
            });

            window.CreationEngineNavigation?.hydrate(this.sceneSurface);
            window.RegelwerkNavigation?.hydrate(this.sceneSurface);

            this.sceneSurface.querySelectorAll('[data-dashboard-route]').forEach((node) => {
                node.addEventListener('click', () => {
                    const route = node.getAttribute('data-dashboard-route');
                    if (!route) {
                        return;
                    }
                    this.pageTurn(route, this.sceneUser);
                });
            });

            this.sceneSurface.querySelectorAll('[data-dashboard-href]').forEach((node) => {
                const navigate = () => {
                    const href = node.getAttribute('data-dashboard-href');
                    if (!href) {
                        return;
                    }
                    window.location.href = href;
                };
                node.addEventListener('click', navigate);
                // Ein-Engine-Invariante (§3): Nicht-Button-Klickziele (z. B.
                // die Ledger-Zeile, D02) müssen per Tastatur dieselbe
                // Transition auslösen wie per Maus.
                if (node.tagName !== 'BUTTON' && node.tagName !== 'A') {
                    node.addEventListener('keydown', (event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            navigate();
                        }
                    });
                }
            });

            this.sceneSurface.querySelectorAll('[data-dashboard-detail]').forEach((node) => {
                const openDetail = (event) => {
                    // The ledger row and its own "Hub öffnen" button both
                    // carry this attribute (row = whole-row click target per
                    // D02, button = the visible affordance inside it) - stop
                    // the bubble here so a button click does not also
                    // re-trigger the ancestor row's identical handler.
                    if (event) {
                        event.stopPropagation();
                    }
                    const detail = node.getAttribute('data-dashboard-detail');
                    if (!detail) {
                        return;
                    }
                    const [kind, rawId] = detail.split(':');
                    if (kind === 'campaign') {
                        this.renderCampaignHubDetail(Number(rawId));
                    }
                };
                node.addEventListener('click', openDetail);
                if (node.tagName !== 'BUTTON' && node.tagName !== 'A') {
                    node.addEventListener('keydown', (event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            openDetail();
                        }
                    });
                }
            });

            this.sceneSurface.querySelectorAll('[data-character-campaign]').forEach((form) => {
                form.addEventListener('submit', async (event) => {
                    event.preventDefault();
                    const button = form.querySelector('button');
                    const status = form.querySelector('[role="status"]');
                    const value = form.querySelector('select').value;
                    button.disabled = true;
                    status.hidden = false;
                    status.textContent = 'Zuordnung wird gespeichert …';
                    try {
                        const character = await window.Auth.makeAuthRequest(
                            `/api/characters/${Number(form.dataset.characterCampaign)}/campaign`,
                            'PUT', { campaign_id: value ? Number(value) : null });
                        if (!form.isConnected) return;
                        const snapshot = this.sceneSnapshot;
                        snapshot.characters = snapshot.characters.map(c => Number(c.id) === Number(character.id) ? character : c);
                        this.renderSceneRoute('characters', this.sceneUser, snapshot);
                        const message = this.sceneSurface.querySelector('#charactersMessageBox');
                        message.hidden = false;
                        message.textContent = character.campaign_id ? 'Charakter mit der Kampagne geteilt.' : 'Charakter ist nur für dich sichtbar.';
                    } catch (error) {
                        status.textContent = error.message || 'Zuordnung konnte nicht gespeichert werden.';
                    } finally {
                        button.disabled = false;
                    }
                });
            });

            this.sceneSurface.querySelectorAll('[data-character-action]').forEach((node) => {
                node.addEventListener('click', () => this.runCharacterAction(node));
            });

            this.sceneSurface.querySelectorAll('[data-dashboard-action="request-campaign-join"]').forEach((node) => {
                node.addEventListener('click', async () => {
                    const box = node.closest('[data-campaign-id]');
                    const status = box.querySelector('[data-join-status]');
                    node.disabled = true;
                    status.hidden = false;
                    status.textContent = 'Anfrage wird gesendet …';
                    try {
                        await window.Auth.makeAuthRequest(`/api/campaigns/${Number(box.dataset.campaignId)}/join-requests`, 'POST');
                        status.textContent = 'Beitrittsanfrage gesendet. Die Spielleitung muss sie noch bestätigen.';
                        node.textContent = 'Anfrage gesendet';
                    } catch (error) {
                        status.textContent = error.message || 'Anfrage konnte nicht gesendet werden.';
                        node.disabled = false;
                    }
                });
            });

            this.sceneSurface.querySelectorAll('[data-dashboard-action="join-campaign"]').forEach((node) => {
                node.addEventListener('click', async () => {
                    const joinBox = node.closest('.book-scene-join');
                    if (!joinBox) {
                        return;
                    }
                    const campaignId = Number(joinBox.getAttribute('data-campaign-id'));
                    const input = joinBox.querySelector('[data-join-input]');
                    const status = joinBox.querySelector('[data-join-status]');
                    const say = (text) => {
                        if (status) {
                            status.hidden = false;
                            status.textContent = text;
                        }
                    };
                    const code = input ? input.value.trim() : '';
                    if (!code) {
                        say('Bitte zuerst den Einladungscode einfügen.');
                        if (input) {
                            input.focus();
                        }
                        return;
                    }
                    node.disabled = true;
                    try {
                        const result = await window.Auth.makeAuthRequest(
                            `/api/campaigns/${campaignId}/accept-invite`,
                            'POST',
                            { token: code },
                        );
                        if (result && result.status === 'pending') {
                            // Generic multi-use link (2026-09-22): redeeming it
                            // files a join request, not instant membership - the
                            // DM approves it from the hub, so there is no hub to
                            // open yet. Don't navigate anywhere.
                            say('Beitrittsanfrage gesendet. Die Spielleitung muss sie noch bestätigen.');
                            node.disabled = false;
                        } else {
                            say('Beigetreten! Der Kampagnen-Hub öffnet sich …');
                            window.location.href = `/campaigns?campaign_id=${campaignId}`;
                        }
                    } catch (error) {
                        node.disabled = false;
                        say(error.message || 'Beitritt fehlgeschlagen. Bitte prüfe den Code.');
                    }
                });
            });

            this.sceneSurface.querySelectorAll('[data-dashboard-section]').forEach((node) => {
                node.addEventListener('click', () => {
                    const section = node.getAttribute('data-dashboard-section');
                    if (!section) {
                        return;
                    }
                    const target = this.sceneSurface.querySelector(`[data-dashboard-section-target="${section}"]`);
                    if (target) {
                        target.scrollIntoView({ behavior: reducedMotion.matches ? 'auto' : 'smooth', block: 'start' });
                    }
                });
            });

            this.sceneSurface.querySelectorAll('[data-dashboard-action="play-launch"]').forEach((node) => {
                node.addEventListener('click', () => {
                    this.openPlayLaunch();
                });
            });

            this.sceneSurface.querySelectorAll('[data-dashboard-action="logout"]').forEach((node) => {
                node.addEventListener('click', async () => {
                    if (window.Auth && typeof window.Auth.logout === 'function') {
                        await window.Auth.logout();
                        return;
                    }
                    window.location.href = '/login.html';
                });
            });
        },

        bindDashboardNavigation() {
            this.bindSceneNavigation();
        },

        // ── Page content (editable copy) ────────────────────────────────
        // Text lives in the page_content table (see vtt/content_defaults.py
        // for the current defaults), fetched once per page and cached here.
        // Every call site passes its own hardcoded string as `fallback`, so
        // a fetch failure or a not-yet-seeded key never blanks the UI - it
        // just shows the same text this file always had.

        async loadPageContent(routeKey) {
            this.pageContent = this.pageContent || {};

            const fetches = [];
            if (!this.pageContent.shared) {
                fetches.push(
                    this._fetchContentMap('shared').then((map) => { this.pageContent.shared = map; })
                );
            }
            if (routeKey && !this.pageContent[routeKey]) {
                fetches.push(
                    this._fetchContentMap(routeKey).then((map) => { this.pageContent[routeKey] = map; })
                );
            }
            if (fetches.length) {
                await Promise.allSettled(fetches);
            }
        },

        async _fetchContentMap(pageKey) {
            try {
                const response = await fetch(`/api/content/${encodeURIComponent(pageKey)}`, { credentials: 'include' });
                if (!response.ok) {
                    return {};
                }
                const data = await response.json();
                return (data && typeof data === 'object') ? data : {};
            } catch (error) {
                console.warn(`Failed to load page content for "${pageKey}", using built-in text.`, error);
                return {};
            }
        },

        content(key, fallback, vars = null) {
            const routeMap = (this.pageContent && this.currentView && this.pageContent[this.currentView]) || {};
            const sharedMap = (this.pageContent && this.pageContent.shared) || {};
            let text = routeMap[key] ?? sharedMap[key] ?? fallback;

            if (vars) {
                Object.entries(vars).forEach(([token, value]) => {
                    text = text.replace(new RegExp(`\\{${token}\\}`, 'g'), String(value));
                });
            }
            return text;
        },

        // ── Play Quick Launch ────────────────────────────────────────────
        // A project-browser-style popup (grid of campaigns, one clear
        // action each) for getting to the play table fast, reachable via
        // the Play ribbon button on every book-mode page. Lives here
        // rather than in a per-page template since buildRibbon() already
        // renders the same ribbon for dashboard/campaigns/characters/
        // character-sheet - one shared implementation keeps all four in
        // sync automatically.

        ensurePlayLaunchModal() {
            if (document.getElementById('playLaunchModal')) {
                return document.getElementById('playLaunchModal');
            }

            const modalHTML = `
                <div id="playLaunchModal" class="play-launch-overlay" hidden role="dialog" aria-modal="true" aria-labelledby="playLaunchTitle">
                    <div class="play-launch-box">
                        <div class="play-launch-header">
                            <div>
                                <h2 id="playLaunchTitle">${escapeHtml(this.content('play_launch.title', 'Play'))}</h2>
                                <p>${escapeHtml(this.content('play_launch.subtitle', 'Wähle eine Session oder starte in wenigen Schritten eine neue.'))}</p>
                            </div>
                            <button type="button" class="play-launch-close" data-play-launch-close aria-label="Schließen">&times;</button>
                        </div>
                        <div class="play-launch-body">
                            <div id="playLaunchStatus" class="play-launch-status" hidden></div>
                            <div id="playLaunchContent">${escapeHtml(this.content('play_launch.loading', 'Lade Kampagnen...'))}</div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            const modal = document.getElementById('playLaunchModal');
            modal.addEventListener('click', (event) => {
                if (event.target === modal || event.target.hasAttribute('data-play-launch-close')) {
                    this.closePlayLaunch();
                }
            });
            return modal;
        },

        openPlayLaunch() {
            const modal = this.ensurePlayLaunchModal();
            modal.hidden = false;
            this.setPlayLaunchStatus('');
            this._playLaunchKeydownHandler = this._playLaunchKeydownHandler || ((event) => {
                if (event.key === 'Escape') {
                    this.closePlayLaunch();
                }
            });
            document.addEventListener('keydown', this._playLaunchKeydownHandler);
            this.loadPlayLaunch();
        },

        closePlayLaunch() {
            const modal = document.getElementById('playLaunchModal');
            if (modal) {
                modal.hidden = true;
            }
            if (this._playLaunchKeydownHandler) {
                document.removeEventListener('keydown', this._playLaunchKeydownHandler);
            }
        },

        setPlayLaunchStatus(message, isError = false) {
            const node = document.getElementById('playLaunchStatus');
            if (!node) return;
            if (!message) {
                node.hidden = true;
                return;
            }
            node.hidden = false;
            node.textContent = message;
            node.classList.toggle('is-error', Boolean(isError));
        },

        async loadPlayLaunch() {
            const content = document.getElementById('playLaunchContent');
            if (!content) return;
            content.textContent = this.content('play_launch.loading', 'Lade Kampagnen...');

            if (!window.Auth || typeof window.Auth.makeAuthRequest !== 'function') {
                this.setPlayLaunchStatus('Nicht angemeldet.', true);
                return;
            }

            try {
                const snapshot = await window.Auth.makeAuthRequest('/api/dashboard/home');
                // makeAuthRequest returns null when the session was expired and it
                // already redirected to /login.html - nothing left to render here.
                if (!snapshot) return;
                this.renderPlayLaunch(snapshot.campaigns || [], snapshot.sessions || []);
            } catch (error) {
                content.innerHTML = '';
                this.setPlayLaunchStatus(error.message || 'Kampagnen konnten nicht geladen werden.', true);
            }
        },

        getPlayLaunchSessionPhase(session) {
            const status = String(session?.runtime_status || '').trim().toLowerCase();
            if (status === 'in_progress' || status === 'active' || status === 'live') {
                return { label: this.content('play_launch.phase_live', 'Live'), tone: 'live' };
            }
            if (status === 'paused') {
                return { label: this.content('play_launch.phase_paused', 'Pausiert'), tone: 'paused' };
            }
            if (status === 'ended' || status === 'completed') {
                return { label: this.content('play_launch.phase_ended', 'Beendet'), tone: 'ended' };
            }
            if (status === 'ready') {
                return { label: this.content('play_launch.phase_ready', 'Bereit'), tone: 'ready' };
            }
            return { label: this.content('play_launch.phase_scheduled', 'Geplant'), tone: 'scheduled' };
        },

        renderPlayLaunch(campaigns, sessions) {
            const content = document.getElementById('playLaunchContent');
            if (!content) return;

            if (!campaigns.length) {
                content.innerHTML = `
                    <div class="play-launch-empty">
                        <h3>${escapeHtml(this.content('play_launch.empty_title', 'Noch keine Kampagne'))}</h3>
                        <p>${escapeHtml(this.content('play_launch.empty_copy', 'Leg direkt los: Name eingeben, wir legen Kampagne und erste Session an und du bist am Tisch.'))}</p>
                        <div class="play-launch-quickcreate">
                            <input type="text" id="playLaunchNewCampaignName" placeholder="${escapeHtml(this.content('play_launch.empty_name_placeholder', 'Name deiner Kampagne'))}" maxlength="255">
                            <button class="btn btn-primary" id="playLaunchQuickCreateBtn" type="button" data-play-launch-create-campaign>${escapeHtml(this.content('play_launch.empty_create_button', 'Kampagne erstellen & zu Play'))}</button>
                        </div>
                    </div>
                `;
                content.querySelector('[data-play-launch-create-campaign]').addEventListener('click', () => {
                    this.quickCreateCampaignAndPlay();
                });
                return;
            }

            const sessionsByCampaign = new Map();
            sessions.forEach((session) => {
                const list = sessionsByCampaign.get(session.campaign_id) || [];
                list.push(session);
                sessionsByCampaign.set(session.campaign_id, list);
            });

            const cards = campaigns.map((campaign) => {
                const campaignSessions = sessionsByCampaign.get(campaign.id) || [];
                // Sessions already arrive ordered by relevance (live/newest
                // first, then soonest scheduled) - see _build_session_summaries
                // server-side, which this list is sourced from.
                const topSession = campaignSessions[0] || null;
                const roleLabel = campaign.is_owner
                    ? this.content('play_launch.role_dm', 'DM')
                    : (campaign.your_role || this.content('play_launch.role_player', 'Spieler'));
                const canManage = Boolean(campaign.is_owner);
                const memberCountText = this.content('play_launch.member_count', '{count} Mitglieder', {
                    count: Number(campaign.member_count || 0),
                });

                let statusDot = '';
                let sessionLine = '';
                let action = '';

                if (topSession) {
                    const phase = this.getPlayLaunchSessionPhase(topSession);
                    statusDot = `<span class="play-launch-status-dot is-${escapeHtml(phase.tone)}">${escapeHtml(phase.label)}</span>`;
                    sessionLine = `<div class="play-launch-card-session">${escapeHtml(topSession.name)}</div>`;

                    if ((phase.tone === 'live' || phase.tone === 'paused') && canManage) {
                        // Tischplatz: the Spielleitung chooses its seat.
                        action = `<div class="play-launch-card-actions">`
                            + `<button class="btn btn-primary btn-sm" type="button" data-play-launch-open="${campaign.id}:${topSession.id}" data-play-launch-seat="dm">${escapeHtml(this.content('play_launch.action_seat_dm', 'Als Spielleitung'))}</button>`
                            + `<button class="btn btn-secondary btn-sm" type="button" data-play-launch-open="${campaign.id}:${topSession.id}" data-play-launch-seat="player">${escapeHtml(this.content('play_launch.action_seat_player', 'Als Spieler'))}</button>`
                            + `</div>`;
                    } else if (phase.tone === 'live' || phase.tone === 'paused') {
                        const label = phase.tone === 'live'
                            ? this.content('play_launch.action_to_play', 'Zu Play')
                            : this.content('play_launch.action_resume', 'Fortsetzen');
                        action = `<button class="btn btn-primary btn-sm" type="button" data-play-launch-open="${campaign.id}:${topSession.id}">${escapeHtml(label)}</button>`;
                    } else if ((phase.tone === 'scheduled' || phase.tone === 'ready') && canManage) {
                        action = `<button class="btn btn-primary btn-sm" type="button" data-play-launch-start="${campaign.id}:${topSession.id}">${escapeHtml(this.content('play_launch.action_start_session', 'Session starten'))}</button>`;
                    } else if (phase.tone === 'scheduled' || phase.tone === 'ready') {
                        action = `<button class="btn btn-secondary btn-sm" type="button" disabled>${escapeHtml(this.content('play_launch.action_waiting_for_dm', 'Wartet auf DM'))}</button>`;
                    } else if (canManage) {
                        action = `<button class="btn btn-primary btn-sm" type="button" data-play-launch-new-session="${campaign.id}">${escapeHtml(this.content('play_launch.action_next_session', 'Nächste Session'))}</button>`;
                    } else {
                        action = `<button class="btn btn-secondary btn-sm" type="button" data-play-launch-goto="/campaigns?campaign_id=${campaign.id}">${escapeHtml(this.content('play_launch.action_open_campaign', 'Kampagne öffnen'))}</button>`;
                    }
                } else {
                    sessionLine = `<div class="play-launch-card-session muted">${escapeHtml(this.content('play_launch.no_session_yet', 'Noch keine Session'))}</div>`;
                    action = canManage
                        ? `<button class="btn btn-primary btn-sm" type="button" data-play-launch-new-session="${campaign.id}">${escapeHtml(this.content('play_launch.action_create_session', 'Session erstellen & zu Play'))}</button>`
                        : `<button class="btn btn-secondary btn-sm" type="button" disabled>${escapeHtml(this.content('play_launch.action_waiting_for_dm_player', 'Warte auf DM'))}</button>`;
                }

                return `
                    <div class="play-launch-card">
                        <div class="play-launch-card-top">
                            <h3 class="play-launch-card-title">${escapeHtml(campaign.name)}</h3>
                            ${statusDot}
                        </div>
                        <div class="play-launch-card-meta">${escapeHtml(roleLabel)} &middot; ${escapeHtml(memberCountText)}</div>
                        ${sessionLine}
                        ${action}
                    </div>
                `;
            }).join('');

            content.innerHTML = `
                <div class="play-launch-grid">${cards}</div>
                <div class="play-launch-newcampaign-row">
                    <button class="btn btn-secondary btn-sm" type="button" data-play-launch-goto="/campaigns">${escapeHtml(this.content('play_launch.add_campaign_button', 'Weitere Kampagne anlegen'))}</button>
                </div>
            `;

            content.querySelectorAll('[data-play-launch-open]').forEach((node) => {
                node.addEventListener('click', () => {
                    const [campaignId, sessionId] = node.getAttribute('data-play-launch-open').split(':').map(Number);
                    this.openPlayFromLaunch(campaignId, sessionId, node.getAttribute('data-play-launch-seat'));
                });
            });
            content.querySelectorAll('[data-play-launch-start]').forEach((node) => {
                node.addEventListener('click', () => {
                    const [campaignId, sessionId] = node.getAttribute('data-play-launch-start').split(':').map(Number);
                    this.quickStartSessionAndPlay(campaignId, sessionId);
                });
            });
            content.querySelectorAll('[data-play-launch-new-session]').forEach((node) => {
                node.addEventListener('click', () => {
                    const campaignId = Number(node.getAttribute('data-play-launch-new-session'));
                    this.quickCreateSessionAndPlay(campaignId);
                });
            });
            content.querySelectorAll('[data-play-launch-goto]').forEach((node) => {
                node.addEventListener('click', () => {
                    this.closePlayLaunch();
                    window.location.href = node.getAttribute('data-play-launch-goto');
                });
            });
        },

        openPlayFromLaunch(campaignId, sessionId, seat = null) {
            this.closePlayLaunch();
            this.enterPlay({ campaignId, sessionId, sourceRoute: this.currentView || this.currentPage || 'dashboard', seat });
        },

        async quickStartSessionAndPlay(campaignId, sessionId) {
            this.setPlayLaunchStatus('Session wird gestartet...');
            try {
                await window.Auth.makeAuthRequest(`/api/sessions/${sessionId}/start`, 'POST');
                this.openPlayFromLaunch(campaignId, sessionId, 'dm');
            } catch (error) {
                this.setPlayLaunchStatus(error.message || 'Session konnte nicht gestartet werden.', true);
            }
        },

        async quickCreateSessionAndPlay(campaignId) {
            this.setPlayLaunchStatus('Schritt 1/2: Session wird erstellt...');
            try {
                const session = await window.Auth.makeAuthRequest(`/api/campaigns/${campaignId}/sessions`, 'POST', {
                    name: 'Session ' + new Date().toLocaleDateString('de-DE'),
                });
                this.setPlayLaunchStatus('Schritt 2/2: Session wird gestartet...');
                await window.Auth.makeAuthRequest(`/api/sessions/${session.id}/start`, 'POST');
                this.openPlayFromLaunch(campaignId, session.id, 'dm');
            } catch (error) {
                this.setPlayLaunchStatus(error.message || 'Session konnte nicht erstellt werden.', true);
            }
        },

        async quickCreateCampaignAndPlay() {
            const nameField = document.getElementById('playLaunchNewCampaignName');
            const button = document.getElementById('playLaunchQuickCreateBtn');
            const name = (nameField?.value || '').trim() || 'Meine erste Kampagne';

            if (button) {
                button.disabled = true;
            }

            try {
                this.setPlayLaunchStatus('Schritt 1/3: Kampagne wird erstellt...');
                const campaign = await window.Auth.makeAuthRequest('/api/campaigns', 'POST', { name });

                this.setPlayLaunchStatus('Schritt 2/3: Erste Session wird erstellt...');
                const session = await window.Auth.makeAuthRequest(`/api/campaigns/${campaign.id}/sessions`, 'POST', {
                    name: 'Session 1',
                });

                this.setPlayLaunchStatus('Schritt 3/3: Session wird gestartet...');
                await window.Auth.makeAuthRequest(`/api/sessions/${session.id}/start`, 'POST');

                this.openPlayFromLaunch(campaign.id, session.id);
            } catch (error) {
                this.setPlayLaunchStatus(error.message || 'Schnellstart fehlgeschlagen.', true);
                if (button) {
                    button.disabled = false;
                }
            }
        },

        async runCharacterAction(node) {
            const id = Number(node.dataset.characterId);
            const action = node.dataset.characterAction;
            const name = node.dataset.characterName || 'Held';
            if (action === 'delete' && !window.confirm(`„${name}“ endgültig löschen? Das kann nicht rückgängig gemacht werden.`)) {
                return;
            }
            node.disabled = true;
            const messages = {
                duplicate: 'Kopie angelegt.',
                archive: 'Held archiviert.',
                restore: 'Held wiederhergestellt.',
                delete: 'Held gelöscht.',
            };
            try {
                if (action === 'duplicate') {
                    await window.Auth.makeAuthRequest(`/api/srd-creator/characters/${id}/duplicate`, 'POST');
                } else if (action === 'archive' || action === 'restore') {
                    await window.Auth.makeAuthRequest(`/api/srd-creator/characters/${id}/archive`, 'POST', { archived: action === 'archive' });
                } else if (action === 'delete') {
                    await window.Auth.makeAuthRequest(`/api/characters/${id}`, 'DELETE');
                } else {
                    return;
                }
                const snapshot = await this.loadSceneSnapshot(this.sceneUser);
                this.sceneSnapshot = snapshot;
                this.renderSceneRoute('characters', this.sceneUser, snapshot);
                const message = this.sceneSurface.querySelector('#charactersMessageBox');
                if (message) {
                    message.hidden = false;
                    message.textContent = messages[action];
                }
            } catch (error) {
                node.disabled = false;
                const box = this.sceneSurface.querySelector('#charactersMessageBox');
                if (box) {
                    box.hidden = false;
                    box.textContent = error.message === 'in_campaign'
                        ? 'Nimm den Charakter zuerst aus der Kampagne, bevor du ihn archivierst.'
                        : (error.message || 'Aktion fehlgeschlagen.');
                }
            }
        },

        async loadSceneSnapshot(user = null) {
            const resolvedUser = user || this.sceneUser || await (window.Auth ? window.Auth.getCurrentUser() : null);
            const snapshot = {
                user: resolvedUser || null,
                campaigns: [],
                characters: [],
                shared_characters: [],
                archived_characters: [],
                drafts: [],
            };

            if (!window.Auth || typeof window.Auth.makeAuthRequest !== 'function') {
                return snapshot;
            }

            const [campaignsResult, charactersResult, sharedResult, archivedResult, draftsResult] = await Promise.allSettled([
                window.Auth.makeAuthRequest('/api/campaigns'),
                window.Auth.makeAuthRequest('/api/characters/mine'),
                window.Auth.makeAuthRequest('/api/characters/shared'),
                window.Auth.makeAuthRequest('/api/characters/mine?archived=only'),
                window.Auth.makeAuthRequest('/api/srd-creator/drafts'),
            ]);

            if (archivedResult.status === 'fulfilled' && Array.isArray(archivedResult.value)) {
                snapshot.archived_characters = archivedResult.value;
            }
            if (draftsResult.status === 'fulfilled' && Array.isArray(draftsResult.value?.drafts)) {
                snapshot.drafts = draftsResult.value.drafts;
            }

            if (campaignsResult.status === 'fulfilled' && Array.isArray(campaignsResult.value)) {
                snapshot.campaigns = campaignsResult.value;
            }

            if (charactersResult.status === 'fulfilled' && Array.isArray(charactersResult.value)) {
                snapshot.characters = charactersResult.value;
            }
            if (sharedResult.status === 'fulfilled' && Array.isArray(sharedResult.value)) {
                snapshot.shared_characters = sharedResult.value;
            } else {
                snapshot.shared_characters_error = true;
            }

            return snapshot;
        },

        async loadDashboardSnapshot(user = null) {
            if (!window.Auth || typeof window.Auth.makeAuthRequest !== 'function') {
                return this.loadSceneSnapshot(user);
            }

            try {
                const snapshot = await window.Auth.makeAuthRequest('/api/dashboard/home');
                if (snapshot && typeof snapshot === 'object') {
                    return snapshot;
                }
            } catch (error) {
                console.warn('Failed to load dashboard home snapshot, falling back to base scene snapshot.', error);
            }

            return this.loadSceneSnapshot(user);
        },

        renderSceneRoute(routeKey, user = null, snapshot = null) {
            if (!this.sceneSurface) {
                return;
            }
            this.sceneRenderVersion = (this.sceneRenderVersion || 0) + 1;

            // content() reads this.currentView to pick the right page's
            // content map - set it here since this is the one place every
            // render path (instant or animated) funnels through.
            this.currentView = routeKey;

            if (user) {
                this.sceneUser = user;
            }
            if (snapshot) {
                this.sceneSnapshot = snapshot;
            }
            if (!this.sceneSnapshot) {
                this.sceneSnapshot = { user: this.sceneUser || null, campaigns: [], characters: [] };
            }
            if (!this.sceneUser && this.sceneSnapshot.user) {
                this.sceneUser = this.sceneSnapshot.user;
            }

            this.sceneSurface.dataset.bookRoute = routeKey;
            const externalTemplateId = this.getExternalTemplateId(routeKey);
            if (externalTemplateId) {
                const template = document.getElementById(externalTemplateId);
                this.sceneSurface.innerHTML = template ? template.innerHTML : '';
            } else {
                this.sceneSurface.innerHTML = this.buildRouteMarkup(routeKey, this.sceneUser, this.sceneSnapshot);
            }
            this.sceneBuiltRoute = routeKey;
            this.bindSceneNavigation();
            this.runRouteInitializer(routeKey);
        },

        ensureDashboardScene(user = null, snapshot = null) {
            this.renderSceneRoute('dashboard', user, snapshot);
        },

        hideLoginContent() {
            if (!this.loginContent) {
                return;
            }

            this.loginContent.classList.remove('visible');
            this.loginContent.style.opacity = '0';
            this.loginContent.style.pointerEvents = 'none';
            this.loginContent.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('book-login-open');
            this.resetLoginBookHeight();
            [this.loginSpread, this.loginLeftPage, this.loginRightPage].forEach((node) => {
                if (!node) {
                    return;
                }
                node.style.removeProperty('transform');
                node.style.removeProperty('opacity');
                node.style.removeProperty('filter');
            });
        },

        open() {
            if (this.isOpened) {
                return;
            }

            this.isOpened = true;
            this.applyOpenedBookState();
            if (this.currentPage !== 'login') {
                this.hideLoginContent();
                this.setSceneState('dashboard');
                return;
            }

            if (this.loginContent) {
                this.loginContent.classList.add('visible');
                this.loginContent.style.opacity = '1';
                this.loginContent.style.pointerEvents = 'auto';
                this.loginContent.removeAttribute('aria-hidden');
            }
            document.body.classList.add('book-login-open');
            this.syncLoginBookHeight();
            this.setSceneState('login');
        },

        applyOpenedBookState() {
            if (this.book) {
                this.book.style.transform = 'rotateY(0deg) scale(1)';
            }
            if (this.bookCover) {
                this.bookCover.style.transform = 'rotateY(-160deg)';
            }
            if (this.bookPages) {
                this.bookPages.style.transform = 'translateX(4px) rotateY(0deg) scaleX(1) scaleY(1)';
            }
            if (this.bookBack) {
                this.bookBack.style.opacity = '1';
            }

            if (this.bookCover) {
                this.bookCover.classList.add('is-open');
            }
        },

        showSceneInstant(routeKey, user = null, snapshot = null) {
            this.renderSceneRoute(routeKey, user, snapshot);
            this.hideLoginContent();
            this.hideTurnLeaf();
            delete document.body.dataset.bookSceneTransitionTarget;
            document.body.dataset.bookSceneTransitionPhase = 'BOOK_MODE';

            if (this.sceneSurface) {
                this.sceneSurface.hidden = false;
                this.sceneSurface.setAttribute('aria-hidden', 'false');
                this.sceneSurface.classList.add('is-visible');
                const camera = this.sceneSurface.querySelector('.book-dashboard-camera');
                if (camera) {
                    camera.style.transform = 'none';
                    camera.style.opacity = '1';
                }
            }

            this.applyOpenedBookState();
            this.isOpened = true;
            this.currentView = routeKey;
            this.currentPage = routeKey;
            this.setSceneState('dashboard');
            document.body.dataset.bookSceneRoute = routeKey;
            this.updateBookmarkPosition(routePathForKey(routeKey));
            window.history.replaceState({ book_scene: routeKey }, '', historyHrefForRoute(routeKey));
        },

        showDashboardInstant(user = null) {
            this.showSceneInstant('dashboard', user, this.sceneSnapshot);
        },

        bootstrapRoute(routeKey, user = null) {
            this.currentView = routeKey;
            this.currentPage = routeKey;
            this.isOpened = true;
            this.showSceneInstant(routeKey, user, this.sceneSnapshot);
        },

        bootstrapDashboardRoute(user = null) {
            this.bootstrapRoute('dashboard', user);
        },

        // First paint of a protected route: the open book with the route's
        // ribbon and an empty spread. A full-screen loading curtain and the
        // closed cover used to flash on every tab switch (owner, 2026-11-08).
        showLoadingShell(routeKey) {
            if (!this.sceneSurface) {
                return;
            }
            this.currentView = routeKey;
            this.sceneSurface.dataset.bookRoute = routeKey;
            this.sceneSurface.innerHTML = this.buildPageShell(routeKey, null, {
                loading: true,
                showRunningHead: false,
                showRightHeader: false,
                folio: this.getRouteMeta(routeKey).folio,
                title: this.getSpreadTitle(routeKey),
                leftPage: '<p class="book-scene-loading">Wird geladen …</p>',
            });
            this.sceneBuiltRoute = null;
            this.sceneSurface.hidden = false;
            this.sceneSurface.setAttribute('aria-hidden', 'false');
            this.sceneSurface.classList.add('is-visible');
            this.setSceneState('dashboard');
        },

        async bootstrapProtectedRoute(config = {}) {
            const {
                routeKey,
                auth,
                statusElementId = null,
                statusMessage = null,
                loginPath = '/login.html',
                snapshotLoader = null,
            } = config;

            const statusNode = statusElementId ? document.getElementById(statusElementId) : null;
            const setStatus = (message) => {
                if (!statusNode) {
                    return;
                }
                if (!message) {
                    statusNode.hidden = true;
                    return;
                }
                statusNode.hidden = false;
                statusNode.textContent = message;
            };

            // The status line only appears when loading is noticeably slow.
            const slowTimer = window.setTimeout(() => {
                setStatus(statusMessage || `${this.getSpreadTitle(routeKey)} wird geladen …`);
            }, 900);

            try {
                if (!auth || typeof auth.requireAuth !== 'function') {
                    throw new Error('Auth client unavailable');
                }

                this.create();
                this.showLoadingShell(routeKey);

                // Page texts are public, so they load alongside the auth check.
                const [user] = await Promise.all([
                    auth.requireAuth(loginPath),
                    this.loadPageContent(routeKey),
                ]);
                if (!user) {
                    return false;
                }

                this.consumeBookEntryBoundary(routeKey);
                const resolvedSnapshot = snapshotLoader
                    ? await snapshotLoader(user)
                    : await this.loadSceneSnapshot(user);

                this.sceneSnapshot = resolvedSnapshot || { user };
                this.sceneUser = this.sceneSnapshot.user || user;
                this.bootstrapRoute(routeKey, user);
                return true;
            } catch (error) {
                console.error(`Failed to bootstrap ${routeKey} scene:`, error);
                window.location.href = loginPath;
                return false;
            } finally {
                window.clearTimeout(slowTimer);
                setStatus('');
            }
        },

        consumeBookEntryBoundary(routeKey) {
            document.body.dataset.bookSceneEntryBoundary = 'direct';
            document.body.dataset.bookSceneEntryPhase = 'BOOK_MODE';
            delete document.body.dataset.bookSceneEntrySourceMode;
            delete document.body.dataset.bookSceneEntrySourceRoute;
            delete document.body.dataset.bookSceneEntryTargetRoute;
            delete document.body.dataset.bookSceneTransitionTarget;
            document.body.dataset.bookSceneTransitionPhase = 'BOOK_MODE';
            // Coming back from the table is a plain tab switch: drop the
            // handoff record and render the book directly, without the old
            // blur/scale arrival (owner, 2026-11-08).
            clearBookReturnBoundary();
        },

        _runPlayExitTransition(handoff) {
            const navigateToPlay = () => {
                handoff.phase = 'play-route-entry';
                handoff.book_exit_completed_at = new Date().toISOString();
                persistPlayHandoff(handoff);
                window.location.href = handoff.target_href;
            };

            this.transitionInFlight = true;
            // Cross-document navigation cannot use a same-document View
            // Transition. Persist the boundary and leave immediately so no
            // animation curtain can block the play surface or input focus.
            navigateToPlay();
            return true;
        },

        enterPlay(config = {}) {
            const {
                campaignId,
                sessionId,
                sourceRoute = this.currentView || this.currentPage || 'campaigns',
                seat = null,
            } = config;

            const resolvedCampaignId = Number(campaignId);
            const resolvedSessionId = Number(sessionId);
            if (!Number.isInteger(resolvedCampaignId) || resolvedCampaignId <= 0) {
                throw new Error('campaignId is required for play handoff');
            }
            if (!Number.isInteger(resolvedSessionId) || resolvedSessionId <= 0) {
                throw new Error('sessionId is required for play handoff');
            }

            const targetHref = buildPlayHref(resolvedCampaignId, resolvedSessionId, seat);
            const handoff = {
                kind: 'book-to-table',
                from_mode: 'BOOK_MODE',
                transition_mode: 'BOOK_TO_TABLE_TRANSITION',
                target_mode: 'TABLE_MODE',
                source_route: sourceRoute,
                source_href: historyHrefForRoute(sourceRoute),
                target_href: targetHref,
                phase: 'book-exit',
                exit_duration_ms: PLAY_EXIT_DURATION_MS,
                arrival_duration_ms: PLAY_ARRIVAL_DURATION_MS,
                target: {
                    family: 'play',
                    campaign_id: resolvedCampaignId,
                    session_id: resolvedSessionId,
                },
                started_at: new Date().toISOString(),
            };

            persistPlayHandoff(handoff);
            return this._runPlayExitTransition(handoff);
        },

        async transitionToRoute(routeKey, user = null, options = {}) {
            if (this.transitionInFlight) {
                return;
            }

            this.transitionInFlight = true;

            try {
                const snapshot = await this.loadSceneSnapshot(user);
                this.sceneSnapshot = snapshot;
                this.sceneUser = snapshot.user || user || this.sceneUser;
                await this.loadPageContent(routeKey);

                const render = () => {
                    this.setSceneState('transition');
                    this.renderSceneRoute(routeKey, this.sceneUser, snapshot);
                    this.hideLoginContent();
                    this.hideTurnLeaf();
                    if (this.sceneSurface) {
                        this.sceneSurface.hidden = false;
                        this.sceneSurface.setAttribute('aria-hidden', 'false');
                        this.sceneSurface.classList.add('is-visible');
                        const camera = this.sceneSurface.querySelector('.book-dashboard-camera');
                        if (camera) {
                            camera.style.opacity = '1';
                            camera.style.transform = 'none';
                            camera.style.filter = 'none';
                        }
                    }
                    this.currentView = routeKey;
                    this.currentPage = routeKey;
                    this.applyOpenedBookState();
                    this.setSceneState('dashboard');
                    document.body.dataset.bookSceneRoute = routeKey;
                    this.updateBookmarkPosition(routePathForKey(routeKey));
                    window.history.replaceState({ book_scene: routeKey }, '', historyHrefForRoute(routeKey));
                };

                // Tabs switch instantly: no crossfade between routes
                // (owner, 2026-11-08).
                render();
            } finally {
                this.transitionInFlight = false;
            }
        },

        async transitionToDashboard(user = null, options = {}) {
            return this.transitionToRoute('dashboard', user, options);
        },

        async goToSpread(index, user = null, options = {}) {
            const routeKey = routeOrder[index] || routeOrder[routeOrder.length - 1] || 'dashboard';
            return this.transitionToRoute(routeKey, user, options);
        },

        async flipToNextPage(user = null, options = {}) {
            const currentIndex = Math.max(routeOrder.indexOf(this.currentView || this.currentPage || 'login'), 0);
            const nextIndex = Math.min(currentIndex + 1, routeOrder.length - 1);
            return this.goToSpread(nextIndex, user, options);
        },

        pageTurn(url, user = null) {
            const target = normalizePath(url);
            const routeKey = routeKeyForPath(target);
            const destination = new URL(url, window.location.origin);
            const templateId = this.getExternalTemplateId(routeKey);
            // Query-driven forms and sheets need their document's handlers.
            // Rendering a missing external template used to leave a blank page.
            if (destination.searchParams.has('intent') || destination.searchParams.has('workspace')
                    || (templateId && !document.getElementById(templateId))
                    || routeKey === 'character-sheet') {
                window.location.href = `${destination.pathname}${destination.search}`;
                return;
            }
            const campaignId = Number(destination.searchParams.get('campaign_id'));
            if (routeKey === 'campaigns' && Number.isInteger(campaignId) && campaignId > 0) {
                return this.renderCampaignHubDetail(campaignId);
            }
            if (routeKey === 'login') {
                window.location.href = routeHref(target);
                return;
            }

            return this.transitionToRoute(routeKey, user);
        },

        updateCurrentPage() {
            const path = normalizePath(window.location.pathname);
            this.currentPage = routeKeyForPath(path);
            document.body.dataset.bookSceneRoute = this.currentPage;
            this.updateBookmarkPosition(path);
        },

        updateBookmarkPosition(url = null) {
            const bookmark = document.querySelector('.bookmark');
            if (!bookmark) {
                return;
            }

            const targetPage = routeKeyForPath(url || this.currentPage);
            bookmark.classList.remove('login', 'signup', 'register', 'dashboard', 'campaigns', 'characters', 'character-sheet');
            bookmark.classList.add(targetPage);
        },

        addPageNumbers(pageNumber) {
            const existing = document.querySelector('.page-number');
            if (existing) {
                existing.textContent = pageNumber;
                return;
            }

            const pageNumEl = document.createElement('div');
            pageNumEl.className = 'page-number';
            pageNumEl.textContent = pageNumber;
            pageNumEl.setAttribute('aria-hidden', 'true');

            const main = document.querySelector('main') || document.body;
            main.appendChild(pageNumEl);
        },
    };

    window.BookScene.updateCurrentPage();

    // A cached document retains enterPlay's transition lock and hidden book.
    // Rebuild it on restoration, including fresh auth and campaign state.
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) window.location.reload();
    });
}());
