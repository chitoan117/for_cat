# FOR_CAT — Overnight engineering 29/10/2026

Thời điểm đầu tiên kiểm tra đồng hồ của phiên tiếp nối: **28/10/2026 23:58:13 +07:00** (Asia/Ho_Chi_Minh). Mốc 23:47 do yêu cầu cung cấp; không có telemetry để xác nhận thời điểm thực thi trước23:58. Kiểm tra/đóng evidence cuối: **29/10/2026 00:25:29 +07:00**. Hoàn tất **6/6 milestone chuẩn bị offline**; dừng sớm, trước hạn05:00. Thời gian kết thúc ở đây là mốc finalize evidence, phần bàn giao văn bản hoàn tất ngay sau đó.

Phạm vi: phần mềm offline Windows, mô phỏng/fake I/O, build và deployment preparation. Không flash, mở thiết bị, điều khiển actuator, thay runtime/services/network/SQLite/NVS production. Servo/pump **LOCKED**. Không SSH trong phiên này; trạng thái3 Jetson services hiện tại **NOT VERIFIED**, thông tin đang chạy do owner cung cấp.

| PHASE | OFFLINE STATUS | PHYSICAL STATUS | EVIDENCE | NEXT ACTION |
|---|---|---|---|---|
|1 HX711 inox|PASS OFFLINE; BUILD PASS|BLOCKED PHYSICAL|`REAL_HARDWARE_BRINGUP_20261028/result.json`, runbook `.md` cùng stem|Owner kiểm tra logic3.3V rồi fresh FIT/VERIFY/reboot|
|2 Ultrasonic/PIR|PASS OFFLINE; BUILD PASS|BLOCKED PHYSICAL|`OVERNIGHT_ENGINEERING_20261029/native_result_pir_sensor_integration_quad_firmware_loop.json`, `native_result_current_hardware_loop.json`, `build_diag_four_ultrasonic.json`|Owner echo level protection; dùng profile4kênh/noRTC; HC1 40→15→40; JSN ngoài blind zone; PIR warm-up|
|3 CAT/DOG fusion|PASS OFFLINE; BUILD PASS|BLOCKED PHYSICAL|`native_result_restart_fusion_approach_dog_loop.json`, `build_cat_approach_dog_warning.json` trong session bundle|Owner buzzer-only rồi fusion hardware, không feed|
|4 Jetson deployment|PASS OFFLINE; BUNDLE READY|BUILD/RUNTIME NOT VERIFIED|`test_deployment.log`20PASS; immutable `release_phase4/manifest.json`; deployment runbook|Owner read-only preflight, staged ARM64 build; review topology|
|5 Camera deployment|PASS OFFLINE; BUNDLE READY|BUILD/STREAM/REMOTE NOT VERIFIED|`test_deployment_test_camera_deployment.log`40PASS; `release_camera/manifest.json`217files|Owner private config/preflight; LAN rồi4G theo runbook|
|6 Focused E2E|PASS OFFLINE; C++14 BUILD PASS|SIMULATED ONLY|`native_result_restart_fusion_overnight_e2e.json`, `overnight_e2e_test.log`, `handoff_result.json`|Owner physical sequence theo ưu tiên dưới đây|

## Checkpoint Phase 1 — 00:02 +07:00

Hoàn tất report/runbook `REAL_HARDWARE_BRINGUP_20261028.md`, dựa trên evidence đã có, không chạy lại test PASS không liên quan. 27 Python tests,81 inox firmware assertions,96 reference compatibility assertions,2 focused inox integration outcomes PASS. Diagnostic inox/reference BUILD PASS. Binary inox384848bytes SHA256 `1d334986e1ca066f674bc70c8a1a13931f948d47c8511ac36403a333fdd02974`.

Gross95→130 tính added35, không lấy tổng chén làm target. Module bowl policy chưa wired vào live closed-loop runtime. Không tự cấp bù; không auto tare. Host current-mount guard không tự migrate model cũ. Các điểm này là giới hạn tích hợp, không phải hardware PASS.

`HX711_BOWL_OFFLINE_READY=YES`

## Checkpoint Phase 2 — 00:06 +07:00

`SENSOR_OFFLINE_READY=YES`. Thêm `include/m4/pir_telemetry.h`: warm-up60s, debounce100ms, rollover-safe, telemetry only. `diagnostics.cpp` thêm `motion_valid`, `motion_quality`, `motion_stable`; trường `motion` legacy vẫn là raw level, được đánh dấu `motion_raw_legacy=true`. Chỉ dùng qualified fields khi cần ổn định; không dùng PIR thay AI hoặc tạo feed.

Focused PIR16checks PASS; actual4-channel integration27checks PASS; quad firmware34assertions PASS;5 current-hardware cases PASS. Integration xác minh guard60/80/100, không overlapping trigger, missing echo thành null, kênh khác vẫn chạy, JSN20cm bị từ chối khi fixture explicitly review min25cm. Minimum này không khẳng định module thật đã nghiệm thu.

Sửa fixture noise test cũ: golden HX reader cần3 raw conversions cho mỗi median observation; trước sửa, focused test báo `noisy scale claimed stable` do chỉ đưa4rawsamples. Bổ sung đủ4triplets, test PASS; không đổi thuật toán cân. Diagnostic current hardware BUILD PASS, binaries/hash ở session bundle mới. Không sửa/xóa binary/report lịch sử.

Physical: tất cả echo phải bảo vệ≤3.3V, JSN blind zone tùy module; chưa soak/geometry/warm-up thực tế. HC1 boot-near không arm, >30cm2s rearm,3 valid5–20cm trong1500ms,20–30cm hysteresis dựa FSM đã PASS; hardware protocol theo Phase1runbook.

## Checkpoint Phase 3 — 00:12 +07:00

`CAT_DOG_FUSION_OFFLINE_READY=YES`. Focused restart test11checks PASS: stale AI không feed, recovery cần encounter mới sau event hết hạn; sequence reset không replay event đã consumed; MCU changed boot/HELLO reset gate, boot-near không cảnh báo, old-session frame bị chặn, release/rearm sau cooldown phục hồi. Dùng actual E2E harness/arbiter/fake HX/servo/buzzer; không hardware.

Actual `approach_dog_loop`29assertions PASS sau thay đổi shared diagnostics. Rebuild `cat_approach_dog_warning` PASS vào bundle mới. Historical19cases186assertions vẫn là evidence CAT/DOG near/far, ambiguous DOG priority, NONE, stale, invalid, CRC/duplicate, cooldown; không chạy lại vì fusion/protocol không đổi. Không thay feed policy hoặc bypass arbiter.

Trong lúc viết test mới có access violation do summary logger trỏ tới fake clock đã hết lifetime; sửa fixture bằng summary clock riêng trước log, focused test PASS. Đây là lỗi test harness mới, không phải lỗi hardware/runtime.

## Checkpoint Phase 4 — 00:16 +07:00

`JETSON_DEPLOY_BUNDLE_READY=YES` (preparation only). Tạo source-only release173files/hash manifest,20focused Python tests PASS: integrity/path traversal, extra file rejection, staging disjoint production, no-overwrite, default plan no writes, build output isolated, read-only command allowlist, rollback fail-closed. Tools `release_bundle.py`, `jetson_preflight.py`, `jetson_build.py`, `stage_release.py`; hướng dẫn `DEPLOYMENT_RUNBOOK.md`.

Build plan C++14/OpenCV4/json-c/sqlite3/CUDA10.2/TRT; ARM64 thực tế **NOT VERIFIED**, không có Jetson binaries mới. Legacy detector stdout/tap pipeline không đổi. ROI producer tự ghiDB, không phải drop-in stdout detector; owner phải review topology riêng trước cutover. Không chạy hai AI cache writers/camera owners. Staging selector backup/rollback chỉ đổi pointer staging, không giả định đó là live runtime rollback. Live units chưa được đọc nên không tự sinh script overwrite cấu hình chưa biết.

## Checkpoint Phase 5 — 00:20 +07:00

`LIVE_CAMERA_JETSON_DEPLOY_READY=YES` (deployment preparation, không cutover). Không viết lại streaming hoặc Flutter. Thêm `camera_preflight.py`, `CAMERA_DEPLOYMENT.md`; frozen release217files gồm source/tools/docs và REAL static web đã PASS trước đó.40tests PASS (20deployment tests chạy lại vì packager thay đổi +20camera deployment focused). Không chạy lại browser/Flutter/backend streaming test cũ vì source không đổi.

Preflight chặn bind0.0.0.0, đổi provider sangREAL, CORS*, hostname sai/cross-origin, missing/private token trong release, missing view-only identity, web artifact thay đổi. Secret không in ra output. LAN/4G test plan dùng cùng HTTPS tailnet origin, không Funnel/publicports. Tailscale/network không bị thay đổi. Static main.dart.js giữ hash historical REAL. Linux permissions, ARM64/CUDA encode và actual network cần owner kiểm tra.

## Checkpoint Phase 6 — 00:25 +07:00

4 kịch bản integration mới,12checks PASS bằng actual `E2E_OFFLINE_DEMO_20261028/sim_support.h`: bowl95+food35=gross130; consumed5→DISLIKE và không top-up; INVALID HX không feed; AI stale trong fake feed đóng servo và báo fault; DOG bad CRC không beep, good frame2beeps, duplicate event không chạy lại.712 JSONL events,7 wire frames được kiểm CRC độc lập bằng Python, kể cả corrupt frame có chủ đích. Restart11checks và focused E2E12checks đều compile/run **C++14 PASS**; Arduino-stub setup/loop tests dùngC++17 vì stub inline variables.

Final preservation/hash checks PASS: golden HX reader/reference/calibration schema, LIVE camera backend/C++ source, Flutter source và release217files khớp source hiện hành. Không rerun full historical E2E56cases/5876events hoặc full Flutter suite. Không có FAIL chưa xử lý trong focused offline checks. Linux/ARM64 thực tế và hardware vẫn chưa xác minh.

**Chọn đúng sensor image:** kiểm tra bàn giao phát hiện `diag_current_hardware` là profile legacy còn RTC16/17/18, không dùng cho pin map4ultrasonic hiện hành. Binary đó chỉ là compatibility build. Đã build thêm **`diag_four_ultrasonic` PASS**, RTC removed, cả4echo OFF lúc boot; đây mới là sensor-only image đề xuất cho owner. Không thay pin hoặc flash để kiểm tra.

### Ma trận E2E A–J: evidence mới và evidence tái sử dụng

| Scenario | Kết quả offline | Evidence / phạm vi |
|---|---|---|
|A CAT near→arbiter→fake35g|PASS|Historical E2E + current inox/restart/focused E2E; vẫn qua arbiter|
|B DOG near→2fakebeeps/no feed|PASS|Historical19cases; current CRC/duplicate integration|
|C Inox + consumed30→LIKE|PASS|`REAL_HARDWARE_BRINGUP_20261028/result.json` gross95→130→100, không chạy lại|
|D Inox + consumed5→DISLIKE|PASS NEW|`overnight_e2e_test.log` gross95→130→125; no top-up|
|E INVALID HX→no feed|PASS NEW|Current inox integration, fake raw invalid|
|F Webcam absent / AI stale|PASS offline logic|Current AI-stale prefeed/during-feed checks; physical webcam unplug NOT VERIFIED|
|G UART duplicate/CRC|PASS NEW|Current fake protocol pipeline + independent Python CRC|
|H Many camera viewers/no backlog|PASS historical reused|`LIVE_CAMERA_REMOTE_PREP_20261028/verification.json` + actual localhost HTTP/browser logs; streaming source unchanged/hash checked; Jetson performance NOT VERIFIED|
|I Detector restart/stale/recovery|PASS offline logic|`restart_fusion_test.log`; fresh=false/NONE then new observations/encounter; actual service restart NOT VERIFIED|
|J Gross lớn vì chén→delta35g|PASS NEW + retained evidence|Current DISLIKE scenario gross95→130; prior inox LIKE test retained|

## File thay đổi và artifacts

Đường dẫn tương đối từ `D:\for_cat`; source authority vẫn là snapshot `FULL_HARDWARE_INTEGRATION_20261027`.

**Thay đổi production-source trong phiên tiếp nối overnight:**

1. `FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/include/m4/pir_telemetry.h` — mới, warm-up/debounce telemetry only.
2. `.../src/diagnostics.cpp` — thêm qualified PIR fields/begin/sample; legacy raw motion vẫn giữ để tương thích.
3. `.../test/current_hardware_loop.cpp` — noise fixture phù hợp median-of-three reader.

**Phase1 đã tạo trước checkpoint tiếp nối, được giữ và xác minh evidence:** `payload/jetson/app/bowl_mass.py`, `hx711_view.py`; firmware `include/m4/inox_mount_binding.h`, `src/hx711_reference_diag.cpp`, `platformio.ini`, `test/hx711_inox_loop.cpp`; E2E `sim_support.h`; tool/tests/verify và binary trong `REAL_HARDWARE_BRINGUP_20261028/`. Báo cáo mới `REAL_HARDWARE_BRINGUP_20261028.md` hoàn tất trong phiên này.

**Bundle mới `OVERNIGHT_ENGINEERING_20261029/`:**

- Native focused tests: `test_pir.cpp`, `test_sensor_integration.cpp`, `test_restart_fusion.cpp`, `test_overnight_e2e.cpp`; `verify_native.py`, `native/*.exe`, full compile/test logs và native_result JSON.
- Deployment/config tests: `test_deployment.py`, `test_camera_deployment.py`, `run_pytests.py`, full pytest logs/result JSON.
- Offline firmware packager `build_firmware.py`; `build_*.log/.json`; `firmware/{diag_current_hardware,diag_four_ultrasonic,cat_approach_dog_warning}/` gồm bin/ELF/bootloader/partitions.
- Staging tools `release_bundle.py`, `jetson_preflight.py`, `jetson_build.py`, `stage_release.py`, `camera_preflight.py`; các bản launcher/config prep đã PASS trước đó được copy vào release/tools, không chỉnh bản gốc.
- `DEPLOYMENT_RUNBOOK.md`, `CAMERA_DEPLOYMENT.md`; immutable `release_phase4/` checkpoint và **`release_camera/` release bàn giao217files**.
- `finalize.py`, **`handoff_result.json`**: thời điểm, readiness, source/binary/manifest hashes, evidence inventory và preservation checks. Không chứa secret.

### Firmware/binary

| Profile | App bytes | SHA256 firmware.bin | Dùng cho |
|---|---:|---|---|
|diag_hx711_inox|384848|`1d334986e1ca066f674bc70c8a1a13931f948d47c8511ac36403a333fdd02974`|Phase1; nằm trong REAL_HARDWARE_BRINGUP bundle|
|diag_four_ultrasonic|399584|`f6369f2947ca1b8f5bd4f634b4f045cd443725cad6a7e3e960c601d07f54c5be`|Sensor-only pin map4kênh/noRTC; chưa flash|
|cat_approach_dog_warning|401408|`eb8db978adee5c9ff959322b783048712b62a1a57294e7dcec78f58e6a5b29ea`|Warning integration, servo/pump locked; chưa flash|
|diag_current_hardware|399056|`bbe149e729bc05fff18ca14252ec538ff48651760c3a8292cc3c41035592a6e3`|Legacy compatibility artifact, **không dùng với wiring4kênh hiện tại**|

`native/*.exe` chỉ fake I/O trên Windows, không phải firmware/Jetson binaries. ELF/bootloader/partitions hashes nằm trong build JSON. Buzzer-only image historical được giữ nguyên, không build lại vì source không đổi. **Không có ARM64/CUDA binary mới đã nghiệm thu.**

## Giới hạn còn lại và thứ tự sáng mai

1. **HX711 BLOCKED_PHYSICAL:** kiểm tra mức logic3.3V/commonGND/mounting chén; sau đó owner flash diagnostic inox, bowl-only30s, fresh FIT0/5/10/20/35/38, independent VERIFY+return, explicit save/reboot0/35/0. Không tái dùng pair mounting cũ, không tare che drift. Theo `REAL_HARDWARE_BRINGUP_20261028.md`.
2. **4ultrasonic/PIR BLOCKED_PHYSICAL:** sensor image đúng `diag_four_ultrasonic`, không legacy RTC. Sau echo-level review, owner dùng `ultra-select hc1 CONFIRM`, `ultra-select jsn1 CONFIRM`, `ultra-select hc2 CONFIRM`, `ultra-select jsn2 CONFIRM` để review/test từng kênh; `ultra-multiplex CONFIRM` chỉ sau cả4kênh reviewed. `ultra-guard 80 CONFIRM`; `ultra-off CONFIRM` khi cần dừng acquisition. HC1 40→15→40; JSN dùng range ngoài blind zone module; PIR đợi≥60s và xem motion_quality/valid/stable, không feed. Physical chattering/temperature/soak chưa kiểm tra.
3. **DOG buzzer BLOCKED_PHYSICAL:** owner buzzer-only kiểm tra GPIO2 ACTIVE_LOW3.3V/2×200ms, rồi shared approach+AI integration. Servo/pump vẫn khóa. Không kết luận buzzer đã kêu từ fake tests.
4. **Jetson NOT VERIFIED:** owner chạy read-only preflight/staged ARM64 build; kiểm source live, service units/ExecStart/environment, single camera/cache writer. Legacy stdout/tap khác candidate direct-DB topology, cần review cutover. Phiên này không SSH, không đọc được current service state; không stop/restart3 services.
5. **Camera/remote NOT VERIFIED:** dùng private config/preflight; owner maintenance window kiểm local/LAN/4G, viewer cap/disconnect/stale/recovery và performance. Không đổi providerMOCK hoặc bật publicFunnel. `run_secure_api.py` thực sự startAPI, không phải dry-run; tuyệt đối không chạy cạnh production8000 một cách vô ý.
6. **Live feed integration chưa hoàn tất:** bowl policy chưa wired vào runtime closed-loop; host legacy calibration store không tự migration mountbinding. Cần explicit integration sau khi có current-mount evidence. Servo90°/45° mới nominal, chưa proof closure/flow/overshoot; pump polarity/bootOFF/powerflow chưa nghiệm thu. Không unlock trước các bước này.

Không có blocker hiện tại cần tăng model. Lỗi khó cần phần cứng được giữ BLOCKED_PHYSICAL; không vượt bằng tare/refit/giả measurement. Cấu hình live chưa biết thì giữ NOT VERIFIED thay vì đoán backup/cutover. Staging rollback tool không thay thế backup/rollback systemd/network thực tế.

## Trạng thái bắt buộc

```text
OVERNIGHT_SOFTWARE_READY=YES
HX711_BOWL_OFFLINE_READY=YES
SENSOR_OFFLINE_READY=YES
CAT_DOG_FUSION_OFFLINE_READY=YES
JETSON_DEPLOY_BUNDLE_READY=YES
LIVE_CAMERA_JETSON_DEPLOY_READY=YES
HX711_PHYSICAL_PASS=NOT_VERIFIED
SENSOR_PHYSICAL_PASS=NOT_VERIFIED
DOG_BUZZER_PHYSICAL_PASS=NOT_VERIFIED
JETSON_REAL_DEPLOY_PASS=NOT_VERIFIED
```

Thao tác đầu tiên sau khi thức dậy: kiểm tra mounting chén/common GND/mức logic HX7113.3V theo runbook Phase1; servo/pump tiếp tục khóa. Không triển khai runtime hoặc cấp thức ăn trước khi kiểm tra cân thật.
