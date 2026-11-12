# Physical resume 27/10/2026 — baseline và frontend RUNTIME_PASS; physical đang BLOCKED

## Điểm dừng quan trọng

Không kích echo sau lắp lại, không mở port diagnostic/TX, không flash, không servo/pump.
Bản firmware tham chiếu của app đã flash vẫn có RTC polling16/17/18; mapping #2 đề xuất dùng chính các chân này.
Wiring thực tế #2 sau lắp lại hiện UNKNOWN; metadata NOT_WIRED cũ không xác nhận được dây hôm nay.
**Cần người dùng cách ly #2 khỏi16/17/18/10 trước khi kích sensor**, sau đó kiểm mức áp/common GND và testHC#1.

## 1–5. Jetson, ESP32, deploy, services, safety

- Branch main, HEAD `dff667d13ac0cff78a494ab33070c1e9cf583f3f`, ahead6. 36 staged files được giữ, index SHA256 `1cd1e194acc1cd884dc1ff147936cdcf64be43cd8fdaa03a0a6d7673a91caae8`.
- Full staged/unstaged diff và untracked inventory được ghi trước backup. Không reset/clean/stage/commit, không xóa evidence hoặc database.
- Backup: backend/device/tools/tests/firmware/config/source liên quan, frontend release cũ và frontend source mirror, systemd user units/drop-ins, Git index; SQLite online consistent backup integrity=ok; AI source/binary/engine metadata SHA256.
- ESP32 `/dev/ttyACM0` có một owner bridgePID4050; camera `/dev/video0` owner detectorPID4082; một detector TensorRT; API8000.
- AI ONLINE/NONE ở lúc quan sát, source EXISTING_CPP_TENSORRT_STDOUT. Không chứng minh mới CAT/DOG physical trong phiên này; model/engine/source/binary không thay.
- Ba services running. API restart có kiểm soát để nhận asset path: PID4052→12167; bridgePID4050 và AI wrapperPID4049 không restart.
- Worker enabled/running=true, DRY_RUN_ONLY, Asia/Ho_Chi_Minh, last_error=null. Meal Plan/occurrence giữ nguyên.
- mDNS Windows từng lỗi resolve tạm; dùngIP192.168.123.8 được lấy qua SSH hostname -I, giữ HostKeyAlias=server-jetson.local. Không sửa mạng Jetson.
- Unit còn các adapter legacy MOCK inert để không mở serial/camera thứ hai; SystemState và AI quan sát là REAL/C++ thật. Không đổi các env này vì không phải fallback.

**Deploy:** chỉ upload REAL41 assets; asset audit1 added/10 changed/1 removed. Release mới:
`/home/toan/for_cat/.native-build/flutter/offline_rc_20261026_resume_20261027_r1`.
Chỉ đổi đường dẫn trong `~/.config/systemd/user/for-cat-api.service.d/40-flutter-real.conf`, giữ nguyên50-scheduled và backend source/config.
Backup40 drop-in cụ thể có trong `backup/40-flutter-real.conf.original`; release cũ vẫn còn.
`/app`, `/kiosk`, `/diagnostics`, REST, WS đều RUNTIME_PASS;12 ảnh REAL ở Windows.
Client-only HTTP/WS fault injection cho OFFLINE/UNKNOWN, không MOCK fallback, hồi phục khi bỏ fault. Không pause service để thử.

**Safety thực đọc:** auto_feed=false, auto_water=false, servo_armed=false, pump_armed=false,
actuator_outputs_enabled=0, actuator_execution=false; actual=null được xác nhận ở HX/worker APIs.
SystemState feed chưa expose actual field riêng; không sửa contract hoặc suy missing thành một phép đo0.
Servo state PWM_NOT_ATTACHED_CLOSE_PHYSICAL_UNVERIFIED, pump state OUTPUT_NOT_ENABLED_PHYSICAL_OFF_UNVERIFIED: cờ không thay phép đo điện/closure.
Các bảng feed_requests/feeding_records/feed_events vẫn0/0/0.

## 6–12. Sensor/calibration

| Hạng mục | Trạng thái phiên này | Bằng chứng / giới hạn |
|---|---|---|
| HC-SR04 #1 | BLOCKED | Raw API health NOT_CONFIGURED, ACKfalse, distance null; chưa voltage review/đặt vật/kích echo sau lắp lại |
| JSN #1 | BLOCKED | NOT_CONFIGURED, ACKfalse, null; chưa kích hoặc test30–50cm |
| HC #2 | BLOCKED | Bản chạy chưa có raw kênh #2; wiring hôm nay UNKNOWN, pin16/17 còn conflict RTC legacy |
| JSN #2 | BLOCKED | Chưa có kênh; đề xuất18/10 chưa physical verify, không suy metadata NOT_WIRED cũ thành kiểm dây thật |
| OLED | RUNTIME_PASS | Telemetry HEALTHY, cấu hình0x3C; chưa người dùng nhìn panel xác nhận mới |
| PIR | RUNTIME_PASS | Telemetry configured, có motion/counter; chưa có timed physical regression chủ động |
| GPIO21 | NOT_TESTED | ReleaseHIGH/raw1 trong baseline, request0; short/hold5s/release chưa làm phiên này |
| HX711 raw | RUNTIME_PASS |16 snapshot/30s raw available, min−669887, max−669731; không saturation/stuck trong cửa sổ này. Tải hiện tại UNKNOWN, chưa load/unload proof |
| HX711 grams | NOT_CALIBRATED | Gramsnull, active modelnull. Candidate/điểm cũ giữ nguyên, không lấy candidate làm active |
| Calibration/persistence mới | NOT_TESTED | Chưa hướng dẫn đặt0g nên không gán nhãn0g cho mẫu nền, chưa fit/activate/reset/save |

HX software path đã có: firmware avg/tare/cal/validate/save/load trong source tham chiếu; NVS m4-calibration/sensors-v2/CRC16/39byte.
Firmware offset/factor không expose đầy đủ nên không suy0; không đọc/ghiNVS trong phiên này.
Host authority lưu cùng SQLite qua hx711_calibration_sessions/points/active, binding USB/pins, signed factor, checksum,
verify độc lập và post-activation restart gate; API chỉ đọc /api/hx711/status và /api/hx711/calibration.
Frontend chỉ READINESS. Không cần patch calibration tối thiểu lúc này; phải thu reference mới sau lắp lại.
Expected/measured/error/error_percent/stable của phép đặt tải mới vẫnnull/UNKNOWN vì người dùng chưa xác nhận tải.
Sau0/5/10/20/30/35 FIT phải NEW VERIFY0/5/10/20/30/35/0, rồi mới xét activation/persistence0/35/0 sau restart.

## 13. Firmware

Để bench #2 cần firmware mới hoặc một đường diagnostic được review hỗ trợ chúng. Đã chuẩn bị candidate r2 riêng, **chưa flash**:
`firmware_candidate_r2/` trong remote evidence; source local `firmware_candidate/esp32/`.
RTC tắt hoàn toàn ở profile mới, một echo tại một thời điểm, cả4 mặc định tắt, rôlesTBD cho #2; actuator disabled.
Pin map vẫn PROPOSED_NOT_PHYSICAL_VERIFIED. Source staged Jetson không bị sửa.
Raw extension #2 chưa được production bridge/SystemState/UI đưa ra API: ghi giới hạn rõ, không sửa backend production cho sensor chưa flash.
Xem `FIRMWARE_CANDIDATE_FLASH_NOT_RUN.md` cho prerequisites, lệnh app-only0x10000 và kiểmNVS.
Runtime venv chưa có esptool; tool venv riêng/manual flash là bước tương lai, không cài tool vào AI/production env.

## 14. Files thay đổi

- Production: duy nhất40-flutter-real.conf trỏ immutable REAL release mới; thêm asset directory mới, không đè release cũ.
- Không thay backend source/schema, config/hardware_current.json, AI/model/engine,50-scheduled, firmware đang chạy hoặc staged Git.
- Evidence mới dưới path bên dưới; candidate source5 file sửa +4 file mới trong workspace riêng (platformio, diagnostic source/config, pin/Arduino adapter, quad header,3 tests), patch/checksum đi kèm.
- Không đồng bộ frontend source mirror Jetson cũ bằng overwrite; build marker có source SHA của Windows RC đã freeze.

## 15. Regression

- Backend thực trên Jetson:428 tests, gồm Linux/PTY synthetic và Scheduled Worker; SOFTWARE_READY. Không inject fixture vào REAL DB.
- Flutter54 tests, analyze sạch; JS14 tests; SOFTWARE_READY. Tổng496 unit/widget/backend/JS, không gọi là physical test.
- Candidate MCU profile build, native UBSan:65+28+3351+36+67+9=3556 assertions/checks; thêm compatibility2 raw frames. Tất cả fake I/O, không servo/pump test thật.
- pip check, git diff --check và staged diff --check sạch; index/AI/backend/config đối chiếu checksum.
- Native harness ban đầu thiếu linker json-c/fixture argv và browser URL block chưa chặn WS; sửa harness, không sửa production để làm test đạt. Giữ attempts trong evidence.

## 16–17. Evidence và bước kế tiếp

Remote:
`/home/toan/for_cat/evidence/physical_resume_20261027_20261027T004813554339Z/`
Local:
`D:/for_cat/PHYSICAL_RESUME_20261027/`

Đọc `preflight_summary.json`, `baseline_runtime_summary.json`, `frontend_deploy_summary.json`,
`regression/summary.json`, `firmware_candidate_r2/software_test_summary.json`, client evidence và manifest SHA256.

**Dừng physical ở đây:** ngắt nguồn ESP32 rồi cách ly sensor #2 khỏi16/17/18/10 trước khi cấp lại và xác nhận wiring.
Sau đó mới review divider/GND của HC#1 và đặt vật phẳng30–50cm, kích/thu nhiều mẫu một sensor.
Không nhảy sang tare/calibration, không kích4 sensor cùng lúc, không servo/pump/auto physical.
