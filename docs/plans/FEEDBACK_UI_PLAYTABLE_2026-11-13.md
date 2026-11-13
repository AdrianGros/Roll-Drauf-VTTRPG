# Feedbackrunde: VTT-Oberfläche, Spieltisch und Karteneditor

Quelle: 12.11.2026, 18:03 UTC, 13:13 min · Abgleich: 13.11.2026 · vorgesehen für Donutarian.

**Status:** Discover abgeschlossen; dokumentiert und gegen den laufenden Stand abgeglichen. Keine neue Funktionsauslieferung aus dieser Aufnahme. Kein externer Kanban-Versand.

| Karte | Priorität | Bereich | Aufgabe | Status | Stelle |
| --- | --- | --- | --- | --- | --- |
| S01 | P2 | Einstellungen/Navigation | Einstellungen im Zahnrad rechts bündeln | Für Apply erfasst | 00:40–03:02;08:42–10:25 |
| S02 | P2 | Buchoptik | Nachtmodus als verbranntes Buch mit roten Akzenten | Für Apply erfasst | 00:40–02:06;03:23–04:00 |
| S03 | P2 | Regelinhalte/Sprache | Englisches SRD 5.2.1 als sprachabhängige Inhaltsfassung | Für Apply erfasst | 04:11–04:58 |
| S04 | P2 | Kalender | Vollen Monatskalender als reguläre Ansicht zeigen | Für Apply erfasst | 03:23–04:00 |
| S05 | P2 | Kartenbibliothek | Vorschaubild und kurzes Label in Own Library | Für Apply erfasst | 05:11–05:41 |
| S06 | P1 | Licht | Gemeldete Lichtfunktion im tatsächlichen DM-Kontext prüfen | Reproduzieren | 05:14–05:41 |
| S07 | P1 | Wände | Gemeldete Wandfunktion mit Sicht-/Lichtwirkung prüfen | Reproduzieren | 05:41–06:08 |
| S08 | P2 | Messen | Measure-Auswahl für Kegel, Kreis/Kugel und Quadrat | Für Apply erfasst | 05:41–06:08 |
| S09 | P2 | Tisch-Navigation | Hamburger, Zurück und App-Menü unterscheidbar machen | Für Apply erfasst | 06:08–06:49;08:42–10:25 |
| S10 | P1 | Navigation/Fehler | Toten Back-Maps-Einstieg korrigieren | Für Apply erfasst | 06:49–07:04 |
| S11 | P2 | Tisch-Arbeitsbereiche | Chat links und Journal rechts einordnen | Für Apply erfasst | 07:19–08:29 |
| S12 | P2 | Journal/Dateien | Journal als zentralen Datei- und Assetzugang nutzen | Für Apply erfasst | 07:19–08:29 |
| S13 | P2 | DM-Arbeitsfläche | DM-Bereiche als Karteireiter unten links bündeln | Für Apply erfasst | 08:29–09:20 |
| S14 | P3 | Konto/Komfort | Discord-Profilbild im Kontobereich anzeigen | Für Apply erfasst | 09:20–10:25 |
| S15 | P2 | Kampagnen/Kontingent | Erweiterung der Kampagnenplätze erreichbar machen | Produktgrenze klären | 09:20–10:25 |
| S16 | P2 | Charakterübersicht/Texte | Gruppen- und Leerzustandstexte passend anzeigen | Reproduzieren | 10:31–10:55 |
| S17 | P2 | Editor/Buchoptik | Karteneditor visuell in die übrige VTT-Oberfläche einordnen | Für Apply erfasst | 10:55–11:10 |
| S18 | P2 | Pinsel/Bildmaterial | Stempel oder Kachelausschnitte als weichen Bildpinsel verwenden | Für Apply; Cachefrage offen | 11:10–12:19 |
| S19 | P3 | Landmasse/Layer | Layer-Verhalten von Generate Landmass klären | Bereits vorhanden / Frage geklärt | 12:19–12:47 |
| S20 | P2 | Kampagnenhub/Karten | Karten im Kampagnenhub übernehmen und verwalten | Für Apply erfasst | 12:29–13:03 |

Der wiederholte Wunsch nach Pinsel-Formen (11:10–11:26) ergänzt **N08** aus der vorigen Aufnahme; S18 enthält die zusätzliche Bildpinsel-Anforderung.

## Befunde und Anforderung für Apply

### S01 – Einstellungen im Zahnrad rechts bündeln

**Heute:** Ansicht und Sprache steht als Textbutton in der Hauptnavigation und als Menüeintrag am Tisch. Ein gemeinsamer Präferenzdialog existiert.

**Anforderung:** Textbutton durch rechts erreichbares Zahnrad ersetzen; Darstellung, Sprache und weitere Anpassungen bleiben dort auffindbar. Back-Menü verwendet denselben verständlichen Einstellungsbegriff. Beschriftung Einstellungen/Options noch nicht endgültig entschieden.

**Belege:** `vtt/static/js/vtt-main-nav.js:105; vtt/static/js/display-preferences.js:72; vtt/templates/play.html:2777`. Zeitmarke: 00:40–03:02;08:42–10:25.

### S02 – Nachtmodus als verbranntes Buch mit roten Akzenten

**Heute:** Der gelieferte Nachtmodus benutzt dunkle Oberflächen und einen goldenen sicheren Standardakzent. Auf Buchflächen werden Hintergrundbilder im Nachtmodus teilweise ausgeblendet; neue verbrannte Buchgestaltung ist damit nicht vorhanden.

**Anforderung:** Buchrücken/Schriftzug und Buchcharakter erkennbar erhalten, dunkles verbranntes Pergament mit roten Akzenten gestalten. Lesbarkeit, Fokus und persönliche Akzentpräferenzen im Apply berücksichtigen. Keine konkrete Texturtechnik oder Farbwerte sind beschlossen.

**Belege:** `vtt/static/css/display-preferences.css:12,31; vtt/static/js/display-preferences.js:46`. Zeitmarke: 00:40–02:06;03:23–04:00.

### S03 – Englisches SRD 5.2.1 als sprachabhängige Inhaltsfassung

**Heute:** Der vorhandene SRD-Inhaltskatalog ist de-DE; die UI-Sprachwahl übersetzt ausdrücklich keine Regeltexte. Die offizielle englische Originalfassung derselben SRD-Version ist verfügbar.

**Anforderung:** Bei englischer Inhaltswahl passende originale SRD-Texte/Namen in Regelwerk, Compendium und den betroffenen CE-/Creator-Ansichten bereitstellen. Inhalte, Quellenverweise und Spielwerte müssen konsistent bleiben; eigene Namen werden nicht automatisch übersetzt. Bestehende deutsche Charakterdaten schützen.

**Belege:** `vtt/rules_content/srd-5.2.1-de/manifest.json; vtt/rules_content/generator.py:16; vtt/static/js/display-preferences.js:85`. Zeitmarke: 04:11–04:58.

### S04 – Vollen Monatskalender als reguläre Ansicht zeigen

**Heute:** Monatsraster mit Wochentagen und allen Monatstagen existiert auch bei null Einträgen. Tatsächlicher Renderer erzeugte 30 Tage/7 Überschriften sowie 29 Tage im Schaltfebruar. Standard ist derzeit rolling30, nicht Monat.

**Anforderung:** Monatsübersicht mit Wochenzeilen und Wochentagsköpfen ist der erwartete sichtbare Kalender; leere Monate bleiben voll dargestellt. Vorhandene Termin-/Zeitzonen-/Filterwege weiterverwenden.

**Belege:** `vtt/static/js/session-calendar.js:43,83; vtt/static/css/session-calendar.css:11`. Zeitmarke: 03:23–04:00.

### S05 – Vorschaubild und kurzes Label in Own Library

**Heute:** Die Liste enthält Titelbuttons und Größenangaben. Erst nach Auswahl wird eine eigene größere Vorschau erzeugt; eine Bildkachel je Listeneintrag fehlt.

**Anforderung:** Karten lassen sich visuell anhand kleiner Vorschauen auswählen; darunter kurze Bezeichnung. Bestehende ausdrückliche Freigabe sichtbarer Bildinhalte und private Projektquelle bleiben getrennt.

**Belege:** `vtt/static/js/play-map-library.js:118,153`. Zeitmarke: 05:11–05:41.

### S06 – Gemeldete Lichtfunktion im tatsächlichen DM-Kontext prüfen

**Heute:** DM-Lichtwerkzeuge und ihre Handler sind vorhanden. Das Protokoll nennt keinen konkreten Klickweg, Karten-/Sichtmodus oder Fehlerstatus; kein frischer Defekt nachgewiesen.

**Anforderung:** Im expliziten DM-Kontext Platzieren, Bearbeiten, sichtbare Wirkung und Wiederladen reproduzieren; Player-Ansicht und aktive Sicht-/Nebelkonfiguration berücksichtigen. Rollenprüfungen nicht zur Fehlerbehebung lockern.

**Belege:** `vtt/static/js/play-dm.js:112; vtt/templates/play.html:1030; tests/test_playtable_vision_fog.py`. Zeitmarke: 05:14–05:41.

### S07 – Gemeldete Wandfunktion mit Sicht-/Lichtwirkung prüfen

**Heute:** Wandwerkzeuge, Editierhandler und vorhandene Geometrie-/Sichttests existieren. Pauschale Aussage scheint nicht zu funktionieren belegt noch keine Ursache.

**Anforderung:** Im DM-Kontext Wand zeichnen, ändern, löschen, speichern und tatsächliche Sicht-/Lichtbegrenzung prüfen; Beobachtung und erwarteten Modus festhalten. Player erhält keine DM-Geometriewerkzeuge.

**Belege:** `vtt/static/js/play-dm.js:100; vtt/templates/play.html:1030; tests/test_playtable_vision_fog.py`. Zeitmarke: 05:41–06:08.

### S08 – Measure-Auswahl für Kegel, Kreis/Kugel und Quadrat

**Heute:** Das vorhandene Messwerkzeug speichert Wegpunkte und zeichnet Strecken mit Entfernungslabels. Ein Formauswahlmenü ist nicht vorhanden.

**Anforderung:** Beim Messen sind die gewünschten Flächenformen über ein einfaches Menü erreichbar; Maße, Ausrichtung und Abbruch sind verständlich. Bisherige kalibrierte Distanzen und getrennte Player-/DM-Kontexte erhalten. Ob Formen geteilt werden, ist im Apply abzugrenzen.

**Belege:** `vtt/static/js/play-ui.js:104,1328,1454; vtt/templates/play.html:2738`. Zeitmarke: 05:41–06:08.

### S09 – Hamburger, Zurück und App-Menü unterscheidbar machen

**Heute:** Hamburger öffnet Arbeitsbereiche; Zurück öffnet ein eigenes Sitzungs-/Navigationsmenü. Die Funktionen sind getrennt, ihre optische Unterscheidung wird als unklar erlebt.

**Anforderung:** Einheitliche, unterscheidbare Bedienelemente für Spielarbeitsbereiche und Navigation/Sitzungsaustritt. Einstellungseinstieg und Hilfe bleiben erreichbar. Konkrete Benennung/Icons im Apply festlegen.

**Belege:** `vtt/templates/play.html:2753,2754,2762; vtt/static/js/play-ui.js:845`. Zeitmarke: 06:08–06:49;08:42–10:25.

### S10 – Toten Back-Maps-Einstieg korrigieren

**Heute:** App-Menü bietet /mapmaker als Ziel an. _normalizeBookReturnTarget lässt genau dieses Ziel nicht zu; die originale Methode liefert null, während Kontrollziele akzeptiert werden. returnToBook wirft anschließend Invalid book return target.

**Anforderung:** Back → Karten erreicht den vorgesehenen Karteneditor über den normalen Einstieg. Gültige bisherige Rückwege, Sitzungsgrenzen und Entwurfsschutz bleiben erhalten; normaler DM- und Player-Klickweg gesondert prüfen.

**Belege:** `vtt/templates/play.html:2769; vtt/static/js/play-ui.js:726,830`. Zeitmarke: 06:49–07:04.

### S11 – Chat links und Journal rechts einordnen

**Heute:** Reihenfolge ist derzeit Journal, Chat, Tools, Session. Session enthält Hinweise und einen rollenabhängigen DM-Steuerungsbereich; die Rubrik ist nicht generell funktionslos. Zunächst nennt das Protokoll Tools als Ersatz für Session, anschließend Journal als Ersatz und rechten Einstieg. Daraus ist keine zusätzliche doppelte Tools-Leiste abzuleiten.

**Anforderung:** Chat steht links, Journal rechts. Die leer wirkende Session-Rubrik entfällt als unnötiger Einstieg; erforderliche Hinweise und DM-Sessionsteuerung bleiben passend erreichbar, ebenso die bestehenden Tools. Endgültige Reihenfolge im Apply am aktuellen Rollenlayout festlegen.

**Belege:** `vtt/templates/play.html:2819`. Zeitmarke: 07:19–08:29.

### S12 – Journal als zentralen Datei- und Assetzugang nutzen

**Heute:** Journal zeigt derzeit Aktivität und Map-Notizen. Bestehende Asset-/Tokenwege sind andere Oberflächen, kein zentraler Journal-Intake.

**Anforderung:** Sessionbezogene Dateien/Assets/Tokens sind im Journal auffindbar und berechtigt verwaltbar, hochladbar und bearbeitbar. Sichtbarkeit und Besitz bleiben je Rolle/Ressource wirksam. Roll20 dient als genannte Bedienreferenz, nicht als beschlossener Nachbau.

**Belege:** `vtt/templates/play.html:2829; vtt/static/js/play-ui.js`. Zeitmarke: 07:19–08:29.

### S13 – DM-Bereiche als Karteireiter unten links bündeln

**Heute:** Seiten, Turn Order und Tokens werden über den Tischbereich geöffnet. Gewünscht ist eine feste Karteireiter-Navigation unten links, unabhängig von der Playbar; auch Layerwechsel ist genannt.

**Anforderung:** DM erreicht diese Bereiche an einer klaren Stelle ohne verteilte leere Menüs. Player-Komposition initialisiert weiterhin keine DM-Werkzeuge oder Handler. MMO-/Gamification-Anregung ist optional, kein zusätzliches Spielsystem.

**Belege:** `vtt/templates/play.html:2752; vtt/static/js/play-dm.js; vtt/static/js/play-player.js`. Zeitmarke: 08:29–09:20.

### S14 – Discord-Profilbild im Kontobereich anzeigen

**Heute:** Der gemeinsame Kontobereich baut derzeit Name, Sessionanzahl und An-/Abmeldeaktion auf; kein Bild wird dort angelegt.

**Anforderung:** Vorhandenes berechtigtes Discord-Profilbild kann ergänzend angezeigt werden; ohne Bild bleibt der Kontobereich nutzbar. Kein neuer Loginanbieter oder Profilzwang.

**Belege:** `vtt/static/js/vtt-main-nav.js:148`. Zeitmarke: 09:20–10:25.

### S15 – Erweiterung der Kampagnenplätze erreichbar machen

**Heute:** Kampagnenkontingent ist am Konto vorhanden und wird bei Erstellung beachtet. Das Protokoll wünscht einen Erweiterungsweg, nennt jedoch weder neue Anzahl noch Berechtigung oder Tarifmodell.

**Anforderung:** Produktgrenze und berechtigten Erweiterungsweg festlegen. Kein neues Zahlenlimit erfinden oder Kontingente still erhöhen. Die offene Freigabe eines vierten Donutarian-Testplatzes wird durch diese allgemeine Anforderung nicht beantwortet.

**Belege:** `vtt/models/user.py:46,163; vtt/auth/routes.py:191; docs/proofs/feedback-final-2026-11-13/owner-campaign-status.json`. Zeitmarke: 09:20–10:25.

### S16 – Gruppen- und Leerzustandstexte passend anzeigen

**Heute:** Die Rubrik Characters in your groups entspricht dem Bereich geteilter Kampagnencharaktere; für leere Ergebnisse gibt es einen eigenen Hinweis. Der Ausdruck no check lässt sich keinem eindeutigen Literal zuordnen.

**Anforderung:** Eigene und geteilte Charaktere sowie leere/fehlerhafte Ladezustände sind verständlich unterschieden. Konkreten störenden Zustand reproduzieren, keine Rubrik allein wegen leerer Inhalte entfernen.

**Belege:** `vtt/static/js/book-scene.js:1645; tools/i18n/extra-messages.json:302`. Zeitmarke: 10:31–10:55.

### S17 – Karteneditor visuell in die übrige VTT-Oberfläche einordnen

**Heute:** Werkstattlayout wird auch hier grundsätzlich gelobt, aber als Stilbruch beschrieben. N19 enthält das frühere positive Feedback dazu, keine Pflicht zum dauerhaft abweichenden Design.

**Anforderung:** Gemeinsame Navigation/Markenelemente und Papier-/Nachtgestaltung sind erkennbar. Gelobte Werkstattfunktionen, Bedienfläche und aktuelles Speichern bleiben erreichbar. Keine neue Editor-Engine allein für die Optik.

**Belege:** `vtt/static/mapmaker/index.html; vtt/static/js/vtt-main-nav.js; docs/plans/FEEDBACK_CHARACTER_MAPMAKER_2026-11-13.json`. Zeitmarke: 10:55–11:10.

### S18 – Stempel oder Kachelausschnitte als weichen Bildpinsel verwenden

**Heute:** Bilder können als Stempel/Kacheln gesetzt werden. Normales Stempelbildladen ist teilweise bereits bedarfsgesteuert und merkt ausstehende Ladevorgänge; das ist noch keine Umwandlung eines Bildausschnitts in eine Pinselspitze.

**Anforderung:** Ein gewähltes Bild bzw. ein Ausschnitt ist als anpassbarer weicher Pinsel nutzbar. Kontur/Weichheit und bestehende Projektwege berücksichtigen. Umwandlung bei Erstnutzung statt Vorberechnung ist eine vorgeschlagene Optimierung, noch keine gewählte Cache-/Speicherarchitektur.

**Belege:** `vtt/static/mapmaker/js/stamps.js:127; vtt/static/mapmaker/js/brush.js:138`. Zeitmarke: 11:10–12:19.

### S19 – Layer-Verhalten von Generate Landmass klären

**Heute:** Übernehmen legt eine neue Rasterebene an und macht sie aktiv; Undo entfernt diese Ebene und stellt die vorherige aktive Ebene wieder her. Vorschau/Abbruch verändern keine Ebene. Das wurde im bestehenden finalen Live-Lauf geprüft.

**Anforderung:** Offene Frage beantwortet: Funktion ist bereits layerbezogen. Übermalen einer bestehenden ausgewählten Ebene wäre ein anderer, noch nicht konkret verlangter Umfang.

**Belege:** `vtt/static/mapmaker/js/landmass-dialog.js:124; docs/proofs/feedback-final-2026-11-13/live-landmass.json`. Zeitmarke: 12:19–12:47.

### S20 – Karten im Kampagnenhub übernehmen und verwalten

**Heute:** Der Hub kennt Kampagnenkarten und zeigt die aktive Karte. Die private Projektbibliothek und bestätigte Snapshot-Übernahme existieren am DM-Tisch; ein gleichwertiger Bibliotheks-/Verwaltungsweg im Hub ist in dessen aktuellem Markup nicht vorhanden.

**Anforderung:** DM erreicht die Kartenverwaltung und Übernahme direkt im Hub. Bestehende Bibliotheksprojekte, freizugebende Bildfassung und Kampagnenkarten bleiben klar unterschieden; keine versteckten privaten Quellen mitveröffentlichen.

**Belege:** `vtt/static/js/book-scene.js:1168; vtt/static/js/play-map-library.js; docs/proofs/feedback-final-2026-11-13/live-landmass.json`. Zeitmarke: 12:29–13:03.

## Anschluss

[Gemeinsame Priorisierung beider neuen Runden](FEEDBACK_NEXT_ROUND_2026-11-13.md) · [strukturierte Karten](FEEDBACK_UI_PLAYTABLE_2026-11-13.json) · [Discover-Bericht](../DADM_DISCOVER_UI_PLAYTABLE_FEEDBACK_2026-11-13.md).

Die Anforderung vollständiger englischer SRD-Inhalte konkretisiert den bisher offenen Sprachumfang I04/VTT-40. Sie behauptet keine bereits erfolgte Inhaltsauslieferung; der gelieferte UI-Katalog bleibt davon getrennt.
