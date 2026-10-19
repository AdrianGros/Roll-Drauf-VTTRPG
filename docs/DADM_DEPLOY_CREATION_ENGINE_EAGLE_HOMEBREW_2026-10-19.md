# DAD-M Deploy: Creation Engine = Eagle Homebrew (Symbiose)

Stand: 2026-10-19 · Branch `feat/eagle-homebrew` (Basis `76e6577`) · Vorgänger:
`docs/DADM_DISCOVER_APPLY_EAGLE_HOMEBREW_2026-10-19.md`

## Auftrag

Die **Creation Engine** behält Namen, URL (`/api/ce/authoring`) und alle Einstiege. Ihre gesamte Funktion kommt
aus Matts **Eagle Homebrew**, 1:1 und unverändert. Ersetzt werden nur die Foundry-Teile, die es in der VTT
nicht gibt. Der bisherige Engine-Code (G1) wird archiviert, soweit er nicht mit dem neuen Editor zusammenarbeitet.

## Entscheidungen (aus der Apply-Phase übernommen)

| Frage | Umsetzung |
|---|---|
| Library | persönliche Bibliothek jeder Person (`scope_kind = library`), in allen ihren Welten nutzbar |
| Welt | eine Kampagne, die die Person leitet (Besitz, DM, Co-DM), oder ihre „Persönliche Werkstatt“ |
| Sprache | Editor exakt wie bei Matt (Englisch); VTT-Hülle Deutsch. `de.json` kann später ohne Codeänderung dazukommen |
| Abschaltung alt | sofort: `/api/ce/authoring` zeigt Eagle Homebrew, Advanced Studio und Sandbox sind weg |
| Regelversion | `modern` (2024), passend zum SRD-5.2.1-Regelwerk der VTT |

## Umsetzung

### Matts Code
- `vendor/eagle-homebrew/`: Checkout am Pin `frontend/eagle-homebrew-host/eagle-homebrew.pin`
  (`518b2f9c24c3b0e6e630ecc51dc176c9bdcf1113`), nicht eingecheckt und nie lokal geändert. `tools/fetch-vendor.sh`
  prüft SHA und Sauberkeit.

### Ersatz der Foundry-Teile (`frontend/eagle-homebrew-host/`)
| Foundry | VTT-Ersatz |
|---|---|
| ApplicationV2-Fenster, `data-action`, Render-Zyklus | `src/foundry-shim.ts`: neutraler Rahmen, rechts angedockt (Seite rückt nach links, wie neben der Seitenleiste), an der Titelleiste verschiebbar, auf Handys volle Breite |
| `fields.create*`, Multi-Select, Document-Tags | gleiche DOM-Struktur; Picker listet Welt- und Library-Dokumente, UUID-Einfügen bleibt |
| `game.i18n`, `ui.notifications`, `CONFIG.DND5E`, `Trait.getBaseItem` | Matts `en.json`; Toasts; Kataloge und Basis-Gegenstände aus dnd5e 5.3.3 generiert (`data/`, MIT-Hinweis in `data/LICENSE-dnd5e.txt`) |
| Welt-Auswahl beim Foundry-Login | Auswahlfeld „Welt“ |
| Flight-Control-Hub „öffnen“ | Button „Neu erstellen“ |
| Seitenleiste + Kontextmenü „Edit with Eagle Homebrew“ | Verzeichnis „Inhalte dieser Welt“ / „Meine Bibliothek“ mit „Edit with Eagle Homebrew“ und „Löschen“ (mit Rückfrage) |
| `module.ts` (`prepareEdit`, `resolveActorMember`, `readPackState`) | `src/entry.ts`, `src/vtt-context.ts`: gleiche Logik über Matts `core/` (Paar-Retrofit, Pair-Flags) |

### Server (`vtt/creation_engine/`)
- `routes.py`: Flight-Control-Vertrag unter `POST /api/ce/authoring/request` (`document.create`,
  `document.update`, `compendium.import`); Fehler wie Flight Control als `{ok:false, reason, detail}`.
  Lesend: `worlds`, `index`, `document`, `documents`; `DELETE document`. `CE_AUTHORING` wirkt pro Anfrage.
- `documents.py`: Foundry-UUIDs, Pack-Namen, Update-Semantik (Wert pro Pfad wird ersetzt, `-=` löscht,
  `_id`/`type` unveränderlich), max. 50 Pfade, JSON-Prüfung, max. 1 MiB je Dokument, 5000 je Library/Welt.
- `models.py` + `migrations/migration_m82_creation_engine_eagle_homebrew.sql`: Tabelle `ce_eagle_documents`
  (additiv; in Prod legt `AUTO_CREATE_SCHEMA=true` sie beim Start an).
- `capability.py`: `authoring_available` für `/api/dashboard/capabilities` und `creation-engine-nav.js`.
- `canonical.py`, `errors.py` bleiben (Regelwerk-Abhängigkeit).

### Abhängigkeiten umgehängt
| Stelle | Vorher | Jetzt |
|---|---|---|
| `vtt/__init__.py` | G1-Transporte + Legacy-Host bei `CE_*`-Flags | Eagle-Blueprint immer registriert |
| `vtt/config.py` | 4 Flags | nur `CE_AUTHORING` |
| `vtt/ce_compat.py` | Laufzeit-Projektion | gleiche Schnittstelle, liefert `None` |
| `vtt/socket_handlers.py` (Token anlegen/ändern) | Engine-Zweige | fester Legacy-Pfad (in Prod schon bisher aktiv) |
| `vtt/campaigns/routes.py` (Kampf-HP) | Engine-Zweig | `combat_service.adjust_hp` |
| `vtt/combat/traps.py` | Engine-Sperre | entfällt |
| `vtt/characters/dnd5e_portable.py` | G1-Compiler für `homebrew_origin` | eigener Strict-Validator; `homebrew_origin` → 409 ohne Schreiben |
| `vtt/endpoints/dashboard_home.py` | `transports.common.authoring_available` | `capability.authoring_available`; `Vary` ohne `X-CE-View-As` |
| `vtt/static/js/creation-engine-nav.js` | Tooltip G1 | Tooltip Eagle Homebrew; Ziel unverändert |
| `infra/docker/Dockerfile` | nur Python | zusätzliche Stufe `creation-engine` (Node 22) baut das Bundle |
| `requirements.txt` | `hypothesis` | entfernt (nur G1-Tests) |
| `.dockerignore`, `.gitignore` | – | `archive/`, `vendor/`, `node_modules`, gebautes Bundle |

Archiv mit vollständiger Liste und Wiederherstellungsweg: `archive/creation-engine-g1/README.md`.

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| Matts eigene Suite (`vitest`, Node 22) | 324/324 grün |
| Typecheck Host + Matts `v13` gegen die Ersatzschicht (`npm run typecheck`) | sauber |
| `tests/test_creation_engine_eagle.py` (Vertrag, Rechte, Grenzen, Seite, Flag) | grün |
| `tests/test_creation_engine_eagle_browser.py` (Chromium, echter Server, echter Login): anlegen mit Attack-Activity, Bearbeiten über das Verzeichnis, Retrofit eines Welt-Dokuments ohne Library (`compendium.import`), Löschen mit Rückfrage, Spieler-Rechte, Handybreite 390 px | 3/3 grün, keine JS-Fehler |
| Spike-E2E (alle 18 Editoren, ohne Server) | 18/18, keine Konsolenfehler |
| Produktions-Image `infra/docker/Dockerfile` | baut; Bundle aus frischem GitHub-Clone am Pin; App-Routen und Bundle per Rauchtest erreichbar |
| Volle Suite vorher/nachher | keine neuen Fehler, siehe „Suite-Vergleich“ |

## Suite-Vergleich

Gleiches Image (Python 3.12, `requirements.txt`, Chromium), gleiche Maschine, 2026-10-19.

| Lauf | bestanden | fehlgeschlagen | Fehler | übersprungen |
|---|---|---|---|---|
| vorher (`76e6577`, unverändert) | 1440 | 62 | 20 | 385 |
| nachher (`feat/eagle-homebrew`) | 945 | 61 | 20 | 0 |

- Nach Testnamen verglichen: **kein Test ist neu rot.** Der einzige Unterschied ist
  `test_dnd5e_portable.py::test_homebrew_import_does_not_bypass_view_as_or_current_suspension`, der schon vorher
  rot war und mit dem G1-Teil archiviert ist (Ursache: die Route antwortet gesperrten Konten mit 404 vor dem
  Importer; der Nachfolgetest prüft genau das).
- Weniger bestandene und keine übersprungenen Tests, weil `tests/creation_engine/` (G1, inkl. der ohne
  `CE_TEST_DATABASE_URL` übersprungenen Postgres-Tests) im Archiv liegt.
- Die 81 vorbestehenden roten Tests (u. a. Navigations- und Balu-Browsertests, die im Testaufbau zur Login-Seite
  umgeleitet werden) sind unabhängig von dieser Änderung und hier nicht behoben.

## Deploy-Hinweise

1. `migrations/migration_m82_creation_engine_eagle_homebrew.sql` wird von `*.sql` in `.gitignore` erfasst und
   muss wie die bisherigen Migrationen mit `git add -f` eingecheckt werden.
2. Der Image-Build braucht Netz zu GitHub (Matts Repo) und zur npm-Registry.
3. Prod hat `CE_AUTHORING=true`: Nach dem Deploy zeigt die Creation Engine sofort Eagle Homebrew.
   `CE_RUNTIME`, `CE_SHADOW`, `CE_LEGACY_ADAPTER` in der Prod-`.env` werden ignoriert und können entfernt werden.
4. Die G1-Tabellen bleiben unverändert (9 Workspaces, 3 Drafts). Ein Löschen wäre ein eigener, späterer Schritt.

## Offen

- Lizenz bzw. schriftliche Freigabe von Matt (bis dahin wird sein Code nur per Pin geholt, nicht eingecheckt).
- Flight-Control-Vertragsdoku von Matt zum Abgleich der `document.update`-Semantik.
- Paritäts-Snapshot (`game.model`, `CONFIG.DND5E` nach `setup`) aus Matts Forge-Welt (Makro im Apply-Dokument).
- Verbrauch der Inhalte (H6): Species/Klassen im SRD-Ersteller, NPCs/Roll-Tables am Spieltisch; Nachfolger der
  archivierten Rasse-in-Charakterbogen-Übergabe.
- Encounter-Mitglieder aus fremden Kompendien (Foundry: `dnd5e.monsters`) gibt es in der VTT noch nicht;
  auswählbar sind Welt- und Library-Actors.

## Deploy-Protokoll (2026-10-19)

- Live-Container vorher mit `76e6577` verglichen: zwei nicht committete Hotfixes liefen in Produktion
  (`vtt/auth/routes.py` Discord-OAuth-State, `vtt/static/js/book-scene.js` Zeile 1781). Beide sind in `fd76ec8`
  enthalten, inklusive `tests/test_discord_only_login_guild_access_gate.py`. Die im Container liegenden,
  nicht eingebundenen Kalender-Dateien sind nicht übernommen (laufende Arbeit im Haupt-Checkout).
- Browser-E2E zusätzlich gegen PostgreSQL 16 mit parallelen Anfragen: 6/6 grün.
- Sicherungen: `/srv/migration/2026-10-07/setup/db-pre-eagle-homebrew-20261019.sql.gz` (pg_dump, 88 Tabellen),
  `/srv/migration/2026-10-07/setup/production.compose.json.bak-pre-eagle-homebrew-20261019`.
- Image `roll-drauf-vtt-app:eagle-fd76ec8` (Commit `fd76ec8`) in `production.compose.json` eingetragen,
  `docker compose -p migration-production -f /srv/migration/2026-10-07/setup/production.compose.json up -d --no-deps app`.
- Nach dem Start: Gunicorn ohne Fehler, Tabelle `ce_eagle_documents` angelegt, G1-Tabellen unverändert;
  öffentlich `/api/ce/authoring` 302 (ohne Login), Bundle 200, Editor-API 401 ohne Login, `/login.html` 200.
- Rollback: Sicherung der Compose-Datei zurückkopieren und denselben `up -d --no-deps app`-Befehl ausführen
  (altes Image `roll-drauf-vtt-app:regelwerk-76e6577-hf`). Die neue Tabelle stört das alte Image nicht.
- Offen: Prüfung mit echtem Konto im Browser durch die Projektleitung.
