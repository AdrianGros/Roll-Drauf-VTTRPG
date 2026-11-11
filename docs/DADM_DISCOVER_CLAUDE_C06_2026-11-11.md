# Discover C06 – Hub, gemeinsamer Kalender und Terminplanung

Status: Quelleninventur abgeschlossen, Apply erforderlich. Profil standard,
dauerhaft. Input R01–R04; R2 präzisiert die spätere Produktentscheidung:
gemeinsamer Kalender der eigenen Sessions für DM und Player, Kampagnenfilter,
30-Tage-/Monatsansicht; darunter fehlende DM-Termine bzw. eigene offene Stimmen.
Die zunächst vermisste und später gefundene Session-Vorbereitung bleibt erforderlich.

## Bestand und passende Vorarbeit

- `book-scene.js` baut Kampagnenübersicht und Hub, hat bereits Suche/Seitenwechsel,
  öffentliche Beitrittsanfragen und Session-Einstieg. Öffentliche und eigene Runden
  werden noch gemeinsam gerendert. Das Hub-Mitgliederledger hat Entfernen für
  vorhandene zulässige Zielrollen, aber keinen vollständigen Aktionsstreifen.
- `GameSession.scheduled_at` ist naive UTC, duration_minutes/status vorhanden.
  Laufzeitstatus und Planung dürfen nicht verwechselt werden: die aktuelle
  get_runtime_status-Projektion bildet cancelled auf paused ab. Ein Kalender
  muss den ursprünglichen Status zeigen und abgesagte Termine kennzeichnen.
- Eigene Kampagnen sind Owner oder aktive CampaignMember; invited/pending/left/
  kicked sind keine Kalenderleseberechtigung. `_is_dm` berücksichtigt einen
  mitgeführten Player-Kontext und erteilt dann keine DM-Schreibrechte.
- Separater Worktree `/home/admin/projects/roll-drauf-vtt-calendar`, HEAD
  `e2a7a5859` (WIP, nicht deployed), enthält SessionSeries/SessionOccurrence,
  campaign-scoped Calendar-Routen, Zeitzonen-/Serienarithmetik, CSS/JS sowie API-,
  Browser- und disposable-Postgres-Tests. Keine dortigen Dateien geändert.
- WIP kennt once/weekly/biweekly/monthly, originären Monatsanker (31→28→31),
  IANA-Zeitzonen, Sommerzeitlücke und doppelte Herbstzeit. Serienspeichern hat
  Campaign-Lock und eindeutigen Request-Key/Digest; Abbruch betrifft nur künftige
  noch nicht gestartete Sessions. Materialisierung erzeugt echte GameSessions.
- WIP-Kalender ist jeweils eine Kampagne, Woche/Monat/Jahr. Kein übergreifender
  eigener Kalender und keine Abstimmungsmodelle/-routen in der Integrationsbasis.
  Der GET materialisiert Serien und schreibt unter Campaign-Lock; das ist ein
  bewusster Abgleichpunkt für die neuen Leser-/Schreibverträge, kein blind zu
  übernehmender Standard. Er hält über next_index den Serienfortschritt fest.
- WIP-Postgrestest erwartet disposable ce_test auf Port 55432 und isolierte
  Testschemas. Er darf nicht auf der Produktionsdatenbank ausgeführt werden.

## Risiken und offene Designpunkte

Medium: WIP gegen C01-Lokalisierung und neuere Live-Dateien integrieren; niemals
den gesamten alten Branch ausrollen. Medium: neue Kalenderprojektion muss über
alle verwendeten IDs aktuelle Mitgliedschaft prüfen; öffentliche Listbarkeit
ist keine Sessionleseberechtigung. Medium: Serien-/Termin-/Abstimmungsaktionen
brauchen klare Rollen, Retry-/Parallelitätsverträge und additive Migrationen.
Medium: Sommerzeit/naive UTC, Absagen und wiederholte Monatsanker sind bestehende
fachliche Verträge; nicht durch Browser-Date-Parsing vereinfachen. Medium:
Terminabstimmungen existieren noch nicht, deshalb muss „ausstehende Stimme“
zusammen mit einem bedienbaren Erstellen-/Abstimmen-/Festlegenweg entworfen werden.
Low: Kalenderplatz, einheitliche Präsentation, schmale Ansicht und Beschriftungen.

Nächster Schritt Apply: WIP-Dateien selektiv wiederverwenden, gemeinsamen
Kalender-Lesevertrag, Serienpflege und Abstimmungstabellen explizit festlegen.
Ergebnis muss Session-Vorbereitung erhalten und normale Navigation belegen.
Private Gespräche/Mitglieder-Chat gehören in C07; keine externen Nachrichten.
