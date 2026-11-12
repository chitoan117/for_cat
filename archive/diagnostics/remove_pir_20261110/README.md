# Bỏ cảm biến chuyển động PIR — 10/11/2026

Đã hoàn tất theo yêu cầu người dùng: firmware được nạp, backend và web đã triển khai, nguồn VIN riêng/UART được xác minh sau khi rút USB. Không còn khởi tạo hoặc đọc GPIO11 trong ứng dụng đang dùng.

- Bình thường: giữ nguyên nhận diện CAT + E1 ≤30 cm và các kiểm tra cân/khóa hiện có.
- Dự phòng khi mất heartbeat Jetson: E1 hợp lệ 2..20 cm qua 3 mẫu mới, cân chén rỗng trong ±2 g và các điều kiện idle/không pause/không lỗi. Bỏ hoàn toàn điều kiện PIR HIGH và mốc thời gian PIR.
- Chống cấp lặp giữ nguyên: chốt lưu NVS trước khi mở, thời gian chờ ≥5 phút; E1 >30 cm liên tục 5 giây mới đủ điều kiện tái kích hoạt. Không cần PIR LOW nữa.
- Giữ nguyên trễ xác nhận mất Jetson 15 giây, chờ 30 giây sau khởi động, servo mở 1350 µs/900 ms, đóng 1600 µs/1450 ms, phần cân/khẩu phần 35 g và kiểm tra ổn định sau đóng.
- Telemetry giữ trường tương thích `motion:null`, thêm `pir_configured:false`. Bridge không biến mức chuyển động cũ thành cảm biến đang lắp; trả `configured:false`, `health:NOT_CONFIGURED`, giá trị và số lần chuyển mức null.
- Web bỏ thẻ PIR trong trang chẩn đoán; mock bỏ cảm biến PIR. Các lịch sử kiểm thử A/B vẫn được ghi rõ là kiểm thử bằng tay.

## Kiểm chứng

- Logic độc lập và adapter dự phòng lấy trực tiếp từ sketch: đạt. Bao gồm biên 2/20 cm, 3 mẫu khác nhau, mẫu lặp/cũ/lỗi/NaN, mất host, cân không rỗng, pause, chống lặp, tái kích hoạt, tràn millis, lưu trước chuyển động và lỗi lưu NVS.
- 1 kiểm tra bridge bỏ PIR + 5 kiểm tra UART: đạt.
- Firmware Arduino ESP32-S3 biên dịch đạt, 416533 byte chương trình, 36040 byte biến toàn cục.
- Flutter analyze đạt; 34 kiểm tra hiện có về mock/offline và lịch sử A/B đạt; release build dùng CanvasKit/font nội bộ đạt.
- Sao lưu ứng dụng UART cũ ba99157d…, xác minh chỉ ghi app tại 0x10000, readback đạt, NVS trước/sau ghi giống từng byte. Tare −700653.3333333334 và g/count −0.000945082600219258 không đổi. Không trừ bì.
- Nhận ACK STOP, phản hồi trạng thái servo và JSON `pir_configured:false` trực tiếp qua ttyTHS1.
- Sau khi người dùng rút USB và bật lại VIN: 10 khung mới trong 20 giây, không reconnect, cân và cả 4 siêu âm trả dữ liệu, kiểm tra pause/resume hai chiều đạt, web HTTP200. Đã khôi phục chế độ tự động bằng `start`.
- Không gửi lệnh chạy thử servo/pump hoặc `inspect_ok`; chưa thực hiện một lượt cho ăn hay thử mất điện thật trong tác vụ này.

## Bản hiện tại

- App SHA256 `a82c6cb442321b98cdfc21f8b7891deb4aa0d92585fe696672e0b9bae8f1e0d9`.
- Source SHA256 `5f0aece2ec8e317a88037dee3f22b734aa57b578a3302aa38916a0f49ac4b887`.
- Bridge SHA256 `8db8cd73a0899b02768aca81610e27485b8c7f35926903c5b6f84cc3db1eb034`.
- Web main SHA256 `b6e2ba1f30c88b6b0de50a63141ee01378c288bb0492af1f6def6d4c3d3eae13`.
- Source chính `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino` và `FallbackGate.h` đã đồng bộ sau xác minh nạp. Năm header còn lại giống bản trước từng byte.
- Source web chính `D:/DA_KT_NC/feeder_demo/lib/diagnostics_page.dart`, `mock_backend.dart` đã cập nhật.
- Remote `/home/toan/for_cat/evidence/remove_pir_20261110`; bridge thực `/home/toan/for_cat/jetson/tools/fc_live_bridge.py`. UART1 vẫn RX41/TX42, 115200 8N1, Jetson ttyTHS1.
- Backup web `/home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2.before_remove_pir_20261110`.

Lần đo cuối: cân +0,88 g; E1 39,67 cm, E2 13,77 cm, D1 9,96 cm, D2 26,84 cm. Đây là ảnh chụp trạng thái, không phải mốc hiệu chuẩn mới. Các tài liệu lịch sử và mã generic cũ có thể vẫn nhắc PIR; không dùng chúng để nạp đè bản hiện tại.
