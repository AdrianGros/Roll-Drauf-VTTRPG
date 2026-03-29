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
