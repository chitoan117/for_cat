# Chuyển lại giao tiếp USB — 11/11/2026

Chủ máy yêu cầu chuyển từ UART dây GPIO41/42 sang USB vì chập chờn; đã xác nhận tắt nguồn VIN riêng và ESP32 chỉ nhận nguồn USB Jetson. UART cũ có probe12s không nhận byte; chưa xác định nguyên nhân vật lý. Không kết luận lỗi UART đã được sửa.

## Đã nạp và chạy

- Chỉ đổi transport của sketch từ HardwareSerial1 RX41/TX42 sang **HardwareSerial0 RX44/TX43**, qua chip WCHUSB–UART trên bo. Sáu header cân/servo/bơm/fallback/meal giữ nguyên từng byte.
- Giữ USB CDC On Boot disabled; không dùng USBnative GPIO19/20 vì GPIO19 đang là ECHO của D2.
- Bridge dùng cổng bền `/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00` ở1152008N1. Userdrop-in `~/.config/systemd/user/for-cat-esp32-bridge.service.d/uart.conf` được đổi sangUSB và lưu backup. Không tự chọn camera/USB khác khi cổng này vắng.
- Đặt DTR/RTS inactive **trước khi mở cổng**, hạn chế reset do thao tác mở lại USB. Không bậtgetty/UARTconsole.
- Flash app-only0x10000, kiểm tra đúng baseline581… trước ghi, partition/OTA, đọc/đối chiếu app mới và NVS trước/sau ghi giống từng byte.
- BootUSB nhận ACKEXIT0, phản hồi servo_position moving0 và statusJSON thực tế. Giữ tare−700986.7333333333, g/count−0.000945082600219258, servo1350us900ms/1600us1450ms, pump5,7→5,5cm/10s, khôngPIR, backupE1<30cm/35g.
- Khôi phục `start`, backupenabledtrue, pumpauto/runningfalse. Đã theo dõi **16 khung mới liên tiếp**, thời gian ESP tăng liên tục,0reconnect/0badframe. Đây là bài kiểm tra ngắn, không phải bằng chứng loại bỏ mọi vấn đề nguồn hoặc mất kết nối lâu dài.
- Không thử motor, pump, cấp thức ăn hoặc sửa mốc cân. Người dùng để nguồn cảm biến tắt, nên cảm biến/cân chưa có dữ liệu và cần thử sau khi cấp nguồn.

## Source hiện tại

App SHA `7772a44d49ce8546c766fce4bac918390f85e80870a6e7cdf414726b19b977b3`.

Canonical sketch `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino`, SHA `945c87d70dcc0060ab7734e3c0d4a93aa1111617e88ec0a34e55cc28f826989d`. Source và artifact build chính đã đồng bộ. Các sourceZIP/bảnUART trước đó là lịch sử, không nạp lại để tránh lệch cổng.

Bridge `/home/toan/for_cat/jetson/tools/fc_live_bridge.py`, SHA `3760de86108f51500a1b3a2c0ca05592a7770d6c24685e6fc55c01e7ad59e2ba`. Giữ toàn bộ UARTlinebuffer/storage/outbox/CATfilter/waterdispatcher trước đó, chỉ đổi mở cổng modemlines và port cấu hình. RX41/TX42 không còn là đường ứng dụng trong bản này.

ESP32 hiện lấy nguồn USB từ Jetson. Firmware fallback vẫn có, nhưng khi Jetson mất nguồn làm USB mất điện thì ESP32 cũng mất nguồn nếu không có giải pháp dự phòng riêng. Không đấu đồng thời VIN5V và nguồnUSB hiện tại; thay đổi cách cấp nguồn/USBdata-only cần đối chiếu mạch thực tế. Chưa thử cúp điện thật.

Evidence `/home/toan/for_cat/evidence/usb_return_20261111`; backupflash/NVS/bridge/uart.conf và runtimeJSON lưu tại đó. `restore_and_verify.py` ghi kết quả khôi phục chế độ và kiểm tra16frames. Bản web/E2/D2 đi kèm ở `../reserves_20261111/README.md`.
