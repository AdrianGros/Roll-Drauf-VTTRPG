# Playtable UX Research

Beginn 22.11.2026, Konzeptpräsentation 23.11.2026. Dies sind Research-/Audit-Artefakte und lokale Mockups. Der Produktionscode wurde nicht geändert.

- [Bestandsaufnahme](../../../docs/DADM_DISCOVER_PLAYTABLE_UX_2026-11-22.md)
- [Drei Studien und vier Artikel](../../../docs/DADM_RESEARCH_PLAYTABLE_UX_2026-11-22.md)
- [Konzeptvergleich und Grenzen](../../../docs/DADM_APPLY_PLAYTABLE_UX_2026-11-23.md)
- [Gesamtindex CSV](inventory.csv), [JSON mit Geometrie und Quellen](inventory.json), [Summen und Quellenhashes](inventory-summary.json)
- [Menübandindex](footer-index.md)
- [Drei lokale Entwürfe](playtable-varianten.html)
- [Aufnahmeabdeckung](evidence/capture-coverage.json), [Mockup-Prüfung](evidence/mockup-verification.json)

K bedeutet Kontrollelement, I Informationselement. 875 indizierte DOM-Einträge/-familien bestehen aus 294 K und 581 I; 241 weitere bedingte Quelltexttexte sind separat indiziert. Das sind keine Funktionszahlen und keine gleichzeitigen Bildschirmbelegungen. Dynamische Inhalte sind Beispieldaten; Details des Abdeckungsumfangs stehen in Discover. Die Nummern sind ein eingefrorener Forschungsindex. Neue Einträge ergänzen den Index, ohne bestehende Einträge umzunummerieren; `build_inventory.py` reproduziert diesen Ausgangssnapshot und ist kein laufender Live-Indexdienst.

Sichtbare Beschriftungen, Tooltips und Platzhalter sind Informationseinträge. Zusätzlich sind im JSON vorhandene ARIA-Beschriftungen als Metadaten erhalten. Die automatische Feldbeschriftungs-Heuristik ist kein vollständiger Accessible-Name-Algorithmus und kein WCAG-Audit. Auswahlfelder trennen ihre Bezeichnung von den dynamischen Optionsdaten; originale DOM-Textvarianten bleiben für die Nachprüfung erhalten.

`collect_inventory.py` startet ausschließlich die bereits vorhandene Test-Fixture mit einer wegwerfbaren SQLite-Datei und eigenen Konten. Es liest keine Produktionsumgebung und verwendet keine Lane-Datenbank. Der Browser verwendet den aktuellen Quellstand; die Skripte ersetzen keine Stylesheets. Einige Etagenmetadaten werden als synthetische Renderer-Eingabe verwendet und sind entsprechend gekennzeichnet. Zugangstokens verbleiben im Arbeitsspeicher der Fixture und werden nicht in Belege geschrieben.

Die vollständige Rohdatei `evidence/captures.json`, generierte Vorschau und nicht ausgewählte Screenshots sind absichtlich nicht Teil des Git-Archivs. Die Rohdatei ist für eine erneute Indexerstellung nötig und kann durch denselben Sammler neu erzeugt werden. Ausgewählte Screenshots zeigen ausschließlich synthetische Inhalte.

Reproduktion im vorhandenen Testcontainer, vom Repository aus:

```bash
docker run --rm --network none \
  -v "$PWD":/app \
  -v /root/.cache/ms-playwright:/root/.cache/ms-playwright:ro \
  -w /app --entrypoint python roll-drauf-vtt-mobile-tests:20261115 \
  docs/research/playtable-ux-2026-11-22/collect_inventory.py

python3 docs/research/playtable-ux-2026-11-22/build_inventory.py
```

Für die visuelle Vorschau wird das Fragment mit dem vorhandenen Visualize-Renderer als `evidence/mockup-preview.html` gewrappt; anschließend prüft `verify_mockups.py` in Chromium die drei Designs, Etagenzugang, Messoptionen, explizites Anheften, Durchblättern, Palettenwechsel und horizontales Einpassen bei 1024/390/320 Pixeln. Der Preview-Runtime lädt seine eigenen Icon-/Positionierungsbibliotheken; das Fragment selbst hat weder API-Aufrufe noch Zugriff auf den VTT. Eine Nutzerstudie oder eine Prüfung produktiver VTT-Aktionen ist damit nicht behauptet.

Aufbewahrung: Research/Audit. Quellenlinks sind Primärquellen; wissenschaftliche PDFs werden nicht erneut veröffentlicht. Belege und Mockups ersetzen keinen späteren integrierten Rollen-/Funktions-/Touchtest.
