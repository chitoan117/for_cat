# Project folder map và handoff — for_cat, checkpoint 27/10/2026

Tài liệu đọc cấu trúc **Windows `D:/for_cat`** tại thời điểm tạo; không build, test hay truy cập Jetson trong lần lập map. AI scope hiện hành **CAT / DOG / NONE**, không có phân biệt danh tính mèo. Mục tiêu feed **35 g/lần**, `actual_dispensed_grams` chỉ là kết quả đo thật, hiện chưa xác minh.

## 1. Trước khi sửa: phân biệt bốn nguồn

1. **Flutter source chính, nằm ngoài root:** `D:/DA_KT_NC/feeder_demo/`. Đã harden offline, `WEB_FINAL_PASS=YES`, frozen; chỉ sửa khi có yêu cầu mới. Artifact cuối local: `D:/for_cat/WEB_FINAL_20261027/web_real/` và `web_mock/`.
2. **Windows root `D:/for_cat/jetson/` và `esp32/` là checkout cũ**, không đầy đủ integration/firmware đang dùng ở checkpoint sau. `D:/for_cat` và Flutter source không có Git metadata tại lần cleanup; không suy đây là bản Git sạch hay đè remote bằng cả cây này.
3. **Bản tham chiếu integration 27/10:** `D:/for_cat/FULL_HARDWARE_INTEGRATION_20261027/payload/` chứa local copy backend, bridge, config và tests; `.../guard_tuning/esp32/` là firmware source 4 ultrasonic/guard. Đây là snapshot/release work, không tự coi là một checkout Jetson hoàn chỉnh. Đối chiếu hashes/evidence trước khi dùng.
4. **Jetson runtime thực tế theo checkpoint:** `/home/toan/for_cat/` là repo tách biệt, có state chưa commit; lần quan sát gần nhất branch `main`, HEAD `dff667d13ac0cff78a494ab33070c1e9cf583f3f`, 36 staged files/index hash trong `FULL_HARDWARE_INTEGRATION_20261027/preflight.json`. Đây là **giá trị lịch sử**, không phải trạng thái live hiện tại. Không reset/clean/đè staged work hoặc SQLite.

`WEB_FINAL_20261027/result.json` ghi analyze +67 Flutter tests +2 web builds PASS; `CLEANUP_EXECUTED_20261027.md` ghi `CLEANUP_PASS=YES`. Hai kết quả là phần mềm/offline, không là physical PASS. Snapshot config/docs cũ có thể chứa AI identity/RTC/pins khác và đã bị authority ở trên hoặc checkpoint 27/10 thay thế.

**Đọc ký hiệu:** loại `SOURCE/RUNTIME/MODEL/DATA/TEST/TOOLING/GENERATED/EVIDENCE/RELEASE/DOCUMENTATION`; quan trọng `CORE/SUPPORT/GENERATED-REGENERATABLE/HISTORICAL-EVIDENCE`; regenerate `YES/NO/PARTIAL` theo dữ liệu và bằng chứng, không hàm ý được phép xóa.

## 2. Toàn bộ item trực tiếp dưới `D:/for_cat`

**Đếm:** 61 item có sẵn trước khi tạo tài liệu + chính tài liệu này = **62 top-level items**. Mỗi mục ghi lần lượt **vai trò/chứa gì; key; dùng bởi; loại; quan trọng; regenerate**.

### `.checks/`
- Vai trò/chứa: log kiểm thử/build host; key `summary.json`, `python-tests.log`, `firmware-builds.log`; dùng bởi Windows test/evidence. Loại GENERATED/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL** bằng `scripts/run_checks.ps1` nhưng kết quả có timestamp/môi trường khác.
### `.deploy/`
- Vai trò/chứa: bundle firmware diagnostic đóng gói trước đây; key `diag_hx711_20261009T033715Z/`, `diag_i2c_20261009T030915Z/`; dùng bởi deployment/evidence. Loại RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL** từ profile/source tương ứng, không coi compile là physical PASS.
### `.env.example`
- Vai trò/chứa: ví dụ biến môi trường; key chính file này; dùng bởi backend/tooling. Loại SOURCE/TOOLING; quan trọng SUPPORT; regenerate **NO** từ build.
### `.gitignore`
- Vai trò/chứa: ignore rules; key chính file này; dùng bởi development/tooling. Loại SOURCE/TOOLING; quan trọng SUPPORT; regenerate **NO**.
### `.native-build/`
- Vai trò/chứa: host binary test native; key `native_drivers.exe`, `native_safety.exe`, `*_strict.exe`; dùng bởi Windows C++ tests. Loại GENERATED/TEST; quan trọng GENERATED-REGENERATABLE; regenerate **YES** bằng các script build/check tương ứng. **Không phải** thư mục `.native-build` trên Jetson.
### `.release/`
- Vai trò/chứa: manifests và quality evidence; key `release_manifest.json`, `firmware_manifest.json`, `quality_summary.json`; dùng bởi release audit. Loại GENERATED/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL** qua `scripts/make_release_manifest.py` và quality scripts; không tái tạo chứng cứ lịch sử y hệt.
### `.tools-venv/`
- Vai trò/chứa: Python tool environment/PlatformIO; key `Scripts/pio.exe`; dùng bởi Windows firmware build/tooling. Loại TOOLING; quan trọng SUPPORT; regenerate **PARTIAL** theo `docs/REPRODUCIBLE_ENVIRONMENT.md`, có thể cần package cache/network.
### `.tools-zig/`
- Vai trò/chứa: compiler/toolchain local; key thư mục công cụ Zig; dùng bởi Windows C++ tests. Loại TOOLING; quan trọng SUPPORT; regenerate **PARTIAL** qua setup/toolchain tương ứng.
### `.venv-ai/`
- Vai trò/chứa: Python environment phục vụ tooling AI; key `Scripts/`, `Lib/site-packages/`; dùng bởi Windows AI tooling. Loại TOOLING/RUNTIME; quan trọng SUPPORT; regenerate **PARTIAL** từ environment/dependencies đã pin, không thay model.
### `.venv/`
- Vai trò/chứa: Python environment cho host/test; key `Scripts/python.exe`, `Lib/site-packages/`; dùng bởi Windows development/test. Loại TOOLING/RUNTIME; quan trọng SUPPORT; regenerate **PARTIAL** với `scripts/setup_dev_windows.ps1` và requirements.
### `ai/`
- Vai trò/chứa: AI data/experiments/tooling ngoài detector C++ production; key `dataset.py`, `training.py`, `datasets/`, `runs/`, `registry/`, `tests/`; dùng bởi Windows AI/data/test. Loại SOURCE/DATA/MODEL/TEST; quan trọng SUPPORT; regenerate **PARTIAL** cho code outputs, **NO** cho dữ liệu thật/provenance.
### `BAO_CAO_TIEN_DO_20261026.md`
- Vai trò/chứa: báo cáo REAL/preview trước worker; key file này; dùng bởi handoff/evidence. Loại DOCUMENTATION/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **NO** như bằng chứng. Dòng “chưa worker” là cũ, bị `SCHEDULED_WORKER_20261026/` thay thế.
### `BUTTON_GPIO21_BRINGUP_20261023/`
- Vai trò/chứa: diagnostic button, app-only flash/boot evidence; key `deploy/deploy_manifest.json`, `physical_flash/stages.json`, `VALIDATION.md`; dùng bởi ESP32/evidence. Loại EVIDENCE/RELEASE; quan trọng HISTORICAL/EVIDENCE; regenerate **NO** cho physical evidence.
### `BUTTON_LATENCY_FIX_20261025/`
- Vai trò/chứa: source delta/manifest cho button latency; key `original/`, `payload/`, `review.diff`, `manifest.json`; dùng bởi bridge/evidence. Loại SOURCE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, không tái tạo lịch sử.
### `CLEANUP_EXECUTED_20261027.md`
- Vai trò/chứa: audit cleanup và verification sau xóa; key chính file; dùng bởi Windows handoff. Loại DOCUMENTATION/EVIDENCE; quan trọng SUPPORT; regenerate **NO** cho số liệu đã thực hiện; kết luận `CLEANUP_PASS=YES`.
### `CLOSED_LOOP_DISPENSE_20261022_PREP_V2/`
- Vai trò/chứa: chuẩn bị closed-loop bench qua fake I/O, kèm firmware/source snapshot; key `CLOSED_LOOP_DISPENSE_BRINGUP.md`, `firmware.bin`, `source_snapshot/`, `verification_NOT_PHYSICAL_PASS.json`; dùng bởi ESP32/test/evidence. Loại SOURCE/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, không PHYSICAL_PASS.
### `CLOSED_LOOP_DISPENSE_20261022_PREP/`
- Vai trò/chứa: bundle bench đầu tiên; key `deploy_manifest.json`, `firmware.bin`, `physical_trial_TEMPLATE.md`; dùng bởi ESP32/evidence. Loại RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; template không là thử thật.
### `CURRENT_HARDWARE_DIAGNOSTIC_20261022/`
- Vai trò/chứa: diagnostic wired-sensor checkpoint trước; key `source_snapshot/esp32/`, `deploy/`, `physical_runs/`, `CURRENT_HARDWARE_DIAGNOSTIC.md`; dùng bởi ESP32/evidence. Loại SOURCE/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, ảnh/log thực không tái tạo.
### `deploy/`
- Vai trò/chứa: deployment templates gốc Windows; key `systemd/forr-cat.service`; dùng bởi Jetson deployment. Loại SOURCE/TOOLING; quan trọng SUPPORT; regenerate **NO** như source. Unit `for-cat-*` checkpoint mới nằm dưới `OFFLINE_REVIEW_20261024/project/deploy/systemd/`, không phải thư mục root này.
### `DISPENSE_BENCH_PREP_20261022_INITIAL/`
- Vai trò/chứa: firmware bench sơ khởi; key `firmware.bin`, `deploy_manifest.json`; dùng bởi ESP32/evidence. Loại RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, không flash tùy tiện.
### `docs/`
- Vai trò/chứa: tài liệu kiến trúc, giao thức, bringup và handoff; key `PROJECT_STATUS_20261026.md`, `NEXT_PHYSICAL_SESSION.md`, `ARCHITECTURE_OVERVIEW.md`, `UART_PROTOCOL.md`; dùng bởi mọi component/development. Loại DOCUMENTATION; quan trọng CORE; regenerate **NO**. Nhiều trang cũ được giữ chronology; kiểm ngày và banner.
### `ESP32_S3_HANDOFF_20261017/`
- Vai trò/chứa: handoff S3 giai đoạn17/10; key `source.zip`, `deploy/`, `handoff_manifest.json`, `SUPERSEDED.md`; dùng bởi ESP32/evidence. Loại RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, đã superseded.
### `ESP32_S3_HANDOFF_20261018_V2/`
- Vai trò/chứa: handoff S3 v2; key `source.zip`, `firmware_increment_from_v1.patch`, `deploy/`, `checks/`; dùng bởi ESP32/test/evidence. Loại RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; không là bản hardware 27/10.
### `ESP32_S3_HANDOFF_20261021_SENSOR_ONLY/`
- Vai trò/chứa: sensor-only prep; key `source_snapshot/`, `deploy_hx711/`, `checks_final/`, `physical_report_NOT_TESTED.json`; dùng bởi ESP32/evidence. Loại SOURCE/TEST/RELEASE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; physical report NOT_TESTED.
### `esp32/`
- Vai trò/chứa: source firmware gốc/legacy Windows, không tự đồng nhất bản flashed hiện tại; key `platformio.ini`, `src/diagnostics.cpp`, `include/m4/`, `test/`, `.pio/`; dùng bởi ESP32/build/native test. Loại SOURCE/TEST/GENERATED; quan trọng CORE đối với source gốc, HISTORICAL với pin map; regenerate **PARTIAL**: `.pio` outputs build lại, source không.
### `evidence/`
- Vai trò/chứa: layout evidence tại Windows; key `README.md`, `hx711/`, `esp32/`, `jetson/`, `servo/`, `pump/`, `webcam/`; dùng bởi physical/evidence. Loại EVIDENCE; quan trọng CORE; regenerate **NO** cho dữ liệu thực. Evidence phiên 27/10 còn ở đường dẫn Jetson tham chiếu trong báo cáo.
### `FEED_NOW_DRY_RUN_20261025/`
- Vai trò/chứa: checkpoint request cho ăn DRY RUN; key `payload/`, `original/`, `manifest.json`, `review.diff`; dùng bởi backend/bridge/web và evidence. Loại SOURCE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, không là physical feed.
### `FLUTTER_REAL_INTEGRATION_20261025/`
- Vai trò/chứa: migration Flutter REAL và ảnh/API evidence; key `backend_payload/`, `web_real_v2/`, `flutter_browser_verified.json`, `sensor_realtime_20261025.json`, screenshots; dùng bởi Flutter/backend/evidence. Loại SOURCE/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; physical sensor claims phải đọc report scope.
### `FRONTEND_AUDIT_20261025/`
- Vai trò/chứa: audit frontend ban đầu; key `audit.json`, `INTEGRATION_PLAN.md`, `source_copy/`, `dart_analyze.log`; dùng bởi Flutter development/evidence. Loại DOCUMENTATION/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**.
### `FRONTEND_USER_APP_OFFLINE_20261026/`
- Vai trò/chứa: redesign user view offline và workspace test tổng hợp; key `BAO_CAO_FRONTEND_OFFLINE.md`, `frontend_original/`, `source_final/`, `verification/`, `screenshots/`, `web_real/`, `web_mock/`; dùng bởi Flutter/test/evidence. Loại SOURCE/TEST/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**. `verification/` không phải source deploy.
### `FULL_HARDWARE_INTEGRATION_20261027/`
- Vai trò/chứa: integration4 ultrasonic, host/source snapshots, flash/sensor/HX session tools và evidence local; key `payload/jetson/{app,device}/`, `payload/config/hardware_current.json`, `firmware/esp32/`, `guard_tuning/esp32/`, `observe_ultrasonic.py`, `VERIFY5_BLOCKER_20261027.md`; dùng bởi Jetson/ESP32/Flutter/test/evidence. Loại SOURCE/TEST/RELEASE/EVIDENCE; quan trọng CORE + HISTORICAL/EVIDENCE; regenerate **PARTIAL**, raw/physical evidence **NO**. `REPORT.md`/`FAST_TRACK_PROGRESS.md` ghi thời điểm cũ; đọc `audit_verify5_failure_result.json` và blocker mới hơn cho HX.
### `HX711_CALIBRATION_20261026/`
- Vai trò/chứa: host multi-point software/metadata và bằng chứng readiness ban đầu; key `payload/jetson/app/hx711_calibration.py`, `hx711_view.py`, `tools/hx711_calibration.py`, `BAO_CAO_HX711_SOFTWARE_READY.md`; dùng bởi backend/HX/tooling/evidence. Loại SOURCE/TEST/EVIDENCE; quan trọng CORE reference + HISTORICAL/EVIDENCE; regenerate **PARTIAL**. Report “waiting TEST0” là thời điểm sớm, không ghi đè kết quả 27/10.
### `HX711_DEMO_ESTIMATE_20261026/`
- Vai trò/chứa: estimate demo dang dở; key `payload/`, `originals/`, `README.md`; dùng bởi HX development/evidence. Loại SOURCE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; **chưa test/deploy/approve**, không overlay lên production.
### `HX711_PHYSICAL_BRINGUP_20261021_PREP/`
- Vai trò/chứa: diagnostic HX bringup preparation; key `HX711_LOADCELL_BRINGUP.md`, `deploy_hx711/`, `physical_status_NOT_VERIFIED.json`; dùng bởi ESP32/evidence. Loại RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; preparation không là gram PASS.
### `jetson/`
- Vai trò/chứa: backend/tool/test cũ của Windows root; key `app/main.py`, `app/api/routes.py`, `app/storage/`, `tools/run_api.py`, `tests/`, `data/events.db`; dùng bởi Windows/backend/test. Loại SOURCE/TEST/DATA; quan trọng CORE legacy + SUPPORT; regenerate **PARTIAL** cho venv/build, **NO** cho DB. Không xem file DB local là canonical Jetson DB.
### `models_final/`
- Vai trò/chứa: model experiment exports riêng; key `behavior_v1.{pt,onnx}`, `cat_detector_v1.{pt,onnx}`, `food_state_v1.{pt,onnx}`; dùng bởi AI research/tooling. Loại MODEL; quan trọng SUPPORT; regenerate **PARTIAL/UNKNOWN** theo training provenance; không tự thay production engine.
### `NETWORK_BOOT_RECOVERY_20261026/`
- Vai trò/chứa: LAN/service recovery và monitor evidence; key `OVERNIGHT_REVIEW.json`, `windows_http_verified.json`, `payload/`; dùng bởi Jetson/network/evidence. Loại EVIDENCE/DOCUMENTATION; quan trọng HISTORICAL/EVIDENCE; regenerate **NO** cho quan sát. Monitor `INCOMPLETE_CAPTURE_NO_FINAL_FILE`, không phải8h PASS.
### `OFFLINE_RC_20261026/`
- Vai trò/chứa: offline RC, source snapshot, demo/build/test manifests; key `regression_result.json`, `release_manifest_sha256.json`, `offline_release_candidate_20261026.zip`, `web_real/`, `web_mock/`; dùng bởi Flutter/demo/evidence. Loại RELEASE/TEST/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; web final mới hơn ở `WEB_FINAL_20261027/`.
### `OFFLINE_RELEASE_20261026.md`
- Vai trò/chứa: tổng kết freeze offline; key file này; dùng bởi handoff. Loại DOCUMENTATION/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **NO** như record. `OFFLINE RELEASE CANDIDATE READY` không là physical release.
### `OFFLINE_REVIEW_20261024/`
- Vai trò/chứa: local project snapshot/handoff và protected AI detector source reference; key `project/jetson/ai/cat_dog_trt.cpp`, `project/jetson/device/`, `DEPLOYED_SOURCE_BASELINE.json`, `checks/`; dùng bởi Jetson C++/test/evidence. Loại SOURCE/TEST/EVIDENCE; quan trọng CORE reference + HISTORICAL/EVIDENCE; regenerate **PARTIAL**; không bọc toàn snapshot thành production deployment.
### `OVERNIGHT_MEAL_PLAN_20261025/`
- Vai trò/chứa: Meal Plan CRUD/preview checkpoint; key `payload/`, `backend_manifest.json`, `web_real_meal_plans/`, `meal_browser_verified.json`; dùng bởi backend/Flutter/evidence. Loại SOURCE/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; worker milestone sau hơn.
### `PHYSICAL_RESUME_20261027/`
- Vai trò/chứa: backup/baseline/deploy/sensor candidate của phiên resume đầu; key `BAO_CAO_RESUME.md`, `preflight_backup_result.json`, `firmware_candidate/`, `screenshots/`, `remote_audit/`; dùng bởi Jetson/ESP32/evidence. Loại SOURCE/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; trạng thái #2/RTC ban đầu trong report đã bị owner wiring và integration tiếp theo thay thế.
### `PROJECT_FOLDER_MAP_AND_HANDOFF_20261027.md`
- Vai trò/chứa: chính bản map đang đọc; key file này; dùng bởi kỹ sư tiếp quản. Loại DOCUMENTATION; quan trọng SUPPORT; regenerate **PARTIAL** bằng kiểm kê read-only mới; status chỉ là snapshot.
### `pytest.ini`
- Vai trò/chứa: cấu hình pytest root; key chính file; dùng bởi Python test. Loại TEST/TOOLING; quan trọng SUPPORT; regenerate **NO**.
### `README.md`
- Vai trò/chứa: giới thiệu/build/workflow gốc; key chính file; dùng bởi development/handoff. Loại DOCUMENTATION; quan trọng SUPPORT; regenerate **NO**; đối chiếu checkpoints mới hơn cho hardware/runtime.
### `requirements-dev.txt`
- Vai trò/chứa: dependencies development; key chính file; dùng bởi Windows tooling/test. Loại TOOLING; quan trọng SUPPORT; regenerate **NO** như bản khai báo.
### `requirements-host-snapshot.txt`
- Vai trò/chứa: snapshot dependencies host; key chính file; dùng bởi environment reproduction. Loại TOOLING/EVIDENCE; quan trọng SUPPORT; regenerate **PARTIAL** bằng snapshot môi trường, không chắc cùng phiên bản.
### `requirements-quality.txt`
- Vai trò/chứa: tooling quality/static checks; key chính file; dùng bởi Windows CI/tooling. Loại TOOLING; quan trọng SUPPORT; regenerate **NO** như source.
### `ruff.toml`
- Vai trò/chứa: quy tắc lint; key chính file; dùng bởi Python quality tools. Loại TOOLING; quan trọng SUPPORT; regenerate **NO**.
### `runs/`
- Vai trò/chứa: outputs các thí nghiệm; key `behavior_pilot_20261021_trial01/`, `detect/`; dùng bởi AI development/evidence. Loại DATA/MODEL/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL/UNKNOWN**, không suy số liệu production.
### `SCHEDULED_WORKER_20261026/`
- Vai trò/chứa: worker/Meal Plan release, live dry-run evidence; key `payload/jetson/app/scheduled_worker.py`, `BAO_CAO_SCHEDULED_WORKER.md`, `live_worker_verified.json`, `web_regression_source/`; dùng bởi backend/Flutter/test/evidence. Loại SOURCE/TEST/EVIDENCE/RELEASE; quan trọng CORE reference + HISTORICAL/EVIDENCE; regenerate **PARTIAL**, live proof **NO**. Worker tự tạo request DRY_RUN_PASS/restart dedupe, không physical dispense.
### `scripts/`
- Vai trò/chứa: setup/build/flash plan/release/test gốc Windows; key `run_checks.ps1`, `setup_dev_windows.ps1`, `prepare_esp32_deploy.py`, `check_release.py`; dùng bởi Windows/Jetson/tooling/test. Loại SOURCE/TOOLING; quan trọng SUPPORT; regenerate **NO** cho source. Một số scripts integration mới chỉ nằm trong dated payload.
### `SERVO_BENCH_HANDOFF_20261021_PREP_V2/`
- Vai trò/chứa: servo bench prep v2; key `SERVO_BRINGUP.md`, `firmware.bin`, `source_snapshot/`, `verification_NOT_PHYSICAL_PASS.json`; dùng bởi ESP32/evidence. Loại SOURCE/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, không physical PASS.
### `SERVO_BENCH_HANDOFF_20261021_PREP_V3/`
- Vai trò/chứa: servo bench prep v3; key `SERVO_BRINGUP.md`, `host_checks/`, `source_snapshot/`, `verification_NOT_PHYSICAL_PASS.json`; dùng bởi ESP32/evidence. Loại SOURCE/TEST/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**.
### `SERVO_BENCH_HANDOFF_20261021_PREP_V4/`
- Vai trò/chứa: servo bench prep v4; key `SERVO_BRINGUP.md`, `deploy_manifest.json`, `source_snapshot/`, `verification_NOT_PHYSICAL_PASS.json`; dùng bởi ESP32/evidence. Loại SOURCE/RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**, chưa chứng nhận servo.
### `SERVO_BENCH_HANDOFF_20261021_PREP/`
- Vai trò/chứa: image servo bench sơ khởi; key `firmware.bin`, `firmware.factory.bin`, `deploy_manifest.json`; dùng bởi ESP32/evidence. Loại RELEASE/EVIDENCE; quan trọng HISTORICAL/EVIDENCE; regenerate **PARTIAL**; factory image không được flash tùy tiện.
### `WEB_FINAL_20261027/`
- Vai trò/chứa: final hardening offline web release; key `result.json`, `web_real/`, `web_mock/`, `analyze.log`, `tests.log`, `verify.py`; dùng bởi Flutter/release. Loại RELEASE/TEST/EVIDENCE; quan trọng CORE release; regenerate **PARTIAL** từ Flutter source và toolchain, không xóa evidence. `WEB_FINAL_PASS=YES`, 67 tests, build REAL/MOCK PASS; không chứng minh deploy lên Jetson.
### `yolov8n_320.onnx`
- Vai trò/chứa: ONNX nano320 export; key chính file; dùng bởi AI/tooling. Loại MODEL; quan trọng SUPPORT; regenerate **PARTIAL** nếu có nguồn/export environment tương ứng; không có bằng chứng từ map này rằng file này tự nó là engine production.
### `yolov8n_416.onnx`
- Vai trò/chứa: ONNX nano416 alternative; key file; dùng bởi AI experiment. Loại MODEL; quan trọng SUPPORT; regenerate **PARTIAL/UNKNOWN**; không phải đường engine320 hardcoded.
### `yolov8n.pt`
- Vai trò/chứa: PyTorch nano weights; key file; dùng bởi AI experiment/export. Loại MODEL; quan trọng SUPPORT; regenerate **PARTIAL/UNKNOWN**; không khẳng định self-trained.
### `yolov8s.onnx`
- Vai trò/chứa: ONNX small-model alternative; key file; dùng bởi AI experiment. Loại MODEL; quan trọng SUPPORT; regenerate **PARTIAL/UNKNOWN**; không phải production engine hardcoded.
### `yolov8s.pt`
- Vai trò/chứa: PyTorch small-model weights; key file; dùng bởi AI experiment/export. Loại MODEL; quan trọng SUPPORT; regenerate **PARTIAL/UNKNOWN**; không khẳng định model tự train.

## 3. Đi sâu core — path thực tế và ranh giới

### 3.1 AI runtime và publication

| Vai trò | Path xác minh được / ý nghĩa |
|---|---|
| Detector reference | `D:/for_cat/OFFLINE_REVIEW_20261024/project/jetson/ai/cat_dog_trt.cpp` — C++ OpenCV/TensorRT, preprocessing/decoder/NMS cùng file; snapshot tham chiếu, **không tự coi byte-identical current remote**. Một snapshot khác: `ESP32_S3_HANDOFF_20261021_SENSOR_ONLY/source_snapshot/jetson/ai/cat_dog_trt.cpp`. |
| TensorRT/latency | `OFFLINE_REVIEW_20261024/project/jetson/ai/latency_runtime.h`, `latency_support.h`, `test_detector_regression.cpp`, `test_latency_support.cpp`; đọc snapshot trước khi thay. |
| Input/class authority | Detector reference ghi input320×320, CAT class15, DOG class16, confidence0.35, NMS0.45; không suy lớp identity. `NONE` là không có detection chấp nhận; lỗi/stale phải được state layer biểu diễn phù hợp. |
| Engine production reference | Code ghi `/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine`; report/`PHYSICAL_RESUME_20261027/preflight_backup_result.json` ghi SHA `48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb`. **Không có `.engine` trong cây Windows `D:/for_cat` đã kiểm kê**; hiện trạng remote cần verify khi có Jetson. |
| Capture process/tap | `FULL_HARDWARE_INTEGRATION_20261027/payload/scripts/run_existing_ai.sh` chạy detector `/home/toan/for_cat/jetson/ai/cat_dog_trt` rồi pipe tới `.native-build/esp32/ai_state_tap`; local tap source `.../payload/jetson/device/ai_state_tap.cpp`. Không tạo camera reader thứ hai. |
| State reader | `FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/app/ai_state.py` đọc state thụ động; `.../app/system_state.py` đưa vào SystemState. `UNKNOWN/STALE` khác `NONE`. |
| Tooling/data | `ai/capture.py`, `dataset.py`, `label_schema.py`, `evaluation.py`, `training.py`, `interchange.py`, `public_data.py`, `sampling.py`, `session.py`, `scripts/`, `tests/`; không phải detector C++ production. |
| Experimental/legacy | `ai/server_training_bundle/{cat_detector,behavior,food_state,provenance}/`, `ai/bowl_detector_server/`, `ai/runs/`, `ai/registry/candidates.json`; đây là research/training data riêng. Tài liệu cũ có ý tưởng identity/behavior, **ngoài scope AI production hiện tại**. |

Không có file `D:/for_cat/jetson/ai/cat_dog_trt.cpp` trong checkout root hiện tại; dùng snapshot nêu trên để tham khảo. Không xác nhận production model tự huấn luyện hay chính xác/FPS từ tên file.

### 3.2 Jetson backend / bridge / scheduler / SQLite

**Windows legacy:** `jetson/tools/run_api.py` → `jetson/app/main.py`; `jetson/app/api/routes.py`; `jetson/app/{storage,serial_link,simulator,behavior,vision,camera,ai}/`; `jetson/tests/`. Local `jetson/data/events.db` tồn tại nhưng không phải database Jetson canonical.

**Snapshot integration 27/10:** prefix `D:/for_cat/FULL_HARDWARE_INTEGRATION_20261027/payload/`:

- `jetson/tools/run_api.py` và `jetson/app/main.py`: API entry/app composition; `app/api/{system_routes,esp32_routes,meal_plan_routes,hx711_routes,routes}.py`: REST/WS endpoints và compatibility.
- `jetson/device/esp32_bridge.cpp`: một serial owner C++ RX-only; `telemetry.h` và `ultrasonic_telemetry.h`: bounded parser/4-channel normalization; `ai_state_tap.cpp`: AI state tap; `feed_policy.h`: Feed Arbiter; `decision_logic.h`: AUTO_CAT/temporal/water dry-run logic. `test_{policy,decision,ultrasonic,dispense_35}.cpp` là tests, không physical outputs.
- `jetson/app/device_state.py`: đọc bridge state từ SQLite; `system_state.py`: REAL/UNKNOWN SystemState; `ultrasonic_state.py`: 4 channel/age/legacy mapping; `hx711_view.py`: host measurement view; `hx711_calibration.py`: session/fit/verify; `jetson/tools/hx711_calibration.py`: CLI vật lý khi được phép.
- `jetson/app/meal_plans.py`, `scheduled_worker.py`, `schedule_gate.py`, `dry_run_requests.py`: plan CRUD/time/dedupe/atomic occurrence+inbox; worker trong API service, không là servo process. Test chính `jetson/tests/{test_meal_plans,test_scheduled_worker,test_dry_run_requests,test_ultrasonic_state,test_system_state}.py` trong cùng payload.
- `jetson/app/storage/`: repositories/SQLite policies; `jetson/app/web/`: diagnostics/preview web legacy; `scripts/run_existing_ai.sh`, `scripts/build_esp32_bridge.sh`: source trong payload nếu có. Không coi mock adapter nội bộ là REAL→MOCK fallback.

Theo checkpoint deployment, DB canonical Jetson là `/home/toan/for_cat/jetson/data/events.db` (WAL), cùng bridge/AI/worker; đây là **remote reference từ report**, không được xác minh live trong lần tạo map. Không copy `D:/for_cat/jetson/data/events.db` đè DB thật. `FULL_HARDWARE_INTEGRATION_20261027/backend_before.tar.gz` và `preflight.json` là backup/evidence, không phải live database.

### 3.3 ESP32 firmware, pin authority, UART

- Legacy Windows: `esp32/platformio.ini`, `esp32/src/{main,diagnostics}.cpp`, `esp32/include/{board_config,pins,safety_logic,uart_v1}.h`, `esp32/include/m4/{hx711,ultrasonic,oled,accessories,calibration,calibration_record,actuator_interfaces}.h`, `esp32/test/`. Đây **không phải** source pin map4-channel mới nhất.
- Snapshot profile mới: `FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/platformio.ini` profile `diag_four_ultrasonic`; `src/diagnostics.cpp`, `include/m4/quad_level_sampler.h`, `candidate_sensor_pins.h`, `arduino_io.h`, `ultrasonic.h`, `hx711.h`, `oled.h`, `accessories.h`; `test/{quad_sampler,quad_firmware_loop,quad_bridge_compat}.cpp`. Guard source là release đã chuẩn bị; flash/runtime history cần đối chiếu evidence, không dựa comment “unflashed” cũ.
- Các module bench riêng `guard_tuning/esp32/include/m4/{servo_bench,dispense_bench,pump_bench,ledc_servo}.h`, `src/{servo_bench,dispense_bench,pump_bench}.cpp` là **bench code**, không phải quyền thực thi production; không sử dụng để suy physical PASS.
- Current wiring declaration local `FULL_HARDWARE_INTEGRATION_20261027/payload/config/hardware_current.json`: HX4/5; servo6; pump7; OLED8/9; JSN2 echo10; PIR11; HC1 12/13; JSN1 14/15; HC2 16/17; JSN2 18/10; button21; RTC removed. Roles HC1 CAT_APPROACH, JSN1 WATER_LEVEL, #2 TBD. Snapshot trước physical closeout có trạng thái test cũ; khi online đọc canonical remote config mới nhất.
- Protocol `docs/UART_PROTOCOL.md`, `docs/UART_SENSOR_STATUS_EXTENSION_PLAN.md`, source `esp32/include/uart_v1.h`; integration diagnostic còn dùng bounded ASCII JSON qua C++ `telemetry.h`. Không nhầm protocol binary CRC và diagnostic telemetry version.

### 3.4 Flutter Web / API client

Source thực tế `D:/DA_KT_NC/feeder_demo/`:

- `lib/main.dart`: app shell/theme, bottom navigation 5 tab, Settings page; `lib/user_pages.dart`: Tổng quan, Cho ăn, Lịch sử.
- `lib/meal_plan_panel.dart`, `lib/meal_plans.dart`: Meal Plan controls/editor/typed schedule. `lib/diagnostics_page.dart`, `lib/diagnostic_models.dart`: System, HX, 4 ultrasonic, AUTO_CAT.
- `lib/feeder_state.dart`, `lib/status_model.dart`, `lib/history_model.dart`, `lib/ui_widgets.dart`: typed state/status/history dedupe/UI primitives.
- `lib/feeder_backend.dart`, `lib/real_backend.dart`: REST client và WebSocket/reconnect/stale, pending/manual, plans/history. `lib/backend_factory.dart` mặc định REAL, MOCK chỉ explicit compile define; `lib/mock_backend.dart` là fixture, không auto fallback. `pending_store*.dart` lưu request identity trên web/other targets.
- `test/{user_app_offline_test,ultrasonic_real_test,real_backend_test,meal_plans_test,scheduled_worker_test,feeder_demo_test}.dart` và các test khác: widget/state/regression; `web/`, `assets/fonts/`, `pubspec.yaml`, `pubspec.lock` là web assets/dependencies.
- Local release `D:/for_cat/WEB_FINAL_20261027/{web_real,web_mock}/`, `result.json`: analyze/67 tests/build PASS. Theo report cũ Jetson từng serve `.native-build/flutter/four_ultrasonic_20261027_r2`; **không suy bản WEB_FINAL đã deploy**. `40-flutter-real.conf` remote là nguồn cấu hình khi kiểm live, không có file đó ở root Windows.

### 3.5 Deployment, test, evidence

- Root template chỉ `deploy/systemd/forr-cat.service`; snapshot unit `OFFLINE_REVIEW_20261024/project/deploy/systemd/{for-cat-api,for-cat-esp32-bridge,for-cat-ai}.service`. `SCHEDULED_WORKER_20261026/payload/deploy/systemd/50-scheduled-dry-run.conf` là checkpoint worker. Unit/drop-in **thực tế trên Jetson** theo report ở `~/.config/systemd/user/`; không xác minh filesystem remote trong map.
- Windows build/release tools `scripts/`; integration copies `FULL_HARDWARE_INTEGRATION_20261027/{build_local,build_guard_release,test_remote,post_deploy_checks,observe_ultrasonic,flash_app_only}.py`; các script physical/flash chỉ dùng khi có quyền và hardware/nguồn thực.
- Test locations: `jetson/tests/` legacy, `FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/tests/` integration; `esp32/test/` legacy và `FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/test/`; `ai/tests/`; Flutter `D:/DA_KT_NC/feeder_demo/test/`.
- Evidence chính local: `FULL_HARDWARE_INTEGRATION_20261027/{REPORT.md,FAST_TRACK_PROGRESS.md,audit_verify5_failure_result.json,VERIFY5_BLOCKER_20261027.md}`, `SCHEDULED_WORKER_20261026/live_worker_verified.json`, `WEB_FINAL_20261027/result.json`. Physical remote path theo report: `/home/toan/for_cat/evidence/full_hardware_integration_20261027_20261027T022005862030Z/`; không được xóa.

## 4. Model inventory chi tiết

| File | Format | Vai trò/giới hạn theo file/references |
|---|---|---|
| `yolov8n.pt` | PyTorch | Nano weights local cho tooling/export; không chứng minh self-trained hay đang được detector production nạp trực tiếp. |
| `yolov8n_320.onnx` | ONNX | Export nano input320 local; có thể là trung gian/đối chiếu, nhưng không chứng minh byte-to-engine provenance. |
| `yolov8n_416.onnx` | ONNX | Export nano416 alternative; detector production reference đang hardcode320. |
| `yolov8s.pt` | PyTorch | Small variant local, alternative; không là engine production reference. |
| `yolov8s.onnx` | ONNX | Export small alternative; không là engine production reference. |
| `models_final/cat_detector_v1.pt`, `cat_detector_v1.onnx` | PyTorch/ONNX | Cặp cat detector experiment/export; không có bằng chứng trong detector C++ rằng đang được production nạp. |
| `models_final/behavior_v1.pt`, `behavior_v1.onnx` | PyTorch/ONNX | Cặp behavior experiment/export, không thuộc CAT/DOG/NONE runtime authority. |
| `models_final/food_state_v1.pt`, `food_state_v1.onnx` | PyTorch/ONNX | Cặp food-state experiment/export, không thuộc CAT/DOG/NONE runtime authority. |
| `/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine` | TensorRT engine trên Jetson | Đường dẫn production được `cat_dog_trt.cpp` reference; không tồn tại trong Windows tree đã kiểm kê. SHA checkpoint ghi ở mục3.1, chưa xác minh hiện trạng remote lần này. Không convert/rebuild. |

`ai/server_training_bundle/README.md`, `ai/registry/candidates.json`, `ai/runs/` chứa thông tin experiment cũ; không lấy đề xuất cũ làm production task hoặc suy tự huấn luyện từ tên artifact. `ai/datasets/README.md` mô tả mặc định empty nhưng cây datasets hiện có nhiều thư mục; không suy dữ liệu hiện tại trống chỉ từ README lịch sử.

## 5. Flow dự án theo path

### A. AI → intent → gate

```text
USB Camera /dev/video0
  -> Jetson detector C++/OpenCV: OFFLINE_REVIEW_20261024/project/jetson/ai/cat_dog_trt.cpp [snapshot]
  -> YOLOv8n TensorRT FP16: /home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine [remote reference]
  -> CAT / DOG / NONE; lỗi/stale -> UNKNOWN/STALE theo state layer
  -> passive C++ ai_state_tap.cpp -> SQLite -> app/ai_state.py -> app/system_state.py
  -> decision_logic.h AUTO_CAT evidence -> feed_policy.h Feed Arbiter -> safety gates
  -> FUTURE/BLOCKED: ESP32 sensor/actuator authority -> servo
```

Paths `ai_state_tap.cpp`, `decision_logic.h`, `feed_policy.h`, `ai_state.py`, `system_state.py` tương ứng `FULL_HARDWARE_INTEGRATION_20261027/payload/jetson/{device,app}/`. Gate hiện dry-run; đường chấm tới servo là thiết kế, không phải khẳng định actual dispense.

### B. Sensor → Flutter

```text
ESP32 sensors: FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/{src/diagnostics.cpp,include/m4/}
  -> USB Serial -> payload/jetson/device/esp32_bridge.cpp + telemetry.h + ultrasonic_telemetry.h
  -> canonical Jetson SQLite /home/toan/for_cat/jetson/data/events.db [remote reference]
  -> payload/jetson/app/{device_state.py,system_state.py,ultrasonic_state.py,hx711_view.py}
  -> payload/jetson/app/api/{system_routes.py,esp32_routes.py,meal_plan_routes.py,hx711_routes.py}
  -> REST + WebSocket -> D:/DA_KT_NC/feeder_demo/lib/{real_backend.dart,user_pages.dart,diagnostics_page.dart}
```

MANUAL/SCHEDULED/AUTO_CAT đều đi qua arbiter; Scheduled Worker trong API dùng cùng SQLite/occurrence identity. Mất dữ liệu = UNKNOWN/STALE/null, không tự đổi MOCK hoặc tạo actual0.

## 6. WHERE DO I EDIT?

**Quan trọng:** bảng chỉ chỉ đường **local đã xác minh** để đọc/soạn patch, không cấp quyền ghi trực tiếp/ghi đè trên Jetson. `payload` là dưới `D:/for_cat/FULL_HARDWARE_INTEGRATION_20261027/payload/`; `guard` là `D:/for_cat/FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/`; `flutter` là `D:/DA_KT_NC/feeder_demo/`. Trước sửa đối chiếu remote source/hashes/staged changes khi được phép.

| Muốn sửa | File/folder nên mở |
|---|---|
| CAT/DOG AI | `D:/for_cat/OFFLINE_REVIEW_20261024/project/jetson/ai/cat_dog_trt.cpp` (reference); runtime deploy remote cần đối chiếu trước |
| TensorRT parsing | Cùng `cat_dog_trt.cpp`; `.../latency_support.h`, `.../test_detector_regression.cpp` |
| AUTO_CAT logic | `payload/jetson/device/decision_logic.h`, `test_decision.cpp`; UI `flutter/lib/diagnostic_models.dart` |
| Feed Arbiter | `payload/jetson/device/feed_policy.h`, `esp32_bridge.cpp`, `test_policy.cpp` |
| Scheduled feeding | `payload/jetson/app/{scheduled_worker.py,meal_plans.py,schedule_gate.py,dry_run_requests.py}`, `api/meal_plan_routes.py`, tests tương ứng |
| API | `payload/jetson/app/main.py`, `api/{system_routes,esp32_routes,meal_plan_routes,hx711_routes,routes}.py` |
| SQLite/history | `payload/jetson/app/{device_state.py,dry_run_requests.py,scheduled_worker.py}`, `storage/`; Flutter `lib/{history_model,real_backend}.dart` |
| UART bridge | `payload/jetson/device/{esp32_bridge.cpp,telemetry.h,ultrasonic_telemetry.h}`, `payload/jetson/tests/test_esp32_bridge.py` |
| ESP32 sensors | `guard/src/diagnostics.cpp`, `guard/include/m4/{hx711,ultrasonic,oled,accessories}.h`, `candidate_sensor_pins.h` |
| Servo | `guard/include/m4/{actuator_interfaces,servo_bench,ledc_servo}.h`, `guard/src/servo_bench.cpp`; bench only, actual actuation blocked |
| Pump | `guard/include/m4/{actuator_interfaces,pump_bench}.h`, `guard/src/pump_bench.cpp`; bench only, actual actuation blocked |
| HX711 | `guard/include/m4/{hx711,calibration,calibration_record}.h`; `payload/jetson/app/{hx711_calibration,hx711_view}.py`, `payload/jetson/tools/hx711_calibration.py` |
| Ultrasonic | `guard/include/m4/{ultrasonic,quad_level_sampler,candidate_sensor_pins}.h`, `guard/src/diagnostics.cpp`; `payload/jetson/device/ultrasonic_telemetry.h`, `payload/jetson/app/ultrasonic_state.py` |
| Flutter dashboard | `flutter/lib/user_pages.dart`, `ui_widgets.dart`, `main.dart` |
| Meal plan UI | `flutter/lib/{meal_plan_panel,meal_plans}.dart` |
| Diagnostics UI | `flutter/lib/{diagnostics_page,diagnostic_models}.dart` |
| REAL/MOCK config | `flutter/lib/{backend_factory,real_backend,mock_backend}.dart` |

## CURRENT_PROJECT_HANDOFF

- **Đã hoàn thành:** REAL architecture và Manual/Scheduled DRY RUN; Meal Plan + Scheduled Worker với dedupe proof lịch sử; 4 ultrasonic có evidence ranging cơ bản và scheduler80ms đạt một cửa sổ theo kiểm thử trước, còn timeout JSN lẻ, không là soak/accuracy certificate. Flutter `WEB_FINAL_PASS=YES`; cleanup `CLEANUP_PASS=YES`.
- **Chờ physical:** HX711 gram calibration/verify/persistence chưa PASS; servo/pump/actual35g/AUTO physical chưa được chứng minh. Các proof cũ chỉ đúng scope và thời điểm của evidence.
- **Blocker gần nhất:** phiên `hxcal_e721ec976ad44342b4522a051ba6c9f1` có VERIFY5 candidate7.371g cho tải khai báo5g và VERIFY0 sau đó +2.258g; candidate chưa active. Owner sau đó báo có một vật ước lượng ~2.371g chạm/trên khay; chưa có bằng chứng đã lấy ra hoặc zero đã phục hồi. Không tự trừ số này, retare/activate/claim PASS. `FULL_HARDWARE_INTEGRATION_20261027/VERIFY5_BLOCKER_20261027.md` và `audit_verify5_failure_result.json` ghi evidence.
- **Khi có Jetson:** theo quyền phiên mới, kiểm kết nối/service/owner/safety và đọc state/evidence thật; kiểm vật ngoài ý muốn đã được nhấc khỏi khay rồi mới đo độc lập/đánh giá lại calibration. Giữ original failed points; servo/pump khóa.
- **Khi không có Jetson:** dùng bản map/release logs để đọc, chuẩn bị test/patch theo yêu cầu; không tuyên bố runtime/physical mới, không đổi model hoặc deploy snapshot tổng hợp.
