# DAD-M Discover: Book UI Polish Wave P1 Responsive Motion Pass

Date: 2026-04-01
Status: completed

## Ausgangslage

- die Buchfamilie ist systemisch vereinheitlicht, reagiert aber auf geringe Viewport-Hoehen noch zu schwach
- `play` haengt fuer die Workspace-Flaeche noch sichtbar an `100vh`-Denken
- Reduced Motion ist bereits vorhanden, greift aber noch nicht konsequent genug auf kleinere Interaktionsbewegungen und den sticky Header

## Hauptbefunde

- geringe Hoehe ist aktuell riskanter als geringe Breite
- `play` ist die sensibelste Route fuer Overflow und Dichte
- die gemeinsame Buchseite braucht zusaetzliche kompakte Regeln fuer `topbar`, `ribbon`, `title`, `chips`, und Panel-Hoehen

## Discovery-Ergebnis

Der naechste P1-Slice soll drei Dinge zusammen erledigen:

- `small-height`-Verdichtung in der gemeinsamen Buchdatei
- `play`-Workspace von harten `viewport`-Hoehen loesen
- Reduced Motion auch auf kleinere Hover-/Chrome-Effekte ausweiten
