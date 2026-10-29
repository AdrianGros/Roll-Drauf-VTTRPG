# Main navigation and Kartenwerkstatt rollout — 2026-10-26

## Discover

Input: Publish the Kartenwerkstatt as a main VTT destination, make the top navigation consistent across the main menus, move Abmelden below the username on the right, and show a completed-session counter.

Current state: `/mapmaker` redirects to the standalone editor but has no main navigation entry. BookScene, play, character sheet, Creation Engine, and Regelwerk each render a different top menu. BookScene has Abmelden inside its ribbon. The dashboard home snapshot omits archived sessions, so it cannot reliably supply a lifetime completed-session count. The running VPS image predates the dirty worktree.

Inventory: `vtt/static/mapmaker/`, `vtt/templates/mapmaker.html`, book route templates and their ribbon markup, `vtt/endpoints/dashboard_home.py`, `vtt/static/js/auth.js`, CE and Regelwerk capability navigation. Live deployment is Docker Compose project `migration-production` with app image `roll-drauf-vtt-app:eagle-fd76ec8`.

Dependencies: JWT cookie authentication, existing dashboard campaign visibility rules, CE capability endpoint, Regelwerk availability endpoint, current live Docker image. No schema migration.

Risks/assumptions: Medium: local worktree has unrelated changes; deploy as a thin image derived from the running image and overlay only this feature. Low: there is no attendance ledger, so “sessions played” means completed sessions in campaigns currently visible to the signed-in user. Public Regelwerk pages show Anmelden until signed in. Authentication entry pages retain their own login navigation.

Next step: Apply the shared navigation contract and isolated release design below.

## Apply

Target: One ordered top ribbon on protected VTT surfaces and public Regelwerk pages: Übersicht, Kampagnen, Charaktere, Karten, Creation Engine (capability gated), Regelwerk (availability gated), Compendium, Spieltisch. The active destination is visibly marked. Spieltisch opens the existing BookScene launcher, including when entered from another page. A compact right-side account memo shows the username, completed-session count, and Abmelden below; signed-out public pages show Anmelden. The Kartenwerkstatt keeps its editor controls and adds the same global ribbon above them. `/mapmaker` remains the stable user-facing route.

Interface: `GET /api/dashboard/navigation` returns `{user: {username}, completed_session_count: number}` under JWT, private/no-store. Count includes archived sessions whose status is `completed` or `ended`, in currently visible campaigns, excluding cancelled sessions. The shared browser module hydrates existing ribbon containers and dynamically rendered BookScene pages; capability links retain their existing gate checks.

Acceptance: all listed surfaces expose the same ordered destinations; the account memo places Abmelden under the username and displays the authenticated count; public Regelwerk shows Anmelden; map editor loads through `/mapmaker` and remains usable; mobile nav stays reachable by horizontal scrolling; targeted browser/API tests pass. Deploy only approved feature files on top of the exact live image, verify public route and app health, then monitor.

Tradeoff: full-page links replace some ribbon-specific page-turn transitions. The editor remains browser-local storage with file export, as before.

Deploy handoff: implement the component and endpoint, run focused tests, build an image FROM the live image with only the selected overlays, switch only the Compose app image, and smoke-test the live site. Roll back to the previous image if health or route checks fail.

## Deploy

Implemented: shared ribbon and account memo in `vtt/static/js/vtt-main-nav.js` and `vtt/static/css/vtt-main-nav.css`; added the component to the book, play, Creation Engine, Regelwerk, and editor entry pages; added `GET /api/dashboard/navigation`; put the existing editor behind the `/mapmaker` main-nav link. No database migration. Production runs `roll-drauf-vtt-app:mapmaker-nav-20261026-v2`, a thin overlay on the image that was running before this change. The unrelated modified worktree files were not bundled into that image. The previous Compose configuration is preserved at `/srv/migration/2026-10-07/setup/production.compose.json.pre-mapmaker-nav-20261026.bak`.

Verification: 27 navigation tests passed, followed by a passing cross-page Spieltisch launcher test. The mapmaker suite passed all earlier cases and found an anonymous Flask-entry console error at its final test; after the fix, the affected Flask-entry and desktop/mobile starter tests passed (3), as did the focused navigation/memo tests (4). Container compilation and asset presence checks passed. The live `/mapmaker`, editor asset, shared script, dashboard, and Regelwerk returned HTTP 200; anonymous navigation API returned the expected 401. The completed-session query ran successfully against the production database from the app container without changing data. Chromium checked the live map page at 1440px and 390px with a rendered canvas, active Karten link, no page overflow, and no console errors. Final phone-width Chromium checks confirmed the eight ordered destinations and guest account action on the live map and Regelwerk pages, with no page errors.

Acceptance: map route live; consistent ordered links on the checked surfaces; account memo and logout placement verified in local authenticated browser tests; completed-session count verified for archived completions and campaign isolation; mobile navigation horizontally scrolls without document overflow.

## Monitor

Observed: app container is running on the final image and recent logs show no errors. The public map editor and Regelwerk navigation work in a real browser after the final deployment.

Residual risk: an authenticated live browser session was not available, so the live counter value and logout click were validated through the local authenticated browser/API suite rather than a production account. The counter reflects completed sessions in campaigns currently visible to the user, because the schema has no attendance ledger. The map editor still saves locally in the browser and exports a file for backup.

Recommended next action: use a normal signed-in account to review the live counter and cross-page navigation, then leave the release in place if the account-specific behavior matches the local tests.
