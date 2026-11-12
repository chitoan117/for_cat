param([switch]$WithOpenCV)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $Root 'jetson\requirements.txt'))) {
    throw 'Run from the forr_cat source tree.'
}
if (Get-Command py -ErrorAction SilentlyContinue) { py -0p }
python -c "import sys; print(sys.version); sys.exit(0 if sys.version_info >= (3, 10) else 2)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ required; system Python was not modified.' }
$DevPython = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $DevPython)) {
    python -m venv (Join-Path $Root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated development venv.' }
}
& $DevPython -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 2)"
if ($LASTEXITCODE -ne 0) { throw 'Existing venv Python is unsupported; it was not overwritten.' }
& $DevPython -m pip install -r (Join-Path $Root 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) { throw 'Project/test dependency installation failed.' }
if ($WithOpenCV) {
    & $DevPython -m pip install 'opencv-python==4.13.0.92'
    if ($LASTEXITCODE -ne 0) { throw 'Optional OpenCV installation failed.' }
}
$ToolsPython = Join-Path $Root '.tools-venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $ToolsPython)) {
    python -m venv (Join-Path $Root '.tools-venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create PlatformIO venv.' }
}
& $ToolsPython -m pip install 'platformio==6.2.0'
if ($LASTEXITCODE -ne 0) { throw 'Isolated PlatformIO installation failed.' }
'Python/test and PlatformIO environments prepared. No system Python or AI frameworks were replaced/installed.'
if (-not (Get-Command zig -ErrorAction SilentlyContinue) -and
    -not (Test-Path -LiteralPath (Join-Path $Root '.tools-zig'))) {
    "Optional HOST C++ harness (official portable Zig): winget install --id zig.zig --exact --location `"$(Join-Path $Root '.tools-zig')`" --silent --accept-package-agreements --accept-source-agreements --disable-interactivity"
}
