$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
& ".\scripts\start_ors.ps1"
& ".\scripts\wait_for_ors.ps1"
& ".\scripts\start_app.ps1"
