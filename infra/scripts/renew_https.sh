#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE_FILE="docker-compose.vtt.roll-drauf.de.yml"
ENV_FILE=".env.vtt.roll-drauf.de"

if ! docker ps >/dev/null 2>&1; then
  echo "[ERROR] Kein Zugriff auf Docker Daemon."
  exit 1
fi

mkdir -p ops/certbot/www ops/certbot/conf

docker run --rm \
  -v "$PWD/ops/certbot/conf:/etc/letsencrypt" \
  -v "$PWD/ops/certbot/www:/var/www/certbot" \
  certbot/certbot renew \
  --webroot \
  -w /var/www/certbot \
  --quiet

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T nginx nginx -s reload || \
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart nginx

echo "[OK] Zertifikats-Refresh abgeschlossen."
