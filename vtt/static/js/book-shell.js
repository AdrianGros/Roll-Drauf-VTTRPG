(function () {
    'use strict';

    // Legacy shell adapter for the lobby/table pages. BookScene owns
    // same-document route rendering; this adapter only keeps the older
    // document routes usable and performs an immediate navigation fallback.
    const routes = window.BookRoutes || {};
    let initialized = false;
    let isNavigating = false;

    function setShellState(state) {
        document.body.dataset.shellState = state;
        document.body.classList.toggle('is-shell-loading', state === 'loading');
        document.body.classList.toggle('is-shell-ready', state === 'ready');
        document.body.classList.toggle('is-shell-navigating', state === 'navigating');
    }

    function normalizePath(path) {
        if (!path) {
            return '/dashboard';
        }

        const [pathname] = String(path).split('?');
        if (pathname === '/') {
            return '/dashboard';
        }
        if (routes[pathname]) {
            return pathname;
        }
        if (pathname.endsWith('.html') && routes[pathname.slice(0, -5)]) {
            return pathname.slice(0, -5);
        }
        return pathname;
    }

    function currentPath() {
        return normalizePath(window.location.pathname);
    }

    function currentConfig() {
        return routes[currentPath()] || routes[window.location.pathname] || null;
    }

    function updateRouteChrome() {
        const config = currentConfig();
        if (!config) {
            return;
        }

        document.body.dataset.bookCurrentRoute = currentPath();
        document.body.dataset.bookMode = config.mode;
        document.body.dataset.bookChapter = config.chapter.toLowerCase();
        document.body.dataset.bookSection = config.section.toLowerCase().replace(/\s+/g, '-');

        document.querySelectorAll('[data-book-field="chapter"]').forEach((node) => {
            node.textContent = config.chapter;
        });
        document.querySelectorAll('[data-book-field="section"]').forEach((node) => {
            node.textContent = config.section;
        });

        const folio = config.folio || ['', ''];
        document.querySelectorAll('[data-book-folio="left"]').forEach((node) => {
            node.textContent = folio[0] || '';
        });
        document.querySelectorAll('[data-book-folio="right"]').forEach((node) => {
            node.textContent = folio[1] || '';
        });

        document.querySelectorAll('[data-book-route]').forEach((node) => {
            const active = normalizePath(node.getAttribute('data-book-route')) === currentPath();
            node.classList.toggle('is-active', active);
            if (active) {
                node.setAttribute('aria-current', 'page');
            } else {
                node.removeAttribute('aria-current');
            }
        });
    }

    function shouldIgnoreKeyboardNavigation() {
        const active = document.activeElement;
        if (!active) {
            return false;
        }
        return ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName)
            || Boolean(document.querySelector('.modal-overlay:not([hidden])'));
    }

    function navigate(path) {
        const target = normalizePath(path);
        if (!target || target === currentPath() || isNavigating) {
            return;
        }

        isNavigating = true;
        document.body.setAttribute('aria-busy', 'true');
        setShellState('navigating');
        window.location.href = path;
    }

    function wireKeyboardNavigation() {
        document.addEventListener('keydown', (event) => {
            const config = currentConfig();
            if (!config || shouldIgnoreKeyboardNavigation() || isNavigating) {
                return;
            }

            if (event.key === 'ArrowLeft' && config.prev) {
                event.preventDefault();
                navigate(config.prev);
            } else if (event.key === 'ArrowRight' && config.next) {
                event.preventDefault();
                navigate(config.next);
            }
        });
    }

    function wireRouteLinks() {
        document.querySelectorAll('[data-book-route]').forEach((node) => {
            if (node.hasAttribute('onclick')) {
                return;
            }
            node.addEventListener('click', (event) => {
                const route = node.getAttribute('data-book-route');
                if (!route || isNavigating) {
                    return;
                }
                if (normalizePath(route) === currentPath()) {
                    event.preventDefault();
                    return;
                }
                event.preventDefault();
                navigate(route);
            });
        });
    }

    function init() {
        if (initialized) {
            return;
        }
        initialized = true;
        setShellState('loading');
        updateRouteChrome();
        wireRouteLinks();
        wireKeyboardNavigation();
        setShellState('ready');
    }

    window.BookShell = {
        init,
        navigate,
        currentConfig,
        resetNavigationState: () => {
            isNavigating = false;
            document.body.removeAttribute('aria-busy');
            setShellState('ready');
        },
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
}());
