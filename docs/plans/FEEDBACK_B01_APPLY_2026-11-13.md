# B01 – Anrufungsprüfung und Rückweg zu Karten

Status: Apply abgeschlossen; Deploy freigegeben durch den Umsetzungsauftrag des Owners.
Input: N01/S10 aus den abgeschlossenen Discover-Berichten, reine Probe unter
`docs/proofs/feedback-round-0946-2026-11-13/prerequisites.json` und tatsächlicher Back-Menü-Handler.

## Ziel und Schnittstellen

Der Generator ergänzt jede Klassenoption um strukturierte `requirements` und eine belegte
`prerequisiteSource`. Enthalten sind Mindestklassenstufe, benötigte andere Option und ggf.
ein bekannter schadensverursachender Hexenmeister-Zaubertrick mit/ohne Angriffswurf.
Alle vorhandenen Voraussetzungstexte müssen vollständig parsebar sein; unbekannte Teile führen
zu einem Generatorfehler. Bestehende IDs, Auswahlzustände und Regeln bleiben erhalten.

Für die sieben vorhandenen Hexenmeister-Zaubertricks wird die Eignung ausdrücklich anhand
der vorhandenen Originalregelblöcke klassifiziert. Utility-Zauber und Zauber einer fremden Klasse
erfüllen die Voraussetzung nicht. Abhängigkeiten werden transitiv geprüft, nicht nur über die
Anwesenheit einer ungültigen Vorgängeroption. Mehrklassenstufen zählen pro Klasse.

Der reine Server-Evaluator liefert zusätzlich `classOptionEligibility[classKey][optionId]`
mit `eligible` und verständlichen `reasons`. Sowohl Creator als auch Aufstiegs-Preview nutzen
diese Entscheidung. Bei noch ungeprüfter lokaler Änderung werden neue Optionen vorübergehend
gesperrt; bereits gewählte bleiben sichtbar. Abschicken/Finalisieren wird unabhängig vom Client
erneut serverseitig geprüft. Keine stille Löschung oder Migration bestehender Figuren.

Die bestehende Aufstiegs-API erlaubt bereits den Austausch einer Optionsliste. Ungültige alte
Anrufungen werden im Assistenten zur Korrektur entsperrt; gültige alte Einträge behalten die
bisherige UI-Sperre. Kein neuer allgemeiner Respec-Modus.

`_normalizeBookReturnTarget` akzeptiert zusätzlich den vorhandenen lokalen Pfad `/mapmaker`.
Fremde Origins werden ausdrücklich abgewiesen. Der bestehende sofortige Rückweg wird erhalten;
es entstehen keine DM-Daten oder privilegierten Kontexte durch Navigation.

## Kriterien / geplante Belege

- Ohne erforderlichen Pakt sind Smite, Lifedrinker, Thirsting Blade, Chain-/Book-Abhängigkeiten
  und transitive Verbesserungen nicht gültig. Gültige Kombinationen bleiben möglich.
- Schadenszaubertricks erfüllen die jeweilige Voraussetzung; Utility-/fremde Zaubertricks nicht.
- Mindeststufen verwenden Hexenmeisterstufen. Direkte Finalisierung und Level-up können die Prüfung nicht umgehen.
- Beide Auswahloberflächen zeigen den Grund, aktualisieren ihn nach Änderungen und lassen ungültige Auswahl korrigieren.
- DM und Player erreichen Karten über das vorhandene Zurück-Menü; externe Rücksprungziele bleiben ungültig.
- Bestehende gezielte Regel-/Aufstiegs- und Browserchecks bleiben grün.

## Risiken, Abwägung und Deploy-Handoff

Medium-Risiko Regeldivergenz wird durch eine einzige serverseitige Entscheidung für beide UIs
und positive/negative API-Tests aufgelöst. Medium-Risiko Bestandsfiguren wird durch unveränderte
Lesbarkeit und ausdrückliche Korrektur statt stiller Zustandsänderung begrenzt.
Low: Kurze Wartezeit bis zur serverseitigen Neuberechnung nach einer Auswahl; keine doppelte JS-Regelimplementierung.
Wiederholbarkeit/Bindung einer Anrufung an einen konkreten Zaubertrick ist getrennte, ältere
Regelmechanik und wird in diesem Voraussetzungsslice nicht erweitert.

Keine Schemaänderung, keine neue Abhängigkeit. Gezielte Tests → Commit/Push → tatsächliches
Image/Compose erneut prüfen → vorhandener Overlay-Release mit erhaltenem vorherigem Image →
Live-Login mit synthetischen Rollen/Creator-Figur → UI-/API-Belege und Rollback-Verweis erfassen.
Retention: dauerhaft. Danach B02; der Gesamtauftrag bleibt bis B11 offen.
