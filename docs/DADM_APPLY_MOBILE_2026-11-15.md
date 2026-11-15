# Apply: Mobile DM-Kernabläufe, 2026-11-15

- status: complete
- input_summary: Discover-Befunde und autorisierte Live-Auslieferung vor 15 Uhr.
- artifacts: diese Spezifikation, retention_class=durable; Browser-Proofs beim Deploy.
- risks_and_assumptions: Engine-Tests ersetzen keine physische Geräteabnahme; siehe unten.
- next_step: Deploy der beschriebenen Gesten und sichtbaren DM-Bedienelemente.

Grundlage: [Discover](DADM_DISCOVER_MOBILE_2026-11-15.md). Umsetzung und Live-Release
sind durch den heutigen Auftrag autorisiert. Kein Schemawechsel, keine neue
Rollenarchitektur und keine Änderung an HTTP-/Socket-Autorisierung.

## Ziel und Verträge

1. Nur die Kartenfläche bekommt `touch-action:none`. Ein Finger bewegt im
   Pan-Werkzeug die Karte, auch beim Start auf Tokens. Im Auswahlwerkzeug bewegt
   er einen berechtigten Token. Zwei Finger zoomen und verschieben die Karte;
   Beginn der zweiten Berührung bricht einen laufenden Token-Drag ab.
2. Pointer-IDs trennen gleichzeitig aktive Finger. `pointercancel`, Fensterverlust
   und Wechsel in Mehrfingerbedienung verwerfen ungespeicherte Drag-/Auswahlzustände.
   Abbruch speichert keine Position; normale Freigabe nutzt bestehende versionierte
   Tokenmutationen. Nach Pinch entsteht weder Tokenplatzierung noch Geisterklick.
   Ergänzung nach dem Pointer-Proof: Touch-Drag öffnet kein Token-Sheet; erst
   Freigabe ohne Bewegung merkt einen Tap vor. Sein folgender Klick öffnet die
   Details innerhalb des bereits festgelegten Event-Pfads, ohne dass derselbe
   Klick einen neu montierten Dialoghintergrund trifft. Ein Timer ist dafür
   keine verlässliche Schnittstelle. Desktop-Auswahl bleibt unverändert.
3. DM-Layers erhält einen sichtbaren Schalter **Mehrfachauswahl** mit aria-pressed.
   Aktiv: Antippen fügt Tokens hinzu/entfernt sie, ohne sie zu verschieben. Shift
   und Desktop-Auswahlrahmen bleiben bedienbar.
4. Sichtbare DM-Buttons **Kopieren** und **Einfügen** benutzen dieselbe interne
   Tokenzwischenablage wie die Tastatur. Einfügen per Button nutzt die Kartenmitte
   der Kartenansicht als Ziel im aktiven Layer. Koordinaten werden wie bei der
   bestehenden Zwischenablage an Kartengrenzen begrenzt; bei einer vollständig
   eingepassten kleinen Karte kann das Ziel dadurch randnah liegen.
   Kein OS-Clipboard-Zugriff und keine Browserberechtigung.
   Einfügen bleibt im Layers-Menü erreichbar, wenn keine Auswahl mehr besteht.
5. Mobile Auswahlbuttons mindestens 44px; Auswahlleiste begrenzt/scrollerbar,
   Dock und Pan-Werkzeug in Hoch- und Querformat erreichbar. Formulare mindestens
   16px auf schmalen Displays gegen unbeabsichtigten Eingabezoom.

## Akzeptanz und Verifikation

- Android-Touch/Chromium und iPhone-Touch/WebKit: autorisierten Tisch öffnen,
  Layer wechseln, mehrere Tokens ohne Tastatur auswählen, kopieren/einfügen,
  verbergen/freigeben; Player erhält weiterhin keine privaten Daten oder DM-Module.
- Echter Browser-Touch in Chromium: Drag speichert, Pan auf Token mutiert nicht,
  Pinch verändert Kartenzoom statt Seitenzoom, Abbruch speichert nichts.
- Hochformat 390x844 und Querformat 844x390: Menü, Layer, Auswahlaktionen,
  Initiative, Chat, Würfel und Journal bleiben erreichbar; Resize/Reload erhält
  serverautorisierte Rolle und gespeicherte Zustände.
- Bestehende Desktop-Layer-/Clipboard-Tests sowie gezielte Rollen-/Sockettests grün.
- Vor Release Quellcommit pushen, bestehende Compose- und Imageidentität prüfen,
  immutable Image bauen und gesamten ausgelieferten Quellbestand abgleichen.
- Nach Release HTTPS-Health plus authentifizierte Touch-Kernabläufe über vorhandenen
  Kampagnenhub prüfen. Vorheriges Image `714f277c8` als Rollback erhalten.

## Tradeoffs und Deploy-Übergabe

Kleine, lokale Erweiterung bestehender Pointer- und DM-Module. Zwei Finger nehmen
auf der Karte das Browser-Pinch in Anspruch; außerhalb bleibt Browserbedienung
unverändert. Zoombuttons bleiben Alternative. Keine Behauptung vollständiger
Hardwarekompatibilität: virtuelle Tastatur, App-Tracking-Schutz, alte WebViews,
große Karten, Screenlock und komplexes Wand-/Lichtauthoring benötigen Geräteabnahme.
Diese Einschränkungen sind offen dokumentiert und blockieren die begrenzte
Kernablauf-Verbesserung nicht. Deploy implementiert nur diese Verträge und
protokolliert verbleibende Lücken mit konkretem Status.
