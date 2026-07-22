# DAD-M Apply: Book UI Polish Wave P1 Responsive Motion Pass

Date: 2026-04-01
Status: applied

## Umgesetzt

- `scroll-padding-top` fuer Buchrouten gesetzt, damit sticky Ribbon und Ankerverhalten ruhiger arbeiten
- neue `max-height`-Breakpoints in `vtt_app/static/css/book-scene.css` fuer kompaktere Buchseiten bei wenig Hoehe
- Reduced-Motion-Regeln in `vtt_app/static/css/book-scene.css` auf Ribbon-Buttons, Tiles, Bookmark und sticky Header erweitert
- `vtt_app/templates/play.html` von fester `100vh`-Hoehenrechnung auf flexiblere Workspace-Hoehen umgestellt
- `play` zusaetzlich mit `max-height`-Breakpoints fuer Toolbar, Floating Panels, Sidebar und Zoom-Topbar verdichtet

## Wirkung

- geringere Overflow-Gefahr auf kleinen Hoehen
- ruhigere Buch-Chrome bei aktivierter Bewegungsreduktion
- `play` bleibt eher in der Buchseite eingebettet statt gegen die Viewport-Hoehe zu verlieren

## Geaenderte Dateien

- `vtt_app/static/css/book-scene.css`
- `vtt_app/templates/play.html`
