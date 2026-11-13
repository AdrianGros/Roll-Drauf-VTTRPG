# B02 / S14 – Optionales Discord-Kontobild

Status: Apply abgeschlossen, vor Implementierung. Die vorhandene OAuth-Anmeldung liest bereits
das Discord-Profil mit `identify`; das Identitätsmodell speichert bislang keinen Avatar-Hash.
Quelle: [Discord User Object](https://docs.discord.com/developers/resources/user#user-object).

## Vertrag

`DiscordIdentityLink.avatar_hash` ist eine zusätzliche nullable Zeichenkette (64 Zeichen).
Nur der bestehende erfolgreich verifizierte OAuth-Callback übernimmt `avatar` aus dem Profil;
er akzeptiert ausschließlich einen Discord-Hash (32 Hexzeichen, optional `a_`). Kein beliebiger
Bild-URL-Import, kein neuer Token oder OAuth-Scope, kein Netzwerkaufruf beim Öffnen einer VTT-Seite.
Eine erneute Discord-Anmeldung aktualisiert/entfernt den Snapshot. Bestehende Konten ohne Snapshot
bleiben unverändert; keine ungefragte erneute Anmeldung erzwingen.

Das bereits geschützte `/api/dashboard/navigation` gibt für das eigene aktive verknüpfte Konto
optional `user.avatar_url` zurück. Die URL wird aus geprüftem Snowflake/Hash ausschließlich unter
`https://cdn.discordapp.com/avatars/…` konstruiert (statisches PNG in kleiner Auflösung).
Andere Konten/Links bleiben unzugänglich. Die gemeinsame Kontonotiz stellt das Bild neben Namen
und Sessionanzahl dar, mit leerem Alttext als Dekoration. Fehlende oder defekte Bilder fallen
auf den weiterhin sichtbaren Namen zurück.

## Rollout und Kriterien

Gezielte Model-/Callback-/API-Tests prüfen gültigen Hash, fehlenden/ungültigen Hash und widerrufenen
Link. Browser prüft Bild und Fehler-Fallback ohne echte Discord-Anmeldung oder Änderungen an
realen Nutzerkonten.

Vor neuer App: bestehender gesicherter DB-Dump, dann idempotentes `ADD COLUMN avatar_hash VARCHAR(64)`
mit kurzem Lock-Timeout; vorhandene Spalte anhand Typ und Nullbarkeit prüfen. Kein Tabellenersatz,
kein Backfill und keine geänderten Kontingente. Das alte Image ignoriert die zusätzliche nullable
Spalte und bleibt als Rollback verwendbar. Erfolgreiche Schemaänderung separat belegen; bei
Timeout/abweichendem Schema abbrechen und App nicht aktivieren.

Medium-Risiko bestehende SQLAlchemy-Abfragen vor Schemaänderung wird durch diese Reihenfolge
aufgelöst. Low: Ein vorhandener Discord-Nutzer sieht sein persönliches Bild erst nach seiner
nächsten regulären Discord-Anmeldung; bis dahin bleibt die Namenanzeige vollständig nutzbar.
Handoff: Implementierung im Umfang dieses Vertrags, gezielte Checks, Schema-Beleg und gemeinsame
B02-Lieferung über die etablierten normalen UI-Einstiege. Retention: dauerhaft.
