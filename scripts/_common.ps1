<#
.SYNOPSIS
  Resolve the Python interpreter used for the ComplyGraph API.

.DESCRIPTION
  Resolution order:
    1. $env:VENV_PYTHON (explicit override, e.g. E:\complygraph-venv\Scripts\python.exe)
    2. apps\api\.venv\Scripts\python.exe (repo-local virtualenv)
    3. "python" on PATH

  Dot-source this file to get the Get-ComplyPython function:
    . "$PSScriptRoot\_common.ps1"
#>

function Get-ComplyPython {
    if ($env:VENV_PYTHON -and (Test-Path -LiteralPath $env:VENV_PYTHON)) {
        return $env:VENV_PYTHON
    }
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $localVenv = Join-Path $repoRoot "apps\api\.venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $localVenv) {
        return $localVenv
    }
    return "python"
}

function Get-ApiDir {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    return (Join-Path $repoRoot "apps\api")
}
