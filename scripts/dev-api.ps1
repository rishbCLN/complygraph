<#
.SYNOPSIS
  Run the ComplyGraph API locally with hot reload (no Docker required).

.DESCRIPTION
  Starts uvicorn against the local SQLite database. Applies Alembic migrations
  first, then (in demo mode) seeds idempotently. Set NO_SEED=1 to skip seeding.

.EXAMPLE
  pwsh scripts\dev-api.ps1
#>

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

$py = Get-ComplyPython
$apiDir = Get-ApiDir

Push-Location $apiDir
try {
    Write-Host "[dev-api] applying migrations"
    & $py -m alembic upgrade head

    if ($env:NO_SEED -ne "1") {
        Write-Host "[dev-api] seeding demo data (idempotent)"
        & $py -m app.seed
    }

    Write-Host "[dev-api] starting uvicorn on http://localhost:8000"
    & $py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}
finally {
    Pop-Location
}
