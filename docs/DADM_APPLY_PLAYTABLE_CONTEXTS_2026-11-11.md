# Apply P1: verbindlicher Kontextvertrag

status: Entwurf abgeschlossen, Übergabe Deploy innerhalb autorisierten Programms.
input_summary: Discover P1, Owner-Entscheidung 01.11., Programmauftrag zur Umsetzung.
artifacts: Kontextmodell/-dienst, HTTP-/Socketintegration, getrennte
Player-/DM-Komposition und Negativtests; retention permanent.

## Entscheidungen und Schnittstellen

- Additive `play_table_contexts`-Tabelle: opake zufällige Capability nur gehasht
  speichern; Nutzer, Kampagne, Session, Modus, Tab-Bindung, Ablauf (acht Stunden),
  ausstellende Login-JTI, Widerruf und Socket-Bindung gehören zum Datensatz.
  Keine Rolle aus Clientflags. Die Capability delegiert Socketnutzung für ihre
  explizite Laufzeit; Login-Widerruf, Logout und Rechteentzug entziehen auch diese
  Delegation. HTTP benötigt weiterhin einen gültigen JWT. Ein gebundener Socket
  darf nach Access-JWT-Ablauf dessen Signatur/Identität prüfen, solange seine
  serverseitige Capability und die ausstellende nicht widerrufene Login-Sitzung
  gültig bleiben. Er erhält dadurch keine neuen Rechte oder längere Kontextlaufzeit.
- POST `/api/play/campaigns/:c/sessions/:s/contexts` verlangt JWT/CSRF und einen
  expliziten Modus. DM nur bei aktueller DM-/Co-DM-/Owner-Berechtigung; Player
  bleibt Player, auch beim Owner. Kontext ist an authentifizierten Nutzer gebunden.
- HTTP sendet `X-VTT-Context` und `X-VTT-Tab`; alle sessionbezogenen Play-/Legacy-
  APIs verlangen einen gültigen passenden Kontext. Ungültige/fehlende Kontexte
  geben 403 vor Fachmutation. Zusätzlich mitgesendete Kontexte werden auch bei
  Nebenwegen validiert. Sheet-to-table verlangt für explizite Tischziele denselben
  Kontext; ohne Kontext bleibt ein eigener Bogenwurf lokal.
- Alte `/api/sessions/:id`-Initiativ-/Verwaltungswege bieten keine geprüfte
  Playerprojektion; sie bleiben ausschließlich für einen gültigen DM-Kontext
  zugänglich. Player verwenden die aktuelle gefilterte Combat-Schnittstelle.
  Chatmoderation und Assetbearbeitung übernehmen die Einschränkung mitgeführter
  Kontexte; private Chatänderungen werden ebenso wie Würfe rollenbezogen verteilt.
- Socket-Join übermittelt dieselben Werte; eine Capability bindet höchstens eine
  aktive Verbindung. Folgeereignisse verwenden ausschließlich die gespeicherte
  Bindung und prüfen Nutzer, Kampagne, Session, Ablauf und aktuelle Mitgliedschaft.
  Ein Wechsel entfernt vorherige Sitz-/Rollenräume. Vor Auslieferung in Tischräume
  werden ungültige Bindungen entfernt; direkte Socketantworten sind durch den
  Eingangs-Guard geschützt. Moderationspfade bekommen keine Player-DM-Eskalation.
- Keine Kontextautorität aus `sessionStorage`: dort liegen ausschließlich bereits
  servererteilte Capability/Bindung. Eine kopierte aktive Verbindung wird verweigert.
  Reload/Reconnect behalten nur ihren validierten Modus. Expliziter Wechsel
  widerruft den alten Kontext und erstellt einen neuen; andere Tabs bleiben unabhängig.
- Globale TableSeat-Zeilen verleihen nach Umstellung keine Befugnis. Fehlender
  Kontext führt insbesondere nicht auf Kampagnen-Ownerrechte zurück. Allgemeine
  Kampagnenverwaltung bleibt separat; Tischverwaltungsaktionen aus ihren expliziten
  Bedienelementen treten in einen autorisierten DM-Kontext ein. Ein bereits aktiver
  Playerkontext wird dafür nicht automatisch hochgestuft.
- Player-/DM-Komposition bekommen getrennte JS-Module. Die gemeinsame Basisseite
  enthält keine DM-Templates; DM-Fragmente werden erst über einen kontextgeprüften
  Endpunkt nachgeladen. DM-spezifische Initialisierung wird nur vom DM-Modul geladen.
  Gemeinsame Würfel-/Karten-/Tokenlogik bleibt in der bestehenden Laufzeit.

## Risiken, Tests und Rückweg

risks_and_assumptions: mittlere Entwurfsrisiken durch die oben festgelegten
Guard-/Binding-/Kompositionsverträge behandelt; Deploy bleibt von ihren Tests
abhängig. Kein neuer Paket-/Architekturentscheid ist während Implementierung nötig.
Die additive Tabelle wird vor Umschaltung gezielt angelegt; bestehende Daten werden
nicht verändert. Altes Image ignoriert die Tabelle. Rückweg ist das gesicherte
Tilesheet-Image, ohne Tabellenlöschung oder Datenbankrückmigration.

Akzeptanz: fehlend/falsch/abgelaufen/fremd 403; Player kann weder DM-Bootstrap noch
DM-Aktion noch DM-Socketereignis erhalten/ausführen; Owner-Player und paralleler
DM-Tab; Mitgliedschafts-/DM-Entzug vor weiterer Datenzustellung; Reload/Reconnect;
alle bestehenden Session-HTTP-Routen durch gemeinsamen Guard abgedeckt; Player-DOM
und geladene Initialisierung ohne DM-Steuerung. Live beider Rollen über Kampagne.
Quelle: [Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/implementation_notes.html),
[python-socketio](https://python-socketio.readthedocs.io/en/stable/server.html),
[MDN sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage).

next_step: Deploy implementiert diesen Vertrag, führt fokussierte Tests aus,
committet/pusht und liefert nach Schema-/Rückwegprüfung app-only live; Monitor
erfasst Sourcecommit, Image, UI-Wege und tatsächliche Ergebnisse.
