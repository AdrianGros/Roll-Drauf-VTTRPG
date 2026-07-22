# DAD-M Soll: Book UI Polish Wave P1 System Normalization

Date: 2026-04-01
Status: approved

## Zielbild

Die Buchfamilie soll fuer Spread-, Focus- und Workspace-Routen aus einer klareren gemeinsamen Stilbasis lesen.

## Soll-Zustand

- `book-scene.css` traegt die wiederkehrenden Shell-Muster fuer `route`, `focus`, und `workspace`.
- `character-sheet` behaelt nur noch die wirklich eigenen Regeln fuer seine Ribbon-/Frame-Besonderheiten.
- `play` behaelt nur noch die wirklich eigenen Regeln fuer Tisch-, Map- und Sidebar-Dichte.
- `main`, `camera`, `page`, `sticky ribbon`, und die Grundabstaende wirken ueber die Route-Familien sichtbar konsistenter.

## Nicht Teil dieses Slices

- kein neuer grosser Motion-Redesign
- keine tiefere Runtime-Zusammenfuehrung von `character-sheet` oder `play` in `book-scene.js`
- keine neue Funktionslogik fuer Campaign-/Character-Aktionen
