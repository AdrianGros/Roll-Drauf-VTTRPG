# Deploy W02: Kartenwerkstatt-Review (Eigenassets, Pixel, Reihenfolge, Masken, Generator)

18.–19.11.2026 · DAD-M Deploy · Task W02 · Base `49e8b9944` · Contract `docs/DADM_APPLY_REVIEW_WEB_2026-11-18.md` (W02).
Status: **partial – implemented in the worktree, not run, not integrated, not deployed.** This worker had
Read/Grep/Glob/Edit/Write only. It ran no tests, no build, no catalogue generation and no git commands.
Integration, tests, commit, deploy and live verification belong to the coordinator (W04).

## Changed files (all inside W02 ownership)

- `vtt/mapmaker_document.py`: optional `assets` list (validated), path `name`, label `font`.
- `vtt/static/mapmaker/js/sha256.js` (new): synchronous SHA-256 for content-addressed IDs.
- `vtt/static/mapmaker/js/document.js`: limits, `validateAssets`, an ID lookup isolated to the document, `referencedAssetIds`, path name, label font, `materialize`/`serialize` (`referencedOnly`).
- `vtt/static/mapmaker/js/stamps.js`: `registerCustomAssets`, `showDocumentAssets`, the "Eigene Bilder" groups, and `ensureDocumentImages` now registers own images (shared by editor, DM table and Atlas snapshot).
- `vtt/static/mapmaker/js/credits.js`: credits for own images that the map actually uses (source/licence as stated by the author).
- `vtt/static/mapmaker/js/render.js`: label font family separate from style, using only the shipped faces.
- `vtt/static/mapmaker/js/brush.js`: optional clip mask. The reference is frozen at stroke start and only the fresh stroke is masked.
- `vtt/static/mapmaker/js/selection.js`: `reorderItems` (canonical in-layer order).
- `vtt/static/mapmaker/js/landmass.js`: versioned presets, preset validation, decoration from separate random streams.
- `vtt/static/mapmaker/js/landmass-dialog.js`: presets (built-in and saved), material or selected tile as output, optional mountains/forests, preview markers, budgets checked before allocation, one undo step.
- `vtt/static/mapmaker/js/asset-dialogs.js` (new): upload dialog (crop, transparent colour key, preview, rights confirmation) and pixel editor (16–256 px, pen/eraser, colour/alpha, undo/redo, unsmoothed zoom).
- `vtt/static/mapmaker/js/app.js`: own-image lifecycle (add/remove/sanitize, budgets), clip, ordering incl. the Alt+wheel session, explicit path connection, area fill, tool-context layer switch, overlays, ZIP with `referencedOnly`, API summary.
- `vtt/static/mapmaker/js/tools.js`: area gesture, Alt+wheel reordering (normal wheel/pinch zoom unchanged), PageUp/PageDown order, Alt+↑/↓ layer switch.
- `vtt/static/mapmaker/js/ui.js`: new controls, palette filters (pack/category/style/perspective), canvas thumbnails without blob URLs, crop comparison (`cropCutSides`, `fitCropToContent`).
- `vtt/static/mapmaker/index.html`, `vtt/static/mapmaker/mapmaker.css`: visible controls and dialog styles.
- `tests/test_review_maps_server.py`, `tests/test_review_maps_browser.py` (new).
- This report.

No asset files, manifests, global navigation, registries, generated UI catalogue or other worker files were changed.

## Data contract as implemented

- `assets` (optional, v1): up to 32 entries `{id:'custom:<sha256 of the PNG bytes>', label≤80, png:'data:image/png;base64,…', width, height, style∈pixel|painted|ink|other, perspective∈top|side|isometric|other, source≤200, licence≤120}`.
  - Limits: ≤4 MiB per decoded PNG, ≤12 MiB in total, ≤2048 px per side, ≤8 million pixels in total. The 50 MiB project limit and the 16 MiB Atlas limit stay in force.
  - The server decodes the PNG (single frame, declared size, `verify`/`load`) and recomputes the SHA-256. The client checks the same bounds and the hash, and decodes when the image is registered.
  - No URLs, SVG or non-PNG data are accepted. A different image always gets a new ID.
- `custom:` IDs resolve only against the document's own `assets` (client: `assetLookup`; server: `own_dims`). An image that another project already loaded into the palette is not enough.
- Old documents without `assets`, `name` or `font` normalize exactly as before (tested). Empty `assets` are omitted.
- Path `name` (optional, ≤80, dropped when empty). Label `font` ∈ `cinzel|badscript|literata` (optional). Both are handled by both validators, rendering, saving and export.

## Acceptance mapping (W02 contract)

| Point | Implementation | Evidence (prepared, not run) |
| --- | --- | --- |
| K15/K16/K19 own images, embedded per project, limits, hash ID | `validateAssets`/`custom_assets`, `addCustomAsset` checks budgets before decode/storage, upload/pixel dialogs | server: `test_invalid_own_images_are_rejected`, `test_count_byte_and_pixel_budgets`, `test_own_image_references_resolve_only_against_this_document`; browser: `test_client_validator_matches_server_bounds_and_isolation`, `test_sha256_matches_hashlib_and_webcrypto` |
| Storage chain: validator, materialize, palette, JSON/ZIP, library, Atlas/table snapshot, export, credits | `ensureDocumentImages` registers images for every load path; full assets in project file, library, draft and Atlas; ZIP has only referenced images plus credits | `test_pixel_editor_image_survives_file_bundle_draft_and_filters`, `test_table_and_atlas_snapshot_render_and_credit_embedded_images`, `test_library_roundtrip_keeps_own_images_and_counts_them_in_quota`, `test_atlas_bundle_preserves_own_images_through_the_same_validator` |
| K17 pixel editor | `PixelEditor`: 16–256 px, pen/eraser, colour/alpha, 40-step undo/redo, CSS zoom `pixelated`, saved as own stamp | pixel test (undo/redo, zoom 8× = 128 px wide and `pixelated`) |
| Upload crop and transparent colour background, no AI | `UploadDialog`: crop fields/drag, maximum side, colour key with tolerance and eyedropper, preview, rights confirmation, SVG rejected | `test_upload_crop_colour_key_and_rejections` (decodes the stored PNG pixels) |
| K18/K20 scatter visible, real area option | "Platzierung" group at the top of the stamp panel, spacing ring around the cursor, "Fläche füllen" with count preview; budget (≤400 per area, map limit, history) is checked before allocation; one undo step | `test_area_fill_is_one_step_and_refuses_over_budget_before_placing` |
| K24/K25 canonical order, buttons, wheel, coverage, layer choice | `reorderItems` + 4 buttons (single and group selection), PageUp/PageDown (+Shift), Alt+wheel only with the select tool and a selection, committed as one step per wheel pause; tile-brush coverage of all cells; `#toolLayer` in the tool context, Alt+↑/↓ | `test_object_order_buttons_keys_and_alt_wheel_are_one_step_each` (render/hit/file order, zoom unchanged), `test_layer_choice_lives_in_the_tool_context_with_keyboard` (1440/390 px) |
| K23 path name, explicit connection | `#selPathName`; `connectPathEndpoints`: same layer and material, ≤32 px, nearest endpoint pair, ≤128 points, one undo step; crossings never connect implicitly | `test_named_paths_connect_only_by_explicit_action` |
| K23 tile paths | **not offered**: the manifests contain no transition metadata (Grep for `transition|autotile|wang|terrainSet` found nothing) | input-dependent; no universal autotile claim |
| K26 style vs. font family | `label.font` with the shipped faces only (Cinzel 400/700, Bad Script, Literata); weight/slant follow the style where the face exists; no new font and no change to credits/licences | `test_label_family_is_separate_from_style_and_roundtrips`, server font tests |
| K28–K30 generator | named presets with versions (3 built-in, up to 12 of your own in localStorage, other versions shown but disabled), material or current tile as output, mountains/forests only with loaded Kenney or built-in symbols and their own random streams, preview markers, cancel/timeout/stale results unchanged, one strict undo step | `test_generator_presets_tile_output_and_seeded_decoration_are_one_undo` (reproducible decoration), existing `test_landmass_browser.py` (preflight without canvas allocation; IDs and status kept) |
| K29 mask | `#brushClip`: alpha of a lower raster layer or occupied cells of a tile layer (never the sea). The reference is copied at stroke start and only the fresh stroke is masked in the work canvas, so old pixels stay. A missing or no longer lower reference switches the mask off with a visible explanation. | `test_brush_clip_paints_only_on_reference_and_keeps_old_pixels` |
| K21 crop diagnosis | Sheet dialog: crop at true pixels, the source edges where visible content continues ("probably cut off"), and "Zusammenhängenden Inhalt erfassen" (grow, then trim transparent margins) | `test_crop_comparison_detects_cut_content_and_fits_a_clean_crop`; **no claim of a fix for specific trees** – the asset ID is still unknown |
| "Filter" | Palette filters for display style (own images and pixel art) and perspective (own images); colour-key filter on upload | in the pixel test |

## Proposed checks (coordinator)

```
python3 -m pytest -q tests/test_review_maps_server.py tests/test_mapmaker_tiles_server.py tests/test_mapmaker_library.py tests/test_feedback_b05_schema.py tests/test_feedback_b06_schema.py
python3 -m pytest -q tests/test_review_maps_browser.py tests/test_mapmaker_browser.py tests/test_c04_mapmaker_browser.py tests/test_feedback_b06_browser.py tests/test_landmass_browser.py tests/test_landmass.py tests/test_mapmaker_sheet_slicer.py
python3 -m pytest -q tests/test_mapmaker_library_browser.py tests/test_atlas_browser.py   # table/library/Atlas regressions
node --check vtt/static/mapmaker/js/*.js   # syntax gate for modules (or the existing JS lint)
python3 tools/i18n/build_catalog.py --check   # after adding the W02 label fragment below
```

Checks actually run: **none** (no shell in this role).

## Known gaps and risks (honest)

- Not run, so any syntax or runtime errors are still unknown. Most exposed: ESM imports between `app.js`, `ui.js`, `asset-dialogs.js` and `stamps.js`; Playwright wheel events with Alt in headless Chromium; exact layer/option texts in the tests (German UI).
- The DE/EN labels exist only as German sources plus the fragment below. They are English only after the coordinator adds them, e.g. to `tools/i18n/tasks/review-maps-w02.json`, and regenerates the catalogue. Without that, the UI falls back to the German source text.
- Atlas: 12 MiB of own images as base64 plus the map PNG can exceed the existing 16 MiB Atlas limit (a 413 message is shown); the limit was deliberately not changed.
- The DM table description shortens credits to 600 characters (`creditSummary`); the PNG still carries the full credits including own images.
- The pixel editor only creates new images (editing an existing own image is not implemented). Upload accepts PNG, JPEG and WebP up to 32 MiB and 8192 px, re-encoded as PNG; there is no AI cut-out.
- Generator layers stay at the top of the layer stack (existing behaviour); decoration gets its own symbol layer above them.
- Generator presets are stored only in the browser (localStorage), not on the server.
- Tile paths/autotiling are not offered (no transition data).
- The Alt+wheel binding is optional; touch has the buttons instead.

## Integration notes

- No route, registry, navigation or schema migration. Server change: the validator only (stricter only for `custom:`/`assets`/`font`/`name`).
- Live check after deploy: Kartenwerkstatt → Symbole → "Pixelbild zeichnen …" / "Eigenes Bild hochladen …"
  1. Place the image, save to the library and reopen.
  2. Take it into a campaign via the DM table library and check the preview.
  3. Copy it into the Atlas.
  4. Export the ZIP and check that CREDITS.txt lists the own image.
  5. Brush → "Malbegrenzung"; Auswählen → "Reihenfolge"; Wege → name/connect; "Landmasse erzeugen" → preset/output/decoration.
  Test in DE/EN, night/parchment theme, at 1440/390/320 px.
- Player authorization is unaffected: the library stays account-private (`own_project`); the DM table and Atlas use their existing authorized paths.

## W02 label fragment (DE source → EN) for `tools/i18n/tasks/review-maps-w02.json`

Common labels that probably already exist (e.g. Abbrechen, Farbe, Größe, Stil, Name, Breite, Höhe, Rückgängig, Wiederholen, Radierer, Werkzeug, Material, Seed, Form, Insel) are deliberately left out. `build_catalog.py --check` reports any that are missing.

```json
{
  "Eigene Bilder": {"de": "Eigene Bilder", "en": "Own images"},
  "Eigenes Bild": {"de": "Eigenes Bild", "en": "Own image"},
  "Eigenes Bild „{label}“ ließ sich nicht dekodieren.": {"de": "Eigenes Bild „{label}“ ließ sich nicht dekodieren.", "en": "Own image “{label}” could not be decoded."},
  "Eigenes Bild „{label}“ hat nicht die angegebene Größe.": {"de": "Eigenes Bild „{label}“ hat nicht die angegebene Größe.", "en": "Own image “{label}” does not have the declared size."},
  "Pixelgrafik": {"de": "Pixelgrafik", "en": "Pixel art"},
  "Gemalt": {"de": "Gemalt", "en": "Painted"},
  "Tusche/Linie": {"de": "Tusche/Linie", "en": "Ink/line"},
  "Sonstiges": {"de": "Sonstiges", "en": "Other"},
  "Draufsicht": {"de": "Draufsicht", "en": "Top-down"},
  "Seitenansicht": {"de": "Seitenansicht", "en": "Side view"},
  "Isometrisch": {"de": "Isometrisch", "en": "Isometric"},
  "Sonstige": {"de": "Sonstige", "en": "Other"},
  "Angaben zum Bild": {"de": "Angaben zum Bild", "en": "Image details"},
  "Quelle / Urheber": {"de": "Quelle / Urheber", "en": "Source / author"},
  "Lizenz oder Nutzungsrecht": {"de": "Lizenz oder Nutzungsrecht", "en": "Licence or usage right"},
  "Der Browser konnte das PNG nicht erzeugen.": {"de": "Der Browser konnte das PNG nicht erzeugen.", "en": "The browser could not create the PNG."},
  "Eigene Bilder dieser Karte: {count}/{max} · {mib} von 12 MiB · {mpx} von 8 Mio. Pixel": {"de": "Eigene Bilder dieser Karte: {count}/{max} · {mib} von 12 MiB · {mpx} von 8 Mio. Pixel", "en": "Own images in this map: {count}/{max} · {mib} of 12 MiB · {mpx} of 8 million pixels"},
  "Eigenes Bild als Stempel": {"de": "Eigenes Bild als Stempel", "en": "Own image as stamp"},
  "Das Bild wird als PNG nur in dieses Kartenprojekt eingebettet, nicht öffentlich freigegeben. Es bleibt ein Rasterbild ohne bearbeitbare Einzelteile. PNG, JPEG oder WebP; keine SVG-Dateien oder Links.": {"de": "Das Bild wird als PNG nur in dieses Kartenprojekt eingebettet, nicht öffentlich freigegeben. Es bleibt ein Rasterbild ohne bearbeitbare Einzelteile. PNG, JPEG oder WebP; keine SVG-Dateien oder Links.", "en": "The image is embedded as a PNG in this map project only and is not published. It stays a raster image without editable parts. PNG, JPEG or WebP; no SVG files or links."},
  "Bilddatei": {"de": "Bilddatei", "en": "Image file"},
  "Ausschnitt: im Bild ziehen oder Zahlen eingeben (Originalpixel).": {"de": "Ausschnitt: im Bild ziehen oder Zahlen eingeben (Originalpixel).", "en": "Crop: drag in the image or enter numbers (original pixels)."},
  "Quellbild mit Ausschnitt": {"de": "Quellbild mit Ausschnitt", "en": "Source image with crop"},
  "Größte Seite im Ergebnis (px, höchstens {px})": {"de": "Größte Seite im Ergebnis (px, höchstens {px})", "en": "Longest side of the result (px, at most {px})"},
  "Hintergrund entfernen (einfache Farbe)": {"de": "Hintergrund entfernen (einfache Farbe)", "en": "Remove background (single colour)"},
  "Diese Farbe transparent machen": {"de": "Diese Farbe transparent machen", "en": "Make this colour transparent"},
  "Toleranz": {"de": "Toleranz", "en": "Tolerance"},
  "Farbe im Bild wählen": {"de": "Farbe im Bild wählen", "en": "Pick colour in image"},
  "Vorschau des Stempels": {"de": "Vorschau des Stempels", "en": "Stamp preview"},
  "Vorschau des eigenen Bilds": {"de": "Vorschau des eigenen Bilds", "en": "Own image preview"},
  "Ich darf dieses Bild in meinen Karten verwenden.": {"de": "Ich darf dieses Bild in meinen Karten verwenden.", "en": "I am allowed to use this image in my maps."},
  "Als eigenes Bild speichern": {"de": "Als eigenes Bild speichern", "en": "Save as own image"},
  "Die Datei ist größer als 32 MiB.": {"de": "Die Datei ist größer als 32 MiB.", "en": "The file is larger than 32 MiB."},
  "Bitte ein PNG-, JPEG- oder WebP-Bild wählen (keine SVG-Dateien).": {"de": "Bitte ein PNG-, JPEG- oder WebP-Bild wählen (keine SVG-Dateien).", "en": "Please choose a PNG, JPEG or WebP image (no SVG files)."},
  "Das Bild ließ sich nicht lesen.": {"de": "Das Bild ließ sich nicht lesen.", "en": "The image could not be read."},
  "Das Bild ist größer als {px} Pixel je Seite. Bitte vorher verkleinern.": {"de": "Das Bild ist größer als {px} Pixel je Seite. Bitte vorher verkleinern.", "en": "The image is larger than {px} pixels per side. Please resize it first."},
  "Der Ausschnitt muss innerhalb des Bildes liegen.": {"de": "Der Ausschnitt muss innerhalb des Bildes liegen.", "en": "The crop must lie inside the image."},
  "Ergebnis {w}×{h} Pixel": {"de": "Ergebnis {w}×{h} Pixel", "en": "Result {w}×{h} pixels"},
  "Bitte bestätigen, dass du dieses Bild verwenden darfst.": {"de": "Bitte bestätigen, dass du dieses Bild verwenden darfst.", "en": "Please confirm that you may use this image."},
  "„{label}“ ist als eigenes Bild in dieser Karte verfügbar.": {"de": "„{label}“ ist als eigenes Bild in dieser Karte verfügbar.", "en": "“{label}” is available as an own image in this map."},
  "Pixelbild zeichnen": {"de": "Pixelbild zeichnen", "en": "Draw pixel image"},
  "Ein neues Pixelbild von 16 bis 256 Pixeln. Gespeichert wird ein PNG-Stempel nur in dieser Karte.": {"de": "Ein neues Pixelbild von 16 bis 256 Pixeln. Gespeichert wird ein PNG-Stempel nur in dieser Karte.", "en": "A new pixel image from 16 to 256 pixels. It is saved as a PNG stamp in this map only."},
  "Neu anlegen": {"de": "Neu anlegen", "en": "New image"},
  "Stift": {"de": "Stift", "en": "Pen"},
  "Deckkraft (%)": {"de": "Deckkraft (%)", "en": "Opacity (%)"},
  "Automatisch": {"de": "Automatisch", "en": "Automatic"},
  "Pixelfläche": {"de": "Pixelfläche", "en": "Pixel canvas"},
  "Pixelbild": {"de": "Pixelbild", "en": "Pixel image"},
  "Eigene Pixelgrafik (Kartenwerkstatt)": {"de": "Eigene Pixelgrafik (Kartenwerkstatt)", "en": "Own pixel art (map workshop)"},
  "Eigene Arbeit": {"de": "Eigene Arbeit", "en": "Own work"},
  "Als eigenen Stempel speichern": {"de": "Als eigenen Stempel speichern", "en": "Save as own stamp"},
  "Das Pixelbild ist noch leer.": {"de": "Das Pixelbild ist noch leer.", "en": "The pixel image is still empty."},
  "„{label}“ ist als eigener Stempel in dieser Karte verfügbar.": {"de": "„{label}“ ist als eigener Stempel in dieser Karte verfügbar.", "en": "“{label}” is available as an own stamp in this map."},
  "Die Vorschau verändert deine Karte nicht. Übernehmen legt eine neue Ebene an und ist ein einziger Rückgängig-Schritt.": {"de": "Die Vorschau verändert deine Karte nicht. Übernehmen legt eine neue Ebene an und ist ein einziger Rückgängig-Schritt.", "en": "The preview does not change your map. Adopting adds a new layer as a single undo step."},
  "Vorlage": {"de": "Vorlage", "en": "Preset"},
  "Eigene Werte": {"de": "Eigene Werte", "en": "Custom values"},
  "Ausgabe": {"de": "Ausgabe", "en": "Output"},
  "Material (Malebene)": {"de": "Material (Malebene)", "en": "Material (paint layer)"},
  "Gewählte Kachel (Kachelebene)": {"de": "Gewählte Kachel (Kachelebene)", "en": "Selected tile (tile layer)"},
  "Berge streuen": {"de": "Berge streuen", "en": "Scatter mountains"},
  "Wälder streuen": {"de": "Wälder streuen", "en": "Scatter forests"},
  "Name der Vorlage": {"de": "Name der Vorlage", "en": "Preset name"},
  "Als Vorlage speichern": {"de": "Als Vorlage speichern", "en": "Save as preset"},
  "Vorlage löschen": {"de": "Vorlage löschen", "en": "Delete preset"},
  "Inselreich": {"de": "Inselreich", "en": "Island realm"},
  "Kontinent": {"de": "Kontinent", "en": "Continent"},
  "Zerklüftete Küste": {"de": "Zerklüftete Küste", "en": "Ragged coast"},
  "{name} · {version} (andere Generatorversion, nicht anwendbar)": {"de": "{name} · {version} (andere Generatorversion, nicht anwendbar)", "en": "{name} · {version} (other generator version, not applicable)"},
  "Vorlagen lassen sich in diesem Browser nicht speichern.": {"de": "Vorlagen lassen sich in diesem Browser nicht speichern.", "en": "Presets cannot be saved in this browser."},
  "Bitte einen Namen und gültige Werte für die Vorlage angeben.": {"de": "Bitte einen Namen und gültige Werte für die Vorlage angeben.", "en": "Please enter a name and valid values for the preset."},
  "Höchstens {count} eigene Vorlagen.": {"de": "Höchstens {count} eigene Vorlagen.", "en": "At most {count} own presets."},
  "Vorlage „{name}“ gespeichert ({version}).": {"de": "Vorlage „{name}“ gespeichert ({version}).", "en": "Preset “{name}” saved ({version})."},
  "Für Kacheln zuerst im Kachelwerkzeug eine Kachel wählen.": {"de": "Für Kacheln zuerst im Kachelwerkzeug eine Kachel wählen.", "en": "For tiles, first choose a tile in the tile tool."},
  "Kachel: {label}": {"de": "Kachel: {label}", "en": "Tile: {label}"},
  "Dekoration nur mit geladenen Berg- oder Waldsymbolen.": {"de": "Dekoration nur mit geladenen Berg- oder Waldsymbolen.", "en": "Decoration needs loaded mountain or forest symbols."},
  "{count} Symbole": {"de": "{count} Symbole", "en": "{count} symbols"},
  "Das Ergebnis überschreitet das Kachel- oder Symbol-Budget der Karte. Wähle eine größere Kachel oder weniger Dekoration.": {"de": "Das Ergebnis überschreitet das Kachel- oder Symbol-Budget der Karte. Wähle eine größere Kachel oder weniger Dekoration.", "en": "The result exceeds the map's tile or symbol budget. Choose a larger tile or less decoration."},
  "Landmasse-Symbole": {"de": "Landmasse-Symbole", "en": "Landmass symbols"},
  "Dieses eigene Bild gehört nicht zu dieser Karte. Bitte eine andere Kachel wählen.": {"de": "Dieses eigene Bild gehört nicht zu dieser Karte. Bitte eine andere Kachel wählen.", "en": "This own image does not belong to this map. Please choose another tile."},
  "Keine passende Ebene für dieses Werkzeug.": {"de": "Keine passende Ebene für dieses Werkzeug.", "en": "No matching layer for this tool."},
  "Aktive Ebene: {name}": {"de": "Aktive Ebene: {name}", "en": "Active layer: {name}"},
  "Malbegrenzung aus: „{name}“ liegt nicht mehr unter der aktiven Malebene.": {"de": "Malbegrenzung aus: „{name}“ liegt nicht mehr unter der aktiven Malebene.", "en": "Paint limit off: “{name}” is no longer below the active paint layer."},
  "Malbegrenzung aus: Die Bezugsebene wurde gelöscht.": {"de": "Malbegrenzung aus: Die Bezugsebene wurde gelöscht.", "en": "Paint limit off: the reference layer was deleted."},
  "Wähle zuerst Symbole, Wege oder Beschriftungen aus.": {"de": "Wähle zuerst Symbole, Wege oder Beschriftungen aus.", "en": "First select symbols, paths or labels."},
  "Die Auswahl liegt bereits ganz vorne.": {"de": "Die Auswahl liegt bereits ganz vorne.", "en": "The selection is already in front."},
  "Die Auswahl liegt bereits ganz hinten.": {"de": "Die Auswahl liegt bereits ganz hinten.", "en": "The selection is already at the back."},
  "Eine Stufe nach vorne": {"de": "Eine Stufe nach vorne", "en": "Bring forward"},
  "Eine Stufe nach hinten": {"de": "Eine Stufe nach hinten", "en": "Send backward"},
  "Ganz nach vorne": {"de": "Ganz nach vorne", "en": "Bring to front"},
  "Ganz nach hinten": {"de": "Ganz nach hinten", "en": "Send to back"},
  "Nach vorne": {"de": "Nach vorne", "en": "Forward"},
  "Nach hinten": {"de": "Nach hinten", "en": "Backward"},
  "Reihenfolge": {"de": "Reihenfolge", "en": "Order"},
  "Reihenfolge ändern": {"de": "Reihenfolge ändern", "en": "Change order"},
  "Kein passender Endpunkt in der Nähe (gleiche Ebene und Art, höchstens {px} px).": {"de": "Kein passender Endpunkt in der Nähe (gleiche Ebene und Art, höchstens {px} px).", "en": "No matching endpoint nearby (same layer and kind, at most {px} px)."},
  "Zusammen hätten die Wege mehr als {count} Punkte. Bitte einen Weg vereinfachen.": {"de": "Zusammen hätten die Wege mehr als {count} Punkte. Bitte einen Weg vereinfachen.", "en": "Together the paths would have more than {count} points. Please simplify one path."},
  "Wege verbinden": {"de": "Wege verbinden", "en": "Connect paths"},
  "Wege verbunden.": {"de": "Wege verbunden.", "en": "Paths connected."},
  "Diese Fläche bräuchte {count} Symbole und überschreitet das Budget (höchstens {max} je Fläche, {limit} pro Karte). Bitte kleiner ziehen oder Symbolgröße erhöhen.": {"de": "Diese Fläche bräuchte {count} Symbole und überschreitet das Budget (höchstens {max} je Fläche, {limit} pro Karte). Bitte kleiner ziehen oder Symbolgröße erhöhen.", "en": "This area would need {count} symbols and exceeds the budget (at most {max} per area, {limit} per map). Drag a smaller area or increase the symbol size."},
  "Fläche füllen": {"de": "Fläche füllen", "en": "Fill area"},
  "Höchstens {count} eigene Bilder pro Karte. Entferne zuerst ein unbenutztes Bild.": {"de": "Höchstens {count} eigene Bilder pro Karte. Entferne zuerst ein unbenutztes Bild.", "en": "At most {count} own images per map. Remove an unused image first."},
  "Eigene Bilder dürfen höchstens {px} Pixel je Seite haben.": {"de": "Eigene Bilder dürfen höchstens {px} Pixel je Seite haben.", "en": "Own images may have at most {px} pixels per side."},
  "Das PNG ist größer als 4 MiB. Bitte verkleinern oder zuschneiden.": {"de": "Das PNG ist größer als 4 MiB. Bitte verkleinern oder zuschneiden.", "en": "The PNG is larger than 4 MiB. Please resize or crop it."},
  "Eigene Bilder wären zusammen größer als 12 MiB.": {"de": "Eigene Bilder wären zusammen größer als 12 MiB.", "en": "Own images would exceed 12 MiB together."},
  "Eigene Bilder hätten zusammen mehr als 8 Millionen Pixel.": {"de": "Eigene Bilder hätten zusammen mehr als 8 Millionen Pixel.", "en": "Own images would exceed 8 million pixels together."},
  "Dieses Bild ist bereits in der Karte vorhanden.": {"de": "Dieses Bild ist bereits in der Karte vorhanden.", "en": "This image is already in the map."},
  "Das Bild ist zu groß für den Verlauf.": {"de": "Das Bild ist zu groß für den Verlauf.", "en": "The image is too large for the undo history."},
  "Eigenes Bild hinzufügen": {"de": "Eigenes Bild hinzufügen", "en": "Add own image"},
  "„{label}“ wird noch auf der Karte verwendet und bleibt erhalten.": {"de": "„{label}“ wird noch auf der Karte verwendet und bleibt erhalten.", "en": "“{label}” is still used on the map and is kept."},
  "Eigenes Bild entfernen": {"de": "Eigenes Bild entfernen", "en": "Remove own image"},
  "Für „Fläche füllen“ ein Rechteck auf der Karte aufziehen.": {"de": "Für „Fläche füllen“ ein Rechteck auf der Karte aufziehen.", "en": "For “Fill area”, drag a rectangle on the map."},
  "Ebene für dieses Werkzeug": {"de": "Ebene für dieses Werkzeug", "en": "Layer for this tool"},
  "Alt+↑ / Alt+↓ wechselt die Ebene.": {"de": "Alt+↑ / Alt+↓ wechselt die Ebene.", "en": "Alt+↑ / Alt+↓ switches the layer."},
  "Malbegrenzung": {"de": "Malbegrenzung", "en": "Paint limit"},
  "Schriftfamilie": {"de": "Schriftfamilie", "en": "Font family"},
  "Name des Wegs (optional)": {"de": "Name des Wegs (optional)", "en": "Path name (optional)"},
  "Endpunkt mit Nachbarweg verbinden": {"de": "Endpunkt mit Nachbarweg verbinden", "en": "Connect endpoint to neighbouring path"},
  "Verbindet nur mit einem Endpunkt derselben Ebene und Art in höchstens {px} px Abstand. Kreuzungen bleiben getrennt.": {"de": "Verbindet nur mit einem Endpunkt derselben Ebene und Art in höchstens {px} px Abstand. Kreuzungen bleiben getrennt.", "en": "Connects only to an endpoint of the same layer and kind within {px} px. Crossings stay separate."},
  "Platzierung": {"de": "Platzierung", "en": "Placement"},
  "Fläche füllen (Rechteck ziehen)": {"de": "Fläche füllen (Rechteck ziehen)", "en": "Fill area (drag a rectangle)"},
  "Eigenes Bild hochladen …": {"de": "Eigenes Bild hochladen …", "en": "Upload own image …"},
  "Pixelbild zeichnen …": {"de": "Pixelbild zeichnen …", "en": "Draw pixel image …"},
  "Eigene Bilder dieser Karte": {"de": "Eigene Bilder dieser Karte", "en": "Own images in this map"},
  "Darstellung": {"de": "Darstellung", "en": "Style"},
  "Zusammenhängenden Inhalt erfassen": {"de": "Zusammenhängenden Inhalt erfassen", "en": "Capture connected content"},
  "Auswahl eine Stufe nach vorne/hinten (mit Umschalt: ganz)": {"de": "Auswahl eine Stufe nach vorne/hinten (mit Umschalt: ganz)", "en": "Move selection one step forward/back (with Shift: all the way)"},
  "Mausrad": {"de": "Mausrad", "en": "Mouse wheel"},
  "Reihenfolge der Auswahl ändern (Auswählen-Werkzeug)": {"de": "Reihenfolge der Auswahl ändern (Auswählen-Werkzeug)", "en": "Change the order of the selection (select tool)"},
  "Ebene des Werkzeugs wechseln": {"de": "Ebene des Werkzeugs wechseln", "en": "Switch the tool's layer"},
  "Bild↑/Bild↓ oder Alt+Mausrad ändern die Reihenfolge in der Ebene.": {"de": "Bild↑/Bild↓ oder Alt+Mausrad ändern die Reihenfolge in der Ebene.", "en": "Page Up/Page Down or Alt+wheel change the order within the layer."},
  "Alle Darstellungen": {"de": "Alle Darstellungen", "en": "All styles"},
  "Alle Perspektiven": {"de": "Alle Perspektiven", "en": "All perspectives"},
  "Stil- und Perspektivangaben gibt es für eigene Bilder; Pixelgrafik erkennt auch Katalogpakete.": {"de": "Stil- und Perspektivangaben gibt es für eigene Bilder; Pixelgrafik erkennt auch Katalogpakete.", "en": "Style and perspective are known for own images; pixel art is also recognised in catalogue packs."},
  "Wie der Stil": {"de": "Wie der Stil", "en": "As the style"},
  "Cinzel (Antiqua-Versalien)": {"de": "Cinzel (Antiqua-Versalien)", "en": "Cinzel (roman capitals)"},
  "Bad Script (Schreibschrift)": {"de": "Bad Script (Schreibschrift)", "en": "Bad Script (handwriting)"},
  "Literata (Buchschrift)": {"de": "Literata (Buchschrift)", "en": "Literata (book face)"},
  "Rechteck auf der Karte aufziehen. Abstand wie beim Streuen; ein Rückgängig-Schritt.": {"de": "Rechteck auf der Karte aufziehen. Abstand wie beim Streuen; ein Rückgängig-Schritt.", "en": "Drag a rectangle on the map. Spacing as for scattering; one undo step."},
  "{count} Symbole – zu viele für diese Fläche (höchstens 400 je Fläche, frei: {free}).": {"de": "{count} Symbole – zu viele für diese Fläche (höchstens 400 je Fläche, frei: {free}).", "en": "{count} symbols – too many for this area (at most 400 per area, free: {free})."},
  "{count} Symbole werden gesetzt.": {"de": "{count} Symbole werden gesetzt.", "en": "{count} symbols will be placed."},
  "{name} (ausgeblendet)": {"de": "{name} (ausgeblendet)", "en": "{name} (hidden)"},
  "Neue Ebene beim ersten Einsatz": {"de": "Neue Ebene beim ersten Einsatz", "en": "New layer on first use"},
  "Keine passende Ebene": {"de": "Keine passende Ebene", "en": "No matching layer"},
  "Keine Begrenzung": {"de": "Keine Begrenzung", "en": "No limit"},
  "Nur auf belegten Kacheln von „{name}“": {"de": "Nur auf belegten Kacheln von „{name}“", "en": "Only on occupied tiles of “{name}”"},
  "Nur auf der Deckung von „{name}“": {"de": "Nur auf der Deckung von „{name}“", "en": "Only on the coverage of “{name}”"},
  "Keine Bezugsebene: Eine Malebene darunter oder eine Kachelebene kann die Malfläche begrenzen.": {"de": "Keine Bezugsebene: Eine Malebene darunter oder eine Kachelebene kann die Malfläche begrenzen.", "en": "No reference layer: a paint layer below or a tile layer can limit the paint area."},
  "Malbegrenzung gilt für die aktive Malebene.": {"de": "Malbegrenzung gilt für die aktive Malebene.", "en": "The paint limit applies to the active paint layer."},
  "Neue Striche erscheinen nur dort; vorhandene Pixel außerhalb bleiben unverändert.": {"de": "Neue Striche erscheinen nur dort; vorhandene Pixel außerhalb bleiben unverändert.", "en": "New strokes appear only there; existing pixels outside stay unchanged."},
  "{count}/{max} eigene Bilder · {mib} von 12 MiB · nur in dieser Karte gespeichert": {"de": "{count}/{max} eigene Bilder · {mib} von 12 MiB · nur in dieser Karte gespeichert", "en": "{count}/{max} own images · {mib} of 12 MiB · stored in this map only"},
  "ohne Lizenzangabe": {"de": "ohne Lizenzangabe", "en": "no licence stated"},
  "„{label}“ als Stempel wählen": {"de": "„{label}“ als Stempel wählen", "en": "Choose “{label}” as stamp"},
  "Verwenden": {"de": "Verwenden", "en": "Use"},
  "„{label}“ aus der Karte entfernen": {"de": "„{label}“ aus der Karte entfernen", "en": "Remove “{label}” from the map"},
  "Wird auf der Karte verwendet": {"de": "Wird auf der Karte verwendet", "en": "Used on the map"},
  "Entfernen": {"de": "Entfernen", "en": "Remove"},
  "Noch keine eigenen Bilder in dieser Karte.": {"de": "Noch keine eigenen Bilder in dieser Karte.", "en": "No own images in this map yet."},
  "Der Ausschnitt enthält keine sichtbaren Pixel.": {"de": "Der Ausschnitt enthält keine sichtbaren Pixel.", "en": "The crop contains no visible pixels."},
  "Quelle {w}×{h} px · Ausschnitt {cw}×{ch} px ab {x},{y}": {"de": "Quelle {w}×{h} px · Ausschnitt {cw}×{ch} px ab {x},{y}", "en": "Source {w}×{h} px · crop {cw}×{ch} px from {x},{y}"},
  "oben": {"de": "oben", "en": "top"},
  "rechts": {"de": "rechts", "en": "right"},
  "unten": {"de": "unten", "en": "bottom"},
  "links": {"de": "links", "en": "left"},
  "Sichtbarer Inhalt läuft über den Rand ({sides}) – vermutlich abgeschnitten.": {"de": "Sichtbarer Inhalt läuft über den Rand ({sides}) – vermutlich abgeschnitten.", "en": "Visible content runs past the edge ({sides}) – probably cut off."},
  "Kein sichtbarer Inhalt wird am Rand abgeschnitten.": {"de": "Kein sichtbarer Inhalt wird am Rand abgeschnitten.", "en": "No visible content is cut off at the edge."}
}
```
