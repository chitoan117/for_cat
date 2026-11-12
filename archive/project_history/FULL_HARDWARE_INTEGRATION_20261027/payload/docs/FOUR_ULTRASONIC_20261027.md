# Four ultrasonic — 27/10/2026

Owner-approved wiring, physical validation NOT_TESTED. Servo/pump/AUTO remain disabled.

| Canonical ID | TRIG | ECHO | Role |
|---|---:|---:|---|
| HC_SR04_1 |12|13|CAT_APPROACH|
| JSN_SR04T_1 |14|15|WATER_LEVEL|
| HC_SR04_2 |16|17|TBD|
| JSN_SR04T_2 |18|10|TBD|

RTC REMOVED. All ECHO10k high/20k GND per owner, not a measured voltage certificate.
Current firmware source release is in `evidence/full_hardware_integration_20261027_*/stage/firmware/esp32`;
the staged root `esp32/` is preserved legacy work and must not be flashed as this release.

## Additive contract

ASCII JSON firmware retains mode `diag_current_hardware`, telemetry schema2 and all legacy fields.
Adds `ultrasonic_schema_version:1` and `ultrasonic:{HC_SR04_1:{...},HC_SR04_2:{...},JSN_SR04T_1:{...},JSN_SR04T_2:{...}}`.
No binary/UART CRC/request change, line bound4096 remains. Unknown extension versions/malformed data reject safely.
Existing firmware lacking extension continues through old parser/aliases; #2 remains UNKNOWN, not a synthesized reading.

Each entry: type/role/trigger_gpio/echo_gpio, wired/configured/enabled, distance_cm/valid,
timeout/stale/state, sample_age_ms/last_update, last_valid_distance_cm/last_valid_update, timeout_count.
`last_update` is the uint32 MCU millis of the latest completed acquisition (including failure), not UTC.
`sample_age_ms=(report_monotonic_ms-last_update) mod 2^32`; unknown timestamps are null.
Last-valid history is retained across ordinary timeouts, never reused as current distance.
SystemState adds host receive age to sample age; if >2000ms initial bench freshness bound, current value is null/STALE.
Link unavailable also hides current values. Wiring/config metadata is not a physical PASS.

C++ normalization stores the map inside the existing telemetry JSON in canonical SQLite;
SystemState exposes the same four IDs in top-level `ultrasonic`. `/api/status` and `/api/ws/state` share it.
`/api/v1/esp32/status` shows normalized telemetry plus updated declaration metadata.
Legacy `approach`/`water_operational` remain the first HC/JSN sensor; no #2 value overwrites them.
Reservoir percentages stay null/NOT_CONFIGURED because #2 roles/geometry are TBD; wired does not imply %.

## Acquisition and physical sequence

All channels OFF on boot; no boot command writes NVS or arms output.
`ultra-select hc1 CONFIRM`, `jsn1`, `hc2`, `jsn2` select exactly one sensor.
`ultra-off CONFIRM` disables all when idle. `ultra-multiplex CONFIRM` requires every
channel individually initialized/reviewed first. One acquisition at a time; guard80ms
after completion/failure, per-channel minimum500ms, bounded echo timeout30ms.
These are initial bench parameters, not final near/water behavior thresholds.
Firmware state machine yields and avoids slow HX/I2C/serial work during active echo.

Physical order: HC1 → JSN1 → HC2 → JSN2, each with flat target30–50cm, ≥20 independent
reports, jitter/timeout/age record, then near/far direction proof. Only after individual
results qualify run four-channel cross-talk test. No inference from one sample.
OLED/PIR/button regression and HX raw/load response follow; gram calibration remains a separate supervised session.

## Rollout

Host changes are tested in isolated SQLite/PTY fixtures, then atomically installed with backups.
One API and one bridge restart needed, AI untouched. Manual ESP32 flash is required for four actual streams.
Host deployment before flash must display firmware_supported=false and #2 UNKNOWN, not zero or NOT_WIRED.
Use `flash_app_only.py --help` in the evidence deployment directory for the exact reviewed manual command.
No flash is performed by software preparation. Servo/pump power must be isolated before bootloader/reset operations.
