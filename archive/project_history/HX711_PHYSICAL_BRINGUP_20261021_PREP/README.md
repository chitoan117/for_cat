# HX711 physical bring-up #1 — prepared, not physically verified

**Profile:** `diag_hx711` · **DOUT4 / SCK5** · UART0 bridge115200 · ESP32-S3/16MB/noPSRAM.

The existing driver and diagnostic command API were reused. Firmware source was
not changed. Servo and pump remain disabled, CAT/DOG source is untouched. No board
flash or physical serial session was executed by the agent; device enumeration
listed no ports at preparation time.

## Start here
- `HX711_LOADCELL_BRINGUP.md`: complete Windows build/flash/monitor and STEPA–E runbook.
- `physical_observations_TEMPLATE.md`: record actual known mass, raw readings,
  validation errors and reboot results. Copy to a NEW actual-observations file
  before filling; send the copy back with the original log.
- `deploy_hx711/deploy_manifest.json`: exact prepared binary hashes.
- `preparation_summary.json`: actual build/config checks and PHYSICAL_NOT_VERIFIED.
- `pio_build_diag_hx711.log`, `compiled_config_probe.json`, `image_info.log`: software evidence.

Factory image:452768bytes SHA256
`71693b72dae84ba2195c460e71476c0bf0cb9083faef8d026249943e91836e6e`.
App:387232bytes SHA256
`ad67dd0c2a70835672cdbf24c3bcbf369c031dcdf8c0fb5c0f291582bf97f775`.

Initial factoryflash may overwrite NVS/gaps; review/backup before applying.
Persistence STEP E uses a real reset/powercycle, **not reflashing**.

After `tare 16`, old calibration is deliberately invalidated; `avg 16` prints raw
counts and grams staynull until calibration. Wait for each asynchronous result.
Use only the actual independently known reference mass. No100gdefault, calibration
factor, noise/error tolerance or physicalPASS is invented.

`release_sha256.json` covers preparation artifacts and the runbook/template as
published. Keep actual operator logs separately under `logs/`; future measurements
are not part of this pre-test manifest and must not be fabricated.
