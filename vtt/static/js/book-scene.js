/**
 * BookScene v2
 * Persistent spellbook scene for login, auth chapters, dashboard, campaigns,
 * characters, and the character-sheet focus route.
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
    const BOOK_RETURN_ARRIVAL_DURATION_MS = 680;

    function buildPlayHref(campaignId, sessionId) {
        const params = new URLSearchParams({
            campaign_id: String(campaignId),
            session_id: String(sessionId),
        });
        return `/play?${params.toString()}`;
    }

    function persistPlayHandoff(handoff) {
        try {
            window.sessionStorage.setItem(PLAY_ENTRY_STORAGE_KEY, JSON.stringify(handoff));
        } catch (error) {
            console.warn('Failed to persist play handoff context:', error);
        }
    }

    function readBookReturnBoundary() {
        try {
            return window.sessionStorage.getItem(BOOK_RETURN_STORAGE_KEY);
        } catch (error) {
            console.warn('Failed to read book return boundary context:', error);
            return null;
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
        bookEntryArrivalTimer: null,
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
            if (document.getElementById('book-scene-wrapper')) {
                this.syncMotionPreference();
                return;
            }

            const bookHTML = `
                <div id="book-scene-wrapper" class="book-scene-wrapper" role="region" aria-label="Spellbook application interface">
                    <div class="book-scene-backdrop" aria-hidden="true"></div>
                    <div class="book-scene-stage">
                        <div id="book" class="book-scene-book" role="doc-cover" aria-label="Interactive spellbook">
                            <div class="book-element book-cover" role="button" tabindex="0" aria-label="Book front cover - press Enter or click to open" aria-pressed="false">
                                <div class="cover-title" aria-hidden="false">Spellbook</div>
                                <div class="cover-ornament" aria-hidden="true">✨</div>
                            </div>
                            <div class="book-element book-pages" role="doc-pagebreak" aria-label="Book pages"></div>
                            <div class="book-element book-back" role="doc-cover" aria-label="Book back cover"></div>
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

            document.body.insertAdjacentHTML('afterbegin', bookHTML);

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
            this.coverTitle = document.querySelector('.book-cover .cover-title');
            this.coverOrnament = document.querySelector('.book-cover .cover-ornament');
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

            this.syncMotionPreference();
            if (reducedMotion.addEventListener) {
                reducedMotion.addEventListener('change', () => this.syncMotionPreference());
            }

            document.addEventListener('click', (event) => {
                if (event.target.closest('.book-cover') && !this.isOpened) {
                    this.open();
                }
            });

            document.addEventListener('keydown', (event) => {
                const cover = event.target && typeof event.target.closest === 'function'
                    ? event.target.closest('.book-cover')
                    : null;
                if (cover && !this.isOpened && (event.key === 'Enter' || event.key === ' ')) {
                    event.preventDefault();
                    this.open();
                }
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
            if (routeKey === 'login') return 'Welcome, Reader';
            if (routeKey === 'signup') return 'Sign Up';
            if (routeKey === 'register') return 'Register';
            if (routeKey === 'dashboard') return 'Übersicht';
            if (routeKey === 'campaigns') return 'Kampagnen';
            if (routeKey === 'characters') return 'Charaktere';
            if (routeKey === 'character-sheet') return 'Character Sheet';
            return 'Spellbook';
        },

        getSpreadCopy(routeKey, side = 'front') {
            if (routeKey === 'login' && side === 'front') {
                return 'The archive opens on a calm title leaf before the first real chapter turns into view.';
            }
            if (routeKey === 'signup') {
                return side === 'back'
                    ? 'The sign-up chapter keeps the reader inside the same spellbook while the account ritual stays readable and calm.'
                    : 'The next folio introduces the key-gated sign-up ritual without leaving the bound object.';
            }
            if (routeKey === 'register') {
                return side === 'back'
                    ? 'The key redemption page waits under the current leaf so the first authenticated chapter can rise straight from the same book.'
                    : 'The invitation chapter continues the onboarding ritual on the same parchment spread.';
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
                    : 'Charaktere ist der Ort für Heldenanlage, Identität und den Rueckweg in die Session-Vorbereitung.';
            }
            if (routeKey === 'character-sheet') {
                return side === 'back'
                    ? 'The focused character sheet settles into the same spellbook, only zoomed deeper into a single hero.'
                    : 'The focus sheet waits as the next in-book zoom step rather than a detached utility screen.';
            }
            return 'The next folio keeps the reader inside the same book.';
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

            if (typeof gsap !== 'undefined') {
                gsap.set(this.turnLeaf, { opacity: 1, x: 0 });
                gsap.set(this.turnSheet, {
                    rotationY: 0,
                    transformOrigin: 'left center',
                });
                if (this.turnShadow) {
                    gsap.set(this.turnShadow, { opacity: 0 });
                }
            }
        },

        hideTurnLeaf() {
            if (!this.turnLeaf) {
                return;
            }

            this.turnLeaf.classList.remove('is-visible');
            this.turnLeaf.setAttribute('aria-hidden', 'true');
            this.turnLeaf.hidden = true;

            if (typeof gsap !== 'undefined') {
                gsap.set([this.turnLeaf, this.turnSheet, this.turnShadow], {
                    clearProps: 'transform,opacity',
                });
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
                + `<button type="button" class="book-dashboard-ribbon-btn book-dashboard-ribbon-btn--play" data-dashboard-action="play-launch">${escapeHtml(this.content('ribbon.play_button', '▶ Spieltisch'))}</button>`
                + `<button type="button" class="book-dashboard-ribbon-btn" data-dashboard-action="logout">${escapeHtml(this.content('ribbon.logout_button', 'Abmelden'))}</button>`;
        },

        buildCampaignPreview(campaigns) {
            if (!Array.isArray(campaigns) || campaigns.length === 0) {
                return `
                    <div class="book-dashboard-preview-empty">
                        Noch keine Kampagnen. Erstelle das erste Kapitel in den Chronicles.
                    </div>
                `;
            }

            return `
                <div class="book-dashboard-preview-list">
                    ${campaigns.slice(0, 3).map((campaign) => `
                        <div class="book-dashboard-preview-item">
                            <span class="book-dashboard-preview-name">${escapeHtml(campaign.name || 'Unbenannte Kampagne')}</span>
                            <span class="book-dashboard-preview-meta">${escapeHtml(campaign.status || 'active')} · ${Number(campaign.member_count || 0)} Mitglieder</span>
                        </div>
                    `).join('')}
                </div>
            `;
        },

        buildCharacterPreview(characters) {
            if (!Array.isArray(characters) || characters.length === 0) {
                return `
                    <div class="book-dashboard-preview-empty">
                        Noch keine Charaktere. Öffne das Personae-Archiv und lege den ersten Helden an.
                    </div>
                `;
            }

            return `
                <div class="book-dashboard-preview-list">
                    ${characters.slice(0, 3).map((character) => `
                        <div class="book-dashboard-preview-item">
                            <span class="book-dashboard-preview-name">${escapeHtml(character.name || 'Unbekannt')}</span>
                            <span class="book-dashboard-preview-meta">Lvl ${Number(character.level || 1)} ${escapeHtml(character.class || 'Abenteurer')} · ${escapeHtml(character.race || 'Volk offen')}</span>
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
                        const directHref = action.href ? ` data-dashboard-href="${escapeHtml(action.href)}"` : '';
                        const sceneRoute = action.route ? ` data-dashboard-route="${escapeHtml(action.route)}"` : '';
                        const sectionTarget = action.section ? ` data-dashboard-section="${escapeHtml(action.section)}"` : '';
                        const disabled = action.disabled ? ' disabled' : '';
                        return `<button type="button" class="btn ${isPrimary ? 'btn-primary' : 'btn-secondary'} book-scene-action-btn"${directHref}${sceneRoute}${sectionTarget}${disabled}>${escapeHtml(action.label || 'Weiter')}</button>`;
                    }).join('')}
                </div>
            `;
        },

        buildCampaignLedger(campaigns) {
            if (!Array.isArray(campaigns) || campaigns.length === 0) {
                return `
                    <div class="book-scene-ledger-item is-empty">
                        <div>Noch keine Kampagne angelegt. Starte hier mit deinem ersten Hub für Einladungen, Session-Prep und den späteren Weg nach Play.</div>
                        ${this.buildActionButtons([
                            {
                                label: 'Erste Kampagne anlegen',
                                href: buildIntentHref('/campaigns', { classic: 1, intent: 'create' }),
                                primary: true,
                            },
                        ], 'book-scene-action-row--inline')}
                    </div>
                `;
            }

            return `
                <div class="book-scene-ledger">
                    ${campaigns.slice(0, 6).map((campaign) => `
                        <div class="book-scene-ledger-item">
                            <div class="book-scene-ledger-head">
                                <strong>${escapeHtml(campaign.name || 'Unbenannte Kampagne')}</strong>
                                <span>${escapeHtml(campaign.status || 'active')}</span>
                            </div>
                            <div class="book-scene-ledger-meta">${Number(campaign.member_count || 0)} Mitglieder · ${campaign.is_owner ? 'Eigene Kampagne' : 'Geteiltes Kapitel'}</div>
                            <div class="book-scene-ledger-copy">${escapeHtml(campaign.description || 'Bereit für Session-Prep, direkte Charakterzuweisung, Karten und Assets vor dem Tisch.')}</div>
                            ${this.buildActionButtons([
                                {
                                    label: Number(campaign.session_count || 0) > 0 ? 'Hub & Session-Prep' : 'Hub öffnen',
                                    href: buildIntentHref('/campaigns', { campaign_id: campaign.id, classic: 1 }),
                                    primary: true,
                                },
                            ], 'book-scene-action-row--inline')}
                        </div>
                    `).join('')}
                </div>
            `;
        },

        buildCharacterLedger(characters) {
            if (!Array.isArray(characters) || characters.length === 0) {
                return `
                    <div class="book-scene-ledger-item is-empty">
                        <div>Noch kein Held im Archiv. Lege hier den ersten Charakter an und führe ihn danach über Bogen und Kampagnenkontext in die Session-Vorbereitung.</div>
                        ${this.buildActionButtons([
                            {
                                label: 'Held anlegen',
                                href: buildIntentHref('/characters', { classic: 1, intent: 'create' }),
                                primary: true,
                            },
                        ], 'book-scene-action-row--inline')}
                    </div>
                `;
            }

            return `
                <div class="book-scene-ledger">
                    ${characters.slice(0, 6).map((character) => `
                        <div class="book-scene-ledger-item">
                            <div class="book-scene-ledger-head">
                                <strong>${escapeHtml(character.name || 'Unbekannt')}</strong>
                                <span>Lvl ${Number(character.level || 1)}</span>
                            </div>
                            <div class="book-scene-ledger-meta">${escapeHtml(character.class || 'Abenteurer')} · ${escapeHtml(character.race || 'Volk offen')}</div>
                            <div class="book-scene-ledger-copy">${escapeHtml(character.background || 'Bereit für Bogen, Identität und die spätere Zuweisung in eine Session.')}</div>
                            ${this.buildActionButtons([
                                {
                                    label: 'Bogen öffnen',
                                    href: buildIntentHref('/character-sheet', { id: character.id }),
                                    primary: true,
                                },
                                character.campaign_id
                                    ? {
                                        label: 'Kampagnen-Kontext',
                                        href: buildIntentHref('/campaigns', { campaign_id: character.campaign_id, classic: 1 }),
                                    }
                                    : {
                                        label: 'Kampagnen öffnen',
                                        href: buildIntentHref('/campaigns', { classic: 1 }),
                                    },
                            ], 'book-scene-action-row--inline')}
                        </div>
                    `).join('')}
                </div>
            `;
        },

        buildDashboardHero(snapshot = null) {
            const homeState = snapshot?.home_state || {};
            const primaryAction = snapshot?.primary_action || {
                label: 'Kampagnen öffnen',
                href: '/campaigns?classic=1',
            };
            const secondaryAction = snapshot?.secondary_action || {
                label: 'Charaktere öffnen',
                href: '/characters?classic=1',
            };
            const primaryGuild = snapshot?.primary_guild || null;
            const socialScopeNote = snapshot?.social_scope?.note
                || this.content('home.social_scope_default', 'Dashboard-Social bleibt vom Session-Chat getrennt.');

            // B2 (Designbrief §5): Die Startseite ist das Inhaltsverzeichnis
            // des Buches -- Lesebändchen zuerst (weiterlesen, wo du warst),
            // dann die Kapitelliste mit echten Zahlen. Keine Prosa mehr, die
            // die App beschreibt.
            const tocRows = [
                { numeral: 'II', label: this.content('home.nav_campaigns', 'Kampagnen'),
                  count: Number(homeState.campaign_count || 0), href: '/campaigns' },
                { numeral: 'III', label: this.content('home.nav_characters', 'Charaktere'),
                  count: Number(homeState.character_count || 0), href: '/characters' },
                { numeral: 'IV', label: this.content('home.nav_play', 'Spieltisch'),
                  count: Number(homeState.session_count || 0), href: null,
                  action: 'play-launch',
                  countLabel: this.content('home.toc_sessions', '{count} Sessions',
                                           { count: Number(homeState.session_count || 0) }) },
            ];
            return `
                <section class="book-home-hero book-ribbon-card" data-dashboard-section-target="social">
                    <div class="book-ribbon-marker" aria-hidden="true"></div>
                    <div class="book-home-hero-kicker">${escapeHtml(this.content('home.hero_kicker', 'Lesebändchen'))}</div>
                    <h2 class="book-home-hero-title">${escapeHtml(this.content('home.hero_title', 'Weiterlesen'))}</h2>
                    ${homeState.summary ? `<p class="book-home-hero-copy">${escapeHtml(homeState.summary)}</p>` : ''}
                    ${this.buildActionButtons([
                        {
                            label: primaryAction.label || 'Weiter',
                            href: primaryAction.href || '/campaigns?classic=1',
                            primary: true,
                        },
                        {
                            label: secondaryAction.label || 'Charaktere öffnen',
                            href: secondaryAction.href || '/characters?classic=1',
                        },
                    ], 'book-scene-action-row--inline')}
                    <div class="book-home-hero-note">
                        <strong>${escapeHtml(this.content('home.social_scope_label', 'Sichtbarkeit:'))}</strong> ${escapeHtml(socialScopeNote)}
                    </div>
                    ${this.dashboardNotice ? `<div class="book-home-hero-notice">${escapeHtml(this.dashboardNotice)}</div>` : ''}
                </section>
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
                </nav>
            `;
        },

        buildDashboardNavigationRail() {
            const items = [
                { section: 'social', label: this.content('home.nav_social', 'Social') },
                { section: 'guilds', label: this.content('home.nav_guilds', 'Guilds') },
                { section: 'campaigns', label: this.content('home.nav_campaigns', 'Kampagnen') },
                { section: 'characters', label: this.content('home.nav_characters', 'Charaktere') },
                { section: 'session-prep', label: this.content('home.nav_session_prep', 'Session Prep') },
                { section: 'play', label: this.content('home.nav_play', 'Spieltisch') },
            ];

            return `
                <nav class="book-home-rail" aria-label="Dashboard home sections">
                    ${items.map((item) => `
                        <button type="button" class="book-home-rail-link" data-dashboard-section="${escapeHtml(item.section)}">
                            ${escapeHtml(item.label)}
                        </button>
                    `).join('')}
                </nav>
            `;
        },

        buildDashboardGuildPanel(snapshot = null) {
            const guilds = Array.isArray(snapshot?.guilds) ? snapshot.guilds : [];
            const primaryGuild = snapshot?.primary_guild || null;

            if (guilds.length === 0) {
                return `
                    <section class="book-home-guild-panel" data-dashboard-section-target="guilds">
                        <div class="book-home-section-kicker">${escapeHtml(this.content('home.guild_panel_empty_kicker', 'Guilds'))}</div>
                        <h3 class="book-home-section-title">${escapeHtml(this.content('home.guild_panel_empty_title', 'Meta-Banner'))}</h3>
                        <p class="book-home-section-copy">${escapeHtml(this.content('home.guild_panel_empty_copy', 'Die Guild-Ebene wird vorbereitet.'))}</p>
                    </section>
                `;
            }

            const memberCountBadge = (count) => this.content('home.guild_badge_member_count', '{count} Mitglieder', { count: Number(count || 0) });

            return `
                <section class="book-home-guild-panel" data-dashboard-section-target="guilds">
                    <div class="book-home-section-kicker">${escapeHtml(this.content('home.guild_panel_kicker', 'Guilds'))}</div>
                    <h3 class="book-home-section-title">${escapeHtml(this.content('home.guild_panel_title', 'Dein Banner im Buch'))}</h3>
                    <p class="book-home-section-copy">
                        ${escapeHtml(this.content('home.guild_panel_copy', 'Guilds bleiben reine Meta-Identität. Sie veraendern keine Rollen, keine Berechtigungen und keinen Session-Chat.'))}
                    </p>
                    ${primaryGuild ? `
                        <div class="book-home-guild-primary">
                            <span class="book-home-guild-primary-kicker">${escapeHtml(this.content('home.guild_primary_label', 'Primaere Gilde'))}</span>
                            <strong>${escapeHtml(primaryGuild.name)}</strong>
                            <p>${escapeHtml(primaryGuild.tagline || primaryGuild.description || '')}</p>
                        </div>
                    ` : ''}
                    <div class="book-home-guild-list">
                        ${guilds.map((guild) => `
                            <article class="book-home-guild-card${guild.is_primary ? ' is-primary' : ''}" data-guild-accent="${escapeHtml(guild.accent || 'gold')}">
                                <div class="book-home-guild-card-head">
                                    <div>
                                        <strong>${escapeHtml(guild.name)}</strong>
                                        <span>${escapeHtml(guild.tagline || '')}</span>
                                    </div>
                                    <span class="book-home-guild-badge">${guild.is_primary ? escapeHtml(this.content('home.guild_badge_primary', 'Primaer')) : escapeHtml(memberCountBadge(guild.member_count))}</span>
                                </div>
                                <p>${escapeHtml(guild.status_preview || guild.description || '')}</p>
                                <button
                                    type="button"
                                    class="btn ${guild.is_primary ? 'btn-secondary' : 'btn-primary'} book-scene-action-btn"
                                    data-dashboard-guild-switch="${Number(guild.id)}"
                                    ${guild.is_primary ? 'disabled' : ''}
                                >
                                    ${guild.is_primary ? escapeHtml(this.content('home.guild_button_current', 'Aktuelle Gilde')) : escapeHtml(this.content('home.guild_button_set_primary', 'Als Primaergilde setzen'))}
                                </button>
                            </article>
                        `).join('')}
                    </div>
                </section>
            `;
        },

        buildDashboardFeed(snapshot = null) {
            const feedItems = Array.isArray(snapshot?.feed_preview) ? snapshot.feed_preview : [];

            if (feedItems.length === 0) {
                return `
                    <section class="book-home-feed" data-dashboard-section-target="social">
                        <div class="book-home-feed-item is-empty">
                            <div class="book-home-feed-kicker">${escapeHtml(this.content('home.feed_empty_kicker', 'Chronik'))}</div>
                            <h3 class="book-home-feed-title">${escapeHtml(this.content('home.feed_empty_title', 'Home-Feed wird vorbereitet'))}</h3>
                            <p class="book-home-feed-copy">${escapeHtml(this.content('home.feed_empty_copy', 'Noch keine Home-Eintraege sichtbar. Kampagnen und Charaktere bleiben solange die stabilen Einstiege.'))}</p>
                        </div>
                    </section>
                `;
            }

            return `
                <section class="book-home-feed">
                    ${feedItems.map((item) => `
                        <article class="book-home-feed-item" data-dashboard-section-target="${escapeHtml(item.section || 'social')}">
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

        buildDashboardContext(snapshot = null) {
            const priorities = Array.isArray(snapshot?.priorities) ? snapshot.priorities : [];
            const quickLinks = Array.isArray(snapshot?.quick_links) ? snapshot.quick_links : [];

            return `
                <section class="book-home-context">
                    <div class="book-home-context-grid">
                        <section class="book-home-context-card">
                            <div class="book-home-section-kicker">${escapeHtml(this.content('home.priorities_kicker', 'Heute wichtig'))}</div>
                            <h3 class="book-home-section-title">${escapeHtml(this.content('home.priorities_title', 'Prioritäten'))}</h3>
                            <div class="book-home-priority-list">
                                ${priorities.map((priority) => `
                                    <div class="book-home-priority-card" data-tone="${escapeHtml(priority.tone || 'info')}">
                                        <strong>${escapeHtml(priority.title || 'Hinweis')}</strong>
                                        <p>${escapeHtml(priority.copy || '')}</p>
                                    </div>
                                `).join('')}
                            </div>
                        </section>

                        <section class="book-home-context-card">
                            <div class="book-home-section-kicker">${escapeHtml(this.content('home.quicklinks_kicker', 'Schnellzugriffe'))}</div>
                            <h3 class="book-home-section-title">${escapeHtml(this.content('home.quicklinks_title', 'Wohin du als nächstes gehst'))}</h3>
                            <div class="book-home-quick-links">
                                ${quickLinks.map((link) => `
                                    <button
                                        type="button"
                                        class="btn btn-secondary book-scene-action-btn"
                                        ${link.href ? `data-dashboard-href="${escapeHtml(link.href)}"` : ''}
                                        ${link.section ? `data-dashboard-section="${escapeHtml(link.section)}"` : ''}
                                    >
                                        ${escapeHtml(link.label || 'Öffnen')}
                                    </button>
                                `).join('')}
                            </div>
                            <div class="book-home-context-note">
                                ${escapeHtml(this.content('home.context_note', 'Dashboard bleibt Home und Social Hub. Kampagnen, Session-Prep und Play bleiben die operativen Folgeflächen.'))}
                            </div>
                        </section>
                    </div>
                </section>
            `;
        },

        buildPageShell(routeKey, user, options) {
            const displayName = escapeHtml(user?.username || 'Donut');
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
                            <div class="book-dashboard-ribbon" role="navigation" aria-label="Book page menu">
                                ${this.buildRibbon(routeKey)}
                            </div>
                            <div class="book-dashboard-crest" aria-label="Current reader">${displayName}</div>
                        </div>

                        <div class="book-running-head" aria-hidden="true">
                            <span class="book-running-head-place">${escapeHtml(options.runningHead || leftTitle)}</span>
                            <span class="book-running-head-rule"></span>
                        </div>

                        <div class="book-spread-shell">
                            <article class="book-spread-page book-spread-page--left">
                                <header class="book-spread-page-header">
                                    <p class="book-spread-page-kicker">${leftEyebrow}</p>
                                    <h1 class="book-spread-page-title">${leftTitle}</h1>
                                    <p class="book-spread-page-copy">${leftCopy}</p>
                                </header>
                                <div class="book-spread-page-body">
                                    ${options.leftPage || ''}
                                </div>
                            </article>

                            <div aria-hidden="true"></div>

                            <article class="book-spread-page book-spread-page--right">
                                <header class="book-spread-page-header">
                                    <p class="book-spread-page-kicker">${rightEyebrow}</p>
                                    <h2 class="book-spread-page-title">${rightTitle}</h2>
                                    <p class="book-spread-page-copy">${rightCopy}</p>
                                </header>
                                <div class="book-spread-page-meta">
                                    ${chips.map((chip) => `<span class="book-dashboard-chip">${escapeHtml(chip)}</span>`).join('')}
                                </div>
                                <div class="book-spread-page-body">
                                    ${options.rightPage || ''}
                                </div>
                            </article>
                        </div>

                        <section class="book-spread-footer">
                            ${options.footer || ''}
                        </section>

                        <footer class="book-folio" aria-hidden="true">
                            <span>${escapeHtml((options.folio && options.folio[0]) || '')}</span>
                            <span>${escapeHtml((options.folio && options.folio[1]) || '')}</span>
                        </footer>
                    </section>
                </div>
            `;
        },

        buildDashboardMarkup(user, snapshot = null) {
            const campaigns = snapshot?.campaigns || [];
            const characters = snapshot?.characters || [];
            const homeState = snapshot?.home_state || {};
            const primaryGuild = snapshot?.primary_guild || null;

            const scene = routeMeta.dashboard || {};
            return this.buildPageShell('dashboard', user, {
                runningHead: `${this.content('shell.left_eyebrow', 'Kapitel I')} · ${scene.section || 'Übersicht'}`,
                folio: scene.folio,
                eyebrow: this.content('shell.left_eyebrow', 'Kapitel I'),
                title: this.content('shell.left_title', 'Übersicht'),
                copy: this.content(
                    'shell.left_copy',
                    'Willkommen zurück, {username}. Dieses Kapitel ist jetzt dein soziales Zuhause: Guilds, Chronik-Feed und die klaren Wege weiter in Kampagnen, Charaktere, Session-Prep und den kontrollierten Pfad nach Play.',
                    { username: user?.username || 'Donut' },
                ),
                rightEyebrow: this.content('shell.right_eyebrow', 'Chronik'),
                rightTitle: this.content('shell.right_title', 'Was gerade zählt'),
                rightCopy: this.content('shell.right_copy', 'Der Feed liest sich wie eine laufende Chronik: Social-Hinweise, Guild-Status und die nächsten operativen Schritte bleiben sichtbar getrennt voneinander.'),
                chips: [
                    this.content('shell.chip_home', 'Übersicht / Social'),
                    this.content('shell.chip_campaigns', '{count} Kampagnen', { count: campaigns.length }),
                    this.content('shell.chip_characters', '{count} Charaktere', { count: characters.length }),
                    primaryGuild ? primaryGuild.name : this.content('shell.chip_guild_fallback', 'Guild folgt'),
                    this.content('shell.chip_prep_blockers', '{count} Prep-Blocker', { count: Number(homeState.prep_blocker_count || 0) }),
                ],
                leftPage: `
                    <div class="book-home-stack">
                        ${this.buildDashboardHero(snapshot)}
                        ${this.buildDashboardNavigationRail()}
                        ${this.buildDashboardGuildPanel(snapshot)}
                    </div>
                `,
                rightPage: `
                    ${this.buildDashboardFeed(snapshot)}
                `,
                footer: this.buildDashboardContext(snapshot),
            });
        },

        buildCampaignsMarkup(user, snapshot = null) {
            const campaigns = snapshot?.campaigns || [];
            const ownedCount = campaigns.filter((campaign) => Boolean(campaign.is_owner)).length;
            const joinedCount = campaigns.filter((campaign) => Boolean(campaign.is_member) && !campaign.is_owner).length;
            const activeCount = campaigns.filter((campaign) => String(campaign.status || '').toLowerCase() === 'active').length;

            return this.buildPageShell('campaigns', user, {
                eyebrow: 'Chapter II',
                title: 'Campaigns',
                copy: 'Lege Kampagnen an, öffne den Kampagnen-Hub und gehe von dort weiter in Session-Prep, direkte Charakterzuweisung, Karten, Assets und schließlich nach Play.',
                rightEyebrow: 'Nächste Schritte',
                rightTitle: 'Kampagnen produktiv nutzen',
                rightCopy: 'Diese Seite ist der Einstieg in die echte Vorbereitungsarbeit: neue Kampagne starten, bestehenden Hub öffnen oder Charaktere für die nächste Session vorbereiten.',
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
                                href: buildIntentHref('/campaigns', { classic: 1, intent: 'create' }),
                                primary: true,
                            },
                            {
                                label: 'Kampagnen-Hub öffnen',
                                href: campaigns.length > 0
                                    ? buildIntentHref('/campaigns', { campaign_id: campaigns[0].id, classic: 1 })
                                    : buildIntentHref('/campaigns', { classic: 1 }),
                            },
                        ])}
                        ${this.buildCampaignLedger(campaigns)}
                    </section>
                `,
                rightPage: `
                    <section class="book-scene-panel">
                        <span class="book-scene-panel-kicker">Vorbereitung</span>
                        <h2 class="book-scene-panel-title">Was du hier erledigst</h2>
                        <p class="book-scene-panel-copy">Kampagnen werden hier nicht nur angezeigt. Von hier aus öffnest du den Hub, bereitest Sessions vor und gehst mit klaren Schritten Richtung Tisch.</p>
                        ${this.buildActionButtons([
                            {
                                label: '+ Kampagne anlegen',
                                href: buildIntentHref('/campaigns', { classic: 1, intent: 'create' }),
                                primary: true,
                            },
                            {
                                label: 'Charaktere öffnen',
                                href: buildIntentHref('/characters', { classic: 1 }),
                            },
                        ])}
                        <div class="book-scene-note-list">
                            <div class="book-scene-note">Neue Kampagnen werden direkt über das echte Erstellformular gestartet, nicht über Prompt-Dialoge.</div>
                            <div class="book-scene-note">Bestehende Kampagnen führen in den Hub, dort weiter in Session-Prep mit Karten, Assets und direkter Charakterzuweisung.</div>
                            <div class="book-scene-note">Wenn noch keine Kampagne existiert, ist der erste klare Schritt: Kampagne anlegen und danach den Hub öffnen.</div>
                        </div>
                    </section>
                `,
                footer: `
                    <div class="book-dashboard-widget-header">
                        <h2>Kampagnen-Werkzeuge</h2>
                        <span class="book-dashboard-widget-tag">hub, session-prep, maps, assets</span>
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
                            <small>Session-bezogene Assets öffnen, Upload vorbereiten und den Vorbereitungsstand vor Play pruefen.</small>
                        </div>
                    </div>
                `,
            });
        },

        buildCharactersMarkup(user, snapshot = null) {
            const characters = snapshot?.characters || [];
            const distinctClasses = new Set(characters.map((character) => character.class).filter(Boolean)).size;
            const highestLevel = characters.reduce((highest, character) => Math.max(highest, Number(character.level || 1)), 1);

            return this.buildPageShell('characters', user, {
                eyebrow: 'Chapter III',
                title: 'Characters',
                copy: 'Lege Helden an, pflege Avatar und Token und wechsle für Details in den Bogen. Danach führt der Weg sauber zurück in Kampagnen und Session-Prep.',
                rightEyebrow: 'Nächste Schritte',
                rightTitle: 'Helden vorbereiten',
                rightCopy: 'Das Charakterarchiv ist kein Platzhalter mehr: hier beginnst du die Heldenarbeit und springst von dort in Bogen, Kampagnenkontext und später in die Session-Zuweisung.',
                chips: [`${characters.length} Helden`, `${distinctClasses} Klassen`, `Höchstes Level ${highestLevel}`],
                leftPage: `
                    ${this.buildStatStrip([
                        { value: String(characters.length), label: 'Charaktere' },
                        { value: String(distinctClasses), label: 'Klassen' },
                        { value: String(highestLevel), label: 'Höchstes Level' },
                    ])}
                    <section class="book-scene-panel">
                        <span class="book-scene-panel-kicker">Archiv</span>
                        <h2 class="book-scene-panel-title">Heldenarchiv</h2>
                        <p class="book-scene-panel-copy">Öffne bestehende Helden, starte neue Figuren direkt aus dem Archiv und führe sie danach über Bogen und Kampagnenkontext bis in die Session-Vorbereitung.</p>
                        ${this.buildActionButtons([
                            {
                                label: 'Held anlegen',
                                href: buildIntentHref('/characters', { classic: 1, intent: 'create' }),
                                primary: true,
                            },
                            {
                                label: 'Archiv öffnen',
                                href: buildIntentHref('/characters', { classic: 1 }),
                            },
                        ])}
                        ${this.buildCharacterLedger(characters)}
                    </section>
                `,
                rightPage: `
                    <section class="book-scene-panel">
                        <span class="book-scene-panel-kicker">Heldenarbeit</span>
                        <h2 class="book-scene-panel-title">Was du von hier aus tust</h2>
                        <p class="book-scene-panel-copy">Erstelle neue Helden, öffne den Bogen für Werte und Ausrüstung und gehe danach zurück in Kampagnen oder Session-Prep, um den Held einsatzbereit zu machen.</p>
                        ${this.buildActionButtons([
                            {
                                label: 'Held anlegen',
                                href: buildIntentHref('/characters', { classic: 1, intent: 'create' }),
                                primary: true,
                            },
                            {
                                label: 'Kampagnen öffnen',
                                href: buildIntentHref('/campaigns', { classic: 1 }),
                            },
                        ])}
                        <div class="book-scene-note-list">
                            <div class="book-scene-note">Der Bogen bleibt die richtige Fläche für detaillierte Bearbeitung von Werten, Inventar, Zaubern und Notizen.</div>
                            <div class="book-scene-note">Avatar und Token werden über Archiv und Bogen konsistent gepflegt und bleiben später im Session-Kontext sichtbar.</div>
                            <div class="book-scene-note">Wenn ein Held kampagnengebunden ist, führt der nächste sinnvolle Schritt über Kampagnen-Hub und Session-Prep in die direkte Zuweisung.</div>
                        </div>
                    </section>
                `,
                footer: `
                    <div class="book-dashboard-widget-header">
                        <h2>Charakter-Werkzeuge</h2>
                        <span class="book-dashboard-widget-tag">anlage, boegen, identität, rueckweg in prep</span>
                    </div>
                    <p class="book-dashboard-widget-copy">
                        Die Charakterarbeit ist bereits operativ: Helden anlegen, Standard Array oder Point Buy nutzen, Avatar und Token setzen und danach zurück in die Kampagnenvorbereitung gehen.
                    </p>
                    <div class="book-scene-widget-stack">
                        <div class="book-scene-widget-card">
                            <span>Erstellung</span>
                            <small>Neue Helden direkt aus dem Archiv starten, ohne den Vorbereitungsweg zu verlassen.</small>
                        </div>
                        <div class="book-scene-widget-card">
                            <span>Werte</span>
                            <small>Standard Array und Point Buy bleiben in der Anlage direkt verfügbar.</small>
                        </div>
                        <div class="book-scene-widget-card">
                            <span>Avatar & Token</span>
                            <small>Identität ist im Archiv und im Bogen vorhanden und kann dort direkt gepflegt werden.</small>
                        </div>
                        <div class="book-scene-widget-card">
                            <span>Rueckweg in Prep</span>
                            <small>Nach dem Bogen geht es sichtbar zurück in Kampagnen und weiter in die Session-Zuweisung.</small>
                        </div>
                    </div>
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
                node.addEventListener('click', () => {
                    const href = node.getAttribute('data-dashboard-href');
                    if (!href) {
                        return;
                    }
                    window.location.href = href;
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

            this.sceneSurface.querySelectorAll('[data-dashboard-guild-switch]').forEach((node) => {
                node.addEventListener('click', async () => {
                    const guildId = Number(node.getAttribute('data-dashboard-guild-switch') || '0');
                    if (!guildId || !window.Auth || typeof window.Auth.makeAuthRequest !== 'function') {
                        return;
                    }

                    node.setAttribute('disabled', 'disabled');
                    try {
                        const snapshot = await window.Auth.makeAuthRequest('/api/dashboard/guilds/primary', 'POST', { guild_id: guildId });
                        this.dashboardNotice = snapshot?.guild_notice || 'Primaere Gilde aktualisiert.';
                        this.sceneSnapshot = snapshot || this.sceneSnapshot;
                        this.sceneUser = this.sceneSnapshot?.user || this.sceneUser;
                        this.renderSceneRoute('dashboard', this.sceneUser, this.sceneSnapshot);
                    } catch (error) {
                        console.error('Failed to switch primary guild:', error);
                        this.dashboardNotice = error.message || 'Primaere Gilde konnte nicht gewechselt werden.';
                        this.renderSceneRoute('dashboard', this.sceneUser, this.sceneSnapshot);
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

                    if (phase.tone === 'live' || phase.tone === 'paused') {
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
                    this.openPlayFromLaunch(campaignId, sessionId);
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

        openPlayFromLaunch(campaignId, sessionId) {
            this.closePlayLaunch();
            this.enterPlay({ campaignId, sessionId, sourceRoute: this.currentView || this.currentPage || 'dashboard' });
        },

        async quickStartSessionAndPlay(campaignId, sessionId) {
            this.setPlayLaunchStatus('Session wird gestartet...');
            try {
                await window.Auth.makeAuthRequest(`/api/sessions/${sessionId}/start`, 'POST');
                this.openPlayFromLaunch(campaignId, sessionId);
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
                this.openPlayFromLaunch(campaignId, session.id);
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

        async loadSceneSnapshot(user = null) {
            const resolvedUser = user || this.sceneUser || await (window.Auth ? window.Auth.getCurrentUser() : null);
            const snapshot = {
                user: resolvedUser || null,
                campaigns: [],
                characters: [],
            };

            if (!window.Auth || typeof window.Auth.makeAuthRequest !== 'function') {
                return snapshot;
            }

            const [campaignsResult, charactersResult] = await Promise.allSettled([
                window.Auth.makeAuthRequest('/api/campaigns'),
                window.Auth.makeAuthRequest('/api/characters/mine'),
            ]);

            if (campaignsResult.status === 'fulfilled' && Array.isArray(campaignsResult.value)) {
                snapshot.campaigns = campaignsResult.value;
            }

            if (charactersResult.status === 'fulfilled' && Array.isArray(charactersResult.value)) {
                snapshot.characters = charactersResult.value;
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
            if (typeof gsap !== 'undefined') {
                gsap.set([this.loginSpread, this.loginLeftPage, this.loginRightPage], {
                    clearProps: 'transform,opacity,filter',
                });
            }
        },

        open() {
            if (this.isOpened) {
                return;
            }

            if (typeof gsap === 'undefined') {
                setTimeout(() => this.open(), 100);
                return;
            }

            this.isOpened = true;
            this.setSceneState('opening');

            const timeline = gsap.timeline();
            timeline.to(this.book, {
                rotationY: 0,
                scale: 1,
                x: 0,
                y: 0,
                duration: 0.92,
                ease: 'power2.out',
                force3D: true,
            }, 0);
            timeline.to(this.bookCover, {
                rotationY: -160,
                duration: 1.2,
                ease: 'power2.inOut',
                force3D: true,
            }, 0.15);
            if (this.coverTitle && this.coverOrnament) {
                timeline.to([this.coverTitle, this.coverOrnament], {
                    opacity: 0,
                    duration: 0.25,
                    ease: 'power1.out',
                }, 0.4);
            }
            timeline.to(this.bookPages, {
                scaleY: [1, 1.002, 1, 1.002, 1],
                duration: 0.4,
                ease: 'sine.inOut',
                force3D: true,
            }, 0.8);
            if (this.loginContent) {
                timeline.add(() => {
                    // currentPage (set from the real URL by updateCurrentPage())
                    // is used here rather than currentView, which create()'s
                    // dashboard pre-render (ensureDashboardScene(), for instant
                    // transitions later) unconditionally overwrites to
                    // 'dashboard' as a side effect - on every page, including
                    // login.html, regardless of whether anyone is logged in.
                    if (this.currentPage === 'login') {
                        gsap.set([this.loginSpread, this.loginLeftPage, this.loginRightPage], {
                            clearProps: 'transform,opacity,filter',
                        });
                        gsap.set(this.loginContent, { opacity: 1, pointerEvents: 'auto' });
                        gsap.fromTo([this.loginLeftPage, this.loginRightPage], {
                            opacity: 0,
                            y: 24,
                            rotationY: (index) => index === 0 ? 5 : -5,
                            transformOrigin: (index) => index === 0 ? 'right center' : 'left center',
                        }, {
                            opacity: 1,
                            y: 0,
                            rotationY: 0,
                            duration: 0.64,
                            ease: 'power2.out',
                            stagger: 0.08,
                            force3D: true,
                        });
                    }
                }, 1.05);
            }

            timeline.eventCallback('onComplete', () => {
                this.bookCover.classList.add('is-open');
                if (this.currentPage !== 'login') {
                    this.hideLoginContent();
                    this.setSceneState('dashboard');
                } else {
                    if (this.loginContent) {
                        this.loginContent.classList.add('visible');
                        this.loginContent.removeAttribute('aria-hidden');
                    }
                    document.body.classList.add('book-login-open');
                    this.setSceneState('login');
                }
            });
        },

        applyOpenedBookState() {
            if (typeof gsap !== 'undefined') {
                gsap.set(this.book, { rotationY: 0, scale: 1, x: 0, y: 0 });
                gsap.set(this.bookCover, { rotationY: -160 });
                gsap.set(this.bookPages, { x: 0, scaleX: 1, scaleY: 1 });
                if (this.bookBack) {
                    gsap.set(this.bookBack, { opacity: 1 });
                }
            } else {
                if (this.book) {
                    this.book.style.transform = 'rotateY(0deg) scale(1)';
                }
                if (this.bookCover) {
                    this.bookCover.style.transform = 'rotateY(-160deg)';
                }
                if (this.bookPages) {
                    this.bookPages.style.transform = 'translateX(4px) rotateY(0deg) scaleX(1) scaleY(1)';
                }
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
            if (!reducedMotion.matches && typeof gsap !== 'undefined') {
                const direction = this.getTurnDirection('login', routeKey);
                const camera = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-camera') : null;
                const page = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-page') : null;
                if (camera) {
                    gsap.fromTo(camera, {
                        opacity: 0,
                        scale: 1.12,
                        x: direction * 96,
                        y: 34,
                        rotationY: direction * -14,
                        transformOrigin: direction > 0 ? 'left center' : 'right center',
                    }, {
                        opacity: 1,
                        scale: 1,
                        x: 0,
                        y: 0,
                        rotationY: 0,
                        duration: 0.86,
                        ease: 'expo.out',
                        force3D: true,
                    });
                }
                if (page) {
                    gsap.fromTo(page, {
                        opacity: 0.86,
                        boxShadow: '0 34px 78px rgba(0, 0, 0, 0.22)',
                    }, {
                        opacity: 1,
                        boxShadow: '0 24px 52px rgba(0, 0, 0, 0.15)',
                        duration: 0.82,
                        ease: 'power2.out',
                    });
                }
            }
        },

        bootstrapDashboardRoute(user = null) {
            this.bootstrapRoute('dashboard', user);
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

            try {
                setStatus(statusMessage || `Opening ${this.getSpreadTitle(routeKey)}...`);

                if (!auth || typeof auth.requireAuth !== 'function') {
                    throw new Error('Auth client unavailable');
                }

                const user = await auth.requireAuth(loginPath);
                if (!user) {
                    return false;
                }

                const entryBoundary = this.consumeBookEntryBoundary(routeKey);
                this.create();

                const resolvedSnapshot = snapshotLoader
                    ? await snapshotLoader(user)
                    : await this.loadSceneSnapshot(user);

                this.sceneSnapshot = resolvedSnapshot || { user };
                this.sceneUser = this.sceneSnapshot.user || user;
                await this.loadPageContent(routeKey);
                this.bootstrapRoute(routeKey, user);
                this.finalizeBookEntryBoundary(entryBoundary);
                setStatus('');
                return true;
            } catch (error) {
                console.error(`Failed to bootstrap ${routeKey} scene:`, error);
                setStatus('');
                window.location.href = loginPath;
                return false;
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

            const raw = readBookReturnBoundary();
            if (!raw) {
                return null;
            }

            try {
                const boundary = JSON.parse(raw);
                clearBookReturnBoundary();

                if (!boundary || typeof boundary !== 'object') {
                    return null;
                }

                const target = boundary.target && typeof boundary.target === 'object' ? boundary.target : {};
                if (boundary.kind !== 'table-to-book') {
                    return null;
                }
                if (boundary.from_mode !== 'TABLE_MODE') {
                    return null;
                }
                if (boundary.transition_mode !== 'TABLE_TO_BOOK_TRANSITION') {
                    return null;
                }
                if (boundary.target_mode !== 'BOOK_MODE') {
                    return null;
                }
                if (target.family !== 'book') {
                    return null;
                }
                if (target.route !== routeKey) {
                    return null;
                }
                if (!['table-exit', 'book-route-entry'].includes(String(boundary.phase || 'table-exit'))) {
                    return null;
                }

                document.body.dataset.bookSceneEntryBoundary = 'table-to-book';
                document.body.dataset.bookSceneEntryPhase = 'TABLE_TO_BOOK_TRANSITION';
                document.body.dataset.bookSceneEntrySourceMode = 'TABLE_MODE';
                document.body.dataset.bookSceneEntrySourceRoute = String(boundary.source_route || 'play');
                document.body.dataset.bookSceneEntryTargetRoute = String(target.route || routeKey);
                return boundary;
            } catch (error) {
                console.warn('Failed to parse book return boundary context:', error);
                clearBookReturnBoundary();
                return null;
            }
        },

        finalizeBookEntryBoundary(boundary = null) {
            if (!boundary) {
                return;
            }

            if (this.bookEntryArrivalTimer) {
                window.clearTimeout(this.bookEntryArrivalTimer);
                this.bookEntryArrivalTimer = null;
            }

            this.setSceneState('return-transition');
            document.body.dataset.bookSceneTransitionTarget = String(boundary.target?.route || this.currentView || 'dashboard');
            document.body.dataset.bookSceneTransitionPhase = 'TABLE_TO_BOOK_TRANSITION';

            const settleBoundary = () => {
                if (!document.body || document.body.dataset.bookSceneEntryBoundary !== 'table-to-book') {
                    return;
                }
                document.body.dataset.bookSceneEntryBoundary = 'arrived';
                document.body.dataset.bookSceneEntryPhase = 'BOOK_MODE';

                const arrivalDuration = Math.max(
                    240,
                    Math.min(960, Number(boundary.arrival_duration_ms) || BOOK_RETURN_ARRIVAL_DURATION_MS)
                );

                this.bookEntryArrivalTimer = window.setTimeout(() => {
                    if (!document.body) {
                        return;
                    }
                    delete document.body.dataset.bookSceneEntrySourceMode;
                    delete document.body.dataset.bookSceneEntrySourceRoute;
                    delete document.body.dataset.bookSceneEntryTargetRoute;
                    delete document.body.dataset.bookSceneTransitionTarget;
                    document.body.dataset.bookSceneTransitionPhase = 'BOOK_MODE';
                    this.setSceneState('dashboard');
                    this.bookEntryArrivalTimer = null;
                }, arrivalDuration);
            };

            if (reducedMotion.matches) {
                this.bookEntryArrivalTimer = window.setTimeout(() => {
                    settleBoundary();
                }, 64);
                return;
            }

            window.requestAnimationFrame(() => {
                window.requestAnimationFrame(() => {
                    settleBoundary();
                });
            });
        },

        _runPlayExitTransition(handoff) {
            const navigateToPlay = () => {
                handoff.phase = 'play-route-entry';
                handoff.book_exit_completed_at = new Date().toISOString();
                persistPlayHandoff(handoff);
                window.location.href = handoff.target_href;
            };

            this.transitionInFlight = true;
            this.setSceneState('play-transition');
            document.body.dataset.bookSceneTransitionTarget = 'play';
            document.body.dataset.bookSceneTransitionPhase = 'BOOK_TO_TABLE_TRANSITION';

            const currentCamera = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-camera') : null;
            const currentPage = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-page') : null;

            if (reducedMotion.matches || typeof gsap === 'undefined') {
                window.setTimeout(navigateToPlay, 64);
                return true;
            }

            const timeline = gsap.timeline({
                defaults: { ease: 'power2.inOut' },
                onComplete: navigateToPlay,
            });

            if (this.sceneBackdrop) {
                timeline.to(this.sceneBackdrop, {
                    opacity: 0.74,
                    filter: 'saturate(0.8) brightness(0.74)',
                    duration: 0.24,
                }, 0);
            }

            if (currentCamera) {
                timeline.to(currentCamera, {
                    opacity: 0.18,
                    scale: 0.94,
                    y: 28,
                    filter: 'blur(1.8px)',
                    duration: 0.3,
                    force3D: true,
                }, 0);
            }

            if (currentPage) {
                timeline.to(currentPage, {
                    opacity: 0.72,
                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.10)',
                    duration: 0.26,
                }, 0.02);
            }

            if (this.bookCover) {
                timeline.to(this.bookCover, {
                    rotationY: -18,
                    duration: PLAY_EXIT_DURATION_MS / 1000,
                    ease: 'expo.inOut',
                    force3D: true,
                }, 0.06);
            }

            if (this.bookPages) {
                timeline.to(this.bookPages, {
                    scaleX: 0.987,
                    scaleY: 0.994,
                    duration: 0.34,
                    force3D: true,
                }, 0.08);
            }

            if (this.book) {
                timeline.to(this.book, {
                    scale: 0.84,
                    x: -112,
                    y: 18,
                    rotationY: -20,
                    rotationX: 5,
                    duration: PLAY_EXIT_DURATION_MS / 1000,
                    ease: 'expo.inOut',
                    force3D: true,
                }, 0.02);
            }

            return true;
        },

        enterPlay(config = {}) {
            const {
                campaignId,
                sessionId,
                sourceRoute = this.currentView || this.currentPage || 'campaigns',
            } = config;

            const resolvedCampaignId = Number(campaignId);
            const resolvedSessionId = Number(sessionId);
            if (!Number.isInteger(resolvedCampaignId) || resolvedCampaignId <= 0) {
                throw new Error('campaignId is required for play handoff');
            }
            if (!Number.isInteger(resolvedSessionId) || resolvedSessionId <= 0) {
                throw new Error('sessionId is required for play handoff');
            }

            const targetHref = buildPlayHref(resolvedCampaignId, resolvedSessionId);
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

            const snapshot = await this.loadSceneSnapshot(user);
            this.sceneSnapshot = snapshot;
            this.sceneUser = snapshot.user || user || this.sceneUser;
            await this.loadPageContent(routeKey);

            const instant = Boolean(options.instant) || reducedMotion.matches || typeof gsap === 'undefined';
            if (instant) {
                this.showSceneInstant(routeKey, this.sceneUser, snapshot);
                this.transitionInFlight = false;
                return;
            }

            const currentRoute = this.currentView || this.currentPage || 'login';
            const direction = this.getTurnDirection(currentRoute, routeKey);
            const currentCamera = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-camera') : null;
            const currentPage = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-page') : null;
            const timeline = gsap.timeline();
            let nextCamera = null;
            let nextPage = null;
            let sceneRendered = false;

            this.setSceneState('transition');
            this.sceneSurface.hidden = false;
            this.sceneSurface.setAttribute('aria-hidden', 'false');
            this.sceneSurface.classList.add('is-visible');

            const renderIncomingScene = () => {
                if (sceneRendered) {
                    return;
                }

                sceneRendered = true;
                this.renderSceneRoute(routeKey, this.sceneUser, snapshot);
                nextCamera = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-camera') : null;
                nextPage = this.sceneSurface ? this.sceneSurface.querySelector('.book-dashboard-page') : null;

                if (nextCamera) {
                    gsap.set(nextCamera, {
                        opacity: 0.8,
                        scale: 1.03,
                        x: direction * 26,
                        y: 8,
                        rotationY: direction * -3,
                        filter: 'blur(0.8px)',
                        transformOrigin: direction > 0 ? 'left center' : 'right center',
                    });
                }

                if (nextPage) {
                    gsap.set(nextPage, {
                        opacity: 0.92,
                        boxShadow: '0 30px 72px rgba(0, 0, 0, 0.22)',
                    });
                }
            };

            this.prepareTurnLeaf(currentRoute, routeKey);
            if (currentRoute === 'login') {
                renderIncomingScene();
            }

            timeline.to(this.book, {
                y: -6,
                rotationX: direction * 0.7,
                duration: 0.22,
                ease: 'sine.out',
            }, 0);
            timeline.to(this.bookPages, {
                scaleY: 1.006,
                duration: 0.26,
                ease: 'sine.out',
            }, 0.06);

            if (this.turnSheet) {
                timeline.to(this.turnSheet, {
                    rotationY: -176,
                    duration: 1.04,
                    ease: 'power2.inOut',
                    force3D: true,
                }, 0.02);
            }

            if (this.turnShadow) {
                timeline.to(this.turnShadow, {
                    opacity: 0.48,
                    duration: 0.22,
                    ease: 'sine.out',
                }, 0.12);
                timeline.to(this.turnShadow, {
                    opacity: 0,
                    duration: 0.34,
                    ease: 'sine.inOut',
                }, 0.58);
            }

            if (this.loginContent && currentRoute === 'login') {
                timeline.to(this.loginLeftPage, {
                    opacity: 0.8,
                    scale: 0.992,
                    filter: 'blur(0.4px)',
                    duration: 0.32,
                    ease: 'power1.out',
                }, 0.08);
                timeline.to(this.loginContent, {
                    opacity: 0,
                    duration: 0.3,
                    ease: 'power2.in',
                }, 0.54);
            } else if (currentCamera) {
                timeline.to(currentCamera, {
                    opacity: 0.8,
                    scale: 0.985,
                    y: 6,
                    filter: 'blur(0.6px)',
                    duration: 0.28,
                    ease: 'power1.out',
                    force3D: true,
                }, 0.04);
            }

            if (currentPage) {
                timeline.to(currentPage, {
                    opacity: 0.9,
                    boxShadow: '0 10px 24px rgba(0, 0, 0, 0.08)',
                    duration: 0.24,
                    ease: 'power1.out',
                }, 0.06);
            }

            timeline.add(() => {
                if (currentRoute !== 'login') {
                    renderIncomingScene();
                }

                if (nextCamera) {
                    gsap.to(nextCamera, {
                        opacity: 1,
                        scale: 1,
                        x: 0,
                        y: 0,
                        rotationY: 0,
                        filter: 'blur(0px)',
                        duration: 0.48,
                        ease: 'expo.out',
                        force3D: true,
                    });
                }

                if (nextPage) {
                    gsap.to(nextPage, {
                        opacity: 1,
                        boxShadow: '0 24px 52px rgba(0, 0, 0, 0.15)',
                        duration: 0.42,
                        ease: 'power2.out',
                    });
                }
            }, 0.54);

            timeline.to(this.book, {
                y: 0,
                rotationX: 0,
                duration: 0.62,
                ease: 'expo.out',
            }, 0.42);
            timeline.to(this.bookPages, {
                scaleY: 1,
                duration: 0.56,
                ease: 'expo.out',
            }, 0.44);

            timeline.eventCallback('onComplete', () => {
                this.hideLoginContent();
                this.hideTurnLeaf();
                if (nextCamera) {
                    nextCamera.style.opacity = '1';
                    nextCamera.style.transform = 'none';
                    nextCamera.style.filter = 'none';
                }
                this.currentView = routeKey;
                this.currentPage = routeKey;
                this.applyOpenedBookState();
                this.setSceneState('dashboard');
                document.body.dataset.bookSceneRoute = routeKey;
                this.updateBookmarkPosition(routePathForKey(routeKey));
                window.history.replaceState({ book_scene: routeKey }, '', historyHrefForRoute(routeKey));
                this.transitionInFlight = false;
            });
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
}());
