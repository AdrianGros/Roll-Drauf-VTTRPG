# M03 Deploy - Login UI Rebalance

goal: Das Zielbild fuer die Login-Seite implementieren, live deployen und gegen das Mockup validieren.

implementation scope:
- Doppelte Layout-Regeln in `login.html` entfernen.
- Login-Geometrie in `book-scene.css` konsolidieren.
- DOM in `login.html` so anpassen, dass links Branding und rechts Formular liegen.
- Live-Deployment auf `vtt.roll-drauf.de`.

verification:
- Linke Buchseite zeigt das Branding-Panel.
- Rechte Buchseite zeigt die Formular-Karte.
- Das Logo erscheint links, nicht im Formular.
- Kein vertikaler Versatz der Formular-Karte.
- Mobile bleibt funktional.

done when:
- Die Live-Seite entspricht strukturell dem Mockup.
- Die Layoutquelle ist konsolidiert.
- Das Ergebnis ist visuell stabil genug fuer einen Abnahmecheck.
