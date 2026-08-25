# Mailserver-Deployment — 24.08.2026

## Ergebnis

Auf dem VPS war kein Mailserver vorhanden. Roll-Drauf verwendet jetzt
`ghcr.io/docker-mailserver/docker-mailserver:15.1.0` als privaten SMTP-Only-
Dienst im bestehenden Docker-Netzwerk.

- Mailserver-FQDN: `mail.vtt.roll-drauf.de`
- Interner TLS-Name: `vtt.roll-drauf.de` (bestehendes Zertifikat)
- App-Transport: `vtt.roll-drauf.de:587` über den internen Docker-DNS-Alias
- Verschlüsselung: STARTTLS
- Authentifizierung: SMTP-Login für `no-reply@vtt.roll-drauf.de`
- Mailbox-Dienst: nur intern; IMAP ist für den Dovecot-SASL-Provider aktiv, IMAP/POP3 sind nicht veröffentlicht
- Host-Mailports: nicht veröffentlicht
- Relay-Schutz: `PERMIT_DOCKER=none`
- ClamAV und Fail2ban: deaktiviert, weil keine öffentlichen Mailports exponiert sind

Die App-Integration liegt in
[`infra/docker/docker-compose.live.yml`](../infra/docker/docker-compose.live.yml).
Persistente Maildaten und DKIM-Schlüssel liegen unter
`infra/mailserver/docker-data/`; dieses Verzeichnis ist lokal von Git
ausgeschlossen.

## Noch notwendige DNS- und Provider-Schritte

Die autoritativen Nameserver sind `ns.checkdomain.de` und `ns2.checkdomain.de`.
Aktuell zeigt `vtt.roll-drauf.de` nur auf den VPS; MX, SPF, DKIM und DMARC fehlen.
Vor öffentlichem Empfang oder verlässlicher Zustellung müssen mindestens diese
Records gesetzt werden:

```text
mail.vtt.roll-drauf.de.     A    82.25.101.159
vtt.roll-drauf.de.          MX   10 mail.vtt.roll-drauf.de.
vtt.roll-drauf.de.          TXT  "v=spf1 ip4:82.25.101.159 -all"
_dmarc.vtt.roll-drauf.de.   TXT  "v=DMARC1; p=none; rua=mailto:postmaster@vtt.roll-drauf.de"
```

DKIM:

```text
mail._domainkey.vtt.roll-drauf.de. TXT ("v=DKIM1; h=sha256; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA49c5hxPpxOPicDokiUinPXfFikeyyNT5fNHvfz1Gn1kLjvoVteaYnUyMD15Ar6bX5Up94gdB0/PBQUoRWWAAdPWp58+rk3HfC7sd4OH8dBiHpKb5InDcgv6XPszRb876GlaAziSswY5hVi1TqX6naiLLVtmD6uyjFj8oiI6P4t5Sb7OfWuHweNj2+LDS1WhVzzErO7FfMt9wAI" "G0+GH7uV/oeDKzcVyWvmVfG8k/NbXTP9ezEopEkBWiYne69r2XlPniX0iIHHM+B7RHl4z/xVyou6OawzjmoP6sFTVq2bH44hi8JQMEt8K6W4SNK7FZNemFZe73KEy0LX6D6IOTQwIDAQAB")
```

Der PTR der VPS-Adresse `82.25.101.159` lautet aktuell
`srv792235.hstgr.cloud`. Für direkte Mailzustellung muss der PTR beim VPS-
Provider auf den verwendeten Mail-FQDN zeigen und dieser FQDN wieder auf die
VPS-Adresse auflösen. Wenn Port 25 ausgehend beim Provider gesperrt ist, muss
stattdessen ein authentifizierter Relay-Dienst auf Port 465 oder 587 hinterlegt
werden.

## Primärquellen

- [Docker Mailserver — Usage und DNS](https://docker-mailserver.github.io/docker-mailserver/latest/usage/)
- [Docker Mailserver — Environment Variables](https://docker-mailserver.github.io/docker-mailserver/latest/config/environment/)
- [Docker Mailserver — TLS](https://docker-mailserver.github.io/docker-mailserver/latest/config/security/ssl/)
- [Docker Mailserver — DKIM, SPF und DMARC](https://docker-mailserver.github.io/docker-mailserver/latest/config/best-practices/dkim_dmarc_spf/)
- [Docker Mailserver — Ports](https://docker-mailserver.github.io/docker-mailserver/latest/config/security/understanding-the-ports/)
- [RFC 7208 — SPF](https://www.rfc-editor.org/rfc/rfc7208)
- [RFC 6376 — DKIM](https://www.rfc-editor.org/rfc/rfc6376)
- [RFC 8314 — TLS für Mail](https://www.rfc-editor.org/rfc/rfc8314)
- [RFC 5321 — SMTP und MX](https://www.rfc-editor.org/rfc/rfc5321)
