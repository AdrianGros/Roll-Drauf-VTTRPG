# DAD-M Apply: Book UI Polish Wave P1 Page Turn and Zoom

Date: 2026-04-01
Status: applied

## Umgesetzt

- `vtt_app/static/js/book-scene.js` um Richtungslogik fuer Seitenwechsel erweitert
- interner Szenenwechsel im Buch auf staerkeren Kamera-Push, Blattversatz und eingehende Folio-Animation umgestellt
- `vtt_app/static/js/book-shell.js` um Route-Handoff via `sessionStorage`-Transition-Intent und Ankunftsanimation erweitert
- `vtt_app/static/css/book-shell.css` um reichere Overlay-Optik mit Schatten- und Blattstruktur erweitert
- `vtt_app/static/css/book-scene.css` um staerkere 3D-/Perspective-Hooks fuer die Szenenkamera ergaenzt

## Wirkung

- der Wechsel zwischen Buchseiten wirkt staerker wie Blaettern plus Kamerafahrt
- echte Routewechsel behalten eher das Gefuehl desselben Buchobjekts
- der Erlebnis-Polish bleibt auf performante `transform`-/`opacity`-Muster fokussiert

## Geaenderte Dateien

- `vtt_app/static/js/book-scene.js`
- `vtt_app/static/js/book-shell.js`
- `vtt_app/static/css/book-scene.css`
- `vtt_app/static/css/book-shell.css`
