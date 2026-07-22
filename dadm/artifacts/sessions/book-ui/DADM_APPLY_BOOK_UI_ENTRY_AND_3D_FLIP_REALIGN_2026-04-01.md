# DAD-M Apply: Entry Scale and 3D Page Flip Realign

Date: 2026-04-01
Status: applied

## Umgesetzt

- dunkler Restlook in `vtt_app/static/css/book-scene.css` entfernt, indem Cover/Pages/Back im fertigen Dashboard-Zustand ganz ausgeblendet werden
- `vtt_app/static/js/book-scene.js` so erweitert, dass der Login als kleineres Entry-Objekt bleibt
- erfolgreicher Login animiert den Entry nun symbolisch in die Buchseiten hinein
- direkte `book-scene`-Route-Bootstraps erhalten einen klareren 3D-Folio-Auftakt
- `vtt_app/static/js/book-shell.js` erweitert, damit route-lokale Buchseiten auch ohne vorausgehenden Wechsel mit 3D-Folio-Ankunft laden
- `vtt_app/static/js/book-shell.js` auf echten `loading -> arrival flip -> ready`-Ablauf gestellt, damit Seiten nicht mehr mittig sichtbar aufspringen
- `vtt_app/templates/login.html` so angepasst, dass auch bereits authentisierte Nutzer nicht mehr instant in die grosse Ansicht hart weiterspringen

## Wirkung

- der Entry bleibt ritualisiert und kleiner
- nach Login fuehlt sich der Uebergang staerker wie `im Buch verschwinden` an
- spaetere Buchseiten laden und wechseln konsistenter im 3D-Folio-Stil

## Geaenderte Dateien

- `vtt_app/static/css/book-scene.css`
- `vtt_app/static/js/book-scene.js`
- `vtt_app/static/js/book-shell.js`
