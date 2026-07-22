# DADM Soll: Campaigns + Characters Book Scene

Date: 2026-04-01
Status: completed

## Zielbild

- `dashboard`, `campaigns` und `characters` leben als Kapitel im selben persistenten Buchobjekt.
- Klick auf Ribbon oder Tiles fuehrt zu internem Seitenwechsel statt zu einem normalen App-Sprung.
- Reload oder Direktaufruf von `/campaigns` und `/characters` bootet dieselbe in-book Darstellung.
- Die Seiten behalten die Mockup-Logik: Menueband oben, inhaltliche Hauptfelder auf der Seite, breite Arbeitsflaeche unten.

## Nicht-Ziel in diesem Slice

- Vollstaendige Neuumsetzung aller alten Campaign-/Character-Management-Interaktionen.
- Character-Sheet Focus-Mode oder Play-Workspace.
