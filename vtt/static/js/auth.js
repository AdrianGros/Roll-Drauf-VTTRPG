/**
 * Cookie-based authentication utilities for frontend.
 */

class Auth {
    static LOGOUT_REDIRECT_KEY = 'book_ui_forced_logout';
    // Instance wrappers keep compatibility with existing templates using `new Auth()`.
    getCurrentUser() { return Auth.getCurrentUser(); }
    refreshAccessToken() { return Auth.refreshAccessToken(); }
    logout() { return Auth.logout(); }
    makeAuthRequest(url, method = 'GET', body = null) { return Auth.makeAuthRequest(url, method, body); }
    requireAuth(redirectTo = '/login.html') { return Auth.requireAuth(redirectTo); }

    static getCookie(name) {
        const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const match = document.cookie.match(new RegExp(`(?:^|; )${escapedName}=([^;]*)`));
        return match ? decodeURIComponent(match[1]) : null;
    }

    static buildHeaders(method = 'GET', includeJson = false, csrfCookieName = 'csrf_access_token') {
        const headers = {};
        if (window.VTTTableContext) {
            headers['X-VTT-Context'] = window.VTTTableContext.token;
            headers['X-VTT-Tab'] = window.VTTTableContext.tab;
        }
        if (includeJson) {
            headers['Content-Type'] = 'application/json';
        }

        const normalizedMethod = method.toUpperCase();
        const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(normalizedMethod);
        if (needsCsrf) {
            const csrfToken = this.getCookie(csrfCookieName);
            if (csrfToken) {
                headers['X-CSRF-TOKEN'] = csrfToken;
            }
        }

        return headers;
    }

    static async getCurrentUser() {
        try {
            const response = await fetch('/api/auth/check', {
                method: 'GET',
                credentials: 'include'
            });
            if (!response.ok) return null;
            const data = await response.json();
            return data.user || null;
        } catch (error) {
            console.error('Failed to check auth state:', error);
            return null;
        }
    }

    static async requireAuth(redirectTo = '/login.html') {
        let user = await this.getCurrentUser();
        if (!user) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                user = await this.getCurrentUser();
            }
        }
        if (!user) {
            window.location.href = redirectTo;
            return null;
        }
        return user;
    }

    static async redirectIfAuthenticated(target = '/dashboard') {
        let user = await this.getCurrentUser();
        if (!user) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                user = await this.getCurrentUser();
            }
        }
        if (user) {
            window.location.href = target;
        }
    }

    static async refreshAccessToken() {
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                credentials: 'include',
                headers: this.buildHeaders('POST', false, 'csrf_refresh_token')
            });
            return response.ok;
        } catch (error) {
            console.error('Failed to refresh token:', error);
            return false;
        }
    }

    static async logout() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include',
                headers: this.buildHeaders('POST')
            });
        } catch (error) {
            console.error('Logout request failed:', error);
        }

        try {
            sessionStorage.setItem(this.LOGOUT_REDIRECT_KEY, '1');
        } catch (error) {
            // ignore storage failures
        }

        window.location.replace('/login.html?logged_out=1');
    }

    static async makeAuthRequest(url, method = 'GET', body = null, retryOn401 = true) {
        if (!window.VTTTableContext && !String(url).endsWith('/contexts') && !String(url).startsWith('/api/auth/')) {
            try {
                if (window.parent !== window && window.parent.location.origin === window.location.origin) {
                    window.VTTTableContext = window.parent.VTTTableContext || null;
                }
            } catch (_) { /* cross-origin parent has no table authority */ }
            const params = new URLSearchParams(window.location.search);
            if (!window.VTTTableContext && /\/character-sheet(?:\.html)?$/.test(window.location.pathname)
                && Number(params.get('campaign_id')) > 0 && Number(params.get('session_id')) > 0) {
                await this.ensureTableContext(Number(params.get('campaign_id')), Number(params.get('session_id')));
            }
        }
        const includeJson = body !== null;
        const options = {
            method,
            credentials: 'include',
            headers: this.buildHeaders(method, includeJson)
        };
        if (String(url).startsWith('/api/auth/')) {
            delete options.headers['X-VTT-Context'];
            delete options.headers['X-VTT-Tab'];
        }

        const table = String(url).match(/^\/api\/(?:play\/)?campaigns\/(\d+)\/sessions\/(\d+)(?:\/|$)/);
        if (table && !String(url).endsWith('/contexts')) {
            await this.ensureTableContext(Number(table[1]), Number(table[2]),
                /^(GET|HEAD)$/i.test(method) || /\/play(?:\.html)?$/.test(window.location.pathname)
                    ? 'player' : 'dm');
        }
        const context = window.VTTTableContext;
        if (context && !String(url).startsWith('/api/auth/')) {
            options.headers['X-VTT-Context'] = context.token;
            options.headers['X-VTT-Tab'] = context.tab;
        }

        if (body !== null) {
            options.body = JSON.stringify(body);
        }

        let response = await fetch(url, options);

        if (response.status === 401 && retryOn401) {
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                return this.makeAuthRequest(url, method, body, false);
            }
            window.location.href = '/login.html';
            return null;
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            const rawCode = error.error || 'API request failed';
            // Desktop-Audit D07/B2: rohe API-Codes ("forbidden") erreichten als
            // Banner die Spieler. Bekannte Codes werden hier einmal zentral
            // übersetzt; der Original-Code bleibt für Aufrufer mit eigener
            // Behandlung als err.apiError erhalten.
            const translations = {
                'forbidden': 'Dafür fehlt dir die Berechtigung.',
                'not found': 'Das wurde nicht gefunden.',
                'API request failed': 'Die Anfrage ist fehlgeschlagen. Bitte versuche es erneut.'
            };
            const err = new Error(window.VTTI18n?.error(error) || translations[rawCode] || rawCode);
            err.apiError = rawCode;
            err.status = response.status;
            throw err;
        }

        const contentType = response.headers.get('Content-Type') || '';
        if (!contentType.includes('application/json')) {
            return null;
        }

        return response.json();
    }

    static async resumeTableContext(campaignId, sessionId) {
        await this.ensureTableContext(campaignId, sessionId);
        const entry = await this.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/contexts`,
            'POST', {resume: true, tab: crypto.randomUUID()});
        const context = {...entry, campaignId, sessionId};
        window.VTTTableContext = context;
        try { sessionStorage.setItem(`vtt.table.context.v1.${campaignId}.${sessionId}`, JSON.stringify(context)); } catch (_) {}
        return context;
    }

    static async ensureTableContext(campaignId, sessionId, mode = 'player', force = false) {
        const key = `vtt.table.context.v1.${campaignId}.${sessionId}`;
        let saved = window.VTTTableContext;
        if (!saved || saved.campaignId !== campaignId || saved.sessionId !== sessionId) {
            try { saved = JSON.parse(sessionStorage.getItem(key) || 'null'); } catch (_) { saved = null; }
        }
        if (saved && !force) {
            window.VTTTableContext = saved;
            return saved;
        }
        const tab = crypto.randomUUID();
        const entry = await this.makeAuthRequest(
            `/api/play/campaigns/${campaignId}/sessions/${sessionId}/contexts`, 'POST', {mode, tab});
        const context = {...entry, campaignId, sessionId};
        window.VTTTableContext = context;
        try { sessionStorage.setItem(key, JSON.stringify(context)); } catch (_) { /* memory-only works */ }
        return context;
    }
}

// `class` declarations don't attach to `window` the way `var`/`function` do -
// book-scene.js reads window.Auth (loadSceneSnapshot, loadDashboardSnapshot,
// and everywhere else it calls window.Auth.makeAuthRequest/getCurrentUser),
// so without this every one of those calls silently fails its `!window.Auth`
// guard and falls back to empty data.
window.Auth = Auth;
