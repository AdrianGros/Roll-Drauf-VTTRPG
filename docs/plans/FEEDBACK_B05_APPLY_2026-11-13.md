# B05 – Auswahl, Objekte und Wege

Status: Apply abgeschlossen; Implementierung nach B04-Checks. Retention: dauerhaft.
Input N12–N17. Bestehende Objekte besitzen IDs, Rasterkacheln hingegen Zellkoordinaten;
Einzelauswahl und Shift-Wegpunkte existieren, der Auswahlhintergrund verschiebt bisher die Ansicht.
Alle Assetbilder liegen bereits im zugelassenen gemeinsamen Katalog; Kacheln sind darin markiert.

## Vertrag

Auswählen (V): Ziehen auf freier Fläche bildet einen sichtbaren Auswahlrahmen; Space/Mausmitte
bleiben Verschieben der Ansicht. Shift-Klick erweitert/reduziert die Objektauswahl, Escape löscht
sie. Sichtbare Symbole, Beschriftungen und Wege werden über ihre vorhandenen Grenzen gewählt.
Rasterflächen bleiben davon ausgenommen. Auf einer aktiven Kachelebene wählt derselbe Rahmen
belegte Zellen dieser Ebene. Objekt- und Zellgruppen sind getrennte Auswahlen; keine implizite
Umwandlung, keine Selektion unsichtbarer Ebenen.

Die primäre Objekt-ID bleibt für bestehende Inspector-/Ortsnavigation kompatibel; transiente
Gruppenreferenzen werden nicht persistiert. Gruppen lassen sich gemeinsam verschieben und löschen,
mit genau einem Undo-Schritt je Geste. Gemeinsame Skalierung für reine Symbol-/Textgruppen folgt
den vorhandenen Größenlimits; gemischte Gruppen und Wege behalten Einzelinspektoren für Größe.
Kachelgruppen verschieben sich in ganzen Zellen. Fremde belegte Zielzellen werden nicht still
überschrieben; ungültiges Verschieben wird verworfen. Gemeinsames Löschen/Undo stellt Reihenfolge,
Zellassets und sämtliche Objekte wieder her. Abgebrochene Gesten werden nicht autosaved.

Neue Wege können geglättet oder geradlinig sein. Ein optionales boolesches `curve` in bestehenden
Path-Objekten (fehlend=false) wird von JS und Python gleich validiert. Quadratische Kurven über
vorhandene Punkte; Trefferprüfung verwendet dieselbe geglättete Geometrie, Grenzen bleiben in der
konvexen Hülle. Bestehende Wege ändern ihr Aussehen nicht. Sichtbarer „Wegpunkte bearbeiten“-Modus
ermöglicht Punktziehen ohne versteckten Modifikator; Shift bleibt kompatibel.

Ein Ort/Symbol darf ohne Text bestehen, wenn ein sichtbarer Pin oder ein zugelassenes Symbol
vorhanden ist. Reine unsichtbare leere Beschriftungen bleiben unzulässig. UI-Platzierung bietet
„Name anzeigen“; Listen bekommen einen verständlichen Ersatznamen. Entfernen von Text/Pin/Symbol
bewahrt diese Invariante, auch bei Dateiimport und Bibliotheksspeicherung.

„Symbole“, „Kacheln (Raster)“ und „Orte und Text“ erklären den Unterschied direkt an den Werkzeugen.
Die gewählte Rasterkachel kann bewusst als frei skalierbares Symbol platziert werden; gespeicherte
Raster werden nicht konvertiert. Rastergröße bleibt am Rasterwerkzeug sichtbar und separat von
Symbolgröße. Undo/Redo erhalten sichtbare Textbeschriftung und die vorhandenen Tastenkürzel.

## Recherche / Risiken / Kriterien

[MDN quadraticCurveTo](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/quadraticCurveTo)
beschreibt Kontroll-/Endpunkt der Canvaskurve. Rendern und Trefferprüfung verwenden dasselbe
`Path2D` mit [isPointInStroke](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/isPointInStroke);
damit ist keine ungenaue separate Polygonannäherung oder zusätzliche Bibliothek nötig.
[W3C Toolbar](https://www.w3.org/WAI/ARIA/apg/patterns/toolbar/) verlangt passende Fokus-/Pfeilbedienung,
wenn Toolbar-Rollen verwendet werden. Vorhandene native Buttons bleiben native Buttons.

Medium Datenverlust bei Gruppengesten → Live-Vorschau reversibel, ein gemeinsamer History-Befehl,
Cancel/Pinch/Undo/Redo und Autosave-Roundtrip gezielt prüfen. Medium JS/Python-Schemadrift → gemeinsame
Dateifälle für alte/neue Kurven und namenlose Symbole. Medium Kachelkollision → keine Überschreibung.
Keine neue Abhängigkeit oder Datenbankmigration, keine Server-/Player-Berechtigungsänderung.

Deploy-Handoff: erst der hier beschriebene Umfang, gezielte echte Editor-Browsergesten auf Desktop
und Mobil, Bibliotheks-Roundtrip, Commit/Push, vorhandener App-Release auf aktuellem Image,
Live-Einstieg Karten → eigene Bibliothek und Lieferbeleg mit Rollback. Keine stillen Pinseländerungen
(B06), keine vollständige Zusammenlegung verschiedener Dokumentarten.
