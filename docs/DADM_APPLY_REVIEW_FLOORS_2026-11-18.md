# Apply K22: private Etagenbilder und Balkonsicht

18.11.2026 · DAD-M standard · Status: begrenztes Design von Koordination akzeptiert, Deploy-Handoff. Basis `49e8b9944`; Aufbewahrung dauerhaft. Benutzerauftrag autorisiert Umsetzung; dieses Supplement konkretisiert die Forschungsgrenze R07 und den übergeordneten Web-Apply.

## Grenze

Eine Etage ist eine private, deckungsgleiche PNG-Bildebene einer bestehenden Kampagnenkarte. Der DM ordnet bis zu acht Etagen, wählt die aktive Etage und entscheidet ausdrücklich, ob transparente Bereiche/definierte rechteckige Öffnungen auf darunterliegende Etagen durchsehen lassen. Der Server komponiert aktive und tiefere Bilder und wendet für Player die bestehende 2D-Wand-/Licht-/Aufklärungsprojektion an. Höhere Etagen und private Quelldateien werden nicht mitgeliefert.

Dies ist echte serverseitige Bildkomposition für mehrere Stockwerke, kein 3D-Sichtmodell. Bestehende Tokens, Wände und Lichter bleiben Objekte der gemeinsamen 2D-Karte; Höhenabhängigkeit von Spielmechanik und Tokenübergänge werden nicht erfunden. Diese Grenze ist im normalen DM-Dialog sichtbar. Alte Karten sind unverändert, solange die neue Etagenfunktion nicht ausdrücklich eingeschaltet ist.

## Daten und Ressourcen

- Additive `map_floor_decks`: map_id als PK/FK, revision, enabled, active_floor_id. Der aktuelle Floor wird in derselben gesperrten Transaktion mit der zugehörigen Bildmenge validiert.
- Additive `map_floor_images`: id, map_id, order_index, name, reveal_below, openings (höchstens 32 Rechtecke), storage_key/provider, png_sha256, size_bytes, width/height, request_id, input_digest, created_by. Eindeutiger Request je Karte; Uploadwiederholung verändert den Bestand nicht.
- Quellen gehen durch den vorhandenen Storageadapter in nicht-öffentliche Schlüssel `users/<campaign owner>/map-floors/...`. Es entstehen keine über die allgemeine Kampagnen-Assetliste lesbaren Asset-Zeilen. Rohbildzugriff ist ein ausschließlich DM-kontextgeprüfter Endpunkt.
- Maximal 8 Etagen, 4 MiB PNG je Quelle, 16 MiB Quelldateien je Karte, 16 Millionen Quellpixel insgesamt; höchstens 2048 Pixel pro Seite, exakte Übereinstimmung mit Kartenweltgröße. PNG-Signatur, Decoderformat, vollständiges Dekodieren und Größenprüfung. Keine URL-Downloads, Skripte, SVG, GIF oder externen Dienste.
- Speicherverbrauch wird der Kampagnenbesitzerin zugeordnet und unter ihrer vorhandenen User-Zeilensperre mit bestehender Quotenlogik reserviert. Alle Floor-Schreiber sperren Besitzer vor Karte. Dateischreibfehler rollen Reservierung/DB zurück und entfernen nur das eigene neue Objekt; Entfernen einer Quelle gibt deren gespeicherte Bytezahl frei.

## Schnittstellen

Neue Blueprint `floor_layers_bp`, unter `/api/play/campaigns/<campaign>/sessions/<session>`:

- `GET /maps/<map>/floors`: nur autorisierter DM-Kontext; vollständige Liste ohne Storagekeys/PNG-Bytes.
- `POST /maps/<map>/floors`: multipart revision, request_id, name, reveal_below und file. Vollständige alte Karte nicht verändern; erste Quelle wird aktive Etage, Einschalten bewusst separat.
- `PUT /maps/<map>/floors`: revision + enabled + active_floor_id + geordnete floor_ids. Exakte bekannte Menge; keine fremden IDs.
- `PUT /maps/<map>/floors/<floor>`: revision + Name/reveal_below/Öffnungsrechtecke. Pixelkoordinaten innerhalb der Bildgröße, positive Flächen, keine verschachtelten Fremdressourcen.
- `DELETE /maps/<map>/floors/<floor>` mit revision: entfernen und aktive Auswahl auf vorhandenen Nachbarn normalisieren; keine Quelle mehr deaktiviert das Deck.
- `GET /maps/<map>/floors/<floor>/image`: nur DM-Kontext, gleiche Karte, keine allgemeinen Assetrechte.
- `GET /floors/view`: jede gültige Tischrolle, ausschließlich aktuelle aktive Karte. Liefert enabled, Karten-ID, opaken view_key, aktuellen Namen und finales PNG als data URL; keine Floor-IDs, Reihenfolge, Öffnungen, Quellreferenzen oder höhere Ebenen. Bei gleichem view_key `unchanged:true`. Fehlende/geänderte Quellen scheitern geschlossen und zeigen dem Player kein vollständiges Ersatzbild.

Alle Änderungswege verwenden aktuelles Kampagnen-/Session-/Kontextrecht, Owner-as-Player bleibt Player. CAS-Revision und Kartensperre verhindern verlorene Änderungen. Der opake view_key ist serverseitig HMAC-abgeleitet und an Rolle/Akteur gebunden; Clientangaben bestimmen keine Sichtrechte. Antworten `private,no-store`.

## Darstellung und Integration

- Gemeinsamer `play-floor-view.js` enthält ausschließlich aktive Darstellung und zustandsgebundene Aktualisierung. Er liefert eine alternative Quelle für `mapImage`, verwirft alte Kartenantworten, begrenzt Polling und entfernt Objekt-URLs/Timer beim Verlassen. Bei aktivem Deck bleibt bereits maskiertes Playerbild die Quelle; bisherige Browser-Lichtmaske wird nicht nochmals darübergelegt.
- Separater `play-floor-dm.js` wird nur im serverautorisierten DM-Kompositionszweig geladen/initialisiert. Einstieg „Etagen und Balkonsicht“ im vorhandenen Raster-/Lichtbereich, Dateiauswahl, Reihenfolge, aktive Ebene, Ein-/Aus, Transparenzschalter und Öffnungen mit expliziten Zahlenfeldern und Buttons. Keine Pflicht zum Draggen oder Doppelklicken.
- Koordination integriert die kleine PlayUI-/Template-/Feedback-Verkabelung; diese gemeinsamen Dateien werden hier nicht verändert. Module und CSS/DOM bleiben unabhängig von der Arbeit anderer Worker.

## Abnahme

1. Synthetisches rotes unteres und blaues oberes Bild: untere rote Fläche ist durch definiertes Loch sichtbar; ohne reveal_below schwarz, außerhalb Loch blau; höhere geheime Etage nicht enthalten.
2. Player und Owner-as-Player erhalten weder Rohbilder noch Konfiguration/Änderungsrecht. Fremde Karten-/Floor-IDs werden abgewiesen; nur aktuelle Karte hat einen Player-Bildweg. Revokation nach bestehendem Kontextvertrag.
3. Playerprojektion setzt vorhandene Wand-/Licht-/Fogmasken auf die tatsächlichen Bildpixel, nicht nur auf einen entfernbaren UI-Overlay. Keine Erweiterung der gespeicherten Aufklärung durch die Ansicht.
4. Ungültige PNGs, falsche Maße, Limits, Revisionskonflikte, Upload-Replay, Speicherfehler und Quoten werden geprüft. Keine Sourcekeys in JSON. Alte Karten erzeugen weiterhin ihren vorherigen Hintergrund und alte Lichtreise.
5. Browserreise der neuen DM-Bedienung und Playeransicht, Reload und Aktualisierung; tatsächliche normale UI-/Live-Verkabelung zusätzlich durch Koordination.

Risiken mittel: Speicher-/PNG-Aufwand (durch Allokations-/Bytegrenzen begrenzt), geheime Quellbilder (private Storagekeys und DM-Prüfung), veraltete Ansichten (Kontextprüfung pro Abruf, Karten-/Sequenzabgleich). Kein bekanntes High/Critical aus dieser begrenzten Prüfung; keine Aussage über andere Bild-/Assetwege. Neue Tabellen sind additiv; altes Image ignoriert sie. Rollback erhält Quelldateien für Wiederaufnahme. Weiterer Schritt: Implementierung, zielgerichtete Tests, Commit an Koordination; kein eigener Produktionszugriff.
