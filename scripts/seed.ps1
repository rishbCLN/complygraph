<#
.SYNOPSIS
  Seed the local SQLite database with the DPDP control library and the AsterLane demo org.

.DESCRIPTION
  Idempotent. Runs against the default local SQLite database (sqlite:///./complygraph.db)
  unless DATABASE_URL is set. Safe to re-run.

.EXAMPLE
  pwsh scripts\seed.ps1
#>

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

$py = Get-ComplyPython
$apiDir = Get-ApiDir

Write-Host "[seed] using interpreter: $py"
Push-Location $apiDir
try {
    & $py -m app.seed
    if (-not $?) { throw "seed failed" }
}
finally {
    Pop-Location
}
