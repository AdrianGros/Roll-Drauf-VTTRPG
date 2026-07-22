(function () {
    'use strict';

    const routes = window.BookRoutes || {};
    const TRANSITION_STORAGE_KEY = 'book_shell_transition_v2';
    const reducedMotion = window.matchMedia
        ? window.matchMedia('(prefers-reduced-motion: reduce)')
        : { matches: false, addEventListener: null, removeEventListener: null };

    let initialized = false;
    let isNavigating = false;
    let navigationTimeoutId = null;

    function setShellState(state) {
        document.body.dataset.shellState = state;
        document.body.classList.toggle('is-shell-loading', state === 'loading');
        document.body.classList.toggle('is-shell-ready', state === 'ready');
        document.body.classList.toggle('is-shell-navigating', state === 'navigating');
    }

    function syncMotionPreference() {
        document.body.classList.toggle('has-reduced-motion', Boolean(reducedMotion.matches));
    }

    function resetNavigationState() {
        isNavigating = false;
        if (navigationTimeoutId !== null) {
            window.clearTimeout(navigationTimeoutId);
            navigationTimeoutId = null;
        }
        document.body.removeAttribute('aria-busy');
        setShellState('ready');
    }

    function normalizePath(path) {
        if (!path) {
            return '/';
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

    function currentConfig() {
        const path = normalizePath(window.location.pathname);
        return routes[path] || routes[window.location.pathname] || null;
    }

    function currentPath() {
        return normalizePath(window.location.pathname);
    }

    function overlayElement() {
        let overlay = document.querySelector('.book-route-turn-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'book-route-turn-overlay';
            overlay.setAttribute('aria-hidden', 'true');
            overlay.innerHTML = '<div class="book-route-turn-shadow"></div><div class="book-route-turn-page"></div>';
            document.body.appendChild(overlay);
        }
        return overlay;
    }

    function chromeTargets() {
        return Array.from(document.querySelectorAll('header, main, footer'))
            .filter((node) => node && !node.closest('.book-route-turn-overlay'));
    }

    function rememberTransitionIntent(path) {
        try {
            sessionStorage.setItem(TRANSITION_STORAGE_KEY, JSON.stringify({
                from: currentPath(),
                to: normalizePath(path),
                ts: Date.now(),
            }));
        } catch (error) {
            // ignore storage failures
        }
    }

    function consumeTransitionIntent() {
        try {
            const raw = sessionStorage.getItem(TRANSITION_STORAGE_KEY);
            if (!raw) {
                return null;
            }
            sessionStorage.removeItem(TRANSITION_STORAGE_KEY);
            const parsed = JSON.parse(raw);
            if (!parsed || !parsed.to || (Date.now() - Number(parsed.ts || 0)) > 5000) {
                return null;
            }
            return parsed;
        } catch (error) {
            return null;
        }
    }

    function clearChromeProps() {
        if (typeof gsap === 'undefined') {
            return;
        }
        gsap.set(chromeTargets(), { clearProps: 'transform,opacity,filter' });
    }

    function updateRouteChrome() {
        const config = currentConfig();
        if (!config) {
            return;
        }

        document.body.dataset.bookRoute = currentPath();
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
            const nodeRoute = normalizePath(node.getAttribute('data-book-route'));
            const active = nodeRoute === currentPath();
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
        const tag = active.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
            return true;
        }
        const modal = document.querySelector('.modal-overlay');
        return Boolean(modal && modal.style.display !== 'none');
    }

    function navigate(path) {
        const target = normalizePath(path);
        const current = currentPath();

        if (!target || target === current || isNavigating) {
            return;
        }

        isNavigating = true;
        document.body.setAttribute('aria-busy', 'true');
        setShellState('navigating');

        if (reducedMotion.matches || typeof gsap === 'undefined') {
            window.location.href = path;
            return;
        }

        const overlay = overlayElement();
        const page = overlay.querySelector('.book-route-turn-page');
        const shadow = overlay.querySelector('.book-route-turn-shadow');
        const targets = chromeTargets();
        rememberTransitionIntent(path);
        overlay.classList.add('is-visible');
        page.style.transform = 'perspective(2200px) rotateY(0deg)';

        const tl = gsap.timeline();
        tl.set(targets, {
            transformOrigin: 'center top',
            willChange: 'transform, opacity, filter',
        }, 0);
        tl.set(shadow, { opacity: 0 }, 0);
        tl.to(page, {
            rotationY: 180,
            xPercent: -3,
            scaleX: 0.965,
            duration: 0.82,
            ease: 'power2.inOut',
            force3D: true,
        }, 0.04);
        tl.to(shadow, {
            opacity: 1,
            duration: 0.28,
            ease: 'sine.out',
        }, 0.08);
        tl.to(targets, {
            opacity: 0.88,
            y: 26,
            scale: 0.968,
            rotationX: 4,
            filter: 'blur(1.4px)',
            duration: 0.34,
            ease: 'power2.inOut',
            stagger: 0.03,
        }, 0);
        tl.add(() => {
            window.location.href = path;
        }, 0.36);

        navigationTimeoutId = window.setTimeout(() => {
            resetNavigationState();
        }, 1800);
    }

    function playArrivalAnimation() {
        const intent = consumeTransitionIntent();
        if (reducedMotion.matches || typeof gsap === 'undefined') {
            clearChromeProps();
            setShellState('ready');
            return;
        }

        const overlay = overlayElement();
        const page = overlay.querySelector('.book-route-turn-page');
        const shadow = overlay.querySelector('.book-route-turn-shadow');
        const targets = chromeTargets();
        if (targets.length === 0) {
            setShellState('ready');
            return;
        }

        const hasIntent = Boolean(intent && intent.to === currentPath());
        overlay.classList.add('is-visible');

        const tl = gsap.timeline({
            onComplete: () => {
                overlay.classList.remove('is-visible');
                gsap.set([page, shadow], { clearProps: 'transform,opacity' });
                clearChromeProps();
                setShellState('ready');
            },
        });

        tl.set(targets, {
            transformOrigin: 'right center',
            opacity: hasIntent ? 0.66 : 0.72,
            x: hasIntent ? 132 : 104,
            y: hasIntent ? 34 : 24,
            scale: hasIntent ? 0.958 : 0.968,
            rotationY: hasIntent ? -14 : -10,
            rotationX: hasIntent ? -5 : -3,
            filter: hasIntent ? 'blur(1.3px)' : 'blur(0.9px)',
        }, 0);
        tl.set(page, {
            rotationY: 166,
            xPercent: 2,
            scaleX: 0.968,
            transformOrigin: 'right center',
        }, 0);
        tl.set(shadow, { opacity: hasIntent ? 0.52 : 0.38 }, 0);
        tl.to(page, {
            rotationY: 88,
            duration: hasIntent ? 0.32 : 0.28,
            ease: 'power2.out',
            force3D: true,
        }, 0);
        tl.to(shadow, {
            opacity: hasIntent ? 0.18 : 0.12,
            duration: hasIntent ? 0.34 : 0.28,
            ease: 'sine.out',
        }, 0.04);
        tl.to(targets, {
            opacity: 1,
            x: 0,
            y: 0,
            scale: 1,
            rotationY: 0,
            rotationX: 0,
            filter: 'blur(0px)',
            duration: hasIntent ? 0.72 : 0.64,
            ease: 'expo.out',
            stagger: 0.04,
        }, 0.08);
        tl.to(page, {
            rotationY: 6,
            opacity: 0,
            duration: hasIntent ? 0.26 : 0.22,
            ease: 'power2.in',
        }, hasIntent ? 0.38 : 0.32);
        tl.to(shadow, {
            opacity: 0,
            duration: hasIntent ? 0.22 : 0.18,
            ease: 'power1.out',
        }, hasIntent ? 0.4 : 0.34);
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
            }
            if (event.key === 'ArrowRight' && config.next) {
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
        syncMotionPreference();
        if (reducedMotion.addEventListener) {
            reducedMotion.addEventListener('change', syncMotionPreference);
        }
        updateRouteChrome();
        wireRouteLinks();
        wireKeyboardNavigation();
        playArrivalAnimation();
    }

    window.BookShell = {
        init,
        navigate,
        currentConfig,
        resetNavigationState,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
}());
