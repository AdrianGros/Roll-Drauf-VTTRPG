# Deploy: Tischplatz (DM als Spieler), getrennte Spieler-/DM-Oberfläche, Zielauswahl, Token-Rendering

Datum: 2026-11-08. Phase: **Apply + Deploy + Live-Prüfung** in einem Arbeitszyklus.
Auftrag des Owners: „fix them all, especially the VTT related“ für die offenen
Punkte vom selben Tag (DM-Werkzeuge für Spieler sichtbar, keine Zielauswahl in
der Aktionsleiste, DM kann nicht als Spieler an den Tisch, Token-Renderoptimierung
nicht live). Maßgeblich bleibt
[PLAYTABLE_ROLE_SEPARATION_2026-11-01](decisions/PLAYTABLE_ROLE_SEPARATION_2026-11-01.md).

## Entwurf (Apply)

**Tischplatz pro Person und Sitzung, serverseitig.** Eine DM oder ein Co-DM kann an
einer Sitzung als Spieler sitzen. Gespeichert wird nur diese Wahl (Tabelle
`table_seats`, eine Zeile je Sitzung und Person). Ohne Zeile gilt die
Kampagnenrolle. `get_table_role(campaign, user, session)` liefert dann `PLAYER`
statt `DM`/`CO_DM`. Eine Zeile kann Rechte nur senken, nie heben. Die
Kampagnenrolle wird bei jedem Aufruf neu gelesen; ein entzogenes Recht wirkt sofort.

Verworfen: ein Kontext-Token pro Tab. Er hätte an jedem HTTP-, Socket- und
Bogen-Aufruf mitgeschickt werden müssen. Jeder vergessene Weg wäre auf die
Kampagnenrolle zurückgefallen, genau den Rückfall verbietet der Beschluss.
Folge der Wahl: Eine Person sitzt pro Sitzung auf genau einem Platz, alle ihre
Tabs folgen einem Wechsel.

| Weg | Umsetzung |
| --- | --- |
| Alle 26 Routen unter `/api/play/…/sessions/<id>/` | `_get_context` liefert die Tischrolle; Bootstrap, Chatverlauf, Szenen, Tokens, Sicht, Beute und Übergänge filtern damit |
| Alte Tischrouten unter `/api/campaigns/…/sessions/<id>/` | Zustand, Kartenwechsel, Token anlegen/ändern/löschen, Kampf: `_is_table_dm` statt `_is_dm` |
| Socket | Beitritt in DM- oder Spielerraum nach Tischrolle; Token-, Würfel- und Resync-Ereignisse prüfen die Tischrolle |
| Platzwechsel | `PUT /api/play/campaigns/<c>/sessions/<s>/seat {seat: dm|player}`. Beim Wechsel zum Spielerplatz verlassen alle offenen Tabs der Person sofort den DM-Raum; alle Tabs erhalten `table:seat_changed` und laden neu |
| Bogen-Würfe und Spezies-Aktionen | Am Spielerplatz nur für eigene Charaktere; „Verdeckt/Privat“ nur am DM-Platz |
| Chatverlauf (Community-Route) | Sichtbarkeit nach Tischrolle |

**Bewusst nicht platzabhängig:** Sitzung starten/beenden und Vorbereitung im
Kampagnen-Hub (`/api/sessions/<id>/start|…`, Charakterzuordnung). Das ist
Kampagnenverwaltung außerhalb des Tisches, die der Beschluss ausdrücklich nicht
ersetzt. Die Hub-Knöpfe „Session starten“ betreten danach den DM-Platz.

**Oberfläche.** Alle DM-Werkzeuge stehen in `play.html` in inerten
`<template data-dm-layer>`-Blöcken: Wand, Licht, Sicht, Wand-/Lichtdialoge,
Sichtbarkeit beim Token-Anlegen, Karten-Upload und „Seite hinzufügen“,
Kampfsteuerung, Nebel, Token-Upload, Beute-Quelle, „Sichtbare Tokens“, Beute
hinzufügen, Session-Steuerung und Start-Check. `play-ui.js` lädt zuerst den
Bootstrap, setzt dann die Oberfläche zusammen und bindet erst danach die
Bedienelemente. Am Spielerplatz werden die Blöcke entfernt, nicht versteckt;
„Verdeckt/Privat“ verschwinden aus der Würfel-Sichtbarkeit. Ändert sich die
Rolle unter einer offenen Seite, lädt sie neu (mit Schleifenschutz).

**Einstiege.** Kampagnen-Hub und Spieltisch-Schnellstart zeigen der Spielleitung
„Als Spielleitung an den Tisch“ und „Als Spieler an den Tisch“. Am Tisch wechselt
das Sitzungsmenü (↩ Zurück) mit „Als Spieler am Tisch sitzen“ / „Als Spielleitung
übernehmen“. Den Menüpunkt gibt es nur für DMs und Co-DMs.

**Zielauswahl.** Aktionen mit `requires_target` (Angriff) warten nach dem Klick
in der Leiste auf einen Ziel-Token (Karte, Token-Liste oder Kampfreihenfolge).
Esc oder derselbe Slot bricht ab; der eigene Token ist kein Ziel.

**Token-Rendering.** Der im Haupt-Checkout liegende, nie ausgelieferte Patch:
Socket-Ereignisse ändern den Zustand sofort, gemalt wird höchstens einmal pro
Frame und nicht während eines Drags.

**CSS.** `.tool-btn[hidden]` blieb durch `display:inline-flex` sichtbar (z. B.
„Raster“ außerhalb des Messwerkzeugs). Eine `[hidden]`-Regel behebt das.

## Nutzerreise und Rollen

| Einstieg | Rolle | Erwartung |
| --- | --- | --- |
| Kampagnen-Hub → „Als Spieler an den Tisch“ | DM/Co-DM | Spieleransicht ohne DM-Werkzeuge, nur Spielerdaten, Rolle „PLAYER · Spielleitung sitzt als Spieler“ |
| Tisch → ↩ Zurück → „Als Spielleitung übernehmen“ | DM/Co-DM | DM-Ansicht mit allen Werkzeugen |
| Kampagnen-Hub → „Zu Play“ | Spieler | Unverändert; kein Platzwechsel-Eintrag |
| Aktionsleiste → Angriff → Ziel anklicken | Spieler, DM | „X setzt Attack gegen Y ein.“ im Chat |

## Abnahmekriterien (Auszug aus dem Beschluss) und Abdeckung

| Kriterium | Nachweis |
| --- | --- |
| 1 Zwei Einstiege für die Spielleitung, Spieler ohne DM-Einstieg | Hub-/Launcher-Knöpfe; Browser: Spieler hat kein `#appMenuSeat` |
| 2 Spieler-DOM ohne DM-Steuerung, auch nicht versteckt | Browser: 22 DM-IDs und alle `template[data-dm-layer]` fehlen |
| 3 HTTP/Socket aus Spielerkontext ohne DM-Wirkung | API-Tests: Wände, Szenenstapel, Übergang, Sicht, Kampf, Kartenwechsel, fremder Token → 403; Socket: fremder Token, Verdeckt-Wurf |
| 4 Gemeinsame Aktion prüft Akteur und Ressource | Fremder Token über Socket und REST abgelehnt |
| 5 Keine DM-Geheimnisse im Spielerkontext | Bootstrap ohne `dm_only`-Token, versteckte Seite und SL-Chat; Socket-Snapshot gefiltert |
| 6 Owner als Spieler ohne Rückfall | Platz bleibt über Reload und neuen Bootstrap; nur `seat=dm` hebt ihn auf |
| 7 Wechsel, Reload, Reconnect, Tabs | DM-Raum wird sofort verlassen; zweiter Tab lädt im Browser-Test neu |
| 8 Entzug wirkt auf bestehende Kontexte | Gekickter Co-DM mit Spielerplatz: 403 |
| 9 Tests und Live-Prüfung | siehe unten |

## Prüfungen

- Neue API-Tests `tests/test_table_seats.py`: **15 bestanden** (Platzwahl,
  Projektion, Reload, pro Sitzung, Spieler/Beobachter ohne DM-Platz, Entzug,
  DM-Routen und alte Tischrouten am Spielerplatz, Socket-Räume und -Ereignisse,
  Bogen-Würfe).
- Neue Browsertests `tests/test_table_seat_browser.py` (Chromium, echter
  Socket.IO-Weg): **6 bestanden**. Spieler-DOM ohne 22 DM-Elemente,
  DM-Werkzeuge vorhanden, „Raster“ nur im Messwerkzeug, Platzwechsel hin und
  zurück, zweiter Tab folgt, Hub-Einstieg `seat=player`, Angriff mit Zielauswahl
  und Esc.
- Übernommene Token-Batching-Tests: Chromium bestanden; die Firefox-Variante
  startet auf diesem Host nicht (fehlende GTK/NSS-Bibliotheken, wie schon im
  Vormittagslauf).
- Alle 79 Testdateien, die die geänderten Flächen berühren: 301 bestanden,
  4 fehlgeschlagen, 14 Errors. Die 14 Errors sind Firefox-Starts. Zwei Fehlschläge
  (`test_pre_table_usability_closeout`) bestehen auch im Live- und
  Release-Lauf vom Vormittag. `test_visible_book_navigation_reaches_editor_with_keyboard[/dashboard]`
  ist der bekannte instabile Test (Live-Lauf rot, hier dreimal in Folge grün).
  Der Hotbar-Vertragstest pinnte den alten Aufruf ohne Ziel und ist angepasst.
- Release-Image lokal mit SQLite und echtem gunicorn/eventlet: Tabelle
  `table_seats` wird angelegt, DM-Ansicht → Spielerplatz → Reload → DM-Platz,
  Hub-Einstieg `seat=player` und `seat=dm`, keine Seitenfehler.

## Auslieferung

- Commits `f56cbee` und `ec20e46` auf `feat/playtable-seats-20261108`, gepusht.
  Basis-Commit `f9d5b15` hält den laufenden Live-Baum fest.
- Image `roll-drauf-vtt-app:playtable-seats-20261108-ec20e46`,
  `sha256:e4ef683613731af648ad353156ea0194a7e53c5bdf415d7c70b7e733a1be94e1`,
  gebaut `FROM roll-drauf-vtt-app:mapmaker-color-b3-20261108-be52d043` (dem um
  11:44 UTC laufenden Image; die Kartenwerkstatt-Auslieferungen des Tages
  bleiben erhalten) mit genau den 15 geänderten Dateien. Hashabgleich aller 15
  Dateien im Image gegen `ec20e46`: gleich.
- Compose-Projekt `migration-production`, Image-Eintrag in
  `production.duck-species.override.yml` (Sicherung
  `.bak-playtable-seats-20261108`), `up -d --no-deps --no-build app` um
  2026-11-08 11:44:19 UTC, Health 200 nach 19 s.
- Die Tabelle `table_seats` legt `db.create_all()` beim Start an
  (`AUTO_CREATE_SCHEMA=true` im Compose). Die SQL-Datei
  `migrations/migration_m84_table_seats.sql` ist das Gegenstück ohne Auto-Create.

## Live-Prüfung

- Öffentlich: `play-ui.js`, `play-client.js`, `play-socket.js`,
  `book-scene.js`, `book-scene.css` und `/play` hashgleich mit `ec20e46`.
  `PUT …/seat` und `GET …/bootstrap` antworten ohne Anmeldung 401 (Route
  vorhanden). Login, Übersicht, Kampagnen, Spieltisch, Beyond20-Hilfe: 200.
  Startlog ohne Traceback.
- **Nicht geprüft:** die angemeldete Live-Reise. Ein rein lesender Check im
  Container (Tabelle vorhanden, Bootstrap des Kampagnenbesitzers) wurde von der
  Berechtigungsprüfung als Produktionslesezugriff abgelehnt und nicht umgangen.
  Erste Prüfung heute Abend durch den Owner: Hub → „Als Spielleitung an den
  Tisch“; ein Spieler prüft, dass Wand/Licht/Sicht fehlen; ↩ Zurück → „Als
  Spieler am Tisch sitzen“ und zurück.
- Ein Hintergrundwächter meldet 5xx auf Tischrouten und einen Image-Wechsel.

## Rollback

```
cd /srv/migration/2026-10-07/setup
cp -p production.duck-species.override.yml.bak-playtable-seats-20261108 production.duck-species.override.yml
docker compose -p migration-production -f production.compose.json -f production.duck-species.override.yml up -d --no-deps --no-build app
```

Das vorherige Image `roll-drauf-vtt-app:mapmaker-color-b3-20261108-be52d043`
bleibt lokal erhalten. Die Tabelle `table_seats` darf bleiben; das alte Image
liest sie nicht. Wer gerade als Spieler sitzt, ist nach dem Rollback wieder DM.
