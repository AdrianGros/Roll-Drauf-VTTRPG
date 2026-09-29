/** Shared, non-provisioning capability check for Creation Engine entry points. */
(function () {
    'use strict';

    let capability;

    async function available() {
        if (!capability) {
            capability = (async () => {
                try {
                    const result = await window.Auth.makeAuthRequest('/api/dashboard/capabilities');
                    return result?.authoring_available === true;
                } catch (_) {
                    return false;
                }
            })();
        }
        return capability;
    }

    async function hydrate(root = document) {
        const entries = Array.from(root.querySelectorAll('[data-creation-engine-nav]'));
        if (!entries.length) return;
        entries.forEach((entry) => {
            if (entry.dataset.creationEngineBound) return;
            entry.dataset.creationEngineBound = 'true';
            if (!entry.hasAttribute('role')) entry.setAttribute('role', 'link');
            entry.addEventListener('click', (event) => {
                if (entry.getAttribute('aria-disabled') === 'true') {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                }
            });
        });
        const enabled = await available();
        entries.forEach((entry) => {
            entry.setAttribute('aria-disabled', String(!enabled));
            entry.textContent = enabled ? 'Creation Engine' : 'Creation Engine · nicht verfügbar';
            entry.title = enabled
                ? 'Homebrew-Völker, Merkmale und weitere Inhalte erstellen'
                : 'Die Creation Engine ist für dieses Konto auf diesem Server nicht verfügbar.';
            if (enabled) {
                const characterId = Number(entry.dataset.creationEngineCharacterId);
                if (window.self !== window.top) entry.setAttribute('target', '_top');
                entry.setAttribute('href', '/api/ce/authoring' + (Number.isInteger(characterId) && characterId > 0 ? `?character_id=${characterId}` : ''));
            } else entry.removeAttribute('href');
        });
    }

    window.CreationEngineNavigation = { hydrate };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => hydrate());
    } else {
        hydrate();
    }
}());
