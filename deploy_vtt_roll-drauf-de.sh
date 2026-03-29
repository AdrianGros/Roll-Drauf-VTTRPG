#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

ENV_FILE=".env.vtt.roll-drauf.de"
COMPOSE_FILE="docker-compose.vtt.roll-drauf.de.yml"
DOMAIN="vtt.roll-drauf.de"
LEGACY_ENV_FILE=".env.vtt.roll-drauf-de"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker ist nicht installiert."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[ERROR] docker compose ist nicht verfuegbar."
  exit 1
fi

if ! docker ps >/dev/null 2>&1; then
  echo "[ERROR] Kein Zugriff auf Docker Daemon (/var/run/docker.sock)."
  echo "[HINWEIS] Fuehre aus: sudo usermod -aG docker \$USER && newgrp docker"
  echo "[HINWEIS] Oder starte dieses Script mit sudo."
  exit 1
fi

if [ -f "$LEGACY_ENV_FILE" ] && [ ! -f "$ENV_FILE" ]; then
  mv "$LEGACY_ENV_FILE" "$ENV_FILE"
  sed -i 's/vtt\.roll-drauf-de/vtt.roll-drauf.de/g' "$ENV_FILE" || true
  echo "[INFO] Legacy Env-Datei auf neuen Domain-Namen migriert: $ENV_FILE"
fi

if [ ! -f "$ENV_FILE" ]; then
  SECRET_KEY="$(openssl rand -hex 32)"
  JWT_SECRET_KEY="$(openssl rand -hex 32)"

  cat > "$ENV_FILE" <<ENV
FLASK_ENV=production
FLASK_DEBUG=0

SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET_KEY

DATABASE_URL=postgresql://vtt:vtt@db:5432/vtt
REDIS_URL=redis://redis:6379/0
SOCKETIO_MESSAGE_QUEUE=redis://redis:6379/0
RATELIMIT_STORAGE_URL=redis://redis:6379/1
RATELIMIT_STORAGE_URI=redis://redis:6379/1

CORS_ORIGINS=https://$DOMAIN,http://$DOMAIN
AUTO_CREATE_SCHEMA=true
LOG_JSON=true
METRICS_ENABLED=true
VOICE_ENABLED=false
USE_SESSION_SOCKET_V2=false
ENV

  echo "[INFO] $ENV_FILE wurde neu angelegt."
fi

mkdir -p ops/certbot/www ops/certbot/conf

echo "[INFO] Starte Deploy fuer $DOMAIN ..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

echo "[INFO] Warte auf App-Healthcheck ..."
for i in {1..60}; do
  if curl -fsS "http://127.0.0.1/health/live" >/dev/null 2>&1; then
    echo "[OK] Healthcheck erfolgreich."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "[ERROR] Healthcheck fehlgeschlagen."
    docker compose -f "$COMPOSE_FILE" logs --tail=120
    exit 1
  fi
  sleep 2
done

echo "[INFO] Container Status:"
docker compose -f "$COMPOSE_FILE" ps

echo
echo "[HINWEIS] DNS fuer $DOMAIN zeigt aktuell nicht auf diese Maschine (wenn extern nicht erreichbar)."
echo "[HINWEIS] Test lokal:  curl -I http://127.0.0.1"
echo "[HINWEIS] HTTPS aktivieren: ./enable_https_vtt_roll-drauf-de.sh <deine-email>"
