# Deploy: Einstieg ohne Buchcover, Tabwechsel ohne Vorhang, Beyond20 robuster

Datum: 2026-11-08. Phase: **Deploy + Live-Prüfung**. Auftrag des Owners:
Die Zwischenseite „Zum Buchzugang“ entfällt. Die Landingpage ist direkt der
Login. Nach der Anmeldung folgt die Übersicht. Zwischen den Tabs wird ohne
Übergang und ohne dunklen Blitz gewechselt. Außerdem soll geprüft werden, ob
Beyond20-Würfe (auch in Firefox) zuverlässig ankommen.

## Nutzerreise und Rollen

| Einstieg | Rollen | Erwartung |
| --- | --- | --- |
| `https://vtt.roll-drauf.de/` → `/login.html` | alle | Offenes Buch, Formular ab dem ersten Bild bedienbar, kein Cover, kein Klick vorab |
| Login (Passwort oder Discord) → `/dashboard` | angemeldete Nutzer | Übersicht ohne dunklen Ladevorhang und ohne Mindestwartezeit |
| Hauptnavigation Übersicht / Kampagnen / Charaktere / Bogen | angemeldete Nutzer | Buch bleibt offen, Navigation bleibt stehen, nur der Inhalt lädt nach |
| Spieltisch betreten und verlassen | DM und Spieler | Kein Eintritts- oder Austrittsvorhang, keine Exit-Wartezeit |
| Spieltisch-Seitenleiste „D&D Beyond“ | DM und Spieler | Zeigt, ob Beyond20 auf der Seite aktiv ist |

## Befund vor dem Fix

- Jeder Seitenwechsel innerhalb des Buchs malte zuerst das geschlossene Cover
  „Zum Buchzugang“, darunter einen dunklen Vollbild-Vorhang „… wird
  vorbereitet“ (Übersicht mit mindestens 620 ms). Das Buch wurde erst nach
  Auth-Check, Daten- und Textabruf geöffnet, nacheinander statt parallel.
- Der Spieltisch startete unsichtbar hinter einem dunklen Eintrittsvorhang und
  wartete beim Verlassen bis zu 900 ms hinter einem Austrittsvorhang.
- Beyond20 (Quellstand v2.21.0, `src/generic-site` und `src/common/utils.js`):
  `Beyond20_RenderedRoll` liefert den Charakter als **Namensstring**. Die Bridge
  las `character.name` und schickte deshalb leere Namen. Würfe während eines
  Socket-Abbruchs gingen verloren. Würfe aus einem schreibgeschützten Platz
  (Session nicht gestartet oder beendet, Zuschauer) wurden kommentarlos
  verworfen. Ob Beyond20 überhaupt auf der Seite lief, war nirgends sichtbar.
- Einrichtungsfallen laut Beyond20-Quelltext: Eintrag ohne `https://` wird
  verworfen. Ohne „Apply“ fehlt die Host-Berechtigung (Firefox-MV2-Build:
  optionale Berechtigung `*://*/`). Die Injektion erfolgt erst beim Laden des
  Tabs. Mit dem Ziel „D&D Beyond Dice Roller & Discord“ gehen keine Würfe an
  eigene VTT-Seiten.

## Änderung

Branch `fix/vtt-entry-beyond20-20261108`. `876a288` hält die Live-Fassung der
berührten Dateien fest. Die Änderung selbst steht in `324482d` und `864678b`.

- `login.html`: offenes Buch und sichtbares Formular serverseitig. Eine
  bestehende Sitzung leitet direkt weiter.
- `book-scene.js` und `book-scene.css`: Das Buch ist immer offen
  (`body.book-scene-open`), die Cover-API ist entfernt. Ein Lade-Rahmen mit der
  Navigation der Zielroute erscheint sofort. Auth und Seitentexte laden
  parallel. In-Page-Wechsel erfolgen ohne View-Transition. Die Rückkehr vom
  Tisch hat keine Ankunftschoreografie mehr.
- `dashboard`, `campaigns`, `characters`, `character-sheet`: Statushinweis
  standardmäßig versteckt, nur bei mehr als 900 ms Ladezeit als kleiner
  Hinweis sichtbar.
- `play.html` und `play-ui.js`: Start in der Stufe `table`, kein Vorhang,
  sofortige Navigation zurück ins Buch. `sendExternalRoll` meldet blockierte
  Würfe sichtbar. Nach jedem Reconnect werden wartende Würfe zugestellt.
- `beyond20-bridge.js`: Charaktername aus String oder Objekt, Warteschlange mit
  Wiederholung, Statuszeile `#beyond20Status`.
- `beyond20.html`: Abschnitt „Wenn keine Würfe ankommen“.

## Prüfungen

- Bridge-Vertrag mit dem exakten Beyond20-2.21-Payload in **Chromium 130 und
  Firefox 131**: alter Stand 4 von 10 Prüfungen rot (Name, Reconnect,
  Statusanzeige), neuer Stand 10 von 10 grün.
- Gezielte Tests auf dem Release-Inhalt: 220 Tests. Davon 7 Fehler. Vier sind
  Firefox-Tests, die auf diesem Host auch gegen Live scheitern, weil Firefox
  hier nicht startet. Drei waren veraltete String-Tests, sie wurden angepasst
  und bestehen.
- Lokale Wegwerf-Kopie des Images (SQLite) mit Frame-Serien von Landing, Login
  und Tabwechsel: vorher Cover-Frame bei jedem Wechsel, nachher keiner. Am Tisch
  gilt Stufe `table`, Vorhang-Opazität 0, keine Seitenfehler. Das Socket-Echo
  eines Wurfs war in dieser Kopie auch mit dem unveränderten Live-Image nicht
  herstellbar. Der Serverpfad ist durch `test_external_rolls.py` abgedeckt.
- Volle Suite (je ca. 26 min) auf dem extrahierten `/app`: Live 12 Fehler und
  10 Errors, Release 14 Fehler und 10 Errors. Die Errors sind identisch. Neu im
  Release waren drei veraltete String-Tests (`test_dashboard_social_hub_guild_navigation`,
  zweimal `test_play_transition_choreography`), inzwischen angepasst und grün.
  Dazu kam `test_creation_engine_navigation::test_play_session_menu_uses_existing_return_transition[True]`.
  Er besteht auf dem Endstand dreimal in Folge, ist also instabil. In derselben
  Datei schlugen im Live-Lauf zwei andere Browser-Tests vergleichbar instabil
  fehl. Die übrigen Fehler sind in beiden Läufen identisch und bestanden schon
  vorher.

## Auslieferung

- Image `roll-drauf-vtt-app:entry-beyond20-20261108`,
  `sha256:e6477ac8ef803c4681e7db724be9a207043d81a2cac0675f1c092125587a5269`,
  gebaut `FROM roll-drauf-vtt-app:research-survey-20261029` und nur mit den 11
  geänderten Anwendungsdateien. Ein Hashabgleich aller 11 Dateien gegen den
  Commit ist gleich.
- Compose-Projekt `migration-production`. In
  `/srv/migration/2026-10-07/setup/production.duck-species.override.yml` ist das
  Image umgestellt (Sicherung `.bak-entry-beyond20-20261108`).
  `up -d --no-deps app` erfolgte um 2026-11-08 09:09:25 UTC. Health liefert 200
  nach 3 s.

## Live-Prüfung

- Öffentlich liefern alle betroffenen Routen und Assets 200. Die ausgelieferten
  `book-scene.js`, `book-scene.css`, `play-ui.js` und `beyond20-bridge.js` sind
  hashgleich mit dem Commit.
- Anonym in Chromium 130 und Firefox 131 gegen `https://vtt.roll-drauf.de`: `/`
  führt auf den Login, das Formular ist sofort sichtbar und editierbar, ohne
  Cover-Text. `/dashboard` ohne Sitzung führt auf den Login. Die Beyond20-Hilfe
  enthält den neuen Abschnitt. Es gab keine Seitenfehler.
- **Nicht geprüft:** eine angemeldete Live-Reise und ein echter Beyond20-Wurf
  aus D&D Beyond. Dafür fehlt ein Live-Testkonto. Beides ist der erste Schritt
  der heutigen Session (Statuszeile am Tisch, ein Probewurf).

## Rollback

```
cd /srv/migration/2026-10-07/setup
cp -p production.duck-species.override.yml.bak-entry-beyond20-20261108 production.duck-species.override.yml
docker compose -p migration-production -f production.compose.json -f production.duck-species.override.yml up -d --no-deps app
```

Das vorherige Image `roll-drauf-vtt-app:research-survey-20261029`
(`sha256:0febdcf788a3…`) bleibt lokal erhalten.
