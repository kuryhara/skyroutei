$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "Starting local OpenRouteService..." -ForegroundColor Cyan
docker compose up -d
Write-Host "ORS is building/loading the Jiangsu graph. First startup can take several minutes." -ForegroundColor Yellow
