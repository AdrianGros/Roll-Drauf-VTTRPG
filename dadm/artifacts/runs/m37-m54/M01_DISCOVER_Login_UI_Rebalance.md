# M01 Discover - Login UI Rebalance

goal: Den aktuellen Login-Layout-Bruch reproduzierbar isolieren und die Ursachen benennen.

scope:
- `vtt_app/templates/login.html`
- `vtt_app/static/css/book-scene.css`
- `/login.html` im geoeffneten Buchzustand

findings:
- Das Login-Layout ist doppelt definiert: einmal inline in `login.html`, einmal global in `book-scene.css`.
- Beide Definitionen widersprechen sich bei `grid-template-columns`, `grid-column`, Padding und responsivem Verhalten.
- Dadurch werden Sidecar und Formular in konkurrierende Layout-Slots gedrueckt.
- Das aktuelle DOM legt das Markenmodul im Formularbereich ab, waehrend das Mockup die Marke links und das Formular rechts vorsieht.
- Das sichtbare Ergebnis ist ein instabiles Mischlayout: rechte Info-Karte, nach unten verschobene Formular-Karte, leere linke Buchseite.

root cause:
- Kein Single Source of Truth fuer die Login-Geometrie.
- Struktur und Semantik folgen nicht dem Zielbild: Branding und Formular sind vertauscht.

acceptance criteria:
- Die Ursache ist auf CSS-/DOM-Ebene benannt.
- Die betroffenen Dateien sind eindeutig.
- Die Discover-Erkenntnisse reichen fuer eine direkte Zieldefinition in M02.
