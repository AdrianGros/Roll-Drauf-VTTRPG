(function () {
    'use strict';

    let availabilityPromise = null;

    function availability() {
        if (!availabilityPromise) {
            availabilityPromise = fetch('/api/rulesets/main', { credentials: 'same-origin' })
                .then((response) => response.ok ? response.json() : { available: false })
                .catch(() => ({ available: false }));
        }
        return availabilityPromise;
    }

    async function hydrate(root = document) {
        const nodes = Array.from(root.querySelectorAll('[data-regelwerk-nav]'));
        if (!nodes.length) return false;
        const state = await availability();
        nodes.forEach((node) => {
            if (!state.available) {
                node.hidden = true;
                node.removeAttribute('href');
                node.setAttribute('aria-disabled', 'true');
                return;
            }
            node.hidden = false;
            node.href = state.readerUrl || '/regelwerk';
            node.setAttribute('aria-disabled', 'false');
            node.textContent = 'Regelwerk · Vorschau';
        });
        return Boolean(state.available);
    }

    window.RegelwerkNavigation = { hydrate };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => hydrate(document), { once: true });
    } else {
        hydrate(document);
    }
}());
