param()
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { $Python = (Get-Command python).Source }
if (-not (Test-Path -LiteralPath (Join-Path $Root 'esp32'))) { throw 'Source root missing' }
& $Python (Join-Path $Root 'scripts\check_release.py')
exit $LASTEXITCODE
