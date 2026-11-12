$ErrorActionPreference='Stop'
$reportRoot=Split-Path -Parent $PSScriptRoot
$reportOutput=Join-Path $reportRoot 'web_build_local'
Push-Location (Join-Path $reportRoot 'frontend')
try {
  & flutter pub get
  if ($LASTEXITCODE -ne 0) { throw 'flutter pub get failed' }
  & flutter build web --release --no-web-resources-cdn --base-href=/flutter/ --dart-define=FEEDER_MODE=real --output=$reportOutput
  if ($LASTEXITCODE -ne 0) { throw 'flutter build failed' }
  $marker=@{mode='REAL';base_href='/flutter/';target_grams=35;source='LOCAL_REPORT_SOURCE_BUILD'} | ConvertTo-Json
  [System.IO.File]::WriteAllText((Join-Path $reportOutput 'forcat_build.json'),$marker,[System.Text.UTF8Encoding]::new($false))
  Write-Output "Đã build: $reportOutput"
} finally { Pop-Location }
