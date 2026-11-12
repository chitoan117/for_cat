$ErrorActionPreference='Stop'
$reportRoot=Split-Path -Parent $PSScriptRoot
$reportPython=Join-Path $reportRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $reportPython)) {
  throw 'Hãy tạo backend/.venv và cài requirements-realtime.txt theo README_VI.md trước.'
}
$env:ESP32_BRIDGE_ENABLED='0'
$env:SYSTEM_STATE_PROVIDER='MOCK'
$env:ESP32_TRANSPORT='MOCK'
$env:CAMERA_PROVIDER='MOCK'
$env:AI_RUNTIME='MOCK'
$env:AI_SHADOW_MODE='true'
$env:SCHEDULED_DRY_RUN_WORKER_ENABLED='0'
$env:API_HOST='127.0.0.1'
$env:API_PORT='8000'
$env:DATABASE_PATH=Join-Path $reportRoot 'backend/jetson/data/report_demo.db'
$env:FORCAT_FLUTTER_WEB_DIR=Join-Path $reportRoot 'web_release'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $env:DATABASE_PATH) | Out-Null
Push-Location (Join-Path $reportRoot 'backend/jetson')
try { & $reportPython -m tools.run_api } finally { Pop-Location }
