# OFFLINE RELEASE 2026-10-26

## Kết luận freeze

**OFFLINE RELEASE CANDIDATE READY** cho phạm vi phần mềm offline, tài liệu và demo local.
Không phải hardware release hoặc xác nhận physical35g. Không có production deploy trong phiên này.

## Định danh checkpoint / worktree

- Workspace tài liệu: `D:/for_cat`; Flutter primary: `D:/DA_KT_NC/feeder_demo`.
- Cả hai đường dẫn **không phải Git worktree** (`git rev-parse --show-toplevel` trả not-a-repository); không có commit mới, không stage/commit/push. Không bịa commit hash.
- Release được định danh bằng `OFFLINE_RC_20261026/release_manifest_sha256.json` và hash các source/build/docs/evidence trong đó.
- Frontend khớp **39/39 file SHA256** với `FRONTEND_USER_APP_OFFLINE_20261026/source_after_sha256.json`; freeze session không đổi frontend production source.
- Diff milestone frontend trước freeze: **28 file =20 sửa +8 thêm**, không xóa; danh sách đầy đủ bên dưới và `FRONTEND_USER_APP_OFFLINE_20261026/frontend_changes.patch`.
- `D:/for_cat/jetson` là checkout cũ. Workspace `FRONTEND_USER_APP_OFFLINE_20261026/verification` được tổng hợp từ checkpoint cục bộ để chạy test, **không phải deployment source**.
- Hồ sơ Jetson trước đó có36 file staged, index SHA256 `1cd1e194acc1cd884dc1ff147936cdcf64be43cd8fdaa03a0a6d7673a91caae8`; chỉ là tham chiếu lịch sử. Không SSH nên không kiểm lại HEAD/index hiện tại, không thay staged work.

## Final regression thực chạy trong phiên RC

| Kiểm tra | Kết quả | Evidence trong `OFFLINE_RC_20261026/` |
|---|---|---|
| `flutter analyze --no-pub` | PASS, không issue | `flutter_analyze.log` |
| `flutter test --no-pub` | **54 PASS** | `flutter_tests.log` |
| REAL release build | **PASS** | `flutter_build_real.log`, `web_real/` |
| MOCK release build | **PASS** | `flutter_build_mock.log`, `web_mock/` |
| Backend offline | **393 PASS, 1 deselected** | `backend_offline.log` |
| JS canonical archived request-client regression | **14 PASS, 0 fail** | `js_regression.log` |
| Frontend diff / source freeze | PASS | `frontend_diff_check.log`, `frozen_source_sha256.json` |
| Local backend/AI/config/service source freeze | UNCHANGED | `protected_local_before_sha256.json`, `protected_local_after_sha256.json` |
| Existing REAL artifact guard | PASS; REAL được nhận, MOCK bị từ chối | `regression_result.json` |
| Screenshots | **36**, hash được xác minh | `screenshot_sha256.json` |

Tổng unit/widget/backend/JS: **461 PASS**, không tính build/guard/docs checks vào tổng test này.
393 là bộ có thể chạy từ workspace offline tổng hợp, không gọi là chạy lại toàn bộ428 tests Jetson lịch sử.
Lệnh và cwd chính xác nằm trong `regression_result.json`; runner `run_final_regression.py` không gọi hardware/service/network remote.

Diff check dùng `git diff --no-index --check` vì không có repo. Exit1 với diff là bình thường;55 warning LF→CRLF của Git Windows đã giữ nguyên trong log và được phân loại riêng.
Không có diagnostic whitespace khác. Lần đầu script đánh dấu FAIL vì coi warning là error; chỉ sửa harness phân loại warning, rồi chạy lại diff/freeze/guard bằng `--finish-only`.
Không chạy lại các suite đã đạt sau đó vì source ứng dụng không đổi. Không thay Git config hoặc chuẩn hóa lại toàn bộ source để che warning.

36 ảnh là bộ browser đã review của **cùng source** ở milestone frontend, không phải36 lượt chụp mới trong freeze.
`FRONTEND_USER_APP_OFFLINE_20261026/browser_offline_report.json` có PASS, zero external asset attempts/runtime errors;
chỉ36 ảnh có tên trong report mới là release evidence, các ảnh debug/attempt không được tính.
Đã có5 tab ở320/390/768/1280, MOCK states và REAL backend absent. Mobile viewport không phải APK/device physical test.

## Audit release freeze

| Điều kiện | Kết quả / phạm vi |
|---|---|
| 5 tab hoạt động | PASS widget/browser checkpoint, primary source khớp freeze |
| REAL/MOCK build | PASS compile riêng, mode guard đúng |
| REAL mất backend | OFFLINE/UNKNOWN; không tự chuyển MOCK |
| Sensor values thiếu | null/unknown, không số giả trong REAL; fixture chỉ MOCK |
| Target35g/actual | Wording tách rõ; null actual là Chưa xác minh, không lấy bowl weight/target làm actual |
| Meal Plan / Scheduled Worker UI | Regression PASS, worker backend/policy/source unchanged |
| History | Merge event/occurrence/receipt, request-ID dedupe; blocked không bị pending ghi đè, không tạo physical completion |
| Diagnostics | Link/sensor states tách biệt; timeout/stale/unwired không hiện distance cũ như live |
| HX711 calibration UI | Read-only READINESS; không command/API calibration mới, không activate model, chưa physical pass |
| AUTO_CAT | Dedicated state thiếu → UNKNOWN/NOT_AVAILABLE; không suy READY từ sensor rời rạc |
| Sensor #2 | NOT_WIRED/UNKNOWN; đề xuất16/17 và18/10 chưa duyệt, không physical pass giả |
| Responsive | Widget/browser evidence320/390/768/1280; không overflow ở các case được kiểm, IDs mở rộng/copy đủ |
| Source scope | Không feature mới hoặc refactor; phiên freeze chỉ docs/evidence/static demo helper |

Không phát hiện blocker trong phạm vi OFFLINE RC. Các giới hạn physical là backlog rõ ràng, không được đổi tên thành pass.

## Production invariants

- **Backend production contract unchanged**: không thêm route/schema hoặc thay semantics request/receipt.
- **AI production unchanged**: không train/retrain/rebuild engine, không chạy detector/camera; không upload binary/model.
- **Scheduled Worker unchanged**: vẫn task trong API hiện có,2s poll, VN UTC+7, window60s/no-catch-up, occurrence unique plan/ngày và canonical inbox atomic.
- **Safety unchanged**: AUTO_FEED=false, AUTO_WATER=false, servo_armed=false, pump_armed=false, actuator_outputs_enabled=0, actuator_execution=false, actual_dispensed_grams=null ở dry-run checkpoint.
- Thiếu telemetry trong REAL là UNKNOWN cho cờ chưa biết; các cờ trên không được hiểu là đã đo GPIO remote hôm nay.
- Không SSH, flash, Jetson service/config/REAL SQLite write, deploy hoặc mở serial/camera reader cạnh tranh.
- Protected-local hash chỉ chứng minh file cục bộ không đổi. SHA AI production từ checkpoint lịch sử, **không đọc lại remote**:
  - source C++ `9b01288e4b6e450217d3029c2d0b4a3aecafb9dc0e2f87e17289d3e83f5b6366`
  - binary `c3651fc3d1331b24a45c6a74b94a883e362fd4ded2412bb8f3ad195f1c443cdc`
  - engine `48fe40017461d2e4edab33c47b30194b84ba7714e32e6d3d2aa4649f5b7471fb`

## File thay đổi của milestone frontend được freeze

| Nhóm | Files |
|---|---|
| UI/model mới | `lib/status_model.dart`, `history_model.dart`, `diagnostic_models.dart`, `ui_widgets.dart`, `user_pages.dart`, `diagnostics_page.dart` |
| UI/backend adapter sửa | `lib/main.dart`, `meal_plan_panel.dart`, `feeder_backend.dart`, `feeder_state.dart`, `real_backend.dart`, `mock_backend.dart`, `backend_factory.dart` |
| Format-only | `lib/pending_store.dart`, `pending_store_base.dart`, `pending_store_stub.dart`, `pending_store_web.dart` |
| Test mới | `test/user_app_offline_test.dart` |
| Regression tests sửa | `test/feeder_demo_test.dart`, `hx711_state_test.dart`, `meal_plans_test.dart`, `mock_backend_test.dart`, `real_backend_test.dart`, `scheduled_worker_test.dart` |
| Web/assets | `web/index.html`, `web/manifest.json`, `pubspec.yaml`, `assets/fonts/Roboto-Regular.ttf` |

## File tạo/sửa trong freeze session này

**Tạo mới:**
1. `docs/PROJECT_STATUS_20261026.md` —25 hạng mục, Software/Runtime/Physical riêng.
2. `docs/NEXT_PHYSICAL_SESSION.md` —20 bước, mỗi bước có mục tiêu/criteria/log/safety.
3. `docs/DEMO_SCRIPT_VI.md` —6phút30, REAL outage và MOCK được giải thích rõ.
4. `docs/DEFENSE_QA_VI.md` —36 câu hỏi/trả lời ngắn.
5. `docs/ARCHITECTURE_OVERVIEW.md` —5 Mermaid +5 ASCII, đường physical được đánh dấu future/BLOCKED.
6. `OFFLINE_RELEASE_20261026.md` —manifest này.
7. `OFFLINE_RC_20261026/README.md`, `run_final_regression.py`, `serve_demo.py`, `finalize_release.py` —runner/evidence/static launcher local; không phải backend hoặc feature app.

**Sửa tài liệu cũ:** `docs/CURRENT_PROJECT_STATE.md` chỉ thêm banner trỏ matrix mới, giữ chronology và cảnh báo pin legacy.
**Không sửa source ứng dụng production trong freeze.**

## Dễ demo / bàn giao

Từ Windows, mở hai terminal theo `docs/DEMO_SCRIPT_VI.md`:

```powershell
D:\for_cat\.venv\Scripts\python.exe D:\for_cat\OFFLINE_RC_20261026\serve_demo.py --mode mock --port 8765
D:\for_cat\.venv\Scripts\python.exe D:\for_cat\OFFLINE_RC_20261026\serve_demo.py --mode real --port 8766
```

Mở `http://127.0.0.1:8765/app?fixture=cat` (MOCK) và `http://127.0.0.1:8766/app` (REAL/backend absent).
Launcher chỉ serve static ở127.0.0.1; không có API sensor/actuator/SQLite hoặc request replay. Ctrl+C để dừng.
Fixture được chọn bằng query chỉ trong MOCK build; query đó không bật MOCK trong REAL.

Gói bàn giao `OFFLINE_RC_20261026/offline_release_candidate_20261026.zip` chứa docs, source/build snapshots, log/manifest và36 ảnh đã chọn.
Không chứa REAL database, AI weights/engine, chromium profile, payload estimate dở hoặc workspace verification dùng để deploy.
Launcher demo dùng build đóng gói nên chạy được sau khi giải nén/chọn lại đường dẫn Python. Runner regression dùng các đường dẫn checkpoint cục bộ đã ghi;
muốn chạy lại393 backend tests cần giữ workspace verification và nguồn fixtures theo provenance, không coi zip là full backend repository.
`release_manifest_sha256.json` và `.zip.sha256` dùng kiểm file khi copy.

## NOT RUN và backlog giữ lại

- **NOT RUN — LINUX/NATIVE REQUIRED:** `test_worker_request_is_consumed_by_existing_cpp_arbiter_on_synthetic_pty` (1 deselected), các native bridge/device suites trên Linux; không fake pass trên Windows.
- **NOT RUN — HARDWARE REQUIRED:** reconnect/live telemetry/AI thật trong phiên RC, sensor đo thật, pin #2 approval, HX711 đặt tải/validation/persistence, servo/pump motion/flow, actual35g, AUTO_CAT/AUTO_WATER physical, reboot/cold-boot/soak và APK/device test.
- Gram calibration **NOT_CALIBRATED**; candidate cuối ngày chưa đủ verify, không activate; unfinished demo estimate bị loại khỏi RC.
- Không physical claim mới; các physical facts lịch sử có giới hạn trong status matrix.
- Bước đầu tiên khi hardware trở lại: **kiểm nguồn/common GND**, rồi enumerate ESP32 và xác nhận telemetry/safety. Các bước sau theo đúng checklist20 bước.

OFFLINE RELEASE CANDIDATE 2026-10-26 — READY
