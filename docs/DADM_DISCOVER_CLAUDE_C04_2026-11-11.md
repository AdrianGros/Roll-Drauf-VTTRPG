# Discover C04 – vorhandene 2D-Kartenpipeline

Status: Inventur abgeschlossen, nächster Schritt Apply. Profil standard,
Aufbewahrung dauerhaft. Input R15–R19/R25–R27; noch keine Kartenimplementierung.

- Private Bibliothek liegt in `vtt/endpoints/mapmaker.py` (Blueprint Mapmaker),
  `MapmakerProject` und `static/mapmaker/js/library.js`. List/Get/Save/Delete,
  Eigentümerprüfung, Kontowechselheader, CAS-Revision und Storagequote vorhanden.
  Dokumente sind begrenztes `rd-mapmaker`-JSON, keine öffentlich freigegebenen Karten.
- Das Projektmodell speichert Metadaten und JSON-Storage-Key, keine PNG-Vorschau.
  `normalize_document` in `vtt/mapmaker_document.py` validiert bekannte Felder und
  PNGs; beliebige URLs/Pfade/ausführbare Inhalte werden nicht akzeptiert.
- `Library.open` validiert gegen bekannte Assets, lädt benötigte Bilder, materialisiert
  Raster-/Vektorebenen und prüft unveränderte Dokumentgeneration während des Ladens.
- `Editor.renderPngBlob` und `Renderer.renderExport` sind vorhandene Browser-
  Exportseams einschließlich Dokumentgeneration und Künstler-Credits. Automatische
  Übernahme kann nicht einfach eine nicht vorhandene Server-PNG-Vorschau kopieren.
- Werkzeuge/History: Raster-Brush/Radierer zielt auf Rasterebene; Tiles haben eigenen
  `erase`-Modus und Zellen-Undo. Ein allgemeiner Radierer wechselt derzeit über
  `targetLayer('raster')`. Das erklärt die Kachel-/Symbolbeobachtung.
- History maximal 60 Schritte und 64 MiB; ein zu großer Schritt leert die History.
  Neue Flächenoperationen müssen diesen vorhandenen Vertrag einhalten oder vorab
  als zu groß verweigert werden. Kein stilles „Undo vorhanden“ bei Budgetüberschreitung.
- Neue Kenney-/2DPIXX-/Castle-Pakete bereits integriert. Zusätzliche von Matt erwähnte
  Dateien liegen nicht als neue Eingabe vor. P4-Kalibrierung trennt Pixelraster und
  physisches Maß; Karteneditor-/Projektpixel bleiben kanonisch.

Medium: Renderstand, Projekt-ID und Revision müssen bei Bibliothek→Tisch zusammen
gehören; paralleles Speichern darf kein anderes PNG einschleusen. Medium: private
Projekte nicht über öffentliche URLs/fremde Kampagnen öffnen. Medium: exportiertes
Tischbild ist eine neue bewusst geteilte Fläche, kein dauerhafter Live-Link zur
privaten Projektquelle. Medium: Raster-/Tile-/Symbol-Radiergeste samt Undo-Budget.
Low: große Palette/Assetladezeiten, vertraute Dateimenüs und Attribute erhalten.

Nächster Schritt: Apply mit vorhandener clientseitiger PNG-Renderpipeline, eigener
expliziter Snapshot-Übernahme im berechtigten DM-Kontext, Projekt-/Revisions-CAS,
Lizenznachweis und begrenzter Vorschau. Separat gerasterte Flächen-/Symbolgeste
mit einem Undo, optionales Stempelraster und Kachelpinsel. Kein 3D-Renderer.
