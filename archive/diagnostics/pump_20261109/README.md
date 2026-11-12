# Pump — ứng viên ngày 09/11/2026, CHƯA NẠP

Yêu cầu: làm bơm nước, vẫn dùng USB hiện tại. Bản đang chạy chưa thay đổi; source gốc D:/CODE_TEST_LOADCELL_CHUAN/esp32 không sửa. Không dùng lại toàn bộ local_pending_before.ino vì thiếu các cập nhật servo/AI/backup mới.

Ứng viên esp32/esp32.ino lấy từ source SHA256 215e0751b82603b60eb9cd8a7c2ecf6a6a586d9858dd1da37387c160ec640fca, chỉ thêm điều khiển nước GPIO7 và các điểm tích hợp. Hai header CatNearGate.h/FallbackGate.h sao chép nguyên. Servo 1350us900ms/1600us1450ms; hiệu chuẩn HX711 không thay đổi.

## Chưa đủ điều kiện triển khai

- SSH 192.168.123.14 timeout; server-jetson.local không phân giải.
- Chưa có số đo thực D1 đầy/cạn, D2 đầy/cạn. D1 từng timeout, cần kiểm tra lại khi nối được.
- Đang hỏi chủ hệ thống: dưới 50% bơm đến 100% hay chỉ 50%; nguồn pump bao nhiêu V, đã nối qua GPIO7 chưa. Chưa có trả lời tại thời điểm chuẩn bị.
- Chưa xác nhận phần cứng thực PC817/PMOS HIGH=ON, chưa thử pump thật. Giữ ngõ GPIO7 chưa điều khiển đến khi người vận hành xác nhận driver.

## Code ứng viên

- NVS riêng fc_water_v2, không đụng HX711, lịch hoặc dấu dự phòng. Không tái sử dụng các mức nước cũ.
- level_cal D1|D2 full_cm empty_cm: lưu hình học thật; không tự suy từ số đo hiện tại. pump_target percent: hiện chỉ chấp nhận >50 đến100, chờ lựa chọn người dùng trước khi chốt.
- pump_driver_high: chỉ gửi khi đã xác nhận mạch thực HIGH=ON; đưa đầu ra OFF. Không được gửi chỉ dựa trên giả định.
- pump_auto on: chỉ sau khi có driver, NVS, hai hình học, mục tiêu và số đo mới hợp lệ. Mặc định tắt sau mọi lần boot; chưa có tự bật lại sau mất điện.
- D1 dưới50% ở3 mẫu khác nhau, liên tiếp không cách quá1200ms -> bơm. Dừng khi đạt mục tiêu.
- Bình cạn, cảm biến invalid/stale, cấu hình không hợp lệ: dừng. Nếu đang bơm thì chốt lỗi, không tự khởi động lại khi tín hiệu phục hồi.
- Giới hạn một lượt30s -> dừng/chốt lỗi. Thông số này chưa hiệu chỉnh theo bơm/chén thật, không phải kết quả nghiệm thu.
- pump_auto off, pump_reset, stop, 0 và sensors_off đều dừng bơm. pump_reset vẫn để tự động tắt.
- Có telemetry pump_enabled/running/fault/reason/driver_confirmed và bowl_water_percent/tank_water_percent. Backend đang chạy chưa cập nhật các trường mới, cần làm sau khi nối lại.

## Kiểm tra

test_water.py trích các hàm percent/off/disable/tick từ chính ứng viên, kiểm tra biên50%, mẫu lặp, mục tiêu, invalid/stale, bình cạn, timeout, millis rollover, driver chưa xác nhận, lỗi storage, chuỗi mẫu ngắt quãng và không tự chạy lại sau lỗi cảm biến. Kết quả water_test_result.txt. Các mức2/12cm trong test là dữ liệu tổng hợp, KHÔNG phải hình học thật và không lưu lên thiết bị.

Biên dịch firmware lưu tại compile.log/build. Cần xem exit code, không suy thành công từ việc có file log. Không có lệnh flash, thay firmware, hiệu chuẩn hay chạy pump nào được gửi tới phần cứng trong phiên này.

## Tiếp tục

Nhận câu trả lời, kiểm tra kết nối và số đo; chốt driver/điện áp/mức dừng; điều chỉnh và kiểm thử ứng viên; biên dịch, sao lưu flash+NVS và triển khai có kiểm tra hash. Hiệu chuẩn D1/D2 bằng số đo thật. Thử bơm có giám sát rồi mới chốt chế độ tự khởi động. Khi sửa backend, trường nước dự trữ trên web phải là D2; D1 là nước chén, không tráo hai vai trò.
