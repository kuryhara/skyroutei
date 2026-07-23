$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "[1/4] Creating Python virtual environment..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

Write-Host "[2/4] Installing Python packages..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "[3/4] Checking Docker..." -ForegroundColor Cyan
docker --version | Out-Host
docker compose version | Out-Host

$pbf = ".\ors-docker\files\jiangsu-latest.osm.pbf"
if (-not (Test-Path $pbf)) {
    Write-Host "[4/4] Downloading Jiangsu OpenStreetMap data..." -ForegroundColor Cyan
    Invoke-WebRequest `
      -Uri "https://download.geofabrik.de/asia/china/jiangsu-latest.osm.pbf" `
      -OutFile $pbf
} else {
    Write-Host "[4/4] Jiangsu map already exists." -ForegroundColor Green
}

Write-Host "Setup finished. Run scripts\start_all.ps1" -ForegroundColor Green
