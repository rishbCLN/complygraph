<#
.SYNOPSIS
  Run the ComplyGraph API test suite (unit + security + E2E).

.DESCRIPTION
  Runs pytest against a throwaway SQLite database created by the test fixtures,
  so the local complygraph.db is never touched. Any extra arguments are passed
  straight through to pytest.

.EXAMPLE
  pwsh scripts\test.ps1
  pwsh scripts\test.ps1 tests/unit -k classifier -v
#>

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

$py = Get-ComplyPython
$apiDir = Get-ApiDir

Push-Location $apiDir
try {
    & $py -m pytest @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
