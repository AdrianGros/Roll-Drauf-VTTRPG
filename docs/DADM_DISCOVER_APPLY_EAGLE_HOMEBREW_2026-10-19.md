# DAD-M Discover + Apply: Eagle Homebrew als Standard-Homebrew-Editor der VTT

Stand: 2026-10-19 · Branch `feat/eagle-homebrew` (Basis `76e6577`, = laufendes Produktions-Image `regelwerk-76e6577-hf`)

## 1. Auftrag

Matts Foundry-Modul **Eagle Homebrew** (https://github.com/MattTheEagle/EagleHomebrew, Stand `518b2f9`, v0.0.3)
wird **1:1** in die VTT übernommen und löst die Erstellungs-Oberfläche der bisherigen Creation Engine als
Standard für Homebrew ab. Vorgabe der Projektleitung: kein neues UI-Design. Ersetzt werden nur die UI-Elemente,
die ohne Foundry wegfallen. Matts Designentscheidungen werden nicht verändert.

## 2. Discover: Ist-Zustand

### 2.1 Eagle Homebrew (Matt)

| Teil | Umfang | Foundry-abhängig? |
|---|---|---|
| `core/` (27 Module) | Katalog der 18 Objektarten, Feldmodelle, Activities, Effects, Advancements, NPC-Aktionen, Encounter/Group, Vehicle, Roll-Table, Paar-Erstellung, verlustfreie Edit-Projektion | **Nein**, reines TS |
| `v13/homebrew-application.ts` | Der gesamte Editor (5466 Zeilen, ApplicationV2) | Nur über eine kleine, klar abgegrenzte Oberfläche (2.3) |
| `v13/module.ts`, `edit-hooks.ts`, `create-pair.ts` | Foundry-Verdrahtung: Hooks, Flight Control, `game.*`, Kontextmenüs | Ja, wird durch VTT-Adapter ersetzt |
| Tests | 28 Dateien, **324 Tests, alle grün** (verifiziert 2026-10-19, Node 22) | – |

Datenformat: native dnd5e-Dokumente (`system.activities.<id>`, eingebettete `effects`, `system.advancement`,
`items`, `results`), verifiziert gegen **dnd5e 5.3.3** unter Regelversion 2024.

### 2.2 VTT Creation Engine (heute)

- Erstellungs-Oberfläche: `/api/ce/authoring` (Interview-Editor für nur 3 Arten: Klasse, Rasse, Zauber),
  Advanced Studio, Homebrew-Sandbox, Rassen-Sheets. Templates `creation-engine.html`, `creation-advanced.html`;
  JS `creation-engine.js`, `creation-advanced.js`, `ce-schema-form.js`, `creation-engine-nav.js`.
- Einstiege: `play.html` (Ribbon + App-Menü), `book-scene.js` (Dashboard/TOC), `dashboard.html`.
- **Produktionsdaten (2026-10-19):** 9 Workspaces, 3 Drafts, 16 Draft-Versionen; 0 Instanzen, 0 Sandboxes,
  0 Homebrew-Events. Es wird also faktisch keine Homebrew-Arbeit abgelöst.
- Der CE-**Kernel** wird außerhalb der Erstellung genutzt (`ce_compat.py`, `socket_handlers.py`,
  `campaigns/routes.py`, `combat/traps.py`, `rules_content/*`, `characters/dnd5e_portable.py`) und bleibt
  vorerst. Nicht Teil dieses Auftrags.
- `rules_content/creator_sources.py` sieht `"homebrew"` als Quellenart für den SRD-Ersteller bereits vor.
- Build: Python-only-Dockerfile, keine Node-Stufe; Frontend ist Vanilla-JS.

### 2.3 Foundry-Oberfläche, die der Editor tatsächlich berührt (gemessen)

| Foundry-Element | Verwendung |
|---|---|
| `foundry.applications.api.ApplicationV2` | Fenster, `render()`, `_renderHTML`/`_replaceHTML`, `data-action`-Verteilung (66 Actions) |
| `foundry.applications.fields.*` | `createFormGroup` (51×), `createTextInput` (22×), `createNumberInput` (18×), `createSelectInput` (12×), `createCheckboxInput` (6×), `createMultiSelectInput` (4×) |
| `elements.HTMLDocumentTagsElement` | Dokument-Picker (Actor/Item, einzeln/mehrfach) |
| `CONFIG.DND5E.*` | 55 Kataloge (Schadensarten, Waffen-IDs, Eigenschaften, Einrichtungen, …) |
| `dnd5e.documents.Trait.getBaseItem` | Namen der Basis-Gegenstände |
| `game.i18n`, `game.settings`, `game.user`, `ui.notifications`, `foundry.utils` | Texte, Regelversion, GM-Check, Meldungen, IDs |
| Flight Control (Server) | genau 3 Anfragen: `document.create`, `document.update` (≤ 50 Pfade), `compendium.import` |

## 3. Spike: Machbarkeit belegt

`frontend/eagle-homebrew-host/` lässt Matts **unveränderte** `homebrew-application.ts` und `core/` im Browser
laufen. Ergebnis (Chromium/Playwright, `tools/spike-e2e.mjs`):

- esbuild bündelt Matts Editor gegen die Ersatzschicht **ohne Fehler** (750 KB).
- **Alle 18 Editoren** rendern mit ihren Abschnitten und Bausteinen, **0 Konsolenfehler**.
- **Create** einer Waffe mit Attack-Activity erzeugt das Paar `Compendium.world.eagle-weapons-2024.Item.<id>` +
  `Item.<id>` mit gleicher ID, gegenseitigen `eagle-homebrew.pair`-Flags, `system.source.rules = "2024"` und
  nativer `attack`-Activity.
- Namenskollision ergibt „Flammenklinge (Duplicate)“, wie in Matts R5/N14c.
- Basis-Waffenliste filtert nach Waffentyp wie in Foundry (alle 87 Katalog-IDs aufgelöst).
- `CONFIG.DND5E` (136 Kataloge) wird automatisch aus dnd5e 5.3.3 erzeugt (`tools/extract-dnd5e-config.mjs`),
  Basis-Gegenstände aus dnd5es eigenen SRD-Kompendien (`tools/extract_base_items.py`, 1568 Einträge).
- Typecheck der Host-Schicht sauber.

## 4. Apply: Zielbild

### 4.1 Grundsatz

Matts Repo ist die **einzige Quelle** für Editor und Logik. Die VTT ersetzt nur (a) die Foundry-UI-Elemente aus
2.3 und (b) die Foundry/Flight-Control-Backends. Eine Änderung an Matts Editor passiert in Matts Repo und kommt
über ein Pin-Update in die VTT. Wir forken nicht und schreiben nichts um.

```
vendor/eagle-homebrew/              Matts Repo, gepinnter Commit, wird nie lokal editiert
frontend/eagle-homebrew-host/       Ersatzschicht (nur wegfallende Foundry-Elemente) + VTT-Kontext
  src/foundry-shim.ts               ApplicationV2, fields, <multi-select>, <document-tags>, i18n, Toasts, CONFIG
  src/vtt-context.ts                HomebrewWindowContext + Flight-Control-Vertrag -> VTT-API
  src/entry.ts                      öffnet Editor (neu / Bearbeiten), entspricht v13/module.ts
  data/                             generierte dnd5e-5.3.3-Kataloge (gepinnt)
vtt/homebrew/                       Flask-Blueprint: Vertrag + Speicherung
vtt/templates/homebrew.html         Seite, die das Fenster trägt
infra/docker/Dockerfile             zusätzliche Node-Stufe baut das Bundle
```

### 4.2 Ersetzte UI-Elemente (abschließende Liste)

| Fällt weg (Foundry) | Ersatz in der VTT | Verhalten bleibt |
|---|---|---|
| ApplicationV2-Fenster | Fensterrahmen mit Titel + Schließen, 520×700, skalierbar | Matts `DEFAULT_OPTIONS` werden 1:1 ausgewertet |
| `fields.create*` | gleiche DOM-Struktur (`.form-group > label + .form-fields`) | Matts Formulare unverändert |
| Multi-Select | Tag-Liste + Auswahl, `.value` ist `string[]`, `change`-Event | wie Foundry |
| Document-Tags (Drag aus Seitenleiste) | Suchliste der eigenen Library-/Welt-Dokumente; UUID einfügen geht weiter | Wert bleibt UUID/UUID-Liste |
| `ui.notifications` | Toast-Stapel | gleiche Stufen info/warn/error |
| „Edit with Eagle Homebrew“ in Blattkopf/Kontextmenü | Button „Mit Eagle Homebrew bearbeiten“ an Homebrew-Einträgen der VTT-Listen | gleicher Edit-Flow (Retrofit, Library zuerst) |
| Flight-Control-Hub-Eintrag | Menüeintrag „Homebrew“ an den heutigen Creation-Engine-Einstiegen | – |

### 4.3 Server-Vertrag (Flight Control, nachgebaut)

`POST /api/homebrew/request` mit `{type, payload}` → `{ok:true, value}` | `{ok:false, reason, detail}`,
Fehlergründe exakt wie Flight Control (`invalid-payload`, `not-permitted`, `conflict`, …).

| type | Semantik |
|---|---|
| `document.create` | `{target:{pack}|{world}, id, data}`, idempotent pro ID → `{created, uuid}` |
| `document.update` | `{uuid, changes}`, Punkt-Pfade, `-=`-Löschung, max. 50 Pfade, JSON-Prüfung → `{changed}` |
| `compendium.import` | Welt-Dokument mit gleicher ID in Library-Pack kopieren (Pair-Retrofit) |

Lesend: `GET /api/homebrew/packs/<collection>/index`, `GET /api/homebrew/documents/<uuid>`,
`GET /api/homebrew/documents?type=Actor|Item` (Picker).

Speicherung: Tabelle `homebrew_documents` (`uuid`, `scope_kind` library|world, `scope_id`, `pack`,
`document_name`, `type`, `name`, `source` JSONB, `revision`, Zeitstempel). UUIDs bleiben im Foundry-Format,
damit Matts Kern unverändert rechnet. Rechte: Library = Besitzer; Welt = Spielleitung der Kampagne
(entspricht Matts GM/Assistant-Gate).

### 4.4 Arbeitspakete

| WP | Inhalt | Abnahme |
|---|---|---|
| **H0** | Lizenz/Freigabe von Matt; Repo als `vendor/` (Subtree, gepinnt) einchecken | Lizenzdatei oder schriftliche Freigabe liegt vor |
| **H1** | Flask-Blueprint + Migration `homebrew_documents`, Vertrag aus 4.3, pytest | Vertragstests inkl. 50-Pfade-Grenze, Idempotenz, Rechte |
| **H2** | `entry.ts` + echte REST-Anbindung, Seite `homebrew.html`, Docker-Node-Stufe | Spike-E2E läuft gegen echten Server |
| **H3** | Edit-Flow (Retrofit, `executeSave`) + Einstiege an Homebrew-Listen | Bearbeiten erhält unbekannte Felder (Matts M19-Kriterien) |
| **H4** | Parität: `CONFIG.DND5E`/`game.model` mit Live-Dump aus Matts Forge-Welt abgleichen; Matts Forge-Checklisten M7–M21 in der VTT nachspielen | alle 18 Arten; Abweichungsliste leer |
| **H5** | Alte Erstellungs-Oberfläche abschalten: Authoring/Advanced/Sandbox/Sheets-Routen + Templates + JS; Einstiege auf Homebrew umbiegen; 3 Prod-Drafts als JSON sichern | Menüs führen zu Eagle Homebrew; Kernel-Tests grün |
| H6 (folgt) | Verbrauch: Homebrew als Quelle im SRD-Ersteller (`creator_sources` „homebrew“), Kompendium, Spieltisch (NPC-Token, Roll-Tables) | eigener Discover |

Deutsche Oberfläche: Matts i18n-Struktur erlaubt eine zusätzliche `de.json` ohne Codeänderung. dnd5e selbst
liefert keine deutschen Texte mit, die Katalogtexte brauchen also eine eigene Übersetzungsquelle (siehe 6).

## 5. Risiken

| Risiko | Stufe | Umgang |
|---|---|---|
| Matts Repo hat keine Lizenz → Einbau rechtlich unklar | **hoch** | H0 blockiert das Einchecken; bis dahin nur lokaler Clone |
| Exakte `document.update`-Semantik von Flight Control für eingebettete Sammlungen (`effects`, `items`, `results`) nicht dokumentiert vorliegend | mittel | `EagleFlightControl/docs/api-contract.md` von Matt anfordern; Spike ersetzt Arrays komplett |
| `CONFIG.DND5E` zur Ladezeit ≠ nach dnd5e-`setup` | mittel | H4: Live-Dump aus Foundry vergleichen |
| `game.model`-Vorgaben (Default-Systemdaten) fehlen ohne Foundry | mittel | aus Live-Dump übernehmen (Makro unten) |
| Drift, wenn Matt weiterentwickelt | niedrig | Pin-Update + E2E bei jedem Update |
| dnd5e-Daten (MIT) und SRD-Inhalte (CC-BY-4.0) | niedrig | Attribution analog `attribution.txt` |

## 6. Offene Entscheidungen (Projektleitung)

1. **Welt/Library in der VTT:** Vorschlag: Library = persönliche Homebrew-Bibliothek der Spielleitung,
   Welt = Kampagne. Offen ist, was „Welt“ bedeutet, wenn der Editor außerhalb einer Kampagne geöffnet wird.
2. **Sprache:** zuerst Englisch exakt wie Matt, oder sofort mit deutscher `de.json` (für die Katalogtexte
   braucht es dann eine Übersetzungsquelle)?
3. **Abschaltung (H5):** alte Erstellungs-Oberfläche sofort mit H2 abschalten oder erst nach H4-Parität?

## 7. Bitte an Matt

1. Lizenz ins Repo (oder schriftliche Freigabe für den Einbau in die VTT).
2. `EagleFlightControl/docs/api-contract.md` (Abschnitt 4 „Documents“) für `document.update`/`compendium.import`.
3. Einmal in der Forge-Welt (Foundry v13, dnd5e 5.3.3, Regelversion 2024) als GM-Makro ausführen:

```js
const seen = new WeakSet();
const clean = (v) => {
  if (typeof v === "function" || typeof v === "symbol") return undefined;
  if (!v || typeof v !== "object") return v;
  if (seen.has(v)) return undefined;
  seen.add(v);
  const out = v instanceof Set ? [...v].map(clean) : Array.isArray(v) ? v.map(clean)
    : Object.fromEntries(Object.keys(v).map((k) => { try { return [k, clean(v[k])]; } catch { return [k, undefined]; } }));
  seen.delete(v);
  return out;
};
saveDataToFile(JSON.stringify(clean({ foundry: game.version, dnd5e: game.system.version,
  rulesVersion: game.settings.get("dnd5e", "rulesVersion"), model: game.model, config: CONFIG.DND5E })),
  "application/json", "eagle-vtt-parity-snapshot.json");
```

## 8. Übergabe an Deploy

Nach Klärung von H0 und Entscheidungen 6.1–6.3: H1 → H2 → H3 → H4 → H5 in dieser Reihenfolge, je mit eigenem
Deploy-Protokoll. Der Spike (`npm run build:spike && npm run e2e:spike`) bleibt als Regressionstest erhalten.
