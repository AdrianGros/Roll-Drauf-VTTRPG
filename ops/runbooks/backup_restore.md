# Backup and Restore Runbook

## Scope

This runbook defines the baseline procedure for PostgreSQL backup and restore in production.

## Preconditions

- `DATABASE_URL` points to production PostgreSQL.
- `PGPASSWORD` is available in the shell/session.
- Backup target storage is encrypted and access-controlled.

## Backup Procedure

1. Export `DATABASE_URL` and target path.
2. Run:
   ```powershell
   ./ops/scripts/backup_db.ps1 -DatabaseUrl $env:DATABASE_URL -OutputPath "./backups/prod"
   ```
3. Upload backup artifact to object storage.
4. Record checksum and timestamp in release/ops log.

## Restore Procedure

1. Identify backup file and checksum.
2. Restore into staging first:
   ```powershell
   ./ops/scripts/restore_db.ps1 -DatabaseUrl $env:STAGING_DATABASE_URL -BackupFile "./backups/prod/<file>.sql.gz"
   ```
3. Run smoke checks against staging.
4. If validated, execute restore/failover procedure for production.
5. Record RTO/RPO evidence in monitoring artifact.

## Validation Checklist

- Backup file exists and is non-empty.
- Restore command returns success.
- App readiness endpoint returns `200`.
- Core API smoke checks pass (`/api/auth/check`, `/health/ready`).
