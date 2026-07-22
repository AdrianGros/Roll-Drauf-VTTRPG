# DADM Monitor: Campaigns + Characters Book Scene

Date: 2026-04-01
Status: live_validated

## Verifiziert

- `git diff --check` laeuft sauber.
- Live-Auslieferung von `/static/js/book-scene.js` enthaelt jetzt `buildCampaignsMarkup`, `buildCharactersMarkup`, `loadSceneSnapshot`, `bootstrapRoute` und `transitionToRoute`.
- Live-HTML von `/campaigns` enthaelt `campaigns-route-book-scene`, `campaignsSceneStatus` und `bootstrapCampaignsScene`.
- Live-HTML von `/characters` enthaelt `characters-route-book-scene`, `charactersSceneStatus` und `bootstrapCharactersScene`.

## Offene Monitoring-Punkte

- Browser-Pruefung der wahrgenommenen Seitenwechsel innerhalb des Buchobjekts aus einer echten eingeloggten Session.
- Visuelle Pruefung von Mobilansicht und Reduced-Motion-Verhalten.
- Bewertung, ob die alten Detail-/Modal-Funktionen im naechsten Slice in dieselbe Buchsprache gezogen werden sollen.

## Technische Einschraenkung

- `node` ist in der aktuellen Umgebung nicht installiert, daher kein `node --check` fuer `book-scene.js`.
