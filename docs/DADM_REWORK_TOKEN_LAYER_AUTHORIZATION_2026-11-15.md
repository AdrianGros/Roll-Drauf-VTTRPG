# Discover → Apply: Token-Layer-Autorisierung nach Live-Negativtest

Status: begrenzte Rework-Freigabe im bestehenden Owner-Auftrag zur serverseitigen
Player/DM-Trennung und zum DM-Layer; Aufbewahrung dauerhaft.

## Discover
Live-Negativtest auf 3253ad0b0: Owner tritt über Hub ausdrücklich als Player ein.
Surface und Bootstrap sind korrekt eingeschränkt. Ein PUT auf seinen eigenen
DM-verdeckten Token mit `patch.visibility=public` liefert dennoch 200.
Ursachen: `_can_manage_token` akzeptiert Tokenbesitz ohne Lesesichtbarkeit;
REST- und Socket-Patchparser erlauben visibility auch Nicht-DMs.
Auch Create kann Nicht-DM-Sichtbarkeit annehmen. Update/Delete können vor Prüfung
einer Leseberechtigung Konfliktantworten mit vollständigem Token serialisieren.
Schwere: hoch, Autorisierung/Geheimnisschutz; kein Nachweis fremder realer Daten,
Reproduktion ausschließlich mit eigenen synthetischen Konten und Tokens.
Der Layer-Slice ist vor dieser Reparatur **nicht technisch abgeschlossen**.

## Apply und Annahmekriterien
Keine neue Architektur/Abhängigkeit/Schemaänderung. Vorhandene serverautorisierte
Kontexte und `is_token_visible_to` bleiben die Autorität.
- REST und Socket: Nicht-DM darf ausschließlich lesbare eigene Tokens ändern/löschen;
  Prüfung vor Versionskonflikt/Serialization. Besitz eines DM-seitigen Tokens genügt nicht.
- Sichtbarkeits-Patches sind ausschließlich DM-Operationen; Nicht-DM erhält forbidden,
  auch wenn er das Zieltoken besitzt. Nicht-DM erstellt weiterhin eigene öffentliche
  Player-Tokens; private/DM-Tokens anlegen ist verboten.
- Bestehende öffentliche Tokenbewegung und berechtigter DM-Reveal bleiben möglich.
- Negativmatrix: Player und Owner-as-Player, HTTP und Socket, Create/Update/Delete,
  korrekte und falsche Versionen. Keine Mutation, keine geheimen Antwortdaten und
  kein privilegierter Broadcast bei verweigertem Zugriff.
- Positivmatrix: eigener öffentlicher Player-Token bewegbar, DM darf verdecken/revealen.
- Anschließend Commit/Push, neues App-Image auf tatsächlicher Basis 003baaa4…,
  Vollhashprüfung, Backup, App-only-Deployment, derselbe Live-Negativtest und Cleanup.

Die Reparatur konkretisiert die bereits verbindlichen Anforderungen aus
AGENTS.md und PLAYTABLE_ROLE_SEPARATION_2026-11-01.md. Es gibt keine offene
Produktentscheidung oder alternative Berechtigungsarchitektur, die den Owner
vor dieser notwendigen Korrektur erneut um eine allgemeine Freigabe bitten würde.
