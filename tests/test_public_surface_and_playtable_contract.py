"""Emergency public-surface and Playtable empty-state contracts."""

from pathlib import Path

import pytest

from vtt import create_app


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAY_TEMPLATE = REPO_ROOT / "vtt" / "templates" / "play.html"
PLAY_UI = REPO_ROOT / "vtt" / "static" / "js" / "play-ui.js"


@pytest.fixture
def app():
    return create_app(config_name="testing")


@pytest.fixture
def client(app):
    return app.test_client()


def test_root_is_the_app_front_door_not_a_showcase(client):
    """The root path leads into the product, not into a marketing landing page.

    The `/showcase` surface existed for two days (a6619f7) so the Beyond20
    maintainers had something public to look at. It is gone on purpose: this
    is a VTT, and its front door is the way in, not a pitch about itself.
    """
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (301, 302, 308)
    assert response.headers["Location"].endswith("/login.html")


@pytest.mark.parametrize("path", ["/showcase", "/showcase.html"])
def test_showcase_surface_stays_removed(client, path):
    """No showcase page is served anywhere.

    These paths do not 404: serve_static() falls back to login.html for every
    unknown path, so an unrouted URL silently renders the login page (a
    pre-existing soft-404 this test does not change). What matters here is
    that the landing/pitch content is gone, so the assertion names the
    content rather than the status code.
    """
    response = client.get(path, follow_redirects=False)
    html = response.get_data(as_text=True)

    assert "Beyond20-Integration ansehen" not in html
    assert "Der offene Spieltisch" not in html
    assert 'id="login-content"' in html


def test_beyond20_review_page_is_public_and_names_the_supported_contract(client):
    response = client.get("/beyond20.html")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for event_name in (
        "Beyond20_RenderedRoll",
        "Beyond20_UpdateHP",
        "Beyond20_UpdateConditions",
        "Beyond20_UpdateCombat",
    ):
        assert event_name in html
    assert "Sessiondaten geschützt" in html


def test_beyond20_page_walks_players_through_manual_setup(client):
    """No automation is possible (Beyond20 declares no externally_connectable
    origin, so a webpage cannot write into its settings) -- the honest
    fallback is a correct, copy-pasteable manual tutorial. The exact labels
    below are the real strings from Beyond20's own options UI, not
    paraphrased, so a player can actually find them.
    """
    response = client.get("/beyond20.html")
    html = response.get_data(as_text=True)

    assert "https://vtt.roll-drauf.de/*" in html
    assert "beyond20CopyBtn" in html
    for real_beyond20_ui_label in (
        "Advanced Options",
        "List of custom domains to load Beyond20",
        "Apply",
    ):
        assert real_beyond20_ui_label in html


def test_playtable_beyond20_hint_sends_players_to_the_correct_tutorial():
    """The old inline hint told players to enter the bare domain
    "vtt.roll-drauf.de" as Beyond20's Custom Domain value -- verified against
    Beyond20's own source (src/common/settings.js) that field requires a full
    URL with protocol and a wildcard (e.g. "https://vtt.roll-drauf.de/*") or
    Beyond20 rejects the entry outright. A player following the old text
    literally would never receive a single roll. Duplicate-instructions risk
    is why the panel now links to the one verified tutorial (/beyond20.html)
    instead of repeating the steps inline.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")

    assert "/beyond20.html" in template
    assert "vtt.roll-drauf.de</strong> als Custom Domain eintragen" not in template


def test_playtable_add_page_offers_upload_or_copy_never_a_dead_end():
    """'Hinzufügen' is documented (2026-08-25) as the one way to add a page,
    with an explicit rule it must never end in the old dead end this test
    used to assert on ('Alle vorhandenen Kampagnenkarten sind bereits
    Seiten' + a disabled control). That dead end is gone on purpose: a map
    already used elsewhere is now offered for copy rather than blocking.
    See docs/PLAYTABLE_AUDIT_2026-08-25.md and tests/test_layer_add_flow.py,
    which cover the copy behaviour itself end-to-end against the backend.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'id="layerAddStatus"' in template
    assert 'role="status"' in template
    assert 'id="layerAddUpload"' in template
    assert 'id="layerAddCopy"' in template
    assert "Alle vorhandenen Kampagnenkarten sind bereits Seiten" not in script
    assert "wird kopiert" in script


def test_playtable_uses_one_upper_control_strip_for_page_and_zoom_controls():
    """The map must not carry a second chrome bar over its artwork."""
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")

    strip_start = template.index('class="book-dashboard-titlebar play-status-strip"')
    controls_start = template.index('class="stage-topbar"')
    map_start = template.index('<section class="stage">')

    assert strip_start < controls_start < map_start
    assert template.count('class="stage-topbar"') == 1
    assert template.count('id="activePagePill"') == 1
    assert template.count('id="btnZoomFit"') == 1


def test_playtable_keeps_session_title_in_header_and_tools_under_map():
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")

    status_start = template.index('class="book-dashboard-titlebar play-status-strip"')
    toolbar_start = template.index('<aside class="left-toolbar"')
    shell_start = template.index('<div class="book-shell-frame book-workspace-shell">')
    sidebar_start = template.index('<aside class="right-sidebar"')

    assert status_start < shell_start < toolbar_start < sidebar_start
    assert template.count('<aside class="left-toolbar"') == 1
    assert 'id="sessionTitleHeader"' in template
    assert "grid-template-columns: 1fr;" in template
    assert "grid-template-rows: minmax(0, 1fr) auto;" in template


def test_playtable_eye_control_activates_pages_without_a_second_activate_row():
    """8e856de removed an earlier visibility toggle specifically because it
    reused the same eye glyph (&#128065;) as the activate button -- two
    look-alike eye icons on one row, ambiguous which did what. S01 brought
    the visibility toggle back (Apply decision: needed for the "view-only"
    actions-menu item), but on a lock/unlock icon that shares no glyph with
    activateIcon. The actual invariant this test protects is "no second
    control reuses the activate icon", not "visibility can never return".
    """
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'title="Seite aktivieren"' in script
    assert 'aria-label="Seite aktivieren"' in script
    assert 'Aktivieren</button>' not in script
    assert '_activateLayer(Number(button.dataset.layerId))' in script
    activate_icon_uses = script.count('const activateIcon = "&#128065;"')
    assert activate_icon_uses == 1
    assert 'const visibleIcon = layer.is_player_visible ? "&#128275;" : "&#128274;"' in script


def test_playtable_floating_widgets_are_draggable_by_their_header():
    """F5: the four independent floating panels (layers, turn order,
    tokens, the token-create popup) are freely movable little windows,
    dragged by their existing header/title bar, desktop only.

    Cheap contract test in this file's own style -- substring assertions
    against the raw template/JS source, not full Playwright geometry. It
    checks: one shared drag-enable helper exists and is wired in for
    exactly the four known widget ids, none of the four lost its
    header/toggle element (the drag handle), and the helper respects the
    1040px mobile "sheet" breakpoint instead of fighting it.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    # All four panels still exist, each with a header usable as a drag
    # handle (the three collapsible widgets keep their .widget-toggle;
    # the token-create popup has no collapse feature but does have a
    # plain <h3> header).
    assert '<div id="layersWidget" class="floating">' in template
    assert '<div id="turnOrderWidget" class="floating">' in template
    assert '<div id="tokenWidget" class="floating">' in template
    assert 'id="tokenCreatePanel" class="floating"' in template
    assert '<h3 class="widget-toggle" data-widget="layersWidget"' in template
    assert '<h3 class="widget-toggle" data-widget="turnOrderWidget"' in template
    assert '<h3 class="widget-toggle" data-widget="tokenWidget"' in template
    assert "<h3>Token platzieren</h3>" in template

    # One shared helper (mirroring _bindWidgetToggles' shape), not four
    # bespoke drag implementations -- applied uniformly to all four ids.
    assert "_bindWidgetDragging()" in script
    widget_ids_literal = (
        '["layersWidget", "turnOrderWidget", "tokenWidget", "tokenCreatePanel"]'
    )
    assert widget_ids_literal in script
    for widget_id in ("layersWidget", "turnOrderWidget", "tokenWidget", "tokenCreatePanel"):
        assert widget_id in widget_ids_literal

    # Desktop only: the mobile "sheet" layout forces .floating panels to
    # position:static below 1040px (see the .table-sheet .floating rule in
    # play.html) -- the drag helper must guard against that breakpoint
    # instead of removing or overriding it.
    assert ".table-sheet .floating" in template
    assert "position: static !important;" in template
    assert 'const WIDGET_DRAG_MIN_WIDTH_MEDIA = "(min-width: 1040px)";' in script
    assert "window.matchMedia(WIDGET_DRAG_MIN_WIDTH_MEDIA)" in script
    assert "desktopMedia.matches" in script

    # Persisted per widget id in sessionStorage, matching this file's own
    # naming convention for session-scoped UI state (*_STORAGE_KEY).
    assert 'const WIDGET_POSITION_STORAGE_PREFIX = "vtt.play.widget-pos.";' in script
    assert "window.sessionStorage.setItem(" in script
    assert "window.sessionStorage.getItem(" in script

    # A drag must not also fire the existing collapse/expand click handler
    # on the same header -- the two features have to coexist.
    assert "suppressToggle" in script


def test_playtable_scene_directory_has_search_duplicate_and_keyboard_nav():
    """S01 (Apply-approved slice, docs/PLAYTABLE_FEATURE_RESEARCH_01_SCENES_2026-08-27.md):
    client-side search/filter, a duplicate action reusing the existing
    add-layer-with-allow_copy endpoint (no new backend route), roving
    tabindex + arrow/Home/End keyboard navigation per the W3C APG listbox
    pattern, and reopening the directory scrolls the active layer into view.
    Cheap contract test in this file's style -- substring assertions against
    the raw template/JS source.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'id="layerSearchInput"' in template
    assert 'role="listbox"' in template
    assert 'this._layerFilterText = searchInput.value' in script

    assert 'data-act="duplicate"' in template or 'data-act="duplicate"' in script
    assert '_duplicateLayer(layerId)' in script
    assert 'this.api.addLayer(this.campaignId, this.sessionId, layer.campaign_map_id' in script

    assert 'role="option"' in script
    assert '_handleLayerListKeydown(event)' in script
    for key in ('"ArrowDown"', '"ArrowUp"', '"Home"', '"End"'):
        assert key in script

    assert 'layer-row.active-row' in script
    assert 'scrollIntoView' in script

    assert '#layersWidget .layer-icon-btn' in template
    assert '#layersWidget .layer-row { min-height: 44px; }' in template


def test_playtable_app_menu_exists_and_is_distinct_from_the_sidebar_toggle():
    """S02 (Apply-approved slice, docs/PLAYTABLE_FEATURE_RESEARCH_02_APP_MENU_2026-08-27.md):
    the application command menu (Return to Campaign / Leave Session / Help)
    is a genuinely separate surface from #btnSidebarToggle, which already
    exposes Journal/Chat/Tools/Session WORKSPACE CONTENT under its own
    "Menü" label + hamburger icon -- reusing that label/icon for the new
    menu would recreate exactly the label-collision class this session
    already fixed once for icons (the S01 eye/lock mixup). Also checks the
    two destructive/informational actions use native <dialog> (the
    good_examples' explicit recommendation) rather than a hand-rolled modal.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'id="appMenu"' in template
    assert 'role="menu"' in template
    assert 'id="appMenuReturn"' in template
    assert 'id="appMenuHelp"' in template
    assert 'id="appMenuLeave"' in template

    # btnBack keeps its own label ("Zurück") -- it must NOT say "Menü",
    # which #btnSidebarToggle already owns for a different surface.
    back_button_start = template.index('id="btnBack"')
    back_button_markup = template[back_button_start:template.index("</button>", back_button_start)]
    assert "Menü" not in back_button_markup
    assert 'aria-haspopup="true"' in back_button_markup
    assert 'aria-controls="appMenu"' in back_button_markup

    assert '<dialog id="appMenuLeaveDialog"' in template
    assert '<dialog id="appMenuHelpDialog"' in template

    assert '_bindAppMenu()' in script
    assert 'this._toggleAppMenu' in script
    for key in ('"ArrowDown"', '"ArrowUp"', '"Home"', '"End"', '"Escape"'):
        assert key in script

    # Closes the sidebar rather than stacking overlays (acceptance
    # criterion), and disables Leave (not hides it) in read-only mode with
    # an explanatory tooltip -- resolves the research doc's own internal
    # contradiction (Apply-handoff recommendation vs Acceptance Criteria)
    # in favor of the stricter, already-established read-only convention.
    assert '.right-sidebar")?.classList.remove("is-open")' in script
    assert "leaveItem.disabled = this.readOnly" in script

    # Sits above #sheetDrawer (the previous highest floating layer, z-index
    # 340) so the menu is always reachable.
    assert "z-index: 350;" in template


def test_playtable_measure_tool_is_available_read_only_and_clears_on_switch():
    """S03 (Apply-approved slice, docs/PLAYTABLE_FEATURE_RESEARCH_03_MAP_TOOLS_2026-08-27.md):
    a waypoint measurement tool reusing the existing tool-rail/world-coordinate
    machinery, client-only and transient (no server mutation, no persistence,
    no broadcast to other clients -- Apply decision, doc section 9's own
    permission contract). Must stay available to read-only users, unlike
    the token tool right next to it which the same file already correctly
    hides for that role.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'data-tool="measure"' in template
    assert 'aria-label="Entfernung messen"' in template
    assert 'id="btnMeasureSnap"' in template
    assert 'id="measureLayer"' in template
    assert 'id="measureAnnounce"' in template
    assert 'role="status" aria-live="polite"' in template

    # The measurement interaction handlers must never gate on this.readOnly
    # -- that's the token-placement tool's job, not this one's.
    measure_section_start = script.index("S03 measurement tool")
    measure_section_end = script.index("_renderMeasurement() {", measure_section_start)
    measure_section_end = script.index("}\n", script.index("announce.textContent", measure_section_end)) + 2
    measure_section = script[measure_section_start:measure_section_end]
    assert "this.readOnly" not in measure_section

    assert "_cancelMeasurement()" in script
    assert 'if (toolName !== "measure") {' in script

    # Nested Escape/Ctrl+Z pop the last waypoint; gridless scenes disable
    # snapping instead of snapping to zero.
    assert "_removeLastWaypoint()" in script
    assert '!gridSize) return point;' in script
    assert 'event.ctrlKey || event.metaKey' in script

    # Touch requires an actual long-press, not a tap -- distinguished from
    # mouse so panning/scrolling on a tablet doesn't drop stray waypoints.
    assert 'this._measurePointerIsTouch = event.pointerType === "touch"' in script
    assert "550)" in script  # the long-press timer duration

    # Waypoints outside the map are clamped to its edge, not dropped.
    assert "Math.max(0, Math.min(width," in script


def test_playtable_observed_token_gets_a_readonly_summary_not_nothing():
    """S04 (Apply-approved slice, docs/PLAYTABLE_FEATURE_RESEARCH_04_TOKEN_HUD_2026-08-27.md):
    a player selecting a token they don't own and can't edit used to see
    NOTHING beyond the one-line "Ausgewählt: NAME" summary -- no HP, no
    indication it isn't theirs. Full HUD repositioning-to-the-token-marker
    (the doc's fuller ambition) was deliberately deferred: this app already
    has an established draggable-floating-panel convention for #tokenWidget
    (F5/S01), and continuously re-anchoring a panel to a moving/zooming
    world-space point is a materially larger, jankier undertaking than
    reusing that existing pattern -- documented as an Apply-phase deviation
    from the research doc's literal "anchored near the marker" wording,
    not a silent scope cut.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'id="tokenSelectionReadonly"' in template
    assert 'id="tokenConnectionNotice"' in template
    assert "showReadonly = Boolean(selectedToken) && !canEditSelected" in script
    # 0 HP must still render as real data, not fall through to "unbekannt"
    # via a truthiness check that treats 0 as missing.
    assert "hasHpData = selectedToken.hp_current != null || selectedToken.hp_max != null" in script
    assert "nicht dein Charakter" in script

    # Delete confirmation states what it affects, not just "really delete?".
    assert "entfernt ihn für alle am Tisch" in script

    # Reconnecting indicator: this app had NO connect/disconnect handling
    # anywhere before this slice.
    assert 'connect: () => { this._connectionLost = false;' in script
    assert 'disconnect: () => { this._connectionLost = true;' in script


def test_playtable_conditions_picker_merges_metadata_instead_of_overwriting():
    """S05 (Apply-approved slice, docs/PLAYTABLE_FEATURE_RESEARCH_05_STATUSES_2026-08-27.md):
    the conditions/status picker reachable from the token HUD. The server
    applies a metadata_json patch as a whole-value overwrite (confirmed by
    reading handle_token_update: `setattr(token, key, value)`, not a merge)
    -- sending a bare {conditions: [...]} patch would silently wipe
    image_url and anything else already on the token. This is the specific
    bug that would have shipped without checking that first.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    assert 'id="btnTokenConditions"' in template
    assert 'id="conditionsPopover"' in template
    assert 'id="conditionsList"' in template
    assert 'id="btnConditionsClearAll"' in template
    assert 'role="dialog" aria-label="Zustände"' in template

    assert "const mergedMetadata = { ...(token.metadata_json || {}), conditions: nextConditions }" in script
    assert "CONDITION_CATALOG" in script
    assert len([line for line in script.splitlines() if '{ id: "' in line and 'label:' in line]) == 16

    # Clear-all names the token and states the count, not a bare "really?".
    assert 'window.confirm(`Alle ${current.length} Zustände von "${token.name}" entfernen?`)' in script

    # Popover is non-modal (Apply decision) -- light-dismiss + Escape, same
    # pattern as the S02 app menu, not a native <dialog>.
    assert "onOutsideClick" in script
    assert "closePopover" in script


def test_playtable_turn_order_announces_and_syncs_with_token_selection():
    """S06 (Apply-approved slice, docs/PLAYTABLE_FEATURE_RESEARCH_06_COMBAT_2026-08-27.md):
    the combat turn-order widget gets a live-region announcement on turn
    change (the research doc's own HIGH-severity accessibility risk),
    "Zug m von n" in the summary, click/keyboard selection that stays in
    sync bidirectionally with map token selection, and pending-disable on
    the DM control buttons so a slow network can't double-fire a turn
    advance. Most of the combat BACKEND (CombatEncounter, version-conflict
    retry, hidden-participant filtering) already existed before this slice
    -- current-state check found seven "new DM-only endpoints" the research
    doc proposed were already built and working.
    """
    script = PLAY_UI.read_text(encoding="utf-8")
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")

    assert 'id="turnOrderAnnounce"' in template
    assert 'role="status" aria-live="polite"' in template
    assert "_announceTurnOrderIfChanged" in script
    assert "this._lastAnnouncedTurnActorId === activeTokenId" in script

    assert "Zug ${activeIndex + 1} von ${order.length}" in script

    assert "_bindTurnItemRow" in script
    assert 'row.addEventListener("click", () => this._selectToken(tokenId))' in script
    assert "this._renderTurnOrder();" in script  # called from _selectToken, completes the bidirectional sync

    assert "_withCombatButtonPending" in script
    assert 'if (button) button.disabled = true;' in script


def test_playtable_selecting_a_token_surfaces_its_controls():
    """F4 Gap B: clicking a token on the map already drew a real selection
    ring and updated #tokenSelectionSummary/#tokenSelectionDetail text --
    but never actually opened the #tokenWidget panel those live in, so on
    both desktop (panel starts collapsed) and mobile (panel lives inside a
    closed #tableSheet) the controls stayed invisible unless the widget
    already happened to be open.

    _openTokenMenu already implemented "expand #tokenWidget, and open
    #tableSheet via #btnTableSheet if hidden" for the toolbar's
    place-a-token tool button. Fixed by factoring that into a shared
    _revealTokenWidget() helper and calling it from _selectToken() too, on
    an actual selection (not a deselection).

    Cheap contract test in this file's own style (see the F5 widget-drag
    test above) -- substring assertions against the raw template/JS
    source, not full Playwright geometry.
    """
    template = PLAY_TEMPLATE.read_text(encoding="utf-8")
    script = PLAY_UI.read_text(encoding="utf-8")

    # One shared reveal helper, not two copies of the same panel-opening
    # logic -- both the "place a new token" tool button and selecting an
    # existing token call it.
    assert "_revealTokenWidget()" in script
    assert script.count("_revealTokenWidget()") >= 3  # definition + 2 call sites
    assert "_openTokenMenu() {\n            this._revealTokenWidget();" in script

    # _selectToken() calls the reveal helper when a token was actually
    # selected, not on deselection (_selectToken(null) is how the map
    # click-to-deselect handler clears the selection).
    select_token_start = script.index("_selectToken(tokenId, repaintMap = false) {")
    select_token_body = script[select_token_start:select_token_start + 700]
    assert "this.selectedTokenId = searchId;" in select_token_body
    assert "this._revealTokenWidget();" in select_token_body
    # The reveal call must sit in the "found a real id" branch, after the
    # assignment above and before the function falls through to the
    # shared find/render tail that also runs for a deselect.
    assign_index = select_token_body.index("this.selectedTokenId = searchId;")
    reveal_index = select_token_body.index("this._revealTokenWidget();")
    assert assign_index < reveal_index

    # A rename control now exists in #tokenSelectionDetail, gated behind
    # the exact same owner-or-DM condition as the pre-existing image-set
    # button (both controls live in the same hidden-toggled container).
    detail_start = template.index('id="tokenSelectionDetail"')
    image_set_index = template.index('id="btnTokenImageSet"')
    detail_section = template[detail_start:image_set_index]
    assert 'id="tokenNameInput"' in detail_section
    assert 'id="btnTokenNameSet"' in detail_section

    assert "_setSelectedTokenName()" in script
    assert 'document.getElementById("btnTokenNameSet")' in script
    assert 'document.getElementById("tokenNameInput")' in script
    # The rename patch reuses the same server-accepted "name" field the
    # socket layer already allows any owning player to set (no new server
    # logic was needed or added for this).
    assert "{ name: nextName }" in script
