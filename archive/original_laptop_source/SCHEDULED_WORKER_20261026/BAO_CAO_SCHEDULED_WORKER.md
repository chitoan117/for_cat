# BÁO CÁO TRIỂN KHAI SCHEDULED WORKER — 26/10/2026

## Kết luận

- **SOFTWARE PASS**: worker nền, lưu occurrence/request atomically, chống trùng,
  dùng chung logic với preview và hiển thị trạng thái thật trên Flutter.
- **DRY RUN PASS**: lịch thật đến hạn tự tạo SCHEDULED35g, được C++ arbiter hiện
  có xử lý, không cần bấm preview; lặp poll/restart vẫn một request mỗi lịch.
- **PHYSICAL NOT TESTED / BLOCKED**: servo/pump tiếp tục disarmed/output0;
  AUTO_FEED=false, AUTO_WATER=false, actuator_execution=false;
  actual_dispensed_grams=null. HX711 chưa hiệu chuẩn gram.

## Thiết kế đã triển khai

Worker là task ASGI `scheduled-dry-run-worker` trong service FastAPI hiện có
`for-cat-api.service`, poll mỗi2giây. Không tạo backend, cơ sở dữ liệu, camera
reader, serial reader hoặc arbiter thứ hai. AI C++/model/engine và firmware ESP32
được bảo toàn; không flash và không gửi lệnh cơ cấu.

Meal Plan dùng UTC+7. Cùng logic kiểm tra TIME_VALID, trạng thái REAL/fresh/safe,
lịch bật/ngày/giờ và cửa sổ60giây phục vụ cả worker lẫn preview. Không chạy bù
bữa đã lỡ. Plan mới vẫn mặc định tắt.

Occurrence có identity theo plan_id + ngày Việt Nam, độc lập revision. Mỗi plan
là một slot HH:mm mỗi ngày; đổi tên/giờ sau khi đã có occurrence hôm đó không
tạo lượt thứ hai. Muốn nhiều bữa/ngày dùng nhiều plan. Bảng scheduled_occurrences
và inbox feed_dry_run_requests được ghi trong một transaction. Retry, poll lặp,
preview hoặc process mới trả lại identity đã lưu; lỗi trước commit không để lại
request mồ côi. SQLite user_version2 và giới hạn ledger hiện có được giữ.

## Kết quả kiểm thử

| Bộ kiểm tra | Kết quả |
|---|---|
| Backend đầy đủ trên Jetson Python3.11 | 399 PASS, gồm30 case worker mới |
| Bộ tập trung worker/Meal Plan/preview | 61 PASS |
| Flutter Windows | Analyze sạch,30 tests PASS, build REAL release PASS |
| JS client từ source canonical, Windows Node | 14 PASS |
| C++/UBSan fake dispense | 9 nhóm/99 assertions PASS, thêm9 kiểm tra35g fake PASS |
| pip check / git diff check | PASS |
| Chromium thật kiosk/app | Worker RUNNING, occurrence Tự động, blocked reason; không POST điều khiển/lỗi runtime/network |

Các case yêu cầu đều có: chưa đến giờ, đúng giờ, poll lặp, restart, disabled,
deleted, nhiều lịch cùng giờ, revision/đổi giờ, UTC+7 qua nửa đêm, C++ arbiter,
disarmed. Có thêm concurrency worker/preview, atomic rollback bằng lỗi giả lập,
inbox full/retry, no catch-up, ASGI lifecycle và cấu hình sai fail-closed.

## Bằng chứng live không bấm preview

Tạo hai plan bật cùng giờ10:20 và một plan tắt. Lúc **10:20:01 ngày26/10/2026,
giờ Việt Nam**, worker tự tạo:

| Plan | Request ID | Inbox / event arbiter |
|---|---|---|
| worker_proof_cd006817c8_a | schedule_7996f4ce027cdc591d2564d57a9e5e8b5dc2356ea5ead400 | 1 / 1 |
| worker_proof_cd006817c8_b | schedule_692bbd1f02c911c3322da10586cdbff69631bda8db651019 | 1 / 1 |
| worker_proof_cd006817c8_disabled | Không có | 0 / 0 |

Hai occurrence có origin=WORKER. Trước thời điểm tạo tự động không có POST
preview/feed trong trace kiểm thử. C++ trả DRY_RUN_BLOCKED / UNATTENDED_SAFE_MODE /
WEIGHT_NOT_CALIBRATED, target35g, actual gramsnull, actuatorfalse.

API restart trong cùng cửa sổ đến hạn đổi PID20482->22570 và worker_id. Process
mới ghi submitted_count0/duplicate_observations4, vẫn đúng hai occurrence và
hai request/event ban đầu. Đổi revision/tên và gọi preview SAU giai đoạn tự động
cũng trả lại identity cũ. Ba plan thử đã xóa; tombstone/receipt giữ làm bằng chứng.
Các bảng cấp thức ăn thật giữ nguyên0/0/0 trước/sau.

## File thay đổi chính

Backend:
- jetson/app/scheduled_worker.py (mới)
- jetson/app/main.py
- jetson/app/meal_plans.py
- jetson/app/dry_run_requests.py
- jetson/app/api/meal_plan_routes.py
- jetson/tests/test_scheduled_worker.py (mới)

Flutter chính tại D:/DA_KT_NC/feeder_demo, snapshot cùng thay đổi ở frontend/feeder_demo:
- lib/meal_plans.dart
- lib/feeder_backend.dart
- lib/real_backend.dart
- lib/meal_plan_panel.dart
- test/scheduled_worker_test.dart (mới)

Cấu hình/tài liệu:
- deploy/systemd/50-scheduled-dry-run.conf (template mới)
- Drop-in thực tế ~/.config/systemd/user/for-cat-api.service.d/50-scheduled-dry-run.conf
- Drop-in40-flutter-real.conf trỏ artifact scheduled_worker_20261026_r1
- docs/SCHEDULED_WORKER.md (mới), docs/CURRENT_PROJECT_STATE.md,
  docs/MEAL_PLANS.md, docs/FLUTTER_FRONTEND.md, docs/LAN_STARTUP.md
- config/hardware_current.json

## Kiểm tra trên Jetson

```sh
systemctl --user status for-cat-api for-cat-esp32-bridge for-cat-ai --no-pager
curl -s http://127.0.0.1:8000/api/meal-plans/worker
journalctl _SYSTEMD_USER_UNIT=for-cat-api.service --since=-10min --no-pager
```

Worker chạy bên trong API, không có service cơ cấu mới. Kết quả API có enabled,
running, last_poll_at, poll_count, error_count, worker_id và recent_occurrences.
Counter theo phiên reset khi restart; occurrence lưu bền không reset.

Mở http://server-jetson.local:8000/app hoặc /kiosk, tải lại một lần, vào Cho ăn.
Lịch bật đến hạn sẽ tự được xét; nút preview vẫn dùng được. UI hiện Worker và
history Tự động; mất trạng thái sẽ UNKNOWN. Đọc cờ phần cứng thật ở /api/status.

## Evidence

Jetson: /home/toan/for_cat/evidence/scheduled_worker_20261026T021542321284Z/

Các file quan trọng: live_worker_verified.json, live_automatic_before_restart.json,
live_http_calls.json, scheduled_creation_journal_lines.json, live_worker_journal.log,
worker_ui_verified.json, screenshots, full regression logs, source/DB backups và
manifest SHA256. Windows: D:/for_cat/SCHEDULED_WORKER_20261026/.

36 file staged/index gốc được bảo toàn. Kết quả này xác nhận tự động tạo request
SCHEDULED ở mức DRY RUN; phần cấp thức ăn vật lý vẫn cần hiệu chuẩn HX711 và
thử nghiệm cơ cấu có kiểm soát trong đợt riêng.
