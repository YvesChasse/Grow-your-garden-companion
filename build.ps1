param([string]$PythonExecutable = "", [switch]$SkipInstall)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not $PythonExecutable) {
    & (Join-Path $PSScriptRoot "setup.ps1")
    $PythonExecutable = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}
if (-not $SkipInstall) {
    & $PythonExecutable -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "Build dependencies could not be installed." }
}
New-Item -ItemType Directory -Force -Path work, dist | Out-Null
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot "work\pyinstaller-cache"
& $PythonExecutable -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Tests failed. Build stopped." }
& $PythonExecutable tools/make_icon.py
if ($LASTEXITCODE -ne 0) { throw "Could not generate the application icon." }
$iconPath = Join-Path $PSScriptRoot "assets\garden.ico"
$entryPath = Join-Path $PSScriptRoot "main.py"
# Avoid collecting unrelated DLLs from tools on the caller's PATH (for example,
# an old ucrtbase.dll bundled by a media tool). Qt's hook supplies its own paths.
$originalPath = $env:PATH
$pythonFolder = Split-Path -Parent (Resolve-Path -LiteralPath $PythonExecutable).Path
$pythonBase = & $PythonExecutable -c "import sys; print(sys.base_prefix)"
try {
    $env:PATH = @($pythonFolder, $pythonBase, (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
    & $PythonExecutable -m PyInstaller --clean --noconfirm --onefile --windowed --name GrowYourGardenCompanion --icon $iconPath --distpath dist --workpath work/build --specpath work $entryPath
    if ($LASTEXITCODE -ne 0) { throw "Executable build failed." }
} finally {
    $env:PATH = $originalPath
}
Write-Host "Built: $PSScriptRoot\dist\GrowYourGardenCompanion.exe"
