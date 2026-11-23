# Discover: freie Kartenansicht und lesbare Szenen

Status: Faktenaufnahme abgeschlossen. Input: Owner-Screenshot mit zerdrückten Szenennamen/Verwaltungsbuttons; Auftrag, über Kartenränder hinaus zu navigieren, Ecken zu zentrieren und die ganze Karte einzupassen. Keine neuen Agents.

Live-Basis: Quelle `3fd012f4251e580a76e3f093ee143e13687e4480`, Image `sha256:4c87060242643b534394516c0a458974c716fd84bc742a84d587b7e72451e516`. Neuer isolierter Branch off dem gepushten UI-Lieferstand. Die Bot-Lanes sind nicht betroffen.

Fakten: `_renderLayers` in play-ui.js legt Thumbnail, editierbaren Namen und sechs Aktionen nebeneinander. Die frühere 22-Pixel-Iconreihe trifft auf die neuen 44-Pixel-Mindestziele; im 360-Pixel-Fenster bleibt kein Raum für das Namensfeld. `PlayFeedbackDM.renderParents` hängt die Hierarchie an denselben verengten Bereich. Die Hierarchiefunktion und bestehenden Handler sind vorhanden.

Die Kartensteuerung in play-ui.js verwendet `scrollLeft/scrollTop` mit einem auf die skalierte Karte begrenzten Spacer. Browser klemmen negative Scrollpositionen. `_setZoom` begrenzt zusätzlich auf mindestens 20 Prozent; `_zoomFit` berücksichtigt untere Bedienleisten nicht. Pinch und Pan referenzieren diese Scrollpositionen. Andere Kartenfunktionen rechnen überwiegend aus der tatsächlichen Bounding-Box und dem Zoom in Weltkoordinaten zurück. Karten-/Token-/Wandmodelle und Servergrenzen sind unabhängig davon.

Inventar: play-ui.js, play-feedback-dm.js, Playtable-Template/CSS, vorhandene Browserreisen für Touch, Clipboard, Kartenpräsentation, Fenster und Rollen. Keine neue Bibliothek oder Migration erforderlich. Risiken mittel: inverse Koordinaten, Touch/Pan, Fokus und Rollen; durch gezielte Eingabe-/Dateninvariantenprüfungen vor Lieferung zu behandeln. Keine offene Rückfrage blockiert den autorisierten Korrekturumfang. Artefakt permanent; nächster Schritt Apply.
