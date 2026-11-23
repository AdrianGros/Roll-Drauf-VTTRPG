# Deploy-Nacharbeit: Beschriftungen in Unterfenstern

Status: begrenzte Nacharbeit aus der visuellen Live-Abnahme, innerhalb des freigegebenen Werkzeuggruppen-Konzepts. Der erste Build `e29cd96f9` bestand die drei funktionalen Live-Reisen; die anschließende Bildkontrolle zeigte jedoch einen verdeckten Text im Figurenfenster. Der Monitor-Abschluss wird erst nach der Korrektur erteilt.

Ursache: die vorhandene Grundregel `.tool-btn .tool-label { display:none }` war für die frühere Werkzeugleiste gedacht. Nach dem Verschieben originaler Buttons in die Unterfenster fehlte dort das ausdrückliche Wiedereinblenden. Die neue gemeinsame Zeilenregel setzt deshalb `display:block` für die Beschriftung. Keine Änderung an Aktionen, Daten, Rollen, Fensterpositionen oder Hauptleistenabmessungen.

Abnahme: die vier Browserfälle prüfen nun sichtbare Beschriftungen für Journal, Einstellungen, Befehlsübersicht und DM-Token-Sichtbarkeit; die Live-Reise prüft diese Texte ebenfalls ausdrücklich. Die Bildkontrolle wird nach Veröffentlichung wiederholt.

Lieferung: ausschließlich die eine geänderte CSS-Datei als Overlay auf dem tatsächlich laufenden Image `sha256:916fb837b9b0d0de1374bef51fbbcdb6644403e198b6a481882af581919a4913`, Quelle `e29cd96f90c59c5389bf3aab13beb40c9d650ec3`. Vor Aktivierung erneute lesbare Datenbanksicherung, keine Migration; andere Dienste und Reminder-Timer bleiben erhalten. Die Release-Identitäten und die Rückwege beider App-only-Schritte werden im abschließenden Monitor dokumentiert.

Risiko niedrig: spezifischer CSS-Selektor für bereits registrierte Befehlszeilen. Artefakte: Nacharbeitsbericht, Browser-/Live-Belege und Lieferidentität permanent im Projekt; Sicherung/Rollback zugriffsbeschränkt; temporäre QA-Zugänge werden entfernt. Nächster Schritt: gezielte Prüfung, Commit/Push, Nachfolgeimage und erneute Live-Abnahme.
