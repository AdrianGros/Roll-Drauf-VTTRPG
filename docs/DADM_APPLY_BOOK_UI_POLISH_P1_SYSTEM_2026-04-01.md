# DAD-M Apply: Book UI Polish Wave P1 System Normalization

Date: 2026-04-01
Status: applied

## Umgesetzt

- gemeinsame `book-route-camera`, `book-route-page`, `book-focus-page`, und `book-workspace-page`-Regeln in `vtt_app/static/css/book-scene.css`
- gemeinsame Body-/Main-Grundgeometrie fuer `character-sheet` und `play` in `vtt_app/static/css/book-scene.css`
- bestehende redundante Layout-Regeln in `vtt_app/templates/character-sheet.html` reduziert
- bestehende redundante Layout-Regeln in `vtt_app/templates/play.html` reduziert

## Wirkung

- Focus- und Workspace-Routen lesen staerker aus derselben Buchbasis
- die Route-Templates tragen weniger doppelte Shell-Logik
- die naechsten Small-Height-, Mobile- und Motion-Paesse koennen auf einer klareren gemeinsamen Grundlage arbeiten

## Geaenderte Dateien

- `vtt_app/static/css/book-scene.css`
- `vtt_app/templates/character-sheet.html`
- `vtt_app/templates/play.html`
