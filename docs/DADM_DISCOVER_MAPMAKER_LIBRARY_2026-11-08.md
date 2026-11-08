# Discover: persönliche Kartenbibliothek

## Auftrag und Istzustand
Der Owner beauftragt einen Startdialog mit vorhandener Karte, leerer Karte und
Template sowie private, erneut bearbeitbare Karten pro Nutzer mit zugewiesenem
Speicher. Die vorangegangenen vier Asset-Batches bleiben vollständig erhalten.

`vtt/static/mapmaker/js/app.js` öffnet bisher automatisch die Silbermark.
`document.js` besitzt bereits ein begrenztes, vollständig editierbares JSON-v1-
Format einschließlich PNG-Malebenen, Vektorelementen und Asset-Ausschnitten.
`storage.js` schreibt nur einen browserweiten IndexedDB-Entwurf. Dateiimport,
Projekt-/PNG-Export und Künstler-Credits sind vorhanden.

`User.storage_quota_gb` und `storage_used_gb` existieren. Live sind Player
überwiegend mit 5 GiB und DMs mit 20 GiB ausgestattet; Headmaster ohne Limit.
Ein Player hat noch kein Kontingent. Bestehende Regeln gewähren ohne Zuteilung
keinen Upload. Die Kampagnen-Asset-Bibliothek verlangt eine Kampagne und ist kein
Speicher für persönliche Editorprojekte. Die Storage-Abstraktion unterstützt
lokale persistente Volumes und S3. Live: local, `/data/vtt-assets`, Requestlimit
64 MiB. Bestehende Uploads reservieren den gemeinsamen Nutzerzähler atomar.

## Abhängigkeiten und Lieferstand
Flask/JWT/CSRF, SQLAlchemy, Pillow und Storage-Adapter sind vorhanden; keine neue
Dependency nötig. Bestehender UI-Einstieg: Hauptnavigation → Karten.
Live-Image bei Bestandsaufnahme: `sha256:e72a98bc24943c658d76038cb8554038c9e444cefd1f64373be682e10a5d879b`,
Tag `roll-drauf-vtt-app:mapmaker-color-b4-20261108-dd1084c4`. Backend entspricht
in den berührten Bestandsdateien `ec20e46fcb4846306466a0964fd8f58177f79d07`;
Mapmaker entspricht `dd1084c48b100ab7e227e8a806fb26a424773c4d`.
Compose-Projekt migration-production nutzt production.compose.json und
production.duck-species.override.yml in /srv/migration/2026-10-07/setup.
Der Hauptcheckout enthält zahlreiche fremde Änderungen. Der separate Checkout
`roll-drauf-vtt-map-library` basiert auf `2f731fe05`; die bestehende Assets-
Endpointdatei ist identisch mit Produktion. Eine vollständige Auslieferung dieses
Checkouts würde neuere Backendarbeit überschreiben und ist ausgeschlossen.

## Befunde, Annahmen und offene Fragen
- Medium, vor Apply zu lösen: gemeinsamer Quota-Zähler muss auch bei parallelen
  Karten-/Asset-Uploads stimmen; Ersetzen darf nur die Größendifferenz belegen.
- Medium, vor Apply zu lösen: globale lokale Entwürfe sind keinem Konto
  zuordenbar; neue private Entwürfe benötigen Kontobindung.
- Medium, vor Apply zu lösen: neuere Produktionsarbeit muss beim Release erhalten
  bleiben; Basis unmittelbar vor Release erneut abgleichen.
- Low: Dateien können bei Prozessabbruch zwischen Storage und DB verwaisen;
  Fehlerpfade und Wartungsgrenze müssen dokumentiert werden.
- Annahme: vorhandene Kontingente gelten gemeinsam für Karten und Asset-Uploads.
  Keine neue Tarifzuteilung oder Kampagnenfreigabe wird verlangt.
- Keine blockierende Produktfrage; bestehende Silbermark dient als erstes Template.

## Nächster Schritt
Apply definiert private Schnittstellen, Konflikt-/Quota-Transaktionen, Startdialog,
Migration und selektives Release auf das tatsächlich laufende Image.
