# Discover C05 – Landmassen im bestehenden Dokument

Status: Inventur abgeschlossen, Apply nach C04-Abgleich. Profil standard,
dauerhaft. Input P5/R29: Seed, Insel/größere zusammenhängende Landmasse,
Landanteil/Küstenverlauf, begrenzte Auflösung, Vorschau/Abbruch und ein Undo.

`static/mapmaker/js/starter.js` enthält bereits deterministisches Mulberry-RNG,
mehrskaliges Value-Noise und eine Viertelauflösungs-Maske für eine feste
2400×1600-Startkarte. Der Generator erzeugt normale Rasterebenen, Stempel und
Beschriftungen; er ist kein frei parametrierbarer Landmassendialog. `brush.js`
stellt bestehendes Material „land“ und wiederverwendbare Canvas-Texturen bereit.
`document.js` begrenzt Seiten auf 256–4096 Pixel, 32 Ebenen, acht Rasterebenen
und 32 Millionen Rasterpixel insgesamt. Raster werden über vorhandene PNG-
Serialisierung in JSON/ZIP, lokale Sicherung und persönliche Bibliothek erhalten.

`Editor.canAddRaster`, `createLayer` und `layerCommand` sind vorhandene Seams für
eine zusätzliche Rasterebene. Ein neuer Canvas kostet Breite×Höhe×4 Bytes;
4096² sind bereits 64 MiB, also die gesamte Historygrenze. Weitere Vorher-/Nachher-
Kopien würden den Undo-Vertrag überschreiten. Das bestehende History.push kann
bei zu großen Befehlen alle alten Schritte verwerfen und ist kein Preflight.

Medium: Rechenarbeit im UI-Thread kann Vorschau/Abbruch blockieren. Medium:
Rastern in eine vorhandene Ebene verändert Zeichnungen und benötigt mehrere
Speicherkopien. Medium: alte Vorschau darf nach Projekt-/Parameterwechsel nicht
übernommen werden. Medium: neue Metadaten im Dokument würden den aktuellen
Client-/Server-Importvertrag ändern und müssten ausdrücklich entworfen werden.
Low: Browser dürfen die Darstellung interpolieren; zugesicherter Determinismus
betrifft die Generator-Maske, nicht jeden gerenderten Schrift-/Canvas-Pixel.

Nächster Schritt Apply: vorhandene Noise-/Raster-/Materialseams abgleichen,
Generatorversion und Parameterbereich festlegen, Rechen-/Speicherbudget und
Abbruchgrenze messbar definieren, Vorschau von Dokumentschreibzugriff trennen.
Kein Klima-/Fluss-/Siedlungssystem, keine neue Bibliothek und keine 200-%-Grenze.
Web-Primärquellen geprüft am 2026-11-11: [Worker](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Using_web_workers),
[übertragbare Buffer](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Transferable_objects),
[ImageData](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/createImageData).
