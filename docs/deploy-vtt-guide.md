# Deploy vtt.roll-drauf.de

## 1) Voraussetzungen

- DNS `A` Record: `vtt.roll-drauf.de` -> Server-IP
- Docker + Docker Compose installiert
- Benutzer hat Zugriff auf `/var/run/docker.sock`

## 2) Docker-Rechte fixen (falls no permission)

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Alternativ jeden Befehl mit `sudo` starten.

## 3) Deploy starten

```bash
cd /home/admin/projects/roll-drauf-vtt
./deploy_vtt_roll-drauf-de.sh
```

Das Script:
- erzeugt `.env.vtt.roll-drauf.de` (falls nicht vorhanden)
- startet `app + postgres + redis + nginx`
- wartet auf Healthcheck unter `http://127.0.0.1/health/live`

## 4) Prüfen

```bash
curl -I http://127.0.0.1
curl -I http://127.0.0.1/health/live
curl -I http://vtt.roll-drauf.de
```

## 5) HTTPS aktivieren (Let's Encrypt)

```bash
cd /home/admin/projects/roll-drauf-vtt
./enable_https_vtt_roll-drauf-de.sh deine@email.de
```

Danach testen:

```bash
curl -I https://vtt.roll-drauf.de
```

## 6) Zertifikat automatisch erneuern

Cronjob (als root oder deploy-user mit Docker-Rechten):

```bash
0 3 * * * /home/admin/projects/roll-drauf-vtt/renew_https_vtt_roll-drauf-de.sh >> /var/log/vtt-cert-renew.log 2>&1
```

## 7) Betrieb

```bash
docker compose -f docker-compose.vtt.roll-drauf.de.yml ps
docker compose -f docker-compose.vtt.roll-drauf.de.yml logs -f --tail=200
```

## 8) Update-Rollout

```bash
git pull
docker compose -f docker-compose.vtt.roll-drauf.de.yml --env-file .env.vtt.roll-drauf.de up -d --build
```

## Nachtrag 2026-08-25 — kanonisches Live-Deploy-Kommando

Der laufende Stack heißt `roll-drauf-vtt`; ohne `-p` leitet Compose den
Projektnamen aus dem Verzeichnis `infra/docker` ab und versucht, einen
zweiten Stack samt kollidierendem Netzwerk anzulegen. Deshalb immer:

```bash
cd /home/admin/projects/roll-drauf-vtt
docker compose -p roll-drauf-vtt \
  -f infra/docker/docker-compose.live.yml \
  --env-file .env.vtt.roll-drauf.de \
  up -d --build app
```

Baut das Image frisch aus dem Arbeitsbaum und tauscht nur den
App-Container (db/redis/mailserver laufen weiter). Danach im Browser hart
neu laden (Strg+Shift+R). Die Mailserver-Laufzeitdaten
(`infra/mailserver/docker-data/`, root-eigene DKIM-Schlüssel) sind per
`.dockerignore` vom Build-Kontext ausgeschlossen — nie entfernen, sonst
bricht der Kontext-Scan mit "no permission to read … mail.private" ab.
