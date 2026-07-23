$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)
Write-Host "Waiting for OpenRouteService..." -ForegroundColor Cyan
for ($i = 1; $i -le 120; $i++) {
    try {
        $health = Invoke-RestMethod "http://localhost:8080/ors/v2/health" -TimeoutSec 4
        if ($health.status -eq "ready") {
            Write-Host "OpenRouteService is ready." -ForegroundColor Green
            exit 0
        }
    } catch {
        # Service may return HTTP 503 while the graph is building.
    }
    Start-Sleep -Seconds 5
}
Write-Host "ORS is still not ready. Check: docker compose logs --tail 100" -ForegroundColor Red
exit 1
