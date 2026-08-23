#!/usr/bin/env bash
# Nightly PostgreSQL backup for Roll Drauf VTT.
#
# Dumps the live database (running in the roll-drauf-vtt-db-1 container) in
# pg_dump custom format, then rotates: 14 daily dumps, monthly dumps for ~6
# months. Run by roll-drauf-vtt-backup.timer; safe to run manually at any time.
set -euo pipefail

DB_CONTAINER="roll-drauf-vtt-db-1"
DB_NAME="vtt"
DB_USER="vtt"
BACKUP_ROOT="/home/admin/backups/roll-drauf-vtt"
DAILY_DIR="$BACKUP_ROOT/daily"
MONTHLY_DIR="$BACKUP_ROOT/monthly"
DAILY_KEEP_DAYS=14
MONTHLY_KEEP_DAYS=190

if ! docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
    echo "backup_database: container $DB_CONTAINER not found" >&2
    exit 1
fi

mkdir -p "$DAILY_DIR" "$MONTHLY_DIR"
chmod 700 "$BACKUP_ROOT" "$DAILY_DIR" "$MONTHLY_DIR"

stamp="$(date +%Y%m%d_%H%M%S)"
dump="$DAILY_DIR/vtt_${stamp}.dump"
tmp="${dump}.partial"

docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" --format=custom "$DB_NAME" > "$tmp"
chmod 600 "$tmp"
mv "$tmp" "$dump"
echo "backup_database: wrote $dump ($(du -h "$dump" | cut -f1))"

# Keep one dump per month: promote the first dump of the current month.
month_tag="$(date +%Y%m)"
if ! ls "$MONTHLY_DIR"/vtt_"${month_tag}"*.dump >/dev/null 2>&1; then
    cp -p "$dump" "$MONTHLY_DIR/"
    echo "backup_database: promoted $(basename "$dump") to monthly"
fi

# Rotation. -mtime uses modification time, which for dumps equals creation time.
find "$DAILY_DIR" -name 'vtt_*.dump' -mtime +"$DAILY_KEEP_DAYS" -print -delete |
    sed 's/^/backup_database: rotated daily /'
find "$MONTHLY_DIR" -name 'vtt_*.dump' -mtime +"$MONTHLY_KEEP_DAYS" -print -delete |
    sed 's/^/backup_database: rotated monthly /'
find "$BACKUP_ROOT" -name '*.partial' -mtime +1 -print -delete |
    sed 's/^/backup_database: removed stale partial /'

echo "backup_database: done ($(ls "$DAILY_DIR" | wc -l) daily, $(ls "$MONTHLY_DIR" | wc -l) monthly on disk)"
