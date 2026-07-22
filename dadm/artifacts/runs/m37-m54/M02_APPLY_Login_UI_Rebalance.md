# M02 Apply - Login UI Rebalance

goal: Ein eindeutiges Zielbild fuer die Login-Seite definieren, das dem Mockup entspricht.

layout contract:
- Linke Buchseite: Branding-/Info-Flaeche auf dunklem Grund.
- Rechte Buchseite: Formular auf einer hellen, schwebenden Papierkarte.
- Das Logo sitzt links im Branding-Panel.
- Das Formular enthaelt keine Markenillustration mehr.
- Die Buchillusion bleibt sichtbar; das Formular wird nicht mehr als loses Overlay wahrgenommen.

component rules:
- `book-scene.css` ist die einzige Quelle fuer die Login-Geometrie.
- `login.html` behaelt nur komponentennahe Form-Stile und Verhalten.
- Das linke Branding-Panel ist schmaler und vertikal gefuehrt.
- Die rechte Formular-Karte ist breiter, zentriert und optisch auf der rechten Buchseite verankert.
- Die `Sign up`-Aktion steht unterhalb der Formular-Karte auf der Seite, nicht innerhalb des Markenbereichs.

responsive rules:
- Desktop: zwei klare Buchseiten.
- Tablet: Formular bleibt dominant, linkes Branding kann kompakter werden.
- Mobile: einspaltig, Branding verschwindet zugunsten des Formulars.

acceptance criteria:
- Die Mockup-Rollen links/rechts sind klar umgesetzt.
- Es gibt keinen Widerspruch mehr zwischen Template und globalem CSS.
- Das Zielbild ist ohne weitere Designentscheidung implementierbar.
