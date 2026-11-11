# Deploy P1: unabhängige Tischkontexte

status: implementiert und veröffentlicht; [Live-Monitor](DADM_MONITOR_PLAYTABLE_CONTEXTS_2026-11-11.md) abgeschlossen.
input_summary: autorisierter Apply-Vertrag P1. artifacts: geänderte Laufzeit,
Tests, separates Release-/Live-Protokoll; retention permanent.

## implementation_summary und files_changed

`vtt/play/contexts.py` und `models/table_context.py`: gehashte Capabilities,
achtstündige explizite Delegation, Login-/Mitgliedschafts-/Rollenwiderruf,
HTTP- und Socketgrenzen einschließlich ausgehender Tisch-/Moderationsräume.
Modellregistrierung und App-Factory integrieren beide Grenzen. Logout widerruft
offene Tischdelegationen. Keine Kampagnen-Ownerprivilegien bei fehlendem Tischkontext.

Play-/Campaign-/Community-/Session-/Sheet-/Permission-Hilfen verwenden den
effektiven Kontext. Legacy-M41-APIs sind auf DM-Kontexte begrenzt; vollständige
Playerzustände kommen aus den aktuellen gefilterten Schnittstellen. Zieltoken
werden auf Session und Sichtbarkeit geprüft. Chatmoderation bleibt im Playerkontext
gesperrt; private Chatänderungen werden rollenbezogen verteilt.

`play-player.js`, `play-dm.js`, `play/surfaces/dm.json` bilden getrennte Kompositionen.
Die Basisseite enthält keine DM-Templates. Die DM-Datei wird nur nach autorisiertem
Bootstrap geladen; Player initialisieren keine Session-/Geometrie-/Upload-DM-Handler.
Eigene Token-Sichtweite, Zielwahl und bestehende gemeinsame Bedienung bleiben erhalten.
Auth-/Play-Client-/Socketmodule transportieren die Capability; Moduswechsel
widerruft nur den bisherigen Kontext, parallele Tabs bleiben unabhängig.

## proofs und acceptance_checklist

- 26 verschiedene API-/Socket-/Aktionsfälle bestanden: `tests/test_table_contexts.py` und
  `tests/test_action_bar_v1.py`. Enthält dynamische Prüfung aller sessionbezogenen
  aktuellen und Legacy-HTTP-Routen bei fehlendem Kontext, sieben ungültige
  Kontextvarianten, Owner-Player, Moderation, Logout/Widerruf und Sessionziele.
  Die zusätzliche Refresh-/Logout-Prüfung bestand mit 2 Fällen; Logout war bereits
  im 25er-Lauf enthalten und ist nicht doppelt gezählt.
- Browserreise im endgültigen Stand in Firefox und Chromium erneut bestanden:
  2 Fälle in 40,21 Sekunden; unabhängige Modi, geladene Module, Reload und
  Playerprojektion ohne versteckten Token, keine JS-Ausnahmen.
- `git diff --check` und Python-Kompilierung bestanden.
- Live-Gates erfüllt: Tabelle gezielt angelegt, Imageidentität und Push erfasst,
  app-only umgeschaltet, angemeldete Player-/DM-Wege geprüft und eigene
  synthetische Daten entfernt; Belege im Monitorbericht.

## Risiken und Übergabe

risks_and_assumptions: niedrig – additive Tabelle enthält nur kurzlebige
Berechtigungsdaten und wird vom alten Image ignoriert. Das tatsächliche
Tilesheet-Image bleibt als Rückweg erhalten. 304 vorhandene Quellpfade wurden
gegen Produktion verglichen; 79 alte, dort bewusst fehlende G1-/Authoringpfade
werden nicht in das Image zurückkopiert. Deployment verwendet nur die P1-Pfade
als Overlay auf dem tatsächlich laufenden Image.

next_step: P2 im selben autorisierten Programm; der abgeschlossene Live-Monitor
enthält Sourcecommit, Imageidentität, UI-Einstiege und Rückweg für P1.
