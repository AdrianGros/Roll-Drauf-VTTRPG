# DADM Apply: Campaigns + Characters Book Scene

Date: 2026-04-01
Status: completed

## Umgesetzte Aenderungen

- `vtt_app/static/js/book-scene.js`
  - von Dashboard-Pilot auf generische Mehrseiten-Buchszene erweitert
  - interne Route-Transitions fuer `dashboard`, `campaigns`, `characters`
  - gemeinsame Snapshot-Ladung fuer Kampagnen- und Charakterdaten
  - route-spezifische Seitenmarkups fuer Dashboard, Campaigns und Characters

- `vtt_app/static/css/book-scene.css`
  - neue Styles fuer Stat-Strips, Ledger, Notiz-Panels und breite Widget-Felder
  - responsive Regeln fuer die neuen Kapitel-Layouts

- `vtt_app/templates/campaigns.html`
  - Direktroute auf Book-Scene-Bootstrap umgestellt
  - klassisches Layout bei aktivem Szenenmodus ausgeblendet

- `vtt_app/templates/characters.html`
  - Direktroute auf Book-Scene-Bootstrap umgestellt
  - klassisches Layout bei aktivem Szenenmodus ausgeblendet

- `vtt_app/templates/dashboard.html`
  - Bootstrap auf gemeinsame `sceneSnapshot` / `sceneUser`-Daten umgestellt
