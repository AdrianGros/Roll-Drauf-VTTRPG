param(
    [Parameter(Mandatory = $false)]
    [string]$FlaskEnv = "production"
)

$ErrorActionPreference = "Stop"
$env:FLASK_ENV = $FlaskEnv

Write-Host "Running database migrations for FLASK_ENV=$FlaskEnv"
flask db upgrade
Write-Host "Migration complete."
