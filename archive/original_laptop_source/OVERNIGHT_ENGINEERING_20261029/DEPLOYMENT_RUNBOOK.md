# Jetson staging + camera — owner-run, chưa cutover

## Trạng thái và source

`JETSON_DEPLOY_BUNDLE_READY=YES` có nghĩa source/dependencies/scripts/hash manifest đã chuẩn bị và focused tests PASS. **Không có ARM64 binary mới đã build trên Jetson**. `JETSON_REAL_DEPLOY_PASS=NOT_VERIFIED`.

Source authoritative: `FULL_HARDWARE_INTEGRATION_20261027/payload`; firmware include từ `guard_tuning/esp32/include`. `ai_reference` lấy từ `OFFLINE_REVIEW_20261024/project/jetson/ai` để resolve `shadow/geometry_detector.cpp` và latency headers; chưa chứng minh trùng source live trên Jetson. Original production detector/engine không bị ghi đè.

Release Phase4 là checkpoint source-only; release cuối `release_camera` bổ sung static web đã build trước đó và preflight. `manifest.json` ghim SHA256 từng file; giữ release immutable. Không chứa SQLite/NVS/engine/token/.env. Manifest giúp kiểm tra integrity, không thay thế xác thực nguồn truyền file; giữ digest manifest qua kênh tin cậy.

## 1. Copy staging khi owner thức dậy

Owner copy nguyên release và các tool Python vào một thư mục inbox **ngoài** `/home/toan/for_cat`, ví dụ `/home/toan/forcat-inbox/release_camera`. Không copy chồng production. Các lệnh dưới dùng integration Python3.11, không system Python3.6.

```sh
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
TOOLS=/home/toan/forcat-inbox/release_camera/tools
"$PY" "$TOOLS/release_bundle.py" verify /home/toan/forcat-inbox/release_camera
"$PY" "$TOOLS/jetson_preflight.py" --production-root /home/toan/for_cat
"$PY" "$TOOLS/stage_release.py" stage --bundle /home/toan/forcat-inbox/release_camera --staging-root /home/toan/forcat-staging --production-root /home/toan/for_cat
```

Lệnh stage mặc định chỉ plan. Sau khi kiểm tra đường dẫn, owner thêm `--execute` để copy **chỉ vào staging mới**, không service/runtime changes. Preflight đọc compiler/OpenCV/json-c/sqlite3/CUDA/TensorRT, engine hash, `systemctl is-active`, `fuser`, V4L2 inventory; không đọc frame hoặc mở UART. `fuser` kết quả1 không chứng minh ownership độc quyền trong tương lai; phải kiểm tra lại ngay khi owner launch.

## 2. ARM64 build không chạy detector

```sh
REL=/home/toan/forcat-staging/releases/release_camera
"$PY" "$REL/tools/jetson_build.py" --bundle "$REL" --output /home/toan/forcat-staging/build/release_camera/run1 --production-root /home/toan/for_cat
```

Mặc định plan. Owner thêm `--execute-build` sau preflight; chỉ compile C++14 vào NEW staging/build/RELEASE/RUN. Build ghi log/hash cho `roi_ai_source`, `esp32_bridge`, `ai_state_tap`; không launch binaries. Không dùng output build mới để overwrite `.native-build` production. TensorRT engine hash phải bằng historical expected; nếu khác dừng để đối chiếu, không thay engine hoặc kết luận corrupt. CUDA10.2/OpenCV4/TRT ABI phải kiểm tra trên Nano.

## 3. Giữ stdout contract và chọn đúng topology

**Legacy production:** `scripts/run_existing_ai.sh` → unchanged `jetson/ai/cat_dog_trt --headless --no-snapshot` → `ai_state_tap CANONICAL_DB`. Contract vẫn là `ENGINE_CONTRACT=PASS; COCO CAT=15 DOG=16;`, rồi `DETECTIONS CAT=... DOG=... MODE=... PROCESSED=...` hoặc `NONE MODE=... PROCESSED=...`. DOG priority; no identity labels. Không sửa supervisor này trong phiên overnight.

**Candidate ROI/camera:** `roi_ai_source DB ROI_CONFIG_OR_- /dev/video0` tự giữ AI-writer lock và cập nhật `ai_latest`; không xuất legacy inference stdout cho tap. **Không pipe producer này vào ai_state_tap**: cùng lock/DB sẽ xung đột. Đây là topology riêng, chưa phải drop-in thay binary detector legacy. Giữ stdout protocol legacy bằng cách giữ nguyên nhánh legacy cho tới owner review cutover.

Owner muốn chạy candidate phải chuyển đúng một AI/camera owner trong maintenance window; service legacy phải được owner xử lý riêng. Bundle không tự stop/restart service. Preview dùng cùng capture packet/frame ID, queue1 và encoder thread; không mở camera thứ hai. FULL_FRAME mặc định; ROI candidate vẫn disabled/unreviewed. Không bật ROI chỉ vì có candidate rectangle.

## 4. Backup và rollback

Trước bất kỳ cutover thật, owner lưu inventory/service unit/drop-ins/ExecStart/environment paths và hash detector/engine. Backup live SQLite bằng SQLite backup API khi cần snapshot consistent; **không copy trần DB đang có WAL** và không restore/reset production DB trong workflow này. Bảo vệ backup chứa config server, không đưa lên web.

Tool `stage_release.py select --staging-root ... --release ...` mặc định plan. Thêm `--execute` chỉ tạo symlink **staging/current**, cùng `selection_backup_TIMESTAMP.json` rồi đổi pointer atomic. Không service nào tự sử dụng symlink này hiện tại; đây không phải live deploy. Output backup chứa previous release. Tool `rollback --staging-root ... --backup ...` cũng plan mặc định; owner `--execute` phục hồi previous staging pointer sau verify hash. First selection không có previous nên rollback refuse; owner có thể bỏ staging pointer khi chưa service nào dùng.

**Rollback runtime thật:** vì phiên này không cutover và không sửa service, runtime cũ vẫn là baseline. Nếu sau này owner thay service paths, phải backup/restore chính xác unit/drop-ins và restart có giám sát trong cửa sổ riêng; staging pointer rollback một mình không đổi service đang chạy. Không cung cấp một script giả vờ biết cấu hình live chưa đọc được. Engine/production detector/SQLite vẫn giữ nguyên.

## 5. Camera + remote sáng mai

Đọc tiếp `CAMERA_DEPLOYMENT.md`. Các biến hiện có giữ `CAMERA_PROVIDER=MOCK`, `AI_RUNTIME=MOCK`, `ESP32_TRANSPORT=MOCK`, `SYSTEM_STATE_PROVIDER=REAL`. Stream REAL là đường ảnh riêng, không đổi ba provider sang REAL. Không chạy network apply hoặc camera launch khi chưa có owner.
