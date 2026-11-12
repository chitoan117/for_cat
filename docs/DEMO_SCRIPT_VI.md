# DEMO SCRIPT VI — 5–7 phút (mục tiêu 6 phút 30 giây)

## Chuẩn bị — ngoài thời lượng nói

- Dùng checkpoint `OFFLINE_RELEASE_20261026.md`, không deploy hoặc kết nối Jetson trong buổi offline này.
- Windows: chạy hai **static server local**, không phải backend giả:

```powershell
# Terminal 1 — các màn hình có dữ liệu demo, badge MOCK luôn hiện
D:\for_cat\.venv\Scripts\python.exe D:\for_cat\OFFLINE_RC_20261026\serve_demo.py --mode mock --port 8765
# Terminal 2 — REAL build, backend cố ý vắng mặt
D:\for_cat\.venv\Scripts\python.exe D:\for_cat\OFFLINE_RC_20261026\serve_demo.py --mode real --port 8766
```

- Mở `http://127.0.0.1:8765/app?fixture=cat` và `http://127.0.0.1:8766/app`.
- Kiểm viewport390 hoặc màn hình desktop; có36 ảnh dự phòng trong `FRONTEND_USER_APP_OFFLINE_20261026/screenshots/`.
- Thông báo ngay: **“Đây là demo phần mềm offline. Màn hình MOCK có fixture; REAL không có backend sẽ hiện mất kết nối.”**
- Không tạo plan thật, không gửi command phần cứng, không dùng screenshot cũ như video live. Nếu browser lỗi thì chuyển sang ảnh đã gắn MOCK và nói đó là ảnh checkpoint.

## 0:00–0:40 — Bài toán và kiến trúc

**Nói:** “Bữa ăn của MÈO hỗ trợ theo dõi thú nuôi, quản lý lịch và chuẩn bị cấp thức ăn theo khối lượng. Kiến trúc tách Jetson xử lý thị giác/giao tiếp ứng dụng khỏi ESP32 đọc cảm biến và kiểm soát cơ cấu. AI không được mở servo trực tiếp.”

**Chỉ sơ đồ:** camera → C++ OpenCV/TensorRT → CAT/DOG/NONE; ESP32 → một C++ USB bridge → SQLite/SystemState → REST/WebSocket → Flutter.
Backend FastAPI Python vẫn tồn tại cho API/scheduling; “C++ runtime” ở đây nói về inference/bridge, không có nghĩa toàn dự án không có Python.

## 0:40–1:25 — Jetson, ESP32 và AI

**Nói:** “Jetson Nano chạy detector YOLOv8n320 bằng TensorRT FP16, xuất nhãn CAT/DOG/NONE. ESP32-S3 đọc HX711, ultrasonic, PIR, button và OLED. Nhãn CAT không chứng minh đúng cá thể mèo hay đang ăn; cần bằng chứng thời gian và khoảng cách.”

**Thao tác:** MOCK Tổng quan với CAT; có thể chuyển `fixture=dog`, rồi `fixture=none` để giải thích nhãn. Đây là fixture UI, không phải camera inference live.
**Giới hạn:** “Detector thật đã chạy ở checkpoint trước; hôm nay không đo lại accuracy/FPS và không thay model/engine.”

## 1:25–2:10 — Flutter REAL và mất backend

**Thao tác:** sang tab browser REAL `:8766/app`.

**Nói:** “REAL là chế độ mặc định. Khi không có backend, app hiện OFFLINE/UNKNOWN, ẩn sensor values cũ và không tạo số dự trữ. Nó không tự chuyển sang MOCK để làm màn hình đẹp. Khi có Jetson trở lại, REAL dùng REST/WS hiện có, không tự mở camera hay serial.”

Chỉ `Mục tiêu mỗi lần: 35 g` và `Kết quả cấp: Chưa xác minh`. Không nói “đã cấp35g”.

## 2:10–3:10 — Meal Plan và Scheduled Worker

**Thao tác:** quay MOCK → Cho ăn. Chỉ giờ/ngày/bật-tắt và lịch tiếp theo, mở Chi tiết kỹ thuật để thấy vị trí worker/occurrence.

**Nói:** “Lịch dùng giờ Việt Nam UTC+7. Trên REAL có backend, CRUD lưu SQLite, plan mới mặc định tắt. Worker nền trong service API hiện có xét lịch mỗi2giây, cửa sổ60giây, không chạy bù. Mỗi plan/ngày có occurrence duy nhất, kể cả đổi revision hoặc restart.”

“Checkpoint26/10 có bằng chứng worker thật tự tạo request SCHEDULED, arbiter trả blocked dry-run. Đó là DRY_RUN_PASS, không phải bữa ăn vật lý. MOCK ở đây chỉ trình bày UI, không ghi vào Jetson.”

Không bật/sửa lịch REAL trong demo offline. Không hứa exactly-once physical dispensing qua mọi dạng mất điện: proof hiện có là ledger/request dedupe, chưa là kết quả cơ cấu.

## 3:10–4:00 — Manual DRY RUN, lịch sử và safety

**Thao tác:** ở MOCK bấm “Yêu cầu cho ăn35g — DRY RUN”, mở hộp xác nhận rồi chọn **Hủy**. Sang Lịch sử, chỉ record MANUAL/SCHEDULED bị chặn và bộ lọc.

**Nói:** “Đây là vị trí gửi intent; không phải nút servo. Backend thật giữ request ID qua retry/reload, arbiter kiểm safety. Receipt blocked và target35g không được đổi thành completion. History ghép event ring, occurrence lưu bền và receipt, dedupe cùng request ID.”

“Chế độ an toàn giữ AUTO_FEED/AUTO_WATER false, servo/pump disarmed và outputs0 ở checkpoint đã xác nhận. Khi mất telemetry, app hiện UNKNOWN chứ không tự khẳng định GPIO đang OFF.”

## 4:00–5:00 — HX711 và mục tiêu35g

**Thao tác:** Hệ thống → HX711 → Hiệu chuẩn cân; chỉ checklist0/5/10/20/30/35 và nút bị disable.

**Nói:** “HX711 đọc loadcell; raw đáp ứng không đồng nghĩa gram đã hiệu chuẩn. Host đã có quy trình fit nhiều điểm, verify độc lập và persistence, UI chỉ đọc metadata. Các phép đặt tải trước đây chưa đạt đủ tiêu chí nên gram calibration chưa PHYSICAL_PASS.”

“35g là mục tiêu cấp thêm: khi có closed loop thật, lấy stable_after trừ stable_before. Không suy từ thời gian servo hay coi trọng lượng đang có trong bát là actual dispensed. Hôm nay actual vẫn null/chưa xác minh.”

Không nói candidate fit là active calibration hoặc lấy fixture calibrated để chứng minh cân thật.

## 5:00–5:45 — AUTO_CAT và nước

**Thao tác:** cuộn AUTO CAT rồi Ultrasonic; nếu mất thời gian dùng ảnh `mock_auto_cat_unknown.png`, `mock_timeout_ultrasonic.png`.

**Nói:** “AUTO_CAT là concept/policy: CAT ổn định, đủ gần, cooldown và cân/safety hợp lệ mới tạo request qua arbiter. Backend chưa expose dedicated state thì UI ghi UNKNOWN/NOT_AVAILABLE, không tự suy READY.”

“HC#2 và JSN#2 chưa đấu/test; pins chỉ là đề xuất có RESERVED conflict. AUTO_WATER còn cần geometry, threshold/hysteresis và controlled pump test. Servo/pump hiện chưa có physical pass.”

## 5:45–6:30 — Kết luận và hướng tiếp

**Thao tác:** chỉ status matrix, kết quả regression và checklist phiên sau.

**Nói:** “Checkpoint này là OFFLINE RELEASE CANDIDATE:54 Flutter tests,393 backend offline tests,14 web-client tests, hai bản build và36 ảnh đã kiểm. Một Linux/PTY test chưa chạy trên Windows; hardware không chạy trong phiên này. Các tầng phần mềm, runtime lịch sử và physical được ghi riêng.”

“Bước đầu khi có hardware trở lại là kiểm nguồn/common GND, sau đó enumerate và telemetry. Tiếp theo mới kiểm cảm biến, hiệu chuẩn/persistence và cơ cấu riêng. Chưa tuyên bố tự cấp đúng35g hay servo/pump pass.”

## Câu nói tránh dùng

| Tránh nói | Nói chính xác |
|---|---|
| Máy đã tự cấp35g | Mục tiêu35g; actual dispense chưa xác minh |
| HX711 đã calibrated | Raw đã có evidence; gram calibration chưa đạt đủ verify/persistence |
| Servo/pump đã pass | Software/safety chuẩn bị; motion/flow physical chưa thử đạt |
| Worker chạy là đã cho ăn | Worker đã tạo request DRY RUN; execution vẫn bị chặn |
| MOCK chứng minh sensor đang hoạt động | MOCK chỉ kiểm UI/fixture, REAL dữ liệu thiếu hiện UNKNOWN |

Nếu cần rút còn5phút: bỏ chuyển DOG/NONE và dùng ảnh chụp diagnostics; giữ nguyên phần giới hạn physical và REAL outage.
