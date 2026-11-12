# Điều khiển nước On / Off — 11/11/2026

Đã triển khai web, backend và nạp firmware ESP32 theo yêu cầu mới của chủ máy. Chế độ nước **mặc định Off**; chỉ bật sau khi người dùng nhấn **On** và xác nhận. **Off** gửi cả `pump_auto off` và `pump_off`, ngừng tự cấp nước và tắt ngõ điều khiển GPIO7. Giữ đọc thô D1/D2 trong vòng cảm biến để kiểm tra trạng thái kết nối; không dùng số đo đó để chạy bơm khi Off. Giao diện theo dõi nước tạm dừng khi Off.

## Logic ESP32 mới

- On: ba mẫu D1 mới, hợp lệ, từ **5,7 cm trở lên** kích hoạt cấp nước. Không có giới hạn trên 6,4 cm của bản cũ.
- Đang bơm: mẫu D1 thô mới đầu tiên **≤ 5,5 cm** làm GPIO7 xuống LOW ngay trong lần xử lý đó, không chờ lọc trung bình hoặc hết thời gian.
- Trong khoảng 5,5–5,7 cm, bơm đã tắt sẽ giữ tắt; bơm đang chạy tiếp tục đến mốc 5,5 cm.
- Bảo vệ: mỗi lượt tối đa **10 giây**; D1 mất/sai/cũ khi đang bơm hoặc quá thời gian thì tắt và giữ lỗi. Cần Off rồi On có xác nhận để thử lại, không tự lặp sau lỗi.
- Khởi động ESP32/API, UART nối lại hoặc ESP32 reboot không tự bật chế độ nước. Không lưu lệnh enable để phát lại sau restart. API chỉ cho bật khi firmware báo đúng chính sách 5,7/5,5/10000.
- Không đổi servo, loadcell, trừ bì, mục tiêu cho ăn35g, UART41/42, PIRđãbỏ hoặc dự phòng E1<30cm. Năm header không liên quan giữ nguyên từng byte.
- Ngắt điện motor **không chặn dòng nước tự chảy do xi phông**. Vấn đề đường ống đã được người dùng nêu vẫn cần xử lý cơ khí trước khi dùng tự động; firmware không thể khóa dòng nước bằng phần mềm.

## Dùng trên Desktop Jetson khi mất Internet

Mở biểu tượng FOR_CAT đang có, hoặc Chromium tại `http://127.0.0.1:8000/app`. Trong **Tổng quan → Chức năng nước** có hai nút **On / Off**. On hiện hộp xác nhận; Off không yêu cầu xác nhận. Backend và UART hoạt động nội bộ, không cần Internet/Tailscale. Jetson và ESP32 vẫn phải có nguồn và UART còn kết nối. Nếu còn giao diện cũ, tải lại trang.

## Đã kiểm tra

- Gate C++ chạy trực tiếp trên Jetson: mặc định Off, bật có điều kiện, biên5,7/5,5, ngắt ở mẫu đích đầu tiên, hysteresis, mẫu trùng, Off khi đang chạy, dữ liệu sai/cũ, timeout10s, millisrollover: PASS.
- 10 kiểm thử Python API/dispatcher với SQLite tạm và serial giả: PASS; yêu cầu xác nhận, dữ liệu mới, không coi queued là enabled, hủy/ưu tiên Off, hết hạn, không phát lại enable, đổi boot, từ chối firmware ngưỡng cũ.
- Flutter:27 kiểm thử UI/offline ban đầu và4 kiểm thử nước cuối cùng: PASS. Analyzer không có lỗi; build REAL, basehref `/flutter/`, CanvasKit/font được phục vụ cục bộ.
- Nạp USB app-only tại0x10000, xác minh firmware baseline651… trước ghi và đọc lại bản mới: PASS. Vùng NVS trước/sau ghi giống từng byte. Tare **−700986.7333333333**, g/count **−0.000945082600219258** giữ nguyên.
- Runtime khởi động qua UART xác nhận `pump_on_cm=5.7`, `pump_off_cm=5.5`, `pump_max_run_ms=10000`, auto/running=false.
- Khôi phục chế độ cho ăn bình thường và backup_enabled=true như trước nạp.
- Chủ máy xác nhận rút USB và bật nguồn VIN riêng. Kiểm tra USB thực sự vắng,8 khung UART mới khác nhau, API chính sách mới hợp lệ, request DISABLE/APPLIED, nước Off và motoroff: PASS. D1 lúc kiểm tra cuối6,28cm; không hiệu chỉnh số đo để khớp mốc người dùng nêu.
- Giao diện thật:1024×600, nút On/Off hiện đủ; mở hộp xác nhận rồi Hủy, nhấn Off và nhận xác nhận từ ESP32. Ảnh `on_off_jetson.jpg`.
- **Chưa chạy bơm thực tế bằng nút On trong bài triển khai này.** Không có lệnh pump_auto on/pump_test/pump_fill phát tới thiết bị thật. Độ chính xác mực nước và thời gian dòng chảy dừng chưa được đo kiểm.

## Source và bản triển khai

- Canonical ESP32: `D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino`, các header cùng thư mục; đã đồng bộ source và artifact bản nạp.
- App SHA256: `581ba17a013a57db033f6de8ae475527b3c8061917dce6247a13a697a2b0a38f`.
- Sketch SHA256: `02b6c30d311eca4fbcadec7c8c3eda4153f6e8833b886742d1b24616d8b7c520`.
- D1PumpGate.h SHA256: `5ac73541050d5fe546d217b95ab2bc2a2a49aac61c2ac54f567c2d4a36bb8547`.
- Flutter source: `D:/DA_KT_NC/feeder_demo`. Thay đổi hiện tại có bản chụp tại `frontend/`.
- Jetson192.168.123.15, source `/home/toan/for_cat/jetson`. BridgeSHA `abaf48106e5d5ad532e4518421bc0a811adb44be7e51706c94d29a6ebddef00c`; modulewaterSHA `7d561e97743604aaddd7942d7c3243e8e124082db1a7a8844885f4169d72fd85`; API mainSHA `4f6bd9f0824494e31caa9c67096e1dcaeec1fe7f425f18df599bee771764d82d`; water_routesSHA `3f30d420ed195b9d902cfd62e875ace08b93e67956bb5e169f059ad568ea2c58`.
- Web live `/home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2`, mainJS SHA `3e9593cdaf52a0381fa75ab18df34277973896944d33e7f3ceefa019e85ffbe4`. Releasewater55_20261111. Bản trước được giữ tại `.before_water55_20261111` cùng thư mục cha.
- Ba user service API/bridge/AI active. Evidence runtime/flash/deployment/external JSON được lưu tại đây và `/home/toan/for_cat/evidence/water55_20261111`.

Các ZIP báo cáo/source trước bản này là lịch sử; không nạp lại651… hoặc khôi phục bridge81…/d18… để tránh mất tính năng mới. Không chạy lại script triển khai nếu backup đã tồn tại; đối chiếu trạng thái/hashes trước.
