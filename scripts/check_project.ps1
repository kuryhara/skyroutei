$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
& $python -m py_compile app.py
Write-Host "Python syntax OK." -ForegroundColor Green
try {
    $health = Invoke-RestMethod "http://localhost:8080/ors/v2/health" -TimeoutSec 5
    Write-Host "ORS status: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "ORS unavailable or still building." -ForegroundColor Yellow
}
