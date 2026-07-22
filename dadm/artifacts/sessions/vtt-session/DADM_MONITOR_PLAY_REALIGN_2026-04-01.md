# DAD-M Monitor: Play Realign

Date: 2026-04-01
Status: live_validated

## Verifiziert

- `git diff --check` ist sauber.
- Die relevanten Status-IDs (`sessionTitle`, `modeBadge`, `roleBadge`, `readOnlyBadge`, `sessionStatusPill`) sind eindeutig vorhanden.
- Live-HTML von `/play` enthaelt jetzt:
  - `play-workspace-realign`
  - `play-workspace-page`
  - `book-dashboard-ribbon`
  - die neuen Titel-/Status-Hooks in der Buchseiten-Huelle

## Offene Monitoring-Punkte

- Visuelle Browser-Pruefung mit echter Session und aktiver Karte.
- Bewertung, ob Ribbon/Titlebar im Live-Spielbetrieb noch kompakter werden sollten.
- Mobil-/Tablet-Test fuer Sidebar und Kartenhoehe.
