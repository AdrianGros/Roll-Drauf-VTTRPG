param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $BackupFile)) {
    throw "Backup file not found: $BackupFile"
}

$tempSqlFile = $BackupFile
if ($BackupFile.ToLower().EndsWith(".gz")) {
    $tempSqlFile = $BackupFile.Substring(0, $BackupFile.Length - 3)
    Write-Host "Decompressing $BackupFile"
    gzip -dkf "$BackupFile"
}

Write-Host "Restoring database from $tempSqlFile"
psql "$DatabaseUrl" -f "$tempSqlFile"

Write-Host "Restore complete."
