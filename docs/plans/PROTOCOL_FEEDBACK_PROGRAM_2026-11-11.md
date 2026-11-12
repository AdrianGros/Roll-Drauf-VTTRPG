# Ausführungsplan: Protokollfeedback bis zur gemeinsamen Live-Abnahme

Status: **Umsetzung läuft; P1–P3 technisch live geprüft, P4–P6 in Arbeit**.
Phase: Apply auf Programmebene, Profil `standard`. Aufbewahrung: dauerhaft.
Auftrag: nächste Punkte ordnen, technische Arbeit autonom erledigen, anschließend
ein zusammenhängender Owner-Test auf `https://vtt.roll-drauf.de`.

Grundlage: [Discover](../DADM_DISCOVER_PROTOCOL_FEEDBACK_PROGRAM_2026-11-11.md),
[40-Punkte-Spezifikation](../PROTOCOL_FEEDBACK_SPECIFICATIONS_2026-11-10.md),
[bestehende Lieferung](../DADM_MONITOR_PROTOCOL_FEEDBACK_2026-11-10.md).
Die [Ausführungsdatei](PROTOCOL_FEEDBACK_EXECUTION_2026-11-11.json) hält
Abhängigkeiten, Kartenstatus und offene Eingaben fest; sie ist kein Hintergrundjob.
Der [gemeinsame Testlauf](../acceptance/PROTOCOL_FEEDBACK_LIVE_RUN_2026-11-11.md)
ist vorbereitet, aber noch nicht gelaufen.

## Ziel, Umfang und Reihenfolge

Am Ende steht ein über die normale Navigation erreichbarer Spielablauf:
Charakter erstellen und Regelherkunft verstehen → eigenen Charakter am Tisch
spielen → persönliche Aktionen zuverlässig ausführen → Karte bearbeiten und
eine veröffentlichte Welt erkunden. Darstellung, Sprache und Entfernungen sind
konsistent. Der Owner muss keine Zwischenpakete einzeln abnehmen.

| Reihenfolge | Paket / Ergebnis | Voraussetzung | Wichtigste Abnahme |
| --- | --- | --- | --- |
| P0 | Lieferbasis und offene Angaben sichern | Bestehende Live-Lieferung | Laufende Quelle/Image, Compose, Datenumfang, Rollback und Unterschiede dokumentiert. |
| P1 | Vollständige Player-/DM-Tischkontexte | P0 | Getrennte Oberflächen und serverseitige Daten-/Aktionsgrenzen; Owner als Player bleibt Player. |
| P2 | Persönliche Charakter-Hotbar und zuverlässige Würfelreise | P1 | Gespeicherte Belegung, erlaubte Aktionen, Firefox-Sende-/Empfangstest mit Reconnect. |
| P3 | Homebrew-Hintergründe/Merkmale und nachvollziehbare Boni | P2 | Eagle → geprüfte Veröffentlichung → Creator → Bogen → erlaubte Tischaktion. |
| P4 | Durchgängige Darstellung, UI-Sprache und Distanzanzeige | P0 | Pergament/Nacht, lesbare Zustände, DE/EN, kalibrierte Rasterdistanzen ohne Änderung gespeicherter Spielwerte. |
| P5 | Landmassengenerator im vorhandenen Karteneditor | P0 | Seed-Vorschau, bewusstes Übernehmen, eine rückgängig machbare Änderung; Bibliothek/Export erhalten. |
| P6 | Nutzbarer Atlas mit Karten, Orten und geschützter Lore | P1 | Welt/Region/Ort verknüpfen, Entwurf von Veröffentlichung trennen, Leser sehen nur Freigegebenes. |
| P7 | Gemeinsame Regression, Live-Bereitschaft und ein Owner-Test | P1–P6 | Ein festgehaltener Releasezustand, vorbereitete Testdaten, alle Wege erreichbar, Ergebnisprotokoll. |

Die Tabelle ist die Arbeitsreihenfolge für einen Agenten. P4/P5 sind fachlich
nicht von P3 abhängig; bei einem inhaltlichen Blocker kann dort weitergearbeitet
werden. Es sind keine parallelen Agenten vorgesehen. Ein blockiertes Zusatzthema
stoppt nicht automatisch das gesamte Programm.

## Technische Verträge und Paketgrenzen

### P0 – Ausgangslage und Wiederaufnahme

Vor jeder Umsetzung die tatsächliche Live-Version und vorhandene neuere Arbeit
abgleichen. Der am 11.11. festgestellte Stand ist Image
`protocol-feedback-20261110-32cc5bfee`, Quellcommit `32cc5bfee…`,
Dokumentationscommit `f942c74eb…`. Die bestehende gemeinsame Oberfläche ist kein
Beweis bereits erfüllter Rollentrennung. Gelieferte Creator-/Bogen-/Kartenfunktionen
und aktuellere Tisch-/Beyond20-/Buchfunktionen bleiben geschützt.

Pro Paket Discover → Apply → Deploy → Monitor dokumentieren. Vor Deploy müssen
mittlere oder höhere technische Befunde im Paket geklärt sein; der Programmplan
ist keine pauschale Freigabe ungeklärter Migrationen oder Autorisierungsdesigns.
Zuerst wird die P1-Discover-Inventur aller relevanten Pfade vervollständigt.
Darauf entsteht `DADM_APPLY_PLAYTABLE_CONTEXTS_2026-11-11.md` mit dem konkreten
Kontextvertrag und verbindlichen Positiv-/Negativfällen. Der Dateiname bezeichnet
das geplante Ergebnis, keine bereits vorhandene Spezifikation.

### P1 – Tischkontexte als Grundlage

Verbindlich ist die [Owner-Entscheidung vom 01.11.](../decisions/PLAYTABLE_ROLE_SEPARATION_2026-11-01.md).
Zielvertrag: servererteilter, widerrufbarer Kontext mit Nutzer, Kampagne, Session,
effektivem Modus, Gültigkeit und verbindlicher Tab-/Verbindungszuordnung. Der
Client darf den Modus wünschen; ausschließlich der Server vergibt Befugnisse.
Konkrete Speicherung, Token-/CSRF-Vertrag, Ablauf und Transportbindung werden im
Paket-Apply entschieden und geprüft, bevor Implementierung beginnt.

- Zwei getrennte Präsentations-/Kompositionsschichten; Player initialisiert
  keine DM-Werkzeuge oder DM-Handler. Gemeinsame geprüfte Domänenlogik bleibt möglich.
- HTTP, Socket-Join und jedes relevante Ereignis, Bootstrap, Resync, Bogenaktionen,
  Beyond20-/Legacy-Einstiege müssen unabhängig ihren Kontext und Ressourcen prüfen.
- Kein Owner-/DM-Fallback bei fehlendem, falschem oder abgelaufenem Kontext.
  Expliziter erneuter DM-Eintritt bleibt möglich. Andere autorisierte Tabs bleiben
  unabhängig; ein Nutzerraum darf keine DM-Geheimnisse in seinen Player-Tab liefern.
- Abstieg und Widerruf entfernen alte Empfangsräume, veraltete Befugnisse und
  bereits lokal gehaltene DM-Daten. Reload, Reconnect, kopierter Tab und parallele
  DM-/Player-Tabs sind eigene Negativfälle.
- Vorhandene `TableSeat`-Semantik ausdrücklich migrieren/ablösen, ohne bestehende
  Clients still privilegiert weiterlaufen zu lassen. Ungültige Altverbindung führt
  zum sicheren Wiedereintritt über die UI, nicht zum Eigentümer-Fallback.

**Gate:** Alle relevanten Pfade inventarisiert, keine ungeprüfte Nebenroute,
beide Oberflächen live erreichbar, Rollen-/Ressourcen-/Tab-/Widerrufsmatrix grün.
Keine getrennte Teilfreigabe einer nur kosmetisch getrennten Player-Oberfläche.

### P2 – Persönliche Aktionen und Würfelergebnisse

Eine gespeicherte Belegung gehört zu Nutzer und berechtigtem Charakter. Sie
referenziert deklarativ Katalogaktion, Slot und Version; weder Skripttext noch
vom Client berechnete Boni sind Autorität. Ziel: bis zu zehn belegbare Plätze,
leere Plätze nur im Bearbeitungsmodus, Belegen/Entfernen/Umordnen per Schaltfläche
und Tastatur; Drag-and-drop als ergänzende Bedienung. Vorhandene Zielauswahl,
Escape-Abbruch und Schutz vor Shortcuts beim Tippen bleiben erhalten.

Fertigkeiten, Rettungswürfe, Waffen und Zauber verwenden die vorhandenen
serverseitigen Ausführungs-/Würfelpfade. Nicht unterstützte Ressourcenmechanik
wird klar benannt; keine scheinbar vollständige Zauber-/Effekt-Engine erfinden.
Vor jeder Ausführung Kontext, Charakter-/Tokenrechte, Ziel und Ressourcen prüfen.
Veraltete Katalogreferenzen werden erklärt, statt still eine andere Aktion auszulösen.

Für wiederholbare Ausführungsanfragen wird ein begrenzter, serverseitiger
Dedup-Vertrag mit Request-ID, Akteur und Kontext festgelegt. Ereignisse besitzen
stabile IDs; Clients deduplizieren und gleichen nach Reconnect mit autoritativem
Zustand ab. Kein pauschales „exactly once“ für den Transport versprechen.
Retention, verpasste Würfelhistorie und sichtbare Wiederaufnahme werden im Apply
präzisiert. Ein Reconnect darf weder neue Würfe erfinden noch fremde Sessiondaten liefern.

**Gate:** Firefox↔Firefox und Chromium↔Firefox, Absender/Empfänger, absichtlicher
Reconnect, wiederholte Anfrage, fremde Session und fremder Token geprüft.
Persistente Belegung funktioniert nach Reload und verändert keinen anderen Charakter.

### P3 – Regelherkunft und Homebrew im aktuellen Arbeitsplatz

Zuerst vorhandene lizenzierte Kataloge gegen auswählbare IDs/Regelversionen prüfen.
Fehler in nachweislich vorhandenen Daten beheben; die unbenannten fehlenden
Talente/Unterklassen nicht mit geratenen oder fremden Regeltexten auffüllen.

Hintergrund und Merkmal erhalten typisierte, versionierte Entwürfe und eine
Prüf-/Veröffentlichungskette im **bestehenden Eagle-Arbeitsplatz**. Veröffentlichung
enthält stabile ID, Revision, Quelle, Scope, Voraussetzungen und unterstützte
mechanische Grants. Freitext wird nicht zu ausführbarer Mechanik interpretiert.
Unbekannte Effekte blockieren spielbare Veröffentlichung mit verständlicher Diagnose.
Charaktere pinnen Inhaltsrevisionen; neue Entwürfe ändern fertige Charaktere nicht.
Persönliche/kampagnengebundene Sichtbarkeit bleibt servergeprüft.

Für berechnete Werte liefert dieselbe Berechnung eine Erklärung aus Basis,
benannten Beiträgen mit Quellen-ID/Revision, Stapelregel und Gesamtwert.
Anzeige und Würfelpfad dürfen nicht getrennt dieselben Boni noch einmal addieren.
Mindestens RK, Initiative, Bewegung, Fertigkeiten/Rettungswürfe und Angriffsboni
werden anhand repräsentativer Figuren abgeglichen; weitere berechnete Bonusfelder
kommen in dasselbe Inventar, nicht in eine unbelegte Vollständigkeitsbehauptung.

VTT-34 wird zunächst als verständlicher visueller Homebrew-Arbeitsplatz mit
Vorschau vorhandener Daten bearbeitet. Ein frei programmierbarer Sheet-Designer
oder ein neues Sheetformat bleibt eine gesonderte Produktentscheidung.

**Gate:** Ein eigenes Hintergrund-/Merkmalsbeispiel ist über UI prüfbar, korrekt
im Creator/Bogen verwendbar und liefert erklärbare Werte; ungültige, fremde und
veraltete Referenzen sind abgedeckt. Migration und Datenrückweg vorher dokumentiert.

### P4 – Darstellung, Sprache und Einheiten

Globale Admin-Palette bleibt globale Admin-Palette; Nutzer wählen eine davon
abgeleitete Pergament-/Nachtansicht. Vorhandene Bogenpräferenzen werden übernommen.
Normale Texte erreichen 4,5:1, Zustände sind zusätzlich über Rand/Form/Attribute
erkennbar. Sichere Farbkombinationen sind der erste konfigurierbare Umfang;
ein unbegrenzter CSS-/Theme-Editor ist nicht Teil dieser Lieferung.

UI-Sprache: stabile Schlüssel, DE als Fallback, EN als zweiter vollständiger
UI-Katalog für die betroffenen Hauptwege einschließlich neuer Pakete. Persistenz
und sichere Darstellung von Platzhaltern gehören zum Vertrag. Eigennamen und
Regelquellen werden nicht automatisch übersetzt. FR/ES und vollständige
Regelwerkübersetzungen bleiben getrennt ausgewiesen.

Einheiten sind Anzeigepräferenzen. Bestehende kanonische Meterwerte bleiben
unverändert; D&D-Anzeige nutzt 1 ft = 0,3 m. Für Tischkarten braucht es eine
explizite physische Größe pro Rasterfeld, getrennt von Pixeln pro Feld. Ohne
Kalibrierung werden Rasterfelder/Pixel ehrlich benannt. Keine erfundene Entfernung
für alte Karten. Atlas-Karten erhalten bei Bedarf eine eigene Maßstabskalibrierung.

Optionales Sticky-Porträt ist abschaltbar, bei wenig Platz aus und berücksichtigt
Reduced Motion; es darf keine Kernbedienung verdecken. VTT-38 ist ein Komfortziel,
kein Grund, die technische Kernlieferung zurückzuhalten.

**Gate:** Repräsentative Hauptwege in DE/EN und beiden Ansichten; 320/390/1440 px,
Tastatur, lange Texte und Reload; Einheitentausch ändert keine gespeicherten Werte.

### P5 – Reproduzierbare Landmasse

Vorhandenes Dokument-/Raster-/Undo-Modell erweitern. Parameter: Seed,
Landanteil/Formvariante und begrenzte Auflösung. Seed plus Parameter plus
Generatorversion ergeben dieselbe Maske. Vorschau verändert das Projekt nicht;
Abbrechen erhält es vollständig. Übernehmen erzeugt eine zusammenhängende
Undo-Operation auf einer ausdrücklich ausgewählten/neuen Rasterebene.

Startumfang: Insel und größere zusammenhängende Landmasse mit einstellbarem
Küstenverlauf; keine vollständige Klima-, Fluss- oder Siedlungssimulation.
Maximalgröße, Abbruchmöglichkeit und Laufzeitbudget auf repräsentativer Hardware
in Apply messen und begründen; keine willkürliche 200-%-Grenze einbauen.
Ohne benötigte neue Bibliothek im vorhandenen Canvas-/Dokumentmodell bleiben.

**Gate:** Determinismus, Vorschau/Abbruch, Undo/Redo, bestehende Ebenen und eigene
Karten erhalten; Speichern/Laden und Export/Import ohne stille Formatverluste.

### P6 – Atlas als erster vollständiger Nutzungspfad

Ein Autor erstellt eine Welt mit Welt-/Regional-/Ortskarte, verknüpft Orte und
publiziert eine ausgewählte Leserfassung. Stabile Orts-IDs sind unabhängig von
grafischen Markierungen. Primäre Hierarchie ist zyklenfrei; zusätzliche Links
sind möglich. Kartenkoordinaten gelten je Karte; Detailkarte ist zunächst ein
bewusster Link, kein automatisch deckungsgleicher Ausschnitt.

Rollen: Owner/Editor/Reader pro Welt, ausdrücklich unabhängig von globalem DM-Status.
Bestehende Authoring-Scopes werden nicht versehentlich zu geografischen Welten
umgedeutet. Private Lore und Entwürfe bleiben getrennt von einer versionierten
Leserprojektion; Berechtigung gilt auch für Suche, Vorschau, Assets und Ereignisse.
Einladungen berechtigen konkrete Personen, keine öffentliche Freigabe per Standard.

Aktuelle Kartenbibliothek und Assets weiterverwenden. Änderungen behalten
Revisionsprüfung; paralleles Bearbeiten derselben Rasterkarte benötigt einen
klaren Bearbeitungs-/Konfliktvertrag. V1 sieht einen aktiven Editor je Rasterkarte
vor, kein zusätzliches Echtzeit-Mal-/CRDT-System. Export/Import muss Atlas-IDs,
Verknüpfungen und referenzierte Karten/Assets sichern, nicht nur ein PNG liefern.

Ein UI-Einstieg „Atlas“ und Welt→Karte→Ort→Detailkarte sind Zielnavigation,
heute noch nicht vorhanden. Die genaue Einbindung und Rechte-/Migrationsverträge
werden vor Code im Paket-Apply festgehalten. Bestehenden Renderer bevorzugen;
Leaflet oder andere neue Abhängigkeiten nur nach begründetem Vergleich und
innerhalb der Repo-Governance, nicht automatisch aus dem alten Entwurf übernehmen.

**Gate:** Zwei Autoren, ein Leser, drei verknüpfte Karten; keine privaten Inhalte
beim Leser; veraltete Revision überschreibt nichts; Wiederladen/Backup-Rundlauf
und vollständig über die Hauptnavigation erreichbare Veröffentlichung geprüft.

## Recherchegrundlage für die Paketverträge

- [Flask-SocketIO: Implementation Notes](https://flask-socketio.readthedocs.io/en/latest/implementation_notes.html):
  Socket-Handler verwenden den Verbindungskontext; HTTP-`before_request` schützt
  sie nicht automatisch. Autorisierung und Widerruf daher explizit je Ereignispfad.
- [OWASP: Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  standardmäßig verweigern und Berechtigung bei jeder Anfrage/Ressource prüfen.
- [MDN: sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage):
  tabbezogener Speicher kann vom Opener kopiert werden. Er allein beweist weder
  eine eindeutige neue Tabidentität noch eine serverseitige Befugnis.
- [Socket.IO: Delivery guarantees](https://socket.io/docs/v4/delivery-guarantees/):
  Standardzustellung ist höchstens einmal; Wiederaufnahme und persistente
  Ereignis-IDs sind Anwendungsaufgaben. Dies ist eine Transportgrenze, kein Nachweis
  bereits vorhandener Python-Stack-Funktionen; diese separat am installierten
  [python-socketio](https://python-socketio.readthedocs.io/en/stable/server.html) prüfen.
- [RFC 9110: If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match):
  bedingte Änderungen verhindern verlorene Updates. Bestehende revisionbasierte
  Kartenverträge und ihre Fehlercodes erhalten; nicht pauschal alle APIs umstellen.

## Autonomer Ablauf und Grenzen

Der bisherige Auftrag autorisiert die technische Umsetzung und Live-Lieferung.
Nach diesem Planungsdurchgang kann die Arbeit paketweise ohne erneute Routine-
Freigaben fortgesetzt werden: recherchieren, entwerfen, bekannte Fehler lösen,
gezielt testen, committen, pushen, ausliefern und technisch live prüfen.
Dieser Plan behauptet keinen bereits laufenden Hintergrundprozess.

Nur beim betroffenen Paket anhalten, wenn notwendige Produkt-/Quellenangaben
fehlen oder ein tatsächlicher Governance-Entscheidungsfall eintritt: kritischer
Befund, hoher Sicherheits-/Datenschutzbefund, ungelöster strategischer Konflikt,
unautorisierte Abhängigkeit/Scopeänderung oder ausgeschöpfte Rework-Grenze.
Die [Repo-Governance](../../dadm/framework/runtime/cards/governance-min.md) verlangt
hier eine menschliche Entscheidung. Routineimplementierung ist kein solcher Fall.
Technische Befunde mittlerer Schwere zuerst nacharbeiten, nicht verdeckt übergehen.

| Eingabe | Betroffene Karten | Währenddessen autonom möglich |
| --- | --- | --- |
| I01: Konkreter fehlender Inhalt mit ID/Quelle/Regelversion | VTT-03 | Vorhandene lizenzierte Kataloge und Auswahlfehler prüfen. Unbenannte Ergänzungen offen lassen. |
| I02: Benanntes 200-%-Steuerelement und Reproduktion | VTT-37 | Übrige Kartenarbeit; keine willkürliche Begrenzung. |
| I03: Zusätzliche Assetdateien und konkrete Rechte/Attribution | VTT-35 | Bestehenden Katalog und Credits regressionsprüfen. |
| I04: Ausgangsregelwerk, Rechte und Zielsprachumfang | VTT-40 | UI-DE/EN; keine automatische Veröffentlichung kompletter Regelübersetzungen. |
| I05: Öffentliche Partner-/Streamingfreigabe und Umfang | VTT-36 | Private technische Live-Abnahme. Kein Kontaktversand oder öffentlicher Stream ohne konkreten Auftrag. |

FR/ES, frei gestaltbarer Sheet-Designer und umfassendere Weltsimulation bleiben
ausdrücklich nachgelagerter Umfang. Wenn diese gewünscht sind, werden sie vor
Erweiterung als eigene Pakete eingeplant. Ihre Ursprungskarten werden dadurch
nicht fälschlich als vollständig erledigt markiert.

## Risiken und Annahmen für die Ausführung

| Schwere | Risiko / Annahme | Behandlung vor betroffenem Deploy |
| --- | --- | --- |
| Mittel | Kontextlebenszyklus und alle Nebenpfade sind noch nicht detailliert entworfen. | P1-Apply muss R01 schließen; kein Implementierungsstart allein auf Basis dieser Roadmap. |
| Mittel | Hotbar-Ausführung und Reconnect brauchen einen gemeinsamen Ereignis-/Dedup-Vertrag. | P2-Apply und Mehrclient-Negativtests; Transportgarantie nicht voraussetzen. |
| Mittel | Homebrew/Atlas können Schema- und Datenänderungen benötigen. | Paketbezogene Migration, Backup und tatsächlich kompatiblen Rückweg festlegen. |
| Mittel | Unbekannte Inhalts-/Rechteangaben verhindern einzelne vollständige Kartenabschlüsse. | I01–I05 bleiben offen; betroffene Zusätze nicht in die Bereitmeldung als geliefert aufnehmen. |
| Mittel | Atlas-Veröffentlichung kann über Suche/Assets mehr verraten als die sichtbare Karte. | Leserprojektion und negative Datenabnahme im P6-Apply festlegen. |
| Niedrig | Die menschliche Schlussabnahme benötigt eine zweite Person und Firefox. | Testdaten und Ablauf vorbereiten; VTT-31 erst nach tatsächlicher Runde schließen. |

Das sind Programmrisiken und noch zu schließende Entwurfsaufgaben, keine bereits
behobenen Befunde. Programmplanung darf abgeschlossen sein; das jeweilige Paket
darf seine Apply-/Deploy-Grenze erst nach passender Risikobearbeitung passieren.

## P7 – Release, Beweise und gemeinsame Owner-Abnahme

Jedes Funktionspaket wird nach fokussierten Tests committed, nach Möglichkeit
gepusht, über die tatsächlich laufende Compose-Konfiguration veröffentlicht und
mit angemeldeten Rollen technisch live geprüft. Kein Staging-Zwang. Pro Paket:
UI-Weg, Rollen, Kriterien, Sourcecommit, Image-ID, Checks, Live-Beleg und Rückweg
festhalten. Ein fehlgeschlagener Push ist separat von Deploymentstatus auszuweisen.

Neue DB-Daten benötigen vor Deploy überprüfte Migration, Backup und dokumentierte
Rückwärtskompatibilität. Den bisherigen Image-Rollback nicht blind für künftige
Schemaänderungen verwenden. App-only-Restart ist der Standard; andere Dienste
oder Daten werden nicht nebenbei neu aufgebaut. Eigene synthetische Testdaten
verwenden und rückstandsfrei entfernen. Owner-Abnahmefiguren dagegen nur mit
klarer Kennzeichnung gezielt bis zur Abnahme behalten.

Vor Einladung zur Abnahme alle Pakete zusammen erneut prüfen und genau **einen**
Releasezustand für den Lauf festhalten. Neue spätere Codeänderungen verlangen
eine aktualisierte betroffene Prüfung, keine pauschale Wiederholung ohne Anlass.
Die bisher gelieferten Funktionen bleiben im selben Lauf enthalten.

Die finale Bereitmeldung nennt Link, normalen UI-Einstieg, Rollen, vorbereitete
Testdaten und noch offene Inputkarten. Sie darf „technischer Umfang testbereit“
heißen, solange Zusatzinhalte offen sind; „alle 40 erledigt“ erst nach tatsächlicher
Klärung jeder Karte und der menschlichen Spielsitzung. Technische Readiness ist
keine vorweggenommene Owner-Abnahme.

## Prüfbarkeit und Deploy-Handoff

Geplant sind `A01`–`A12` im gemeinsamen Testskript und eine vollständige
VTT-01–VTT-40-Zuordnung in der Ausführungsdatei. Der Planungsabschluss prüft
Kartenvollständigkeit, Abhängigkeiten, Kriterienverweise und ehrliche Statuswerte.
Es sind keine neuen Anwendungstests für diese Dokumentationsänderung nötig.

**Nächste autonome Arbeit:** P0 aktuell abgleichen, P1-Discover mit vollständigem
Autorisierungs-/Ereignispfadregister abschließen, danach P1-Paket-Apply mit konkretem
Kontextlebenszyklus. Erst nach Auflösung seiner mittleren Risiken wechselt P1 zu Deploy.
Der nächste Fachschritt ist damit konkret; diese Dokumente allein deployen keine Funktion.

## Owner-Steuerung nach den Reviews vom 11.11.

Die neuen Reviews sind in [Discover/Kategorisierung](../DADM_DISCOVER_VTT_REVIEWS_2026-11-11.md)
erfasst. Die Implementierung ist nun ausdrücklich mit **Claude-Code-Agenten über
das vorhandene Abo** eingeplant; Codex koordiniert, führt Tests aus, integriert
und liefert live. Verbindliche Aufträge und neue Reihenfolge stehen im
[Claude-Ausführungsplan](VTT_REVIEW_CLAUDE_EXECUTION_2026-11-11.md).

P1–P3 bleiben technisch geliefert. C01-Darstellung/Sprachen einschließlich der
PlayChrome-Kontrastnacharbeit und C03-Loginfrist sind live geprüft. C02-Bogen und
C04-Kartenfunktionen sind in Quelle8848c621c live; zwei mittlere Live-Befunde
(Firefox-Bildaktualisierung und mobiler Import-/Export-Kopf) verhindern deren Abschluss.
C06-Kalender ist separat als teilweise implementierter Branch gesichert,76pass4fail,
noch nicht integriert oder live. Claude-Abo-Kontingent ist erneut ausgeschöpft,
Reset12.11.19:10Europe/Berlin, kein automatischer API-/Zusatznutzungsfallback.
Der verbindliche Fortsetzungsstand steht im
[Handoff](../DADM_DEPLOY_CLAUDE_HANDOFF_2026-11-12.md). Das Gesamtpaket ist nicht testbereit.
Kartenbedienung und Bibliothek→Tisch kommen vor Generator und Atlas; P6 hängt
nun ausdrücklich auch von P5 ab. Kalender, private Gespräche und Compendium-Wege
sind als eigene neue Pakete mit vorgeschaltetem Discover/Apply sichtbar. Keine
stille Mitlieferung, keine 3D-Erweiterung und keine bloße Wiederaufnahme überholten G1.
