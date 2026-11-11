# Monitor P1: Tischkontexte live verifiziert

status: **P1 veröffentlicht und technisch live geprüft**. Das Gesamtprogramm
P2–P7 ist weiterhin in Arbeit; keine vorweggenommene Gesamt- oder Owner-Abnahme.
input_summary: Deploy P1 und fokussierte Prüfungen. artifacts: dieser Bericht
und [Belege](proofs/playtable-contexts-2026-11-11/README.md), retention permanent.

## Beobachtetes Ergebnis

Jeweils in Chromium und Firefox: normaler Kampagnen-Hub → ausdrücklich als Player
eintretender Kampagnen-Owner und unabhängig als DM eintretender zweiter Tab →
Player-Reload. Der Player hat keinen DM-DOM und lädt das DM-Modul nicht; der
DM-Tab besitzt die Sessionwerkzeuge. Der Owner-Player erhält keine versteckten
Tokens; direkte DM-Mutation und fehlender HTTP-Kontext liefern jeweils 403.
Zusätzlich betritt ein gewöhnlicher Player den Tisch über seinen normalen
Hub-Einstieg. Alle vier Live-Reisen bestanden, keine JS-Ausnahmen.

26 verschiedene fokussierte API-/Socket-/Aktionsfälle und zwei finale lokale
Browserfälle bestanden. Darunter dynamische Abdeckung der aktuellen und alten
Session-HTTP-Routen bei fehlendem Kontext, Owner-Player, fremde/ungültige/abgelaufene
Kontexte, Ressourcen-/Sessiongrenzen, parallele Sockets, Reconnect, Mitgliedschafts-
und DM-Entzug, Moderationsauslieferung, Observer-Schreibsperre, Logout und Refresh.

## Release, Daten und Rückweg

- Funktionsstand `721fc1c8c` (Hauptänderung `ab4e5e074`), gepusht auf
  `feat/protocol-feedback-20261110`.
- Image `roll-drauf-vtt-app:feedback-contexts-20261111-721fc1c8c`;
  `sha256:eb81dc1c236e0ecf834084909b7eac0c4b7c393b790886a08860776b473fb610`.
- 22 Overlaydateien auf dem tatsächlichen Tilesheet-Ausgangsimage; 230 erwartete
  Quelldateien im fertigen Image geprüft, keine Hashabweichung.
- Geprüft lesbarer Datenbankdump vor Schemaänderung; additive Kontexttabelle mit
  geprüften Spalten angelegt. Vorhandene Daten nicht migriert/umgeschrieben.
- Nur App neu erstellt. Andere erfasste Dienste haben identische Container-IDs
  und Startzeiten. Öffentliche `/health/live`-Antwort nach Abnahme/Bereinigung `ok`.
- Zwei eigene synthetische Konten und ihre Kampagne, Karte, Session, zwei Tokens,
  sechs Kontexte und Login-Sitzungen gezielt entfernt. Temporäre Credentialdateien
  auf Host und im App-Container gelöscht; keine fremden Inhalte verändert.
- Vorheriges Image gesichert. Rückweg:
  `/srv/migration/2026-11-11/feedback-contexts/rollback.sh`, syntaktisch geprüft.
  Weder Produktionsrollback noch Backup-Restore wurden als zusätzlicher Eingriff
  ausgeführt. Altes Image ignoriert die additive Tabelle; kein Datendowngrade nötig.

## Risiken und nächste Arbeit

risks_and_assumptions: niedrig – bestehende Tischclients ohne Capability müssen
neu eintreten. Ein ungültiger Kontext erhält keine Owner-Ersatzrechte.
Die veröffentlichte Trennung betrifft Tischwege; eigenständige globale Konto- und
Kampagnenverwaltung bleibt ein separater Berechtigungsbereich gemäß Owner-Entscheid.

Persönliche Aktionsbelegung, Request-Dedup und vollständige Firefox-Würfelreise
sind **P2 und noch nicht geliefert**. next_step: P2-Discover/Apply abschließen,
darauf persistenten Hotbar-/Ausführungs-/Wiederaufnahmevertrag umsetzen und live
prüfen. Der gemeinsame Owner-Test erfolgt erst nach P2–P6 und Gesamtprüfung P7.
