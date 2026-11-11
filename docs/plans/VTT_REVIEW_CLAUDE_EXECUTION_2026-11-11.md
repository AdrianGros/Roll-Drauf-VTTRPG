# Verbindlicher Ausführungsplan – VTT-Reviews mit Claude Code

Status: **Apply / geplant, Implementierungsagenten noch nicht gestartet**.
Auftrag: neue Protokolle aufnehmen und Claude-Agenten fest für die Umsetzung
verwenden, weil bereits ein Claude-Abo vorhanden ist. Aufbewahrung: dauerhaft.
Grundlage: [Discover/Kategorisierung](../DADM_DISCOVER_VTT_REVIEWS_2026-11-11.md),
[bisheriges Programm](PROTOCOL_FEEDBACK_PROGRAM_2026-11-11.md),
[maschinenlesbare Aufträge](VTT_REVIEW_CLAUDE_EXECUTION_2026-11-11.json).

Dieser Plan ergänzt den bestehenden Gesamtauftrag. Er bezeichnet keine bereits
laufende Hintergrundarbeit und keine neue Live-Lieferung. Das jüngste Anliegen
ist Planung; aus diesem Planungsschritt wird keine Anwendung veröffentlicht.

## Festgelegter Einsatz von Claude

Claude Code `2.1.312` ist vorhanden, mit `claude.ai`/First Party/Pro angemeldet.
Die drei geprüften API-/Auth-Token-Umgebungsvariablen sind nicht gesetzt. Deshalb
wird die vorhandene Abo-Anmeldung als Ausführungsweg festgelegt. Vor jedem Lauf
Auth-Methode erneut prüfen; keine API-, Provider- oder automatische Extra-Usage-
Ausweichlösung. Abo-Limits führen zu einem dokumentierten Checkpoint. Restkontingent
und kontoseitig aktivierte Extra-Usage sind noch zu prüfen; der Loginstatus beweist
weder freies Kontingent noch eine harte Ausgabengrenze.

| Verantwortung | Ausführender | Feste Aufgabe |
| --- | --- | --- |
| UI/Charakter-Implementierung | Claude `vtt-ui-implementer` | C01, C02: bestehende Flächen und ihre erlaubten Bedienwege ändern, passende Tests vorbereiten. |
| Server-/Kampagnen-Implementierung | Claude `vtt-domain-implementer` | C03, C06, C07, C08: genau einen freigegebenen Daten-/Rechtevertrag implementieren. |
| Karten-/Atlas-Implementierung | Claude `vtt-maps-implementer` | C04, C05, C09: vorhandene 2D-Kartenpipeline und später Atlas erweitern. |
| Unabhängige Quellprüfung | Claude `vtt-reviewer` | Exakten Diff gegen Apply und Akzeptanz prüfen, Befunde mit Schwere/Datei nennen; keine Änderungen. |
| Koordination/Integration | Codex | Quellenabgleich, Aufgaben-/Dateieigentum, technische Recherche, Tests ausführen, Rework zuweisen, Commits integrieren. |
| Live-Auslieferung/technische Abnahme | Codex | Push, tatsächliches Image/Compose abgleichen, Sicherung/Migration im genehmigten Umfang, App deployen, Live-UI prüfen und Belege führen. |
| Gemeinsame fachliche Endabnahme | Owner + DM/Player | Ein zusammenhängender Testlauf mit Checkliste; menschlichen Spieltest nicht durch Agentprüfung ersetzen. |

Die vier nativen Definitionen liegen unter `.claude/agents/`; `CLAUDE.md` verweist
auf die bestehenden `AGENTS.md`- und DAD-M-Regeln. Modelle erben die vorhandene
Claude-Sitzung (`model: inherit`); keine ungefragte Modell-/Tarifumstellung.
Implementierer erhalten Read/Grep/Glob/Edit/Write, Reviewer nur Read/Grep/Glob.
Kein Bash-/MCP-/Agent-Werkzeug in diesen Rollen: keine eigene Verschachtelung,
Commit-/Deploymentbefehle oder Kontakte nach außen. Tests und Git übernimmt die
Koordination. Diese Werkzeuggrenze ist keine Behauptung einer Host-Sandbox.

Standard: **ein Claude-Schreiber gleichzeitig**, danach separater Reviewer.
Höchstens zwei unabhängige Implementierungsaufträge gleichzeitig, nur wenn der
Koordinator disjunkte Dateien und ausreichendes Abo-Kontingent belegt. Gemeinsame
Navigation, Katalogbundles, Modell-/Routenregistrierung und Migrationen bleiben
Integrationsdateien; sie werden nicht gleichzeitig von mehreren Agenten geändert.

## Reihenfolge und überprüfbare Pakete

| Auftrag | Inhalt und Scope | Voraussetzung / Gate | Abnahme vor Lieferung |
| --- | --- | --- | --- |
| C00 | Integrationsbasis und Claude-Handoff sichern | Zuerst. Laufendes Image und andere Branches abgleichen; vorhandene P4-Nacharbeit erhalten. | Quellstand, Dirty-Manifest, offene Befunde, Abo-Ausführungsweg, exakter Worker-Basiscommit und erlaubte Dateien festgehalten. |
| C01 | P4 abschließen; Buchrahmen/Navigation und DE/EN/Nachtmodus konsistent | C00; Apply um R07/R08/R11/R14 ergänzen. | Keine alten Bogenflächen beim Laden, keine doppelte zweite Navigation; beide Sprachen/Ansichten und 320/390/1440 px über echte Hauptwege. UI-Wort als Benutzername bleibt unverändert; Kartenmaßstab und getrennte Rollen erhalten. |
| C02 | Avatar-/Token-Upload erreichbar, erlaubte Bearbeitung als Standard, optionaler Schreibschutz, unabhängige Charakterkopie, Creator-Korrekturlinks und Ringer-Prüfung | C01; bestehende Upload-/Kopier-/Regelpfade wiederverwenden. | Echter Upload über Bogen; neuer Charakter mit neuer ID unabhängig änderbar, Original unverändert; keine neue erfundene Slotgrenze. Fehler führt zum richtigen Feld; unzulässige Talentwiederholung wird erklärt. |
| C03 | Anmeldung mit absoluter Sechs-Stunden-Grenze | C00; eigenes Auth-Discover/Apply vor Code. | Login/Refresh/Reload/Discord-Login/Tisch-Reconnect geprüft; Refresh verlängert nicht über absolutes Ende; kein Regelwerk-Logout als unbelegter Fehler „behoben“. Rollen und unabhängige Tabs bleiben korrekt. |
| C04 | 2D-Kartenbedienung und Bibliothek → Spieltisch | C01; vorhandene aktuelle Assets/Projektformate erhalten. | Kartenbutton öffnet normale Fläche; Speichern/Import/Wechsel sichtbar unter Karten; eigene Karte mit Vorschau direkt als Tischseite verwenden. Radierer für Raster/Kacheln/Symbole, bewusster Alle-Ebenen-Modus, ein Undo je Geste; optionales Stempelraster und größere Kachelpinsel funktionieren. |
| C05 | P5-Landmassengenerator in bestehender Pipeline | C04; bounded Apply für Seed/Größe/Laufzeit. | Deterministische Vorschau, Abbrechen ohne Änderung, explizite Übernahme als eine Undo-Aktion; Speichern/Laden/Export/Import erhalten. |
| C06 | Kompakter Kampagnen-Hub, echte Werkzeuge, Kalender/Planung mit Erinnerungsbereich | C00 + C01; Kalender-WIP zuerst inventarisieren. | Gemeinsame Übersicht zeigt nur eigene berechtigte Sessions mit Zeit/Kampagnenfilter; nur berechtigte Leitung plant. Termin/Abstimmung synchron zu Mitgliedern; eigener offener Vote und fehlender DM-Termin sichtbar. Bestehende Prep-Funktionen erreichbar. |
| C07 | Persistente private Gespräche und kompakte Mitgliederaktionen | C02 + C06; eigenes Nachrichten-Discover/Apply. | Charakter/Chat/Entfernen am passenden Mitglied; Dialog nur berechtigte Teilnehmer, keine Lecks durch Suche/IDs/History/Events; Unterhaltung nach Reload vorhanden; Sessionchat bleibt getrennt. |
| C08 | Compendium → Charakter und offene Fortschrittsentscheidungen | C02; bestehende geprüfte Mechaniken nutzen. | Berechtigter Charakter erhält unterstützten Inhalt genau einmal; falscher Charakter/falsche Kampagne abgewiesen. Offene Zauber-/Stufenwahl erscheint, führt durch bestehende Fortschrittsprüfung; keine neuen unfreigegebenen Regeltexte/Bilder. |
| C09 | P6-Atlas mit Welt/Karte/Ort und geschützter Veröffentlichung | C04 + C05; Editor-zu-Tisch-Gate bestanden, eigenes Atlas-Apply. | Owner/Editor/Reader, private Lore und unveränderliche Leserfassung, stabile Ortslinks, Revisions-/Bearbeitungskonflikt, Backup-Rundlauf; Welt auch ohne Karte möglich. Kein 3D-Modus. |
| C10 | P7-Gesamtprüfung und ein gemeinsamer Owner-Test | C01–C09 technisch geliefert; inputabhängige Zusätze separat ausgewiesen. | Ein festgehaltener Source-/Imagezustand, alle normalen Einstiege, vorbereitete eigene Testdaten und erweiterte A01–A12-Checkliste; tatsächliche DM-/Firefox-Player-Spielreise gesondert protokolliert. |

C03 ist fachlich unabhängig von C02; C06 kann nach eigenem Design parallel zu
Kartenarbeit vorbereitet werden. Die Tabelle bleibt die bevorzugte Reihenfolge
für einen Schreiber. Ein Kontingentlimit oder fehlendes Asset stoppt nur den
betroffenen Auftrag; andere Arbeit darf nicht fälschlich als erledigt gelten.

## Fachliche Verträge vor Implementierung

**Darstellung/Charaktere:** Nutzerpräferenz schreibt keine globale Adminpalette.
DE/EN gilt für verfasste UI, nicht für beliebige Benutzer-/Regeltexte. Quelleninventar
muss auch Buch-Builder, dynamische UI-Fragmente und Fehlermeldungen abdecken.
Standard-Bearbeitung öffnet nur serverseitig erlaubte Felder; lokaler Bogen-Lock ist
Bedienkomfort, keine Autorisierung. SRD-Werte, Bonusquellen und Pins bleiben aus
bestehender Mechanik. Der vorhandene Duplizierer ist Ausgangspunkt; keine zweite
Kopierlogik und keine unbenannte Änderung von Slot-/Storage-Quoten.

**Auth:** Sechs Stunden sind die äußere Dauer einer Anmeldung, keine pauschale
Access-JWT-Laufzeit. Das C03-Apply bestimmt Startzeit/Identität der Auth-Kette,
Refresh-Grenze, Rotation, Widerruf, Socketprüfung, verständlichen Wiedereintritt
und den Bestandsvertrag. Keine stillschweigende globale Abmeldung oder Übernahme
nicht abgestimmter Bestandsmigration. Bis dahin kein Auth-Deploy.

**Kampagnen/Kalender:** R2 ersetzt rechts oben den alten Überblickstext durch den
Kalender und präzisiert R1. Bestehende nützliche Session-Vorbereitung wird verlinkt,
nicht pauschal gelöscht. Einheitliche Kalenderdarstellung begründet keine zusätzlichen
Schreibrechte. Zeitzone/Sommerzeit, geplante/abgesagte Termine, eigene Teilnahme und
fehlende Votes gehören ins C06-Apply. Zuerst vorhandenen Kalender-WIP abgleichen;
kein Komplett-Cherry-Pick ohne Prüfung aktueller Rollen- und Produktentscheidungen.

**Nachrichten:** Neue private Daten bekommen vor Code einen Teilnehmer-,
Kampagnenmitgliedschafts-, Verlauf-/Aufbewahrungs- und Widerrufsvertrag. Sichtbare
Memberbuttons sind keine Berechtigungsgrenze. C07-Apply behandelt mindestens
HTTP, Lesen/Suche, direkte IDs, Ereignisse, Mitgliedschaftsverlust und DM/Player-
Trennung. Dateianhänge, externe Mails/Discord-Nachrichten und ein eigener Mailserver
sind nicht aus dem Wunsch nach internem Chat abgeleitet.

**Karten/Atlas:** Pixel, Rasterfelder und physische Maße bleiben getrennt. Bibliothek
→ Tisch verwendet einen bewusst bestimmten Kartenstand/Snapshot und erhält das
bearbeitbare Projekt; fremde Privatassets dürfen nicht über Tisch-/Atlasbilder lecken.
C04-Apply legt Snapshot/Rechte/Credits/Ressourcenbudget fest. Generator arbeitet im
bestehenden Undo-/Rastermodell. Atlas nutzt stabile IDs und veröffentlichte
Leserprojektionen; Reader erhält keine privaten Lore-/Asset- oder Suchdaten.

**Compendium:** Hinzufügen und Fortschritt sind servervalidierte Aktionen mit
konkreter Figur und Quelle; keine ungeprüften Clientboni, keine Umgehung von
Zauberlisten, Stufe, Berechtigung, Nutzungsgrenze oder gepinnten Revisionen.
Der genaue unterstützte Startumfang wird vor C08-Code am aktuellen Katalog geprüft.

Für C03/C06/C07/C09 ist dieses Dokument ein fester Arbeitsauftrag mit Akzeptanz,
kein Ersatz ihres noch ausstehenden konkreten Discover/Apply. DAD-M-Phasen bleiben
explizit; mittel-oder-höhere Befunde vor dem nächsten Übergang bearbeiten.

## Agent-Handoff und Zusammenführung

1. Koordination schließt C00 ab, sichert eigene vorhandene Änderungen und benennt
   den geprüften Basiscommit. Ein Worker startet nicht auf dem uncommitteten P4-Stand.
2. Expliziten Worktree von diesem Commit erstellen, z. B. `git worktree add -b
   claude/vtt-c04 <neuer-pfad> <geprüfter-basiscommit>`. Keine automatische Basis
   von `main` annehmen; Claude-Worktree-Defaults ersetzen keinen Quellabgleich.
3. Handoff benennt Auftrag/Phase, Discover/Apply, Besitzliste, verbotene gemeinsame
   Dateien, Akzeptanz, Daten-/Migrationsgrenze und erwartetes Rückgabeformat.
4. Claude-Code-Implementierer editiert genau diesen Auftrag. Codex führt die
   kleinsten passenden Tests im vorhandenen Test-Image aus. Bei Fehlern erhält
   derselbe Auftrag konkrete Befunde zur Nacharbeit, keine Ausweitung des Scopes.
5. Claude-Reviewer bekommt den exakten Diff plus Vertrag und Testergebnisse.
   Separates read-only Review; keine Behauptung selbst gelaufener Tests.
6. Codex integriert nur eigene geprüfte Slices, aktualisiert Quell-/Live-Abgleich,
   commit/push und liefert im bestehenden Produktions-Compose. Rückweg und neue
   Datenbanksicherung nur entsprechend dem konkreten Paketvertrag.
7. Live: tatsächlicher UI-Einstieg und Rolle, Sourcecommit, Pushstatus, Image-ID,
   gezielte Prüfungen, Bilder/Logs ohne Geheimnisse und Rückweg im Lieferbeleg.
   Danach Monitor; „lokal fertig“ ist keine Lieferung.

Beispiel für einen **zukünftigen** C01-Lauf im explizit vorbereiteten Worker-Worktree:

```bash
env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
  claude --agent vtt-ui-implementer --permission-mode acceptEdits \
  --tools 'Read,Grep,Glob,Edit,Write' --output-format json --print \
  'Bearbeite ausschließlich C01 in Phase Deploy. Lies CLAUDE.md und den zugewiesenen Handoff mit Basiscommit, Apply und Dateibesitz. Gib Teilstatus und Prüflücken ehrlich zurück.'
```

Dies ist ein Startbeispiel, kein bereits ausgeführter Auftrag. `--bare` wird nicht
verwendet, weil dieser Modus die normale OAuth-Anmeldung nicht liest. Keine
`--dangerously-skip-permissions`-Vorgabe. Keine neue Claude-Konfiguration überschreibt
benutzerweite Einstellungen oder andere Worktrees.

## Abnahme und bewusst spätere Themen

Bestehende A01–A12 bleiben bis zur menschlichen Durchführung NOT_RUN. C10 erweitert
die Schritte um: Avatar-/Tokenupload und unabhängige Kopie; Creator-Korrekturlink;
Kalender/ausstehende Abstimmung; private Gesprächsteilnehmer; Radierer/Undo und
Bibliothekskarte direkt zum Tisch; Compendium-/Fortschrittsweg. Die absolute
6-Stunden-Grenze wird mit kontrollierter Zeitprüfung technisch getestet; der Owner
muss dafür keinen sechsstündigen Testtermin aussitzen.

Neue Brushes/Bilder/Regeltexte ohne konkrete Dateien/Quelle bleiben inputabhängig.
Eine neue numerische Charakterslot-Obergrenze, 3D-/Godot-Integration, frei gestaltbarer
Sheet-Designer und öffentliche Streams sind nicht beschlossen. Verify-Ticket-Cleanup
und Rift-Statistik sind separater Bot-Backlog. Kein Versand an Discord aus diesem
Planungsauftrag. Bestehende Live-Features und neue Assetlieferungen schützen.

## Recherche und Grenzen der Verifikation

Lokal: CLI-Version, Authstatus und Umgebungsvariablen-Präsenz ohne Werte geprüft;
keine Zugangsdaten in diesem Dokument. Agentdefinitionen anhand offizieller
[Subagent-Dokumentation](https://code.claude.com/docs/en/sub-agents) und
[CLI-Referenz](https://code.claude.com/docs/en/cli-reference) erstellt.
Abo-Anmeldung und API-Key-Vorrang:
[Anthropic-Hilfe](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-max-or-ultra-plan).
Diese Quellen belegen verfügbare Funktionen, nicht einen bereits erfolgreichen
Implementierungslauf. Noch kein neuer Gesamt-Livezustand, kein ausgeführter Rollback.
