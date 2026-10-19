# Archiv: Creation Engine G1

Archiviert am 2026-10-19 (Branch `feat/eagle-homebrew`). Die **Creation Engine** behält ihren Namen und ihre
Einstiege (`/api/ce/authoring`, Menüpunkte „Creation Engine“). Ihre Funktion kommt jetzt vollständig aus
Matts **Eagle Homebrew** (`vendor/eagle-homebrew`, Pin in `frontend/eagle-homebrew-host/eagle-homebrew.pin`).
Siehe `docs/DADM_DEPLOY_CREATION_ENGINE_EAGLE_HOMEBREW_2026-10-19.md`.

Dieser Ordner wird weder importiert noch getestet (`pytest.ini`: `testpaths = tests`) noch ins Image kopiert
(`.dockerignore`: `archive/`). Die Pfade darunter spiegeln die ursprünglichen Repo-Pfade.

## Was hier liegt

| Archivierter Pfad | Was es war |
|---|---|
| `vtt/creation_engine/` (ohne `canonical.py`, `errors.py`) | G1-Kernel: Typen, Evaluator, Kommando-Kernel, Content-Store, Policies, Interview-Compiler (Klasse, Rasse, Zauber), Homebrew-Sandbox, Advanced Studio, Legacy-Adapter, HTTP-/Socket-Transporte |
| `vtt/templates/creation-engine.html`, `creation-advanced.html` | alte Editor-Seiten |
| `vtt/static/js/creation-engine.js`, `creation-advanced.js`, `ce-schema-form.js` | alter Editor-Client |
| `vtt/static/css/creation-engine.css`, `creation-advanced.css` | alte Editor-Styles |
| `tests/creation_engine/` | 36 G1-Testdateien (inkl. Hypothesis-Property-Tests) |
| `tests/test_homebrew_origin_sheet.py` | Rassen-Übergabe in den Charakterbogen |
| `tests/test_dnd5e_portable.py` | Ursprungsfassung inkl. `homebrew_origin`-Fällen (die Plain-Fälle laufen weiter in `tests/`) |
| `tools/ce_homebrew_check.py` | G1-Prüfskript |

## Was bewusst nicht archiviert ist

| Bleibt | Grund |
|---|---|
| `vtt/creation_engine/canonical.py`, `errors.py` | RFC-8785-JSON und Fehlerklassen, genutzt von `vtt/rules_content/validator.py` und `generator.py` (Regelwerk) |
| `vtt/ce_compat.py` | gleiche Schnittstelle, liefert jetzt immer `None`; Aufrufer in `models/character.py`, `models/token_state.py`, `characters/routes.py` bleiben unverändert |
| `tools/ce_test_postgres.py` + pytest-Marker `postgres` | wird auch von Nicht-CE-Tests genutzt (Sitzungskalender) |
| `migrations/migration_m73…m80_creation_engine_*.sql` | Schema-Historie; bereits angewendet |
| `docs/creation-engine/` | Spezifikation und Errata als Referenz |
| Tabellen `ce_*` in der Datenbank | **nicht gelöscht**. Stand Produktion 2026-10-19: 9 Workspaces, 3 Drafts, 16 Draft-Versionen, sonst 0 Zeilen |

## Was mit G1 wegfällt

- Interview-Editor für Klasse, Rasse, Zauber mit Entwurfs-Historie, Vorlagen und Revisionen → ersetzt durch Eagle Homebrew (18 Objektarten).
- Homebrew-Sandbox und Advanced Studio (`/api/ce/authoring/advanced`).
- Rasse-in-Charakterbogen-Übergabe und `homebrew_origin` im 5E-Charakterexport/-import. Alt-Exporte mit
  `homebrew_origin` werden mit HTTP 409 abgelehnt, ohne zu schreiben. Die Anzeige im Charakterbogen
  (`renderHomebrewOrigin`) bleibt verdeckt, weil kein Charakter mehr einen Ursprung liefert.
  Nachfolger: Species aus Eagle Homebrew im SRD-Ersteller (Arbeitspaket H6).
- Laufzeit-Projektion von Charakteren/Tokens (`ce_legacy`), „View As“ (`X-CE-View-As`) und die Socket-Events
  `ce:receipt`/`ce:error`. In Produktion gab es keine Repräsentation, das Verhalten am Spieltisch ist unverändert.
- Config-Flags `CE_RUNTIME`, `CE_SHADOW`, `CE_LEGACY_ADAPTER` (werden ignoriert, können aus `.env` entfernt werden).
  `CE_AUTHORING` schaltet jetzt den Eagle-Homebrew-Editor.
- Python-Abhängigkeit `hypothesis` (nur von G1-Tests genutzt) aus `requirements.txt` entfernt.

## Wiederherstellen

1. Pfade aus diesem Ordner an ihre ursprüngliche Stelle zurück verschieben (`git mv archive/creation-engine-g1/<pfad> <pfad>`).
2. In `vtt/__init__.py` die G1-Registrierung (`register_creation_engine`, `install_creation_engine_host`) und in
   `vtt/config.py` die Flags wieder einsetzen; `vtt/ce_compat.py`, `vtt/characters/dnd5e_portable.py`,
   `vtt/socket_handlers.py`, `vtt/campaigns/routes.py`, `vtt/combat/traps.py` aus dem Commit vor der
   Archivierung (`76e6577`) übernehmen; `hypothesis` wieder in `requirements.txt`.
3. Die Route `/api/ce/authoring` würde dann doppelt belegt: zuerst den Eagle-Blueprint abschalten.
