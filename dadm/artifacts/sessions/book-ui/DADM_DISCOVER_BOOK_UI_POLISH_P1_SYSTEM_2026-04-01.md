# DAD-M Discover: Book UI Polish Wave P1 System Normalization

Date: 2026-04-01
Status: completed

## Ausgangslage

- `dashboard`, `campaigns`, und `characters` lesen bereits stark aus `book-scene.css`.
- `character-sheet` und `play` nutzen dieselbe Buchsprache, ziehen aber zentrale Geometrie und Header-Abstaende noch ueber route-lokale Inline-CSS glatt.
- Dadurch entsteht Stil-Drift: gleiche Muster wie `route page`, `focus page`, `workspace page`, `sticky topbar`, und `main width` werden mehrfach definiert.

## Problem

- dieselbe Buchfamilie wird in mehreren Templates leicht unterschiedlich beschrieben
- die naechste Mobile-/Motion-/Small-Height-Welle wuerde sonst wieder an mehreren Stellen parallel gefixt
- die Seite fuehlt sich zwar schon zusammengehoerig an, ist aber systemisch noch nicht ausreichend vereinheitlicht

## Discovery-Ergebnis

Der erste Polish-Slice sollte nicht neue Optik erfinden, sondern die gemeinsame Buch-Huelle staerken:

- gemeinsame `route camera`-Geometrie
- gemeinsame `route page`-Hoehenlogik
- gemeinsame `focus page`- und `workspace page`-Varianten
- weniger route-lokale Layout-Overrides in `character-sheet` und `play`
