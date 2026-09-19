<#
.SYNOPSIS
  Create a local virtualenv and install the API dependencies (no Docker required).

.DESCRIPTION
  Creates apps\api\.venv using the Python on PATH (must be 3.12.x; 3.14 is too new
  for the pinned pydantic-core wheel) and installs requirements.txt.

  To reuse an existing interpreter instead, set VENV_PYTHON and skip this script.

.EXAMPLE
  pwsh scripts\setup.ps1
#>

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\_common.ps1"

$apiDir = Get-ApiDir
$venvDir = Join-Path $apiDir ".venv"

if (-not (Test-Path -LiteralPath $venvDir)) {
    Write-Host "[setup] creating virtualenv at $venvDir"
    python -m venv $venvDir
}

$py = Join-Path $venvDir "Scripts\python.exe"

Write-Host "[setup] upgrading pip"
& $py -m pip install --upgrade pip

Write-Host "[setup] installing requirements"
& $py -m pip install -r (Join-Path $apiDir "requirements.txt")

Write-Host "[setup] done. Interpreter: $py"
