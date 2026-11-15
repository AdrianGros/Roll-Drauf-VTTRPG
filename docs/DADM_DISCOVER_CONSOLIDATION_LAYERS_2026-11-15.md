# Discover: Konsolidierung und DM-Token-Layer

Status: abgeschlossen; Profil standard; Aufbewahrung dauerhaft.

## Eingabe und Grenze
Owner-Auftrag 15.11.: Arbeitsstand der letzten zwei Tage konsolidieren, Nutzen der
Protokolle und Änderungs-/Abnahmestatistik erklären, Testkatalog für nächste Woche
vorbereiten, vorhandene autorisierte Änderungen committed live bereitstellen und
DM-Token-Layer samt gruppierter Auswahl ergänzen. Bestehendes Live-VTT ist bis zum
geplanten Februarstart die gemeinsame Testumgebung. Kein zweites Benutzerziel.
Keine pauschale Freigabe zurückgestellter oder supersedierter Implementierungen.

## Iststand und Inventar
- Aktive Basis: `4158a0c4be0d730881fb0b7ba2ca28a5ffd5e958`, Image
  `sha256:a7f79477d77508c6c3b113e86de258340be6e9709a121b9662e2e7eeeae5cd83`.
- Tatsächliches Compose-Projekt `migration-production`; Dateien
  `/srv/migration/2026-10-07/setup/production.compose.json` und
  `production.duck-species.override.yml`. Nur Asset-Volume, kein Source-Bindmount.
- Vollinventur: 80.855 Dateien unter vtt plus app.py und requirements.txt.
  Sechs Abweichungen: zwei obsolete `.html.orig`, generiertes Eagle-build.json,
  Eagle-Sourcemap, duckfolk-2024.json-Beispiel und requirements.txt
  (Live enthält den Testeintrag hypothesis nicht). Laufzeitcode ansonsten identisch.
  `docker diff`: keine nachträglichen Änderungen an /app.
- Zwei jüngste Protokolle: 11.11. 09:46 Charakterbau/Karteneditor und
  12.11. 18:03 Oberfläche/Karteneditor, am 13./14.11. in N01–N20/S01–S20 umgesetzt.
  Kanonisch: `docs/plans/FEEDBACK_IMPLEMENTATION_2026-11-13.json`.
- 40 Karten: 35 delivered_for_owner_acceptance, 2 existing_evidence,
  N07 scope_defined_pending_apply, S15 planned, N11 deferred_by_owner.
- Vorgängerregister: 40 VTT-Karten; C00–C10-Programm (9 Funktionspakete live,
  Integration abgeschlossen, Gesamtprüfung technisch abgeschlossen).
  Diese sind überlappende Bearbeitungsstufen, keine 91 unabhängigen Änderungen.
- Zwölf ursprüngliche menschliche A01–A12-Abnahmen: alle not_run.
- Token-Datenmodell kennt public/dm_only/owner_only; Server filtert Bootstrap,
  Snapshots und Ereignisse nach autorisiertem Tischkontext. DM-Modul wird nur nach
  autorisiertem Surface-Abruf geladen. Rechte werden nicht durch Sichtbarkeit ersetzt.
- Bestehende DM-Auswahl: Einzelklick, Auswahlrahmen und Clipboard seit 15.11.;
  vorhandene Dockreiter Seiten/Initiative/Tokens. Neuer Layerreiter fehlt.

## Abhängigkeiten, Risiken und Annahmen
- Mittel, Releaseherkunft: die sechs Abweichungen müssen vor Auslieferung
  explizit reconciled werden; benötigte generierte Artefakte versionieren,
  obsolete Backups nur im Image entfernen, requirements dem Commit angleichen.
  Kein blinder Build aus dem ursprünglichen schmutzigen Worktree.
- Mittel, Rollenschutz: bestehende serverseitige Token-Sichtbarkeit und
  Tischkontexte weiterverwenden; Negativfälle Player und Owner-im-Player-Kontext
  gehören in gezielte und Live-Prüfungen. Keine neue Berechtigungsquelle.
- Niedrig, Abnahmezahlen: technische Lieferung und menschliche Zustimmung sind
  getrennte Beobachtungen. Nicht protokollierte Zustimmung wird nicht erfunden.
- Niedrig, Altworktrees: Übersetzungsreste, Sprite-Versuche und SRD-Neuerfassung
  sind teilweise supersediert. Erhalten und inventarisieren statt ungeprüft bündeln.

## Offene Fragen und Übergabe
Kein blockierendes Produktdetail für den Layer-Slice. N07 und S15 bleiben sichtbare
separate Implementierungsaufgaben; N11 bleibt ausdrücklich zurückgestellt.
Apply definiert Layer-/Auswahlvertrag, Dateireconciliation und Test-/Releasebelege.
