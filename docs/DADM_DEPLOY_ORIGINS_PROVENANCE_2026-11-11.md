# Deploy P3: Herkunftsfassungen und Bonusquellen

status: kompatibles Leser-Zwischenrelease; Gesamtpaket noch nicht abgeschlossen.
input_summary: Apply P3, autorisiertes Gesamtprogramm. artifacts: additive
`ce_rule_revisions`, Profil-/Auswahllogik, Regelherleitungen, Herkunfts-API,
Kataloginventar, Tests; retention permanent.

Implementierung: typisierte Profile, Quell-/Profildigest und immutable Revisionen;
alle ausgewählten Homebrew-IDs einschließlich verknüpftem Herkunftstalent werden
serverseitig aufgelöst. Fertige Figuren nutzen ausschließlich kopierte Pins.
Import verlangt dieselben serverseitig freigegebenen Revisionen/Digests; Rebuild
und Kampagnenbindung prüfen weiter. Grants wirken im bestehenden Evaluator einmal.
Herleitungen umfassen Attribute/Modifikatoren, HP, RK, Initiative, Bewegung,
Skills/Saves, Übungsbonus, passive Wahrnehmung und Zauberwerte sowie Waffenangriffe.
Manuelle Überschreibungen werden als letzte Änderung ausgewiesen.

Dateien: `creation_engine/origins.py`, `origin_routes.py`, Modell
`models/ce_rule_revision.py`, `characters/origin_catalog.py`, reine
`rules_content/origin_profiles.py` sowie die vorhandenen Creator-/Import-/Party-/
Inventar-/Spezies-Lesepfade. Kataloginventar im Proof: 12 Klassen, 12 Unterklassen,
17 Talente, vier Hintergründe des vorhandenen lizenzierten Pakets. I01 bleibt offen.

Verifikation Leser-Gate: **126 Fälle bestanden** (Profil-/Provenienzmatrix für alle
Klassen, Publikation/Source-CAS/Pins/Import/Rebuild, Inventar und bestehende Regel-
Beispiele). Zwei alte Inventar-Regressionen verlangten noch implizite Tischrechte;
sie treten jetzt ausdrücklich in den autorisierten Player-Kontext ein. Verhalten
und Rechte in Produktion werden dafür nicht aufgeweicht.

`CE_PLAYABLE_ORIGINS` bleibt im ersten Image standardmäßig aus. Das Deployment
prüft, dass kein aktivierender Produktions-Override vorliegt. Neue Tabelle nur
additiv nach Backup. Dieses Image wird der kompatible Rückweg des späteren
schreibenden Release. Aktuelle Eagle-UI/Creator-Auswahl folgt vor Paketabschluss;
dieser Zwischenstand ist keine fertige P3-Lieferung. Python-Kompilierung und
Diff-Prüfung sind Teil des Gates. Keine neuen Runtime-Abhängigkeiten.

Akzeptanz Leser: Pins ohne publizierenden Featureflag auswertbar; unterstützte
Grants, Importrechte und Bonusgesamtwerte geprüft. Rest: visueller Zusatz,
Entwurfsrevision, vollständige UI-Reise und technische Live-Abnahme. Nächster
Schritt: Leser-Image bereitstellen, danach P3-UI/Writes aktivieren und gegen den
kompatiblen Leser-Rückweg verifizieren.

## Schreibendes Release und Oberfläche

Leser-Zwischenrelease live verifiziert: [Checkpoint](proofs/origins-provenance-2026-11-11/reader-checkpoint.json).
Neue Tabelle angelegt und reflektiert, Backup-Archiv lesbar; unveränderliche
Hintergrund-/Merkmalspins bei abgeschalteter Publikation im laufenden Image geprüft.
Keine Testfigur dafür in die Datenbank geschrieben. Dieses Image ist der Rückweg.

UI umgesetzt: vorhandene Eagle-Navigation → neuer Hintergrund-/Merkmalsbereich,
Anlegen eines normalen Eagle-Dokuments, beschriftete Felder, Entwurf speichern
mit Quellrevision/Digest-CAS, sichere Vorschau, bewusstes Veröffentlichen. Creator
lädt freigegebene Fassungen und zeigt deren Regeltext; Bogen zeigt Pins und
aufklappbare Herleitungen. Waffenangriffs-/Schadenszusätze entsprechen genau den
serverseitigen Würfelspezifikationen. Neue Publikation ist im schreibenden Image
standardmäßig eingeschaltet; kein Produktions-Override dafür gesetzt.

Prüfungen nach UI-Ergänzung: **54** Backend-/Import-/Inventarfälle bestanden;
abschließend **29** gezielte Herkunfts-/Sicherheits-/Waffen-Provenienzfälle bestanden
(überlappende Gruppen, nicht addieren). **2** Browserreisen Chromium 1440 px und
Firefox 390 px bestanden: normaler Charaktere-Menüeinstieg → Eagle → Merkmal und
Hintergrund speichern/veröffentlichen → Creator-Auswahl → Finalisierung → Bogen
mit gepinnter Initiative +3 aus dem eigenen Merkmal. Keine Seitenfehler, kein
horizontaler Überlauf. JS-Syntax mit dem vorhandenen Playwright-Node geprüft;
Python-Kompilierung und `git diff --check` bestanden. Kein neues Paket installiert.

Noch nicht als Gesamtpaket fertig markiert: Commit/Push und App-Overlay auf den
verifizierten Leserstand; Live-Reise Autor/Player mit kampagnengebundener
Veröffentlichung, erlaubter Tischaktion, neuer Publikationsfassung und Beweis,
dass der kompatible Leser die tatsächlich erzeugten Pins lesen kann; Bereinigung
und Monitor danach. Frühere Zwischenstände haben keine Owner-Abnahme ersetzt.
