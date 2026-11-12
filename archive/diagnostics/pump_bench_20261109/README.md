# Pump thử tay — 09/11/2026

ĐÃ NẠP bản pump-test-only, không bật bơm tự động. App SHA256 677847e499b0b0af5ab8faa701b7c15822f9a8ac7d8c1af9061fd5ee6c3fa78a. Thay bản 6012fe3f5011aca92449dea620ec870b68e67b22a66641aa0fdbb360f027396f sau khi đọc backup flash, kiểm tra app, partition, OTA; write/verify PASS, NVS giữ nguyên.

GPIO7 theo PCB PC817/PMOS HIGH=ON, LOW=OFF. Chỉ thêm pump_bench; servo/cân/ngưỡng mèo/backup giữ nguyên. Mặc định OFF trên boot. pump_test chỉ chạy1000ms; lệnh lặp khi chạy không kéo dài; pump_off, 0, stop, sensors_off tắt ngay. Kiểm thử native biên thời gian, rollover, busy/calibration PASS. Compile399333 bytes chương trình,35896 globals.

Lần thử1 lúc10:26 chưa gửi lệnh bơm: preflight phát hiện exited=0 do USB bridge mở cổng reset ESP32 sau nạp. Lần thử sau gửi0 để tạm dừng cho ăn, xác nhận exited=1/servo_moving=0, rồi gửi đúng một pump_test.

Log10:27:17 START;10:27:18 DONE/OFF sau1000ms;10:27:22 OFF bổ sung. Chưa có xác nhận vật lý bơm quay/nước ra. Người dùng sau đó yêu cầu CHỜ LỆNH của họ rồi mới chạy: tuyệt đối không thử lại tự động. Pump đangOFF, cho ăn vẫn tạm dừng; chưa inspect_ok hoặc xác nhận cửa ĐÓNG sau reboot, không tự bịa mốc.

Người dùng đã xác nhận nguồn bơm đúng, đầu hút có nước và có chỗ hứng trước lượt thử đã thực hiện. Nhưng lệnh chạy tiếp cần họ yêu cầu mới. Chưa chốt mức dừng tự động, chưa đo D1/D2 đầy/cạn. Bản tự động pump_20261109 là ứng viên khác CHƯA NẠP, cần rebase trên firmware thử tay hiện tại nếu phát triển tiếp.

Jetson SSH192.168.123.14 đã kết nối lại. Lúc kiểm tra cả4 siêu âm timeout và HX chưa có raw, không tự retare hoặc bypass cân. AI latest còn timestamp/boot cũ; cần kiểm tra lại khi làm chức năng AI, không xem đó là nhận diện mới.

Source gốc đồng bộ bằng sync_source.py với guard SHA cũ và source_sync.json. Backup nguồn trước thay đổi ở ../pump_20261109/before. Evidence flash/test nằm /home/toan/for_cat/evidence/pump_bench_20261109 và bản local. Không đổi web/API/bridge source. Không coi ACK GPIO là chứng minh có dòng nước.
