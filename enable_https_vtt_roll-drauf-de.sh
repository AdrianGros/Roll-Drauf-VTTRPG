#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

DOMAIN="vtt.roll-drauf.de"
EMAIL="${1:-${LETSENCRYPT_EMAIL:-}}"
COMPOSE_FILE="docker-compose.vtt.roll-drauf.de.yml"
ENV_FILE=".env.vtt.roll-drauf.de"

if [ -z "$EMAIL" ]; then
  echo "[ERROR] Bitte E-Mail angeben: ./enable_https_vtt_roll-drauf-de.sh <email>"
  exit 1
fi

if ! docker ps >/dev/null 2>&1; then
  echo "[ERROR] Kein Zugriff auf Docker Daemon."
  echo "[HINWEIS] sudo usermod -aG docker \$USER && newgrp docker"
  exit 1
fi

mkdir -p ops/certbot/www ops/certbot/conf

echo "[INFO] Stelle sicher, dass HTTP-Stack laeuft..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d app db redis nginx

echo "[INFO] Fordere Let's Encrypt Zertifikat fuer $DOMAIN an..."
docker run --rm \
  -v "$PWD/ops/certbot/conf:/etc/letsencrypt" \
  -v "$PWD/ops/certbot/www:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  --non-interactive

echo "[INFO] Schalte Nginx auf HTTPS-Konfiguration um..."
cp ops/nginx/vtt.roll-drauf.de.https.conf ops/nginx/vtt.roll-drauf.de.conf
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart nginx

echo "[INFO] Pruefe Nginx-Konfiguration..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T nginx nginx -t
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T nginx nginx -s reload || true

echo "[INFO] HTTPS-Test..."
curl -I --max-time 20 "https://$DOMAIN" || true

echo
echo "[OK] HTTPS wurde konfiguriert."
echo "[HINWEIS] Fuer automatische Verlaengerung: ./renew_https_vtt_roll-drauf-de.sh"
