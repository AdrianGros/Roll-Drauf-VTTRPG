# Apply C00/C01 – Integrationsbasis und Abschluss der Präsentation

Status: Apply abgeschlossen; Übergabe des begrenzten C01 an Deploy.
Input: Owner „Go ahead“, Review R07/R08/R11/R14/R28, bisheriges P4-Apply,
Discover der neuen Reviews. Profil standard; Aufbewahrung dauerhaft.

## C00-Fakten und Grenze

Die neun erfassten eigenen P4-Nacharbeitsdateien wurden unverändert als
`1b2ffc330127ea8eb074532efafa585e562ba911` gesichert. Das ist ein Checkpoint,
keine Live-Lieferung. Katalogcheck: 2.356 vorhandene UI-Einträge baubar.
Es verbleiben unmarkierte Buch-/Kampagnen-Literale; die Kandidatenliste ist
nur Quellinventar, keine Erlaubnis beliebige Datenwerte zu übersetzen.
Aktuelles Live-Image beim Abgleich weiterhin `sha256:1f436745…`, Quelle 447774d57…;
neuere Kenney-Assets bereits integriert. C01 ändert keine Assets oder Serverregeln.

Claude 2.1.312: vorhandene First-Party-Pro-Anmeldung, konfiguriertes Modell Opus
wird geerbt. Read-only-Kontingentabfrage: 5-Stunden-Auslastung 0 %, Woche 76 %,
Extra Usage ausgeschaltet. Eine Implementierungssitzung gleichzeitig; kein API-
Fallback oder Einschalten zusätzlicher Nutzung. Werte sind Momentaufnahme.
Kein offener Architektur-/Berechtigungsentscheid für diese UI-Grenze.

## Ziel und Entscheidungen

1. P4-Präferenz-, Rollen-, Maßstabs- und Speicherschema bleiben unverändert.
   Bestehende explizite UI-Kataloge verwenden. Fehlende eigene UI-Literale in
   Buch-Buildern, Kapitel-/Statuslabels und Kampagnen-Seams markieren; dynamische
   Werte nur als Textparameter. Keine DOM-Pauschalübersetzung. Keine Quellnamen,
   Chats oder Homebrew-/Regeltexte anhand ihres Inhalts umschreiben.
2. Kataloggenerator prüft auch Zusatznachrichten auf DE/EN-Vollständigkeit und
   identische Platzhalter. Eigene Quellen zu `extra-messages.json` ergänzen;
   bestehende nummerierte Inventare nicht neu generieren. Generierte Bundles
   erzeugt die Koordination nach der Rückgabe.
3. Creator behält seine vorhandenen Controller/IDs/Schritte und erhält eine
   optisch konsistente Buch-/Blattkomposition aus vorhandenen Styles/Tokens.
   Kein zweiter BookScene-Router, kein neues Framework, keine Änderung an
   Erstellungs-/Regelmechanik. Hauptnavigation bleibt einmal vorhanden.
4. Bogen: während der asynchronen Initialisierung werden falsche alte Formular-
   /Bogenflächen nicht sichtbar. Vorhandenes Lade-/Fehlerfeedback bleibt sichtbar;
   korrekter Bogen erst nach Profilauflösung, kein dauerhaft versteckter Fehler.
   Doppelten zweiten Block aus Archiv/Kampagnen/CE-Navigation entfernen, normale
   Hauptnavigation und genau einen bestehenden Bearbeitungsumschalter erhalten.
   Standard-Bearbeitung und Upload-/Kopiermechanik gehören in C02.
5. Lesbare semantische Farben in beiden Ansichten auch für Buchübersichten und
   Creator. Canvas-/Dokumentfarben und globale Adminpalette nicht verändern.
   Keine zusätzlichen Animationen. Lokale Einstellungen und ungespeicherte
   Creator-Entwürfe bei Navigation/Sprachreload weiter schützen.

## Abnahme

- DE/EN × Pergament/Nacht in repräsentativer Matrix bei 320/390/1440 px, normale
  Hauptwege einschließlich Kampagnen-Hub, Creator, Bogen, Karten, Compendium, Eagle.
- Kein unerklärter horizontaler Überlauf; relevante normale UI-Texte mindestens
  4,5:1 mit tatsächlich ermitteltem Hintergrund; aktive Zustände nicht nur Farbe.
- Benutzer-/Charaktername „Speichern“ bleibt bei englischer UI „Speichern“;
  kanonische Charakterdaten und kalibrierte Messung bleiben unverändert.
- Verzögerte Bogenantwort zeigt Ladezustand statt Altbogen; korrekter Bogen und
  Fehlerweg danach sichtbar. Keine doppelte Navigationsgruppe; Bearbeitungsmodus
  weiter erreichbar. Creator-Rahmen auch bei schmaler Ansicht vollständig bedienbar.
- Gezielte Browser-/API-Regression, Katalogcheck und JS-/Inline-Syntax. Unabhängiger
  Claude-Diffreview vor Integration; genaue Befunde statt bloßer Freigabeformel.

## Besitz und Deploy-Handoff

Nur die Liste in `docs/proofs/claude-c01-2026-11-11/handoff.json` darf geändert
werden. Server, Auth, Regeln, Modellregistrierung, Kalender, Nachrichten, Assets,
G1 und Produktion sind außerhalb. Keine neuen Dependencies oder Migrationen.
Worker-Worktree startet am ausdrücklich übergebenen Launchcommit, der diesen
Vertrag enthält. Agent prüft/editiert; Koordination führt Tests/Generator aus,
integriert und liefert P4 samt additiver Maßstabstabelle nach dessen bestehendem
Backup-/Rollbackvertrag. Medium-Risiken der unvollständigen UI und des Ladeblitzes
sind durch diese expliziten Quell-/Ladeverträge und Abnahmetests behandelt; technische
Befunde im Deploy vor Live nacharbeiten. Anschließend Monitor und C02.

## Präzisierung nach Review und Quellenabgleich am 2026-11-12

Der unabhängige Review fordert die verbleibenden unmarkierten primären Hub-
Aktionen/namenshaltigen Hinweise sowie echte EN-/Benutzertext-Prüfung auf den
neu übersetzten Übersichten. Diese sind Teil der bestehenden C01-Grenze und
werden vor Live nachgearbeitet. Die fünf ergänzten Lade-/Fehler-/Bewegungs- und
Creatorprüfungen bestehen inzwischen; das ersetzt diese zusätzliche Abnahme nicht.

Zusätzlich zeigt der Quellabgleich: regelwerk-compendium.js und regelwerk-reader.js
verwenden noch keine UI-Katalogaufrufe für ihre selbst formulierten dynamischen
Bedienelemente. Da diese Hauptwege schon zur C01-EN-Abnahme gehören, werden genau
diese beiden Dateien, ihre bestehenden Templates regelwerk.html und
regelwerk-compendium.html sowie tests/test_c01_rulebook_browser.py zum Dateibesitz
hinzugefügt. Das ist eine ausdrückliche Korrektur der unvollständigen UI-Inventur,
keine neue Compendium-Featurearbeit (die bleibt C08).

Übersetzt werden ausschließlich eigene Controls, Tabellen-/Filterüberschriften,
Status-/Fehlertexte und bewusste UI-Formatlabels. Regelblöcke, Suchauszüge,
Dokument-/Buchtitel aus Quellen, Facetwerte, Entitätsnamen und Benutzertexte
bleiben unverändert. Reader-Renderer/DOM-Helfer dürfen nicht pauschal alle
eingehenden Strings übersetzen. Vorhandene explizite Katalogfunktionen benutzen,
neue DE/EN-Einträge ergänzen; gefrorene Inventare und generierte Dateien nicht
vom Worker ändern. Die Nachweise prüfen eine EN-Tabellenüberschrift/Filter und
gleichzeitig den unveränderten deutschen Entitäts-/Regeltext.

Ladezustand erst nach erfolgreichem synchronem Rendern bereit setzen; anfänglicher
Render-/Nicht-JSON-Fehler lässt keine halbe alte Fläche sichtbar. Überholte
Antworten dürfen einen inzwischen bereiten Stand nicht überdecken. Keine neuen
Controller oder Rechte. Zusatzkatalog darf denselben Quellschlüssel weiterhin
bewusst übersteuern, muss abweichende Übersetzungen dabei mindestens sichtbar
melden; Hashkollisionen anderer Quellen bleiben Fehler. Hauptnavigation genau
einmal und Draftstand nach Sprachreload ausdrücklich prüfen.
