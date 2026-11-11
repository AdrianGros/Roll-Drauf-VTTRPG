# Discover P1: Tischkontexte

status: abgeschlossen. input_summary: Owner autorisiert Umsetzung des Programms
P0–P7 und Live-Lieferung; Quellen sind Programmplan und Entscheidung 01.11.
artifacts: dieser Bericht und nachfolgender Apply-Vertrag, retention permanent.

## Nachgeprüfter Bestand

Produktion verwendet inzwischen `roll-drauf-vtt-app:tilesheet-slicing-20261111-802321cd`,
Image `sha256:b9cf16b34a11bafce75c0e5c0e03284abb659e91134075d2261f55bdf1075ccc`.
Der bereits live laufende Slice `802321cd3` wurde als `26300984b` in den isolierten
Feedbackbranch übernommen. Frühere Feedbackfunktionen bleiben erhalten.
Compose-Dateien entsprechen weiterhin dem Programmplan.

Tischpfade liegen in `vtt/play/routes.py`, `vtt/campaigns/routes.py` (State,
Token, Combat, Kartenaktivierung, Start/Ende, Zuweisung), `socket_handlers.py`
(Join, Resync, Token, Chat/Würfel, externe Würfe), `community/routes.py`
und `characters/{sheet_link,srd_creator,species_actions,srd_party_routes}.py`.
`get_table_role` und zwei `_is_table_dm`-Hilfen verwenden globale TableSeat-Zeilen.
HTTP-Middleware läuft nicht bei Socket-Ereignissen. Rollenräume sind vorhanden;
nutzerbezogene Räume und ihre Snapshot-Skiplogik müssen parallele Modi beachten.
Die aktuelle Oberfläche verwendet DM-Templates und bedingte Bindings in einer
gemeinsamen JS-Datei. Authentifizierte Requests werden durch `auth.js` vermittelt.

## Risiken und Grenze

risks_and_assumptions: mittel – fehlender tabbezogener Kontextvertrag, veraltete
Empfangsräume und Legacypfade; mittel – additive Datentabelle benötigt gezielte
Schemaanwendung vor Appwechsel; niedrig – bestehende Clients müssen neu eintreten.
Keine allgemeine bestehende Rechteumgehung wird aus dieser Inventur behauptet.
Die konkrete Behandlung dieser Anforderungen ist Gegenstand des Apply-Vertrags.
Keine neue Laufzeitabhängigkeit erforderlich; vorhandene SQLAlchemy-/Socket-APIs
und Einzelprozess-Verbindungsverwaltung sind vorhanden.

next_step: Apply mit gespeichertem Kontext, separater Komposition, vollständigem
Guardvertrag und fokussierter Rollen-/Widerrufsmatrix; danach Implementierung.
