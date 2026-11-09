# OC0 + OC1: Fundament und Durchstich „Oglans Book of Chaos“

Datum: 2026-11-09. Programm: [`docs/decisions/OGLANS_BOOK_OF_CHAOS_PROGRAM_V1.md`](decisions/OGLANS_BOOK_OF_CHAOS_PROGRAM_V1.md).

## Discover (OC0)

- Der Reader (`vtt/rules.py`, `regelwerk-reader.js`) kennt genau ein Paket mit festem Ruleset-ID
  und Quellversion `5.2.1` in der URL.
- Das Paketschema verlangt ein Quell-PDF mit SHA-256, Seitenzahl und `sourcePages`. Die
  Abdeckung ist seitenbasiert: Pflicht-, Ausschluss-, Review-Bereiche, Abschnitte als
  Seitenblöcke. `contentStatus: original` gibt es schon.
- Kompendium und Creator-Daten werden aus der SRD-Struktur abgeleitet (Zauberköpfe,
  Klassentabellen) und passen nicht ohne Weiteres auf ein eigenes Buch.
- Laufendes Image `beyond20-feed-20261108-fa4fe5c`. Dessen Regelwerk-Python, -Skripte und
  -Schemas sind gleich dem Stand `0748abb41`. Die Templates `regelwerk*.html` laden live
  zusätzlich die Hauptnavigation; der Zweig übernimmt sie zuerst unverändert (`eb9c60e9a`).
- Das GitHub-Repository ist öffentlich: Lesezimmer-Material bleibt darum privat auf dem Server.

## Apply (OC0)

- **Paketart `original`:** neue optionale Manifest-Felder `kind` und `routeKey`. Das
  Seitenmodell bleibt, aber Seiten sind Clean-Room-Kartennummern (Blöcke je Kapitel: 00xx
  Rahmen, 02xx Unterklassen, 06xx Zauber …). `source.sha256` pinnt die versiegelte
  Übergabe, der Source-Lock in `source-locks.json` ebenfalls. SRD-Paket und seine
  Artefakte bleiben bytegleich.
- **Validator:** Bei `original` muss jeder Text `original` sein. Begriffe aus
  `vtt/rules_content/brand-denylist.txt` sind verboten (ganze Wörter), und eine Überschrift
  darf keinem SRD-Eintragsnamen gleichen (Zauber, Talente, Klassenmerkmale, Unterklassen,
  Gegenstände, Völker, Hintergründe, Klassen).
- **Generator:** eigenes Buch nur mit Navigation, Suche und Abdeckung, URLs
  `/regelwerk/<routeKey>/de/<slug>`, Reader `/regelwerk/<routeKey>`, Lizenz
  `/regelwerk/<routeKey>/lizenz`.
- **Routen:** `/api/rulesets` (Bücherliste), `/api/rulesets/<id>/manifest|documents|search|license`
  für eigene Bücher. Die SRD-Routen bleiben wörtliche Pfade und haben Vorrang. Schalter
  `OGLAN_BOOK` (App-Konfiguration oder Umgebung, Standard an).
- **Reader:** Buchwahl unter dem Titel, Titel, Suche, Hinweise, Fußzeile und Lizenzseite
  je Buch. Das SRD bleibt Hauptbuch unter `/regelwerk`.
- **Werkzeug:** `tools/seal_original_package.py` berechnet Digests, Inhaltsliste,
  Attributions- und Übergabe-Pin und erzeugt die Artefakte.
- **Abnahme OC0:** SRD-Routen, -API und -Artefakte unverändert. Eigenes Buch anonym lesbar,
  durchsuchbar, mit eigener Lizenzseite. Mit `OGLAN_BOOK=0` überall 404. Validator weist
  Markenbegriffe, SRD-Namen und Nicht-Originaltext ab.

## Apply (OC1)

- Dokumente: `frame.foreword` (Vorwort, Karte 1), `subclasses.druid` (Karte 201),
  `spells.catalog` (Karte 601). Abschnitte: Vorwort, Unterklassen, Zauber.
- Ablauf über den Clean Room: Lesezimmer-Karten → Schleuse → Übergabe → Schreibstube →
  Versiegeln → Validator → Endkontrolle gegen die Spurliste → Live-Vorschau.
- Owner-Review danach; erst dann werden die Karten als geprüft eingetragen.

## Deploy (OC0 + OC1)

- Commits: `eb9c60e9a` (Live-Templates übernommen), `4068a6284` (OC0 Fundament), `81672369d`
  (Paket 0.1.0, Tests) auf `feat/oglans-book-of-chaos-oc0-20261109`, gepusht.
- Clean Room: Lesezimmer-Agent mit 13 Karten (2 für OC1, 11 für OC2) und Inventar-Abgleich. Die
  Schleuse lief mit 267 Sperrbegriffen, die Übergabe OC1 ist versiegelt
  (`bbcbad181591eed75a5d004b898ce3e3dbb8cdfd3d7d146321fd87b33d2249e8` = `source.sha256`). Die
  Schreibstube (frischer Agent ohne Web und ohne Lesezimmer) hat drei Dokumente geschrieben, nach
  einer Überarbeitungsrunde der Schleuse. Endkontrolle gegen alle Sperrbegriffe: 0 Treffer.
  Protokoll und Karten liegen privat auf dem Server.
- Paket `oglans-book-of-chaos-de` 0.1.0, Status `preview`, Digest
  `sha256:1b1506aa5099d17186e84260506391e3703c3b9bcab2be8afa2797a7e13e0744`. Inhalt: Vorwort,
  Druiden-Unterklasse „Zirkel der Nachtzeichner“, Signaturzauber „Oglans Grünspanguss“.

## Prüfungen

- Neu: `tests/test_regelwerk_original_package.py` (10), `tests/test_regelwerk_books.py` (12),
  `tests/test_regelwerk_books_browser.py` (2: 1440 und 390 px), alle grün.
- Regelwerk-, Kompendium-, Creator-Daten- und SRD-Creator-Tests: 211 grün, nachdem der R0-Test
  den zweiten Source-Lock erwartet (gewollte Änderung, SRD-Pin unverändert geprüft).
- `tests/test_creation_engine_navigation.py`: 12 Fehlschläge, dieselbe Liste wie auf dem
  unveränderten Stand `0748abb41`. Sie haben mit diesem Paket nichts zu tun.
- SRD-Paket: Digest `sha256:f8bec2d832471…` vor und nach der Änderung gleich, Artefakte
  bytegleich (`stale_artifacts` leer).

## Auslieferung

- Image `roll-drauf-vtt-app:oglan-oc1-20261109-8167236`
  (`sha256:496595790afb006e6907fe6ecef49ea617d65802583e300bbb91aeeb01908cf4`), gebaut
  `FROM roll-drauf-vtt-app:beyond20-feed-20261108-fa4fe5c` (laufendes Image) mit den elf
  geänderten Pfaden. Im Image hashgleich mit `81672369d`; beide Pakete validieren dort.
- `production.duck-species.override.yml` umgestellt (Sicherung `.bak-oglan-oc1-20261109`),
  `up -d --no-deps --no-build app` um 2026-11-09 10:06:01 UTC.

## Live-Prüfung

- `/api/rulesets` listet SRD (published) und Oglans Book of Chaos (preview).
- `/regelwerk/oglan`, `/lizenz`, die drei Dokumente: 200. Unbekannter Slug: 404. SRD-Seiten: 200,
  SRD-Digest unverändert.
- Suche „Leuchtbild“ findet die Unterklasse; die Lizenz-API nennt „© 2026 Roll Drauf“ und die
  SRD-Namensnennung.
- `regelwerk-reader.js` und `regelwerk.css` öffentlich hashgleich, `Cache-Control: no-cache`.
  Startlog ohne Fehler.
- Echter Browser gegen die Live-Seite, anonym, 1440 und 390 px: Titel, Buchwahl, Vorwort,
  Unterklasse, Zauber und der Wechsel zurück zum SRD funktionieren. Keine Seitenfehler, kein
  horizontaler Überlauf.

## Offen

- Owner-Prüfung der Karten gegen das eigene Exemplar (76 Faktenfragen, privat). Danach trägt der
  Owner die Karten als geprüft ein (`reviewedPageRanges`).
- OC2: elf Unterklassen (Karten liegen im Lesezimmer) und die Kompendium-Anbindung des Buchs.
- Privates Remote für den Clean-Room-Ordner, sobald der Owner eines anlegt.

## Rollback

```
cd /srv/migration/2026-10-07/setup
cp -p production.duck-species.override.yml.bak-oglan-oc1-20261109 production.duck-species.override.yml
docker compose -p migration-production -f production.compose.json -f production.duck-species.override.yml up -d --no-deps --no-build app
```
Nur das Buch ausblenden: `OGLAN_BOOK=0` in der App-Umgebung setzen und den Container neu
erstellen. Das vorherige Image `beyond20-feed-20261108-fa4fe5c` bleibt lokal erhalten.
