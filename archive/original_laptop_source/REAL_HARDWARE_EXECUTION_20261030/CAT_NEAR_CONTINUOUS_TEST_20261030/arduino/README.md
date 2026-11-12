# Bản một file cho Arduino IDE

Mở `FOR_CAT_25G/FOR_CAT_25G.ino`. File tự chứa toàn bộ driver và controller,
không cần copy thư mục include hoặc cài thư viện HX711/servo bên ngoài.

Chọn ESP32S3 Dev Module, ESP32 by Espressif Systems 3.3.11, Flash Size 16 MB,
PSRAM Disabled, USB CDC On Boot Disabled, UART0/external USB-UART bridge.
Serial 115200. Dùng partition scheme tương ứng board đã được review.

Điền thông số thực trong `namespace user_settings`. Giá trị 0/false hiện tại
là chưa biết, không phải preset. Calibration NVS được đọc, không tự tare/save.
Nếu calibration chỉ ở RAM, upload/reset có thể làm mất; không restore bằng
offset xấp xỉ đã nói trước đó.

Sketch dùng sender Jetson `jetson/sender.py` và protocol FC1 của project.
Nó không nhận bare CAT như một inference đủ điều kiện. Serial Monitor chỉ
xem telemetry hoặc gửi STOP; không mở đồng thời với sender Jetson.

Đã compile/link bản một file với ESP32 Arduino core 3.3.11 bằng PlatformIO
`arduino_single`: PASS, RAM 31624 B, chương trình 342457 B. Chưa chạy GUI Arduino
IDE/preprocessor Arduino IDE và chưa upload board.

ZIP handoff trước đó được giữ nguyên; file .ino này được tạo sau ZIP.
