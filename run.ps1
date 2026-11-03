$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$pythonWindow = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $pythonWindow)) {
    & (Join-Path $PSScriptRoot "setup.ps1")
}
Start-Process -FilePath $pythonWindow -ArgumentList ('"' + (Join-Path $PSScriptRoot "main.py") + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
