# SOURCE ESP32 HIỆN TẠI — 10/11/2026

Mở `esp32/esp32.ino` bằng Arduino IDE, hoặc mở cả thư mục ESP32 trong VS Code. Giữ sáu file `.h` cùng thư mục với `.ino`.

## Các file chính

- esp32.ino: firmware tích hợp, đọc cảm biến, HX711/OLED, UART, servo, pump, lịch nhận từ Jetson và chu trình cấp thức ăn.
- CatNearGate.h: cửa sổ xác nhận khoảng cách mèo đến gần.
- FallbackGate.h: chính sách dự phòng khi Jetson mất heartbeat; hiện đã bỏ PIR.
- PortionSettleGate.h: kiểm tra khối lượng ổn định sau khi đóng cửa.
- MealPreferenceGate.h: theo dõi lượng thức ăn giảm và phân loại kết quả món A/B.
- D1PumpGate.h và PumpFill59Gate.h: logic bơm theo cảm biến D1, chạy giới hạn và tự ngắt.

## Phiên bản này

- UART1: RX GPIO41, TX GPIO42, 115200 baud, 8N1. Jetson J6 chân8 TX → GPIO41; chân10 RX ← GPIO42; chân6 GND ↔ GND.
- Bỏ PIR; GPIO11 không sử dụng.
- Bình thường giữ CAT + E1 ≤30 cm. Dự phòng giữ E1 hợp lệ 2..20 cm qua3 mẫu mới, cân chén rỗng và các khóa hiện có; không còn cần PIR.
- Khẩu phần mục tiêu35 g. Servo mở1350 µs/900 ms, đóng1600 µs/1450 ms, dừng1500 µs. Đóng theo thời gian; không có phản hồi vị trí.
- E1 TRIG12/ECHO13; E2 16/17; D1 14/15; D2 18/19; HX711 DOUT4/SCK5; OLED SDA8/SCL9; servo6; pump7 HIGH bật; nút21; buzzer2 activeLOW.

## Biên dịch

Board ESP32-S3, Arduino ESP32 core3.3.12, flash4MB, PSRAM disabled, USB CDC On Boot disabled vì GPIO19 dùng cho D2. Thư viện Adafruit SSD1306 và Adafruit GFX cần có trong Arduino libraries; phần PWM servo và HX711 được triển khai trong sketch. Xem các `#include` ở đầu sketch để đối chiếu thư viện.

`firmware/` kèm các binary đã biên dịch của bản đang dùng để lưu trữ. Không tự ghi toàn chip chỉ vì có các file này; quy trình cập nhật hiện tại chỉ ghi app và giữ NVS. UART1 dùng giao tiếp ứng dụng, USB-UART dành để nạp.

Mốc0/hệ số cân được lưu trong NVS của ESP32, không phải toàn bộ trạng thái NVS nằm trong source. Lần lưu mốc gần nhất đã xác nhận: tare −700986.7333333333, g/count −0.000945082600219258. Đây là thông số của bộ cân đang lắp, không tự áp dụng cho bo/cân khác.

Source và binary đúng bản đã nạp bỏ PIR. Các lần kiểm tra trước có dao động cân và gián đoạn UART/ESP32 khởi động lại; gói source không có nghĩa các vấn đề phần cứng đó đã được xử lý xong.
