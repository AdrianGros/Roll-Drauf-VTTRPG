# DAD-M Discover: Book UI Polish Wave P1 Page Turn and Zoom

Date: 2026-04-01
Status: completed

## Ausgangslage

- die Buchfamilie ist strukturell und responsiv bereits stabilisiert
- die Erlebnisluecke liegt jetzt im wahrgenommenen Bewegungsfluss
- `book-scene.js` und `book-shell.js` animieren bereits, aber der Zoom wirkt noch zu flach und der Route-Handoff noch zu technisch

## Hauptbefunde

- interne Szenenwechsel innerhalb des persistenten Buchs brauchen mehr Tiefenstaffelung
- echte Routewechsel brauchen einen glaubwuerdigen Hand-off zwischen ausgehendem und eingehendem Buchblatt
- die vorhandene Overlay-Struktur ist funktional, aber visuell noch zu schlicht

## Discovery-Ergebnis

Der naechste Erlebnis-Slice soll:

- Richtungslogik fuer Vorwaerts-/Rueckwaerts-Blaettern einfuehren
- den `book-scene`-Kamerawechsel mit staerkerem Prezi-artigem Zoom vertiefen
- den `book-shell`-Routewechsel mit Page-Turn-Overlay plus Ankunftsanimation auf der Zielseite koppeln
