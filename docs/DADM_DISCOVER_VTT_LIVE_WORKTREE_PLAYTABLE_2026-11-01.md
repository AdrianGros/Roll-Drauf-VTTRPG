# VTT: Live-Stand, Arbeitsbäume und Playtable

Datum: 2026-11-01. Phase: **Discover abgeschlossen**. Profil: `standard`.
Ausgangs-HEAD: `436c3cda107566edd3887a2f7a0b200aaba569cd` auf
`feat/creation-engine-g1`. Alle Bestandszahlen beziehen sich auf den Zustand
**vor** den Dokumentationsänderungen dieses Audits.

## Auftrag und Grenze

Zuerst feststellen, welche Arbeit uncommittet, unveröffentlicht oder überholt
ist; den tatsächlichen Playtable gegen die gewünschte DM-/Spielertrennung und
persönliche Charakter-Aktionsleiste prüfen; vorhandene Projektplanung einordnen.
Zusätzlich die vom Owner beschlossene Live-Abschlussregel in `AGENTS.md` verankern.

Die Klarstellung des Owners gilt: **Bewusste Ablösungen sind gewollt.** Der
neuere beschlossene Produktstand zählt; bestehender Live-Code ist nicht allein
aufgrund seiner Existenz zu erhalten. Unterschiede werden deshalb nach
Entscheidungsstand und Funktion bewertet, nicht pauschal als Regression.

Kein Anwendungscode, keine Nutzerdaten und kein Live-Deployment wurden durch
diesen Audit geändert. Es wurden keine Worktrees gelöscht, Änderungen verworfen
oder fremde Änderungen committed. Die Änderung der Repo-Regel ist ausdrücklich
beauftragt und keine verdeckte Playtable-Implementierung.

## Ergebnis

Es gibt sowohl unveröffentlichte Arbeit als auch bereits ausgelieferte, noch
uncommittete Arbeit. Der größere Befund ist die fehlende Zusammenführung:

- Sechs registrierte Worktrees enthalten zusammen **113 geänderte/staged
  Dateien und 643 untracked Dateien**; der Haupt-Checkout allein 38 und 614.
- Live läuft ein Image mit Eagle Homebrew, Species-/Bogen-Erweiterungen,
  Kartenwerkstatt, Hauptnavigation und Forschungsumfrage. Kein einzelner
  untersuchter Worktree entspricht diesem gesamten Stand.
- **81 von 86 Anwendungsdateien, die nur im Haupt-Checkout liegen, gehören zur
  ausdrücklich archivierten G1-Engine.** Sie sind keine 81 ausstehenden Features.
  Die übrigen fünf sind der Sitzungskalender.
- Die DM-/Spieler-Rollenprüfung existiert. Ein wählbarer Einstieg des DM als
  Spieler fehlt. Sichtbare DM-Werkzeuge lassen sich zusätzlich als CSS-Fehler
  reproduzieren.
- Die existierende Hotbar ist ein bewusst reduzierter erster Schritt mit drei
  festen Aktionen. Belegbare Charakter-Makros wurden dabei ausdrücklich vertagt.

## Wie der Live-Stand bestimmt wurde

Die laufende Anwendung ist `roll-drauf-vtt-app-1`, Image
`roll-drauf-vtt-app:research-survey-20261029`, Image-ID
`sha256:0febdcf788a3662a484e2a16429c82b588e4dc0d509b3a8d186849a00be20dd6`.
Containerstart: 2026-10-29, 12:07:12 UTC. Es gibt **keinen Source-Bind-Mount**;
Änderungen im Arbeitsbaum erscheinen folglich nicht automatisch live.

Die Containerlabels nennen Compose-Projekt `migration-production` und
Arbeitsverzeichnis `/srv/migration/2026-10-07/setup`. Genannt werden
`production.compose.json`, `production.duck-species.override.yml` und das
Umfrage-Override unter `/tmp/research-survey-deploy-20261029/override.yml`.
Der App-Port wird auf `127.0.0.1:15000` veröffentlicht. Das unterscheidet sich
vom älteren Repo-Runbook mit Projekt `roll-drauf-vtt`.

SHA-256-Vergleich der ausgewählten Code-/Asset-Verzeichnisse `vtt`, `tests`,
`migrations`, `tools` sowie ausgewählter Root-Konfigurationen gegen `/app`:

| Vergleich | Dateien |
| --- | ---: |
| Identisch | 512 |
| Unterschiedlicher Inhalt | 38 |
| Nur im Haupt-Checkout | 133 |
| Nur im Container | 23 |

Dies ist ein Dateivergleich, keine Featurezählung. Fehlende Tests oder
Migrationsdateien im Image beweisen nicht, dass ihre Funktionen oder Tabellen
fehlen. Insbesondere existieren live bereits `research_survey_responses`,
`session_series`, `session_occurrences`, `ce_eagle_documents` und
`ce_species_revisions` — durch reine Schemaabfrage geprüft.

Öffentliches HTTPS liefert 200 für `/health/live`, `/dashboard`, `/play` und
`/research-survey`. Die ausgelieferten Dateien `play-ui.js`, `vtt-main-nav.js`
und `eagle-homebrew/build.json` stimmen mit dem Container überein.
`/static/js/session-calendar.js` liefert 404. Ein 200 auf einer HTML-Hülle ist
noch kein Nachweis einer erfolgreichen angemeldeten Nutzerreise.

Der Remote-Abgleich mittels `git ls-remote origin` scheitert an
`Permission denied (publickey)`. Die lokale Anzeige „ahead 1“ für den aktiven
Branch und „ahead 6“ für `main` beruht daher auf gespeicherten Remote-Refs;
der aktuelle GitHub-Stand ist **nicht bestätigt**.

## Vollständige Worktree-Inventur

Alle 756 betroffenen Dateien stehen mit Status, Pfad, Größe, Hash und
Live-Abgleich in [worktree-inventory.csv](proofs/vtt-live-audit-2026-11-01/worktree-inventory.csv).
`outside_live_scan` bedeutet nicht „nicht deployed“, sondern „außerhalb der
untersuchten Image-Verzeichnisse“. Der CSV-Vergleich zum Haupt-Checkout ist
ebenfalls der eingefrorene Zustand vor diesem Audit.

| Worktree / Branch | Änderungen | Einordnung |
| --- | --- | --- |
| `roll-drauf-vtt` / `feat/creation-engine-g1` | 38 tracked; 614 untracked; HEAD `436c3cd` | Gemischt: bereits live, echter Kalender-/Performance-Rest und überholtes G1. Kein fertiger Release-Gesamtstand. |
| `roll-drauf-vtt-eagle` / `feat/eagle-homebrew` | sauber; HEAD `6d79274`; 13 nur hier vorhandene Commits gegenüber Haupt-HEAD | Beschlossener CE-Nachfolger, Species, Sheet-to-table und mobile Bogenverbesserungen; weitgehend live. Kartenwerkstatt/Nav/Umfrage fehlen teilweise in diesem Baum. |
| `roll-drauf-vtt-p13` / `feat/srd-creator-p13` | 8 tracked; 10 untracked | Homebrew-Typen und Paketverwaltung auf G1/Advanced Studio. Durch die Eagle-Ablösung technisch überholt; fachliche Paketanforderungen gesondert abgleichen. |
| `roll-drauf-vtt-dadm-audit` / `feat/dadm-audit-framework` | 49 staged; ca. +4.880/−55 Zeilen | Eigenständige Auditwerkzeuge, Runtime-Karten und Knowledgebase; kein fehlendes Playtable-Feature. Separates Review/Commit, kein App-Rollout nötig. |
| `roll-drauf-vtt-claude-research` / `claude/playtable-research` | 14 untracked Forschungsdateien; Basis 75 Commits hinter Haupt-HEAD | 13 Dateien byteidentisch zum Hauptbaum; das Arbeitspaket dort enthält den älteren Stand ohne spätere Ergänzungen. Historische Recherchekopie, kein Code-Release. |
| `vtt-fixes` / `fix/balu-vtt-navigation-20260930` | 18 tracked; 5 untracked; Basis 27 Commits hinter Haupt-HEAD | Größtenteils übernommene Navigations-/Mitgliedschaftsarbeit. Für 10/18 tracked Patches besteht bereits ein vollständiger Reverse-Patch-Abgleich im Hauptbaum. Rest nur nach Hunk-/Testvergleich schließen, nicht pauschal löschen. |

Die 614 untracked Dateien im Hauptbaum umfassen **577 Proof-/Research-Artefakte**
und nur 37 andere Dateien. Gesamtgröße etwa 303,7 MiB. Die großen Blöcke sind
Mapmaker-DAO (249 Dateien), World-Atlas-Recherche (266) und weitere Mapmaker-/
Turtonia-Nachweise. Das sind überwiegend Bilder, Exporte und Hilfsskripte,
nicht Hunderte ausstehende Produktfunktionen. Keine automatische Löschung.

### Was konkret im Hauptbaum liegt

| Arbeit | Nachweis / Inhalt | Live- und Abschlussstatus |
| --- | --- | --- |
| Kartenwerkstatt und gemeinsame Hauptnavigation | Commit `436c3cd`, `vtt/static/mapmaker/`, `vtt-main-nav.*`, Template-Einbindungen, Navigationstests | Editor, Navigation und mehrere uncommittete Template-Einbindungen sind live. Release-/Git-Konsolidierung statt erneuter Funktionseinführung. |
| Forschungsumfrage | Neue API, Modell, Template, M82-SQL, 4 Tests, zwei Phasenberichte und Forschungsdokumente | Drei neue Anwendungsdateien byteidentisch live, Tabelle vorhanden. SQL-Datei nur staged; Integration noch uncommittet. Seite derzeit Direktlink, kein Eintrag im gemeinsamen Hauptmenü. |
| Sitzungskalender | `calendar_routes.py`, `session_calendar.py`, `session_series.py`, JS/CSS, Migrationstool, drei Testdateien; Änderungen an BookScene, Kampagnen und Dashboard | Tabellen live bereits vorhanden; Code und Browser-Asset fehlen live. Echter noch nicht abgeschlossener Rollout. |
| Token-Renderoptimierung | Änderung an `play-ui.js`, neuer `test_token_render_batching.py` | Noch nicht live; bündelt Token-Events pro Animationsframe und schützt den aktiven Drag. Vier Chromium-Fälle bestehen. |
| Discord-Login-/Zugangskorrektur | `vtt/auth/routes.py` und 76 zusätzliche Testzeilen | Anwendungsdatei byteidentisch live und auch im Eagle-Verlauf enthalten. Uncommittet im Hauptbaum bedeutet hier nicht unveröffentlicht. |
| Zusätzlicher Dashboard-Rückkehrtest | `tests/test_login_invite_return.py` | Ein weiterer Test im Hauptbaum; kein eigener ausstehender App-Rollout. |
| „D&D“ → „5E“-Textänderungen | README, Modelldocstrings, Portable-Fehlertexte, alter CE-Editor und Tests | Gemischte kleine Textarbeit, teilweise auf überholten G1-Flächen. Nur noch geltende Oberflächen/Text-Hunks übernehmen. Kein Grund, G1 wiederherzustellen. |
| Backup-Skript | `.partial`-Bereinigung auf Tages-/Monatsordner eingegrenzt | Ein-Zeilen-Änderung; Ausführungspfad/aktiver Hoststand hier nicht geprüft. Separater Betriebsrest. |
| `infra/docker/7dtd/` | 10 neue Dateien | Separates Gameserver-/Infra-Paket; kein VTT-Playtable-Release. |
| Forschungsagenda und DAD-M-Pilot | 11 weitere Dateien unter `docs/research/` | Forschung/Protokolle, keine ausstehenden VTT-UI-Funktionen. |

Von den insgesamt 36 dirty/untracked `vtt/`-Dateien sind 9 byteidentisch live,
16 verschieden und 11 im Live-Anwendungsverzeichnis nicht vorhanden. Letztere
sind sechs überholte G1-Dateien plus die fünf Kalenderdateien.

## Überholt, bewusst ersetzt oder noch relevant?

Die verbindliche Ablösung ist im Eagle-Worktree dokumentiert:
`docs/DADM_DEPLOY_CREATION_ENGINE_EAGLE_HOMEBREW_2026-10-19.md` nennt ausdrücklich
„sofort“ Eagle unter `/api/ce/authoring` und das Ende von Advanced Studio/Sandbox.
`archive/creation-engine-g1/README.md` führt die archivierten Pfade auf.
Diese Entscheidung wird durch die aktuelle Owner-Klarstellung gestützt.

Folgerungen:

- G1-Runtime, alter Interview-Editor und P13 auf Advanced Studio nicht als
  fertige, auszuliefernde Features verbuchen. Anforderungen daraus können weiter
  gelten; ihre alte technische Umsetzung ist nicht automatisch der Zielstand.
- Eagle ist kein versehentlicher Verlust von G1, sondern dessen gewollter Ersatz.
- Mapmaker/Hauptnavigation und Umfrage ergänzen diesen Nachfolger. Dass sie in
  einem anderen Baum liegen, macht sie nicht überholt.
- Der Live-/Worktree-Diff von `play-ui.js` zeigt einen konkreten unbeabsichtigten
  Rückschritt **bei unverändertem Kopieren der alten Gesamtdatei**: `_sheetUrl`
  mit `session_id`, neue Bogen-Tab-Links und benannte Sheet-Würfe würden entfernt.
  Es wurde keine Ablösungsentscheidung für diese Funktionen gefunden. Die
  Token-Optimierung ist dagegen ein eigener, klar abgrenzbarer neuer Patch.
- `docs/deploy-vtt-guide.md` und `infra/scripts/deploy_live.sh` sind als aktuelle
  Betriebsanleitung unzureichend: Projekt/Pfade passen nicht zum laufenden
  Migrationsstack. Die alten Anweisungen nicht ungeprüft ausführen.

## Playtable: gewünschte Trennung und tatsächliche Umsetzung

### DM kann noch nicht als Spieler eintreten

`vtt/play/service.py:99` liefert für den Kampagnen-Owner immer `DM`, sonst die
aktive Mitgliedsrolle. `vtt/play/routes.py:142` verwendet diese Rolle für den
Bootstrap. Die relevanten Dateien sind byteidentisch live. In den untersuchten
Einstiegen, HTTP-Verträgen und Socket-/Playtable-Dateien wurde keine zweite,
wählbare Spielerperspektive für DM/Co-DM gefunden.

Damit existieren Rollen und gefilterte Daten für tatsächliche Spieler, aber
noch nicht die gewünschte Auswahl „als Spielleitung / als Spieler“ für dieselbe
berechtigte Person. Ein bloßes Umschalten der Buttons wäre dafür unzureichend:
Bootstrap, erneutes Laden, API-Schreibrechte, private Ereignisse, Fog, eigene
Tokens/Charaktere und Socket-Neuverbindung müssen dieselbe Perspektive verwenden.
Wie diese Auswahl gespeichert und zwischen Tabs abgegrenzt wird, gehört in Apply.

### Warum Spieler DM-Werkzeuge sehen

Der Client setzt `toolWall.hidden`, `toolLight.hidden` und
`btnVisionToggle.hidden` nach der Operatorrolle (`play-ui.js`, live etwa
Zeilen 4053–4065). Das Template hat allerdings Display-Regeln für `.tool-btn`
und `.tabletop-shell > .left-toolbar .tool-btn` ohne ausreichende Hidden-Regel.

**Reproduktion mit öffentlich ausgeliefertem HTML/CSS:** Bei 1440 und 390 Pixeln
werden alle drei Buttons trotz `hidden=true` mit `display:flex` und positiver
Breite/Höhe gerendert. Das ist ein belegter Darstellungsfehler. Zusätzlich
deaktiviert `_syncControlState()` einige Session-Bedienelemente nur, statt sie
für Spieler aus der Oberfläche zu entfernen.

Die Reproduktion ist ein isolierter Browsernachweis mit Live-Markup/-Styles und
Spieler-Hidden-Flags, **keine angemeldete Live-Spielerreise**. Ein Rechteleck
allein aus sichtbaren Buttons wird nicht behauptet. Die 24 bestehenden
Rollen-/Vision-Tests bestehen gegen den Eagle-Baum; dessen sieben geprüfte
Playtable-/Socket-Dateien stimmen per Hash mit Live überein. Das belegt die
abgedeckten Backend-Grenzen, nicht eine noch nicht vorhandene DM-Spielerumschaltung.

### Hotbar und Charakter-Makros

`vtt/play/actions.py` enthält nur `attack_basic`, `dash_move`, `interact_object`.
`_renderActionHotbar()` erzeugt genau diese drei Slots. Keine persönliche
Slotbelegung, keine gespeicherten Makros, keine Zuordnung von Charakteraktionen.
`_fireHotbarSlot()` übergibt `target_token_id=null`; `attack_basic` verlangt ein
Ziel. Der Angriffsslot kann diesen Vertrag daher nicht selbst erfüllen.

Das Arbeitspaket vom 27.08. markiert S07 als DONE, schränkt den Umfang aber
ausdrücklich auf diese feste Auswahl ein: keine individuellen Aktionen, keine
Persistenz, kein Drag-and-drop, keine Seiten, kein Target-Picker. Die Forschung
beschreibt den größeren Wunsch, ihre Umsetzung wurde damit noch nicht zugesagt
oder fertiggestellt. Für die jetzt gewünschte MMO-Leiste ist echte neue Arbeit
nötig, nicht nur ein vergessener Commit.

## Was nach einem kurzen Audit live gehen sollte

Dies sind priorisierte **Kandidaten und Übergaben**, keine pauschale Freigabe
aller vorgefundenen Dateien. Aufwand ist relativ, keine Zeitzusage.

| Reihenfolge | Kandidat | Aufwand / Abhängigkeit | Konkrete Abnahme vor Abschluss |
| --- | --- | --- | --- |
| 1 | Sichtbarkeit der DM-Werkzeuge korrigieren | Klein, klarer Playtable-Fehler; auf aktuellem Zielstand | Echte Spieler-/DM-Ansichten desktop/mobil prüfen: Spieler sehen keine DM-Actions; DM behält erreichbare Werkzeuge. API-Sperren bleiben wirksam. |
| 2 | Vorhandene Token-Renderoptimierung übernehmen | Klein bis mittel; einzelne Hunks mit aktuellem Sheet-to-table-Code zusammenführen | Vier vorhandene Browserfälle plus Live-Bewegung/Drag und Bogenwürfe am richtigen Tisch. Kein komplettes Ersetzen der alten Datei. |
| 3 | Sitzungskalender abschließen | Mittel; UI, API, vorhandenes Schema und Cancel-Semantik zusammen | Aktuelles Schema gegen Models prüfen; Kalender über Kampagnen-Hub erreichbar; Wiederholung, Zeitzonen, Absage und Rollen desktop/mobil; gezielte PostgreSQL-Konkurrenzprüfung. |
| Separat | Bereits live befindliche Navigation/Umfrage/Auth in Git zusammenführen | Release-Hygiene; keine neue Funktion erfinden | Nachvollziehbarer Commit-/Image-Bezug. Umfrage bei weiter geltendem Produktbedarf über UI erreichbar machen. |
| Nächster Playtable-Kernauftrag | DM-Einstieg als Spieler | Mittel bis größer; Apply-Vertrag für Rolle/Perspektive nötig | Gleiche Person kann beide Ansichten wählen; tatsächlicher Spielerumfang bei Daten und Aktionen, einschließlich Reload/Reconnect. |
| Danach | Persönliche Charakter-/Makroleiste | Größer; Aktionstypen, Besitz, Slotpersistenz und Zielauswahl klären | Belegen, speichern, wiederladen und ausführen über UI; Würfel-/Aktionsresultat am richtigen Tisch; keine DM-Werkzeuge in der Spielerleiste. |

Der fachliche Schwerpunkt bleibt die Rollenwahl und Spielerleiste. Kalender,
Forschungsumfrage, Framework und Gameserver sind keine Voraussetzungen dafür.
Kein neues Frameworkprojekt muss vor dem kleinen Sichtbarkeitsfix fertig werden.

## Planung: vorhanden, aber nicht in einem verlässlichen Gesamtstatus

| Planungsstrang | Was vorliegt | Aktuelle Aussagekraft |
| --- | --- | --- |
| Buch-/Workspace-Design, März/April | Discover/Soll/Apply/Deploy/Monitor für Einstieg, Navigation und Play-Workspace | Bestehende Designgeschichte; Änderungen seitdem müssen berücksichtigt werden. |
| Masterplan 1–100, August | Breite Roadmap einschließlich Release Engineering und Stabilisierung | Historischer Problemkatalog. Alte Reifeprozente und Staging-Pflichten sind keine aktuelle Messung oder heutige Owner-Vorgabe. |
| Playtable S01–S11, August | Elf Recherchen, später Apply-Entscheidungen, Deploy-/Qualitätsnotizen | Viele Funktionen vorhanden. Kopfstatus „research-first“ und spätere DONE-Abschnitte widersprechen sich; DONE bezeichnet den begrenzten damaligen Umfang. |
| Roll20-Parität, September | Folgeschritte u. a. Fog und UX | Ergänzt ältere Grenzen; ist kein Beweis für persönliche Makros oder eine DM-Spieleransicht. |
| Creator P1–P13, Oktober | P1–P12 umgesetzt/dokumentiert, P13 im separaten Arbeitsbaum | P13 basiert auf dem inzwischen ersetzten G1-System. |
| Eagle und Creator-Programm C0–C11, Oktober | Neuer CE-Stand, genehmigtes Paritätsprogramm, C0-Nachweisregister | Nur im Eagle-Baum vollständig auffindbar. C0 ist abgeschlossen; Register: 43 partial, 5 open, 0 accepted. Das ist ein konservativer Abnahmestand, kein Beleg, dass 43 Funktionen fehlen. |
| Regelwerk R0–R7 | Genehmigtes Programm mit abgeschlossenem Publikationsstand | Eigenständiger, konkreter Fortschritt; lesbares Regelwerk ist nicht automatisch ausführbare Charaktermechanik. |
| Navigation/Kartenwerkstatt, 26.10. | Gemeinsame Navigationsleiste und Rolloutprotokoll | Live vorhanden. „Es fehlt jede Navigation“ wäre falsch. |

**Warum es nach Limbo aussieht — aus den Befunden abgeleitet:**

1. Produktziel, begrenzter Teilschritt und Gesamt-Abnahme werden unter denselben
   Begriffen geführt: S07 DONE klingt nach fertiger Makroleiste, meint aber drei
   feste Buttons. Eine archivierte Engine bleibt im anderen Hauptbaum aktiv.
2. Deployments wurden als gezielte Ergänzungen auf bestehende Images gesetzt,
   ohne den zusammengeführten Quellstand anschließend vollständig festzuhalten.
   Git-Status beantwortet deshalb weder „live?“ noch „noch gebraucht?“.
3. Planungs- und Statuswissen liegt verteilt auf mehrere Branches und sich
   überlagernde Nummernsysteme. Das neuere C0-Register ist im aktuellen Checkout
   nicht sichtbar, während dort alte G1-Arbeit wie aktive Entwicklung aussieht.
4. UI-Erreichbarkeit und rollenbezogene Gesamtreise sind kein durchgängiger
   Abschlussnachweis. Hidden-Attribute im Code und erfolgreiche APIs erkennen
   beispielsweise den sichtbaren Button-Fehler nicht.

### Welche Planung jetzt fehlt

Apply braucht einen kleinen, verbindlichen Playtable-Auftrag statt einer neuen
100-Punkte-Roadmap: gewünschte DM-/Spielerreisen, Rollen-/Perspektivvertrag,
Aktionen/Slotbesitz, Fehlerfälle, konkrete Abnahme und einen Release-Nachweis.
Ein gemeinsames Lieferregister sollte pro Fähigkeit den neuesten Beschluss,
Commit, Image, UI-Einstieg, Rollenprüfung, Live-Nachweis und nächsten offenen
Schritt verbinden. Historische Pläne sollten als ersetzt/veraltet gekennzeichnet
werden, sobald diese Zuordnung geprüft ist.

Die bestehende Hauptleiste bietet Übersicht, Kampagnen, Charaktere, Karten,
Creation Engine, Regelwerk, Compendium und Spieltisch. Am Tisch kommen Tool-Dock,
Hotbar, Seiten-/Tokenflächen, Sidebar und Sitzungsmenü hinzu. Zu klären ist die
**Hierarchie und Zuständigkeit dieser vorhandenen Flächen**, insbesondere
globaler Einstieg → Kampagne → Sitzung → gewählte Tischrolle → passende
Werkzeuge/Charakteraktionen. Die konkrete neue Navigation wird hier nicht
vorweggenommen; sie gehört zum Apply-Vertrag und soll das erarbeitete Buch-UI
weiterführen.

## Risiken, Annahmen und offene Punkte

| Schwere | Befund | Behandlung / offene Grenze |
| --- | --- | --- |
| Hoch, Release | Hauptbaum und Live-Image repräsentieren verschiedene Generationen plus Einzelergänzungen. | Vor einem vollständigen Build den beschlossenen Gesamtstand konsolidieren. Kleine, exakt abgegrenzte Fixes benötigen keine Wiederbelebung alter Features. |
| Hoch, Produkt | DM-Spielerwahl fehlt; feste Hotbar wird mit dem größeren Makroziel verwechselt. | Zwei explizite Abnahmepakete für Rollenwahl und Charakterleiste; kein DONE aus alten Teilstatus ableiten. |
| Mittel, UI | Hidden-DM-Buttons werden sichtbar gerendert; Teile der Session-UI sind nur disabled. | Kleiner erster Fix mit tatsächlicher Sichtbarkeitsprüfung. |
| Mittel, Integration | Kalendercode fehlt live trotz vorhandener Tabellen. | Tabellenstruktur/Migration und aktuelles Eagle-Wiring vor Rollout prüfen. M82 bezeichnet außerdem unterschiedliche Arbeiten in mehreren Bäumen. |
| Mittel, Nachweis | Kein authentifizierter Live-Zweirollenlauf in diesem Audit. | Für die nächste Auslieferung eine klar benannte eigene Abnahmekampagne mit DM-/Spielerzugängen verwenden; keine fremden Kampagnendaten verändern. |
| Mittel, Sicherung | Remote-Zugriff scheitert; tatsächlicher Push-Stand unbekannt. | SSH-/Repo-Zugang wiederherstellen; lokale Commits und Live-Deploy getrennt ausweisen. |
| Niedrig, Bestand | Hunderte untracked Proofs und teilweise bereits übernommene Alt-Patches. | Aufbewahrung/Archivierung gezielt entscheiden; nicht als Feature-Backlog zählen oder ungeprüft löschen. |

Annahme für den nächsten Auftrag: „als Spieler“ meint eine echte eingeschränkte
Spielteilnahme mit eigenen Charakteraktionen. Ob zusätzlich eine rein lesende
Spielersicht Vorschau gewünscht ist, kann Apply ergänzen; sie ersetzt diese
Anforderung nicht. Für eine belastbare Zeitplanung fehlen noch der genaue
Makroumfang und die Entscheidung über Perspektivwechsel zwischen mehreren Tabs.

## Verifikation und Belege

- Git-Status, Historie und alle sechs Worktrees gelesen; Branch-Divergenz,
  Duplikate und ausgewählte Reverse-Patches geprüft.
- Container-Metadaten, Dateihashes und öffentliche HTTPS-Routen geprüft;
  Schemaabfrage nur auf Tabellennamen, keine Nutzerinhalte gelesen.
- Hauptbaum: **61 Tests bestanden** (Playtable-Rechte/Vision, Kalender und
  Umfrage). Die vier zusätzlichen Chromium-Tests scheiterten zunächst beim
  Browserstart an fehlender `libatk`, nicht an Produktassertionen.
- Mit den bereits vorhandenen Browserbibliotheken erneut nur diese vier
  Token-Tests ausgeführt: **4 bestanden**. Firefox war abgewählt und wurde
  nicht verifiziert. Keine neue Dev-/Staging-Umgebung eingerichtet.
- Eagle-Baum: **24 Playtable-Rechte-/Vision-Tests bestanden**; Vergleich der
  relevanten sieben Play-/Socket-Dateien mit Live ohne Unterschiede. Die
  Testdatenbanken waren isolierte SQLite-In-Memory-Fixtures.
- Live-CSS-Reproduktion mit Chromium 151.0.7922.34, 1440/390 px: Wand, Licht
  und Sicht trotz Hidden-Flag sichtbar. Keine Mutation der Live-Anwendung.
- Nicht ausgeführt: vollständige Testsuite, Kalender-Browserreise,
  PostgreSQL-Konkurrenztest, vollständiger Build, Deployment, echte
  angemeldete DM-/Spielerreise, Prüfung aller alten Proofs/Infra-Pakete.

Belege (dauerhaft aufzubewahren):

- [Runtime-Zusammenfassung](proofs/vtt-live-audit-2026-11-01/runtime-summary.json)
- [Dateiinventur aller Worktrees](proofs/vtt-live-audit-2026-11-01/worktree-inventory.csv)
- [Live-Dateihashes](proofs/vtt-live-audit-2026-11-01/live-hashes.json)
- [Live-/Hauptbaum-Vergleich](proofs/vtt-live-audit-2026-11-01/live-vs-worktree.json)
- [Öffentliche HTTP-Prüfungen](proofs/vtt-live-audit-2026-11-01/public-http.json)
- [CSS-Sichtbarkeitsnachweis](proofs/vtt-live-audit-2026-11-01/live-hidden-css.json)
- [Token-Testlauf](proofs/vtt-live-audit-2026-11-01/token-batching-tests.txt)
- [Eagle-Rechtetestlauf](proofs/vtt-live-audit-2026-11-01/eagle-role-tests.txt)

Zusätzliche Rohlogs, lokale Live-Codekopien und isolierte Screenshots liegen
temporär unter `/tmp/vtt-discover-20261101/`. Die Hashinventur ersetzt kein
Source-Backup; die existierenden Worktrees/Images wurden erhalten.

## Abschluss und nächster Schritt

Die [Repo-Regel](../AGENTS.md) verlangt für beauftragte Funktionsänderungen ab
jetzt Commit, Live-Auslieferung, erreichbaren UI-Einstieg und dokumentierte
Live-Prüfung im selben Arbeitszyklus. Eine gesonderte Dev-/Staging-Umgebung ist
keine Voraussetzung. Bewusste Ablösungen bleiben erlaubt; Audit-/Planungsphasen
werden nicht als Featureimplementierung ausgegeben.

**Nächster begrenzter Schritt: Apply für die sichtbare DM-/Spielertrennung am
Playtable**, beginnend mit dem belegten Toolbar-Fehler, danach dem Vertrag für
„als Spieler betreten“. Ausgangspunkt ist der zuletzt beschlossene Eagle-
Produktstand mit den weiter geltenden Live-Ergänzungen. Abnahme und Live-Pfad
müssen vor Deploy konkret sein; der Alt-Backlog wird dafür nicht pauschal
eingespielt. Dieser Report ist keine Behauptung, dass die Rollenwahl oder
Makroleiste bereits umgesetzt sei.
