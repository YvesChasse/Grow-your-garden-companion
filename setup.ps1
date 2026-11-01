param([string]$PythonExecutable = "")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($PythonExecutable) {
        & $PythonExecutable -m venv .venv
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv .venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv .venv
    } else {
        throw "Install Python 3.11 or newer from python.org, then run setup again."
    }
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment." }
}
& $venvPython -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 or newer is required." }
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed. Check your internet connection." }
Write-Host "Ready. Double-click Run Companion.cmd to start."
