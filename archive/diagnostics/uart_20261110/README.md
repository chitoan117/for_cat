# Chuyển giao tiếp Jetson–ESP32 sang UART — 10/11/2026

Đã nạp firmware UART1, rút USB, cấp nguồn VIN riêng và xác minh hai chiều trên `/dev/ttyTHS1`. Người dùng xác nhận đã rút USB và bật nguồn riêng; kiểm tra độc lập trên Jetson cũng xác nhận USB vắng mặt và UART còn dữ liệu mới.

| Jetson Nano 2GB, J6 | ESP32-S3 |
|---|---|
| Chân vật lý 8, TX | GPIO41, RX UART1 |
| Chân vật lý 10, RX | GPIO42, TX UART1 |
| Chân vật lý 6, GND | GND |

115200 baud, 8N1, không flow control. GPIO43/44 dành lại cho UART0/USB–UART để nạp. Dây tín hiệu UART dùng mức 3,3 V. ESP32 nhận nguồn 5 V riêng tại VIN/5V và GND khi đã rút USB lập trình; không đưa 5 V vào GPIO.

## Đã xác minh

- User chạy root setup: tắt `nvgetty.service`, quyền `root:dialout 0660` cho `ttyTHS1`; udev rule lưu để áp dụng lại khi khởi động.
- Firmware biên dịch đạt; 5 kiểm tra cầu nối đạt, bao gồm không tự chuyển về USB khi đã cấu hình UART nhưng UART vắng mặt.
- Sao lưu flash, đối chiếu đúng ứng dụng cũ `e179a8cc…`, bảng phân vùng và OTA; chỉ ghi ứng dụng tại `0x10000`.
- Đọc/đối chiếu bản nạp đạt; vùng NVS trước/sau ghi giống từng byte.
- Nhận ACK `EXIT 0`, phản hồi `SERVO ESTIMATE ... moving=0`, và status JSON thực tế qua `ttyTHS1`.
- Giữ nguyên tare `-700653.3333333334`, g/count `-0.000945082600219258`, servo mở 1350 µs/900 ms, đóng 1600 µs/1450 ms. Sáu header điều khiển giữ nguyên.
- Bridge thực tế có cả các sửa camera/CAT gate và SQLite outbox trước đó; chỉ thêm lựa chọn cổng và bỏ thao tác modem DTR/RTS trên UART Jetson.

App SHA256: `ba99157def49160152f3b83a20db11b70e1c4f77057c0b49a7758608a9065f8d`.

Source SHA256: `be5aceea12743f4a77a5a14fa8920b9bd25a90072c934f7f9947ccc166af37bc`.

Bridge SHA256: `2d7160e9e15de76dc34647c24471ace22e06409aaae77c19ade18b7702742c85`.

Source chính đã đồng bộ: `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino`.

## Kết quả nguồn riêng, không USB

API, AI và bridge đang chạy và đều enabled. `Linger=yes`; `nvgetty` disabled; udev rule và user drop-in lưu bền. Bridge có `for-cat-esp32-bridge.service.d/uart.conf`, `FORCAT_ESP32_PORT=/dev/ttyTHS1`.

`verify_external.py` đạt: USB thật sự vắng mặt, 20 khung UART mới trong 20 giây, không reconnect, cân có dữ liệu, mốc cân không đổi, phản hồi hai chiều qua chuyển pause/resume và HTTP `/app` 200. Đã gửi `start` để khôi phục chế độ tự động trước cập nhật. Không gửi lệnh thử servo/pump hay `inspect_ok`, không trừ bì. Không khẳng định cửa vật lý đã đóng chỉ từ trạng thái phần mềm. Không có bài thử cúp điện toàn bộ hệ thống hoặc một lượt cho ăn trong quy trình này.

Tại lần kiểm tra cuối: E1 50,76 cm; E2 13,72 cm; D1 6,6 cm; D2 27,7 cm; cân −2,05 g. Mốc và hệ số cân lưu bền đúng bản trước nạp; không tự trừ bì vì chưa xác nhận chén rỗng ở trạng thái mới. Lần kiểm tra đầu tiên ngay sau rút USB chưa có dữ liệu (chờ bật VIN); chạy lại sau xác nhận nguồn riêng đã đạt.

Remote evidence: `/home/toan/for_cat/evidence/uart_20261110`. `deploy_uart.py` lưu backup/boot/readback/NVS và tự khôi phục cả firmware USB lẫn bridge cũ nếu kiểm tra UART sau nạp thất bại.

Các metadata cũ tên JSN/D2 echo10 trong cầu nối chưa sửa trong tác vụ chuyển UART; chân native D2 vẫn là 18/19. Không dùng metadata legacy để đấu dây.
