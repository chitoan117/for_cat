# Bữa ăn của MÈO — frontend user app, offline 26/10/2026

## Kết quả

Đã hoàn thiện P0/P1 và Settings/responsive P2 trong `D:/DA_KT_NC/feeder_demo`.
Giữ tên ứng dụng, theme cam/kem/xanh, 5 tab; REAL là mặc định, MOCK chỉ được chọn khi compile rõ ràng.

| Kiểm tra | Kết quả |
|---|---|
| Flutter analyze `--no-pub` | Không có issue |
| Flutter unit/widget/regression | **54 PASS** |
| Backend offline trong workspace tổng hợp tách biệt | **393 PASS, 1 deselected** |
| Existing archived web request-client regression | **14 PASS** |
| Flutter web release REAL và MOCK | **Cả hai build thành công**, base `/flutter/`, local CanvasKit/font |
| Chromium local, viewport 320/390/768/1280 | **36 screenshot**, 5 tab và các trạng thái; không runtime error, không external asset request |
| REAL khi backend vắng mặt | OFFLINE/UNKNOWN, không fallback MOCK, không % hoặc grams giả |

Logs: `flutter_analyze.log`, `flutter_tests.log`, `flutter_release_real.log`, `flutter_release_mock.log`, `backend_offline.log`.
Browser: `browser_offline_report.json`, ảnh và snapshot semantics trong `screenshots/`.
Các `browser_attempt_*.json` và ảnh debug là lần kiểm tra trước khi sửa font fallback/selector chụp, không phải kết quả cuối.

393 là bộ Python có thể chạy từ các checkpoint cục bộ đã tổng hợp, **không đồng nghĩa chạy lại toàn bộ checkpoint Jetson trước đây**.
Một bài `test_worker_request_is_consumed_by_existing_cpp_arbiter_on_synthetic_pty` không chạy do Windows không có Linux PTY/native bridge.
Fixture `verification/jetson/tests/conftest.py` chỉ cung cấp boot identity synthetic trên Windows cho SQLite test; production identity và assertion được giữ.
Backend production không bị sửa hoặc triển khai trong đợt này.

## Thay đổi theo tab

### 1. Tổng quan
- Header REAL/backend connection tách riêng link ESP32; CAT/DOG/NONE/UNKNOWN dễ hiểu.
- Kho thức ăn/nước hiện % chỉ khi có giá trị hợp lệ; thiếu dữ liệu không được đổi thành 0%.
- `Mục tiêu mỗi lần: 35 g`; chưa có phép cấp thật thì `Kết quả cấp: Chưa xác minh`.
- Không lấy HX711 bowl weight hoặc target để tạo actual dispensed. Giá trị future field chỉ được hiện nếu feed báo execution thật, không dry-run và link còn hợp lệ.
- Lịch tiếp theo dùng giờ Jetson TIME_VALID, timezone VN, lịch bật và occurrence dedupe; cache lỗi không được hiện như lịch mới nhất.
- Tóm tắt hệ thống, request gần đây, hoạt động gần đây. Không raw/tare/scale/ID trên dashboard.

### 2. Cho ăn
- Nút MANUAL 35 g vẫn ghi rõ DRY RUN, xác nhận trước POST, giữ durable request-ID/retry/reload GET-only.
- Danh sách lịch ăn, giờ/ngày/bật-tắt/sửa/xóa/thêm qua API hiện có; lịch mới mặc định tắt.
- Worker counters, poll time, IDs, occurrence, preview/arbiter receipt nằm trong `Chi tiết kỹ thuật`.
- Không diễn giải DRY_RUN_BLOCKED thành bữa ăn đã hoàn tất. MOCK không ghi lịch vào Jetson.

### 3. Lịch sử và audit nguồn

Lịch sử cũ chỉ lấy bounded event ring, vốn có telemetry và có thể đã trôi mất request cũ.
Occurrence bền đã tồn tại trong API Meal Plan nhưng trước đây chưa được đưa vào tab Lịch sử.
Frontend hiện ghép:

| Nguồn hiện có | Ý nghĩa |
|---|---|
| `GET /api/v1/esp32/events?limit=100` | Native dry-run request và system/serial/sensor events có thật |
| `GET /api/meal-plans`, trường `recent_occurrences` | Scheduled occurrence lưu bền, kể cả khi event ring rỗng |
| Receipt đã kiểm tra từ flow MANUAL/SCHEDULED | Request pending/blocked theo canonical identity |

- Dedupe theo request ID; decision blocked không bị ghi đè bằng pending. Có timestamp thật thì dùng timestamp đó; thiếu thì ghi rõ, không dùng giờ client thay thế.
- Filters Tất cả/Cho ăn/Nước/AI/Hệ thống. Không tạo nhật ký cấp nước hoặc AI transition bằng cách suy từ snapshot.
- Contract hiện tại không expose water actuation history/AI transition stream đầy đủ: UI ghi chưa hỗ trợ/chưa có dữ liệu. MOCK có event fixture riêng, luôn có badge.
- Request chưa physical dispense không có completed-feed entry. Lịch sử đã tải có thể giữ khi mất kết nối và được ghi là cache.
- Offline tests kiểm tra event ring rỗng nhưng occurrence vẫn ra History, dedupe native event + occurrence, malformed/unsafe payload và null actual.

### 4. Hệ thống
- Diagnostics cho Jetson/backend, ESP32, AI, HX711, 4 ultrasonic, PIR, OLED, button, Scheduled Worker, AUTO CAT, actuator safety.
- Phân biệt NOT_WIRED, NOT_CONFIGURED, TIMEOUT, STALE, OFFLINE, UNKNOWN, DISABLED, NOT_CALIBRATED, DRY_RUN, BLOCKED; cấu hình cảm biến không tự chứng minh sensor khỏe.
- Không coi thiếu telemetry là servo/pump đã OFF. Boolean không có dữ liệu hiện UNKNOWN/Chưa rõ; không dùng giá trị mặc định false để xác nhận GPIO.
- Technical snapshot/IDs mở rộng được, wrap không overflow; có sao chép JSON đầy đủ.

#### Hiệu chuẩn
- `GET /api/hx711/calibration` **read-only**; 404 được hiểu là unsupported, lỗi/malformed là unknown.
- Checklist Tare 0, 5, 10, 20, 30, 35 g đọc `point_summaries`; đã thu FIT không đồng nghĩa kiểm chứng PASS.
- Expected/candidate/error/stability/PASS-FAIL chỉ hiện nếu `latest_session.validation_results` có các giá trị đó; không tự tính pass từ dữ liệu thiếu.
- Nút bắt đầu hiệu chuẩn bị disable vì chưa có command API phù hợp. Metadata cache được đánh dấu nếu connection chưa xác nhận.
- Không sửa tiêu chí calibration, không activate model, không dùng công việc HX711_DEMO_ESTIMATE chưa hoàn tất.

#### AUTO_CAT
- UI model chuẩn bị IDLE/CAT_DETECTED/APPROACHING/READY_TO_REQUEST/BLOCKED/COOLDOWN.
- Dedicated state không được expose trong contract hiện tại thì state UNKNOWN, NOT_AVAILABLE. Không suy READY_TO_REQUEST từ CAT + distance.
- Checks AI/distance/stable/cooldown/HX711 chỉ dùng bằng chứng được expose; thiếu thì UNKNOWN. Dedicated state bị ẩn khi AI hoặc ESP32 stale.
- UI mô tả request qua arbiter rồi DRY RUN/BLOCKED; không tạo request hoặc history AUTO_CAT nếu backend không có event.

#### Bốn ultrasonic
- HC-SR04 #1: existing approach, cấu hình TRIG12/ECHO13; JSN-SR04T #1: water operational, TRIG14/ECHO15.
- Có configured + invalid + timeout evidence thì TIMEOUT, không bị gọi nhầm NOT_CONFIGURED. Stale/timeout/unwired/config-disabled không hiện distance cũ.
- #2 lấy NOT_WIRED từ metadata hiện có; nếu không có metadata thì UNKNOWN. Vai trò chưa chốt ghi TBD, actual pins để null.
- HC-SR04 #2 đề xuất 16/17; JSN-SR04T #2 đề xuất 18/10. Đây là **đề xuất chưa áp dụng**, có RESERVED conflict trong checkpoint phần cứng và cần được xác nhận trước khi đấu.
- Schema UI: sensor_id/type/role/enabled/wired/distance_cm/valid/timeout/stale/age/state. Không sửa config firmware/GPIO.

### 5. Cài đặt
- Read-only thiết bị, endpoint, REAL/MOCK, AI runtime dự án và metadata model/input nếu backend cung cấp, mục tiêu35g, AUTO_FEED/AUTO_WATER.
- Metadata model/input thiếu được ghi chưa có metadata; không trình bày runtime dự án như số liệu live đã kiểm chứng.
- Không có command mở khóa servo/pump hoặc GPIO editor. MOCK có bộ chọn fixture riêng, REAL không có selector này.

## Files và artifacts

Source mới chính: `lib/status_model.dart`, `history_model.dart`, `diagnostic_models.dart`, `ui_widgets.dart`, `user_pages.dart`, `diagnostics_page.dart`, `test/user_app_offline_test.dart`.
Source thay đổi chính: `main.dart`, `meal_plan_panel.dart`, `feeder_backend.dart`, `feeder_state.dart`, `real_backend.dart`, `mock_backend.dart`, `backend_factory.dart`.
Các regression tests được cập nhật theo wording/tab mới; format-only ở các pending-store files được giữ và có trong diff.
`web/index.html`, `web/manifest.json` dùng tên/theme ứng dụng. `pubspec.yaml` + `assets/fonts/Roboto-Regular.ttf` bundle font từ artifact cục bộ cũ, không tải font mới.
Các ký tự cần fallback ngoài font được thay bằng Material Icons hoặc chữ, browser xác nhận không gọi font CDN.

- `frontend_original/`, `frontend_before_sha256.json`: bản trước đợt này.
- `frontend_changes.json`, `frontend_changes.patch`: danh sách/diff đầy đủ.
- `source_final/`: snapshot source cuối; `source_after_sha256.json`: checksum.
- `web_real/`, `web_mock/`: compiled artifacts riêng, không đè published build cũ.
- `frontend_offline_bundle.zip`: source và hai web artifact, không chứa DB hoặc model AI.
- `offline_backend_provenance.json`: nguồn checkpoint dùng cho verification, không phải deployment source.
- `reproduce/`: các script kiểm thử/build/chụp/package offline, dùng đúng đường dẫn local của phiên này.

## Screenshot index

Tất cả ảnh có tên `mock_*` là **MOCK**, không chứng minh phần cứng.

| Nội dung | Ảnh |
|---|---|
| 5 tab tại bốn chiều rộng | `screenshots/mock_{320,390,768,1280}_tab{0..4}.png` |
| CAT/DOG/NONE/offline/stale/timeout/calibrated fixtures | `screenshots/mock_fixture_*.png` |
| HC#1 TIMEOUT + #2 proposal | `screenshots/mock_timeout_ultrasonic.png` |
| Checklist và action disable | `screenshots/mock_calibration_read_only.png` |
| AUTO_CAT missing dedicated state | `screenshots/mock_auto_cat_unknown.png` |
| REAL build không có backend | `screenshots/real_backend_absent.png` |
| Actual dispense chưa xác minh | `screenshots/real_unverified_dispense.png` |
| Các tab REAL offline còn lại | `screenshots/real_offline_tab{1..4}.png` |

Ảnh mobile là viewport web Android-like; **không phải thử APK trên điện thoại Android thật**.
Đã xem trực quan dashboard, feeding320, history390, diagnostics, checklist, TIMEOUT, AUTO_CAT, settings desktop và REAL outage.

## Contract, safety và các phần chưa chạy

**Không đổi backend production contract**; chỉ bổ sung frontend GET calibration có capability fallback, ghép các nguồn history đã có và các UI model.
Existing REST/WS, request-ID, revision/idempotency, target35g và dry-run invariants được giữ qua regression.
No SSH, no deploy, no flash, no serial/camera reader mới, no train/retrain/engine rebuild, no REAL SQLite fixtures.

Safety trong fixture dry-run/receipt: AUTO_FEED=false, AUTO_WATER=false, servo_armed=false, pump_armed=false,
actuator_outputs_enabled=0, actuator_execution=false, actual_dispensed_grams=null.
Đó không phải xác nhận lại phần cứng remote trong đợt offline; REAL backend vắng mặt hiển thị unknown.

**NOT RUN — HARDWARE REQUIRED:** reconnect Jetson thật, WS/live telemetry thật, HX711 đặt tải/calibration/persistence,
ultrasonic #1 đo thật, #2 đấu dây/pin confirmation, PIR/OLED/button physical, AUTO_CAT physical,
servo/pump và physical35g dispense, reboot/cold boot/soak. Không tuyên bố PHYSICAL PASS.

**NOT RUN — LINUX/NATIVE REQUIRED:** synthetic PTY C++ worker integration và native bridge/device suite.
Các bài này không được thay bằng fake PASS trên Windows.

Các pending hardware/calibration giữ nguyên checkpoint trước; cần đợt có phần cứng và người thao tác riêng.
