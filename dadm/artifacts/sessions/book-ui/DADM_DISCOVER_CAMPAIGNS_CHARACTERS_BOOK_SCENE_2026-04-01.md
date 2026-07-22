# DADM Discover: Campaigns + Characters Book Scene

Date: 2026-04-01
Status: completed

## Ist-Zustand

- `login -> dashboard` blieb bereits im Buchobjekt.
- `campaigns` und `characters` waren trotz Book-Shell visuell noch eigenstaendige Routen mit klassischem App-Layout.
- Direkte Aufrufe oder Reloads auf `/campaigns` und `/characters` fielen aus dem persistenten Buchfluss heraus.
- Die vorhandene `book-scene.js` kannte praktisch nur die Dashboard-Seite als in-book Ziel.

## Problem

- Der User-Flow fuehlte sich nach dem Dashboard nicht wie weiteres Blaettern im selben Maerchenbuch an.
- Routewechsel wirkten wie Wechsel zwischen normalen Screens statt wie Folgeseiten desselben Objekts.

## Scope dieses Blocks

- `campaigns` und `characters` als echte Buch-Folgeseiten derselben Szene aufbauen.
- Direktaufrufe der beiden Routen auf denselben Szenen-Host legen.
