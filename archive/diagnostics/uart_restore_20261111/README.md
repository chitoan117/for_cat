# Khôi phục TX/RX UART theo yêu cầu — 11/11/2026

Người dùng báo mất TX/RX rồi xác nhận đã rút USB và chuyển sang UART dây. Bản đang nạp khi đó là USB-UART0 (777…), còn Jetson cũng cấu hình cổng USB; vì vậy cần chuyển **cả firmware lẫn bridge** về UART1 GPIO41/42. Người dùng xác nhận tắt VIN/cắm USB tạm để nạp, sau đó rút USB và bật VIN riêng.

## Đã hoàn tất

- Dùng đúng biến thể UART của firmware cùng logic hiện tại: appSHA **581ba17a013a57db033f6de8ae475527b3c8061917dce6247a13a697a2b0a38f**. So sánh sáu header điều khiển giống từng byte với bản USB777. Đây là đổi transport có chủ đích, không quay về logic bơm/cân/servo cũ.
- UART ứng dụng1152008N1: Jetson J6physical8TX→ESP32GPIO41RX; J6physical10RX←GPIO42TX; J6physical6GND↔GND. USBWCHGPIO43/44 chỉ để nạp trong cấu hình này.
- Xác minh `ttyTHS1` root:dialout0660 và nvgetty/serial-getty không active. Bridge mới mở TTL UART không thao tác modem DTR/RTS; giữ nhánh USB đặt DTR/RTS inactive trước open khi được cấu hình USB. Kiểm thử hai nhánh open bằng đúng hàm trích từ bridge PASS.
- Backupflash, đối chiếu đúng777… trước khi ghi, xác minh partition/OTA, nạp app-only0x10000, đọc/đối chiếu app581… và NVS trước/sau ghi giống từng byte.
- Boot nhận ACKEXIT0, servo_position moving0 và statusJSON quaUART. Giữ waterOff. Không gửi lệnh mở/đóng thử, feed/pump_test hoặc lấy lại mốc cân.
- Drop-in bền `~/.config/systemd/user/for-cat-esp32-bridge.service.d/uart.conf`: `FORCAT_ESP32_PORT=/dev/ttyTHS1`. Không tự dùng USB khi đã chọn UART. nvgetty vẫn tắt.
- Người dùng xác nhận rútUSB/bậtVIN. Bài kiểm tra ngoàiUSB đạt: **20 khung mới khác nhau**, uptime ESP tăng xuyên suốt, cuối128022ms; không reset, không tăng reconnect/badframe. `backup_offline=false` sau bootgrace30s xác nhận ESP nhận heartbeat từ Jetson, không chỉ có chiều ESP→Jetson.
- Chế độ cho ăn bình thường đã khôi phục, backupenabledtrue, waterauto/runningfalse; API/bridge/AI active. Đây là bài kiểm tra giao tiếp ngắn; không khẳng định mọi nguyên nhân UART chập chờn trước đây đã được loại bỏ.

## Trạng thái cảm biến cuối lượt

E1≈65,89cm; E2≈13,75cm; D1≈6,24cm; D2≈19,65cm. Cân signed≈−2,0g. Đã giữ tare−700986.7333333333 và grams/count−0.000945082600219258; **không tự trừ bì** vì lần này không có xác nhận chén rỗng/vị trí cân mới.

Web dự trữ vẫn là bản `reserves_20261111`: thức ăn E2, bình nước D2 luôn độc lập On/OffD1. Mốc cạn lưu trước đó E2=14,06cm dung sai0,3 và D2=20,25cm dung sai0,37; mốc đầy chưa có. Số đo cuối ngoài dung sai mốc cạn, nên phần trăm hiện null/NEEDS_FULL đúng chính sách không bịa%. Không tự dời mốc cạn hoặc tạo mốc đầy để ép0/100%. Khi thực sự đầy, dùng Cài đặt→Mức dự trữ→Lưu đầy từng hộp/bình; muốn lấy lại đáy cần xác nhận cạn thật và vị trí cảm biến.

Servo1350us900ms/1600us1450ms/STOP1500; mục tiêu35g và xác minh ổn định35–40g; khôngPIR; fallback2<=E1<30cm×3/heartbeat15s/bootgrace30s/NVSanti-replay; D1pump5,7cm→5,5cm/10s giữ nguyên. Chưa có bài thử cấp thức ăn/pump hoặc cúp điện thật trong lượt này.

## Source hiện tại

Canonical `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino` SHA **02b6c30d311eca4fbcadec7c8c3eda4153f6e8833b886742d1b24616d8b7c520**, artifact build đồng bộ đúng581…; sáu header không đổi.

Bridge `/home/toan/for_cat/jetson/tools/fc_live_bridge.py` SHA **a68b28e83fcf369c2b2c20767aefe39486604cf8fc69c1118f432c80b401f031**. Giữ toàn bộ linebuffer, SQLiteoutbox, CATfilter và waterdispatcher của bản3760…; chỉ thêm nhánh mở `/dev/ttyTHS*` không điều khiển modemlines.

Jetson192.168.123.15. Backendmain1793…/system_state3447…/reservoir_modules và livewebmainJS59ef40a45169aa5093c14704555e54c4c027b04a2f231ef30ad4892544fbae90 không đổi. Filehiệuchuẩndựtrữ trênJetson được giữ nguyên. USB-return777… bên dưới là lịch sử; không nạp lại khi muốn dùng41/42.

Evidence `/home/toan/for_cat/evidence/uart_restore_20261111`, bao gồm flash/NVS/bridge/unit backups, boot_uart_frame.json, paused_uart.json và external_result.json. Runtime đang chạy qua UART với USB vắng mặt, không bị giữ ở ROM.
