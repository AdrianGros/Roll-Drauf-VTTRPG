# B03 – Verbranntes Buch und gemeinsame Kartenwerkstatt

Status: Apply abgeschlossen; Umsetzung folgt nach der B02-Prüfung.
Input: S02/S17/N19. Der aktuelle Nachtmodus ist kontrastkorrigiert, aber flächig violett;
die Werkstatt verwendet bereits dieselben Schriftfamilien und teilweise gemeinsame Tokens.

## Vertrag

Die vorhandenen semantischen Farbvariablen erhalten nachts warme Kohle-/Papierbrauntöne,
helle Pergamenttinte und einen roten Standardakzent. Die persönliche Auswahl Bronze/Petrol
bleibt erhalten; der ausdrücklich gewünschte rote Nachtstandard geht einer alten automatisch
übernommenen Brandingfarbe vor. Tagesmodus und gespeicherte Präferenzschlüssel bleiben gültig.

Seiten und Einband werden mit CSS-Verläufen, feinen Linien und inneren Rand-/Bundschatten
als versengtes Buch dargestellt. Unter langen Texten bleiben kontrastgeprüfte ruhige Flächen;
keine neuen Rasterbilder, Laufzeitbibliotheken oder Farbeingriffe in Kartenpixel.
Die Kartenwerkstatt erhält dieselben Panel-, Feld-, Linien- und Schrift-Tokens. Werkzeuge,
Abstände und Kartenfläche bleiben erhalten; die positive Werkstattreferenz wird nicht durch
eine neue Bedienarchitektur ersetzt.

## Kriterien / Risiken / Handoff

Paper/Night, DE/EN, 390px und große Ansichten in Buch, Creator, Regelansicht, Tisch und Editor
prüfen. Nachts sichtbar warme Buch-/Pergamentränder und roter Standard; persönliche Akzente
funktionieren weiterhin. Kontrasttests messen tatsächlich zusammengesetzte Farben, inklusive
Verläufen. Keine neue seitliche Überbreite; Karte/Canvas unverändert.

Medium-Risiko Text auf neuen Materialflächen: bestehende Kontrasthelfer und gezielte Browser-
Reisen vor Release. Low: dezente Textur zugunsten ruhiger Leseflächen; keine Shader oder Filter
auf dem gesamten Inhalt. B02-Tischkomposition und Rollen bleiben verbindlich.

Keine Schema-/Abhängigkeitsänderung. Deploy: gezielte Präsentationschecks, Commit/Push, laufendes
Image erneut abgleichen, vorhandener App-Release mit vorherigem Image als Rollback, Live-
Darstellung über die normalen Einstiege und Belege erfassen. Retention: dauerhaft.
