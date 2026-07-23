Set-Location (Split-Path -Parent $PSScriptRoot)
docker compose down
Write-Host "OpenRouteService stopped." -ForegroundColor Green
