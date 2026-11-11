# Discover C02 – Charakterbedienung und Creator-Korrektur

Status: Faktenaufnahme abgeschlossen, Quelle C01-Launchbasis fb9642e32…;
vor Implementierung gegen das fertige C01 abgleichen. Profil standard, dauerhaft.
Input: R09–R13; keine Codeänderung in diesem Discover.

- Bogen setzt `editable` ausschließlich anhand `mode=edit` (Default view).
  Eigentümerprüfung des PUT-/Identitätsbackends bleibt davon unabhängig.
- `sheetIdentityGrid` und vollständiger Identitätsbereich werden von
  `SheetFeedback` in den Verwaltungstab verschoben. `renderIdentityCard` hat
  Upload/Ersetzen/Entfernen; der Picker liegt außerhalb des Bogen-Templates.
  POST/DELETE identity sind vorhanden und nur für den Charaktereigentümer erlaubt.
- GET `/api/characters/:id/sheet` prüft Leserecht und liefert Figur, Zauber,
  Ausrüstung, Inventar; keine explizite Rechteprojektion für diese Bedienelemente.
  PUT `/api/characters/:id` ist ebenfalls eigentümergebunden.
- `/api/srd-creator/characters/:id/duplicate` prüft Eigentümerschaft und verwendet
  `srd_manage.duplicate`: tiefe Kopie, neue ID, Beziehungen neu, keine Kampagne oder
  Avatarübernahme. Bereits Browserfälle für Duplizieren/Archiv/Entwurf vorhanden.
- Creator berechnet `stepOf(path)` und exportiert `SC.goStep`. Die Findings-Liste
  zeigt aktuell Meldung und Quellenzitat ohne Korrektureinstieg.
- Backend hat `feat-repeat` für nicht wiederholbare Talente. Die Auswahl der
  Verbesserungsstufen bietet trotzdem alle Talente dieser Kategorie an. Der
  gemeldete Ringer-Fall ist daher kein Beleg fehlender Serverprüfung.
- Existierende Tests: Identitätsproduktisierung, SRD-Manage API/Browser,
  SRD-Creator API/Browser und Fortschritt. Keine neuen Klassen-/Talenttexte nötig.

Risiken: medium – UI-Schreibschutz darf kein neues Recht schaffen; shared Reader
und Owner-as-Player getrennt prüfen. medium – Upload-Controls können zwar im DOM
existieren, aber durch Tab/Mode verborgen sein; echten Upload testen. low – Slotzahl
nicht beschlossen, keine neue Grenze ergänzen. low – Kopie alter Bildreferenzen
nicht ungeprüft als geteilter Storage übernehmen.

Nächster Schritt: C02-Apply auf C01-Rückgabe: serverseitige minimale UI-Rechteprojektion,
Eigentümer-Defaultbearbeitung mit lokalem Lock, sichtbarer Identitätsweg, bestehende
Kopie und Finding-Zielnavigation. Kein zweites Kopier-/Uploadbackend.
