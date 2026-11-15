# VTT-Arbeitsstand zum 15.11.2026

Die Protokolle haben konkrete Lieferungen ausgelöst: Aus den beiden jüngsten
Aufzeichnungen sind **40 eindeutige Feedbackpunkte** entstanden. **35 sind technisch
live geliefert**, **2 durch vorhandenes Verhalten beantwortet**, **2 noch umzusetzen**,
**1 ausdrücklich zurückgestellt**. Das entspricht 87,5 % gelieferter Karten bzw.
92,5 % technisch bearbeiteter/beantworteter Karten. **Menschliche Abnahme ist noch offen.**
Diese Zahlen beschreiben den Stand vor dem zusätzlichen Layer-Slice dieser Sitzung.

## Was die Protokolle leisten

Die Aufzeichnungen vom 11.11. 09:46 (Charakterbau/Karteneditor) und 12.11. 18:03
(Oberfläche/Spieltisch) wurden am 13./14.11. in zwei Inventare mit N01–N20 und
S01–S20 überführt. Jede Karte enthält Quellenbezug/Zeitmarke, beobachtetes Problem,
gewünschten Nutzen und Priorität. Gemeinsam genannte Pinselwünsche sind verknüpft,
keine doppelten Implementierungsaufträge.

Daraus entstanden begrenzte B-Pakete, Apply-Verträge, gezielte Tests, Quellcommits,
Live-Images und Rollenreisen mit Belegen. Der Nutzen ist damit nachprüfbar:
**Aussage → eindeutige Anforderung → bewusste Produktentscheidung → Umsetzung →
Live-Nachweis → menschliche Abnahme.** Lob, bestehende Funktionen, neue Wünsche
und unklare Aussagen werden getrennt; die unklare 0-%-Aussage erzeugt keinen
willkürlichen Reglerumbau. Neuere Entscheidungen überschreiben ältere Annahmen:
Englisch bedeutet inzwischen offizielles eingebettetes PDF statt Neuerfassung.

## Zahlen und Bedeutung von „Approval“

| Messgröße | Stand | Einordnung |
| --- | ---: | --- |
| Jüngste eindeutige Karten | 40 | 20 Charakter/Karteneditor + 20 Oberfläche/Spieltisch |
| Technisch live geliefert | 35 | Owner-Abnahme ausstehend; 87,5 % |
| Bereits vorhanden/beantwortet | 2 | N20 Assetbestand, S19 Landmassen-Layer |
| Noch zu implementieren | 2 | N07 Homebrew-Freigaben, S15 Kampagnenplätze |
| Owner hat zurückgestellt | 1 | N11 unbekannter 0-%-Regler |
| Gelieferte Funktionspakete | B01–B09 | B04 ohne N07; B06 ohne N11 |
| Ursprüngliche menschliche Abnahmereisen | 12 | A01–A12; 0 durchgeführt dokumentiert, 12 offen |
| Dokumentierte Owner-Abnahme der 35 jüngsten Lieferkarten | 0 | 35 als `delivered_for_owner_acceptance`, kein beobachtetes Testergebnis |
| Git-Aktivität 13.–14.11., lokale Kalendertage | 33 Commits | 9 feat, 9 fix, 15 docs; Commitdatum, Branchhistorie bis 4158a0c4b |
| Bereits heute geliefert vor dieser Sitzung | 1 weiterer Funktionscommit | 4158a0c4b Auswahlrahmen und Token-Clipboard |

Ein Implementierungsauftrag, ein technischer Review und eine menschliche Abnahme
sind unterschiedliche Zustimmungen. Die aktuelle Umsetzung ist vom Owner beauftragt.
Explizite neuere Produktentscheidungen sind unter anderem N07 (konkrete veröffentlichte
Homebrew-Optionen je Kampagne), N11 (zurückstellen) und S03 (PDF statt Neuerfassung).
Ein vollständiges zentrales Zählregister aller Gesprächs-Approvals existiert nicht;
deshalb behaupten wir keine künstliche Approval-Gesamtzahl. „0 dokumentierte
Abnahmen“ bedeutet nicht, dass es keine Umsetzungsfreigaben gab.

Vorgängerregister nicht addieren: Die ursprünglichen 40 VTT-Karten und die neun
C01–C09-Lieferpakete bearbeiten weitgehend dieselben Themen in früheren Stufen.
C00 ist Integration, C10 Gesamtprüfung. VTT-/C-/N-/S-Zahlen zusammenzurechnen
würde Änderungen mehrfach zählen. Der neu vorbereitete Wochenkatalog umfasst
20 zusammengefasste Testreisen; auch das sind keine zusätzlichen Features.

## Was geplant war und was daraus geworden ist

| Paket | Karten | Nutzen und heutiger Stand |
| --- | --- | --- |
| B01 | N01, S10 | Ungültige Anrufungswahlen werden abgewiesen; Zurück → Karten funktioniert. Live. |
| B02 | S01/04/09/11/13/14/16 | Zahnrad-Einstellungen, voller Monatskalender, verständlichere Tisch-/Chatnavigation, Dockreiter, Discordbild und passende Leertexte. Live. |
| B03 | N19, S02/17 | Gemeinsame Buchoptik und Nachtmodus mit roten Akzenten; Karteneditor fügt sich ein. Live. |
| B04 | N02–N06 | Ruhigere Klassenauswahl, einzelne Würfelergebnisse, erlaubte Hintergründe, Aufstiegsmerkmale, Zaubersortierung. Live. N07 separat offen. |
| B05 | N12–N17 | Kartenobjekte/Kacheln gemeinsam auswählen und bearbeiten, Kurven, namenlose Symbole, Undo/Redo. Live. |
| B06 | N08–N10/N18, S18 | Pinselspitzen/Bildpinsel, unabhängiger Radierer und verständlicher Entwurfs-/Anmeldestatus; Credits-Kompatibilität repariert. Live. N11 zurückgestellt. |
| B07 | S06–S08 | Licht/Wände, Wiederverbindung und Messformen; PostgreSQL-ID-/Ereignisfehler behoben. Live. |
| B08 | S05/12/20 | Bibliotheksvorschauen, Kartenübernahme im Kampagnenhub und Journal als Assetzugang. Live. |
| B09 | S03 | Offizielles englisches SRD-PDF samt Öffnen/Download/Attribution. Live; Compendium/Creator-Regeltexte bleiben gemäß Entscheidung deutsch. |
| B10 | S15 | Kontingenterweiterung erreichbar machen. Noch nicht implementiert. |
| B11 | alle | Neuer gemeinsamer Abnahmelauf nach B-Lieferungen. Wochenkatalog vorbereitet; vollständiger menschlicher Spieltest offen. |
| 15.11. | zusätzlicher Auftrag | DM-Layer, gruppierte Tokenauswahl, Ein-/Ausblenden; eigener Releasebeleg dieser Sitzung. |

Die ältere C-Runde brachte zusätzlich u. a. getrennte DM-/Player-Kontexte,
persönliche Aktionen/Würfe, Charakterbild-/Bogenkorrekturen, sechs Stunden absolute
Anmeldedauer, Kalender, private Gespräche, Compendium-Übernahme und Atlas-Leserprojektion.
Ihre technische Lieferung ist dokumentiert; echte gemeinsame Spielabnahme bleibt offen.

## Was tatsächlich noch fehlt

| Punkt | Typ | Nächster begrenzter Schritt |
| --- | --- | --- |
| N07 | Umsetzung offen, Produktgrenze geklärt | Kampagnen-Allowlist für veröffentlichte Homebrew-Optionen entwerfen, Berechtigungen testen, liefern. Kein Prerequisite-Bypass. |
| S15/B10 | Umsetzung offen | Bestehenden berechtigten Quota-Erweiterungsweg prüfen und UI-Einstieg festlegen; kein erfundenes/automatisch erhöhtes Limit. |
| N11 | Vom Owner zurückgestellt | Erst ursprünglichen Regler identifizieren. |
| Owner-Abnahme | Testergebnisse fehlen | Wochenkatalog mit DM + Firefox-Spieler durchführen und Ergebnisse je Test erfassen. |
| Separate Donutarian-Testkampagne | Konkrete Quota-Freigabe fehlt | Konto hat laut letztem Beleg 3/3 Plätze; keinen vierten Platz ohne Freigabe anlegen. Synthetische Live-Fixtures benötigen diese nicht. |
| Früherer Maßstab-Browsertest | Bekannte Prüflücke | B09-Beleg meldet einen auch ohne B09 fehlschlagenden Kalibrierungsfall. Im Wochenkatalog erneut bewerten; keine pauschale Grünmeldung. |

## Konsolidierungs- und Liefergrenze

Der ursprüngliche Haupt-Worktree enthält ältere Änderungen. Sie werden nicht
pauschal ausgerollt. Das aktuelle Live-Image ist vom neueren Feedback-Branch;
ein vollständiger Vergleich von 80.855 Laufzeitdateien fand lediglich sechs
explizit behandelte Build-/Altdateiabweichungen. Benötigte Artefakte sind nun
versioniert, obsolete Templatebackups werden aus dem neuen Image entfernt.
Ein eigener sauberer Release-Worktree verhindert die Aufnahme supersedierter
SRD-Neuerfassung, alter Übersetzungsreste oder unbewerteter Sprite-Versuche.

Live bleibt gemäß Owner-Auftrag die schnelle gemeinsame Testumgebung. Die geplante
Dev-Umgebung zum Februarstart wird heute nicht zur Lieferbedingung. Laufzeitcode
muss trotzdem vollständig einem Commit entsprechen. Der neue Release prüft sämtliche
Anwendungsdateien, Requirements und unerwartete zusätzliche Dateien gegen den Commit;
Image-Label allein genügt nicht. Lokale alte Dateien bleiben erhalten, sind aber
kein Beweis, dass eine Änderung fehlt oder erneut veröffentlicht werden soll.

## Belege und nächster Testtermin

- [Kanonisches Umsetzungsregister](plans/FEEDBACK_IMPLEMENTATION_2026-11-13.json)
- [B-Paketplan und einzelne Lieferbelege](plans/FEEDBACK_IMPLEMENTATION_2026-11-13.md)
- [Verbindliche verbleibende Produktentscheidungen](decisions/FEEDBACK_REMAINING_SCOPE_2026-11-13.md)
- [C-Programm](plans/VTT_REVIEW_CLAUDE_EXECUTION_2026-11-11.json)
- [Ursprüngliche A01–A12-Abnahme](acceptance/PROTOCOL_FEEDBACK_LIVE_RUN_2026-11-12.md)
- [Wochenkatalog 16.–22.11.](acceptance/TEST_CATALOG_2026-11-16.md)
- [Aktuelle Discover-/Quellinventur](DADM_DISCOVER_CONSOLIDATION_LAYERS_2026-11-15.md)
- [Layer-Vertrag und Releasegrenze](DADM_APPLY_CONSOLIDATION_LAYERS_2026-11-15.md)

Stand eingefroren auf Basis 4158a0c4b; die Lieferung dieser Sitzung wird separat
in `docs/proofs/consolidation-layers-2026-11-15/delivery.json` und Deploy/Monitor dokumentiert.
