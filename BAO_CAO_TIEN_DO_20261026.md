# BÁO CÁO TIẾN ĐỘ DỰ ÁN MÁY CHO MÈO ĂN

**Checkpoint: 26/10/2026**

## 1. Kết luận tổng quan

Dự án đã đạt mốc tích hợp dữ liệu phần cứng thật từ ESP32 và AI C++ trên Jetson
lên giao diện Flutter. Các yêu cầu MANUAL và SCHEDULED preview đi qua cùng một
arbiter, có nhận dạng request và kết quả DRY RUN. Meal Plan đã lưu bền và thao tác
được trên giao diện. Truy cập LAN và tự khởi động dịch vụ đã được xử lý.

Mục tiêu cấp **35 g thức ăn thực tế mỗi lần** vẫn ở giai đoạn chuẩn bị: HX711
chưa hiệu chuẩn gram; chưa xác minh servo cấp đủ 35 g hoặc pump điều khiển nước.

**Mốc hiện tại:** REAL integration + Meal Plan CRUD + explicit SCHEDULED preview.
**Hạng mục kế tiếp đã đề xuất, chưa triển khai:** worker tự xét lịch đến hạn ở
chế độ DRY RUN. Hiện việc xét lịch vẫn cần bấm nút preview.

## 2. Những phần đã hoàn thành

### 2.1. Luồng tích hợp REAL

ESP32 -> USB Serial -> một C++ bridge -> SQLite dùng chung -> backend FastAPI
hiện có -> REST/WebSocket -> Flutter /kiosk và /app.

AI dùng chương trình C++ OpenCV/TensorRT hiện có; passive state tap đưa kết quả
vào cùng SQLite/SystemState. Mã, binary và engine AI được bảo toàn. Không có
backend/camera/serial reader cạnh tranh được tạo thêm cho giao diện.

- Đọc, kiểm tra và giới hạn telemetry; phát hiện dữ liệu sai/quá dài/stale.
- Kết nối lại serial, phân biệt thiết bị mất kết nối với dữ liệu cũ.
- Provider REAL dùng giá trị thật hoặc UNKNOWN/null/STALE.
- Giao diện cập nhật WebSocket, ẩn số cũ khi mất kết nối và tự phục hồi.
- Một cơ sở dữ liệu chuẩn; schema user_version=2 được giữ, các bảng bổ sung là additive.

### 2.2. AI

- Camera USB và pipeline TensorRT C++ đã chạy, kết quả CAT/DOG/NONE được tích hợp.
- Có bằng chứng live và xác nhận trước đó của người dùng về camera/AI.
- Chưa có chứng nhận độ chính xác theo từng lớp trong một bộ thử chuẩn mới.
- EATING/consumed grams chưa được xác nhận trên phần cứng vì thiếu gram hiệu chuẩn.

### 2.3. Phần cứng cơ bản

| Hạng mục | Trạng thái được ghi nhận | Giới hạn hiện tại |
|---|---|---|
| OLED 0x3C | Đã xác nhận hoạt động | Tiếp tục theo dõi lỗi phát sinh |
| PIR GPIO11 | Đã xác nhận tín hiệu thật | Không thay cho điều kiện CAT_NEAR |
| HX711 GPIO4/5 | Raw/đáp ứng tải đã kiểm tra | Gram calibration DEFERRED |
| HC-SR04 #1 GPIO12/13 | Raw ranging đã xác nhận | Chưa chốt ngưỡng tiếp cận production/độ chính xác chuẩn |
| JSN #1 GPIO14/15 | Có dữ liệu thật; người dùng chấp nhận basic ranging cho bố trí/quy mô khoảng 25 cm | Timeout/số nhảy vẫn lưu trong log; chưa hiệu chuẩn hình học/ngưỡng nước |
| Button GPIO21 | Người dùng xác nhận nhấn nhanh tăng đúng một lần, giữ 5 giây không lặp, thả không tăng | PASS diagnostic input, chưa là PASS cấp thức ăn |
| Cảm biến kho #2 | NOT_WIRED, GPIO TBD | Phần trăm kho để null |
| Servo/pump | Chưa xác minh vận hành thật | Arm/AUTO/output enable vẫn khóa |

Các Echo ACK có thể mất sau MCU reboot. Helper sensor-only hiện có đã khôi phục
thu nhận trong các phiên cần thiết, với đúng hai lệnh xác nhận cố định. ACK
không được diễn giải thành phép đo điện áp hay hiệu chuẩn khoảng cách.

### 2.4. Flutter

- Giữ thiết kế cam/xanh và năm tab của nguồn người dùng.
- REAL mặc định; MOCK là chế độ phát triển được chọn rõ ràng.
- Thông tin AI, HX raw, trạng thái cảm biến/thiết bị lấy từ backend thật.
- Gram chưa hiệu chuẩn và tồn kho chưa đấu nối hiển thị null/không có giá trị.
- MANUAL có xác nhận DRY RUN, ID lưu trước POST, khóa khi đang gửi, retry cùng ID
  khi kết quả chưa rõ; khôi phục pending bằng GET sau reload.
- Lịch sử phân biệt event DRY RUN với một lần cấp thức ăn hoàn tất.

### 2.5. Meal Plan và arbiter

- Tạo/sửa/xóa/tải lại Meal Plan lưu trên SQLite Jetson.
- Giờ Việt Nam UTC+7, chọn ngày trong tuần, target cố định 35 g.
- Lịch mới mặc định tắt; kiểm tra revision chống ghi đè thay đổi cũ.
- Giới hạn 32 lịch active và 256 identity gồm tombstone; ID đã xóa không bị stale POST tạo lại.
- Explicit SCHEDULED preview kiểm tra TIME_VALID, ngày/giờ, kết nối và trạng thái an toàn.
- Cửa sổ đến hạn 60 giây; bỏ bữa đã lỡ, không chạy bù hàng loạt.
- Cùng due-instance tạo cùng request ID, đi qua C++ arbiter hiện có.
- Đã thử thực tế: lặp preview cùng lượt -> một inbox row và một arbiter event.
- Kết quả hiện tại là DRY_RUN_BLOCKED / UNATTENDED_SAFE_MODE / WEIGHT_NOT_CALIBRATED.

**Chưa có worker tự chạy lịch.** Cờ enabled hiện chỉ cho phép xét bằng nút preview.
AUTO_CAT temporal gate, behavior FSM và water fail-safe đã có phần chuẩn bị phần
mềm/dry-run; production near/water thresholds chưa được xác lập.

## 3. Truy cập và khởi động

- App: http://server-jetson.local:8000/app
- Kiosk: http://server-jetson.local:8000/kiosk
- Chẩn đoán: http://server-jetson.local:8000/diagnostics
- IPv4 quan sát gần nhất: 192.168.123.8.

Lỗi timeout trong ảnh xuất hiện ở địa chỉ mạng cũ 192.168.137.59; sau reboot ba
service cũng đang dừng vì trước đó chưa boot-enabled. Đã khôi phục dịch vụ,
bật enabled cho API/bridge/AI và Linger=yes. Windows HTTP200 và Chromium thật
đã xác minh REAL REST/WS tại hostname .local. Đã kiểm tra cấu hình enabled/active;
chưa thực hiện thêm một cold reboot riêng để xác nhận chu kỳ boot mới.

## 4. Kiểm thử và giám sát

| Kiểm tra | Kết quả |
|---|---|
| Backend trên Jetson | 369 tests PASS ở release Meal Plan |
| Flutter trên Windows | Analyze không có issue; 25 tests PASS; build release PASS |
| Chromium thật | CRUD lịch, đọc lại giữa kiosk/app, SCHEDULED preview, chống trùng và lịch sử DRY RUN đạt |
| Truy cập LAN sau khôi phục | App/kiosk/API HTTP200 từ Windows; REAL WS trên hostname .local đạt |
| Watcher dừng bình thường/SIGTERM | COMPLETED và INTERRUPTED FINAL được ghi đúng trong hai phép thử Linux |

Quan sát qua đêm có 7 giờ 48 phút 30 giây, 938 mẫu định kỳ, 937 lần API thành
công. Trong 937 lần đọc được, ESP32 và AI đều báo kết nối. Một lần lỗi API trùng
lúc triển khai lại backend. HC có 19 và JSN có 16 mẫu khoảng cách hợp lệ; phần
còn lại chủ yếu invalid/null. Đây không phải phép đo mọi xung siêu âm.

Không có FINAL.json của phiên cũ nên kết luận **INCOMPLETE**, không ghi đủ 8 giờ
PASS. Nguyên nhân dừng chính xác chưa xác định từ journal cũ. Đã cải thiện
watcher để lưu INTERRUPTED khi nhận SIGTERM/SIGINT; mất điện đột ngột vẫn có
thể ngăn final write. File báo cáo cũ được giữ nguyên.

## 5. Việc còn lại theo ưu tiên

1. Worker SCHEDULED DRY RUN: tự xét lịch đúng giờ trong backend hiện có, chống
   trùng qua restart, TIME_VALID, bỏ missed window và có trạng thái trên app.
2. Hiệu chuẩn HX711 khi có quả cân; kiểm tra lặp lại, reference 20+10+5=35 g.
3. Thử servo cấp thực tế có người giám sát và quyền vận hành phần cứng rõ ràng;
   dùng delta khối lượng ổn định sau-trước để xác minh target 35 g.
4. Hoàn thiện AUTO_CAT với ngưỡng tiếp cận và xác nhận theo thời gian từ thử nghiệm thật.
5. Xác lập hình học/ngưỡng nước LOW/TARGET rồi thử pump có kiểm soát.
6. Kiểm thử kịch bản demo đầu-cuối và phục hồi lỗi sau khi các điều kiện trên đạt.

## 6. Vị trí mã và hồ sơ

- Nguồn Flutter chính: D:/DA_KT_NC/feeder_demo.
- Repo Jetson: /home/toan/for_cat; snapshot Flutter: frontend/feeder_demo.
- Hướng dẫn: docs/MEAL_PLANS.md, docs/LAN_STARTUP.md, docs/FLUTTER_FRONTEND.md.
- Release/kiểm thử Meal Plan: D:/for_cat/OVERNIGHT_MEAL_PLAN_20261025.
- Khôi phục mạng và review qua đêm: D:/for_cat/NETWORK_BOOT_RECOVERY_20261026.
- Trạng thái chuẩn: config/hardware_current.json và docs/CURRENT_PROJECT_STATE.md.

36 file staged và index gốc cùng các thành phần AI được bảo toàn. Các thay đổi
phần mềm gần đây không flash ESP32, không thay NVS/pin và không vận hành actuator.
