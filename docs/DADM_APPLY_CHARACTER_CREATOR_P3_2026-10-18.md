# DAD-M Apply – Character Creator P3: Entwurfs-API, Finalisieren, Quellenmodell

Stand 2026-10-18, Branch `feat/creation-engine-g1`. Matrixpunkte 10, 14, 45.

## Ergebnis

- **Neue Tabelle `srd_creator_drafts`** (Modell `vtt/models/srd_creator_draft.py`): Besitzer, Status `draft | finalized | discarded`, `version` (optimistische Sperre), Schritt, Name, Zustand (JSON), gepinnte Quellen, `character_id` (eindeutig). Entsteht auf Umgebungen mit `AUTO_CREATE_SCHEMA=true` automatisch (so auch live), reine Neuanlage, keine Änderung bestehender Tabellen.
- **API** `/api/srd-creator` (Blueprint `vtt/characters/srd_creator.py`, JWT + CSRF wie die Charakter-Routen):
  - `GET /meta`, `GET /creator-data`
  - `POST /evaluate` (zustandslos, nur Anzeige)
  - `GET|POST /drafts`, `GET|PUT|DELETE /drafts/<id>`
  - `POST /drafts/<id>/finalize`
  - `GET /characters/<id>` (gespeicherter SRD-Block + frische Auswertung + `sourceStatus`)
- **Serverseitig statt Client-Vertrauen:** Der Client schickt nur Auswahlen (`state`). `sanitize_state` prüft Struktur, Größe (100 KB), Tiefe, Feldnamen und lehnt unbekannte Felder ab; die Regelprüfung macht `creator_rules.evaluate`. Abgeleitete Werte (TP, RK, Attribute, Stufe) kommen beim Finalisieren ausschließlich aus der Serverauswertung, nie aus dem Request.
- **Entwürfe dürfen unvollständig oder regelwidrig gespeichert werden** (Befunde werden gemeldet). **Finalisieren** verlangt `complete` (keine Fehler, nichts offen) und einen Namen, sonst `422 draft_incomplete` mit den Blockern.
- **Genau ein Charakter pro Entwurf:** Finalisieren legt den Charakter an und setzt den Entwurf in derselben Transaktion bedingt (`status='draft' AND version=…`) auf `finalized`; Wiederholung liefert denselben Charakter (`alreadyFinalized`), parallele Ausführung unterliegt der Versionssperre.
- **Quellen-/Paketmodell** (`vtt/rules_content/creator_sources.py`): registrierte Quellen (heute nur `srd-5.2.1-de`, CC-BY-4.0), Pflicht-SRD, beim Finalisieren gepinnt als `{id, kind, version, license, digest}`. `sourceStatus` meldet `drifted`, wenn sich Paketversion oder -Digest später ändern. Weitere Paketarten (Homebrew, lizenziert) docken hier an.
- **Charakter-Datenmodell:** `character_data = {system_id: "srd_5_2_1_de", system_version: 1, srd: {schema, sources, draftId, finalizedAt, state, derived}}`. Spalten (Name, Spezies, Klasse, Hintergrund, Stufe, XP, RK, TP, Attribute, Übungsbonus) werden aus der Auswertung geschrieben, damit Karte, Initiative und andere Verbraucher unverändert funktionieren. Mehrklassig: Klassenname z. B. „Kämpfer 3 / Magier 2“.
- **Schutz in der allgemeinen Charakter-API:** SRD-Charaktere können dort weder gefälscht (`character_data` mit `system_id`/`srd`) noch in abgeleiteten Feldern überschrieben werden (`409 srd_character_managed`); Name, aktuelle TP, XP u. Ä. bleiben änderbar. Roll-Drauf-Light-Ersteller und Import sind unberührt (Test).

## Tests

`tests/test_srd_creator_api.py`: 26 Tests (Struktur-/Größenprüfung, Quellenmodell, Besitzer-Isolation, Versionskonflikte, Entwurfslimit 25, Finalisieren: unvollständig/Name/Regelfehler/ein Charakter/idempotent/Überschreibungen, keine Client-Werte, Fälschungsschutz, Drift). Gesamtlauf der Charakter- und Regelwerk-Tests: 374 grün; die 5 Fehlschläge und 6 Fehler gehören zu Browser-Tests (kein Browser im Image) und einem Homebrew-Import-Test, der auch auf dem unveränderten HEAD fehlschlägt.

## Bekannte Lücken

- Kein Verlauf/Respec (P10), kein Stufenaufstieg (P8): `srd.state` ist die Grundlage dafür.
- Lesezugriff auf `/characters/<id>` folgt der bestehenden Regel (Besitzer oder aktives Kampagnenmitglied); Geheimhaltung einzelner Felder (z. B. Notizen) kommt mit P11.
- Live-Auslieferung: Image `regelwerk-2415d0a` ist gebaut, der Neustart des App-Containers wurde von der Berechtigungsprüfung der Sitzung abgelehnt und ist offen.
