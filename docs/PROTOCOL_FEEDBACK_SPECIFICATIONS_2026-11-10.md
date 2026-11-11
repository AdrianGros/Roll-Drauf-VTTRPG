# Technische Spezifikationen und Liefermatrix zum Protokollfeedback

Grundlage: fünf Gespräche vom 28.10., 05.11. und 08.11.2026; 40 zuvor erstellte
Kanbankarten. Sprecher sind keine technische Zuordnung. `Q1`–`Q5` entsprechen den
ursprünglichen Protokolldateien. Der detaillierte Vertrag für Paket 1 steht in
`DADM_APPLY_PROTOCOL_FEEDBACK_2026-11-10.md`; tatsächliche Veröffentlichung und
Nachweise stehen getrennt im Deploy-/Monitor-Bericht.

**Statusbegriffe:** „Paket 1“ bedeutet implementierter Umfang mit vorgesehenem
Prüfnachweis, bis zum Live-Nachweis keine Erledigt-Markierung. „Bestand“ bezeichnet
bereits laufende Funktionen. „Teilumfang“ lässt ausdrücklich weitere Arbeit offen.
„Offen“ bedeutet keine Implementierung in dieser Lieferung.

| Karte | Technischer Vertrag | Umfang / Nachweis |
| --- | --- | --- |
| VTT-01 | Attributwürfe als Multimenge behandeln; alle Summen sichtbar, erschöpfte Werte deaktiviert, Duplikate korrekt zuweisbar. Server prüft weiter die Summe. | Paket 1; Creator-Browsertest mit zwei 18ern und erneuter Zuordnung. |
| VTT-02 | Angelegte Startausrüstung muss aus gewählten Klassen-/Hintergrundpaketen stammen; Paketwechsel entfernt ungültige Anlegewahl. Finalisierung weist manipulierte Rüstung/Schild mit 422 zurück. Bestehende Charaktere behalten später erworbene Ausrüstung. | Paket 1; API-Negativfälle, Paket A/B/C, Inventar-Abnahme. |
| VTT-03 | Für konkret fehlenden Inhalt Quelle, Regelversion, Lizenz, ID, Voraussetzungen und verfügbare Klassenstufe erfassen; erst dann Daten-/Evaluatorfehler von absichtlich begrenztem SRD-Angebot unterscheiden. | Offen; keine konkrete fehlende Talent-/Unterklassen-ID aus dem Gespräch ableitbar. Keine fremden Regeltexte ergänzen. |
| VTT-04 | Einheitliche Stufenzeilen mit Charakterstufe, Klasse, Klassenstufe, TP und neuen Merkmalen; horizontales Scrollen bei kleinen Displays. | Paket 1; Creator-Stufentest. |
| VTT-05 | Einheitliche Feld-/Labelausrichtung für manuelle Werte und andere Creator-Auswahlen; kontrollierte Mindestbreite, kein verdecktes Label. | Paket 1; Creator-Styles und bestehende Browserflüsse. |
| VTT-06 | Text-/Hintergrundpaare mit mindestens 4,5:1 für normalen Text; Auswahl außerdem über Rand und Zustand. Konfigurierbare Nutzerfarben benötigen eigene validierte Farbpalette. | Teilumfang: neue Creator-/Bogen-Komponenten; Nacht-Kontrasttest. Beliebige konfigurierbare Buttons bleiben offen. |
| VTT-07 | Gewählte Zaubercheckbox bleibt nach Rerender/Filter sichtbar als gewählt markiert; Auswahl über Eingabezustand und hervorgehobenen Rand. | Paket 1; Creator-Styles und bestehende Zauber-Auswahltests. |
| VTT-08 | Berechtigter Kampagneneintrag bietet Gruppenübersicht mit konkreter Kampagnen-ID; Nichtmitglieder bekommen keinen privilegierten Hub-Einstieg. | Bestand in `buildCampaignLedger`; Gruppenziel wird im neuen Kampagnentest geprüft. |
| VTT-09 | Zwei berechtigte Firefox-Sessions an derselben Session; Würfel-ID muss genau einmal bei Absender und Empfänger erscheinen. Reconnect und andere Session als Negativfall. | Offen; Firefox-Bogenprüfung ist kein Nachweis der Socket-Übertragung. Zusammen mit Tischkontext-Paket abnehmen. |
| VTT-10 | Getrennte Player-/DM-Komposition; servererteilter, widerrufbarer und pro Tab gebundener Tischkontext. Player darf weder DM-Handler initialisieren noch DM-Daten/Events empfangen. Alle HTTP-/Socket-/Legacy-Pfade gemäß Entscheidung 01.11. abnehmen. | P1 am 11.11. implementiert und technisch live geprüft; [Monitor/Nachweise](DADM_MONITOR_PLAYTABLE_CONTEXTS_2026-11-11.md). Gemeinsame Owner-Abnahme separat. |
| VTT-11 | Ortsliste selektiert vorhandenes Label, öffnet den Inspektor und fokussiert Namensfeld. Name/Typ/Lore über bestehenden Projektvertrag speichern und erneut laden. | Paket 1 ergänzt Auffindbarkeit; bestehende Editier-/Dateirundlauf-Tests und Live-Bibliotheksreise. |
| VTT-12 | Aktive Ebene auf der Leinwand benennen; direkter Einstieg in Ebenenverwaltung. Bestehende Hinzufügen-/Umbenennen-/Löschen-/Undo-Aktionen weiterverwenden. | Paket 1; Pan-/Ebenentest und bestehende Ebenenregression. |
| VTT-13 | Initialbereich Spielen; separate Tabs für Zauber, Inventar, Merkmale und Verwaltung. Verborgene Inhalte müssen ihre bestehenden Handler behalten; Würfelergebnis bleibt bereichsübergreifend sichtbar. | Paket 1; Tastatur, Tabnavigation, Inventar, Aufstieg und Verwaltung in Browsern. |
| VTT-14 | Kopf mit Avatar, Token, Name, Klasse/Stufe; Bilder begrenzt und mit Alternativtext. Uploadzugang im Verwaltungsbereich. | Paket 1; 1440/390/320 px, Uploadzugang geprüft. |
| VTT-15 | Münzen und angelegte Gegenstände im Kopf aus Inventarantwort anzeigen; fehlendes Startinventar deutlich melden. Initialladen und jede Inventaränderung aktualisieren Anzeige. | Paket 1; Münzupdate auf 37 GM und bestehende Inventarprüfungen. |
| VTT-16 | Deduplicierte bekannte/vorbereitete/Buch-Zauber mit Zugehörigkeit; Filter Grad und Name. Filter ist Anzeige, keine Änderung vorbereiteter Zauber. | Paket 1; Browsertest mit tatsächlichem Grad und Trefferzahl. |
| VTT-17 | Creator-Filter sticky im vorhandenen Scrollcontainer, kompakte mobile Form. Checkboxen unter Filter bleiben bedienbar. | Paket 1; CSS und Creator-Browserprüfungen. |
| VTT-18 | Klassenmerkmale aus versionierten Klassendaten je Klassenstufe ableiten, Mehrklassigkeit zählt je Klasse. | Paket 1; zusätzliche Spalte im vorhandenen Stufenverlauf. |
| VTT-19 | Startgegenstände benennen Quelle und Paket; Boni verwenden vorhandene Evaluationsherkunft. Weitere Boni ohne Herkunft müssen einzeln reproduzierbar erfasst werden. | Teilumfang: Rüstungs-/Schildbesitz erklärt. Vollständige Bonus-Provenienz bleibt offen. |
| VTT-20 | Bereits autorisierte Kampagnen lokal nach Name/Beschreibung filtern; maximal fünf sichtbare Zeilen, Seitensteuerung, Treffer-/Leerstatus. DOM-Zeilen erhalten laufende Einladungseingaben. | Paket 1; 50 Kampagnen in Chromium und Firefox, Suchtreffer am Listenende. |
| VTT-21 | Im SRD-Bogen Pergament/Nacht als lokale Darstellungspräferenz; Schrift, Flächen und Formulare abgestimmt. Nicht als globaler Darkmode ausweisen. | Teilumfang: SRD-Spielbogen; übrige VTT-Seiten bleiben eigenes Gestaltungspaket. |
| VTT-22 | UI-Texte zuerst nach stabilen Schlüsseln inventarisieren, DE-Fallback und Sprachpersistenz definieren; DE/EN als nächster fachlicher Umfang. Übersetzungen nicht mit Regelwerkversionen vermischen. | Offen; vollständiger Textkatalog und geprüfte Übersetzungen fehlen. FR/ES bleiben nachgelagerter Umfang. |
| VTT-23 | Kanonische Bewegung in Metern unverändert speichern; reine Anzeige m/ft mit D&D-Verhältnis 1 ft = 0,3 m. Präferenz lokal, Reload hält Auswahl. | Teilumfang: Bewegung im SRD-Bogen. Kartenraster und sonstige Distanzen benötigen gesonderten Vertrag. |
| VTT-24 | Konto-Abmeldebutton mit lesbarer Schrift, passender Fläche/Rand und mindestens 32 px Höhe; vorhandener Logout bleibt zuständig. | Paket 1; Nav-Browserprüfung und Live-Abmeldung. |
| VTT-25 | Hauptnavigation → Charaktere → Held anlegen führt direkt `/srd-creator`; alter Create-Intent leitet dorthin weiter. | Bestand; bestehender SRD-Test und Live-Creator-Reise. |
| VTT-26 | Frischer Editor öffnet bewusste Auswahl Bibliothek/leer/Template; Silbermark nur auf ausdrückliche Templatewahl. Eigenes Autosave wird erhalten. | Bestand; vollständige Mapmaker-Tests und frischer Live-Browserkontext. |
| VTT-27 | Rechte Maus startet Pan-Geste mit Pointer Capture; Werkzeug, Dokumentgeneration und Undo unverändert. Danach primäre Zeichenfunktion weiter nutzbar. | Paket 1; Browser-Gestenprüfung, Chromium und Firefox live. |
| VTT-28 | Jeden Homebrew-Typ mit Schema, Quelle, Revision, Zulässigkeit im Creator und Wirkung im Evaluator definieren. Zunächst Hintergründe/Merkmale; Creation-Engine-Rassen sind kein Nachweis aller Typen. | Offen; benötigt eigenen Inhalts-/Evaluationsvertrag und Migration bestehender Entwürfe. |
| VTT-29 | Persönliche Hotbar speichert deklarative Aktionsreferenzen je Spieler/Charakter/Slot; Server validiert Kontext, Ressourcen und Aktion bei jeder Ausführung. Kein frei ausführbarer JS-Code. | Offen; abhängig von VTT-10, keine DM-Toolbar im Player umbenennen. |
| VTT-30 | Bedienaufgaben mit Rolle, Browser, Einstieg, Soll/Ist und Repro; automatisierte Prüfungen und Live-Reisen als nachvollziehbare Evidenz ablegen. | Teilumfang: technische Prüfungen und Abnahmecheckliste in dieser Lieferung; externe Feedbacksammlung bleibt offen. |
| VTT-31 | Vollständiger Spielabend mit menschlicher DM-/Player-Runde und Firefox; Würfel, Wechsel, Reload, Datenrechte und Restfehler protokollieren. | Offen; automatisierter Smoke-Test ersetzt keinen vollständigen Spielabend. |
| VTT-32 | Generator liefert Vorschau einer Landmaske aus Seed; erst Übernehmen erzeugt eine rückgängig machbare Änderung auf gewählter Rasterebene. Bestehende Karte nicht ungefragt ersetzen. | Offener Entwurf; Qualitäts-/Laufzeitgrenze und gewünschte Kartenformen fehlen. |
| VTT-33 | Erster Atlas-Vertrag: Orte referenzieren stabile IDs, Karten und separat berechtigte Wissenseinträge; Spieler-/DM-Lore getrennt. Zoom/Navigation ohne neue Veröffentlichung fremder Daten. | Offen; Setting-Datenmodell und gewünschter erster Nutzungspfad noch festzulegen. |
| VTT-34 | Visueller Arbeitsplatz zunächst als Prototyp mit vorhandenen Datenverträgen, Tastatur und speicherbaren Layouts; kein paralleles ungeprüftes Regel-/Sheetformat. | Entscheidung offen; kein Architekturwechsel aus dem Gespräch allein. |
| VTT-35 | Jeder zusätzliche Asset-Eintrag braucht Urheber, Ursprung, konkrete Lizenzversion und Attribution; Import nur bei vollständigem Nachweis. Bestehender Katalog und Credits bleiben erhalten. | Bestand wird geschützt; angebotene zusätzliche Dateien/Lizenzen liegen nicht vor, daher keine neuen Pakete eingebaut. |
| VTT-36 | Technische Spielreife und externe Streamingfreigabe getrennt dokumentieren; Testrollen/-teilnehmende und Streamumfang ausdrücklich definieren. | Produktentscheidung offen; diese technische Lieferung erteilt keine Partner-/Streamingfreigabe. |
| VTT-37 | Repro muss konkretes Steuerelement, Ausgangswert, 200-%-Aktion und Fehlwirkung benennen. Danach erst zulässigen Wertebereich begründen. | Offen wegen unklarem Bezug; keine willkürliche Zoom-/Pinselgrenze. |
| VTT-38 | Optionales Sticky-Porträt nur bei Platz, abschaltbar und mit Reduced-Motion-Verhalten. Nicht Voraussetzung für kompakten Bogen. | Zurückgestellt; statische kompakte Kopfporträts sind geliefert. |
| VTT-39 | Dezente Goldkante als sekundäres Gestaltungsmittel; aktive Auswahl zusätzlich mit Zustandsattribut, Form/Rand und Kontrast. | Im neuen Bogen umgesetzt; kein Zwang zur globalen Neugestaltung. |
| VTT-40 | Ausgangs-Regelwerk, Nutzungsrechte und Sprachversion fixieren; Übersetzung mit Glossar, stabilen Entry-IDs, Quellenbezug und fachlicher Prüfung. | Offen; Gespräch klärt nicht eindeutig eigenes Regelwerk versus SRD/Oglan-Inhalte. Keine automatische Vollübersetzung veröffentlichen. |

## Nächste eigenständige Apply-Verträge

1. **Tischkontexte und Spieleraktionen:** vollständige Route-/Eventinventur,
   widerrufbare Kontexte, Bootstrap-/Resync-Filter, getrennte Bundles,
   Rollen-/Tab-/Reconnect-Negativmatrix; danach Hotbar und Firefox-Übertragung.
2. **Regelinhalte:** reproduzierbare fehlende IDs, Homebrew-Schemata und
   Creator-/Evaluatorbindung. Keine Quellen ohne gesicherte Rechte ergänzen.
3. **Darstellung und Sprache:** globaler Theme-/Einheitenumfang, Textinventar,
   DE/EN-Qualität und Regelwerkübersetzung getrennt.
4. **Weltwerkzeuge:** Generator und Atlas mit eigenen Daten-/Lore-Rechten;
   die unklare 200-%-Äußerung benötigt zunächst ein benanntes Bedienelement.

Diese Matrix dokumentiert verbleibende Arbeit ausdrücklich. Paket 1 ist keine
Vollständigkeitsbehauptung über alle 40 Karten.

Fortsetzung vom 11.11.: Der [autonome Programmplan](plans/PROTOCOL_FEEDBACK_PROGRAM_2026-11-11.md)
ordnet die Restarbeit in P0–P7 und verbindet alle Karten mit einem gemeinsamen
[Live-Abnahmelauf](acceptance/PROTOCOL_FEEDBACK_LIVE_RUN_2026-11-11.md).
Das ist ein Planungsstand; neue Pakete sind dadurch nicht implementiert oder abgenommen.
