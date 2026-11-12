# PROJECT STATUS — 2026-10-26

## Phạm vi và cách đọc

Đây là status matrix của checkpoint **OFFLINE RELEASE CANDIDATE**, thay cho việc suy trạng thái mới từ tài liệu Windows cũ.
Phiên release này chỉ đọc source/evidence cục bộ và kiểm thử offline; không SSH, không đo lại hardware, không deploy.
Các giá trị Runtime/Physical dưới đây là **bằng chứng lịch sử đến checkpoint**, không phải tình trạng live hôm nay.
Nếu hỏi thiết bị hiện đang online hay cờ GPIO hiện tại: **UNKNOWN** cho tới khi có telemetry thật mới.

- **PASS:** kiểm thử đúng tầng được nêu, không ngụ ý physical.
- **DRY_RUN_PASS:** request/decision được kiểm chứng, không thực thi cơ cấu.
- **SOFTWARE_READY:** code/UI/policy đã chuẩn bị; chưa xác nhận vận hành đầu-cuối physical.
- **NOT_TESTED:** chưa có phép thử đạt yêu cầu trong phạm vi này.
- **BLOCKED:** gate chưa cho phép hoặc có kết quả không đạt; không được tự bỏ gate.
- **NOT_WIRED:** xác nhận chưa đấu ở checkpoint; không đồng nghĩa sensor hỏng.
- **NOT_CALIBRATED:** chưa có calibration được xác nhận hợp lệ cho phép đo này.
- **UNKNOWN:** bằng chứng chưa đủ/không fresh/contract chưa cung cấp.
- **PHYSICAL_PASS:** chỉ dùng trong cột Physical, kèm giới hạn và nguồn bằng chứng lịch sử cụ thể.

## Matrix

| Hạng mục | Software | Runtime | Physical | Ghi chú |
|---|---|---|---|---|
| ESP32 telemetry | PASS | PASS | PHYSICAL_PASS | USB/C++ bridge đã nhận telemetry thật 23–26/10; heartbeat/stale/reconnect có gate. Không kiểm lại live ở phiên RC. |
| OLED | SOFTWARE_READY | PASS | PHYSICAL_PASS | Owner xác nhận hiển thị, cấu hình 0x3C, SDA8/SCL9; bằng chứng trước RC. |
| PIR | SOFTWARE_READY | PASS | PHYSICAL_PASS | Owner xác nhận đáp ứng; GPIO11. Không suy từ CONFIGURED thành độ chính xác đo đã chứng nhận. |
| GPIO21 | PASS | DRY_RUN_PASS | PHYSICAL_PASS | Nút diagnostic short/hold/release đã thử; INPUT_PULLUP, LOW khi nhấn; một request mỗi press, không điều khiển servo trực tiếp. |
| HX711 raw | PASS | PASS | PHYSICAL_PASS | DOUT4/SCK5, có raw/đáp ứng tải trước RC; raw pass không phải gram calibration pass. |
| HX711 gram calibration | SOFTWARE_READY | NOT_CALIBRATED | NOT_CALIBRATED | Có FIT 0/5/10/20/30/35 thật và candidate; kiểm chứng zero/35 chưa đạt tiêu chí, chưa model active hợp lệ. Persistence chưa thử. |
| HC-SR04 #1 | SOFTWARE_READY | PASS | PHYSICAL_PASS | Raw ranging/near–far được owner xác nhận; TRIG12/ECHO13. Không chứng nhận absolute accuracy/near threshold; monitor dài hạn từng timeout nhiều. |
| HC-SR04 #2 | SOFTWARE_READY | NOT_WIRED | NOT_WIRED | Chỉ có schema UI; role vận hành chưa chốt, actual pins null. Đề xuất16/17 chưa duyệt, xung đột RESERVED. |
| JSN #1 | SOFTWARE_READY | PASS | PHYSICAL_PASS | JSN-SR04T #1 TRIG14/ECHO15: owner xác nhận ranging/display cơ bản; chưa geometry/threshold/pump validation, có timeout ngoài vùng demo. |
| JSN #2 | SOFTWARE_READY | NOT_WIRED | NOT_WIRED | Schema UI; đề xuất18/10 chưa áp dụng, RESERVED; chưa geometry/full-empty. |
| Camera | SOFTWARE_READY | PASS | PHYSICAL_PASS | USB camera trên Jetson đã capture/inference trong checkpoint trước; không mở camera thêm trong RC. Không tuyên bố mọi ánh sáng/góc đều đạt. |
| AI CAT/DOG/NONE | PASS | PASS | PHYSICAL_PASS | Detector C++ TensorRT đã xuất nhãn thật trước RC; chỉ xác nhận inference cơ bản, không phải accuracy/FPS benchmark hay nhận dạng cá thể mèo. |
| Backend | PASS | PASS | NOT_TESTED | FastAPI hiện có đã chạy trên Jetson trước RC; 393 tests offline trong workspace tổng hợp. Cột physical không dùng để cấp chứng nhận cơ cấu. |
| WebSocket | PASS | PASS | NOT_TESTED | REST/WS state và browser thật đã có bằng chứng trước RC; RC tests dùng fixtures/local. Live reconnect cần kiểm lại khi có hardware. |
| Flutter | PASS | PASS | NOT_TESTED | 54 tests, REAL/MOCK build, 36 ảnh local tại320/390/768/1280; chưa test APK/điện thoại Android thật. RC mới chưa deploy Jetson. |
| Manual Feed | DRY_RUN_PASS | DRY_RUN_PASS | BLOCKED | APP/KIOSK/BUTTON request qua arbiter, chống double-click/retry; actual=null, không cấp thật. |
| Meal Plan | PASS | DRY_RUN_PASS | NOT_TESTED | CRUD SQLite, revision/idempotency, VN UTC+7; plan mới mặc định tắt. Lịch lưu được không chứng minh đã cấp ăn. |
| Scheduled Preview | DRY_RUN_PASS | DRY_RUN_PASS | BLOCKED | Dùng cùng evaluate/occurrence identity với worker; không bypass gate. |
| Scheduled Worker | PASS | DRY_RUN_PASS | BLOCKED | Worker nền trong API hiện có, live proof26/10 10:20+07, hai plan một occurrence mỗi plan; restart không tạo thêm trong proof. |
| Feed Arbiter | DRY_RUN_PASS | DRY_RUN_PASS | BLOCKED | Một C++ arbiter nhận MANUAL/SCHEDULED/AUTO_CAT intent; safe mode vẫn chặn thực thi. |
| AUTO_CAT | SOFTWARE_READY | UNKNOWN | BLOCKED | Policy/request path chuẩn bị; dedicated backend state chưa expose đầy đủ nên UI UNKNOWN/NOT_AVAILABLE. Không có proof physical feeding. |
| AUTO_WATER | SOFTWARE_READY | BLOCKED | BLOCKED | Shadow/preview policy có; geometry/ngưỡng chưa xác nhận, AUTO_WATER=false, pump vẫn khóa. |
| Servo | SOFTWARE_READY | BLOCKED | NOT_TESTED | Owner báo đã đấu; không có motion/closure/current test được chấp nhận. servo_armed=false ở checkpoint cũ. |
| Pump | SOFTWARE_READY | BLOCKED | NOT_TESTED | Owner báo có pump/F5305S; không có controlled flow test. pump_armed=false ở checkpoint cũ. |
| 35 g actual dispense | SOFTWARE_READY | BLOCKED | NOT_TESTED | Target là khối lượng cấp thêm dự kiến. Chưa có stable before/after của lần cấp thật; actual_dispensed_grams=null. |

## Những điểm dễ nhầm khi bàn giao

1. Root `D:/for_cat/jetson` và các tài liệu M3/M4 cũ không phải snapshot production mới nhất. Không deploy checkout Windows cũ hoặc workspace verification tổng hợp lên Jetson.
2. `HX711_CALIBRATION_20261026/BAO_CAO_HX711_SOFTWARE_READY.md` là mốc **trước** các phép đặt tải; dòng “0 điểm” ở đó là lịch sử, không phải tình trạng cuối ngày.
3. Phiên `hxcal_91ca4d57d8c24e5d92a3f063a8b01494`: FIT đã có candidate nhưng zero verification khoảng−0.6242g thất bại; vòng chẩn đoán0→35→0 cho delta tải khoảng35.9604g, vượt tiêu chí35±0.35g. Không activate model, không có PHYSICAL_PASS calibration.
4. Owner chấp nhận demo sai số khoảng±5g không thay thế tiêu chí formal; payload `HX711_DEMO_ESTIMATE_20261026` còn dở, chưa test/deploy/approve, bị loại khỏi RC.
5. HC#1/JSN#1 có ranging cơ bản trước đây nhưng monitor dài hạn ít valid sample, không được gọi reliability/soak pass. Monitor gần7h48m thiếu FINAL, không phải8h PASS.
6. GPIO10/16/17/18 còn RESERVED trong checkpoint đã audit. Đề xuất #2 không phải quyền đấu hoặc flash pin map legacy. External RTC không bắt buộc cho scheduler hiện tại; dùng giờ Jetson đã TIME_VALID.
7. Khi REAL mất backend: cờ chưa có dữ liệu là UNKNOWN, không tự suy false/OFF. Chỉ MOCK compile rõ ràng được dùng fixture; không tự fallback.

## Nguồn bằng chứng

- `../FRONTEND_USER_APP_OFFLINE_20261026/BAO_CAO_FRONTEND_OFFLINE.md`, `COMPLETION.json`, `browser_offline_report.json`, manifest source SHA256 và36 ảnh có tên trong report.
- `../OFFLINE_RC_20261026/regression_result.json`: final regression của phiên release này; `../OFFLINE_RELEASE_20261026.md`: kết luận freeze.
- `../SCHEDULED_WORKER_20261026/BAO_CAO_SCHEDULED_WORKER.md`: request IDs, restart proof, path evidence Jetson.
- `../FRONTEND_USER_APP_OFFLINE_20261026/verification/config/hardware_current.json`: **bản sao checkpoint** pin/physical facts; không phải config vừa áp dụng.
- HX physical cuối ngày: hồ sơ phiên trước trong bàn giao hội thoại và đường dẫn evidence tham chiếu `/home/toan/for_cat/evidence/hx711_calibration_20261026T041547966931Z/physical/<session>/`, gồm `return_zero_cycle_20261026T095009549692Z/result.json`. Không truy xuất lại remote ở phiên RC; cần đọc lại khi có hardware.
- `../NETWORK_BOOT_RECOVERY_20261026/OVERNIGHT_REVIEW.json`: giới hạn soak/network.

## Safety freeze và backlog

Checkpoint trước: AUTO_FEED=false, AUTO_WATER=false, servo_armed=false, pump_armed=false,
actuator_outputs_enabled=0, actuator_execution=false, actual_dispensed_grams=null.
Đây là invariants của luồng DRY RUN; cờ live hôm nay vẫn UNKNOWN nếu không có telemetry.

Backlog khi có phần cứng: nguồn/common GND; pin approval #2; ultrasonic reliability/geometry;
calibration và persistence thật; đường kiểm thử cơ cấu riêng có kiểm soát; closed-loop35g;
dedicated AUTO_CAT state nếu cần API review sau này; water threshold/pump; APK/device và reboot/soak.
Không mục nào trong backlog được mở thành feature ở phiên RC này. Xem [checklist phiên kế tiếp](NEXT_PHYSICAL_SESSION.md).
