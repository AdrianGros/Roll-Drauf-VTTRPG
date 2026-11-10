# Apply: Protokollfeedback in technische Lieferpakete übersetzen

Status: technischer Vertrag für Paket 1; Übergabe an Deploy. Owner autorisiert
Entwurf, Umsetzung und Live-Lieferung mit Auftrag vom 10.11.2026.
Aufbewahrung: dauerhaft. Grundlage: Discover vom gleichen Datum und 40 Kanbankarten.

## Ziel und Paketgrenzen

**Paket 1 – Creator, Spielbogen und Kartenbedienung:** vorhandenen SRD-Creator und
Karteneditor weiterverwenden; keine neue UI-Bibliothek, keine neuen App-Abhängigkeiten
und keine Bestandsdatenmigration. Die Rekonstruktion des produktiven Standes ist
Commit `5bb9ae9bd`; neue Funktionalität wird gesondert committed.

**Eigenes Paket 2 – Tischkontexte und Hotbar:** die vollständige Entscheidung
`PLAYTABLE_ROLE_SEPARATION_2026-11-01.md` ist maßgeblich. Bestehende globale Sitzplätze
reichen dafür nicht. Dieses Paket benötigt vor Implementierung einen eigenen Apply-
Vertrag mit Kontextentzug, Tabbindung, Daten-/Socketgrenzen und Legacy-Verhalten.
Paket 1 berührt weder Autorisierungswege noch Tischaktionen und behauptet diese
Anforderung nicht als erledigt.

**Weitere fachliche Pakete:** Kompendiums-/Homebrew-Umfang, vollständige
Oberflächen-/Regelwerkübersetzungen, Weltatlas, Landmassenerzeugung und visuelles
Sheet-Authoring erhalten eigene Verträge. Vorab-Streaming bleibt eine ausdrücklich
offene Produktfreigabe. Ein veröffentlichter Editor-Fix erteilt sie nicht implizit.

## Recherche und begründete Entscheidungen

- [W3C APG Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/): Spielbogenbereiche
  bekommen Tablist/Tab/Tabpanel, `aria-controls`, `aria-labelledby`, roving Tabindex,
  Pfeiltasten/Home/End. Automatische Aktivierung ist hier passend, weil die Inhalte
  bereits geladen und ein Tabwechsel sofort darstellbar ist.
- [W3C Kontrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html):
  Textfarben werden auf ihren Hintergrund abgestimmt; pauschal weiße Schrift behebt
  das Problem bei hellen Farben nicht. Auswahl wird außerdem mit Rand/Zustand markiert.
- [MDN Sticky](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/position):
  Zauberfilter bleibt im tatsächlichen Scrollcontainer erreichbar. Auf kleinen
  Displays darf er nicht den gesamten Viewport überdecken.
- [MDN Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events)
  und [Pointer Capture](https://developer.mozilla.org/en-US/docs/Web/API/Element/setPointerCapture):
  rechte Maustaste als zusätzliche Pan-Geste im bestehenden Inputmodell; das aktive
  Werkzeug bleibt gleich. Dokument, Undo und Autosave werden durch Panning nicht verändert.
- [MDN Contextmenu](https://developer.mozilla.org/en-US/docs/Web/API/Element/contextmenu_event):
  Editor verhindert das native Kontextmenü auf der Leinwand; Browser-Sonderfälle,
  insbesondere Firefox, werden im Browser geprüft.
- [Playwright Browser](https://playwright.dev/python/docs/browsers): passendes Chromium
  und Firefox für dieselbe automatisierte Abnahme; Browser-Abhängigkeiten nur im
  separaten Prüfimage, nicht als neue Anwendungsabhängigkeit.

## Oberflächen- und Datenverträge für Paket 1

### Charaktererstellung

1. Attributzuordnung zeigt alle unterschiedlichen Werte des Würfelsets. Der Text
   nennt ihre Gesamt-/Restanzahl; ausgeschöpfte Werte bleiben sichtbar, aber sind
   für eine weitere unzulässige Zuweisung deaktiviert. Duplikate sind als Multimenge
   zu behandeln. Servervalidierung bleibt die maßgebliche Regelgrenze.
2. Jede Zeile des Stufenverlaufs zeigt zusätzlich Klassenstufe und auf dieser
   Klassenstufe gewährte Merkmale, auch bei Mehrklassigkeit.
3. Startausrüstung unterscheidet Paketbesitz und tatsächlich angelegte Ausrüstung.
   Rüstungen/Schilde werden aus den gewählten Klassen-/Hintergrundpaketen ermittelt;
   ein Paketwechsel verwirft nicht mehr vorhandene angelegte Gegenstände. Die UI
   erklärt Herkunft und den späteren Inventarimport. Bestehende Charaktere werden
   nicht stillschweigend umgeschrieben. Regel-/Inventarprüfung muss Manipulationen
   bei neuer Finalisierung separat abdecken.
4. Zauberauswahl erhält eindeutigen ausgewählten Zustand, gut erreichbare Filter
   und konsistente Form-/Tabellendarstellung. Keine Quellen außerhalb vorhandener
   lizenzierter Inhalte werden ergänzt.

### Kompakter Spielbogen

1. SRD-Spielbogen bekommt eigene Bereiche: **Spielen, Zauber, Inventar, Merkmale,
   Verwaltung**. Spielen ist der Initialbereich; Attribut-/Fertigkeitswürfe und
   Kerndaten bleiben dort direkt erreichbar. Tabwechsel erhält bestehende Aktionen.
2. Kopfbereich zeigt Name, Klasse/Stufe, Avatar/Token und eine kurze Münzübersicht.
   Upload-/Inventarverwaltung bleibt über ihre bestehenden Funktionen erreichbar.
3. `SheetFeedback.compose(character, detail, creatorData, nodes)` komponiert die
   bereits vorhandenen, sicher über Textknoten aufgebauten Bereiche. IDs der
   Inventar-/Stufen-/Verwaltungs-Roots bleiben erhalten. Keine neuen Datenrechte.
4. Inventarladen/-änderung aktualisiert die Münzübersicht über den vorhandenen
   onChange-Callback. Ohne übernommenes Startinventar wird das deutlich gesagt.
5. Zauber nach Grad filtern; Daten stammen aus dem bestehenden Creator-Datensatz.
   Auswahl verändert keine vorbereiteten Zauber und gibt keine unbekannten Zauber frei.
6. Darstellungspräferenzen Pergament/Nacht sowie m/ft sind reine Browserpräferenzen.
   Gespeicherte Spielwerte und Rollen werden dadurch nicht verändert. Fehlender
   Browserstorage darf die Seite nicht blockieren.

### Karteneditor

1. Rechtsziehen verschiebt in jedem Werkzeug die Ansicht; aktives Werkzeug und
   Dokument bleiben unverändert. Pinsel-/Stempelgesten mit primärer Taste sowie
   Touch/Pinch und Abbruch behalten ihre bisherigen Verträge.
2. Orte bleiben über **Orte → Ort auswählen → Werkzeug/Inspektor** bearbeitbar;
   expliziter Bearbeitungshinweis und Eingabefokus verbessern die Auffindbarkeit.
3. Aktive Ebene bekommt einen direkt erreichbaren Einstieg ins vorhandene
   Ebenenmanagement; Hinzufügen/Löschen werden nicht neu implementiert.
4. Startauswahl, private Bibliothek, Revisionskontrolle, Import/Export und der
   aktuelle Künstlerkatalog bleiben erhalten. Kein automatisch geladenes Template.

### Kampagnen und Navigation (ergänzter Apply-Vertrag)

1. Die bereits serverseitig erlaubte Kampagnenliste wird nach Name/Beschreibung
   lokal durchsuchbar und zeigt höchstens fünf Einträge pro Seite. Vor/Zurück,
   Trefferanzahl und leerer Trefferzustand sind beschriftet. Filterwechsel setzt
   die Seite zurück. Die Liste verändert keine Sichtbarkeits-/Beitrittsrechte.
2. Blättern blendet vorhandene Zeilen aus; laufende Einladungseingaben bleiben
   erhalten. Einzelne Hubs und die Gruppenübersicht behalten ihre bisherigen Ziele.
3. Abmelden erhält einen lesbaren, zur Kontokarte passenden Button mit mindestens
   32 px Höhe; Authentifizierungs- und Abmeldeablauf bleiben unverändert.
4. Abnahme: 50 erlaubte Kampagnen, letzter Treffer über Suche und Seitenwechsel,
   kein Treffer, Filter löschen, Gruppenlink und beide Browser. Neue Testdaten
   bleiben ausschließlich in der lokalen Testdatenbank; Live nur eigene Inhalte.

## Akzeptanz und technische Nachweise

- Creator: doppelte Würfelsummen, vollständige Zuordnung, erneute Zuweisung,
  Stufen/Mehrklassigkeit, Paketwechsel und getragene Ausrüstung.
- Spielbogen: Initialübersicht, Tastaturtabs, Zaubergradfilter, Münzupdate,
  Bilder/Uploadzugang, Inventar- und Stufenaktionen. 1440/390/320 px, kein Überlauf.
- Karten: malen → rechts verschieben → weitermalen, unveränderte Dokumentrevision
  beim Panning, Undo/Redo, Orte editieren, Ebenen erreichen und Dateirundlauf.
- Angemeldete Live-Reisen für vorhandene Player-/DM-Testkonten über Hauptnavigation.
  Nur eigene synthetische Testcharaktere/-karten; bestehende Benutzerinhalte nicht ändern.
- Commit/Push, Overlaydateiliste und SHA-256, vorheriges und neues Image,
  tatsächliche Compose-Dateien, Health und Rollback dokumentieren.

## Risiken, Rollout und Deploy-Handoff

Das Ausgangsimage bleibt als Rollback erhalten. Overlay nur mit den im Paket
geänderten Pfaden; vor Umschaltung prüfen, dass die Produktion noch auf der
inventarisierten Basis läuft. App allein über die aktiven Compose-Dateien neu
erstellen, Datenbank/Redis/Mail nicht neu starten. Bei fehlgeschlagenen fachlichen
Prüfungen nicht ausliefern; bei Live-Regression auf das vorherige Image zurückstellen.

Die tabellarische Kanban-Zuordnung wird im Deploy-/Monitor-Nachweis fortgeschrieben:
bereits vorhanden, geändert und geprüft, oder weiterhin eigenes offenes Paket.
Paket 1 darf nicht als Abschluss aller 40 Punkte oder der vollständigen
Playtable-Rollentrennung bezeichnet werden.
