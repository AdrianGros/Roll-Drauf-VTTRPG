# DAD-M Discover: Roll Drauf Character Creator (SRD 5.2.1, Parität)

Date: 2026-10-18
Status: Discover abgeschlossen, wartet auf Review (Zuständig: Content Lead / Abnahme-Owner)
Vorgänger: Regelwerk 1.0.0 (live), Compendium C1 + C2 (live, Image `regelwerk-113e001`)

## 1. Ziel

Ein Charakter-Ersteller im Roll Drauf VTT mit dem Funktionsumfang eines modernen
Online-Creators (Parität in der Nutzerführung und im Funktionsumfang), vollständig
eigenständig umgesetzt auf den veröffentlichten SRD-5.2.1-Daten (`srd-5.2.1-de`).

Parität heißt hier: gleiche Fähigkeiten für Spielende, nicht gleicher Inhaltsumfang.
Der Inhalt ist auf den SRD-Umfang begrenzt (12 Klassen mit je 1 Unterklasse,
9 Spezies, 4 Hintergründe, 17 Talente, 339 Zauber). Alles darüber hinaus läuft über
die Creation Engine (Homebrew, Eigenbau-Spezies) und bleibt Sache der Spielenden.

## 2. Rechtliche und technische Leitplanken

- Keine fremden Quellcodes, Assets, Texte oder nicht-SRD-Inhalte; kein REA-Repo
  (vom Owner ausdrücklich verworfen). Wir bauen aus Funktionsbeschreibungen und
  eigenen Entwürfen, nicht durch Übernahme fremder Implementierung.
- Regelinhalt ausschließlich aus dem veröffentlichten Paket (CC BY 4.0); die
  Namensnennung bleibt in jeder Ansicht erreichbar, die SRD-Text zeigt.
- Berechnete Regeln (Modifikatoren, Übungsbonus, TP, RK, Zauberplätze) sind
  eigener Code gegen Regeln, nicht gegen Fremdcode.
- Kein Zugriff auf Fremdkonten, keine Anmelde-Imports, kein Scraping.
- Der Ersteller schreibt nie ins Regelwerk-Paket; das Paket bleibt unveränderlich.

## 3. Ist-Zustand (aus dem Code, nur gelesen)

| Baustein | Stand |
|---|---|
| `models/character.py` | Zeilenmodell mit 6 Attributen, TP, RK, Übungsbonus, `character_data` (JSON), Relationen Spells / Equipment / Inventory. Kein Regelsystem-Bezug außer `character_data.roll_drauf_light`. |
| Roll-Drauf-Light-Ersteller (`characters.html`, 3 Schritte) | Identität (Spezies, Fraktion, Klasse, Hintergrund), Attribute, "Bereit für den Bogen". Auf eigenen Katalog `vtt/roll_drauf/catalog.py` mit Stufen 1-5 begrenzt, `progression.py`, `POST /characters/<id>/level-up`. |
| Charakterbogen (`character-sheet.html`) | Kernwerte, Zauber, Ausrüstung, Inventar als freie Eingabe (Name, Stufe, Schule). Keine Regelverknüpfung, keine Berechnung aus Klasse/Spezies. |
| D&D-5e-Portabel-Import (`dnd5e_portable.py`) | Versioniertes JSON `dnd5e_character`, importierter Regeltext wird nie ausgeführt. |
| Creation Engine (`vtt/creation_engine/`) | Versionierte Entwürfe, Revisionen, Spezies-Homebrew-Profil mit Übergabe auf neue oder bestehende Charaktere (`race-to-sheet-2026-09-28.md`); geführter Modus. Bestehende Verträge (1.1.4 / core 1.1.3 / A1) bleiben eingefroren. |
| Regelwerk-Compendium | Abfragbare Entitäten mit stabilen IDs, Facetten und Detailansicht; Zauberlisten je Klasse aus Zauberzeilen abgeleitet; Endpunkt `/api/rulesets/srd-5.2.1-de/compendium(/entry/<id>)`. |

Folgerung: Es gibt keinen Ersteller für SRD 5.2.1. Der vorhandene Ersteller ist ein
anderes System (`roll_drauf_light`, Stufe 1-5). Beide müssen nebeneinander laufen.

## 4. Paritäts-Matrix (Funktion, Datenquelle, Lücke)

Priorität: M = muss für "benutzbar", S = soll, K = kann später.

| # | Funktion | Daten (vorhanden) | Lücke / Eigenbau | Prio |
|---|---|---|---|---|
| 1 | Ersteller-Assistent mit Reihenfolge Klasse, Herkunft (Hintergrund + Spezies), Attribute, Ausrüstung, Zauber, Details, Prüfung | Klassen, Spezies, Hintergründe | Neuer Assistent, Zustand serverseitig als Entwurf | M |
| 2 | Klassenwahl mit Vorschau (TW, Hauptattribut, Rettungswürfe, Rüstungs-/Waffenübung, Fertigkeitswahl, Stufe-1-Merkmale) | `class` + `class-feature` (Stufe) | Strukturierte Felder aus Klassenzeilen liegen vor; Fertigkeitswahl (n aus Liste) muss maschinenlesbar werden | M |
| 3 | Spezies mit Größe, Bewegung, Merkmalen, Wahlmerkmale (z.B. Abstammung) | `species` | Wahlmerkmale fehlen als Struktur | M |
| 4 | Hintergrund: Attributsboni (+2/+1 oder +1/+1/+1), Ursprungstalent, Fertigkeiten, Werkzeug, Ausrüstung A/B | `background` | Boni und Ausrüstungsoptionen als Struktur nachziehen | M |
| 5 | Attribute: Standardreihe, Punktekauf, Würfeln (4W6 niedrigsten streichen), manuell | Regeltext | Reine Logik, Validierung serverseitig | M |
| 6 | Abgeleitete Werte live: Modifikatoren, Übungsbonus, Rettungswürfe, Fertigkeiten, passive Wahrnehmung, Initiative, RK, TP, Zauber-SG/Angriffsbonus | Klassen- und Rüstungsdaten | Rechenkern `vtt/rules_content/creator_rules.py` mit Tests | M |
| 7 | Ausrüstung: Startpaket A/B oder Gold, freier Einkauf aus Katalog, Gewicht/Last | `gear`, `armor`, `weapon`, `tool` | Startpakete in Struktur (Items per ID) | M |
| 8 | Zauber: Zaubertricks/vorbereitete Zauber/Zauberbuch, Zauberplätze, Filter nach Klasse/Grad/Schule | `spell` + Klassenlisten, Zauberplatztabellen | Zauberplatz- und Vorbereitungsregeln als Struktur | M |
| 9 | Stufenaufstieg 1-20: Unterklasse (Stufe 3), Attributserhöhung/Talent, Klassenwahlmerkmale, neue Zauber | `class-feature`, `class-option`, `feat`, `subclass` | Fortschrittslogik, Wahlprüfungen | M |
| 10 | Talente mit Voraussetzungen | `feat` | Voraussetzungen maschinenlesbar | S |
| 11 | Mehrklassigkeit (Voraussetzungen, Zauberplätze kombiniert) | Regelwerkstext | Eigene Regel-Implementierung, hohes Risiko | S |
| 12 | Begleiter/Wildgestalt/Vertraute aus Kreaturenwerten | `creature` | Verknüpfung per ID | K |
| 13 | Erscheinungsbild, Persönlichkeit, Gesinnung, Hintergrundgeschichte, Avatar/Token | Charaktermodell (Avatar/Token vorhanden) | Felder in `character_data.srd` | S |
| 14 | Regelverweise überall: Klick auf Merkmal/Zauber/Gegenstand öffnet Compendium-Detailansicht | `entry/<id>` | UI-Komponente, Einbettung als Fenster | M |
| 15 | Bogen: Aktionen, Zauberliste mit Plätzen, Ressourcen (Kurz-/Langrast), Inventar mit Lastgrenze | Compendium + Bogen | Bogen ist aktuell Freitext; erhält regelbasierte Ansicht für SRD-Charaktere | M |
| 16 | Import/Export (Portabel-JSON, PDF-Druckansicht in Roll-Drauf-Lila `#4b235a`) | `dnd5e_portable`, Compendium | Exportschema für SRD-Charaktere | S |
| 17 | Homebrew: eigene Spezies/Gegenstände aus der Creation Engine als Option im Ersteller | Creation Engine, Race-to-Sheet | Auswahl "Eigenbau" in Schritt Herkunft | S |
| 18 | Entwürfe speichern/fortsetzen, Handy-tauglich | Entwurfs-Konzept der Creation Engine | Eigener Entwurfsspeicher im Ersteller | M |
| 19 | Validierungs-/Warnhinweise (ungültige Wahl, fehlende Pflichtwahl) mit Regelverweis | alles | Regelprüfer, gemeinsam für Ersteller und Stufenaufstieg | M |
| 20 | Kampagnenregeln: Inhaltsfreigaben je Kampagne (nur SRD, mit Homebrew) | Kampagnenmodell | Einstellung, später | K |

Bewusst nicht Teil der Parität: nicht-SRD-Klassen/-Unterklassen/-Spezies, Marktplatz,
Mitgliedschaftsmodelle, fremdes Konto-/Inhaltssystem.

## 5. Zielarchitektur (Vorschlag)

1. **Strukturdaten ergänzen (Paket-unabhängig).** Maschinenlesbare Ersteller-Metadaten
   (`creator-rules.json`, abgeleitet aus dem Paket durch `tools/build_regelwerk.py`,
   ohne Paketversion zu ändern): Klassen (Fertigkeitswahl, Übungen, Startausrüstung A/B,
   Zauberfähigkeit, Zauberplätze je Stufe), Spezies-Wahlen, Hintergrund-Boni und
   Ausrüstung. Was sich nicht sicher parsen lässt, wird in einer geprüften,
   handgepflegten Ergänzungstabelle mit Quellverweis auf die Regelstelle geführt und
   per Test gegen den Quelltext abgesichert (wie bei den Zauberlisten).
2. **Rechenkern** `creator_rules.py`: reine Funktionen (kein Flask, keine DB), voll
   getestet; liefert Zustand + Warnungen. Gleicher Kern für Ersteller und Level-up.
3. **Datenmodell.** SRD-Charakter: `character_data.system_id = "srd_5_2_1_de"` und
   Block `character_data.srd` (Auswahlen mit Compendium-IDs, nie Kopien von Regeltext).
   Die bestehenden Spalten (Attribute, TP, RK, Stufe) werden aus dem Kern geschrieben,
   damit Karte, Initiative und andere Verbraucher unverändert funktionieren. Die
   Rollen-Drauf-Light-Charaktere und der Portabel-Import bleiben unberührt.
4. **API.** `POST /api/srd-creator/drafts` (+ `PUT` je Schritt, `POST …/finalize`,
   `POST /characters/<id>/srd-level-up`). Serverseitige Prüfung bei jedem Schritt;
   der Client rechnet nur zur Anzeige. Auth, CSRF und Besitzerprüfung wie bei den
   bestehenden Charakter-Routen.
5. **UI.** Neuer Assistent (eigene Seite, Handy zuerst), Auswahlkarten mit
   Compendium-Detail als Seitenfenster, Live-Zusammenfassung. Einstieg im Dialog
   "Charakter erstellen" als Systemwahl (Roll Drauf Light | SRD 5.2.1).
6. **Creation Engine.** Nur Anbindung über vorhandene Verträge (Homebrew-Spezies per
   Revisions-Referenz als Herkunft), keine Vertragsänderung an 1.1.4/core 1.1.3/A1.
7. **Bogen.** SRD-Charaktere erhalten eine regelbasierte Bogenansicht (berechnete
   Werte, Zauberplätze, Merkmale mit Regelverweis); Freitext-Bogen bleibt für andere
   Systeme.

## 6. Meilensteine (je ein DAD-M-Zyklus, Status-DM nach jedem)

| Zyklus | Inhalt | Abnahme |
|---|---|---|
| P1 | Ersteller-Strukturdaten + Tests (Klassen, Spezies, Hintergründe, Startausrüstung, Zauberplätze); Abweichungen zur Quelle dokumentiert | Tests, Quellabgleich |
| P2 | Rechenkern + Prüfer (Stufe 1), Attribut-Methoden, abgeleitete Werte | Tests, Rechenbeispiele je Klasse |
| P3 | Entwurfs-API + Finalisieren auf Stufe 1, Persistenz in Charakter | API-Tests, Live-Smoketest |
| P4 | Assistent-UI (Klasse, Herkunft, Attribute, Ausrüstung, Zauber, Details, Prüfung) | Handy-Abnahme durch Owner |
| P5 | Regelbasierter Bogen für SRD-Charaktere + Regelverweise | Handy-Abnahme |
| P6 | Stufenaufstieg 2-20 (Unterklasse, Talent/Attribute, Zauber) | Tests je Klasse |
| P7 | Homebrew-Anbindung, Export/Druckansicht, Mehrklassigkeit (Entscheidung nötig) | Abnahme |

Parallel: echter Browser-Test (Playwright oder vergleichbar) einführen, weil bisher nur
jsdom getestet wird; das ist Voraussetzung für die Abnahme von P4.

## 7. Risiken

- **Quellqualität:** Gedruckte Tabellen haben Fehler (Klassen-Zauberlisten). Der
  Ersteller muss weiter abgeleitete Listen verwenden und Abweichungen testen.
- **Parsen von Regeltext:** Fertigkeitswahlen, Startausrüstung A/B und Wahlmerkmale
  sind Prosa. Kontrollierte Ergänzungstabelle mit Quellverweis statt Heuristik.
- **Mehrklassigkeit** und Zauberplatz-Kombination sind fehleranfällig; bewusst spät.
- **Umfang der Handy-Oberfläche:** Der Assistent ist die größte UI-Fläche; wir
  liefern in Schritten, jeder Schritt auf dem Live-VTT abnehmbar.
- **Kopplung:** Bestehende Verbraucher von `Character`-Spalten dürfen nicht brechen;
  deshalb Spalten weiter schreiben, `srd`-Block additiv.

## 8. Offene Entscheidungen (Standardannahme in Klammern)

1. Reihenfolge der Schritte: Klasse zuerst wie im SRD 5.2 (ja).
2. Erlaubte Attribut-Methoden: Standardreihe, Punktekauf, Würfeln, manuell (alle vier,
   Kampagne kann einschränken später).
3. Korrigierte Paketversion 1.0.1 für Zauberlistentabellen (offen seit C2; blockiert
   den Ersteller nicht, da abgeleitete Listen genutzt werden).
4. Startstufe: 1 mit späterem Aufstieg; Direktstart auf höherer Stufe kommt mit P6
   (ja).
5. Mehrklassigkeit in P7 oder später (später).
6. Browser-Test-Werkzeug auf dem Server (Playwright im Container, kein Netz zur
   Laufzeit) (ja).

## 9. Nächster Schritt

Nach Freigabe dieses Discovers: Zyklus P1 (Strukturdaten + Quellabgleich). Bis dahin
keine Code-Änderung am Ersteller; dieses Dokument ist das einzige Ergebnis.
