# Cleanup thực hiện — 27/10/2026

## Kết quả

**CLEANUP_PASS: YES**. Đã xóa **4.870 file**, tổng **697.256.979 bytes**.

| Thước đo | Bytes |
|---|---:|
| Dung lượng file trước cleanup | 8.152.608.080 |
| Dung lượng file sau cleanup, trước khi tạo report này | 7.455.351.101 |
| Reclaimed theo chênh lệch tổng kích thước file | **697.256.979** (~665 MiB) |

Đây là tổng **logical file size** từ filesystem traversal, không phải số block vật lý/thay đổi free-space trên ổ đĩa. Không đi theo symlink/reparse point. Flutter source chính nằm ngoài `D:/for_cat` tại `D:/DA_KT_NC/feeder_demo`; số liệu before/after chỉ tính `D:/for_cat`. Hai build kiểm thử được ghi vào thư mục temp ngoài repo, nên không làm tăng dung lượng repo. Report này được tạo sau phép đo.

## Đã kiểm tra trước khi xóa

- `git status --short --branch` tại `D:/for_cat` và Flutter source đều báo **not a git repository**. Không thể xác định staged/uncommitted bằng Git ở hai đường dẫn này; do đó giữ toàn bộ source, config, scripts, test, docs, model, evidence và release artifacts.
- Tìm reference trong scripts/docs/manifest: `esp32/.pio/build/*/firmware.bin` được dùng bởi deployment/release scripts; **giữ tất cả `.bin`**, cùng `.elf`, `.map`, source và manifest. Chỉ xóa `.o`, `.o.d`, `.a` trong các thư mục build đã kiểm kê; build system có thể tạo lại chúng.
- So sánh SHA256 các ZIP có cùng kích thước: **không phát hiện cặp ZIP byte-identical** trong phạm vi audit; không xóa ZIP/release chỉ vì tên hoặc ngày.
- Chỉ xóa `__pycache__` khi toàn bộ file bên trong là Python bytecode; không xóa thư mục có file bất ngờ. Không có trường hợp bất ngờ bị bỏ qua.
- 8 Chromium profiles được tạo bởi harness **offline loopback** của checkpoint frontend; Chrome không sử dụng các profile đó. Giữ nguyên screenshots, snapshots, browser reports và các profile có nguồn/giá trị chưa chắc chắn.

## Phân loại đã xóa

| Path / nhóm | Files | Bytes |
|---|---:|---:|
| `FRONTEND_USER_APP_OFFLINE_20261026/chromium_profile_1793017406912` |348|67.773.995|
| `.../chromium_profile_1793017746570` |352|67.941.594|
| `.../chromium_profile_1793017868965` |348|67.823.120|
| `.../chromium_profile_1793017972575` |348|67.867.688|
| `.../chromium_profile_1793018093266` |348|67.782.800|
| `.../chromium_profile_1793018147455` |348|67.824.871|
| `.../chromium_profile_1793018214953` |170|15.291.990|
| `.../chromium_profile_1793018282857` |352|67.938.748|
| `esp32/.pio/build/` — chỉ `.o`, `.o.d`, `.a` |1.152|143.342.066|
| `FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32/.pio/build/` — chỉ `.o`, `.o.d`, `.a` |134|16.827.272|
| `FULL_HARDWARE_INTEGRATION_20261027/firmware/esp32/.pio/build/` — chỉ `.o`, `.o.d`, `.a` |134|16.823.044|
| `PHYSICAL_RESUME_20261027/firmware_candidate/esp32/.pio/build/` — chỉ `.o`, `.o.d`, `.a` |67|8.396.644|
| `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, các `__pycache__` project |—|~21,92 MB|

Danh sách đầy đủ từng thư mục cache và số bytes/file được lưu tại `C:/Users/chito/AppData/Local/Temp/opencode/cleanup_execution_20261027.json`. Kết quả kiểm kê sau cleanup: `C:/Users/chito/AppData/Local/Temp/opencode/cleanup_inventory_20261027.json`.

## Chủ động giữ

Toàn bộ source/test/config/build scripts/docs, `.git` nếu có, databases/migrations, dataset/labels/video/ảnh, model ONNX/YOLO/engine, firmware `.bin`, current release `WEB_FINAL_20261027`, HX711 calibration/physical evidence và các artifact/log có reference hoặc chưa xác định chắc chắn.
Giữ `.venv`, `.venv-ai`, `.tools-venv`, `.tools-zig`, `.checks`, `.release`, `.native-build`, các ZIP, backup và release cũ có thể còn được tham chiếu; không xóa chỉ vì dung lượng lớn.

## Validation sau cleanup

| Check | Kết quả |
|---|---|
| `flutter analyze --no-pub` | **PASS** |
| `flutter test --no-pub` | **PASS — 67 tests** |
| `flutter build web --release --dart-define=FEEDER_MODE=real` | **PASS** |
| `flutter build web --release --dart-define=FEEDER_MODE=mock` | **PASS** |

Cả hai build dùng `--no-pub --no-wasm-dry-run --no-web-resources-cdn --base-href=/flutter/`; output được ghi riêng dưới `C:/Users/chito/AppData/Local/Temp/opencode/cleanup_web_{real,mock}_20261027`, không ghi đè `WEB_FINAL_20261027`.
Log và lệnh chính xác: `C:/Users/chito/AppData/Local/Temp/opencode/cleanup_validation_20261027.json` và `cleanup_{analyze,test,build_real,build_mock}_20261027.log`.

Không kết nối Jetson, không flash, không đổi backend hoặc runtime production trong cleanup.
