# Apply P2: Charakteraktionen, Quittungen und Wiederaufnahme

status: Entwurf abgeschlossen, Übergabe Deploy. input_summary: Discover P2,
autorisierter Programmplan. artifacts: Modelle, API, bestehende Würfelpfade,
Hotbar-UI und Mehrteilnehmertests, retention permanent.

## Daten- und Ausführungsverträge

- Additive `character_hotbars`: eindeutig je Nutzer/Charakter, maximal zehn Slots
  mit deklarativen aktuellen Katalog-IDs; Layoutrevision für vergleichendes Update.
  GET/PUT `/api/play/campaigns/:c/sessions/:s/characters/:id/hotbar` verlangen den
  P1-Kontext, einen an diesem Tisch verknüpften berechtigten Charakter/Token.
- Katalog aus autoritativer SRD-Auswertung und vorhandenem Inventar: Attribute,
  Fertigkeiten, Rettungswürfe, Initiative, Waffenangriff/-schaden, Zauberangriff.
  Bekannt/vorbereitet ausgewählte benannte Zauber können ausdrücklich angekündigt
  werden; Ressourcen/Effekte bleiben dabei manuell, die UI benennt diese Grenze.
  Keine vorgetäuschte automatische Zauberwirkung oder frei ausführbare Skripte.
- Layout speichert Referenzen, keine Boni. Ausführen verlangt aktuelle Katalog-
  Revision, gültigen Kontext, Ressource, Spielmodus und Aktion. Entfernte Einträge
  bleiben als ungültig erkennbar; kein Ersatz durch eine ähnlich benannte Aktion.
  Würfe delegieren an die bestehenden SRD-Würfel-/Inventarpfade; Ergebnisherkunft
  und Ressourcenprüfung werden nicht separat nachgebaut.
- Additive `table_request_receipts`: Kontext, Request-ID, kanonischer Request-Digest,
  Zustand und bestätigte JSON-Antwort; eindeutige Kontext-/Request-Paarung. Vor
  Ausführung atomar claimen. Wiederholung derselben Anfrage liefert dieselbe
  Quittung ohne weiteren Broadcast. Anderer Inhalt zur ID: 409. Unterbrochene
  Ausführung mit noch offener Quittung wird nicht blind erneut ausgeführt; Zustand
  abgleichen. Retention 24 Stunden, danach kein unbegrenztes Exactly-once-Versprechen.
- Neue UI sendet stabile Request-IDs für Aktionen und Würfe. Bestehende generische
  APIs/Bogenwürfe bleiben kompatibel; wenn eine ID vorliegt, greift derselbe
  Dedup-Vertrag. Der neue persönliche Ausführungspfad verlangt die ID.
- Persistente Chat-ID ist Ereignisidentität. Reconnect setzt die Verbindungssequenz
  zurück und lädt den autoritativen Zustand sowie die letzten 100 sichtbaren
  Nachrichten; gleiche IDs erscheinen im jeweiligen Verlauf einmal. Ältere
  Nachrichten bleiben serverseitig über den bestehenden gefilterten Chatabruf
  verfügbar. Lücken und Serverneustart dürfen Würfelergebnisse nicht verschwinden
  lassen. Keine unautorisierte Historie aus anderen Sessions oder DM-Kontexten.

## Oberfläche und Prüfgrenze

Eigenen verknüpften Charaktertoken wählen → persönliche Leiste → „Belegen“.
Slots per beschrifteten Feldern wählen, entfernen und umordnen; Tastatur und
ergänzendes Drag-and-drop. Leere Plätze werden im Bearbeitungsmodus dargestellt.
Generische Aktionen und bestehende Zielwahl bleiben daneben zugänglich.
Shortcuts nur außerhalb Textfeldern/Dialogs; Ausführung zeigt erst nach Server-
bestätigung Erfolg. Offline kein ungeprüftes späteres Abfeuern gespeicherter Würfe.

risks_and_assumptions: mittlere Risiken sind durch Claim/Quittung, wiederholte
P1-Autorisierung und Katalogversionierung im Entwurf behandelt; Deploy-Gates
verlangen Positiv-/Negativtests. Quittung kann nach Prozessabbruch „in Bearbeitung“
bleiben: Abgleich statt zweiter Ausführung ist die bewusste sichere Fehlerform.
Additive Tabellen, Backup vor Anwendung, altes P1-Image als Rückweg; keine Änderung
vorhandener Charakterdaten. Neue App-Abhängigkeiten sind nicht erforderlich.

Akzeptanz: persönliche persistente Belegung getrennt je Figur/Nutzer; fremde
Ressourcen/Referenzen verweigert; identische Request-ID würfelt genau einmal;
Firefox↔Firefox und Chromium↔Firefox mit Reconnect, gleicher Chat-ID, verpasstem
Wurf und isolierter zweiter Session. Owner-Player aus P1 bleibt geschützt.

Recherche: [Socket.IO-Zustellung](https://socket.io/docs/v4/delivery-guarantees/)
und [Python-Server](https://python-socketio.readthedocs.io/en/stable/server.html).
next_step: Deploy implementiert diese begrenzten Verträge, prüft sie gezielt,
committet/pusht und liefert mit Live-Nachweisen vor Fortsetzung zu P3.

## Live-Nachtrag: Übergabe einer noch nicht geschlossenen Verbindung

Der Produktionsabgleich ergänzt den Reconnect-Vertrag: ein neuer Transport darf
nicht auf das verzögerte Schließen des alten TCP-/Polling-Transports angewiesen
sein. Vor jedem Socket-Join rotiert ein authentifiziertes HTTP-Resume die opake
Capability desselben Kontextdatensatzes vergleichend. Rolle, Loginbindung,
Session und Ablauf bleiben serverbestimmt; die alte Capability und SID werden
ungültig, der alte Socket geschlossen. Parallele unabhängige Kontexte bleiben.
Request-Quittungen behalten dieselbe context_id, also auch nach dieser Übergabe
ihre Dedup-Wirkung. Ohne gültige alte Capability keine Wiederaufnahme; kein
Owner-/DM-Fallback. Autorisierung und Empfängerauswahl verlangen zudem die aktuelle
SID. Dies ist ein begrenzter Reconnect-Fix im bestehenden P1/P2-Vertrag.
