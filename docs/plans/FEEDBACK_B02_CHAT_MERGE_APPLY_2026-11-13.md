# B02 – Ergänzung zur Chat-Erhaltung

Status: begrenzter Apply-Nachtrag abgeschlossen, vor Korrektur.
Discover-Beleg: Der echte Zwei-Client-Würfeltest zeigt im Chat eine gespeicherte Klartextzeile,
obwohl der Client den vollständigen Würfel-Broadcast empfangen hat. `_appendChatMessage`
verwirft bisher jeden Broadcast für eine bereits in der History vorhandene Nachrichten-ID.
Die Reihenfolge History/Broadcast kann damit die angezeigte Detaildarstellung bestimmen.

Die bestehende ID-Deduplizierung bleibt erhalten. Ein vollständig vom Server ausgelieferter
Würfel-Broadcast darf dieselbe bereits geladene Klartextzeile um seine Zusammenfassung und
Einzelwürfel ergänzen. Keine zweite Zeile, keine neue History-Abfrage oder neue DB-Felder.
Verdeckte Platzhalter dürfen niemals durch Beibehalten alter Details wieder sichtbar werden;
ein verdecktes Ereignis entfernt gegebenenfalls zuvor vorhandene Details derselben Zeile.
Alle Daten stammen weiter aus dem bereits autorisierten HTTP-/Socket-Kontext.

Medium-Risiko unterschiedlicher Ankunftsreihenfolge wird durch den Zwei-Client-Test und eine
gezielt verzögerte History/Broadcast-Reihenfolge geprüft. Öffentliche Details, Deduplizierung,
persistierter Klartext nach Reload und verdeckte Platzhalter müssen erhalten bleiben.
Kein Architekturausbau, keine Rechte-/Datenprojektion auf dem Server ändern.
Handoff: kleine Merge-Korrektur, gezielte Browserprüfung, in B02-Release und Live-Belege aufnehmen.
Retention: dauerhaft.
