param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [Parameter(Mandatory = $false)]
    [string]$OutputPath = ".\backups"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $OutputPath "vtt_backup_$timestamp.sql"
$gzipFile = "$backupFile.gz"

Write-Host "Creating PostgreSQL dump to $backupFile"
pg_dump --no-owner --no-acl --format=plain --dbname="$DatabaseUrl" --file="$backupFile"

Write-Host "Compressing backup"
gzip -f "$backupFile"

Write-Host "Backup complete: $gzipFile"
