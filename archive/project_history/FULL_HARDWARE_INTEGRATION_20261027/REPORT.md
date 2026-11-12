# Full hardware integration — 27/10/2026

## Kết luận hiện tại

Host integration **RUNTIME_PASS**; firmware/vertical software **SOFTWARE_READY**.
**ESP32 FLASH REQUIRED** — chưa thực hiện flash, chưa gửi sensor acquisition/servo/pump command.
Physical validation vẫn **NOT_TESTED**; không có PHYSICAL_PASS mới.

## Bảo vệ baseline

Evidence: `/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/`.
Git branch main, HEADdff667d13ac0cff78a494ab33070c1e9cf583f3f, original36 staged files/index
SHA2561cd1e194acc1cd884dc1ff147936cdcf64be43cd8fdaa03a0a6d7673a91caae8 được giữ.
Preflight ghi full staged/unstaged diff/untracked trước khi sửa, backup source/config/firmware staged,
bridge executable, frontend/source mirror/release cũ, units/drop-ins, consistent SQLite backup integrityok,
AI source/binary/engine metadata. Không reset/clean/stage/commit hoặc xóa dữ liệu/evidence.

Ba services hoạt động; serial và camera mỗi thiết bị một owner. AI C++ TensorRT ONLINE/NONE,
không model/engine/source/binary change. Bridge và API restart có kiểm soát cho host update;
AI service không restart. Worker enabled/running, DRY_RUN_ONLY, Asia/Ho_Chi_Minh, last_error=null.
Meal Plan và HX calibration metadata được đối chiếu giữ nguyên qua rollout.
Các bảng cấp thật feed_requests/feeding_records/feed_events giữ nguyên0/0/0.

## Pin map và wiring

Owner xác nhận HX4/5, servo6, pump7, OLED8/9, PIR11, button21; HC1 12/13,
JSN1 14/15, HC2 16/17, JSN2 18/10. RTC REMOVED, reserved pins list rỗng.
Nguồn và divider10k/20k/common GND là lời xác nhận wiring, không phải phép đo mới.
All four canonical inventory entries ghi wired=true nhưng physical_status=NOT_TESTED.
Các physical facts cũ trong config/document retained là lịch sử, không thay kết quả assembly mới.

## Những gì đã tích hợp

- Firmware profile `diag_four_ultrasonic`: RTC không init/poll/set, all echoes OFF khi boot,
  GPIO6/7 disabled; HC1→JSN1→HC2→JSN2 đọc tuần tự nếu multiplex được cho phép.
- Một channel active acquisition; guard80ms sau success/failure, min500ms/kênh,
  timeout30ms, không long-delay mới. Thông số khởi đầu bench, chưa ngưỡng hành vi cuối.
- ASCII JSON extension `ultrasonic_schema_version=1`, map4 uppercase IDs, mode/schema2 và
  legacy two-channel fields giữ. UART/binary CRC/request framing không đổi; bound4096.
- Mỗi kênh có enabled/configured/wired, distance/valid/timeout/stale/state,
  sample_age_ms/last_update, last_valid_distance_cm/last_valid_update, timeout_count, role/pins.
- Invalid distance=null; last-valid history không bị dùng làm current reading. MCU clock32 wrap
  được kiểm; C++ kiểm identity/pins/roles/flags/age và legacy aliases.
- Cùng C++ bridge RX-only chuẩn hóa4 kênh vào JSON trong SQLite hiện có; không schema migration.
- SystemState/REST/WS expose `ultrasonic` map4 ID; tăng tuổi mẫu theo host receive age,
  stale/lost link ẩn current distance, giữ historical fields để chẩn đoán.
- Legacy approach/water_operational vẫn là HC1/JSN1. #2 rolesTBD, không tự biến thành reservoir%.
- Flutter REAL System→Ultrasonic đọc canonical map, state/distance/age/pins/role riêng từng kênh.
  Metadata thiếu hoặc mất backend không quay về pin RTC reserved cũ; không fake distance.

Additive backend contract changes chỉ gồm map/version/metadata mới và nullable age/state fields;
không route mới, không thay request/receipt/worker/Meal Plan/arbiter. Old firmware không có extension
vẫn được chấp nhận; #2 UNKNOWN + firmware_supported=false + flash-required reason.

## Deployment

- Host files: `config/hardware_current.json`; `jetson/device/telemetry.h`, `ultrasonic_telemetry.h`,
  `test_ultrasonic.cpp`; `jetson/app/device_state.py`, `system_state.py`, `ultrasonic_state.py`;
  `jetson/tests/test_system_state.py`, `test_ultrasonic_state.py`;
  `docs/CURRENT_PROJECT_STATE.md`, `FOUR_ULTRASONIC_20261027.md`.
- Tested bridge binary replaces executable atomically with backup; no serial TX path added.
- REAL UI release `.native-build/flutter/four_ultrasonic_20261027_r2`; only40-flutter-real.conf
  changed asset path,50-scheduled unchanged. Old releases kept for rollback.
- Flutter source changes at `D:/DA_KT_NC/feeder_demo`: `lib/diagnostic_models.dart`,
  `lib/diagnostics_page.dart`, new `test/ultrasonic_real_test.dart`. Source mirror Jetson not blindly overwritten.
- Firmware source is the isolated reviewed `stage/firmware/esp32`, compiled images in
  `host_release/firmware`. The root staged `esp32/` stays legacy work and must not be flashed as this release.
- REAL and MOCK web build succeeded; only REAL deployed. 14 REAL browser screenshots verify
  navigation, new4-channel display and client-only outage/recovery without POST/fallback.

## Regression

| Check | Kết quả |
|---|---|
| Backend staged and post-deploy on Jetson |445 tests, SOFTWARE_READY|
| Flutter final |63 tests, analyze clean, SOFTWARE_READY|
| JS existing request client |14 tests, SOFTWARE_READY|
| Total unit/widget/Python/JS |522 tests (not physical)|
| Firmware MCU build |diag_four_ultrasonic + legacy diag_current_hardware, SOFTWARE_READY|
| Native UBSan |3576 assertions/checks across scheduler/real loop/parser/legacy drivers/policy/decision/fake dispense|
| Compatibility |2 generated firmware frames accepted by bridge|
| Host checks |pip check, git diff --check, staged diff --check clean; index and protected AI hashes preserved|

All synthetic records go to isolated temporary/evidence test DBs or PTYs, never canonical REAL SQLite.
Early test attempts needed stage-root/support-fixture corrections and typed Dart fixture correction;
attempt logs retained. Final results above include whole suites, not only failed test retries.
The extra63rd Flutter case fixes offline pin metadata reverting to obsolete reserved/proposed pins.
The final frontend build is r2, not superseded r1.

## Trạng thái từng phần

| Hạng mục | Trạng thái | Giới hạn |
|---|---|---|
| HC-SR04 #1 |SOFTWARE_READY|Old firmware echo disabled, no new target/near-far test|
| JSN-SR04T #1 |SOFTWARE_READY|Old firmware echo disabled, no new target test|
| HC-SR04 #2 |SOFTWARE_READY|Host wired metadata true; runtime value UNKNOWN pending manual flash|
| JSN-SR04T #2 |SOFTWARE_READY|Same; roleTBD, no sample/physical PASS|
| Cross-talk |NOT_TESTED|Only fake-overlap/scheduling tests done; needs real four streams|
| HX711 |NOT_CALIBRATED|Raw available; no new known-load test or RAW_PHYSICAL_PASS in this milestone|
| OLED |NOT_TESTED|Runtime telemetry HEALTHY/config0x3C; no new panel observation|
| PIR |NOT_TESTED|Runtime configured/motion exists; no controlled physical transition test|
| Button |NOT_TESTED|No supervised short/hold5s/release sequence in this milestone|
| Servo |BLOCKED|No motion command, no PWM attachment permission|
| Pump |BLOCKED|No ON command/flow test|

Safety remains AUTO_FEED=false, AUTO_WATER=false, servo_armed=false, pump_armed=false,
actuator_outputs_enabled=0, actuator_execution=false, actual_dispensed_grams=null.
Active HX model stays null; no fake grams/tare/scale or actual dispense.

## Manual flash and next physical action

Isolated esptool5.3.0 installed in evidence `flash_tool/`, not production/AI venv.
`flash_app_only.py` default only prints plan: serial_opened=false/flash_performed=false.
Write mode checks image SHA, expected USB identity, safety, unique port owner,
bootloader/partition compatibility, writes **only0x10000 app**, verifies image and NVS unchanged,
then restarts RX bridge in finally. No erase-all/factory/partition/NVS write command.

Exact manual command, **only after external servo/pump power is disconnected**:

```sh
E=/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z
"$E/flash_tool/bin/python" "$E/flash_app_only.py" --write-app --power-isolated
```

Firmware SHA256: df6efed399250ec7a876587af9b32daf6569452b261a23eec92e344db7014786.
Script logs its own timestamped manual_flash_* directory when the operator actually runs it.
If bootloader/partition/identity/NVS check fails: stop and report, never force factory flash.

**Single next physical action now:** disconnect external servo/pump power while keeping Jetson/ESP32 USB powered,
then confirm that isolation. Flash remains a separate operator step; no target or weight placement requested yet.
After manual flash: re-check baseline/safety, then place a flat target30–50cm for HC1 only and collect ≥20 samples;
near/far proof follows. Do not enable all four until every channel is verified individually.
