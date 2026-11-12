param(
    [Parameter(Mandatory=$true)][ValidateSet('esp32s3_16mb_no_psram_hw_safe_uart','diag_i2c','diag_rtc','diag_hx711','diag_food_sensor','diag_water_sensor','diag_oled_button_buzzer')][string]$EnvName,
    [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Use the supported Windows build environment; Jetson linux_aarch64 package is not forced.' }
$Root = Split-Path -Parent $PSScriptRoot
$Pio = Join-Path $Root '.tools-venv\Scripts\pio.exe'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath (Join-Path $Root 'esp32'))) { throw 'Source root missing' }
if (-not (Test-Path -LiteralPath $Pio) -or -not (Test-Path -LiteralPath $Python)) { throw 'Existing isolated Windows Python/PlatformIO environments required.' }
& $Pio run --project-dir (Join-Path $Root 'esp32') -e $EnvName
if ($LASTEXITCODE -ne 0) { throw 'Build failed; no deploy bundle produced.' }
$Arguments = @((Join-Path $Root 'scripts\prepare_esp32_deploy.py'), '--env', $EnvName)
if ($OutputDirectory) { $Arguments += @('--output', $OutputDirectory) }
& $Python @Arguments
if ($LASTEXITCODE -ne 0) { throw 'Deploy bundle verification failed.' }
