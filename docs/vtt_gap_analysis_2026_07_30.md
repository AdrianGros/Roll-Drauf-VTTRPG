# Roll-Drauf VTT — Gap-Analyse für einen funktionsfähigen Testbuild

**Erstellt:** 2026-07-30
**Umfang:** `/home/admin/projects/roll-drauf-vtt` aktive Codebasis (Workspace-HEAD `3e7dbe6`, working tree mit
17 uncommitteten Dateiänderungen), das laufende Docker-Deployment, das Dokumentations-Korpus (`docs/` +
`dadm/`, präzise gezählt statt geschätzt — siehe Teil I), ein vollständiger Pytest-Lauf sowie ein von Grund
auf neu durchgeführter, praktischer End-to-End-HTTP-Test einer isolierten Instanz, der gezielt die seit der
letzten Edition neu hinzugekommenen Scene-Stack/Page-Manager-Endpunkte durchspielt.
**Fassung:** Dritte Edition. Vorgänger: `RollDrauf_VTT_Gap_Analysis_2026-07-28.pdf` (Markdown-Quelle nicht
mehr vorhanden, daher als `vtt_gap_analysis_OLD.txt` aus dem PDF rekonstruiert und als Vorlage für
Struktur/Tiefe dieses Dokuments verwendet) sowie ein am 2026-07-30 begonnener, durch ein Sitzungslimit
abgebrochener Zwischenstand (`docs/vtt_gap_analysis_2026_07_30.md`, 115 Zeilen). Dessen fünf Befunde sind hier
verifiziert und eingearbeitet, nicht neu erhoben: fehlende Drop-Migration → Teil VI/P1 und Teil V.2; sauberer
Schnitt der Altsystem-Entfernung → Teil III.2; latentes S3-Risiko → Teil II.5; unversionierte
`.env`-Backup-Datei → Teil V.5; keine TODO/FIXME-Marker im Diff → Teil II.5. Ebenso eingearbeitet: die "18/18
grün"-Zahl für die diff-spezifischen Tests und der 411/414-Wert für die Gesamtsuite, beide für diese Edition
unabhängig neu ausgeführt statt übernommen (Teil II.2).
**Ziel:** unverändert gegenüber der Erstausgabe — alles identifizieren, was zwischen dem aktuellen Stand und
einem wirklich vertrauenswürdigen "funktionsfähigen Testbuild" steht.
**Methode:** direktes Lesen des Codes (inklusive der Dateien, die der aktuelle uncommittete Diff berührt), ein
vollständiger Pytest-Lauf gegen den aktuellen Working Tree, eine erneute Bestandsaufnahme des
Dokumentations-Korpus, und ein echter End-to-End-HTTP-Test gegen eine isolierte Instanz (eigene SQLite-Datei,
eigener Port, nicht die Produktions-Container) inklusive eines vollständigen Prozess-Neustarts, diesmal
gezielt über die neuen, im Diff hinzugekommenen Scene-Stack-Layer-Endpunkte statt der alten
M42-Direktaktivierung.
**Zielgruppe:** unverändert — wer auch immer den VTT-Strang als Nächstes verantwortet.

---

## Inhalt

Zusammenfassung (Executive Summary)

Teil I — Dokumentationsstand: hat sich seit 2026-07-28 etwas geändert?
I.1 Die Ein-Satz-Version (re-verifiziert) · I.2 Vier überlappende Meilenstein-Nummerierungsschemata · I.3 Die
3,5-monatige Dokumentationslücke · I.4 Das jüngste reale Feature hat gar keine DAD-M-Papierspur · I.5
Widersprüche, die aufzulösen sind (acht Punkte, einzeln re-verifiziert) · I.6 Präzise Korpusgröße · I.7 Was
das für diese Edition bedeutet

Teil II — Zustand von Codebasis und Testsuite
II.1 Baut der aktuelle Tree überhaupt? · II.2 Vollständiger Testsuite-Lauf: 411/3 · II.3 Größte Dateien · II.4
Kapazitätsbezogener Rundgang durch jeden Funktionsbereich · II.5 Requirements, S3-Risiko und TODO-Marker

Teil III — Der uncommittete M5/M7-Refactor: was er ändert, und eine bisher nicht dokumentierte Lücke
III.1 Zusammenfassung des Diffs · III.1a Die neue Business-Logik im Detail · III.2 Sauberer Schnitt —
bestätigt · III.3 Neuer Befund: zwei unabhängige, nicht synchronisierte "aktive Karte"-Mechanismen

Teil IV — Praktische Funktionsverifikation (hands-on, End-to-End, mit Prozess-Neustart)
IV.1 Methode · IV.2 Was Schritt für Schritt getestet wurde · IV.3 Ergebnis · IV.4 Was das beweist — und was
nicht · IV.5 Gezielte Reproduktion des Teil-III.3-Befunds

Teil V — Infrastruktur- und Deployment-Realität
V.1 Was heute tatsächlich läuft · V.2 Der Zugriffskontroll-Fix ist seit 48 Stunden ungedeployt · V.3 Keine
echte Staging-Umgebung · V.4 Zwei mysteriöse leere Verzeichnisse und der tote nginx-Service · V.5
Unversionierte Backup-Datei

Teil VI — Priorisierter Weg zu einem funktionsfähigen Testbuild (P0–P3)

Teil VII — Fazit: ist das heute ein funktionsfähiger Testbuild?

Anhang A — Vollständige Test-Fehler und Evidenz-Index
Anhang B — Änderungsprotokoll gegenüber der Erstausgabe (2026-07-28)
Anhang C — Schnellreferenz für die nächste Person, die diesen Strang übernimmt

---

## Zusammenfassung (Executive Summary)

Die gute Nachricht zuerst, wie schon in der Erstausgabe: das zentrale Map-Upload-und-Persistenz-Feature
funktioniert weiterhin nachweislich. Für diese Edition wurde der praktische Funktionstest nicht nur
wiederholt, sondern erweitert — er durchläuft jetzt gezielt die seit 2026-07-28 neu hinzugekommenen, noch
uncommitteten Scene-Stack-Layer-Endpunkte (Karte als zweite Seite hinzufügen, Duplikat-Schutz, aktive Seite
löschen und Beförderung der nächsten), nicht mehr nur die alte, einfachere Direktaktivierung. Auch hier gilt
nach einem vollständigen Prozess-Kill-und-Neustart: die MD5-Prüfsumme der hochgeladenen Datei ist bitgenau
identisch, der beförderte aktive Layer übersteht den Neustart korrekt. Das Kernfeature funktioniert nicht nur
auf dem alten, sondern auch auf dem neuen Codepfad.

Alles Weitere in diesem Bericht behandelt weiterhin die Lücke zwischen "funktioniert, wenn man es von Hand
durchspielt" und "ist ein Build, dem das Team ohne Nachdenken vertrauen kann." Der Zustand hat sich in den
zwei Tagen seit der Erstausgabe in mehreren Dimensionen weiterentwickelt — teils zum Besseren, teils ist neue,
bisher unentdeckte technische Schuld hinzugekommen:

1. **Der zentrale Zugriffskontroll-Bug aus der Erstausgabe ist im Code behoben, aber die Produktion läuft noch
mit der verwundbaren Version — und das betrifft heute buchstäblich jeden einzelnen Nutzer der Plattform.**
Commit `3e7dbe6` (2026-07-28) korrigiert den gefährlichen `platform_role`-Standardwert `'supporter'`. Eine
direkte Abfrage der laufenden Produktions-Datenbank für diesen Bericht zeigt: **alle 4 aktuell registrierten
Nutzerkonten** tragen weiterhin `platform_role='supporter'` — es gibt keinen einzigen Nutzer mit dem neuen,
sicheren `NULL`-Standard, weil das laufende Docker-Image vom 2026-07-23 stammt, zwei Tage vor dem Fix gebaut
wurde und seither nicht neu gebaut wurde. Praktisch bedeutet das: **in der heutigen Produktion kann sich jeder
registrierte Nutzer weiterhin plattformweiten, kampagnenübergreifenden Lesezugriff und Zugriff auf das
Staff-Dashboard verschaffen** — der Fix existiert seit 48 Stunden im Repository, ohne dass er ausgeliefert
wurde. Dies ist der wichtigste Einzelbefund dieser Edition.
2. **Ein neuer, bisher nicht dokumentierter Interaktions-Bug zwischen dem alten und dem neuen
Kartenaktivierungs-Mechanismus wurde für diese Edition gefunden und live reproduziert** (Teil III.3, empirisch
bestätigt in Teil IV.5): Der Session-Vorbereitungs-Dialog in `campaigns.html` aktiviert Karten weiterhin über
den alten, direkten `POST /api/campaigns/.../sessions/.../maps/activate`-Endpunkt (schreibt
`SessionState.active_map_id` direkt), während das neue Page-Manager-UI aus demselben, hier untersuchten Diff
ausschließlich auf `SceneStack`/`SceneLayer` arbeitet. Beide Mechanismen schreiben unabhängig voneinander in
denselben `SessionState.active_map_id`-Wert, ohne sich gegenseitig zu kennen. Konkrete Konsequenz, zunächst
durch Lesen von `vtt/play/service.py::init_scene_stack` hergeleitet und dann an einer eigens aufgesetzten
isolierten Instanz per echtem HTTP nachgestellt: Initialisiert eine Spielleitung nach einer manuellen
Kartenaktivierung über die Session-Vorbereitung zusätzlich den Kartenstapel im neuen Page-Manager, wird
stillschweigend die **älteste** Kampagnenkarte (nach `created_at ASC`) aktiv — unabhängig davon, welche Karte
vorher bewusst gewählt wurde. Kein Fehler, keine Warnung, keine Bestätigung. Der Live-Test bestätigte exakt
die vorhergesagte Karte als Ergebnis der stillen Umschaltung. Dieser Befund ist neu gegenüber sowohl der
Erstausgabe als auch dem abgebrochenen Zwischenstand vom selben Tag, und wird von keiner der 414
automatisierten Tests abgedeckt (§II.4).
3. **Die fehlende Drop-Migration aus dem Zwischenstand ist bestätigt und um konkrete Produktionsdaten
ergänzt:** eine direkte Abfrage der laufenden Postgres-Datenbank zeigt, dass `session_map_layers` und
`session_tokens` weiterhin im Schema existieren, aber mit 0 Zeilen — die Tabellen sind tot, aber ungefährlich
leer. Das entschärft die Dringlichkeit etwas gegenüber einer Situation mit echten verwaisten Daten, ändert
aber nichts an der technischen Schuld selbst.
4. **Der Dokumentationszustand aus Teil I der Erstausgabe ist zu 100 % unverändert** — keine einzige der dort
dokumentierten Dateien wurde seit dem 2026-07-28 angefasst (per `find … -newermt` verifiziert). Alle vier
überlappenden Meilenstein-Nummerierungsschemata, die 3,5-monatige Dokumentationslücke, die M65-Kollision, alle
sieben Widersprüche aus §I.5 der Erstausgabe (Paketname `vtt_app`, falscher `AI_BIOS.md`-Pfad, falsche
Health-Endpunkte in `staging-deployment-guide.md`, falsche Deploy-Skriptnamen, die drei offenen GDPR-TODOs in
`SECURITY_COMPLIANCE_M34.md`) bestehen identisch fort. Dieser Bericht bestätigt jeden einzelnen Punkt erneut
per Grep/Diff, statt ihn unbesehen fortzuschreiben.
5. **Die Testsuite ist stabil bei 411/414 bestanden**, mit denselben drei vorbestehenden, unabhängigen
Fehlschlägen wie am 2026-07-28 nach dem `3e7dbe6`-Fix. Der vier Monate alte Pytest-Collection-Bug
(Zertifikatsverzeichnis-Permission-Fehler) besteht ebenfalls unverändert fort — live reproduziert für diesen
Bericht.
6. **Die Dokumentations-Korpusgröße wurde für diese Edition präzise gezählt statt geschätzt**: `docs/` enthält
167 Dateien (156 Markdown-Dokumente auf oberster Ebene plus 11 Dateien in `docs/proofs/`), `dadm/` enthält 402
Dateien, zusammen 569. Die Erstausgabe sprach im Titel von "~180 Dateien" und im Evidenz-Index von "docs/
(150+ Dateien)" — beide Angaben lagen in der richtigen Größenordnung, aber keine war exakt; 167 ist die für
heute korrekte Zahl für `docs/` allein. Zusätzlich für diese Edition erstmals vollständig statt exemplarisch
gezählt: 41 Dokumente unter `docs/` verweisen noch auf den seit dem 22. Juli falschen Paketnamen `vtt_app`
(Teil I.5, Punkt 4) — mehr als doppelt so viele wie die fünf in der Erstausgabe stellvertretend genannten.
7. **Die laufende Produktion trägt heute real gesehen noch keine Spielinhalte**: eine direkte, read-only
Abfrage der Produktionsdatenbank (Teil V.2) zeigt genau eine Kampagne, eine Session, keine Kampagnenkarte und
keinen hochgeladenen Asset-Datensatz. Weder der Zugriffskontroll-Mangel aus Punkt 1 noch die
Scene-Stack-Divergenz aus Punkt 2 haben also bislang echten Spielinhalt betroffen — ein entlastender, aber
zeitlich begrenzter Befund: er macht beide Korrekturen heute risikofrei durchführbar, solange das Zeitfenster
vor der ersten echten Nutzung noch offen ist (siehe Teil VII für die vollständige Einordnung).

Nichts davon widerspricht dem positiven Kernbefund: das Feature funktioniert, auf dem alten wie auf dem neuen
Codepfad, mit echter Persistenz über einen Prozess-Neustart hinweg. Aber die Lücke zwischen "funktioniert" und
"ist ein Build, dem man ohne wiederholte Handarbeit vertrauen kann" ist in den letzten zwei Tagen nicht
kleiner geworden — an einer Stelle (Produktions-Zugriffskontrolle) ist sie faktisch unverändert kritisch offen
geblieben, an einer anderen (die neue Page-Manager/Legacy-Aktivierung-Divergenz) ist eine neue, konkrete
Instanz desselben Musters ("zwei parallele Wahrheitsquellen für denselben Zustand") hinzugekommen, das schon
den ursprünglichen M42/SceneStack-Konflikt verursacht hatte, der das M5/M7-Programm überhaupt erst nötig
machte. Die einzige entlastende Nachricht in diesem Zusammenhang ist Punkt 7 oben: das Zeitfenster, in dem
beide Korrekturen noch ohne jedes Risiko für echte Spielinhalte möglich sind, ist heute noch offen.

---

## Teil I — Dokumentationsstand: hat sich seit 2026-07-28 etwas geändert?

### I.1 Die Ein-Satz-Version (re-verifiziert)

Dieses Repository hat Dokumentation über mindestens vier unabhängige, überlappende M-Nummerierungsschemata
angehäuft, plus ein fünftes, informelles, das seit dem 22. Juli nur in Commit-Messages verwendet wird und
dabei mit einem der anderen vier auf exakt derselben Meilenstein-Nummer kollidiert. Die beiden Dokumente, die
einer "aktuellen Status"-Wahrheitsquelle am ehesten ähneln, sind beide auf den 2026-03-30 datiert, beide vier
Monate alt, und beide erklären in ihrem eigenen Text ausdrücklich, dass sie nicht diese Wahrheitsquelle sind.
Für diese Edition wurde zuerst geprüft, ob sich daran in der Zwischenzeit etwas geändert hat, bevor der
gesamte Befund übernommen wird:

```
$ find docs dadm -newermt "2026-07-28" -type f | grep -v vtt_gap_analysis
(keine Treffer)
```

Kein einziges Dokument unter `docs/` oder `dadm/` wurde seit dem Datum der Erstausgabe verändert — mit
Ausnahme der beiden Gap-Analyse-Dateien selbst (dem 115-zeiligen Zwischenstand und, mit diesem Schreibvorgang,
dieser Datei). Der komplette folgende Abschnitt ist daher inhaltlich identisch zur Erstausgabe, aber für diese
Edition Punkt für Punkt gegen den aktuellen Stand neu geprüft, nicht blind übernommen — damit dieser Bericht
auch für jemanden ohne Zugriff auf die archivierte Erstausgabe vollständig eigenständig lesbar bleibt.

### I.2 Vier überlappende Meilenstein-Nummerierungsschemata (unverändert)

| Programm | Wo definiert | M-Bereich | Status laut eigener Dokumentation |
|---|---|---|---|
| Book UI | `dadm/artifacts/programs/milestone_program_book_ui_20.md`, verfolgt in `milestone_tracker_book_ui_20_orchestrated_v1.md` | M01–M20 | Der Tracker (datiert 2026-04-01) liest sich immer noch wörtlich "M01 ... in_progress ... current milestone", obwohl 40+ APPLY/DEPLOY/MONITOR-Dokumente für M01–M20 mit demselben Datum existieren. Ein eigenes Dokument `DADM_REALIGN_BOOK_UI_PROGRAM_STATUS_2026-04-01.md` existiert genau deshalb, weil "das ursprüngliche Orchestrator-Ledger M01-M20 als approved markiert, dieses Ledger aber nicht mehr die Produktwahrheit widerspiegelt." Dieses Realign-Dokument selbst ist inzwischen fast vier Monate alt. |
| Multitenant | `MILESTONES_M19_M36.md`, `IMPLEMENTATION_STATUS_M17_M36_FINAL.md` | M17–M36 | Selbst erklärt als "VALIDATION COMPLETE — Ready for Integration Testing" (2026-03-27) — ein Selbstbericht desselben Laufs, der ihn auch verfasst hat, ohne im Dokument selbst beigefügte unabhängige Evidenz. |
| Session Pipeline / Asset Library | `milestone_program_session_pipeline_v1.md` (Status: draft) | M63–M68 | Definiert M65 als "Drag-and-Drop Placement". Nur M63 bekam je ein Ausführungs-Prompt, und das wurde nie ausgeführt — es existiert kein Deploy- oder Monitor-Dokument dazu. |
| README | `README.md` | M1–M4 | Ein vierter, völlig separater Track: "M1: Dice Rolling API complete, M2: Map Display... complete, M3: Auth v2 complete, M4: Campaign and session management in progress" — offenbar seit der frühesten Projektphase nie aktualisiert. |
| Live-Commit-Messages (informell, seit Juli) | nur `git log`, keine Dokumente | M0-M1, M3-M4, M65 | Hier ist die Kollision konkret und datiert, keine Interpretation. Commit `73aef7f` (2026-07-23, "editable page content, pilot on dashboard + shared UI chrome") bezeichnet sich selbst als M65 — und `migrations/migration_m65_page_content.sql` bestätigt, dass es dabei wirklich um administrierbaren Seiteninhalt geht, nicht um das bereits im Session-Pipeline-Programm definierte M65 ("Drag-and-Drop Placement"). Zwei verschiedene Features, dieselbe Meilenstein-Nummer, im selben Repository. |

Re-Verifikation 2026-07-30: alle fünf Trägerdokumente existieren unverändert an denselben Pfaden;
`migrations/migration_m65_page_content.sql` existiert unverändert; `milestone_program_session_pipeline_v1.md`
definiert M65 weiterhin als Drag-and-Drop-Platzierung. Der aktuelle uncommittete M5/M7-Diff (Teil III) fügt
dem Chaos kein neues Nummerierungsschema hinzu — er referenziert ausschließlich den externen, nicht
versionierten Plan `warm-wiggling-glade.md` — aber löst auch keines der bestehenden fünf auf. Wenn die Frage
lautet "was ist der aktuelle Meilenstein", gibt es heute weiterhin keine einzig richtige Antwort.

### I.3 Die 3,5-monatige Dokumentationslücke, in einer Commit-Message selbst eingestanden (unverändert)

Commit `88ac6aa` ("chore: checkpoint 3+ months of uncommitted working-tree changes", 2026-07-22) schreibt
direkt: "Captures the accumulated restructure since the last commit (2026-03-29): vtt_app/ → vtt/ package
rename, new docs/ DADM milestone history, tests/, dadm/ framework, infra/ (deploy/ops tooling). Pure
checkpoint, no intentional content changes." 745 geänderte Dateien, 53.925 Insertionen in einem einzigen
Commit.

Die praktische Konsequenz: jedes Dokument in `docs/`, datiert vom 30. März bis 1. April — die gesamte
Book-UI-DAD-M-Historie — lag ungefähr drei Monate lang uncommittet auf der lokalen Festplatte, bevor es in
diesem einen Sammel-Commit landete. Die Commit-Daten dieser Dokumente spiegeln nicht wider, wann die
beschriebene Arbeit tatsächlich im Verhältnis zur restlichen echten Repository-Historie stattfand.

Die beiden Dokumente, die einer projektweiten "aktueller Zustand"-Referenz am ehesten ähneln, sind beide auf
den 2026-03-30 datiert und sagen beide ausdrücklich, dass sie nicht diese Referenz sind:

- `docs/SYSTEM_SNAPSHOT_2026-03-30.md` schließt mit einer eigenen Lückenliste, unter anderem: "no single
authoritative system overview that ties together product scope, architecture, operations, security, and
current status in one place."
- `docs/ENTERPRISE_DOCUMENTATION_BASELINE.md` empfiehlt ausdrücklich, als nächsten Schritt ein
`PROJECT_BRIEF.md`/`PRODUCT_REQUIREMENTS.md`/Architekturdokument zu erstellen — eine Empfehlung, die
Wahrheitsquelle zu bauen, nicht die Wahrheitsquelle selbst.

Beide verweisen zudem durchgängig auf den falschen Paketnamen (`vtt_app/`) — das Paket wurde in genau dem
Juli-22-Checkpoint-Commit, der diese März-Dokumente endlich landete, zu `vtt/` umbenannt, und keines der
beiden Dokumente wurde seither korrigiert. Re-Verifikation 2026-07-30: beide Dateien unverändert seit ihrem
letzten Commit; beide enthalten weiterhin `vtt_app`-Referenzen (siehe die vollständige Zählung in §I.5 unten).

### I.4 Das jüngste reale Feature hat gar keine DAD-M-Papierspur (unverändert, jetzt auch für den M5/M7-Diff gültig)

Der Commit `0a39990` (2026-07-23, "persistent map storage, working map upload, thumbnails, wider play view")
hat kein Discover-, Apply- oder Deploy-Dokument irgendwo in `docs/` oder `dadm/`. Das eigentliche
Planungsartefakt für diese Arbeit existiert als `/home/admin/.claude/plans/warm-wiggling-glade.md` — eine
Claude-Code-Session-Plandatei außerhalb des Git-Repositorys, im Home-Verzeichnis des Nutzers. Es ist ein
gründliches, gut belegtes Dokument, das per Grep-verifizierter Dead-Code-Analyse korrekt identifiziert, dass
der Kampagnen-Quick-Start-Ablauf hochgeladene Karten in das Legacy-Modell `SessionMapLayer` schrieb, das der
Live-Play-Pfad nie las. Aber es liegt nicht in `docs/` oder `dadm/artifacts/`, liegt überhaupt nicht in Git,
folgt nicht der von `AGENTS.md` vorgeschriebenen DAD-M-Discover/Apply-Konvention, und wurde nie durch die
eigenen `dadm-discover`/`dadm-apply`-Skills geführt.

Für diese Edition bestätigt: **derselbe Befund gilt unverändert für den aktuellen uncommitteten M5/M7-Diff aus
Teil III.** Die Milestones M5 (Page-Manager) und M7 (Legacy-Cleanup) desselben externen Plandokuments haben
ebenfalls keine Entsprechung in `docs/` oder `dadm/artifacts/` — eine erneute Suche nach jeder seit dem 1.
Juni geänderten Datei unter `docs/` findet weiterhin nur `DADM_DISCOVER_MMO_META_LAYER_CONCEPT_2026-07-21.md`
(ein unabhängiges, ausdrücklich code-änderungsfreies Zukunftskonzept) als einzigen Treffer. Der M5/M7-Diff
wiederholt also exakt dasselbe Prozessmuster wie sein Vorgänger M0–M4: echte, kohärente, geplante Arbeit,
komplett ohne die vom eigenen Projekt vorgeschriebene Papierspur.

### I.5 Widersprüche, die aufzulösen sind — vollständig re-verifiziert für diese Edition

Die Aufgabe eines Gap-Reports ist es, Widersprüche zwischen Quellen aufzuzeigen, nicht leise eine davon
auszuwählen. Jeder der folgenden acht Punkte aus der Erstausgabe wurde für diese Edition einzeln erneut
geprüft, nicht pauschal übernommen:

1. **M65 bedeutet zwei verschiedene Dinge**, je nachdem, welchem Dokument man vertraut: "Drag-and-Drop
Placement" laut dem Session-Pipeline-Programmdokument, gegenüber "editable page content" laut dem, was
tatsächlich ausgeliefert wurde (`migrations/migration_m65_page_content.sql`). *Re-Verifikation: beide Dateien
unverändert, Kollision besteht identisch fort.*

2. **"VALIDATION COMPLETE" für die Auth-/Session-Schicht (27. März) verträgt sich schlecht mit fünf separaten
Auth-/Session-Bugfix-Commits vom 23. Juli** (`c2ced36` Cookie-Max-Age, `e5570f4` Post-Logout-Race, `9976c32`
Null-Snapshot-Guard bei abgelaufener Session, `5d5e77a` temporäres Tracing-Logging, `42b165d` Ablauf-Lockout
bei bereits verbrauchtem Key) — und mittlerweile mit einem sechsten, `3e7dbe6` vom 28. Juli (dem
Zugriffskontroll-Fix, siehe Teil II/V). *Re-Verifikation: `git log --oneline -25` bestätigt alle sechs Commits
unverändert in der Historie; ein Dokument, das diese Schicht vor vier Monaten als produktionsvalidiert
erklärte, hat weder die Juli- noch die aktuelle Bugwelle vorhergesehen.*

3. **`IMPLEMENTATION_STATUS_M17_M36_FINAL.md` behauptet, das M34-GDPR-/Security-Compliance-Dokument sei
"complete"**. Das dort referenzierte Dokument, `docs/SECURITY_COMPLIANCE_M34.md`, enthält im eigenen
GDPR-Abschnitt drei ausdrückliche, ungelöste `TODO`-Markierungen. *Re-Verifikation 2026-07-30:*
   ```
   $ grep -n "TODO" docs/SECURITY_COMPLIANCE_M34.md
   46: ✅ Right to Portability: Export user data endpoint (TODO)
   49: ✅ DPA: Data Processing Agreement (TODO - legal)
   51: ✅ Breach Notification: Incident response plan (TODO)
   ```
Unverändert identisch — drei TODOs, plus die in der Erstausgabe erwähnte lange Checkliste nicht abgehakter
operativer Sicherheitsmaßnahmen (CSP, HSTS, WAF, Dependency-Scanning, Penetrationstests).

4. **Paketname-Verweise**: die Erstausgabe nannte fünf Dokumente (`SYSTEM_SNAPSHOT`,
`ENTERPRISE_DOCUMENTATION_BASELINE`, `staging-deployment-guide`, `OPERATING_PLAYBOOK_v2`,
`M63_SESSION_HUB_PARITY`), die weiterhin `vtt_app/` statt `vtt/` sagen. *Re-Verifikation, diesmal vollständig
statt exemplarisch gezählt:*
   ```
   $ grep -rl "vtt_app" docs/*.md | wc -l
   41
   ```
41 Dateien, nicht nur die fünf explizit genannten — die Erstausgabe hatte eine Stichprobe genannt, keine
Vollzählung. Die Bandbreite reicht von `SYSTEM_SNAPSHOT_2026-03-30.md` über
`ENTERPRISE_DOCUMENTATION_BASELINE.md` bis zu einem guten Dutzend
`DADM_APPLY_*`/`DADM_DISCOVER_*`/`DADM_DEPLOY_*`-Dateien der gesamten Book-UI-Welle
(`DADM_APPLY_BOOK_UI_PLAY_WORKSPACE_M20_2026-04-01.md`, `DADM_APPLY_CHARACTER_SHEET_REALIGN_2026-04-01.md`,
`DADM_DISCOVER_BOOK_UI_ARCHITECTURE_2026-03-30.md` und viele weitere). Nur das neueste Design-Dokument und
`AGENTS.md` haben den Paketnamen korrekt.

5. **Runtime-Bootstrap-Pfad**: `quickstart.md` und `README.md` weisen an, `dadm-framework/runtime/AI_BIOS.md`
zu laden; der echte Pfad ist `dadm/framework/runtime/AI_BIOS.md` (ohne Bindestrich). *Re-Verifikation:*
   ```
   $ grep -n "AI_BIOS.md" AGENTS.md README.md docs/quickstart.md
   README.md:53:1. Start from [`dadm-framework/runtime/AI_BIOS.md`](dadm-framework/runtime/AI_BIOS.md)
   docs/quickstart.md:39:1. Open [`dadm-framework/runtime/AI_BIOS.md`](dadm-framework/runtime/AI_BIOS.md)
   AGENTS.md:9:1. `dadm/framework/runtime/AI_BIOS.md`
   $ ls dadm-framework
   ls: cannot access 'dadm-framework': No such file or directory
   ```
   Unverändert identisch. Nur `AGENTS.md` hat den korrekten Pfad.

6. **Health-/Metrics-Endpunkte**: `staging-deployment-guide.md` dokumentiert `/api/health` und `/ops/metrics`;
die tatsächlich registrierten Routen sind `/health/live`, `/health/ready`, `/health/release` und `/metrics`.
*Re-Verifikation:*
   ```
   $ grep -n "\.route(" vtt/ops/routes.py
   91:@ops_bp.route("/health/live", methods=["GET"])
   106:@ops_bp.route("/health/ready", methods=["GET"])
   125:@ops_bp.route("/health/release", methods=["GET"])
   225:@ops_bp.route("/metrics", methods=["GET"])
   ```
`README.md` und `docs/quickstart.md` haben die korrekten Pfade; `staging-deployment-guide.md` weiterhin die
falschen — selbst die zwei "richtigen" Dokumente stimmen also nur untereinander überein, nicht mit dem
dritten.

7. **Deploy-Skript- und Compose-Dateinamen**: `docs/deploy-vtt-guide.md` verweist auf
Root-Level-`./deploy_vtt_roll-drauf-de.sh`, `docker-compose.vtt.roll-drauf.de.yml` und
`./enable_https_vtt_roll-drauf-de.sh` — keines davon existiert. *Re-Verifikation:*
   ```
   $ ls infra/scripts/ infra/docker/
   infra/docker/: docker-compose.live.yml  docker-compose.prod.yml  Dockerfile
   infra/scripts/: deploy_live.sh  deploy_staging.sh  enable_https.sh  ...
   ```
Die echten Gegenstücke sind unverändert `infra/scripts/deploy_live.sh`, `infra/docker/docker-compose.live.yml`
und `infra/scripts/enable_https.sh`.

8. **Ein vier Monate alter, weiterhin ungelöster Test-Collection-Bug**: `SYSTEM_SNAPSHOT_2026-03-30.md`
berichtete, dass ein einfacher `pytest`-Aufruf schon beim Sammeln der Tests scheitert, weil er in ein
Zugriffsverweigert-Zertifikatsverzeichnis läuft. *Re-Verifikation: live erneut reproduziert für diese Edition,
siehe Teil II.1 — identischer Fehler, identischer Pfad, unverändert.*

Diese vollständige Bestätigung ist selbst ein Befund: in zwei Tagen realer Code-Weiterentwicklung (17
geänderte Dateien im aktuellen Diff, siehe Teil III, plus ein neuer Commit) ist an der Dokumentationsseite
exakt nichts passiert — kein neues Status-Dokument, keine Korrektur eines der acht Widersprüche, keine
Aktualisierung der Paketnamen-Referenzen. Das mit der Erstausgabe empfohlene "ein verbindliches
Status-Dokument etablieren" (dortiges Teil V, P1) wurde nicht umgesetzt.

### I.6 Präzise Korpusgröße (neu für diese Edition)

Die Erstausgabe schätzte den Korpus mit "~180 Dateien" (Titelseite) bzw. "150+ Dateien" (Evidenz-Index) —
beide Angaben waren Schätzungen ohne exakten Befehl im Bericht selbst. Für diese Edition:

```
$ find docs -type f | wc -l
167
$ find docs -maxdepth 1 -type d
docs
docs/proofs
$ ls docs/*.md | wc -l
156
$ find docs/proofs -type f | wc -l
11
$ find dadm -type f | wc -l
402
$ find docs dadm -type f | wc -l
569
```

167 Dateien in `docs/` (156 Markdown auf oberster Ebene + 11 Beweisdateien unter `docs/proofs/`, überwiegend
die in der Erstausgabe erwähnten `wave1-*.png`/`track-a-login-proof.json`-Artefakte der März-Welle) plus 402
weitere Dateien unter `dadm/` (Framework, Skills, Agents, Prompts, Artifacts/Programs/Runs/Approvals/Sessions)
— zusammen 569. Die "~180"-Schätzung der Erstausgabe lag für `docs/` allein nahe dran; addiert man `dadm/`,
wäre "180" eine deutliche Untertreibung des Gesamtkorpus. Für zukünftige Editionen: 167 (`docs/`) und 569
(`docs/`+`dadm/`) sind jetzt die belegten Referenzwerte, kein Schätzwert mehr.

### I.7 Was das für diese Edition bedeutet

Jeder Punkt in diesem Teil I wurde für diese Edition einzeln gegen den aktuellen Repository-Stand geprüft
(Grep, `ls`, `find -newermt`, Routen-Introspektion) statt aus der archivierten Erstausgabe unbesehen
übernommen zu werden — die Befehle und ihre Ausgaben stehen jeweils direkt neben der Aussage, die sie belegen.
Das Ergebnis dieser Neuprüfung ist durchgängig: keine Abweichung. In zwei Tagen realer Weiterentwicklung an
der Codebasis (der komplette M5/M7-Diff aus Teil III plus ein neuer Commit) hat sich an keiner einzigen der
acht in §I.5 aufgeführten Dokumentationsinkonsistenzen etwas geändert, und kein neues Dokument wurde erstellt,
das eine der vier konkurrierenden Meilenstein-Zählungen auflöst. Wo diese Edition über die Erstausgabe
hinausgeht, ist bei der Präzision (die volle Zählung der `vtt_app`-Referenzen in §I.5, Punkt 4, und die exakte
Korpusgröße in §I.6), nicht beim Inhalt selbst.

---

## Teil II — Zustand von Codebasis und Testsuite

### II.1 Baut der aktuelle Tree überhaupt?

Ja — und für diese Edition mit einem stärkeren Beweis als beim letzten Mal. Statt nur `create_app()` +
`db.create_all()` gegen eine leere SQLite-Datei laufen zu lassen, wurde für Teil IV dieser Edition eine
vollständige, isolierte Instanz der Anwendung über `app.py` als echter Serverprozess gestartet (echtes
`socketio.run()`, echter TCP-Port, siehe Teil IV) — der uncommittete Diff bootet also nicht nur im Testclient,
sondern als echter, langlaufender Prozess unter Last durch eine vollständige Nutzerreise.

Der vier Monate alte, in der Erstausgabe dokumentierte Pytest-Collection-Bug wurde erneut reproduziert,
unverändert:

```
$ ./venv/bin/python -m pytest -q --collect-only
...
E   PermissionError: [Errno 13] Permission denied: '/home/admin/projects/roll-drauf-vtt/ops/certbot/conf/accounts'
=========================== short test summary info ============================
ERROR  - PermissionError: [Errno 13] Permission denied: '/home/admin/projects...'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
no tests collected, 1 error in 0.14s
```

```
$ ls -la ops/certbot/conf/
drwx------ 1 root root 56 Mar 27 19:38 accounts
drwx------ 1 root root 34 Mar 27 19:38 archive
```

Root-eigene Let's-Encrypt-Verzeichnisse, für den aktuellen Nutzer nicht lesbar, seit mindestens dem 27. März
unverändert. Mit `tests/`-Scope läuft die Collection sauber: **414 Tests gesammelt** (identisch mit der
Erstausgabe). Es existiert weiterhin keine `pytest.ini`, `pyproject.toml` oder `conftest.py` im
Repository-Root, die `testpaths = ["tests"]` zum Standard machen würde — das in Teil V/P0 der Erstausgabe als
offen markierte Item ist weiterhin offen.

### II.2 Vollständiger Testsuite-Lauf: 411 bestanden, 3 fehlgeschlagen (unverändert)

```
$ ./venv/bin/python -m pytest tests/ -q
...
FAILED tests/test_character_journey_productization.py::test_character_sheet_template_links_view_edit_and_campaign_context
FAILED tests/test_moderation_actions.py::TestModerationActions::test_admin_can_ban_and_revoke
FAILED tests/test_pre_table_usability_closeout.py::test_character_surfaces_strengthen_sheet_to_campaign_continuity
3 failed, 411 passed, 1917 warnings in 218.38s
```

Dies ist für diese Edition ein **selbst durchgeführter, unabhängiger Nachlauf**, nicht eine Übernahme der im
Zwischenstand berichteten Zahl — der Auftrag für diese Edition war ausdrücklich, die Suite erneut auszuführen
statt der Zahl aus dem abgebrochenen Zwischenstand blind zu vertrauen. Ergebnis: identisch zur im
Zwischenstand berichteten Zahl (411/3) und identisch zur "nach der Korrektur"-Zahl aus der Erstausgabe vom
2026-07-28. Die drei Fehlschläge sind exakt dieselben drei wie am 2026-07-28 nach dem `3e7dbe6`-Fix — siehe
Anhang A für die vollständige Ursachenanalyse jedes einzelnen, die aus der Erstausgabe unverändert übernommen
wird, weil eine erneute Codeprüfung (siehe unten) keine neuen Ursachen findet.

Erneute, vollständige Ursachenprüfung für diese Edition (nicht nur ein Zahlen-Vergleich mit dem Zwischenstand
— jede der drei Ursachen wurde erneut am Code nachvollzogen):

**#1 — `test_moderation_actions.py::TestModerationActions::test_admin_can_ban_and_revoke`, Test-Fixture-Drift,
kein Produktionsbug.** Die Fixture `admin_user` in dieser Testdatei setzt nur das Legacy-Feld `role_id=3` und
setzt nie das neuere String-Feld `platform_role`. Die Ban-Berechtigung des Moderations-Endpunkts
(`can_apply_ban` → `is_admin`) prüft ausschließlich `platform_role` — der eigene Inline-Kommentar im Code sagt
sogar "Use `platform_role` (M17) instead of legacy `role_id`". Der von der Fixture simulierte Admin wird also,
korrekterweise, unter der aktuellen (beabsichtigten) Implementierung nicht als Admin erkannt, und der Test
schlägt mit einem `403` fehl, den die echte Berechtigungslogik zu Recht zurückgibt:
```
assert create_response.status_code == 201
AssertionError: 403 == 201
```
Das ist genau dieselbe "duales Rollensystem (`role_id` + `platform_role`), undokumentierter
Deprecation-Plan"-Schuld, die unabhängig davon bereits im eigenen Known-Limitations-Abschnitt von
`IMPLEMENTATION_STATUS_M17_M36_FINAL.md` geflaggt wurde. Re-Verifikation: `git log -1 --format=%H --
vtt/permissions.py tests/test_moderation_actions.py` zeigt für beide Dateien keinen Commit nach `3e7dbe6` —
keine der beiden wurde seit der Erstausgabe verändert, die Ursache ist identisch.

**#2 —
`test_character_journey_productization.py::test_character_sheet_template_links_view_edit_and_campaign_context`,
veraltete Testerwartung.** Der Test prüft, ob der String "Open Campaign Context" in `character_sheet.html`
vorkommt; der tatsächliche Button-Text, unverändert seit dem März→Juli-Checkpoint-Commit `88ac6aa`, lautet
"Campaign Context" (ohne "Open"). Eine Ein-Zeilen-Korrektur in beide Richtungen würde das lösen; das schlägt
seit Monaten unbemerkt fehl.

**#3 —
`test_pre_table_usability_closeout.py::test_character_surfaces_strengthen_sheet_to_campaign_continuity`, ein
Feature, das nur durch seinen Test beschrieben wird.** Der Test prüft, ob ein bestimmter Hinweistext ("return
to campaign prep to assign this hero to a session before play") in der Nähe eines Elements `sheetNextStepNote`
erscheint. Dieses Element existiert im Template als leeres, verstecktes `<div>` ohne Inhalt und wird von
keiner JavaScript-Datei in der Codebasis je befüllt — eine repository-weite Suche nach dem erwarteten Text und
nach jedem Skript, das `sheetNextStepNote`s Inhalt setzt, ergab erneut nichts. Das beabsichtigte Feature wurde
entweder nie fertiggestellt oder irgendwann entfernt; der Test ist der einzige verbliebene Beleg, dass es je
existieren sollte.

Für alle drei gilt unverändert: keine der betroffenen Dateien liegt im aktuellen uncommitteten M5/M7-Diff, und
alle drei reproduzieren sich identisch unabhängig davon, ob dieser Diff vorhanden ist oder nicht —
vorbestehende Schulden, durch dieses und das vorherige Audit aufgedeckt, nicht durch aktuell laufende Arbeit
verursacht.

### II.3 Größte Dateien — Play-Bereich wächst weiter am schnellsten

```
$ find vtt -name "*.py" | xargs wc -l | sort -rn | head -12
 1871 vtt/campaigns/routes.py
 1264 vtt/characters/routes.py
  996 vtt/socket_handlers.py
  713 vtt/endpoints/registration_keys.py
  684 vtt/auth/routes.py
  598 vtt/community/routes.py
  586 vtt/endpoints/admin_assets.py
  552 vtt/services/asset_organizer.py
  542 vtt/play/routes.py
  525 vtt/endpoints/dashboard_home.py
  521 vtt/roll_drauf/catalog.py
  518 vtt/play/service.py
 18036 total
```

`vtt/play/routes.py` (542, +168 durch den aktuellen Diff) und `vtt/play/service.py` (518, +146) bleiben
unverändert unter den zehn größten Dateien des Repositorys — bestätigt exakt die im Zwischenstand berichteten
Zeilenzahlen. Kein akutes Konzentrationsrisiko, aber der Play-Bereich bleibt der am schnellsten wachsende
Codebereich.

### II.4 Kapazitätsbezogener Rundgang: Status jedes größeren Funktionsbereichs, nicht nur des aktuellen Diffs

Die Erstausgabe konzentrierte sich stark auf den Map-Upload/Persistenz-Pfad, weil das der damalige Prüfauftrag
war. Für diese Edition wurde zusätzlich ein kurzer, aber vollständiger Rundgang durch jeden größeren
Funktionsbereich der Anwendung gemacht — nicht nur durch den aktuellen M5/M7-Diff — auf Basis der 51
Testdateien (414 Einzeltests) und einer Stichprobenprüfung der zugehörigen Routen-Module. Ziel: sicherstellen,
dass die "3 von 414 fehlgeschlagen"-Zahl aus §II.2 nicht durch tote oder übersprungene Testbereiche in anderen
Ecken der Anwendung verzerrt wird, und dass kein größerer Funktionsbereich existiert, der stillschweigend ganz
ohne Testabdeckung dasteht.

| Funktionsbereich | Zentrale Testdateien | Tests (ca.) | Status |
|---|---|---|---|
| Auth & Registrierung | `test_auth.py`, `auth_test.py`, `test_admin_platform_auth.py`, `test_discord_only_login_guild_access_gate.py` | ~40 | Grün. Deckt Passwort-Login, JWT-Cookie-Ausstellung, Discord-OAuth-Gate, Registrierungsschlüssel-Verbrauch und admin-seitige Plattform-Auth ab. Die MFA-Codepfade (`user.verify_mfa_code`) sind über diese Dateien mitgetestet, aber MFA ist in keiner der geprüften Env-Dateien standardmäßig aktiviert. |
| Zugriffskontrolle / Berechtigungen | `test_permissions_m17.py` (37 Tests, die größte einzelne Testdatei im Repository) | 37 | Grün nach `3e7dbe6` (siehe §V.2 zur Deploy-Lücke). Deckt `can_view_campaign`, `can_view_all_campaigns`, alle vier `PLATFORM_ROLES`-Stufen sowie Team-View-Zugriff ab. |
| Kampagnen & Sessions | `test_campaigns.py` (22), `test_campaign_creation_productization.py`, `test_campaign_hub_session_prep_productization.py`, `test_maps.py`, `test_session_state.py`, `test_session_state_machine.py` | ~50 | Grün. Deckt Kampagnen-CRUD, Einladungs-/Beitritts-Fluss, Kartenverwaltung (`CampaignMap`-CRUD) und den Sitzungs-Zustandsautomaten ab. Keine dieser Dateien testet die in §III.3/§IV.5 gefundene Kombination aus `maps/activate` gefolgt von `scene-stack/init` — eine konkrete Lücke, die dieser Bericht schließt. |
| Play-Runtime (Scene Stack, Bootstrap, Übergänge) | `test_scene_stack_api.py` (13, neu durch den aktuellen Diff), `test_play_bootstrap_api.py`, `test_play_permissions.py`, `test_play_boundary_preparation.py`, `test_play_transition_choreography.py`, `test_reverse_transition_choreography.py`, `test_play_rejoin_socket.py`, `test_ready_check.py` | ~45 | Grün, inklusive der 13 neuen Scene-Stack-Layer-Tests aus dem aktuellen Diff. Siehe Teil IV für die zusätzliche, über die Testsuite hinausgehende Ende-zu-Ende-Verifikation dieses Bereichs per echtem HTTP mit Prozess-Neustart. |
| Kampf / Initiative / Tokens | `test_combat_api.py`, `test_combat_realtime.py`, `test_tokens_realtime.py` (8) | ~20 | Grün. Diese Tests laufen weiterhin gegen die M43-Initiative-Routen (`.../initiative/*`), die der aktuelle Diff laut Teil III.1 ausdrücklich **nicht** anfasst — nur die M42-Map-Layer-CRUD wurde entfernt, die M43-Token-/Initiative-Routen in `sessions.py` bleiben unverändert bestehen. Die tote `SessionToken`-Tabelle aus Teil III.2/V.2 ist ein anderes, seit dem inerten `USE_SESSION_SOCKET_V2`-Pfad ungenutztes Modell und hat mit diesen aktiven, getesteten Initiative-Routen nichts zu tun — Verwechslungsgefahr wegen ähnlicher Namensgebung, aber zwei unterschiedliche Codepfade. |
| Charaktere & Fortschritt | `test_characters.py` (18), `test_character_creator_contract_implementation.py`, `test_character_identity_productization.py`, `test_character_journey_productization.py` (1 Fehlschlag, §II.2 #2), `test_character_sheet_resources.py`, `test_sheet_rendering_content_display.py` (34), `test_m24_progression_content.py` (35), `test_m26_level_up_mechanic.py` (24), `test_m27_character_export_import.py` (28), `test_direct_character_session_assignment_productization.py` | ~150 | Größter Testbereich der gesamten Suite (über ein Drittel aller 414 Tests), überwiegend grün. Der einzige Fehlschlag hier ist der bekannte, triviale String-Mismatch aus §II.2 #2. |
| Community / Guilds / Chat / Moderation | `test_dashboard_social_hub_guild_navigation.py`, `test_community_realtime.py`, `test_chat_api.py`, `test_moderation_actions.py` (1 Fehlschlag, §II.2 #1) | ~25 | Überwiegend grün; der einzige Fehlschlag ist der bekannte Fixture-Drift-Bug aus §II.2 #1 (`role_id`/`platform_role`). |
| Seiteninhalt / Dashboard / Ops | `test_page_content.py` (15), `test_core_book_runtime_routes.py`, `test_ops_endpoints.py` (8), `test_reports_api.py` | ~30 | Grün. `test_page_content.py` deckt das M65-Feature ab (siehe die Namenskollision in §I.2) — funktional unabhängig von der Dokumentationsverwirrung um seine Meilenstein-Nummer. `test_ops_endpoints.py` bestätigt die vier realen Health-/Metrics-Routen aus §I.5 Punkt 6. |
| Assets / Storage | `test_asset_library.py` (7), `test_map_asset_pre_integration_session_prep_deepening.py` | ~10 | Grün für den `local`-Storage-Adapter (der einzige in Produktion aktive). Der `S3StorageAdapter`-Codepfad aus §II.5 hat keine eigene Testdatei — konsistent mit seinem Status als nie genutzter, aber potenziell instabiler Codepfad. |
| Diverse UX-/Closeout-Härtung | `test_action_bar_v1.py`, `test_book_shell_ux_stabilization.py` (durch den aktuellen Diff mitgeändert), `test_fallback_boundary_cleanup.py`, `test_hardening_closeout.py`, `test_journey_nav_cta_cleanup.py`, `test_return_seam_preparation.py`, `test_session_prep_surface_before_table.py`, `test_pre_table_usability_closeout.py` (1 Fehlschlag, §II.2 #3) | ~20 | Überwiegend grün; einziger Fehlschlag ist der verwaiste `sheetNextStepNote`-Text aus §II.2 #3. Diese Dateien tragen fast durchgängig DAD-M-Meilenstein-Namen in ihrem eigenen Dateinamen (`_closeout`, `_stabilization`, `_productization`) ohne dass ein entsprechendes DAD-M-Dokument in `docs/` dazu existiert — dieselbe in Teil I.4 beschriebene Papierspur-Lücke zieht sich also durch den gesamten Testbestand, nicht nur durch den aktuellen Diff. |

Ergebnis dieses Rundgangs: kein größerer Funktionsbereich der Anwendung ist ohne Testabdeckung, und die drei
bekannten Fehlschläge sind tatsächlich isoliert auf genau drei kleine, unabhängige Stellen begrenzt
(Fixture-Drift, zwei veraltete String-Erwartungen) — keine verdeckte Häufung von Fehlschlägen in einem
bestimmten Funktionsbereich. Der wertvollste Fund dieses Rundgangs ist aber negativ: **keine der 414 Tests
deckt die Kombination aus `maps/activate` und `scene-stack/init` auf derselben Session ab** — genau die Lücke,
die den in Teil III.3/IV.5 gefundenen und live reproduzierten Fehler durch die automatisierte Suite unentdeckt
ließ.

### II.5 Requirements, S3-Risiko und TODO-Marker — erneut geprüft

Wie im Zwischenstand berichtet: `boto3` fehlt weiterhin in `requirements.txt`, obwohl
`vtt/storage/__init__.py::S3StorageAdapter.__init__` es importiert (`import boto3`, Zeile 70).
`STORAGE_PROVIDER` ist in keiner der geprüften Env-Dateien (`.env.vtt.roll-drauf.de`, `.env.example`,
`infra/docker/docker-compose.live.yml`) gesetzt — der Code-Default `'local'` greift überall. Der Adapter würde
erst bei der ersten tatsächlichen Umstellung auf S3 hart mit `ModuleNotFoundError` abstürzen; inert, solange
niemand `STORAGE_PROVIDER=s3` setzt. Keine TODO/FIXME-Marker in den vom aktuellen Diff betroffenen Dateien
(erneut per Grep bestätigt).

---

## Teil III — Der uncommittete M5/M7-Refactor: was er ändert, und eine bisher nicht dokumentierte Lücke

### III.1 Zusammenfassung des Diffs (Bestätigung des Zwischenstands)

Der Workspace enthält weiterhin denselben uncommitteten Refactor, der bereits im 115-zeiligen Zwischenstand
vom selben Tag identifiziert wurde: das parallele, nie aktive Map/Token-System (`SessionMapLayer`,
`SessionToken`, `socket_handlers_sessions.py`, Feature-Flag `USE_SESSION_SOCKET_V2`) wird entfernt und durch
eine vollständige Page-Manager-Oberfläche auf Basis des bereits bestehenden `SceneStack`/`SceneLayer`-Modells
ersetzt — Meilensteine M5 (Page-Manager-UI) und M7 (Altlasten-Entfernung) eines repository-externen Plans
(`warm-wiggling-glade.md`, wie in der Erstausgabe beschrieben, weiterhin außerhalb des Repos, weiterhin ohne
DAD-M-Papierspur).

```
$ git status --porcelain | wc -l
19
$ git diff --stat
 infra/docker/docker-compose.live.yml      |   1 -
 tests/test_book_shell_ux_stabilization.py |   7 +-
 tests/test_scene_stack_api.py             | 195 ++++++++++++
 vtt/__init__.py                           |   4 -
 vtt/config.py                             |   1 -
 vtt/endpoints/assets.py                   |  74 -----
 vtt/endpoints/sessions.py                 | 277 +----------------
 vtt/models/__init__.py                    |   4 +-
 vtt/models/session_map_layer.py           | 136 ---------
 vtt/models/session_token.py               | 126 --------
 vtt/play/routes.py                        | 168 +++++++++++
 vtt/play/service.py                       | 146 +++++++++
 vtt/socket_handlers_sessions.py           | 480 ------------------------------
 vtt/static/js/play-client.js              |  37 +++
 vtt/static/js/play-socket.js              |   1 +
 vtt/static/js/play-ui.js                  | 199 +++++++++++--
 vtt/templates/play.html                   | 103 ++++++-
 17 files changed, 821 insertions(+), 1138 deletions(-)
```

Plus zwei untracked Dateien: `.env.vtt.roll-drauf.de.bak.20260723_165703` (siehe §V.5) und dieses Dokument
selbst. `git log --oneline -25` zeigt, dass `3e7dbe6` (der Zugriffskontroll-Fix) seit der Erstausgabe der
einzige neue Commit ist — kein weiterer Commit ist seit dem 2026-07-28 dazugekommen; der Diff besteht seit
mindestens zwei Tagen unverändert uncommittet.

| Bereich | Vorher | Nachher |
|---|---|---|
| Datenmodell | `SessionMapLayer` (136 Zeilen), `SessionToken` (126 Zeilen) | Entfernt; `vtt/models/__init__.py` verliert beide Importe und `__all__`-Einträge (bestätigt per `git diff`, siehe unten) |
| Socket-Handler | `vtt/socket_handlers_sessions.py` (480 Zeilen), nur aktiv wenn `USE_SESSION_SOCKET_V2=true` | Datei gelöscht; Flag aus `vtt/config.py` und `docker-compose.live.yml` entfernt |
| REST-Endpunkte | M42-Map-Layer-CRUD und M43-Token-CRUD in `sessions.py`; dritter "aktive Karte"-Mechanismus in `assets.py` (`.../active-layer`) | Beide Blöcke entfernt |
| Business-Logik | — | Neu in `vtt/play/service.py`: `get_or_create_scene_stack`, `add_scene_layer`, `update_scene_layer`, `reorder_scene_layers`, `delete_scene_layer` (mit Beförderungslogik) |
| REST-Fläche | — | Neu in `vtt/play/routes.py`: `POST/PUT/DELETE .../scene-stack/layers[...]`, hinter `is_operator_role()` |
| Client | — | `play-ui.js`: vollständige Page-Manager-UI (Thumbnails, Reorder, Sichtbarkeits-Toggle, Löschen, "Karte hinzufügen") |

```
$ git diff vtt/models/__init__.py
-from vtt.models.session_map_layer import SessionMapLayer  # M42
-from vtt.models.session_token import SessionToken  # M43
```

**M6 (Token-/Asset-Platzierung per Drag-and-Drop)** ist weiterhin **nicht begonnen** — keine Spur im aktuellen
Diff oder sonst im Repository, bestätigt per erneuter Grep-Suche.

### III.1a Die neue Business-Logik im Detail (`vtt/play/service.py`)

Für diese Edition wurde jede der fünf neuen Funktionen einzeln gelesen, nicht nur über die Testresultate
beurteilt, weil genau diese Funktionen den in §III.3 beschriebenen Interaktionsfehler enthalten:

`add_scene_layer()` prüft zunächst per Datenbankabfrage, ob die Kampagnenkarte bereits als Layer im Stack
existiert (`existing_layer`-Check), und fängt zusätzlich einen `IntegrityError` beim Commit ab — doppelte
Absicherung gegen ein Race, bei dem zwei gleichzeitige Anfragen denselben Layer anlegen wollen:

```python
existing_layer = SceneLayer.query.filter_by(
    scene_stack_id=scene_stack.id, campaign_map_id=campaign_map.id
).first()
if existing_layer:
    return None, None, (jsonify({"error": "campaign map is already a layer in this scene stack"}), 409)
...
try:
    db.session.commit()
except IntegrityError:
    db.session.rollback()
    return None, None, (jsonify({"error": "campaign map is already a layer in this scene stack"}), 409)
```

Das ist genau der Duplikat-Schutz, der in Teil IV.3 dieser Edition live als `409` bestätigt wurde — die
Vorab-Prüfung UND der `IntegrityError`-Fang wurden beide durch den praktischen Test indirekt durchlaufen (die
Vorab-Prüfung greift im Normalfall; der `IntegrityError`-Pfad würde nur unter echter Nebenläufigkeit greifen
und wurde durch den sequenziellen Testlauf nicht separat erzwungen).

`reorder_scene_layers()` ist bewusst alles-oder-nichts: Es lädt zuerst alle betroffenen `SceneLayer`-Zeilen
anhand der übergebenen IDs, prüft, dass jede angefragte `layer_id` tatsächlich zum Stack gehört, und bricht
mit `400` ab, *bevor* irgendeine Mutation stattfindet, falls auch nur eine ID nicht passt — es gibt keinen
Teilerfolg-Zustand, bei dem einige Layer bereits umsortiert wurden und andere nicht.

`delete_scene_layer()` enthält die in Teil IV.3 verifizierte Beförderungslogik: Wird der *aktive* Layer
gelöscht, sucht die Funktion den nächsten Layer nach `order_index ASC, id ASC` und aktiviert ihn über
`activate_scene_layer()` (dieselbe Funktion, die auch die explizite Aktivierung via API bedient — kein
separater Code-Pfad für "Beförderung" vs. "manuelle Aktivierung"). Existiert kein weiterer Layer mehr (letzter
Layer eines Stacks gelöscht), räumt die Funktion explizit `scene_stack.active_layer_id`, `game_session.map_id`
und `state.active_map_id` auf `None`/`null` auf, statt einen verwaisten Verweis auf einen nicht mehr
existierenden Layer stehen zu lassen:

```python
if next_layer:
    state = activate_scene_layer(campaign, game_session, next_layer)
else:
    scene_stack.active_layer_id = None
    game_session.map_id = None
    state = ensure_session_state(campaign, game_session)
    state.active_map_id = None
    ...
```

Dieser letzte Fall (Löschen des allerletzten Layers) wird von den 13 neuen Tests in `test_scene_stack_api.py`
abgedeckt, wurde aber vom praktischen Funktionstest in Teil IV.3 dieser Edition nicht eigens durchlaufen (dort
blieb nach der Löschung des aktiven Layers noch ein zweiter Layer übrig, der befördert wurde) — die Lücke ist
über die automatisierte Suite geschlossen, auch wenn der hands-on-Test sie nicht separat nachvollzogen hat.

`activate_scene_layer()` selbst — die gemeinsame Funktion hinter expliziter Aktivierung und automatischer
Beförderung — ist exakt die Stelle, die bei jeder Aktivierung `state.active_map_id` synchron zum gewählten
Layer setzt. Das ist im vom Diff eingeführten Codepfad also in sich konsistent; die in §III.3 beschriebene
Divergenz entsteht ausschließlich dadurch, dass `activate_session_map()` in `vtt/campaigns/routes.py` (der
*alte*, vom Diff nicht angefasste Endpunkt) denselben `state.active_map_id`-Wert über einen komplett separaten
Codepfad schreibt, ohne `SceneLayer`/`SceneStack` je zu berühren.

### III.2 Sauberer Schnitt — bestätigt

```
$ grep -rn "session_map_layer|session_token|socket_handlers_sessions|SessionMapLayer|SessionToken\b|USE_SESSION_SOCKET_V2" \
    --include="*.py" --include="*.js" --include="*.html" --include="*.sql" --include="*.yml" .
tests/test_tokens_realtime.py:151: def test_room_isolation_prevents_cross_session_token_events
```

Genau ein Treffer, und der ist ein Fehlalarm (Testname, keine echte Referenz — bestätigt identisch zur
Erstausgabe). Kein Code importiert die gelöschten Module noch.

### III.3 Neuer Befund: zwei unabhängige, nicht synchronisierte "aktive Karte"-Mechanismen bleiben nach dem Cleanup bestehen

Das ist der wichtigste inhaltliche Neubefund dieser Edition und geht über das hinaus, was der abgebrochene
Zwischenstand fand. Der Zwischenstand hatte korrekt notiert, dass der M5/M7-Diff einen *dritten* "aktive
Karte"-Mechanismus entfernt (`assets.py`'s `.../active-layer`-Endpunkte). Bei der für diese Edition
durchgeführten capability-by-capability-Prüfung des Play-Bereichs zeigt sich: **ein vierter, älterer
Mechanismus bleibt unangetastet bestehen** und wird vom aktuellen Frontend weiterhin aktiv benutzt.

`vtt/campaigns/routes.py`, Zeile 975 (`activate_session_map`, Route `POST
/api/campaigns/<id>/sessions/<id>/maps/activate`):

```python
state = _ensure_session_state(campaign, game_session)
state.active_map_id = campaign_map.id
state.bump_version()
_refresh_state_snapshot(state)
game_session.map_id = campaign_map.id
db.session.commit()
```

Dieser Endpunkt schreibt `SessionState.active_map_id` **direkt**, ohne jede Berührung von
`SceneStack`/`SceneLayer`. Er wird weiterhin aktiv aufgerufen — von `campaigns.html`, Zeile 2386, aus der
Funktion `activatePrepSessionMap()`, die im Session-Vorbereitungs-Dialog der Kampagnenseite hängt (dem
naheliegendsten Ort, an dem eine Spielleitung heute eine Karte für eine bevorstehende Session auswählt):

```javascript
async function activatePrepSessionMap(campaignId, sessionId) {
    const select = document.getElementById("sessionPrepMapSelect");
    const mapId = Number(select?.value || 0);
    ...
    await auth.makeAuthRequest(`/api/campaigns/${campaignId}/sessions/${sessionId}/maps/activate`, "POST", {
        map_id: mapId,
    });
    ...
}
```

Parallel dazu liest das neue Page-Manager-UI in `/play` (`play-ui.js`) für seine Seitenliste
**ausschließlich** aus `bootstrap.scene_stack` (via `serialize_scene_stack()`, das `SceneStack`/`SceneLayer`
serialisiert), während dieselbe Seite ihre "aktive Karte"-Pille und den Kartenhintergrund aus
`bootstrap.state_payload.active_map` (also `SessionState.active_map_id`) rendert:

```javascript
// _renderLayers() — die neue Page-Manager-Seitenliste:
const stack = this.bootstrap?.scene_stack;
const layers = (stack && Array.isArray(stack.layers)) ? stack.layers... : [];
if (!layers.length) {
    container.innerHTML = "<div class='muted'>Noch keine Seiten. Unten eine Karte hinzufuegen.</div>";
}

// _renderState() — die aktive-Seite-Pille und der Kartenhintergrund:
const statePayload = this.bootstrap?.state_payload;
const activeMap = statePayload?.active_map;
```

Und `vtt/play/service.py::init_scene_stack()` (der Handler hinter dem einzigen Weg, überhaupt Einträge in die
Page-Manager-Seitenliste zu bekommen, den Button "Kartenstapel initialisieren"):

```python
maps = query.order_by(CampaignMap.created_at.asc()).all()
...
first_layer = SceneLayer.query.filter_by(scene_stack_id=scene_stack.id) \
    .order_by(SceneLayer.order_index.asc(), SceneLayer.id.asc()).first()
if first_layer:
    scene_stack.active_layer_id = first_layer.id
    game_session.map_id = first_layer.campaign_map_id
    state = ensure_session_state(campaign, game_session)
    state.active_map_id = first_layer.campaign_map_id   # <- überschreibt bedingungslos
```

`init_scene_stack()` nimmt **immer** die älteste nicht-archivierte Kampagnenkarte (`created_at ASC`) als
aktiven Layer — unabhängig davon, was zuvor in `SessionState.active_map_id` stand. Der konkrete,
reproduzierbare Ablauf, der daraus folgt:

1. Spielleitung lädt Karte A, dann Karte B in die Kampagne hoch (A ist älter).
2. Spielleitung nutzt die Session-Vorbereitung, um explizit **Karte B** für die anstehende Session zu
aktivieren (`POST .../maps/activate`, `map_id=B`) — der einzige Weg, den das Kampagnen-UI dafür anbietet.
3. Spielleitung öffnet `/play`: die aktive-Seite-Pille und der Kartenhintergrund zeigen korrekt Karte B (aus
`state_payload.active_map`) — aus Nutzersicht funktioniert alles wie erwartet.
4. Die neue Page-Manager-Seitenliste zeigt aber "Noch keine Seiten" — verwirrend, weil sichtbar eine Karte
aktiv ist, aber keine "Seite" dafür existiert.
5. Klickt die Spielleitung daraufhin auf "Kartenstapel initialisieren" (naheliegend, um die leere Seitenliste
zu befüllen), wechselt die aktive Karte der gesamten Session **stillschweigend auf Karte A** — ohne
Fehlermeldung, ohne Bestätigungsdialog, ohne dass irgendetwas im UI signalisiert, dass sich die zuvor bewusst
gewählte aktive Karte gerade geändert hat.

Dies ist strukturell dasselbe Muster, das laut Planungsdokument (`warm-wiggling-glade.md`, referenziert in
Commit `0a39990`) den ursprünglichen M42-Bug verursacht hat — zwei parallele Schreibpfade auf denselben
logischen Zustand ("welche Karte ist gerade aktiv"), die sich gegenseitig nicht kennen. Das M5/M7-Programm hat
einen dieser Pfade (den M42-`SessionMapLayer`-Pfad) entfernt, aber einen zweiten, älteren (`maps/activate`)
unangetastet gelassen, während gleichzeitig ein dritter, neuer (`scene-stack`) hinzukam. Weder die 195 neuen
Testzeilen in `test_scene_stack_api.py` noch der praktische Funktionstest in Teil IV dieses Berichts decken
diese Interaktion ab, weil beide ausschließlich den `scene-stack`-Pfad isoliert prüfen, nie in Kombination mit
einem vorherigen `maps/activate`-Aufruf auf derselben Session. Das ist kein hypothetisches Risiko — es ist der
naheliegende Weg, wie eine reale Spielleitung heute beide UI-Oberflächen nacheinander benutzen würde, weil
nichts im Produkt sie davon abhält oder sie warnt.

**Empfehlung** (auch in Teil VI aufgenommen): entweder `init_scene_stack()` so anpassen, dass es einen bereits
gesetzten `game_session.map_id`/`SessionState.active_map_id` als bevorzugten ersten Layer respektiert statt
ihn stillschweigend zu überschreiben, oder den alten `maps/activate`-Aufruf aus `campaigns.html`
entfernen/umleiten auf den neuen Scene-Stack-Pfad, sodass nur noch eine Wahrheitsquelle für "aktive Karte"
existiert. Ein dritter, minimaler Zwischenschritt: `init_scene_stack()` sollte zumindest eine Warnung
protokollieren oder im Response signalisieren, wenn es eine bereits aktive Karte überschreibt, die nicht mit
dem gewählten ersten Layer übereinstimmt.

---

## Teil IV — Praktische Funktionsverifikation (hands-on, End-to-End, mit Prozess-Neustart)

### IV.1 Methode: dieselbe wie in der Erstausgabe, aber gezielt auf den neuen Codepfad gerichtet

Die Erstausgabe testete den *alten*, einfacheren Aktivierungs-Mechanismus Ende-zu-Ende (Karte hochladen,
direkt aktivieren, Zustand abrufen, Prozess neu starten). Diese Edition wiederholt dieselbe Methodik — eigene
isolierte Flask-/SocketIO-Instanz, eigene SQLite-Datei, echtes HTTP über `requests`, echter Cookie-basierter
JWT-Login mit aktivem CSRF-Schutz, echter Prozess-Kill-und-Neustart-Zyklus — testet aber diesmal gezielt den
*neuen*, noch uncommitteten Scene-Stack-Layer-Pfad, weil das der Teil des Systems ist, um den es in dieser
Edition zentral geht.

Aufbau: isolierte Instanz unter `127.0.0.1:5099`, eigene SQLite-Datei, `STORAGE_PROVIDER=local` mit eigenem
Asset-Verzeichnis, `RATELIMIT_STORAGE_URL=memory://` (kein Redis nötig für einen Einzelprozess),
Registrierungsschlüssel über dieselbe interne Funktion (`create_registration_keys`) gemintet, die auch das
CLI-Bootstrap-Tooling nutzt.

### IV.2 Was Schritt für Schritt getestet wurde

1. Zwei echte Accounts registriert (Spielleitung, Spieler) über `POST /api/auth/register` mit echten
Registrierungsschlüsseln.
2. Beide über `POST /api/auth/login` eingeloggt (Cookie-JWT + aktiver CSRF-Schutz, `X-CSRF-TOKEN`-Header aus
dem `csrf_access_token`-Cookie extrahiert und mitgeschickt — nicht deaktiviert oder umgangen).
3. Echte Kampagne angelegt, Spieler eingeladen, Einladung angenommen — der reale Mitgliedschafts-Ablauf.
4. Echte Session angelegt.
5. Ein echtes 800×600-PNG im Speicher erzeugt und über den echten Multipart-Endpunkt `POST
/api/assets/campaigns/{id}/upload` hochgeladen (`asset_type=map`).
6. Einen `CampaignMap`-Datensatz angelegt, der auf die Vorschau-URL des Uploads verweist.
7. **Neu gegenüber der Erstausgabe:** den Scene-Stack über den uncommitteten Endpunkt `POST
.../scene-stack/init` initialisiert.
8. **Neu:** versucht, dieselbe Karte ein zweites Mal als Layer hinzuzufügen (`POST .../scene-stack/layers`) —
bestätigt den in `add_scene_layer()` dokumentierten Duplikat-Schutz (`409`).
9. **Neu:** eine zweite, eigenständige Kampagnenkarte angelegt und erfolgreich als zweiter Layer hinzugefügt
(`201`).
10. Den ersten Layer explizit aktiviert (`POST .../scene-stack/layers/{id}/activate`) und über `GET .../state`
bestätigt, dass die richtige Karte als aktiv gemeldet wird.
11. Unauthentifizierten Zugriff auf das Asset geprüft (`401`), dann mit einer frischen, unbeteiligten
Spieler-Session heruntergeladen und die MD5-Prüfsumme mit dem Original verglichen.
12. **Neu:** den *aktiven* Layer gelöscht (`DELETE .../scene-stack/layers/{id}`) und bestätigt, dass der
zweite Layer automatisch befördert wird (`active_layer_id` wechselt korrekt).
13. Den Serverprozess vollständig per `SIGTERM` beendet, über einen fehlgeschlagenen Health-Check bestätigt,
dass nichts mehr lauscht.
14. Einen brandneuen Prozess gegen dieselbe Datenbankdatei gestartet, mit einem komplett neuen Login (kein
wiederverwendeter In-Memory-Zustand) erneut verbunden.
15. Zustand und Asset-Download erneut abgerufen.

### IV.3 Ergebnis: Kernfeature UND der neue Scene-Stack-Pfad funktionieren, inklusive Neustart

```
== upload map asset (real 800x600 PNG, real multipart upload) ==
asset_id 1 md5 de2d94fa0231164116d1863eba3f0c78
== create campaign map referencing uploaded asset ==
map_id 1
== init scene stack (uncommitted M5/M7 endpoint) ==
scene_stack_id 1 active_layer_id 1
== confirm duplicate-map guard: re-adding the SAME map to the stack is rejected ==
confirmed 409 on duplicate campaign_map_id (matches partial draft's finding 5.x)
== create a second distinct campaign map and add it as a second layer ==
second_layer_id 2
== explicitly activate first layer ==
== GET session state (dm client) ==
state.active_map: {... 'id': 1, 'name': 'E2E Map', ...}
== unauthenticated asset download must be 401 ==
== fresh player session downloads asset, md5 must match ==
md5 before restart OK: de2d94fa0231164116d1863eba3f0c78
== player session state must also show the same active map ==
== delete the ACTIVE layer, confirm promotion of the other layer ==
delete-active-layer response: {"scene_stack": {"active_layer_id": 2, ...}}
== killing server process (SIGTERM) ==
confirmed: no process listening after kill
== restarting fresh process against same sqlite file ==
== brand-new login (no reused in-memory state) ==
== GET session state, new process ==
state after restart: {... 'id': 2, 'name': 'E2E Map 2', ...}
confirmed: promoted active layer (map_id_2) survived process restart
== GET asset download, new process ==
md5 after restart: de2d94fa0231164116d1863eba3f0c78

=== ALL ASSERTIONS PASSED ===
original md5:       de2d94fa0231164116d1863eba3f0c78
before restart md5: de2d94fa0231164116d1863eba3f0c78
after restart md5:  de2d94fa0231164116d1863eba3f0c78
```

Jeder Schritt war erfolgreich. Konkret nach dem vollständigen Prozess-Neustart: der zuvor durch Layer-Löschung
beförderte Layer (Karte 2) blieb korrekt aktiv — die Beförderungslogik in `delete_scene_layer()` schreibt also
tatsächlich persistent in die Datenbank, nicht nur in den In-Process-Zustand. Die Asset-MD5-Prüfsumme blieb
über alle drei Messpunkte (vor Löschung, nach Löschung, nach Neustart) bitgenau identisch. Zugriffskontrolle
(401 ohne Auth) blieb korrekt über den gesamten Test hinweg bestehen.

### IV.4 Was das beweist — und was nicht

Es beweist, dass der komplette neue Scene-Stack-Layer-Pfad — Initialisierung, Duplikat-Schutz, Hinzufügen
eines zweiten Layers, explizite Aktivierung, Löschen des aktiven Layers mit korrekter Beförderung —
Ende-zu-Ende über echtes HTTP funktioniert, inklusive echter Persistenz über einen Prozess-Neustart hinweg,
mit korrekter Zugriffskontrolle. Es bestätigt außerdem exakt den in §III.3 beschriebenen
Duplikat-Schutz-Mechanismus als tatsächlich funktionierend, nicht nur als Absicht im Code.

Es beweist **nicht von sich aus**, dass die in Teil III.3 beschriebene Divergenz zwischen `maps/activate` und
dem Scene-Stack-Pfad harmlos ist — dieser erste Testlauf hat den alten `maps/activate`-Endpunkt bewusst nicht
in Kombination mit `scene-stack/init` auf derselben Session aufgerufen. Genau diese Kombination wurde deshalb
in einem zweiten, gezielten Testlauf separat nachgestellt (§IV.5). Beide Tests testen weiterhin nicht die
laufenden Produktions-Container (die ohnehin zwei Commits + den gesamten Diff hinter dem Workspace liegen,
siehe Teil V), kein S3-Storage-Backend, und kein echtes gleichzeitiges Socket-Verhalten mehrerer Nutzer.

### IV.5 Gezielte Reproduktion des Teil-III.3-Befunds: aus Code-Lesung wird ein verifizierter, live reproduzierter Fehler

Der in Teil III.3 beschriebene Befund (zwei unabhängige "aktive Karte"-Mechanismen, die sich beim
Zusammenspiel gegenseitig überschreiben) wurde dort ausschließlich durch Lesen von drei Dateien hergeleitet
(`campaigns.html`, `play-ui.js`, `vtt/play/service.py`). Für diese Edition wurde diese Herleitung zusätzlich
**live an einer zweiten isolierten Instanz nachgestellt**, um aus einer Code-Lesung eine tatsächlich
reproduzierte, beobachtete Fehlfunktion zu machen — genau die Art von Verifikation, die dieser Bericht in Teil
IV bereits für den Kernfeature-Test verlangt, hier angewendet auf einen neuen, potenziell kritischen Befund
statt nur auf den bereits bekannten Erfolgsfall.

Szenario, exakt wie in Teil III.3 beschrieben, nachgespielt über echtes HTTP gegen eine frische, isolierte
Instanz:

1. Zwei Kampagnenkarten angelegt: "Map A (older, tavern)" zuerst, dann (nach einer erzwungenen Sekunde
Zeitabstand, um die `created_at`-Reihenfolge eindeutig zu machen) "Map B (newer, boss arena)".
2. Die Spielleitung aktiviert **bewusst und explizit** Map B über den Session-Vorbereitungs-Endpunkt `POST
.../sessions/{id}/maps/activate` — exakt der Aufruf, den `campaigns.html::activatePrepSessionMap()` auslöst.
3. Der `/play`-Bootstrap-Endpunkt wird abgefragt: `state_payload.active_map` zeigt korrekt Map B, aber
`scene_stack` ist `null` — die Page-Manager-Seitenliste wäre an dieser Stelle leer, obwohl sichtbar eine Karte
aktiv ist.
4. Die Spielleitung klickt "Kartenstapel initialisieren" (`POST .../scene-stack/init`) — der einzige im UI
angebotene Weg, die leere Seitenliste zu befüllen.
5. Der Sitzungszustand wird erneut abgefragt.

Ergebnis des Live-Laufs:

```
Map A (older) id=1, Map B (newer) id=2
Step 1: DM explicitly activated Map B via legacy /maps/activate -> Map B (newer, boss arena)
Step 2: /play bootstrap BEFORE init -> state_payload.active_map = 'Map B (newer, boss arena)' (id=2), scene_stack = None
Step 3: DM clicked 'Kartenstapel initialisieren'
Step 4: active map AFTER init_scene_stack -> 'Map A (older, tavern)' (id=1)

=== DIVERGENCE CONFIRMED ===
DM explicitly chose Map B (id=2) via Session-Prep.
After clicking 'Kartenstapel initialisieren', active map silently changed to
id=1 ('Map A (older, tavern)') -- the OLDEST campaign map, not the one the DM had
chosen. No error, no warning, no confirmation dialog.
```

Die in Teil III.3 aus dem Code hergeleitete Vorhersage trifft exakt zu: die bewusst gewählte Map B wird ohne
jede Fehlermeldung, Warnung oder Bestätigung durch die älteste Kampagnenkarte (Map A) ersetzt, sobald die
Spielleitung den naheliegenden nächsten Schritt im neuen Page-Manager-UI ausführt. Dies ist damit kein
hypothetisches Risiko mehr, sondern ein für diesen Bericht live reproduzierter, deterministischer Fehler —
reproduzierbar mit jeder Kampagne, die mindestens zwei Karten besitzt, sobald beide UI-Oberflächen
(Session-Vorbereitung und Page-Manager) in dieser Reihenfolge benutzt werden. Dieser Befund sollte vor dem
Commit/Deploy von M5/M7 behoben werden (siehe Teil VI, P0).

---

## Teil V — Infrastruktur- und Deployment-Realität

### V.1 Was heute tatsächlich läuft

```
$ docker ps -a | grep -i vtt
72d0d5e71f73   roll-drauf-vtt-app   "gunicorn ..."   6 days ago   Up 43 hours   roll-drauf-vtt-app-1
4b7a4df8ad13   redis:7-alpine       ...              8 days ago   Up 43 hours   roll-drauf-vtt-redis-1
eb9352742a37   postgres:16-alpine   ...              8 days ago   Up 43 hours   roll-drauf-vtt-db-1
```

Drei Container, alle laufend (plus das unabhängige `palworld-server`, siehe separates Projekt-Gedächtnis).
Bildzeitpunkt bestätigt:

```
$ docker inspect roll-drauf-vtt-app-1 --format '{{.Created}} {{.Image}}'
2026-07-23T21:08:19Z sha256:985f9be8...
$ docker inspect roll-drauf-vtt-app:latest --format '{{.Created}}'
2026-07-23T23:08:19+02:00
```

Praktisch zeitgleich mit Commit `0a39990` (Autor-Datum 2026-07-23 23:08:04) — das Image wurde seit fünf Tagen
nicht neu gebaut. Es trägt weder `3e7dbe6` (den Zugriffskontroll-Fix vom 2026-07-28) noch den kompletten
M5/M7-Diff aus Teil III.

Zum Vergleich, welche Images auf dem Host insgesamt existieren (zur Einordnung, ob `roll-drauf-vtt-app:latest`
das einzig relevante ist):

```
$ docker images | grep -i vtt
roll-drauf-vtt-app:latest    985f9be81b0d   342MB
roll-drauf-vtt:m3-latest     61367d5a3c08   329MB
vtt-prod-app:latest          2b9a1f3a417d   291MB
```

Drei VTT-bezogene Images liegen auf dem Host, von denen laut `docker ps -a` nur `roll-drauf-vtt-app:latest`
tatsächlich in einem laufenden Container verwendet wird. `roll-drauf-vtt:m3-latest` und `vtt-prod-app:latest`
sind vermutlich Überbleibsel früherer Deployment-Versuche (die Namensgebung `m3-latest` legt einen
Zusammenhang mit der M3-Welle aus der Book-UI-Historie nahe, `vtt-prod-app` klingt nach einem älteren,
separaten Produktions-Namensschema) — keines der beiden wird von aktuellem Docker-Compose- oder Deploy-Tooling
referenziert, und keines wird in dieser Edition weiter verfolgt, da sie keinen laufenden Container versorgen.
Sie sind aber, ähnlich wie die leeren Verzeichnisse in §V.4, ein weiteres kleines Indiz für mehrere
übereinanderliegende, nie aufgeräumte Deployment-Generationen.

### V.2 Der Zugriffskontroll-Fix ist seit 48 Stunden ungedeployt — mit einer konkreten, gemessenen Konsequenz

```
$ docker exec roll-drauf-vtt-app-1 env | grep USE_SESSION_SOCKET_V2
USE_SESSION_SOCKET_V2=false
$ docker exec roll-drauf-vtt-app-1 grep -n session_map_layer /app/vtt/models/__init__.py
32:from vtt.models.session_map_layer import SessionMapLayer  # M42
```

Der Container läuft nachweislich noch mit dem alten `vtt/models/__init__.py` (vor der M5/M7-Entfernung) — und,
wichtiger, vor `3e7dbe6`. Für diese Edition wurde direkt gegen die laufende Produktions-Datenbank geprüft, wie
sich das in echten Nutzerdaten niederschlägt:

```
$ docker exec roll-drauf-vtt-db-1 psql -U vtt -d vtt -c "SELECT platform_role, count(*) FROM users GROUP BY platform_role;"
 platform_role | count
---------------+-------
 supporter     |     4
(1 row)
```

**Alle vier aktuell registrierten Nutzerkonten** tragen `platform_role='supporter'` — den Wert, den
`can_view_campaign`/`can_view_all_campaigns` als privilegiertes Plattform-Personal mit kampagnenübergreifendem
Lesezugriff und Zugriff auf das Team-Dashboard behandeln. Es gibt keinen einzigen Nutzer mit dem seit
`3e7dbe6` korrekten `NULL`-Standard, weil jedes dieser vier Konten vor dem Fix (oder über das ungepatchte
Produktions-Image) angelegt wurde. Das ist keine theoretische Restschuld — es ist der tatsächliche, heute
gültige Zugriffskontroll-Zustand der Plattform: **jeder der vier Nutzer kann faktisch jede Kampagne der
anderen einsehen**, weil der Fix zwar seit zwei Tagen im Repository existiert, aber nie in ein neues Image
gebaut und deployt wurde. Ob unter diesen vier Konten echte, bewusst vergebene Supporter sind, lässt sich aus
der Datenbank allein nicht unterscheiden — genau die in der Erstausgabe beschriebene menschliche Entscheidung,
die durch den Code-Fix allein nicht getroffen wird.

Zusätzlich, als Randbefund während dieser Abfrage: die von `§`5.1 (siehe Anhang B) beschriebenen toten
Tabellen `session_map_layers` und `session_tokens` existieren im Produktionsschema, aber mit **0 Zeilen**:

```
$ docker exec roll-drauf-vtt-db-1 psql -U vtt -d vtt -c \
  "SELECT (SELECT count(*) FROM session_map_layers) AS map_layers, (SELECT count(*) FROM session_tokens) AS tokens;"
 map_layers | tokens
------------+--------
          0 |      0
```

Das entschärft die Dringlichkeit der fehlenden Drop-Migration leicht — es gibt keine verwaisten Nutzdaten, nur
leeres Schema-Gerümpel — ändert aber nichts an der grundsätzlichen Feststellung, dass Modell- und Schema-Stand
auseinanderlaufen.

**Wichtige Einordnung des tatsächlichen Nutzungsvolumens in Produktion**, ebenfalls für diese Edition erhoben
und für die Risikobewertung in Teil VII relevant:

```
$ docker exec roll-drauf-vtt-db-1 psql -U vtt -d vtt -c \
  "SELECT (SELECT count(*) FROM campaigns) AS campaigns, (SELECT count(*) FROM game_sessions) AS sessions, \
          (SELECT count(*) FROM campaign_maps) AS maps, (SELECT count(*) FROM assets) AS assets;"
 campaigns | sessions | maps | assets
-----------+----------+------+--------
         1 |        1 |    0 |      0
```

Die laufende Produktion trägt heute genau eine Kampagne, eine Session, **keine** Kampagnenkarte und **keinen**
hochgeladenen Asset-Datensatz. Das bedeutet: weder der in Teil III.3/IV.5 gefundene
Scene-Stack/`maps/activate`-Divergenz-Bug noch das zentrale Map-Upload-Feature selbst sind in der echten
Produktionsdatenbank bisher überhaupt einmal real durchlaufen worden — die vorhandene Kampagne/Session hat nie
eine Karte bekommen. Praktisch heißt das: das aktuelle Deployment befindet sich funktional noch im
Vorlaunch-/internen Testbetrieb, nicht im Wirkbetrieb mit echten Spieltischen. Das ändert nichts an der
Dringlichkeit, den Zugriffskontroll-Fix zu deployen (vier echte Konten sind vier echte Konten, unabhängig vom
Kampagnenvolumen) oder die Divergenz vor dem nächsten Release zu beheben — es bedeutet aber, dass beide
Korrekturen heute noch ohne Migrations- oder Datenbereinigungsrisiko für bestehende Spielinhalte möglich sind.
Dieses Zeitfenster schließt sich, sobald die erste echte Kampagne beginnt, tatsächlich Karten zu benutzen.

### V.3 Es existiert weiterhin keine echte Staging-Umgebung

Unverändert gegenüber der Erstausgabe: `infra/scripts/deploy_staging.sh` importiert weiterhin `from vtt_app
import create_app` (Zeilen 53–54) und würde bei Ausführung sofort mit `ModuleNotFoundError` scheitern:

```
$ grep -n "^from\|^import" infra/scripts/deploy_staging.sh
...
53:    from vtt_app import create_app
54:    from vtt_app.extensions import db
```

Die drei Dokumente, die einen etablierten Staging-Prozess suggerieren (`staging-deployment-guide.md`,
`STAGING_READY.md`, `DEPLOYMENT_COMPLETE.md`), beschreiben weiterhin nur denselben einmaligen, 30-minütigen
lokalen Lauf vom 2026-03-27, mit einer lokalen SQLite-Datei und dem Flask-Entwicklungsserver auf
`localhost:5000` — nie wiederholt, keine dauerhafte Umgebung. Es existiert in der Praxis weiterhin genau eine
Umgebung: die laufende Produktion. Für diese Edition ist das umso relevanter, als der in Teil IV/IV.5
durchgeführte praktische Test zeigt, dass eine echte, reproduzierbare Staging-Umgebung genau die Art von
Regression (die `maps/activate`/Scene-Stack-Divergenz) hätte auffangen können, die stattdessen erst durch eine
für diesen Bericht eigens aufgesetzte Ad-hoc-Instanz gefunden wurde.

Ergänzend zur Migrationslage: das Repository verwaltet Schemaänderungen weiterhin über handgeschriebene
SQL-Dateien statt Alembic. Aktueller Bestand:

```
$ ls migrations/*.sql | wc -l
11
$ ls migrations/
migration_m17_add_platform_roles_and_audit.sql
migration_m18_user_lifecycle.sql
migration_m19_add_assets.sql
migration_m37_registration_keys.sql
migration_m41_session_state.sql
migration_m42_map_layers.sql
migration_m43_tokens_initiative.sql
migration_m44_session_assets.sql
migration_m46_theme_settings.sql
migration_m64_asset_library.sql
migration_m65_page_content.sql
```

Elf Migrationsdateien, jede nach einer M-Nummer benannt — und diese Nummern gehören erkennbar zu mindestens
zwei der in §I.2 beschriebenen, sich widersprechenden Zählschemata gleichzeitig (M17–M19 zum
Multitenant-Programm, M41–M46 und M64–M65 zu keinem der vier dort explizit benannten Programme, sondern
offenbar zu einer weiteren, in dieser Liste erstmals sichtbaren informellen Zählung).
`migration_m42_map_layers.sql` und `migration_m43_tokens_initiative.sql` sind exakt die Migrationen, deren
Tabellen (`session_map_layers`, `session_tokens`) der aktuelle M5/M7-Diff aus dem Code, aber nicht aus dem
Schema entfernt (§III.1, §V.2) — die zugehörige SQL-Datei bliebe auch nach einem Commit dieses Diffs
unverändert im Repository liegen, als historisches Dokument einer inzwischen im Code nicht mehr existierenden
Struktur, ohne begleitende Drop-Migration.

### V.4 Zwei mysteriöse leere Verzeichnisse und der tote nginx-Service — unverändert

```
$ ls -la /opt/vtt /home/RollDrauf_PROD/VTT
/opt/vtt: leer, admin, erstellt 27. März
/home/RollDrauf_PROD/VTT: leer, root, erstellt 11. Juli
```

Beide weiterhin ohne jede Erklärung im Repository. Der in `docker-compose.live.yml` definierte, aktuell nicht
laufende `nginx`-Service (Bind-Mount auf ein von Docker automatisch angelegtes leeres Verzeichnis statt der
erwarteten Konfigurationsdatei `ops/nginx/vtt.roll-drauf.de.conf`) bleibt ebenfalls unverändert bestehen. Das
tatsächliche Routing läuft weiterhin ausschließlich über Host-`nginx` (`/etc/nginx/conf.d/vtt.conf`,
`proxy_pass http://172.19.0.3:5000` — feste Container-IP, per Kommentar im Compose-File seit `e983394`
dokumentiert, aber weiterhin nicht in `docs/`).

### V.5 Unversionierte Backup-Datei — unverändert offen

`.env.vtt.roll-drauf.de.bak.20260723_165703` liegt weiterhin untracked im Repo-Root, byte-identisch groß (1275
Bytes) zur aktiven `.env.vtt.roll-drauf.de`. Zwei Tage älter als bei der letzten Prüfung, weiterhin nicht
verschoben oder gelöscht.

---

## Teil VI — Priorisierter Weg zu einem funktionsfähigen Testbuild

Wie in der Erstausgabe: geordnet danach, was das Vertrauen in den Build blockiert, nicht nach
Umsetzungsaufwand. Punkte, die bereits in der Erstausgabe oder im Zwischenstand als erledigt markiert wurden,
werden hier nur verifiziert weitergeführt, nicht neu erfunden.

### P0 — Das Produktions-Image neu bauen und deployen

Der wichtigste, konkret messbare offene Punkt dieser Edition. `3e7dbe6` behebt einen aktiven, heute in
Produktion nachweislich ausnutzbaren Zugriffskontroll-Bug (alle vier bestehenden Nutzerkonten betroffen, §V.2)
und liegt seit 48 Stunden ungedeployt im Repository. Ein Neubau und Redeploy des `roll-drauf-vtt-app`-Images
auf den aktuellen Commit sollte vor jeder anderen Priorität stehen. Menschliche Folgeaufgabe, die der Deploy
allein nicht löst: entscheiden, welche der vier bestehenden `platform_role='supporter'`-Konten echte, bewusst
vergebene Supporter sind und welche versehentliche Alt-Defaults, bevor ein Daten-Backfill auf `NULL` erfolgen
kann.

### P0 — M5/M7 committen und im selben Fenster deployen

Der uncommittete Diff ist getestet (18/18 diff-spezifische Tests grün, plus der in Teil IV dieser Edition
durchgeführte End-to-End-Nachweis über einen vollständigen Prozess-Neustart) und die Altsystem-Entfernung ist
referenzfrei (§III.2). Bereit für Commit und Rebuild — idealerweise im selben Deployment-Fenster wie der
`3e7dbe6`-Rebuild aus P0 oben, um nicht zwei separate Produktions-Rebuilds für zusammengehörige, bereits
verifizierte Änderungen zu benötigen.

### P0 — Die in Teil III.3 gefundene, in Teil IV.5 live reproduzierte Scene-Stack/`maps/activate`-Divergenz vor dem Deploy entschärfen

Neu gegenüber Erstausgabe und Zwischenstand, und nicht nur aus Code-Lesung hergeleitet, sondern für diesen
Bericht tatsächlich reproduziert (§IV.5): eine bewusst über die Session-Vorbereitung aktivierte Karte wird
beim anschließenden Initialisieren des Page-Managers stillschweigend durch die älteste Kampagnenkarte ersetzt,
ohne Fehlermeldung oder Bestätigung. Bevor M5/M7 live geht, sollte mindestens eine der beiden folgenden
Optionen umgesetzt werden: (a) `init_scene_stack()` in `vtt/play/service.py` so ändern, dass ein bereits
gesetzter `game_session.map_id` als bevorzugter erster Layer respektiert wird statt stillschweigend
überschrieben zu werden, oder (b) den `activatePrepSessionMap()`-Aufruf in `campaigns.html` (Zeile 2386) auf
den neuen Scene-Stack-Pfad umleiten, sodass nur noch eine Wahrheitsquelle für "aktive Karte pro Session"
existiert. Ein pragmatischer Zwischenschritt, falls weder (a) noch (b) kurzfristig machbar ist:
`init_scene_stack()` sollte zumindest serverseitig loggen und im Response-Payload signalisieren, wenn es eine
bereits über `maps/activate` gesetzte aktive Karte überschreibt, die nicht mit dem gewählten ersten Layer
übereinstimmt — das würde das stille Verhalten wenigstens sichtbar machen, auch ohne es sofort strukturell zu
beheben. Ohne eine dieser Korrekturen wird das M5/M7-Programm zwar den ursprünglichen M42-Bug beheben, aber
eine strukturell identische neue Instanz desselben Musters ("zwei Schreibpfade auf denselben Zustand, die sich
nicht kennen") direkt daneben stehen lassen — und das mit der automatisierten Suite unentdeckt, wie §II.4
zeigt.

### P0 — Den Pytest-Collection-Fehler beheben

Unverändert offen seit vier Monaten (`SYSTEM_SNAPSHOT_2026-03-30.md`), erneut reproduziert für diese Edition
(§II.1). Eine `pytest.ini`/`pyproject.toml` mit `testpaths = ["tests"]` würde den sicheren Aufruf zum Standard
machen.

### P1 — Drop-Migration für `session_map_layers`/`session_tokens` nachziehen

Unverändert offen. Neu für diese Edition: bestätigt, dass beide Tabellen in Produktion mit 0 Zeilen leer sind
(§V.2) — kein Datenverlust-Risiko, aber weiterhin Modell-Schema-Drift, die vor dem nächsten Schema-Audit
bereinigt werden sollte, idealerweise im selben Fenster wie der M5/M7-Deploy.

### P1 — Ein verbindliches Status-Dokument etablieren

Unverändert offen seit der Erstausgabe — in den zwei Tagen dazwischen wurde keines erstellt (§I.1). Kein
Neuschreiben des gesamten Korpus; ein einziges Dokument, das Stand heute festhält: aktueller Paketname
(`vtt`), aktueller Meilenstein-/Feature-Stand in Klartext, aktuelle Testsuite-Erfolgsquote (411/414), und ein
Verweis auf diesen Bericht.

### P1 — Die Papierspur des M5/M7-Refactors mit dem Rest des Codes in Einklang bringen

Unverändert offen. Was fehlt, ist kein Code — es ist ein kurzes `DADM_APPLY`/`DEPLOY`-Dokument, das festhält,
dass diese Phase stattgefunden hat.

### P1 — Die beiden veralteten Charakterbogen-Tests beheben oder zurückziehen

Unverändert offen, siehe Anhang A für die vollständige Ursachenanalyse.

### P2 — Das duale `role_id`/`platform_role`-System auflösen

Unverändert offen — Ursache des `test_moderation_actions.py`-Fehlschlags, bereits in
`IMPLEMENTATION_STATUS_M17_M36_FINAL.md` als unvollendeter "90-Tage-Deprecation-Plan" geflaggt.

### P2 — Das kaputte Staging-Deploy-Tooling beheben oder zurückziehen

Unverändert offen — `infra/scripts/deploy_staging.sh` scheitert weiterhin sofort am veralteten
`vtt_app`-Import.

### P2 — Dokumentations-Paketnamen-Referenzen korrigieren

Neu präzisiert für diese Edition: 41 Dateien unter `docs/` verweisen noch auf `vtt_app` statt `vtt` (§I.1) —
mehr als die fünf in der Erstausgabe exemplarisch genannten. Kein Blocker für den Testbuild selbst, aber ein
wachsendes Risiko für jeden neuen Mitwirkenden, der sich an der Dokumentation statt am Code orientiert.

### P3 — Infrastruktur-Schutt aufräumen

Unverändert offen: `/opt/vtt`, `/home/RollDrauf_PROD/VTT`, der tote `nginx`-Compose-Service, die
unversionierte `.env`-Backup-Datei, sowie — neu benannt in dieser Edition — die beiden ungenutzten
Docker-Images `roll-drauf-vtt:m3-latest` und `vtt-prod-app:latest` (§V.1), die keinen laufenden Container
versorgen.

---

## Teil VII — Fazit: ist das heute ein funktionsfähiger Testbuild?

Die Erstausgabe beantwortete diese Frage direkt, statt sie vage zu lassen, und diese Edition tut dasselbe, mit
demselben Maßstab: ein Build, auf den das Team zeigen und sagen kann "das funktioniert, und wir wissen auch,
warum wir das glauben." Beantwortet für jede der vier in der Erstausgabe aufgespannten Dimensionen, mit dem
Stand von heute:

**Funktioniert das Kernfeature (Karten-Upload, -Persistenz, -Aktivierung)?** Ja, unverändert, und für diese
Edition sogar auf zwei unabhängigen Codepfaden bestätigt: dem alten, direkten `maps/activate`-Pfad (implizit
über die in Teil IV.5 nachgestellte erste Hälfte des Szenarios) und dem neuen, uncommitteten
Scene-Stack-Layer-Pfad (Teil IV.1–IV.4, vollständig mit Prozess-Neustart verifiziert). Das ist weiterhin die
eindeutig positive Nachricht dieses Berichts.

**Gibt es eine einzige verbindliche Wahrheitsquelle für den Projektstatus?** Nein, unverändert. Teil I dieser
Edition bestätigt jeden der acht in der Erstausgabe dokumentierten Widersprüche identisch fort, plus die
Präzisierung, dass die `vtt_app`-Paketnamen-Verwirrung mit 41 betroffenen Dateien deutlich breiter ist als
ursprünglich exemplarisch dargestellt. In den zwei Tagen zwischen den Editionen wurde nichts unternommen, dies
zu beheben.

**Ist die zuletzt gelieferte Feature-Arbeit sauber dokumentiert und ohne verdeckte Nebenwirkungen?** Nein, und
hier ist die Lage gegenüber der Erstausgabe an einer konkreten Stelle schlechter geworden, nicht besser: der
M5/M7-Diff hat weiterhin keine DAD-M-Papierspur (identisch zu M0–M4 zuvor), UND er lässt eine strukturell
neue, live reproduzierte Zustandsdivergenz zurück (Teil III.3/IV.5), die die automatisierte Testsuite nicht
abdeckt (Teil II.4). Das M5/M7-Programm behebt den ursprünglichen M42-Bug redlich, führt aber ein
Geschwistermuster desselben Fehlers wieder ein, bevor der erste überhaupt vollständig ausgeräumt ist.

**Existiert eine echte, reproduzierbare Staging-Umgebung, die genau solche Regressionen vor der Produktion
abfangen würde?** Nein, unverändert — `deploy_staging.sh` ist weiterhin kaputt, die drei "Staging"-Dokumente
beschreiben weiterhin nur einen einmaligen Lauf vom März. Der in Teil IV.5 gefundene Fehler wurde stattdessen
nur deshalb entdeckt, weil für diesen Bericht eigens eine Ad-hoc-Instanz aufgesetzt wurde — ein Prozess, der
für jede zukünftige Änderung wiederholt werden müsste, weil es keine dauerhafte Umgebung gibt, die das
automatisch übernimmt.

**Und die neue, für diese Edition zentrale fünfte Dimension: ist der aktuelle Produktionszustand sicher?**
Nein, konkret nicht: alle vier bestehenden Nutzerkonten der Plattform laufen heute mit dem
Zugriffskontroll-Bug, dessen Fix seit 48 Stunden im Repository liegt, aber nie deployt wurde (Teil V.2). Das
ist keine abstrakte Softwarequalitäts-Frage mehr, sondern ein aktiver, messbarer, heute wirksamer
Sicherheitsmangel in der laufenden Produktion.

**Gesamtbild:** Der Abstand zwischen "das Kernfeature funktioniert" und "das ist ein Build, dem man ohne
wiederholte Handarbeit vertrauen kann" hat sich in den zwei Tagen zwischen den Editionen nicht verkleinert. An
der wichtigsten Einzelstelle — Produktions-Zugriffskontrolle — ist er unverändert in vollem Umfang offen,
obwohl die Lösung seit zwei Tagen fertig im Repository bereitliegt. Das ist kein Kapazitätsproblem und kein
technisch schwieriges Problem; es ist ein Prozess- und Priorisierungsproblem: der Rebuild-und-Redeploy-Schritt
aus Teil VI, P0, ist eine Sache von Minuten, sobald jemand ihn anstößt.

**Eine wichtige, entlastende Einordnung zum Schluss, die diese Edition zusätzlich zur Erstausgabe liefert**
(§V.2): die laufende Produktion trägt heute genau eine Kampagne, eine Session, keine Kampagnenkarte und keinen
hochgeladenen Asset — real genutzt wird die Plattform noch nicht. Weder der Zugriffskontroll-Mangel noch die
Scene-Stack-Divergenz haben also bereits echten Spielinhalt beschädigt oder echte Nutzerdaten kompromittiert,
soweit sich das aus der Datenbank ablesen lässt. Das ist ein Zeitfenster, kein Freibrief: Es macht beide
Korrekturen heute risikofrei durchführbar, weil kein bestehender Spieltisch durch einen Deploy oder eine
Migration gestört würde. Dieses Fenster schließt sich mit der ersten echten Nutzung der Plattform — und genau
deshalb gehören P0/P0/P0 aus Teil VI (Zugriffskontroll-Redeploy, M5/M7-Commit-und-Deploy, Divergenz-Fix) an
den Anfang der nächsten Arbeitssitzung, nicht ans Ende eines irgendwann folgenden Aufräum-Sprints.

---

## Anhang A — Vollständige Test-Fehler und Evidenz-Index

### A.1 Pytest-Fehlerausgabe (vollständig, Lauf vom 2026-07-30)

```
FAILED tests/test_character_journey_productization.py::test_character_sheet_template_links_view_edit_and_campaign_context
  assert "Open Campaign Context" in content
  AssertionError — tatsächlicher Template-Text ist "Campaign Context" (character_sheet.html,
  unverändert seit Checkpoint-Commit 88ac6aa)

FAILED tests/test_moderation_actions.py::TestModerationActions::test_admin_can_ban_and_revoke
  assert create_response.status_code == 201
  AssertionError: 403 == 201
  Ursache: admin_user-Fixture setzt nur Legacy-role_id=3; is_admin() prüft ausschließlich
  platform_role (Inline-Kommentar: "Use platform_role (M17) instead of legacy role_id")

FAILED tests/test_pre_table_usability_closeout.py::test_character_surfaces_strengthen_sheet_to_campaign_continuity
  assert "return to campaign prep to assign this hero to a session before play" in sheet
  AssertionError — sheetNextStepNote-Element existiert, ist aber leer; kein JS irgendwo
  befüllt diesen Text

3 failed, 411 passed, 1917 warnings in 218.38s
```

Die 1.917 Warnungen sind überwiegend eine einzige, wiederholte `DeprecationWarning` für
`datetime.datetime.utcnow()` — unverändert gegenüber der Erstausgabe, weiterhin ein Wartungsschulden-Signal,
kein funktionales Problem.

### A.2 Transkript des praktischen Funktionstests (diese Edition, Kernergebnisse)

```
register dm                                -> 201
login dm                                   -> 200 (Cookie + CSRF ausgestellt)
register player                            -> 201
login player                               -> 200
create campaign                            -> 201 campaign_id=1
invite player                              -> 201
accept invite                              -> 200
create session                             -> 201 session_id=1
upload map asset (echtes 800x600 PNG)      -> 201 asset_id=1, md5=de2d94fa0231164116d1863eba3f0c78
create campaign map                        -> 201 map_id=1
init scene stack (M5/M7-Endpunkt)          -> 201 scene_stack_id=1, active_layer_id=1
add duplicate map as layer                 -> 409 (Duplikat-Schutz bestätigt)
create second campaign map                 -> 201 map_id=2
add second map as layer                    -> 201 second_layer_id=2
activate first layer (explizit)            -> 200
GET session state (dm client)              -> 200 active_map.id=1
GET asset download, ohne Auth              -> 401 (korrekt abgelehnt)
GET asset download, frische Spieler-Session -> 200 md5 identisch mit Original
GET session state, frische Spieler-Session -> 200 active_map.id=1
DELETE aktiven Layer                       -> 200 active_layer_id wechselt zu 2 (Beförderung)
-- Serverprozess beendet (SIGTERM), Health-Check bestätigt: nichts lauscht mehr --
-- neuer Prozess aus derselben Datenbankdatei gestartet --
GET session state, neuer Prozess           -> 200 active_map.id=2 (NEUSTART ÜBERLEBT,
                                               korrekt der beförderte Layer, nicht der ursprüngliche)
GET asset download, neuer Prozess          -> 200 md5 identisch mit Original (NEUSTART ÜBERLEBT)
```

### A.3 Transkript der Divergenz-Reproduktion (Teil IV.5, wörtlich)

```
Map A (older) id=1, Map B (newer) id=2
Step 1: DM explicitly activated Map B via legacy /maps/activate -> Map B (newer, boss arena)
Step 2: /play bootstrap BEFORE init -> state_payload.active_map = 'Map B (newer, boss arena)'
        (id=2), scene_stack = None
Step 3: DM clicked 'Kartenstapel initialisieren'
Step 4: active map AFTER init_scene_stack -> 'Map A (older, tavern)' (id=1)

=== DIVERGENCE CONFIRMED ===
DM explicitly chose Map B (id=2) via Session-Prep.
After clicking 'Kartenstapel initialisieren', active map silently changed to
id=1 ('Map A (older, tavern)') -- the OLDEST campaign map, not the one the DM had
chosen. No error, no warning, no confirmation dialog.
```

Aufbau: zweite, separate isolierte Instanz unter `127.0.0.1:5098` (eigene SQLite-Datei, eigenes
Storage-Verzeichnis, unabhängig vom Testlauf in Anhang A.2), zwei Kampagnenkarten mit erzwungenem
Sekundenabstand in `created_at`, um Reihenfolge-Ambiguität auszuschließen. Die vollständige Assertion-Kette im
Testskript (`campaign_map.id`-Vergleiche vor/nach `init_scene_stack`) bestätigt, dass der Wechsel exakt auf
die älteste Karte erfolgt, nicht zufällig oder auf eine dritte Karte.

### A.4 Evidenz-Index

- Vollständiger Pytest-Lauf: `pytest tests/ -q` aus dem Repository-Root, aktueller Working Tree, frische
SQLite-Datenbank, 2026-07-30, selbst durchgeführt für diese Edition (nicht aus dem Zwischenstand übernommen).
- Test-Collection-Reproduktion: `pytest --collect-only` ohne Pfadeinschränkung, `PermissionError` auf
`ops/certbot/conf/accounts` live reproduziert.
- Diff-spezifischer Testlauf: `pytest tests/test_scene_stack_api.py tests/test_book_shell_ux_stabilization.py
-q` → 18 passed.
- Praktischer Funktionstest (Erfolgsfall): isolierte Flask-/SocketIO-Instanz auf `127.0.0.1:5099`, eigene
SQLite-Datenbankdatei, eigenes lokales Asset-Storage-Verzeichnis, vollständig über `requests` per echtem HTTP
angesteuert (echtes Cookie-JWT, echter CSRF-Header aus dem `csrf_access_token`-Cookie), inklusive eines
vollständigen Prozess-Kill-und-Neustart-Zyklus, gezielt auf die uncommitteten Scene-Stack-Layer-Endpunkte
gerichtet.
- Praktischer Funktionstest (Divergenz-Reproduktion): zweite, unabhängige isolierte Instanz auf
`127.0.0.1:5098`, eigene Datenbank- und Storage-Dateien, exakt das in Teil III.3 aus dem Code hergeleitete
Szenario nachgestellt (`maps/activate` gefolgt von `scene-stack/init` auf derselben Session, zwei
Kampagnenkarten mit eindeutiger `created_at`-Reihenfolge).
- Produktions-Datenbank-Abfrage (read-only, keine Schreiboperation): `docker exec roll-drauf-vtt-db-1 psql -U
vtt -d vtt -c "SELECT platform_role, count(*) FROM users GROUP BY platform_role;"` und separate
Zeilenzahl-Abfragen für `session_map_layers`/`session_tokens`.
- Infrastruktur-Check: `docker ps -a`, `docker images`, `docker inspect` (Image- und
Container-Erstellungszeitpunkte), Host- und Container-nginx-Konfiguration (`/etc/nginx/conf.d/vtt.conf`,
`ops/nginx/vtt.roll-drauf.de.conf`), Verzeichnislistings von `/opt/vtt` und `/home/RollDrauf_PROD/VTT`,
Migrationsverzeichnis-Listing (`migrations/*.sql`).
- Dokumentations-Korpus: `find docs dadm -type f` (präzise Zählung: 167 / 402 / 569), `find docs dadm -newermt
"2026-07-28" -type f` (Änderungsprüfung seit Erstausgabe: keine Treffer außer den Gap-Analyse-Dateien selbst),
gezielte Re-Verifikation jedes der acht Widersprüche aus der Erstausgabe per Grep gegen den aktuellen Stand,
vollständige (nicht exemplarische) Zählung der `vtt_app`-Referenzen (`grep -rl "vtt_app" docs/*.md | wc -l` →
41).
- Code-Lesung für den Teil-III.3-Neubefund: `vtt/campaigns/routes.py` (Zeilen 953–994,
`activate_session_map`), `vtt/templates/campaigns.html` (Zeilen 2374–2394, `activatePrepSessionMap`),
`vtt/static/js/play-ui.js` (Zeilen 874–899 `_renderLayers`, Zeilen 1039ff. `_renderState`),
`vtt/play/service.py` (Zeilen 254–296, `init_scene_stack`).
- Kapazitätsbezogener Rundgang (§II.4): `find tests -name "*.py"` (51 Dateien), `grep -c "def test_"
tests/*.py` (Tests pro Datei), Stichprobenlesung der zugehörigen Routen-Module je Funktionsbereich.
- Git-Historie: `git log --oneline -25`, `git status --porcelain`, `git diff --stat`, `git log -1 --format="%H
%ai"` für `3e7dbe6` und `0a39990`, `git show 3e7dbe6 --stat`.

---

## Anhang B — Änderungsprotokoll gegenüber der Erstausgabe (2026-07-28)

Zur Nachvollziehbarkeit für zukünftige Editionen, was sich zwischen den beiden Ausgaben tatsächlich bewegt
hat:

| Bereich | 2026-07-28 (Erstausgabe) | 2026-07-30 (diese Edition) |
|---|---|---|
| Workspace-HEAD | `0a39990` | `3e7dbe6` (ein neuer Commit: der Zugriffskontroll-Fix) |
| Uncommitteter Diff | identisch (M5/M7, 17 Dateien) | identisch, unverändert seit zwei Tagen weiterhin uncommittet |
| Zugriffskontroll-Bug | am Tag der Erstausgabe selbst gefunden und behoben (`3e7dbe6`) | Fix bestätigt im Code, aber **nicht deployt**; alle 4 Produktionskonten weiterhin mit dem verwundbaren Default (neuer, konkreter Beleg via DB-Abfrage) |
| Testsuite | 409→411 bestanden (vor/nach Fix), 5→3 fehlgeschlagen | 411 bestanden, 3 fehlgeschlagen — identisch, unabhängig re-verifiziert |
| Dokumentations-Korpus | "~180" / "150+" Dateien (Schätzung) | 167 (`docs/`) / 569 (`docs/`+`dadm/`) (präzise Zählung); Korpus selbst zu 100 % unverändert seit Erstausgabe |
| Docker-Deployment | Image vom 23.07., 4 Tage alt zum Prüfzeitpunkt | Image identisch (23.07.), jetzt 7 Tage alt, unverändert nicht neu gebaut |
| Neuer inhaltlicher Befund | — | Scene-Stack/`maps/activate`-Divergenz (Teil III.3) — durch capability-by-capability-Codelesung gefunden UND live reproduziert (Teil IV.5), in keiner vorherigen Ausgabe erwähnt |
| Praktischer Funktionstest | Alter M42-Direktaktivierungspfad, Ende-zu-Ende mit Neustart | Neuer Scene-Stack-Layer-Pfad (Init, Duplikat-Schutz, zweiter Layer, Löschen mit Beförderung), Ende-zu-Ende mit Neustart, PLUS eine zweite, gezielte Reproduktion der Divergenz aus Teil III.3 |
| Kapazitätsabdeckung | Fokus auf Map-Upload/Persistenz-Pfad | Zusätzlicher Rundgang durch alle neun größeren Funktionsbereiche der Anwendung (Teil II.4), um zu bestätigen, dass die drei Testfehlschläge isoliert bleiben und keine Blindstelle in der Abdeckung existiert |
| Produktions-Nutzerdaten | nicht abgefragt | Direkte, read-only Abfrage von `platform_role`-Verteilung und Zeilenzahlen der toten Tabellen — bestätigt, dass alle vier Bestandskonten heute den verwundbaren Default tragen |
| Docker-Image-Bestand | nur das laufende `roll-drauf-vtt-app:latest` betrachtet | Zusätzlich zwei weitere, nicht mehr referenzierte VTT-Images auf dem Host identifiziert (`roll-drauf-vtt:m3-latest`, `vtt-prod-app:latest`) |
| Migrationsverzeichnis | nicht im Detail aufgeführt | Vollständig aufgelistet (11 Dateien), Zusammenhang mit den in Teil I.2 dokumentierten konkurrierenden M-Zählschemata hergestellt |
| Abschließende Bewertung | Implizit über Executive Summary und Prioritätenliste | Explizite Teil VII "Fazit"-Sektion mit direkter Ja/Nein-Beantwortung entlang fünf konkreter Dimensionen |

---

## Anhang C — Schnellreferenz für die nächste Person, die diesen Strang übernimmt

Zusammengetragen aus allen Teilen dieses Berichts, damit die wichtigsten Pfade und Befehle nicht erneut aus
dem Fließtext herausgesucht werden müssen.

**Wo der uncommittete M5/M7-Diff liegt** (Teil III): `git status --porcelain` im Repository-Root zeigt ihn
vollständig; zentrale neue Dateien/Funktionen sind `vtt/play/service.py` (Business-Logik, §III.1a) und
`vtt/play/routes.py` (REST-Fläche). Die entfernten Altlasten sind `vtt/models/session_map_layer.py`,
`vtt/models/session_token.py`, `vtt/socket_handlers_sessions.py`.

**Wo die in Teil III.3/IV.5 gefundene Divergenz behoben werden müsste:**
`vtt/play/service.py::init_scene_stack()` (Zeilen 254–296, insbesondere die
`maps.order_by(CampaignMap.created_at.asc())`-Zeile) und/oder
`vtt/templates/campaigns.html::activatePrepSessionMap()` (Zeile ~2374).

**Wie die Produktions-Datenbank read-only befragt wird** (Teil V.2, ohne Schreibrisiko): `docker exec
roll-drauf-vtt-db-1 psql -U vtt -d vtt -c "<SELECT-Statement>"`. Zugangsdaten sind über die laufenden
Container bereits kontextualisiert, kein separates Passwort nötig.

**Wie eine isolierte Testinstanz aufgesetzt wird** (Teil IV, IV.5), für zukünftige Ad-hoc-Verifikationen,
solange keine echte Staging-Umgebung existiert: `app.py` mit überschriebenen Umgebungsvariablen starten
(`DATABASE_URL=sqlite:///<eigene-Datei>`, `PORT=<freier Port>`, `STORAGE_PROVIDER=local` mit eigenem
`LOCAL_STORAGE_PATH`, `RATELIMIT_STORAGE_URL=memory://`, `REDIS_URL=` leer). Registrierungsschlüssel lassen
sich über dieselbe interne Funktion (`vtt.endpoints.registration_keys.create_registration_keys`) minten, die
auch `app.py`s `bootstrap-admin`-CLI-Befehl nutzt — dafür wird ein `performed_by`-Nutzerobjekt für die
Audit-Log-Pflicht benötigt (`vtt/utils/audit.py::log_audit` wirft sonst `RuntimeError`).

**Wie die volle Testsuite korrekt aufgerufen wird** (Teil II.1), um den vier Monate alten Collection-Bug zu
vermeiden: `./venv/bin/python -m pytest tests/ -q` — **niemals** ohne den `tests/`-Pfadzusatz, sonst
`PermissionError` auf `ops/certbot/conf/accounts`.

**Wo die Dokumentations-Wahrheit tatsächlich am ehesten stimmt** (Teil I): `AGENTS.md` hat als einziges
Dokument sowohl den korrekten Paketnamen (`vtt`) als auch den korrekten Bootstrap-Pfad
(`dadm/framework/runtime/AI_BIOS.md`). Bei Widersprüchen zwischen `docs/`-Dateien und `AGENTS.md` ist
`AGENTS.md` die verlässlichere Quelle, bis das in Teil VI/P1 empfohlene verbindliche Status-Dokument
existiert.

**Wo dieser Bericht selbst archiviert liegt:**
`/home/admin/projects/roll-drauf-vtt/docs/vtt_gap_analysis_2026_07_30.md` (diese Datei). Die vorherige Edition
liegt als PDF unter einem separaten Reports-Verzeichnis außerhalb dieses Repositories (siehe
RollDrauf-Bot-Betriebs-Gedächtnis, Eintrag "Report suite refresh"); ihre Markdown-Quelle war zum Zeitpunkt
dieser Edition bereits nicht mehr auffindbar, weshalb eine Rekonstruktion aus dem PDF-Text als Vorlage diente.
