# Design-Jury: B2-Abnahme-Screenshots — Befunde & Baseline-Empfehlung

**Datum:** 2026-08-25 · **Material:** 160 Screenshots des B2-Abnahmelaufs (`artifacts/strict-acceptance-2026-08-24/`) · **Verfahren:** vier unabhängige KI-Juroren (R7, Regelwerk — **beratend, nie alleiniges Gate**) mit getrennten Blickwinkeln: A Cross-Browser/Viewport-Konsistenz, B Buch-Metapher/Designbrief-Treue, C Telefon-Zellen, D Zustands-Lesbarkeit der Journey. Kernbehauptungen wurden von der Hauptsession stichprobenverifiziert; solche Punkte sind mit **[VERIFIZIERT]** markiert.

**Klartext-Fazit:** Die Abnahme war funktional grün, aber die Jury findet (a) zwei echte Produkt-Blocker, (b) eine große Evidenz-Lücke im Abnahmelauf selbst, und (c) ein Bündel Designbrief-Verstöße. **Die 160 Baselines dürfen NICHT pauschal eingefroren werden** — Empfehlung unten, pro Checkpoint.

---

## 1. Die Top-Befunde (jury-übergreifend dedupliziert)

### Produkt-Blocker

1. **Fehl-Login ohne sichtbares Feedback (Chromium Phone-Landscape).** Nach ungültigem Submit liegt „invalid credentials" komplett unter dem Fold; der Submit-Knopf ist an der Unterkante angeschnitten. Der Nutzer sieht *nichts* passieren. (Juroren C+D unabhängig; Zellen `dm-/player-chromium-phone-landscape-login-recovery.png`.) → **Scroll-to-Error fehlt**; Firefox rettet es nur durch zufällige Scroll-Position.
2. **Leeres Buch am Checkpoint „login-ready" (6 Zellen leer, 2 Geister).** Firefox zeigt auf allen drei Desktop-Viewports (beide Rollen) eine komplett leere Doppelseite ohne Formular; chromium/firefox-narrow zeigen ein halbtransparentes Geisterformular. (Juroren A+B unabhängig, Vollauflösung bestätigt.) Entweder frisst die Einblende-Transition real den Inhalt (exakt die §2-Diagnose des Designbriefs) oder der Robot schießt vor Animationsende — **beides ist ein Blocker**: einmal fürs Produkt, einmal für die Beweiskraft.

### Abnahme-Evidenz-Lücke (Robot-Baustelle, high)

3. **[VERIFIZIERT] `login-submitted`, `dashboard-redirect` und `dashboard-settled` sind in allen 20 Zellen byte-identisch** (MD5 von der Hauptsession geprüft). Drei Checkpoints, ein Frame: Es existiert keinerlei Evidenz für Submit-Übergang und Redirect-Zustand. (Juroren A, B, D unabhängig.) → strict_journey muss die Zwischenzustände real einfangen oder die Checkpoints ehrlich zusammenlegen.
4. **Animations-Nichtdeterminismus an login-initial/logout-return:** Chromium friert je Viewport verschiedene Frames ein — bis hin zu komplett leeren Seiten (`player-chromium-phone-portrait-login-initial.png`), Firefox zeigt überall den gesetzten Deckel. (Juroren A+C.) → Capture braucht benannte Readiness-Bedingungen statt Timing (deckt sich wörtlich mit Annex-Empfehlung Gate B/§2).

### Systemische Design-Befunde (high)

5. **Sprache leckt im Rendering:** Fehlermeldung „invalid credentials" englisch in durchgehend deutscher UI (A, C, D); Umlaut-Ersatzschreibungen **im gerenderten Text** — „prueft", „PRIMAERE GILDE" (direkt neben korrektem „PRIMÄRE GILDE"!), „ausschliesslich" (B). Diese Strings kommen aus JS (`book-scene.js`-Inhalte), nicht aus Templates — der Template-Grep von stil_lint (2 Funde) ist strukturell blind dafür. → bestätigt die §8.4-Empfehlung „Sprach-Scan auf der gerenderten Seite" als eigenes Gate.
6. **Gold als Textfarbe auf Papier, flächendeckend** („DER ZUGANG LIEGT IM SERVER", alle Sektionsköpfe) — wörtlicher Verstoß gegen Designbrief §4.1 („nie als Textfarbe auf Papier") und das Kontrast-Gate (B).
7. **Fokus-Sichtbarkeit:** Bei desktop-large sitzt das fokussierte Element halb unter der Viewport-Kante — Firefox scrollt gar nicht nach (A, D; 4 Zellen); der Gold-Hairline-Fokusring ist systemisch kontrastschwach, dieselbe Farbe dient überall als Deko (D). → deckt die §8.4-Fokus-Warnung („unsichtbare Indikatoren verstecken sich in Themes mit eigenen Fokus-Ringen") empirisch.
8. **Meta-Prosa & Dreifach-Navigation:** Dashboard und Login-Rechtsseite erklären ihre eigene Architektur in ganzen Absätzen (Brief §3.4-Verstoß); drei parallele Wege zu denselben Zielen (Top-Nav + Inhaltsverzeichnis + Button-Grid) — die Dreifach-Bindung kehrt als Dreifach-*Darstellung* wieder (B). B3-Futter.

### Weitere Befunde (medium/low, Auswahl)

- ✨-Ornament rendert je Browser völlig anders (Chromium Umriss-Sterne, Firefox Emoji, tw. geclippt) — Emoji-Fallback statt Asset; laut Brief-Abrissliste ohnehin zu löschen (A, B, C).
- Doppelseite unter 1200 px beim Login, Einzelseite beim Dashboard in derselben Breite — Seitenmodell inkonsistent (B, C).
- Kein Logout-Feedback (zugeklapptes Buch, von login-initial kaum unterscheidbar) und kein sichtbarer Lade-Zustand nach Submit (D).
- Landscape login-ready: Submit unterm Fold (Chromium, C+D); unbekannte goldene Pille rechts geclippt in allen Landscape-keyboard-Zellen (C — bitte identifizieren).
- Streifen-„Papiertextur" liest sich als Wireframe-Platzhalter, besonders auf dem Cover (B); „1 Mitglieder" (B); Primärknöpfe Plum statt Oxblood-Rubrizierung (B); Kolumnentitel scrollt weg, Folio fehlt (B); „▶ SPIELTISCH" konkurriert dauerhaft mit aktivem Tab und CTA (D).
- Positiv (B): Lesebändchen-Idee sitzt, Inhaltsverzeichnis mit römischen Kapiteln + Punktführung steht, Kern-Chrome spricht Deutsch mit echten Umlauten, Login hat genau eine primäre Aktion.

---

## 2. Baseline-Freigabe-Empfehlung (pro Checkpoint)

**Grundsatz-Empfehlung: Jetzt nur die Dashboard-Checkpoints einfrieren.** Codex arbeitet gerade an der Login-Seite (Banner, Scroll-Fix) — jede heute eingefrorene Login-Baseline ist in Tagen wieder Makulatur. Und §8.2 gilt: eine schlechte Baseline segnet ein schlechtes Design.

| Checkpoint | Empfehlung | Begründung |
|---|---|---|
| dashboard-settled (20) | ✅ freigeben | strukturell konsistent über alle Zellen; einziger Vorbehalt: dm/player haben verschiedene Seed-Gilden (Bernsteinkreis/Nebellaterne) — kurz bestätigen, dass das Testdaten-Design ist |
| login-recovery (18 von 20) | ✅ freigeben, außer 2 | `*-chromium-phone-landscape-*` NICHT (Blocker-Befund 1) |
| dashboard-keyboard (16 von 20) | ✅ freigeben, außer 4 | `*-desktop-large-*` NICHT (Fokus abgeschnitten, Befund 7) |
| login-ready | ⛔ warten | 8 von 20 Zellen leer/Geister (Befund 2) + Codex baut Login gerade um |
| login-initial / logout-return | ⛔ warten | nichtdeterministische Animationsframes (Befund 4) — erst Readiness-Fix im Robot |
| login-submitted / dashboard-redirect | ⛔ warten | beweislose Duplikate (Befund 3) — erst Capture-Fix |

Freigabe-Kommandos (nach eigenem Blick in `baseline_review.html`; drei Aufrufe, weil `--only` ein Muster pro Lauf nimmt):

```bash
venv/bin/python -m tools.robots.review_baselines --run artifacts/strict-acceptance-2026-08-24 \
  --promote --note "B2: Dashboard-settled Erstfreeze (Jury 2026-08-25)" --only '*-dashboard-settled.png'
# dashboard-keyboard ohne desktop-large:
#   je ein Lauf mit --only '*-desktop-wide-dashboard-keyboard.png', '*-desktop-narrow-…', '*-phone-portrait-…', '*-phone-landscape-…'
# login-recovery ohne chromium-phone-landscape:
#   '*firefox*-login-recovery.png', '*chromium-desktop*-login-recovery.png', '*chromium-phone-portrait-login-recovery.png'
```

---

## 3. Konsequenzen für die Robot-Flotte (Upgrade 3, vorgeschlagen)

1. **strict_journey Readiness statt Timing:** benannte Bedingungen (`form-visible-and-opaque`, `cover-settled`) vor jedem Screenshot; Animationsende abwarten oder `reduced-motion` fürs Capture erzwingen — behebt Befunde 2 (Beweis-Hälfte) und 4.
2. **Submit-/Redirect-Zustände real einfangen** (Screenshot im Navigation-Race oder Checkpoints zusammenlegen) — behebt Befund 3.
3. **Fokus-Vertrag:** dashboard-keyboard zusätzlich per Geometrie prüfen: fokussiertes Element vollständig im Viewport (scroll-into-view) + Fokusring-Kontrastmessung — Befund 7 wird messbar statt Jury-Meinung.
4. **Rendered-Language-Scan** als neues R4-Teilgate: gerenderte Seiten auf `[a-z]-only`-Englisch-Strings und Umlaut-Ersatz scannen (JS-Inhalte!); stil_lint-Umlaut-Grep zusätzlich auf `vtt/static/js` ausweiten — Befund 5.
5. **Klick-Vertrag für die goldene Landscape-Pille** (C-Befund 4): identifizieren, dann Vertrag oder Abriss.

Die Design-Befunde 6, 8 und die medium/low-Liste sind **B3/B5-Futter für Codex** (Gold-Text → Rubrizierung, Meta-Prosa raus, Navigation konsolidieren, ✨-Abriss, Fokusring), nicht Robot-Arbeit.

---

*Erstellt von der KI-Jury (4 unabhängige Juroren) + Verifikation der Hauptsession. Beratend gemäß Regelwerk R7 — die Freigabe-Entscheidung liegt bei Adrian (§6).*
