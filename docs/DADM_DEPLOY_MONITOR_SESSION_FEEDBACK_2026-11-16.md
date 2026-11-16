# Sessionfeedback: konsolidierte Lieferung und Monitor

Status: live ausgeliefert und technisch geprüft; neue Owner-Abnahme ist möglich.
Profil standard; retention permanent. Ziel: https://vtt.roll-drauf.de.

## Auftrag und Konsolidierung

Der Owner hat den bisherigen Playtable-Stand nach einem vollständigen Durchgang
als approved erklärt und R01–R06 zur Umsetzung und Live-Auslieferung autorisiert.
[Apply](DADM_APPLY_SESSION_FEEDBACK_2026-11-16.md) und
[Abnahmereisen](acceptance/PLAYTABLE_SESSION_2026-11-16.md) halten diese Grenze fest.
Die historische allgemeine Playtable-Spielabnahme ist kein offener Lieferblocker.
N07 (Creator-Homebrew), S15/B10 (Kontingente) und der zurückgestellte N11-Regler
bleiben außerhalb dieses Auftrags. Superseded G1-Code wurde nicht reaktiviert.
Die Umsetzung liegt in einem isolierten Worktree; fremde Änderungen im
ursprünglichen Arbeitsverzeichnis wurden nicht gebündelt.

## Gelieferte Reisen und Abnahmegrenzen

Alle Reisen beginnen unter **Kampagnen → Sitzung → als Player/DM öffnen**.
Kampagnenbesitz erzeugt in einer ausdrücklich gewählten Playeransicht keine
DM-Befugnisse. Die Player-Komposition montiert keine DM-Steuerungen.

| Slice | Sichtbarer Einstieg und Rollen | Ergebnis / Abnahmekriterium |
|---|---|---|
| R01 Beyond20 | Werkzeugleiste → Beyond20, Player und DM | Adresse kopieren, drei Aufgabenblöcke, nachgeordnete Fehlerhilfe; Empfangsstatus bei Würfeln. |
| R02 Tokenmenü | Werkzeugleiste → Tokens, Player und DM | Ein Tokenfenster mit direktem Bild-Upload und Platzierung; der doppelte zentrale Token-Werkzeugbutton entfällt. |
| R03 Fenster | Seiten, Initiative, Tokens, DM-Layers, Chat, Journal, Würfeln, Beyond20; Bogen, Einstellungen und Dialoge | Mehrere bewegliche Fenster; Position pro Nutzer/Kampagne/Tischmodus auch nach Schließen und Reload; Reset im App-Menü. Feste Werkzeugleiste und Hotbars bleiben erreichbar. |
| R04 Initiative | Eigenen Token auswählen → Initiative würfeln; eigener Bogen oder Beyond20 | Validierter Akteur, bestehende Werte beim Kampfstart erhalten; Beyond20-Initiative aktualisiert denselben Token und beide Turn-Order-Ansichten. Andere Wurftypen erhalten die Akteurzuordnung, ohne automatische HP-Änderung. |
| R05 Bibliothek | Tokens → Auswahl speichern / Bearbeiten / Platzieren | Persönliche Vorlagen je Kampagne und servervalidiertem Modus für Player und DM. Bild und berechtigte Bogenbindung über Karten hinweg wiederverwendbar; kein alter Initiativwert oder Instanzzustand. |
| R06 Kampagnenräume | Tisch → Chat → Kampagnenchat in Gespräche öffnen; Hauptnavigation → Gespräche | Derselbe dauerhafte Kampagnenverlauf; alle eigenen aktiven Kampagnen erscheinen als Räume. Private Gespräche und bisherige Sessionwürfe behalten ihre Grenzen. |

Bibliotheken sind zunächst persönlich und kampagnenintern. Vorlagenänderungen
verändern keine schon platzierten Instanzen. Eine Charakterbindung ist je Karte
einmal zulässig; Besitz und Berechtigung werden bei jeder Platzierung erneut
geprüft. Neue Karte bedeutet keine Heilung eines gebundenen Charakters.

## Umsetzung und geänderte Bereiche

- `vtt/play/token_library.py`, `vtt/models/session_feedback.py`: Vorlagenmodell,
  Eigentum, Kontextprüfung und erlaubte Werte; zusätzliche Kampagnenchat-Tabelle.
- `vtt/play/rolls.py`, `vtt/socket_handlers.py`, `vtt/combat/service.py`,
  `vtt/characters/sheet_link.py`: gemeinsamer Initiativdienst, bestehende Receipts,
  Akteurprüfung, Sperren bei konkurrierenden Würfen und Bindung pro Karte.
- `vtt/campaign_rooms.py`, `play-campaign-room.js`, `private-conversations.js`:
  gemeinsamer Raum, UUID-Deduplizierung, Verlaufscursor und erneute
  Mitgliedschafts-/Sperrprüfung bei jedem Aufruf.
- `play-windows.js`, `play-windows.css`, `play-token-library.js`, `play-ui.js`,
  `play.html`, DM-Surface und DE-/EN-Kataloge: vorhandene autorisierte Inhalte
  werden in bewegliche Fenster übernommen; gemeinsamer erlaubter Upload.
- `beyond20.html`, `beyond20-bridge.js`, `play-socket.js`: kurze Anleitung,
  erhaltener Wurftyp/ausgewählter Akteur, verworfene Würfe ignorieren und Versand
  erst nach bestätigtem Sessionbeitritt.

Kein neues Laufzeitpaket. Die beiden Tabellen sind additiv; es gab keine
Übernahme alter Session- oder privater Nachrichten in Kampagnenräume.

## Gezielte Verifikation

78 verschiedene Backendfälle sind bestanden. Die API-Auswahl und späteren
gezielten Wiederholungen überlappen und werden nicht addiert. Sie prüfen
Vorlagen, Rollen/Kontexte, fremde/geheime Tokens, Initiative, doppelte Events,
Chatmitgliedschaft, private Gespräche, Upload und Charakterbindung pro Karte.
Die Backendlogik wurde nach diesen Prüfungen nicht mehr verändert.

Die Browserauswahl umfasst 17 Fälle in Chromium, Firefox und WebKit:
Sessionfeedback, persönliche Aktionen, Rollenkomposition, mobile Bedienung,
Layer und Clipboard. Die abschließende Wiederholung schließt die präzisierte
Leistenprüfung ein. JavaScript-Syntax (sieben geänderte Einstiegspunkte),
Python-Kompilierung, DE-/EN-Katalogprüfung (3373 Quellen) und Diff-Prüfung sind
dokumentiert. Die vollständige Repository-Testsuite wurde nicht ausgeführt.
Die konkreten Läufe stehen in [checks.json](proofs/session-feedback-2026-11-16/checks.json).

## Live-Nachweise und begrenzte Reworks

Der erste komplette Live-Durchlauf bestätigte neun Reisegruppen über die normale
Kampagnennavigation mit isolierten synthetischen DM-/Player-Konten, Chromium und
Firefox sowie Owner-as-Player. Echte HTTP-/Socket-/PostgreSQL-Wege wurden benutzt.
Ein vorheriger Prüflauf hatte die alte statt der neuen gleichnamigen Tokeninstanz
ausgewählt; die Prüfung wurde auf Name und Zielkarte präzisiert und vollständig
wiederholt. Dieser Fehler lag in der Prüfroutine.

Die anschließende Sichtkontrolle fand eine tatsächliche R03-Darstellungsregression:
die aus dem alten Layoutcontainer gelöste Werkzeugleiste war etwa 235px hoch;
Labels und einige Kontrastregeln fehlten. Ein begrenzter CSS-Rework erhält die
feste, kompakte und beschriftete Zeile, Hidden-Regeln und Kontraste ausdrücklich
an der neuen Montageposition. Ein neuer Test reproduzierte die alte Höhe; danach
wurde die Browserauswahl erneut ausgeführt. Beide Reworks sind im Apply erfasst.

Auf dem korrigierten Live-Image sind erneut alle neun Reisegruppen bestanden:
normaler DM-/Player-Einstieg, Owner-as-Player, direkter Upload und Bibliothek,
Firefox-Fensterpersistenz, native und externe Initiative mit zwei Clients,
Replay-/Konkurrenzprüfung, gemeinsamer Kampagnenraum, Wiederverwendung auf der
zweiten Karte und 390px-Bedienung. Keine Browser-Page-Errors. Die feste Leiste
misst rund 65px auf Desktop und 69px bei 390px statt vorher rund 235px.
[Live-Protokoll](proofs/session-feedback-2026-11-16/live.json),
[Playeransicht](proofs/session-feedback-2026-11-16/live-player-map.png) und
[mobile DM-Ansicht](proofs/session-feedback-2026-11-16/live-dm-mobile.png)
belegen den korrigierten Stand. Fünf öffentlich ausgelieferte neue/geänderte
Assets stimmen per SHA-256 mit dem Commit überein; `/health/live` meldet `ok`.
Die gezielt geprüften Abnahmereisen der sechs Slices sind bestanden.

Die dedizierten Testkonten und ihre eigene Kampagne, Sitzungen, Vorlagen,
Nachrichten und vier Assetdateien wurden nach jedem Durchlauf entfernt.
Container- und Hostkopien der synthetischen Zugangsdaten sind entfernt.
[Cleanup](proofs/session-feedback-2026-11-16/cleanup.json) enthält die
gezählten Datensätze; reale Spieler-/Kampagnendaten gehörten nicht zum Löschscope.

## Auslieferung, Rücknahme und verbleibende Prüfung

Die konkreten Quellcommits, laufende Image-ID, Compose-Dateien, Backups,
Schema-Prüfung, Push-Status und Rollbackreferenzen stehen in
[delivery.json](proofs/session-feedback-2026-11-16/delivery.json).
Featurecommit: `e0669312017b2830a13a0d87daaf6e0d7a6d5c00`;
aktueller Anwendungscommit mit Leistenkorrektur:
`d4ff7e4fe2ef77a4a36ca41fa205ef5db2ad5b02`.
Beide sind auf `origin/feat/session-feedback-20261116` gepusht.
Aktuelles Image:
`roll-drauf-vtt-app:feedback-session-feedback-20261116-20261111-d4ff7e4fe`;
laufende ID:
`sha256:7d8f4a54b36b125611ac116b37d10c09632dbea9a920c8c5b0413ea63efd4617`.
Es gibt keinen Source-Bind-Mount; lediglich das bestehende Assetvolume bleibt.
Das gebaute Image wird für alle 80863 ausgelieferten Anwendungsdateien gegen
den committed Quellstand geprüft. Die Veröffentlichung erfolgt ausschließlich
für den App-Service; Datenbank, Redis und Mail werden nicht neu gestartet.
Vorimage und guarded Rollbackscript bleiben erhalten; ein Restore wurde nicht
probeweise ausgeführt. Additive Tabellen müssen bei App-Rollback nicht gelöscht
werden. Das Datenbankarchiv wurde mit `pg_restore --list` geprüft.
Aktueller Rücknahmeweg:
`/srv/migration/2026-11-11/feedback-session-feedback-20261116/d4ff7e4fe/rollback.sh`.
Er kehrt zum Featurestand vor der CSS-Korrektur zurück; dessen ursprünglicher
Rücknahmeweg zum vorherigen Playtable-Stand bleibt ebenfalls im Lieferprotokoll.
Nach erfolgreicher Live-Verifikation wurden ausschließlich diese Dokumentations-
und Belegdateien ergänzt; der Anwendungsquellstand wurde nicht verändert.

Die installierte Beyond20-Erweiterung mit einem echten D&D-Beyond-Tab und
konkrete Handyhardware wurden nicht verwendet. Automatisiert geprüft sind der
DOM-Vertrag, die normalen UI-Wege und die Serverwirkung. Die nächste begrenzte
Aktion ist die menschliche Abnahme der neuen Reisen auf dem ausgelieferten VTT.
