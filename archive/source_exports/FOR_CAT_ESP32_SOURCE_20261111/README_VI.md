# Dự phòng mất liên lạc / Jetson mất điện — 11/11/2026

Yêu cầu: ESP32 dùng E1 dưới30cm để mở cửa và dùng loadcell đóng theo mục tiêu35g khi Jetson không liên lạc. Người dùng xác nhận chỉ dùng USB để nạp, nguồn VIN đã tắt; cảm biến/tải sẽ cấp đủ nguồn sau khi nạp, rồi thử UART.

## Đã hoàn tất phần code và nạp

- FallbackGate.h đổi từ2..20cm sang **2 <= E1 <30cm**, yêu cầu3 mẫu mới hợp lệ. Đúng30.0cm không kích hoạt vì yêu cầu lần này là “<30”. Chế độ AI bình thường vẫn <=30cm.
- Không dùng PIR hoặc kết quả AI khi chạy dự phòng. Chặn thêm khi bộ theo dõi bữa ăn đang CAPTURING/OBSERVING, tránh ghi chốt một lượt không thể bắt đầu.
- Giữ heartbeat timeout >15s, bootgrace30s, chén gần0g (±2g), số đo cân mới/hợp lệ, motoridle, không pause/inspection/calibration/DOG alarm.
- Giữ NVS ghi chốt trước khi mở, chống lặp qua reboot; sau một lượt cần cooldown>=5phút và E1>30cm liên tục5s để tái kích hoạt. Không xóa chốt để ép thử.
- Chu trình cấp thức ăn, servo, hệ số cân, kiểm tra ổn định khối lượng và5headerkhác giữ nguyên. Mục tiêu35g; độ chính xác vật lý chưa được chứng minh đúng35.000g.
- Policy và adapter thực trích từ sketch đã kiểm tra đạt: ngưỡng2/20.1/29.9/29.999 được chấp nhận,30/30.01/NaN bị loại; mẫu trùng/cũ, mất heartbeat/bootgrace, scaleinvalid/khôngrỗng, các khóa, mealguard, NVSfault, chống lặp, millisrollover.
- Biên dịch ESP32-S3core3.3.12 đạt:416541byte chương trình,36040byte globals.
- Nạp USB app-only tại0x10000, xác minh đúng baselinea82… và partition/OTA trước ghi, verify-flash đạt; vùng NVS trước/sau ghi giống từng byte. Bridge81c591… không thay đổi.
- Tool dùng `--after no-reset`, không phát lệnh khởi động ứng dụng, không thử servo/pump. Người dùng sẽ rút USB và cấp nguồn riêng để boot/test UART. Chưa xác minh runtime bản mới.

App SHA256 `651cc2ed9a7b601a41d28203bff5c997ffe2676850731cfeadac7d88be619638`.
Source SHA256 `95b3bf627ff9486e6e02480c8956f195b75795c0f03cb92b739b1b719463aedf`.
Canonical `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino` và FallbackGate.h đã đồng bộ.

## Kết nối hiện tại

Jetson đổi DHCP từ192.168.123.14 sang **192.168.123.15**; SSH dùng `server-jetson.local`, keyopencode_jetson, HostKeyAlias192.168.123.13. UART ứng dụng vẫn `/dev/ttyTHS1`, JetsonJ6physical8TX -> ESPRX41; physical10RX <- ESPTX42; physical6GND <-> GND. USB1a86 serial5C85066678 chỉ dùng nạp/nguồn tạm. Rút USB trước bật VINriêng.

Trước nạp, UART từng tươi nhưng cân signed_g=null, backup_wait_clear=true do chốt lượt trước; không thử cấp thức ăn khi cân chưa có dữ liệu. User chọn cấp đủ5V sau nạp. Không lấy lại mốc cân; giữ tare/hệ số trong NVS, lần xác nhận gần nhất tare−700986.7333333333 và g/count−0.000945082600219258.

## Kiểm thử vật lý đang chờ

Owner đã được hỏi: rút USB, cấp đủ nguồn riêng, UART nối đúng, hộp có thức ăn, chén rỗng đúng vị trí, cửa đóng và có người quan sát. Chưa chạy trước khi đủ điều kiện.

`observe_offline.py` là kịch bản chuẩn bị cho thử thật: yêu cầu UART ngoàiUSB, cân±2g, đã bậtbackup, không chốt/cooldown/inspection/mealactive; dừng bridge/API rồi chỉ đọc UART, **không gửi heartbeat/CAT/manual_feed**, quan sát firmware tự offline và cấp35g. Hết bài thử gửiSTOP và bật lại dịch vụ, lưu dữ liệu/log. Cần owner xác nhận quan sát thực tế. Nếu backup_wait_clear=true, giữ E1>30cm đến khi đủcooldown/rearm, không giả xác nhận cửa đóng.

MấtInternet/Wi-Fi không đồng nghĩa mấtUART. Thử mất liên lạc bằng ngừng heartbeat chỉ chứng minh logic dự phòng, không chứng minh nguồn duy trì khi mất điện thật. Thử mất điện thật cần nguồn độc lập còn cấp được ESP32, HX711, E1 và servo khi Jetson tắt.
