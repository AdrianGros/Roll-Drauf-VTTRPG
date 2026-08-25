# Robot-Flotte & Regelwerk — Roll Drauf VTT

**Datum:** 2026-08-24
**Scope:** Forschung und Design-Leitfaden; kein Anwendungs- oder Robot-Code wurde geändert.
**Frage:** Welche Robotertypen brauchen wir über den strengen Journey-Robot hinaus, damit Ästhetik, User-Funnels und Frontend-Best-Practices konsistent bleiben — und wie stellen wir sicher, dass jeder Knopf **real geklickt** und sein erwartetes Ergebnis **verifiziert** wird?

**Schwesterdokumente (Tiefen-Annexe, nicht ersetzt durch dieses Dokument):**

- [ROBOT_TESTING_RESEARCH_2026-08-24.md](ROBOT_TESTING_RESEARCH_2026-08-24.md) — der strenge Login→Dashboard-Journey-Robot (Gates A–I, Evidence-Vertrag, Phasenplan). Gilt als Annex für Robot **R1**.
- [USER_BEHAVIOR_RESEARCH_2026-08-24.md](USER_BEHAVIOR_RESEARCH_2026-08-24.md) — Friction-Metriken und Verhaltens-Proxies. Gilt als Annex für Robot **R3**.
- [DESIGNBRIEF_BUCH_UI_2026-08-24.md](DESIGNBRIEF_BUCH_UI_2026-08-24.md) §7 — die fünf Mess-Gates (Layout-Monotonie, Kontrast-Pin, Ein-Engine-Invariante, Sprach-Lint, Reduced-Motion-Pin, Token-Lint). Gelten als Pflichtenheft für Robots **R4/R5**.

Dieses Dokument ist der **Dachplan** für die Flotte: Taxonomie, Regelwerk, Klick-Verträge, Baureihenfolge.

---

## 1. Klartext-Zusammenfassung

Heute prüfen unsere Robots vor allem: „Existiert das erwartete Element im DOM, läuft der Hauptpfad durch?" Das reicht nicht, aus zwei Gründen:

1. **Ein Knopf, der da ist, kann trotzdem tot sein.** Kein Robot klickt heute *jeden* Knopf und prüft, ob das Versprochene passiert. Ein Knopf ohne Wirkung, ein Link ins Leere, ein Dialog der nie aufgeht — alles würde grün durchlaufen.
2. **Ästhetik-Drift ist unsichtbar für Funktionstests.** Codex baut die GUI in hohem Tempo; jede Phase kann Farben, Fonts, Abstände oder Sprache leicht verschieben, ohne dass irgendein Test rot wird. Genau diese Dominosteine fangen nur Token-/Style-Audits und Screenshot-Baselines ([Lastest 2026 Guide](https://lastest.cloud/blog/visual-regression-testing-design-systems-2026), [Augment Code](https://www.augmentcode.com/guides/visual-regression-testing-ai-generated-uis)).

Die Antwort ist keine einzelne neue Suite, sondern eine **Flotte aus 12 Robotern** mit klarer Arbeitsteilung — plus ein **Klick-Vertrags-System** als gemeinsames Fundament: jeder interaktive Knopf bekommt einen registrierten, maschinenlesbaren Vertrag („wenn geklickt, dann passiert X"), und ein Crawler-Robot setzt diesen Vertrag flächendeckend durch.

---

## 2. Das Fundament: Klick-Verträge (Interaction Contracts)

### 2.1 Prinzip

Jedes interaktive Element (Button, Link, Tab, Formular-Submit, Token-Drag-Ziel, Close-X, Ribbon-Eintrag) bekommt einen Eintrag in einer **Vertrags-Registry** — Katalogdaten statt Hardcode, dieselbe Hausregel wie bei den Vendor-Preisen in Goblin Delve. Der Vertrag beschreibt:

- **Wer:** stabiler Selektor (bevorzugt `data-testid`, sonst Role+Name nach [Playwright-Locator-Empfehlung](https://playwright.dev/docs/locators)),
- **Wo:** Seite und Zustand (Checkpoint), in dem das Element sichtbar sein muss,
- **Was:** die Aktion (click, fill+submit, drag, keyboard),
- **Dann:** die beobachtbare Nachbedingung — mindestens eine aus: Ziel-Route, sichtbar werdendes Element, verschwindendes Element, Socket-Event, Netzwerk-Antwort, sichtbare Statusmeldung,
- **Schwere:** blocker/high/medium/low, analog zum Evidence-Vertrag aus Gate I.

Vorschlag für das Format (eine YAML-Datei pro Seite unter `tools/robots/contracts/`):

```yaml
# tools/robots/contracts/dashboard.yaml
page: dashboard
state: dashboard-settled          # Checkpoint-Name aus strict_journey
elements:
  - id: nav-campaigns
    selector: '[data-testid="nav-campaigns"]'
    label: "Kampagnen"
    kind: nav
    action: click
    expect:
      route: "/campaigns"
      visible: "#book-campaigns-scene"
    severity: blocker
  - id: logout
    selector: '[data-testid="logout"]'
    label: "Abmelden"
    kind: auth
    action: click
    expect:
      route: "/login"
      hidden: "#book-dashboard-scene"
    severity: blocker
  - id: open-dice-tray
    selector: '[data-testid="open-dice-tray"]'
    kind: panel
    action: click
    expect:
      visible: '[data-testid="dice-tray"]'
      reversible_via: escape        # Escape/Close muss den Zustand zurücknehmen
    severity: high
```

### 2.2 Der Button-Crawler-Robot (R2) setzt die Verträge durch

Pro Seite/Zustand macht der Crawler vier Dinge:

1. **Inventur:** alle interaktiven Elemente einsammeln (`role=button|link|tab|menuitem`, `a[href]`, `button`, `[onclick]`, `[tabindex]`, Formular-Controls) — sichtbar und unsichtbar getrennt erfasst.
2. **Abgleich gegen die Registry:**
   - Element auf der Seite, aber **nicht registriert** → Finding „undokumentierter Knopf" (medium; blockt, sobald die Registry als vollständig erklärt wurde).
   - Registriert, aber **nicht auffindbar/sichtbar/enabled** → Finding nach Vertrags-Schwere.
3. **Ausführung:** jedes registrierte Element wird **wirklich geklickt** (bzw. per Tastatur aktiviert — beides, wegen der Ein-Engine-Invariante), mit Playwrights web-first Assertions auf die Nachbedingung ([Playwright assertions](https://playwright.dev/docs/test-assertions)). Nach jedem Klick: Zustand zurücksetzen (zurücknavigieren oder Seite neu laden), damit Klick N+1 nicht vom Seiteneffekt von Klick N abhängt.
4. **Totmann-Erkennung:** ein Klick, nach dem **nichts** Beobachtbares passiert (keine DOM-Mutation, keine Navigation, kein Request, kein aria-live-Update innerhalb des Readiness-Fensters) → Finding „toter Knopf" (high), auch wenn kein expliziter Vertrag verletzt wurde.

Sicherheitsgrenzen: Der Crawler läuft **nur gegen den Wegwerf-Stack** (`stack.py`), nie gegen Live — er klickt schließlich auch Lösch- und Submit-Knöpfe. Destruktive Verträge (`kind: destructive`) werden zuletzt und je in frischem Zustand ausgeführt. Read-only-Läufe gegen Staging/Live bleiben den visuellen Robots vorbehalten (Grenze aus Gate A).

Praxis-Härtung aus der Web-Recherche (Belege in §8.3):

- **Reset = Reload + Erreichungspfad-Replay.** Jede Kontrolle speichert in der Registry ihren Reach-Path (URL + Klickfolge ab Startzustand). Browser-Zurück oder blindes Neuladen stellen Ajax-/SPA-Zustände nachweislich nicht wieder her — das ist die zentrale Ingenieurs-Lehre aus Crawljax.
- **Pro Klick zwei Artefakte** (Screenshot vorher/nachher plus Netzwerk-Mitschnitt) — das Muster von Googles Robo-Test; nur so sind Totmann-Funde debugbar statt anzweifelbar.
- **Containment-Politik:** Popups abfangen, `target="_blank"` schließen, externe Navigation blocken; ein unerwarteter Seitenwechsel nach einem Klick ist ein *Finding*, kein Robot-Absturz.
- **Jede randomisierte Reihenfolge wird geseedet** und der Seed steht in jedem Report, damit jeder Lauf exakt wiederholbar ist (gremlins.js-Muster).

### 2.3 Was das von Codex verlangt (Definition of Done für GUI-Phasen)

- Jedes neue/geänderte interaktive Element bekommt ein `data-testid` **und** einen Registry-Eintrag **in derselben Phase**. Nachrüsten ist teuer, mitliefern ist billig.
- Ein Element ohne beschreibbare Nachbedingung ist ein Designfehler („was soll der Knopf denn tun?") und geht zurück ins Discover.

---

## 3. Die Flotte: 12 Roboter, Status und Zweck

| # | Robot | Zweck (eine Zeile) | Status heute | Gate-Typ |
|---|---|---|---|---|
| R1 | **Journey-Robot** | Die Kern-Funnels als geordnete Checkpoint-Reise mit Evidence (Login→Dashboard→Play) | ✅ gebaut ([strict_journey.py](../tools/robots/strict_journey.py)); Abnahme 2026-08-24: 160 Checkpoints, 0 Produktbefunde, `blocked` bis Baseline-Review; WebKit + Play-Handoff fehlen | blockierend |
| R2 | **Button-Crawler / Klick-Verträge** | Jeden Knopf real klicken, Nachbedingung prüfen, tote/undokumentierte Knöpfe melden | ✅ v1 gebaut 2026-08-24 ([crawler.py](../tools/robots/crawler.py) + [contracts/](../tools/robots/contracts/)); Dashboard vertraglich erfasst, 23 Elemente offen | blockierend |
| R3 | **Funnel-Budget-Robot** | Pro User-Funnel Schritte/Klicks/Zeit-bis-Aktion messen und gegen Budget prüfen | ❌ neu; Metrik-Vertrag existiert im USER_BEHAVIOR-Annex | blockierend (Budget), beratend (Trends) |
| R4 | **Stil-Lint (statisch)** | Token-Lint (Hex nur in theme.css, Zahl sinkt monoton), Sprach-Lint (Umlaute, engl. Chrome-Strings), Font-/Spacing-Scale-Lint | ✅ v1 gebaut 2026-08-24 ([stil_lint.py](../tools/robots/stil_lint.py), Ratchet-Baseline 556 Hex / 2 Umlaut-Ersatz) | blockierend |
| R5 | **Stil-Audit (Laufzeit)** | An jedem Checkpoint alle *computed styles* einsammeln (Farben, Fonts, Radien, Schatten) und gegen den Token-Katalog diffen → „Stil-Streuner" | ❌ neu | blockierend nach Baseline-Freeze |
| R6 | **Visual-Baseline-Robot** | Screenshot-Diffs gegen menschlich freigegebene Baselines an allen Checkpoints | 🔶 Vergleich in strict_journey; Review-Werkzeug gebaut 2026-08-24 ([review_baselines.py](../tools/robots/review_baselines.py)); 160 Baselines warten auf Adrians Freigabe | blockierend; Baseline-Update nur durch Mensch |
| R7 | **KI-Design-Jury** | Screenshot + Designbrief an ein Modell (Claude), Prosa-Befund zu Hierarchie, Satzspiegel, Buch-Metapher-Treue | ❌ neu | **nur beratend**, nie alleiniger Blocker |
| R8 | **A11y-Robot** | axe-Scan an settled/revealed States + Tastatur-Journey + Fokus-Sichtbarkeit + Kontrast | ❌ neu; Gate F im Annex fertig spezifiziert | blockierend (A/AA-Verstöße) |
| R9 | **Chaos-Affe** | Seeded Zufalls-Klick/Tipp/Scroll-Läufe; Invarianten: kein Console-Error, keine Sackgasse, kein Zombie-Overlay | ❌ neu | beratend, Absturzfunde blockierend |
| R10 | **Mehrspieler-/Echtzeit-Robot** | Zwei+ Kontexte (DM+Spieler) parallel; Sichtbarkeitsregeln, Socket-Zustände, Rejoin | ✅ gebaut ([fullsession.py](../tools/robots/fullsession.py), [mobile_session.py](../tools/robots/mobile_session.py)) | blockierend |
| R11 | **Performance-Robot** | Navigation Timing + LCP/INP/Long Tasks als Trend, Canvas-FPS beim Token-Drag; Budgets erst nach Baseline | ❌ neu; Gate H spezifiziert | beratend → blockierend nach Baseline |
| R12 | **Hygiene-Robot** | Console-Errors, requestfailed, unerwartete 4xx/5xx, kaputte Fonts/Assets, Socket-Verbindungszustand | 🔶 rudimentär in [session.py](../tools/robots/session.py) (nur ≥500) | blockierend |

Drei Anmerkungen zur Arbeitsteilung:

- **R2 und R1 überlappen nicht:** R1 beweist, dass die *erzählte Reise* funktioniert (wenige Pfade, tief, mit Screenshots und Geometrie). R2 beweist *Flächendeckung* (alle Knöpfe, flach, mit Nachbedingung). Beide zusammen ersetzen die alten `views.py`-Pins, die nur DOM-Existenz prüfen.
- **R4 und R5 sind zwei Hälften derselben Regel:** R4 verhindert, dass neue Hardcodes in den *Quelltext* kommen; R5 fängt, was trotzdem im *Browser* ankommt (Vendor-CSS, Inline-Styles, JS-gesetzte Farben). Erst beide zusammen halten Adrians „Katalogdaten statt Hardcode"-Regel dicht.
- **R7 ist bewusst nur Jury, nicht Richter:** KI-Ästhetik-Urteile sind wertvoll als Review-Verstärker (semantisches Rausch-Filtern ist 2026 Stand der Technik, vgl. [askui-Überblick](https://www.askui.com/blog-posts/leading-ai-visual-testing-tools), [TestMu AI](https://www.testmuai.com/blog/visual-testing-ai-agent/)), aber nicht deterministisch. Deploy-Gates müssen reproduzierbar sein; die Jury liefert Findings für den menschlichen Screenshot-Review vor jedem Commit (Haus-Disziplin aus dem Designbrief).

---

## 4. Die User-Funnels (Messobjekte für R1/R3)

Vorschlag der fünf verbindlichen Funnels; jeder bekommt einen benannten Checkpoint-Pfad und ein Budget (max. Schritte / max. Klicks; Zeiten zunächst nur als Trend):

| Funnel | Pfad | Rollen |
|---|---|---|
| F1 Ankommen | Erstbesuch → Registrierung/Discord-Login → Dashboard settled | neu |
| F2 Wiederkommen | Login → Dashboard → letzte Kampagne öffnen | DM, Spieler |
| F3 Leiten | Dashboard → Kampagne anlegen → Sitzung vorbereiten → Tisch öffnen | DM |
| F4 Mitspielen | Einladung/Beitritt → Charakter zuordnen → am Tisch sitzen → erster Wurf | Spieler |
| F5 Blättern | Dashboard → jede Buchseite und zurück (Klick, Tastatur, Link — dreifach) | beide |

Budget-Verstöße („F4 braucht plötzlich 9 statt 6 Klicks") sind Findings mit Severity high — das ist der automatisierte Frühwarner gegen schleichende Funnel-Verschlechterung.

---

## 5. Das Regelwerk (die Gesetze, die die Flotte durchsetzt)

Jede Regel nennt ihren Vollstrecker. Regeln ohne Robot sind Wünsche; deshalb gibt es hier keine Regel ohne Vollstrecker.

| § | Regel | Vollstrecker | Gate |
|---|---|---|---|
| §1 | **Kein Knopf ohne Vertrag.** Jedes interaktive Element ist in der Registry; undokumentierte Knöpfe sind Findings. | R2 | blockierend nach Registry-Freeze |
| §2 | **Kein toter Knopf.** Jeder Klick erzeugt seine vertraglich erklärte, beobachtbare Wirkung — geprüft durch echtes Klicken, nie durch DOM-Existenz. | R2 | blockierend |
| §3 | **Ein Weg, ein Ergebnis.** Klick, Tastatur und Link lösen dieselbe Transition aus (Ein-Engine-Invariante, Designbrief §7). | R2 (Doppel-Ausführung), R8 | blockierend |
| §4 | **Farben, Fonts, Abstände nur aus dem Katalog.** Hex-Literale außerhalb theme.css: Zahl darf nur sinken; kein computed style außerhalb des Token-Katalogs. | R4 + R5 | blockierend |
| §5 | **Grün heißt bewiesen.** Null Findings ohne vollständige Gate-Ausführung + Evidence = `inconclusive`, nicht `passed` (Gate-I-Vertrag). | run_all/report | blockierend |
| §6 | **Baselines ändert nur ein Mensch.** Kein Auto-Update von Screenshots; jede Baseline-Änderung hat eine begründete Freigabe. | R6 + Review | blockierend |
| §7 | **Jeder Funnel hat ein Budget.** Schritte/Klicks pro Funnel sind deklariert; Überschreitung ist ein Finding. | R3 | blockierend |
| §8 | **Erreichbar für alle.** WCAG-A/AA automatisiert, 4.5:1-Kontrast, 44px-Touch für primäre Telefon-Aktionen, Fokus nie verdeckt. | R8 | blockierend |
| §9 | **Robots sind Deploy-Gates.** Kein Deploy ohne grüne Pflicht-Suite (Hausregel, wie bei Goblin Delve). Beratende Robots (R7, R9, R11 vor Baseline) blocken nicht, ihre Findings landen aber im Review. | run_all | blockierend |
| §10 | **Ticket → Szenario vor Fix.** Jeder gemeldete Bug wird erst als Robot-Szenario (Vertrag, Checkpoint oder Canary) reproduziert, dann gefixt. | alle | Prozessregel |
| §11 | **Der Robot muss selbst durchfallen können.** Jede Suite hat Canary-Fixtures (versteckter CTA, toter Knopf, Fremd-Hexwert, Kontrastbruch); ein Lauf, der die eigenen Canaries nicht findet, ist `inconclusive`. | alle | blockierend |
| §12 | **Klicken nur im Wegwerf-Stack, Live nur lesend.** Mutierende Robots (R2, R9, R10) laufen ausschließlich gegen den Disposable-Stack; gegen Staging/Live laufen nur read-only Sicht-Robots mit Umgebungs-Metadaten. | stack.py-Grenze | blockierend |
| §13 | **GUI-Phase ohne Vertragspflege ist nicht fertig.** Codex' Definition of Done umfasst `data-testid` + Registry-Eintrag + ggf. Baseline-Antrag für jedes berührte Element. | Review + R2 | Prozessregel |

---

## 5b. V-Regeln — rein visuelle Gestaltungsgesetze (Kulissen-Regeln)

Nachtrag 2026-08-24, auf Adrians Anstoß: Die §-Regeln oben sichern Konsistenz und Funktion, aber nicht die **Komposition unter Bewegung** — was passiert mit Hintergründen, Texturen und Ebenen, wenn gescrollt, gezoomt oder das Fenster verändert wird. Dafür gibt es die V-Familie.

Grundsatz: **Jede V-Regel prüft das Ergebnis, nie die Technik.** Ob ein Hintergrund per mitwachsender Fläche, `background-attachment`, oder Transform-Parallax gebaut ist, bleibt Codex überlassen — der Robot prüft nur, was der Spieler sieht. (Praxis-Warnung für die Bauweise: iOS-WebKit ignoriert `background-attachment: fixed` **absichtlich** — im [WebKit-Tracker als „by design" markiert](https://bugs.webkit.org/show_bug.cgi?id=275247); der Standard-Workaround ist eine eigene `position: fixed`-Ebene, die die Textur trägt ([CSS-Tricks](https://css-tricks.com/the-fixed-background-attachment-hack/)). Transform-Ebenen oder mitwachsende Flächen sind die robusten Wege; alle Belege in §8.1. Der Robot bleibt davon unberührt, weil er das Ergebnis misst.)

Prüfverfahren („**Kulissen-Check**", als Erweiterung von R6/Gate C): An jedem Seiten-Checkpoint fährt der Robot eine **Scroll-Treppe** (0 % / 25 % / 50 % / 75 % / 100 % der Scrollhöhe) über die Viewport-Matrix aus Gate G. An jeder Stufe: Geometrie der Hintergrund-Ebene gegen den Viewport, plus Pixel-Stichproben an Ecken und Kanten des Screenshots gegen die erlaubten Token-Flächenfarben (die PIL-Infrastruktur dafür existiert bereits in `strict_journey.py`).

Drei Praxis-Korrekturen aus der Web-Recherche (Belege in §8.1): **keine `fullPage`-Screenshots als Beweismittel** — fixe Ebenen verdoppeln sich in gestitchten Aufnahmen, Inhalte in inneren Scroll-Containern fehlen ganz, und `fullPage` kann sogar das Rendering verändern (drei dokumentierte Playwright-Defekte); Mobil-Profile laufen in **zwei Viewport-Höhen** (URL-Leiste sichtbar/eingeklappt), weil die 100vh-Falle genau dort sitzt; und wenn eine Buchseite in einem **inneren Container** scrollt, scrollt der Robot diesen Container, nicht `window` — sonst prüft er ins Leere.

| V | Regel | Prüfung | Status |
|---|---|---|---|
| V1 | **Der Hintergrund reißt nie ab.** Auf jeder scrollbaren Seite füllt die gestaltete Hintergrundfläche an *jeder* Scroll-Position den gesamten Viewport. Erlaubte Bauweisen: (a) die Fläche wächst mit dem Inhalt mit (Hintergrund-Höhe ≥ `scrollHeight`), oder (b) der Inhalt scrollt als Kulissen-/Parallax-Aufbau über einer feststehenden, viewport-füllenden Ebene. Verboten: harte Abrisskante, durchscheinende Browser-Default-Fläche. | Scroll-Treppe: Rect der Hintergrund-Ebene deckt Viewport; Pixel-Stichproben an den vier Kanten ∈ Token-Katalog | **gesetzt** (Adrian, 2026-08-24) |
| V2 | **Kein nackter Body.** `html` und `body` tragen immer eine Token-Fläche, damit auch Overscroll/Rubber-Banding und Ladezustände nie Browser-Grau zeigen. | Computed style von `html`/`body` ∈ Token-Katalog (R5) | Vorschlag |
| V3 | **Parallax respektiert Reduced Motion.** Bei `prefers-reduced-motion` steht die Kulisse still (keine scroll-gekoppelten Transforms) — V1-Deckung muss trotzdem gelten. | Scroll-Treppe mit emulierter Präferenz: Transform-Delta der Kulissen-Ebene = 0 (Anschluss Reduced-Motion-Pin, Designbrief §7) | Vorschlag |
| V4 | **Bilder werden nie verzerrt.** Gerendertes Seitenverhältnis = natürliches Seitenverhältnis (kleine Toleranz); `naturalWidth == 0` (kaputtes Bild) ist ein Finding. | Für jedes sichtbare `img`/Textur-Element: Rect vs. `naturalWidth/Height` (Anschluss R12) | Vorschlag |
| V5 | **Texturen kacheln unsichtbar.** Papier-/Holz-Wiederholtexturen ohne sichtbare Kachelkante oder Moiré. | Nicht deterministisch prüfbar → Baseline-Review (R6) + KI-Jury (R7, beratend) | Vorschlag |
| V6 | **Eine Lichtquelle.** Alle Schatten haben konsistente Richtung und stammen aus dem Token-Katalog; keine Ad-hoc-`box-shadow`. | R5-Laufzeit-Audit (Schatten-Offsets katalogisiert) | Vorschlag |
| V7 | **Sticky-Chrome verdeckt nie das Sprungziel.** Nach jeder Anker-/Abschnittsnavigation ist die Zielüberschrift vollständig sichtbar unterhalb fixer Leisten. | Nach Navigation: Ziel-Rect ∩ Sticky-Rects = ∅ (Geometrie, Gate C) | Vorschlag |
| V8 | **Seitenkante bleibt Seitenkante.** Die Buch-Metapher verlangt an allen Viewports sichtbare Papierränder — Inhalt klebt nie direkt an der Viewport-Kante (Mindestrand aus dem Token-Satzspiegel; Ausnahme: der bewusst randlose Kartentisch). | Rect des Inhaltsblocks vs. Viewport-Kanten ≥ Token-Randbreite | Vorschlag |

Gate-Verhalten: V1 sofort **blockierend** (ist gesetzt). V2–V8 laufen zunächst beratend und werden mit Adrians Freigabe im nächsten Design-Review einzeln auf blockierend gestellt — dieselbe Zwei-Stufen-Logik wie bei den Performance-Budgets (§/Gate H).

---

## 6. Baureihenfolge & Stand

### Stand 2026-08-24 Abend — Konsolidierung mit Codex' B2-Abschluss + Robot-Upgrade 2

**Codex-Stand (B2 + strenge GUI-Journey):** B2-Responsive-Closeout ist fertig (1024px-/Phone-Landscape-Clipping, 48px-Nav-Ziele, TOC-Fokus/Kontrast, Buchdeckel aus der Tastatur-Navigation, Invalid-Login-Recovery mit zugänglicher Fehler-Assoziation). Abnahmelauf: **160 Checkpoints** (DM/Spieler × Chromium/Firefox × 5 Viewports), **0 Produktbefunde** — Status `blocked`, weil 160 Screenshot-Baselines menschliche Freigabe brauchen und WebKit-Abhängigkeiten fehlen. Das ist §5 in Aktion: der Lauf *weigert sich*, ohne Beweise grün zu sein. Alles uncommitted/undeployed.

**Robot-Upgrade 2 — geliefert (2026-08-24, neue Dateien, Codex' offene Änderungen unberührt):**

1. **[review_baselines.py](../tools/robots/review_baselines.py)** (R6, §6/§8.2): erzeugt pro Abnahmelauf einen Kontaktbogen (`baseline_review.html`, nach Checkpoint gruppiert, mit Diff-Masken gegen bestehende Baselines) und übernimmt nach Review per `--promote --note '…'` in `snapshots/strict_journey/` samt Herkunfts-Manifest. Kein Auto-Update, abweichende Baselines nur mit `--force`. Getestet: 160 Zellen, alle NEU.
2. **[stil_lint.py](../tools/robots/stil_lint.py)** (R4, §4/§8.4): Ratchet pro Datei (Betterer-Muster, in Python — kein Node-Toolchain im Repo). Baseline eingefroren: **556 Hex-Literale** außerhalb theme.css (Vendor-Dateien ausgenommen), **2 Umlaut-Ersatzschreibungen**. Zahl steigt ⇒ rot; sinkt ⇒ Baseline senkt sich selbst.
3. **[crawler.py](../tools/robots/crawler.py) + [contracts/](../tools/robots/contracts/)** (R2, §1–§3): Button-Crawler v1 mit JSON-Vertrags-Registry. Pro Seite: Inventur aller Interaktionselemente, Registry-Abgleich (undokumentierte Knöpfe = Findings), echtes Klicken **mit Maus und Tastatur** inkl. Nachbedingungs-Assertion, Totmann-Orakel **mit Leerlauf-Rauschmessung** (Socket-Polling/Statusregionen täuschen sonst Effekte vor — Crawljax-Normalisierer-Lehre), Containment, geseedete Reihenfolge, Vorher/Nachher-Screenshots, §11-Canary. Testlauf: **passed, 44 s, 8 Ausführungen, Ein-Engine-Invariante für alle Nav-Paare bestätigt, Canary gefangen, 23 undokumentierte Knöpfe** als Arbeitsliste in `inventory.json`.

**Realbefund des ersten Crawler-Laufs (wichtig für B3):** Das Dashboard trägt **zwei Ribbons im DOM** — das versteckte Template-Markup aus `dashboard.html` (mit `onclick`/`data-book-route`, nicht klickbar, von `book-scene-stage` überdeckt) und die sichtbare, von `book-scene.js` gerenderte Kopie (ohne beides, ohne IDs). Exakt die „verstecktes Alt-Markup täuscht DOM-Pins"-Fehlerklasse aus dem R1-Annex, jetzt empirisch belegt. Die Verträge nutzen bis B3 `:not([onclick])` + Textfilter; B3 räumt das Doppel-Markup ab und gibt den Live-Knöpfen `data-testid` (§13).

**Nachtrag 2026-08-25 — Robot-Upgrade 2 abgeschlossen + Jury + Spieltisch-Audit:**

- **R2-Crawler: Dashboard voll vertraglich erfasst** (26 Verträge, Lauf `passed`, 30 Ausführungen, Canary gefangen; einziges offen dokumentiertes Element: der Buchdeckel-Div — Soll-Verhalten klärt B3). Neue Vertragsarten: `in_viewport` (Scroll-Ziele), `expect_disabled`, `nth`, `text_exact`; Totmann-Orakel rauschnormalisiert (Scroll zählt als Effekt).
- **Kulissen-Check gebaut** ([kulissen.py](../tools/robots/kulissen.py), V1/V2 + Gate-C-H-Overflow): Scroll-Treppe mit `elementFromPoint`-Deckungs-Orakel (Inhalt über einer Kante ist legitim; nacktes html/body ist der Abriss), `background-image` zählt als Bemalung, Canary auf nackter `data:`-Seite (app-unabhängig). Befunde: Purpur = `linear-gradient` auf `body` (ok), `html` unbemalt (low, Overscroll-Propagation), **6px H-Overflow bei 390×760** (die URL-Leisten-Höhe — Beleg für die Zwei-Höhen-Regel), und `blocked` auf Telefonen, weil der neue zweistufige Login (`#passwordLoginContinueBtn`) auf phone-portrait nie sichtbar wird → an Codex' Login-Baustelle.
- **KI-Design-Jury (R7) hat getagt:** 4 unabhängige Juroren über alle 160 Abnahme-Screenshots — Befunde und **Baseline-Freigabe-Empfehlung pro Checkpoint** in [DESIGN_JURY_B2_BASELINES_2026-08-25.md](DESIGN_JURY_B2_BASELINES_2026-08-25.md). Kernaussage: **nicht pauschal einfrieren** — submitted/redirect/settled sind byte-identisch (MD5-verifiziert, Evidenz-Lücke im Robot), login-ready ist in 8 Zellen leer/geisterhaft, Chromium-Landscape-Recovery zeigt kein Fehler-Feedback. Jetzt freigeben: nur dashboard-settled/-keyboard (ohne desktop-large)/login-recovery (ohne chromium-landscape).
- **Spieltisch-Audit:** [PLAYTABLE_AUDIT_2026-08-25.md](PLAYTABLE_AUDIT_2026-08-25.md) — fullsession+mobile-Robots grün; P0: DM-Geheimnisse werden nur clientseitig gefiltert; Kampf-Backend fertig aber vom Tisch nie aufgerufen; Charakterbogen am Tisch fehlt.
- Beide Berichte liegen als PDF im Bot-`/report` (`RollDrauf_VTT_Playtable_Audit_2026-08-25.pdf`, `RollDrauf_VTT_Design_Jury_Review_B2_2026-08-25.pdf`).

**Nachtrag 2026-08-25 Abend — Fixes implementiert (Audit P0/P2 + Jury-Robot-Liste):**

- **P0 Geheimnisfilter serverseitig, live:** `serialize_state_payload`/`serialize_scene_stack`/Socket-Snapshots sind rollengefiltert; Token-Events laufen über rollengetrennte Räume (`:dm`/`:players`/`:user:<id>`), Sichtbarkeitswechsel wird für Spieler als created/deleted übersetzt, EINE Sequenznummer pro Mutation, unsichtbare Mutationen senden `state:tick` (play-socket.js sollte das Event als seq-tragendes No-op registrieren — bis dahin kostet eine verdeckte Mutation einen gefilterten Resync). Szenario-Tests zuerst geschrieben (§10): [tests/test_playtable_audit_fixes.py](../tests/test_playtable_audit_fixes.py), 5/5 grün; 48 angrenzende Bestandstests grün; fullsession-Robot 0 Findings.
- **P2 Würfel-Persistenz:** interne `roll_dice`-Würfe landen als `ChatMessage(content_type="dice_roll")` in derselben Historie wie Beyond20 — Reload löscht nichts mehr.
- **Jury-Robot-Fixes in strict_journey:** `_wait_visual_settle` (Playwright zählt `opacity:0` als sichtbar — Geisterbild-Klasse abgestellt), Tastatur-Gate prüft jetzt auch vertikalen Anschnitt mit einmaligem scrollIntoView (Jury D4/D5), und die tote Zwei-Schritt-Login-Erwartung (`#passwordLoginContinueBtn`) ist entfernt — der committete Login navigiert im selben Tick; `login-submitted` ist jetzt ein ehrlicher In-Flight-Capture (Jury-Befund 3). Validiert: Journey läuft auf Chromium+Firefox wieder komplett durch; neuer echter A11y-Fund dabei: Login-Seiten ohne sichtbare Landmark (medium, an Codex).
- **Gleicher Stale-Fix chirurgisch in `tools/robots/session.py`** (Datei ist in Codex' Baustelle — mit Datumskommentar markiert): dadurch Kulissen-Check **passed über alle 8 Zellen inkl. Telefon** — der „Phone-Login-Regression"-Verdacht von heute Mittag war die veraltete Robot-Erwartung.
- **stil_lint ausgeweitet** (Jury-Befund 5): Umlaut-Ersatz-Scan über `vtt/static/js` + `content_defaults.py` mit erweitertem Muster; Ratchet neu eingefroren bei **584 Hex / 10 Umlaut-Ersatz** (Hex stieg von 556 durch die Login-Arbeit — Argument, den Ratchet ins Deploy-Gate zu hängen). Der separate Rendered-Text-Scan bleibt Upgrade-3-Backlog.
- **Crawler-Härtung:** Re-Login-Ergebnis wird geprüft (vorher liefen Folgeverträge unbemerkt ausgeloggt weiter). Stand: Codex' Commits haben Dashboard-Knöpfe umbenannt („Zur Gildenübersicht", „Vorbereitung öffnen") → Textverträge brauchen §13-Pflege; frische Inventur liegt im letzten Crawler-Lauf.
- **Bewusst NICHT angefasst** (Codex' uncommittete Dateien): Kampf-Anschluss + Charakterbogen-Panel (P1, brauchen `play.html`/`play-ui.js`) — bereit zum Bau, sobald seine Play-Änderungen committed sind.

**Nachtrag 2026-08-25 Nacht — Spieltisch auf Vordermann (Audit P1+P2 umgesetzt):**

Szenarien zuerst (§10): [test_playtable_audit_fixes.py](../tests/test_playtable_audit_fixes.py) jetzt 8/8 (Combat-Filterung, Presence dazu), fullsession um drei Phasen erweitert (server_encounter, sheet_at_table, presence_roster) — **kompletter End-to-End-Lauf grün, exit 0, 0 Findings**.

- **Kampf-Anschluss (P1):** Der Tisch fährt jetzt das getestete Combat-Backend — „Kampf starten" (Server würfelt Initiative inkl. Dex), Rundenanzeige „Runde N · Am Zug: X", aktive Zeile markiert, „Nächster Zug", „Kampf beenden"; Spieler sehen alles live. Dabei ein neues P0-Loch VOR Live-Gang gestopft: Combat-Payloads re-serialisieren alle Teilnehmer-Tokens — Events/State sind jetzt rollengefiltert (versteckte Teilnehmer raus aus participants UND initiative_order; verdeckter aktiver Akteur maskiert; DM-Raum voll, Spieler-Raum gefiltert, Owner persönlich).
- **Charakterbogen am Tisch (P1):** Bogen-Lade rechts (`#sheetDrawer`), öffnet vom Token („Bogen öffnen" für Besitzer/Operator, `character_id`-Verknüpfung), Escape schließt. Dafür `X-Frame-Options` DENY→SAMEORIGIN + CSP `frame-ancestors 'self'` (Fremd-Framing bleibt blockiert).
- **Presence (P2):** `presence:update`-Roster bei Join/Leave/Disconnect; Chip „Am Tisch: …" in der Statusleiste.
- **Protokoll-Erkenntnis:** Der Client verwirft wiederholte `event_seq` als stale → bei Mehr-Raum-Varianten gilt „spezifischste zuerst" (DM → Owner → Spieler); Emitter entsprechend geordnet. `state:tick` ist jetzt clientseitig als seq-tragendes No-op registriert (Resync-Kosten verdeckter Mutationen entfallen).
- **Nebenbefunde gefixt:** (a) REST-Token-Endpunkte broadcasten jetzt (vorher waren REST-erzeugte Tokens bis zum Reload unsichtbar — Robot-Fund); (b) `.play-empty-state` überschrieb per `display:grid` das `hidden`-Attribut — der Leerzustand lag IMMER über dem Tisch (Robot-Screenshot-Fund, Ein-Zeilen-Fix); (c) Robot-Reports schreiben in den Lauf-Workdir statt nach `/tmp` (root-Altdateien → PermissionError).
- **Offener Layout-Befund an Codex:** die geöffnete rechte Sidebar überdeckt die Floating-Widgets und fängt deren Klicks ab (drei Robot-Treffer; Robot umgeht per DOM-Klick, UI-Fix steht aus).

**Offen vor B3-Start (Reihenfolge, Stand 2026-08-25):**

1. **Mensch (Adrian):** `baseline_review.html` des Abnahmelaufs öffnen, reviewen, `--promote --note` ausführen, Baselines committen — hebt den `blocked`-Status des Abnahmelaufs.
2. WebKit installieren (`venv/bin/playwright install --with-deps webkit`) — wegen der iOS-Befunde aus §8.1 (Kulissen-Verhalten weicht genau dort ab) keine Kür, sondern Pflichtmatrix.
3. Crawler + stil_lint in `run_all.py` einhängen — **nach** Codex' Commit (run_all ist dort gerade uncommitted in Arbeit; §-Kollisionsvermeidung).
4. **B3-Netz spannen:** die 23 undokumentierten Elemente aus `inventory.json` (Rail-Links, Szenen-Aktionen, Guild-Knöpfe) vertraglich erfassen, DANN erst die Blätter-Engines konsolidieren — die Ein-Engine-Prüfung des Crawlers ist das Regressionsnetz für genau diesen Umbau.
5. Danach: Kulissen-Check (V1/V2) auf die frisch eingefrorenen Baselines aufsetzen.

### Ursprüngliche Reihenfolge (Referenz)

Angedockt an den bestehenden Phasenplan des Journey-Annex (Phase 0–5) und die Designbrief-Phasen B1–B7 — kein neuer Parallelplan, sondern Einsortierung:

1. **Jetzt (parallel zu B1):** Registry-Format festlegen + Verträge für Login/Dashboard schreiben (die Selektoren aus `strict_journey.CRITICAL_SELECTORS` sind der Startbestand). R4-Lints verdrahten — aber nicht handstricken: `stylelint-declaration-strict-value` als Subprozess mit JSON-Ausgabe, dazu eine Ratchet-Baseline-Datei im Repo (Verstoß-Zahl steigt ⇒ rot; sinkt ⇒ Baseline automatisch runter — Betterer-Muster, Belege §8.4). Billigster Ertrag der ganzen Flotte. §11-Canaries als Fixture-Seite anlegen.
2. **Mit B2 (Seitenmodell):** R2-Crawler bauen, zuerst nur Dashboard + Navigation (F5). R12 auf Gate-E-Niveau heben (4xx, requestfailed, Fonts). R6-Baselines für die B2-Seiten einfrieren, inkl. **Kulissen-Check** (Scroll-Treppe für V1–V3; siehe §5b).
3. **Mit B3 (Blätter-Engine):** §3-Doppelausführung (Klick vs. Tastatur) in R2; R8 axe + Tastatur-Journey; R3-Funnel-Budgets für F1/F2/F5.
4. **Mit B4/B6/B7 (Tisch & Telefon):** Verträge für den Spieltisch inkl. Drag-Verträgen (Token ziehen → Position persistiert, andere Clients sehen es — Anschluss an R10). R11-FPS-Messung beim Token-Drag. Telefon-Funnels F4.
5. **Danach:** R5-Laufzeit-Stil-Audit (braucht den fertigen Token-Katalog aus B1/B2 als Referenz), R9-Chaos-Affe, R7-KI-Jury, R11-Budgets aus gesammelten Trends.

---

## 7. Grenzen (was die Flotte nicht kann)

Aus dem USER_BEHAVIOR-Annex übernommen und hier verbindlich: Die Robots beweisen Erreichbarkeit, Wirkung, Konsistenz und Regression — sie beweisen **nicht**, dass Menschen die Hierarchie verstehen, Spaß haben oder sich nicht überfordert fühlen. Dafür bleiben: menschlicher Screenshot-Review vor Commit (Haus-Disziplin), die KI-Jury als Verstärker, und echte Playtests mit Spielern als eigene Erkenntnisquelle. KI-Jury-Findings und Mensch-Findings werden getrennt von Mess-Findings ausgewiesen (Gate-I-Taxonomie).

---

## 8. Praxisbelege aus dem Feld (Web-Recherche 2026-08-24)

Vier parallele Recherche-Stränge zu Beispielen und Erfahrungsberichten: Kulissen/Parallax, Screenshot-Testing im Alltag, Alles-Klicker/Crawler, und Durchsetzung (Tokens/A11y/Funnels/Sprache). Nur Primärquellen und Erfahrungsberichte; reines Vendor-Marketing wurde aussortiert. Zuerst die Konsequenzen, dann die Belege.

### 8.0 Was sich dadurch am Plan konkret ändert

1. **Kulissen-Check korrigiert:** keine `fullPage`-Screenshots, zwei Viewport-Höhen pro Mobil-Profil, innere Scroll-Container explizit scrollen (eingearbeitet in §5b).
2. **V1-Bauweise:** iOS ignoriert `background-attachment: fixed` absichtlich → Codex baut die Kulisse als `position: fixed`-Ebene oder mitwachsende Fläche (eingearbeitet in §5b-Präambel).
3. **V3 aufgewertet:** scroll-gekoppelte Bewegung hat dokumentierte Gesundheitsfolgen (Schwindel/Migräne bei vestibulären Störungen) — Empfehlung: V3 wie einen A11y-Blocker behandeln, nicht wie Politur. Freigabe bleibt bei Adrian.
4. **R6 bekommt drei Betriebsregeln:** genau *eine* gesegnete Render-Umgebung (gepinnter Container), Null-Flake-Politik mit Quarantäne-Liste, Massen-Rebaseline als geplante Batch-Operation statt 200 Einzel-Diffs.
5. **R6-Umfang kuratiert:** wenige zusammengesetzte „Galerie-Screens" pro Fläche statt „alles screenshotten" — Review-Aufmerksamkeit ist die echte Währung, nicht Speicherplatz.
6. **R4 nicht handstricken:** `stylelint-declaration-strict-value` + Ratchet-Baseline im Repo (eingearbeitet in §6).
7. **R2-Reset erstklassig:** Reload + Reach-Path-Replay, Artefakte pro Klick, Containment, Seeds (eingearbeitet in §2.2).
8. **R8-Bericht zweispaltig:** „maschinell geprüft" vs. „braucht Mensch" — automatisierte Tools finden nur ~40 % bekannter Barrieren; ein grüner axe-Lauf heißt nie „barrierefrei".
9. **Sprach-Lint invertieren:** zusätzlich zum Template-Grep ein Rendered-Page-Scan auf englische Leck-Strings (Bibliotheks- und Server-Meldungen entgehen jedem Key-Vollständigkeits-Lint).
10. **§7-Klick-Budgets sind Neuland:** kein einziges dokumentiertes Vorbild für „Klick-Anzahl als CI-Gate" gefunden — die Schwellen erfinden wir selbst und führen sie als Ratchet.

### 8.1 Kulissen & Parallax (Belege zu den V-Regeln)

- iOS-WebKit unterstützt `background-attachment: fixed` **absichtlich nicht** — von WebKit-Ingenieuren als „by design" markiert, Stand April 2026 offen ([WebKit-Bug 275247](https://bugs.webkit.org/show_bug.cgi?id=275247)); der etablierte Workaround ist eine separate `position: fixed`-Ebene ([CSS-Tricks](https://css-tricks.com/the-fixed-background-attachment-hack/)).
- Flickrs Homepage-Parallax lief 2013 mit 80-ms-Frames (Budget: 16 ms), weil Scroll-Handler `marginTop`/`backgroundPosition` mutierten; der Wechsel auf `translate3d`-GPU-Ebenen fixte es ([Flickr Engineering](https://code.flickr.net/2013/06/04/adventures-in-jank-busting-parallax-performance-and-the-new-flickr-home-page/)). Googles Referenz dazu: nur Compositor-Animationen, „don't guess it, test it" ([web.dev](https://web.dev/articles/speed-parallax)) → R11 misst Frame-Zeiten *während* gescripteter Scrolls, nicht nur Endpixel.
- Selbst korrektes JS-Parallax **reißt prinzipbedingt** auf Browsern mit asynchronem Scrolling — Mozillas Diagnose am Firewatch-Site-Beispiel: „Any parallax implementation that uses JS will have similar problems" ([Bugzilla 1292013](https://bugzilla.mozilla.org/show_bug.cgi?id=1292013)) → der Kulissen-Check sollte später auch *mid-fling* screenshotten (während des Momentum-Scrolls), nicht nur an gesetzten Stufen.
- Die „weiße Lücke unter dem Inhalt"-Klasse auf Mobil kommt aus der 100vh-vs-URL-Leisten-Falle; Fixes: `svh`/`dvh` oder eine fixe Ebene ([dev.to-Analyse](https://dev.to/nirazanbasnet/dont-use-100vh-for-mobile-responsive-3o97), [Workaround-Gist](https://gist.github.com/TomDawson/624763cea7cf4392c239b6845a3831ba)). Und: Overscroll-Rubber-Banding zeigt die Farbe von `html`, nicht `body` — ist nur `body` bemalt, blitzt Weiß hinter dem „Buch" ([peter.coffee](https://peter.coffee/htmls-background-color)) → deckt V2 als billigen Computed-Style-Check.
- Parallax/Scroll-Effekte verursachen bei vestibulären Störungen dokumentierte reale Beschwerden bis Bettruhe; Branchen-Konsens: unter `prefers-reduced-motion` stillstellen ([web.dev](https://web.dev/articles/prefers-reduced-motion), [A List Apart Erstbericht](https://alistapart.com/article/accessibility-for-vestibular/), [WCAG 2.3.3](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)) → Begründung für Konsequenz Nr. 3.
- Playwright-`fullPage`-Screenshots sind für fixe Kulissen das falsche Werkzeug: fixe Elemente wiederholen sich in gestitchten Aufnahmen ([#33506](https://github.com/microsoft/playwright/issues/33506)), Inhalte innerer Scroll-Container fehlen komplett ([#12962](https://github.com/microsoft/playwright/issues/12962)), und `fullPage` kann das Rendering selbst verändern ([#20859](https://github.com/microsoft/playwright/issues/20859), [#29968](https://github.com/microsoft/playwright/issues/29968)).
- Gute Vorbilder mit belastbaren Writeups: Firewatch-Launch-Site (Mehr-Ebenen-Parallax, [Nachbau-Analyse](https://medium.com/@hamstu/recreating-the-firewatch-parallax-effect-213694d42f4e)), Flickr 2013 (s. o.), Keith Clarks [Pure-CSS-Parallax](https://keithclark.co.uk/articles/pure-css-parallax-websites/) (Compositor-only, aber: eigener Scroll-Container nötig — genau der Fall, in dem der Robot den Container statt `window` scrollen muss).

### 8.2 Screenshot-Testing im Alltag (Belege zu R6/R7)

- Houseful (Zoopla) stabilisierte ~200 flakige Visual-Tests: Ursache war fast nie die Diff-Engine, sondern Nichtdeterminismus der Seite (async Skripte, Ladezustände, Animationen, Dritt-Inhalte); Fixes: Daten mocken, Spinner explizit abwarten, `animations: disabled`, Masken, kleinste stabile Region screenshotten — plus eine **Null-Flake-Politik**: flakiger Test wird sofort gefixt oder in Quarantäne, sonst stirbt das Vertrauen in Rot ([Houseful-Postmortem](https://www.houseful.blog/posts/2023/fix-flaky-playwright-visual-regression-tests/)).
- Cross-OS-Baselines scheitern sofort (win32-Baselines vs. Linux-Runner); Praxis-Antwort: genau eine gepinnte Render-Umgebung, notfalls als „Playwright-Server im Docker-Container", mit dem sich lokale Läufe und CI verbinden — Baselines werden byte-identisch ([Duncan Mackenzie](https://www.duncanmackenzie.net/blog/visual-regression-testing/), [Playwright-Server-Setup](https://patricktree.me/blog/consistent-visual-assertions-via-playwright-server-in-docker)). Passt direkt auf unseren Wegwerf-Stack.
- Langzeit-Erfahrung aus der Praxis: schon kleine OS-/Browser-Updates lassen Baselines **massenhaft** platzen; das eigentliche Kostenzentrum ist das Regenerieren — Massen-Rebaseline also als geplante, menschlich freigegebene Batch-Operation einplanen ([HN-Praktikerthread](https://news.ycombinator.com/item?id=21812532)).
- Netlify (2.200+ Storybook-Stories, 50+ CI-Läufe/Tag) screenshottet bewusst **nicht** alles, sondern kuratierte Sammel-Stories — Review-Aufmerksamkeit ist der Engpass ([Netlify](https://www.netlify.com/blog/storybook-visual-regression-testing/)). Shopify Polaris dagegen screenshottet jede Komponente pro PR und macht den Diff zum PR-Gate ([Polaris-README](https://www.npmjs.com/package/@shopify/polaris)) — beide bestätigen: **nur akzeptierte Diffs werden Baseline, nie automatisch** (unser §6).
- Anti-Aliasing-/Font-Rauschen: kleine Toleranz (`maxDiffPixelRatio`) plus standardisierte Masken von Tag 1, statt Pixel-Perfektion pro Test zu tunen ([Shakacode](https://www.shakacode.com/blog/flaky-visual-regression-tests-and-what-to-do-about-them/)).
- KI-Bildmodelle als Reviewer: zuverlässig bei Farb-Drift, Abständen, Schriftgewichten, fehlenden/doppelten Elementen; **unzuverlässig beim Zählen und bei Pixelkoordinaten** ([Praktiker-Synthese 2026](https://www.digitalapplied.com/blog/screenshot-driven-ui-development-vision-models-2026)). Verifizierte Applitools-Nutzerberichte nennen Re-Approval-Aufwand und CI-Kopplung an externe SaaS als reale Kosten ([G2-Reviews](https://www.g2.com/products/applitools/reviews?qs=pros-and-cons)). Kein einziger belastbarer Bericht einer LLM-Jury als *alleiniges* Gate gefunden → bestätigt unsere R7-Entscheidung „beratend, nie Blocker" und: der Jury nie Zähl-Aufgaben geben (Würfel-Pips!).

### 8.3 Alles-Klicker & Crawler (Belege zu R2/R9)

- Facebooks Sapienz fand per automatischer UI-Erkundung hunderte einzigartige Crashes pro Monat, 75 % der Reports wurden als echt eingestuft und gefixt; getestet wird bewusst **durch die UI**, weil UI-reproduzierbare Fehler quasi keine False Positives haben ([Meta Engineering](https://engineering.fb.com/2018/05/02/developer-tools/sapienz-intelligent-automated-software-testing-at-scale/)) → Signal-Rausch-Disziplin: jeder Totmann-Fund braucht Dedup + reproduzierbaren Klickpfad.
- Crawljax (peer-reviewed, industriell validiert) ist die Blaupause für den Crawler: Kandidaten-Klickables aus dem DOM sammeln, feuern, **DOM-Diff mit Normalisierern als Orakel** („kein Diff auf keinem Kanal = toter Knopf"); und seine härteste Ingenieurs-Lehre: Ajax-Zustände lassen sich nur per Reload + exaktem Event-Replay wiederherstellen ([ACM-TWEB-Paper](https://dl.acm.org/doi/10.1145/2109205.2109208), [PDF](https://people.ece.ubc.ca/amesbah/resources/papers/tweb-final-old.pdf)).
- Googles Firebase Robo-Test (Produktions-Crawler für Millionen Apps) ist bewusst **deterministisch** und liefert pro Aktion einen annotierten Screenshot plus Video; gescriptete Preludes (Login) vor dem freien Crawlen sind eingebaut ([Robo-Docs](https://firebase.google.com/docs/test-lab/android/robo-ux-test)) → unser Muster: Login-Prelude, dann vertragsgetriebenes Klicken.
- gremlins.js-Praxisbericht unter Playwright: Console-Monitor nötig, `target="_blank"`-Tabs schließen, und die Horde „entkommt" bei Multi-Page-Navigation aus der App ([Quality-Duck-Bericht](https://www.thequalityduck.co.uk/build-better-front-ends-with-automated-monkey-testing-and-gremlins-js/), [gremlins.js-Seeding](https://github.com/marmelab/gremlins.js/)) → Containment-Politik für R9.
- Industrieller Model-Based-Testing-Erfahrungsbericht: echte Gewinne, aber die Arbeit verlagert sich ins **ständige Nachpflegen des Modells**, Pfad-Explosion inklusive ([arXiv-Erfahrungsbericht](https://arxiv.org/abs/2104.02152)); `@xstate/test` wurde deprecated → bestätigt unsere flache Vertrags-Registry gegen ein App-weites Zustandsmodell. Höchstens winzige Per-Widget-Maschinen (Würfel-Modal, Token-Drag).
- Selektor-Debatte: Role+Name zuerst (doppelt als A11y-Prüfung — ein Vertrag ohne accessible name ist ein Gratis-A11y-Finding), `data-testid` als Fallback ([Kent C. Dodds](https://kentcdodds.com/blog/making-your-ui-tests-resilient-to-change), [Gegenposition](https://dev.to/marktnoonan/why-i-rarely-use-getbyrole-testing-library-and-the-first-rule-of-aria-4581)) → Registry speichert beide; Widerspruch zwischen beiden ist ein Warn-Finding (Selektor-Drift).
- DB-Isolation beim Massen-Klicken: ein Team dokumentiert fünf gescheiterte Strategien gegen echtes Postgres bei Parallelität ([Playwright #33699](https://github.com/microsoft/playwright/issues/33699)) → keine Transaktions-Tricks durch den Browser; destruktive Verträge seriell mit Stack-/DB-Snapshot-Restore, nicht-destruktive parallel.

### 8.4 Durchsetzung: Tokens, A11y, Funnels, Sprache (Belege zu R3/R4/R5/R8)

- **GDS-Experiment** („die unzugänglichste Webseite der Welt", 143 bekannte Barrieren): das beste automatische Tool fand ~41 %, alle zehn zusammen 71 % — 29 % blieben für jede Automatik unsichtbar ([GDS-Blog](https://accessibility.blog.gov.uk/2017/02/24/what-we-found-when-we-tested-tools-on-the-worlds-least-accessible-webpage/), [Repo mit Barrieren-Katalog](https://github.com/alphagov/accessibility-tool-audit)). Deques Gegenzahl (57 %) misst Issue-*Volumen*, nicht Kriterien-Abdeckung ([Deque](https://www.deque.com/blog/automated-testing-study-identifies-57-percent-of-digital-accessibility-issues/)). Beide zusammen: axe hart-failen lohnt (fast keine False Positives), aber der Report braucht die Zwei-Spalten-Wahrheit (Konsequenz Nr. 8). Der GDS-Katalog verpasster Barrieren ist eine fertige Spec für Eigen-Checks — z. B. „Links ohne Farbe unterscheidbar", im Sepia-Buch-Theme besonders relevant.
- **Token-Durchsetzung bei den Großen:** Shopify erzwingt Polaris-Tokens mit 40+ kategorisierten Stylelint-Regeln und misst damit zugleich Adoption pro Kategorie ([stylelint-polaris](https://polaris-react.shopify.com/tools/stylelint-polaris)); Atlassian trennt Durchsetzung (Lint + Autofix) von Messung (Adoption-Scanner über die gerenderte App) ([Atlassian Design Tokens](https://atlassian.design/tokens/design-tokens/)) — Präzedenz für unser R4+R5-Paar. Ratchet-Tooling ist reif: [Betterer](https://phenomnomnominal.github.io/betterer/docs/tests/) senkt die Baseline automatisch bei Verbesserung, failt nur bei Verschlechterung; das Plugin der Wahl ist [stylelint-declaration-strict-value](https://github.com/AndyOGo/stylelint-declaration-strict-value) ([Praxis-Writeup](https://www.michaelmang.dev/blog/linting-design-tokens-with-stylelint/)).
- **Fokus-Sichtbarkeit automatisiert:** Tab-Journey mit `toBeFocused()` plus Computed-Style-Prüfung des Indikators — wichtig: „Outline vorhanden" reicht nicht, sie muss Breite > 0 **und** nicht-transparente Farbe haben; genau in Themes mit eigenen Fokus-Ringen (unser Buch!) verstecken sich unsichtbare Indikatoren ([Green-Report-Rezept](https://www.thegreenreport.blog/articles/testing-focus-order-and-visibility-for-wcag-compliance/testing-focus-order-and-visibility-for-wcag-compliance.html)). Tastatur-Robot auf benannte kritische Journeys begrenzen — exhaustives Durch-Tabben über der Kartenfläche ist flaky und aussagelos.
- **Robots als Deploy-Gates hat ein großes Vorbild:** GOV.UKs „Smokey" prüfte die kritischen Journeys alle paar Minuten gegen Produktion **und** war zugleich das Promotions-Gate im Deployment; Doktrin im README: jede Journey deckt nur einen kritischen Bereich, die Liste bleibt rigoros klein, sonst frisst Flakiness das Vertrauen ([alphagov/smokey](https://github.com/alphagov/smokey)). Dazu der Checkly-Mechanismus: CI-Journey-Robots und Produktions-Monitore sind **dieselben Skripte** mit Umgebungs-Schalter, sonst driften sie ([Checkly](https://www.checklyhq.com/blog/synthetic-monitoring-with-checkly-and-playwright-test/)).
- **Klick-Budgets: Negativ-Befund.** Trotz gezielter Suche kein dokumentiertes Vorbild für „Schritte/Klicks pro Aufgabe als CI-Gate" — die Praxis prüft Abschluss und Latenz, nicht Interaktions-Zahl. §7 ist also echtes Neuland: billig zu bauen (Klicks im Journey-Robot zählen, gegen Budget-Datei diffen), aber die Schwellen müssen wir selbst kalibrieren.
- **Sprach-Durchsetzung:** Hardcoded-String-/Key-Vollständigkeits-Linting ist reifes Tooling ([i18n-lint](https://github.com/jwarby/i18n-lint), [locize](https://www.locize.com/blog/missing-translations)); selbst GitLab kam zum Schluss, dass menschlicher Review unexternalisierte Strings nicht zuverlässig fängt ([GitLab-Issue](https://gitlab.com/gitlab-org/gitlab-foss/-/issues/57970)). Für unsere deutsche App ist der wertvollere Check der **umgekehrte**: gerenderte Seiten auf englische Leck-Strings scannen — Bibliotheks-Komponenten und Server-Fehlermeldungen entgehen jedem Template-Lint.

---

## 9. Quellen (zusätzlich zu den Annex- und §8-Quellen)

- [Visual Regression Testing for Design Systems: The 2026 Guide](https://lastest.cloud/blog/visual-regression-testing-design-systems-2026) — Token-Adoption 84 %, DTCG-Spec stabil, Token-Änderungen als Domino-Risiko
- [Visual Regression Testing in the Age of AI UIs (Augment Code)](https://www.augmentcode.com/guides/visual-regression-testing-ai-generated-uis) — warum KI-generierte UI-Änderungen eine visuelle Testschicht erzwingen
- [Who Leads the Pack in AI-Driven Visual Testing (askui)](https://www.askui.com/blog-posts/leading-ai-visual-testing-tools) / [TestMu AI: Visual Testing AI Agent](https://www.testmuai.com/blog/visual-testing-ai-agent/) — Stand der Technik semantisches Diff-Rauschfiltern
- [Visual Regression Tools Compared (Autonoma)](https://getautonoma.com/blog/visual-regression-testing-tools) — Werkzeuglandschaft 2026 (BackstopJS, Playwright-Snapshots, Chromatic, Percy, Applitools)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices) / [Assertions](https://playwright.dev/docs/test-assertions) / [Locators](https://playwright.dev/docs/locators) — Klick + Ergebnis-Assertion als Paar; Role/Name-Locators
- [BrowserStack: Playwright Assertions](https://www.browserstack.com/guide/playwright-assertions) / [Click/Type/Hover](https://www.browserstack.com/guide/playwright-click-type) — Element-State-Assertions (visible/enabled/focused) für die Crawler-Inventur
