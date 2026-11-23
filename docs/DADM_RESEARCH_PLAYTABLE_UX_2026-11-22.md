# Research: komplexer Playtable, einfache Bedienung

Status: fokussierter Research-Review, keine Produktionsimplementierung. Recherche am 22.11.2026. Drei wissenschaftliche Studien plus vier Fachartikel/Design-Leitlinien, jeweils am Primärtext geprüft. Grundlagenstudien werden ausdrücklich als ältere Evidenz eingeordnet; die neueste ausgewählte Journalveröffentlichung gehört zum Jahrgang 2026. Dies ist keine systematische Vollerhebung der gesamten HCI-Forschung.

## Fragestellung und Methode

Wie lässt sich der Funktionsumfang des DM-Spieltischs zugänglich machen, ohne den dauerhaften Suchaufwand, Fehlbedienungen und visuelle Unruhe weiter zu erhöhen? Gesucht wurden empirische Vergleiche statischer, adaptiver und vom Benutzer anpassbarer Menüs, Untersuchungen komplexer Produktivsoftware sowie aktuelle Apple-Leitlinien für Werkzeugleisten und Informationshierarchie. Suchbegriffe umfassten „static adaptive adaptable menus“, „multiple interface bloated software“, „adaptive user interfaces performance preferences“ und „Apple HIG toolbars layout progressive disclosure“.

Eingeschlossen: begutachtete Originalstudien mit nachvollziehbarer Stichprobe/Versuchsanordnung und Originalartikel der jeweiligen Designautoren. Ausgeschlossen: bloße Produktwerbung, unbelegte „7±2 Buttons“-Regeln, Sekundärzusammenfassungen anstelle verfügbarer Volltexte und Apple-Optik als vermeintlicher Wirksamkeitsnachweis. Für die Studien wurden Methoden, Ergebnisse und Grenzen gelesen, nicht nur Suchtreffer oder Abstracts. Primär-PDFs werden verlinkt und nicht erneut im Repository veröffentlicht.

## Drei wissenschaftliche Studien

### S1 — Kompakte persönliche Oberfläche mit vollständigem Rückweg

McGrenere, Baecker & Booth (CHI 2002): *An Evaluation of a Multiple Interface Design Solution for Bloated Software*. [Autoren-Volltext](https://www.dgp.toronto.edu/~joanna/papers/JMcGrenere_CHI_2002.pdf), [DOI 10.1145/503376.503406](https://doi.org/10.1145/503376.503406).

20 erfahrene bzw. mittel-erfahrene Word-Nutzer nahmen ungefähr sechs Wochen teil; die personalisierte Variante wurde vier Wochen verwendet. Eine reduzierte, selbst zusammengestellte Oberfläche blieb mit der vollständigen Oberfläche umschaltbar. Bei 19 vollständig geloggten Personen verwendeten 14 ihre persönliche Oberfläche mindestens während der Hälfte ihrer Arbeitszeit. Die wahrgenommene Navigation fiel zugunsten der persönlichen Variante aus. Zufriedenheits- und Kontrollbefunde waren differenzierter; nicht alle Vergleiche waren auf dem üblichen 5%-Niveau signifikant. Maßgeblich: S. 3–6, insbesondere Nutzungstabelle und Ergebnisdiskussion.

Grenzen: kleine Stichprobe, alte Desktopsoftware, keine VTT-Anfänger oder laufende Spielsitzungen. **Ableitung für uns:** freiwillige Pins mit brauchbarer Startbelegung sind plausibel; der vollständige Funktionszugang muss sichtbar erhalten bleiben. Keine Zusage, dass Personalisierung für jeden Nutzer schneller ist.

### S2 — Stabile Positionen, kontrollierte Anpassung

Findlater & McGrenere (CHI 2004): *A Comparison of Static, Adaptive, and Adaptable Menus*. [Universitäts-Volltext](https://www.cs.ubc.ca/labs/edapt/papers/findlater2004.pdf), [Publikationsseite](https://www.cs.ubc.ca/labs/imager/tr/2004/findlater04menus/).

27 Personen verglichen statische, automatisch angepasste und selbst anpassbare Split-Menüs im Labor. Statisch war schneller als automatisch angepasst. Der Vorteil selbst anpassbarer Menüs hing unter anderem von der Reihenfolge und davon ab, ob die Personen tatsächlich personalisierten. 15 von 27 bevorzugten die selbst anpassbare Variante insgesamt; daraus folgt keine durchgängige statistische Überlegenheit gegenüber jeder anderen Variante. Maßgeblich: S. 5–7, Reihenfolgeeffekt und Diskussion zur Einführung der Anpassung.

Grenzen: begrenzte Auswahlaufgabe, keine komplexen Mehrfensterabläufe; die statische Variante profitierte von vorab bekannten Häufigkeiten. **Ableitung:** Positionen nicht unbemerkt nach Nutzungshäufigkeit verschieben. Anpassung bewusst auslösen, erklären und rücksetzbar halten. Die Studie belegt weder eine ideale Zahl von Werkzeugleisten-Buttons noch eine generelle Schädlichkeit jeder adaptiven Hilfe.

### S3 — Aktueller Vergleich: Präferenz und Leistung auseinanderhalten

Gaspar-Figueiredo, Vanderdonckt, Abrahao & Insfran: *User experience with adaptive user interfaces: Comparing performance and preferences*, Journal of Systems and Software 231 (2026), 112598; online 2025. [Universitätsnachweis und Autorenfassung](https://research.dial.uclouvain.be/entities/publication/43f870fe-7842-46f0-b223-d7c70932c074), [DOI 10.1016/j.jss.2025.112598](https://doi.org/10.1016/j.jss.2025.112598).

40 Personen verglichen 20 Menüvarianten mit statischer Referenz. Erfasst wurden Auswahlzeiten und EEG-basierte UX-Maße; Präferenzen wurden den Leistungsbefunden gegenübergestellt. Rangfolgen unterscheiden sich nach Zielgröße. Es gibt keinen universellen Gewinner für alle Varianten und Maße. Maßgeblich in der zugänglichen Autorenfassung: Abschnitte 5–7, insbesondere Zielkonflikte und externe Validität.

Grenzen: relativ kleine Aufgaben innerhalb kurzer Sitzungen; Autoren verlangen Replikationen mit komplexeren Aufgaben. EEG-abgeleitete Konstrukte sind keine direkte Messung unserer DM-Belastung; Vorliebe ist kein Ersatz für Aufgabenerfolg. **Ableitung:** die Entwürfe mit tatsächlichen Tischaufgaben vergleichen, statt den optisch beliebtesten Entwurf automatisch als den bedienbarsten zu behandeln. Keine ungetestete automatische Umordnung als Standard.

## Vier Fachartikel und Design-Leitlinien

### A1 — Apple: Toolbars

[Apple Human Interface Guidelines — Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars.md), aktueller Abruf 22.11.2026, insbesondere Best practices, Item groupings und macOS.

Apple priorisiert bewusst gewählte Hauptaktionen, logische Funktionsgruppen, stabile Anordnung und anpassbare Werkzeugleisten. Die Leiste soll nicht jede Funktion aufnehmen; seltenere Funktionen bleiben anderweitig erreichbar. Hauptnavigation, lokale Aktionen und Inspektorzugang bekommen erkennbare Bereiche. Die Empfehlung von ungefähr drei Gruppen ist Designpraxis, keine universelle experimentelle Grenze. Native systemverwaltete Overflow-Menüs sind eine plattformspezifische Umsetzung, keine direkt übernehmbare Web-API.

**Übertragung:** wenige stabile Gruppen, einheitliche Aktionsbausteine und ein vollständiger Auffindepfad. Apples Symbolpräferenz setzt erkennbare Standardsymbole voraus. Unsere Fachbegriffe wie Etagen, Spielersicht und Token-Layer rechtfertigen weiterhin sichtbare Textlabels. Transparenzeffekte werden nicht als Lösung für Bedienkomplexität übernommen.

### A2 — Apple: Layout

[Apple Human Interface Guidelines — Layout](https://developer.apple.com/design/human-interface-guidelines/layout.md), aktueller Abruf 22.11.2026, Visual hierarchy und Adaptability.

Gemeinsame Ausrichtung, klare Hierarchie und funktionale Gruppierung erleichtern die Zuordnung von Inhalt und Steuerung. Weitergehende Optionen werden bei Bedarf zugänglich. Das Layout soll bei anderen Breiten, Textgrößen und Sprachen verständlich bleiben.

**Übertragung:** Karteninhalt bleibt dominant; Status und Bedienung bekommen verschiedene feste Orte. Felder und Beschreibungen verwenden gemeinsame Abstände. Die schmale Ansicht braucht eine bewusste Priorisierung statt einer langen, standardmäßig seitlich abgeschnittenen Reihe. Die Quelle ist eine Hersteller-Leitlinie und kein kontrollierter Wirksamkeitsnachweis unserer konkreten Anordnung.

### A3 — Nielsen: Progressive Disclosure

[Jakob Nielsen — Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/), 03.12.2006, besonders Usability Criteria und Managing Complexity.

Häufig benötigte Funktionen gehören in die erste Ebene; spezialisierte Optionen in nachvollziehbar beschriftete zweite Ebenen. Beide falschen Extreme schaden: alles gleichzeitig anzeigen oder relevante Alltagsfunktionen verbergen. Die Grenzziehung benötigt Aufgabenanalyse und Beobachtung; Klickhäufigkeit allein kann auch Suchprobleme widerspiegeln.

**Übertragung:** komplexe Etagen- und Lichtformulare müssen nicht dauerhaft im Menüband stehen. Ihr Zugang darf aber nicht nur „Mehr“ ohne erkennbare Zuordnung heißen. Tiefe Kaskaden vermeiden. Diese ältere fachliche Synthese ist eine begründete Gestaltungsheuristik, keine zusätzliche vierte wissenschaftliche Studie.

### A4 — Kaley: Contextual Menus

[Anna Kaley — Contextual Menus: Delivering Relevant Tools for Tasks](https://www.nngroup.com/articles/contextual-menus/), 17.03.2019, Tips for Effective Contextual Menus.

Kontextmenüs zeigen relevante Aktionen zum aktuellen Objekt. Sichtbare Auslöser und zusätzliche Wege über die Hauptoberfläche sichern Auffindbarkeit; reine Rechtsklick- oder Gestenzugänge reichen nicht. Die Funktion muss vom Auslöser unabhängig gleich bleiben.

**Übertragung:** HP, Zustände und Token-Sichtbarkeit in einen benannten Figurenkontext bündeln. Globale Sitzungsaktionen dort nicht unmotiviert untermischen. Rechteabhängig fehlende DM-Funktionen bleiben auf der Player-Oberfläche vollständig unmontiert; die Empfehlung, kontextuell unbrauchbare Aktionen teilweise zu deaktivieren, ist keine Aufforderung, privilegierte Funktionen Spielern offenzulegen.

## Bewertung vor dem Konzept

Der belastbare gemeinsame Nenner ist **vorhersehbare Anordnung, verständliche Gruppierung und vom Nutzer kontrollierter Zugang zur Tiefe**. Daraus folgt keine einzelne wissenschaftlich bewiesene VTT-Anordnung. Insbesondere sind drei verschiedene Fragen getrennt zu bearbeiten:

1. **Was ist es?** Werkzeugmodus, Fensteröffner, Objektaktion, Navigation, Zustandsschalter oder reine Information.
2. **Wann wird es gebraucht?** Immer, bei ausgewählter Figur, in einer Kampfaufgabe, beim Vorbereiten oder nur bei Verwaltung. Diese Häufigkeiten sind derzeit Hypothesen; es liegen keine ausgewerteten Nutzungsdaten vor.
3. **Wie wird es dargestellt?** Gemeinsamer Buttonbaukasten mit konsistenter Größe, Schrift, Iconfamilie und Zuständen. Einheitliche Optik darf die verschiedenen Bedienregeln nicht verschleiern.

Eine reine Vereinheitlichung von Rahmen und Farben löst die vermischte Informationsarchitektur nicht. Eine Reduktion auf unbeschriftete Icons verschiebt Komplexität ins Gedächtnis. Ein zweiter „Einfachmodus“, der Funktionen unerreichbar macht, gefährdet fortgeschrittene Aufgaben. Eine immer automatisch wechselnde Leiste kann eingeübte Positionen entwerten. Diese Bewertung motiviert drei überprüfbare Alternativen; sie ersetzt keine Nutzerstudie.

## Ergänzende Zugänglichkeitsreferenz

Die [W3C-Erläuterung zu WCAG 2.2, SC 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) unterscheidet das AA-Minimum von 24 × 24 CSS-Pixeln mit Ausnahmen vom erhöhten 44 × 44-Ziel. Für den Tisch schlagen wir mindestens 44 × 44 und im normalen Dock 52 Pixel Höhe vor; 52 ist eine Konzeptentscheidung. [SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) nennt 4,5:1 für normalen Text. Sichtbare Beschriftung, Fokus, alternative Tastaturwege und Text statt reiner Farbcodierung gehören zur späteren Abnahme. Diese Referenzen sind zusätzliche normative Orientierung, nicht Teil der vier Fachartikel.

## Nächster Schritt und Aufbewahrung

Discover erfasst den tatsächlichen Bestand mit separatem Quellen-/Bildschirmnachweis. Apply stellt drei alternative Konzepte und lokale Mockups gegenüber. Erst eine spätere Entscheidung führt zur Umsetzung. Quellenverzeichnis, Inventar und Konzept haben Aufbewahrungsklasse Research/Audit; isolierte Browseraufnahmen werden nach ihrem Evidenzumfang beschriftet. Risiken: mittel bei ungetesteter Verlagerung kritischer Befehle, niedrig bei noch unbekannten Nutzungshäufigkeiten. Beides wird durch auffindbare vollständige Befehle und den beschriebenen Aufgabentest im Konzept adressiert.
