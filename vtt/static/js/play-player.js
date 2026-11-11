// Independent Player composition. It never fetches or installs DM controls.
window.PlayPlayerSurface = {
    compose(ui) {
        document.querySelectorAll('[data-dm-slot]').forEach((slot) => slot.remove());
        document.querySelectorAll('#rollVisibility option[value="blind"], #rollVisibility option[value="self"]')
            .forEach((option) => option.remove());
        // Owners retain their token's sight-range setting; DM geometry tools
        // and their handlers live exclusively in the DM composition.
        document.getElementById('btnTokenSightRangeSet')?.addEventListener('click',
            () => ui._setSelectedTokenSightRange());
    },
    composeSeatSwitch(payload) {
        const template = document.querySelector('template[data-seat-switch]');
        if (!template) return;
        if (payload.can_switch_seat) template.replaceWith(template.content.cloneNode(true));
        else template.remove();
    }
};
