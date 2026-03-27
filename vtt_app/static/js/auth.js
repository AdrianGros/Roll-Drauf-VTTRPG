/**
 * Cookie-based authentication utilities for frontend.
 */

class Auth {
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
        const user = await this.getCurrentUser();
        if (!user) {
            window.location.href = redirectTo;
            return null;
        }
        return user;
    }

    static async redirectIfAuthenticated(target = '/dashboard') {
        const user = await this.getCurrentUser();
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

        window.location.href = '/login.html';
    }

    static async makeAuthRequest(url, method = 'GET', body = null, retryOn401 = true) {
        const includeJson = body !== null;
        const options = {
            method,
            credentials: 'include',
            headers: this.buildHeaders(method, includeJson)
        };

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
            throw new Error(error.error || 'API request failed');
        }

        const contentType = response.headers.get('Content-Type') || '';
        if (!contentType.includes('application/json')) {
            return null;
        }

        return response.json();
    }
}
