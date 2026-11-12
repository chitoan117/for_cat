# E2 / D2 theo dõi dự trữ độc lập — 11/11/2026

Đã triển khai backend và web thật trên Jetson. Người dùng yêu cầu D2 luôn theo dõi bình nước, E2 theo dõi hộp thức ăn, nút On/Off chỉ dành cho D1 và pump ngoài chén.

## Đã sửa

- Phát hiện `app/system_state.py` dùng nhầm `JSN_SR04T_1` (thực tế D1, chén nước) làm thức ăn dự trữ, tính theo mốc mặc định5–35cm nên cho khoảng97% khi D1 gần6cm. Đã bỏ cách tính và các mốc mặc định này.
- Thức ăn dùng **E2**, khóa protocollegacy `HC_SR04_2`, chân native16/17. Nước dự trữ dùng **D2**, khóa legacy `JSN_SR04T_2`, chân native18/19. D1 không thay thế E2/D2 khi mất số đo.
- Hai ô dự trữ không đọc `waterControl.enabled` nữa; D2 vẫn hiển thị khi chức năng bơm Off. Hết nhãn “Tạm dừng theo dõi nước” trên ô bình dự trữ.
- Card On/Off đổi tên **Cấp nước chén**. Chỉ hiển thị số đo D1 khi bật; chức năng bơm vẫn mặc định Off, xác nhận trước On,5,7cm bắt đầu/5,5cm dừng,10s bảo vệ như bản trước.
- Theo người dùng xác nhận cả hai đang ở đáy/cạn, đã thu11 cặp mẫu thật trước khi chuyển USB: **E2 đáy14,06cm**, dung sai0,3cm; **D2 đáy20,25cm**, dung sai0,37cm. Lưu bền tại `/home/toan/for_cat/jetson/data/reservoir_calibration.json`; có số đo cạn hợp lệ thì hiển thị0%.
- **Chưa có mốc đầy thật, không tự gán số cm.** Nếu có vật liệu cao hơn đáy nhưng chưa lưu đầy thì phần trăm chưa xác định; UI ghi “Cần lưu mức đầy”. Khi đầy, vào **Cài đặt → Mức dự trữ → Lưu đầy thức ăn / Lưu đầy nước**, xác nhận rồi lấy5 mẫu mới riêng từng cảm biến. Từ chối mẫu nhiễu hoặc mốc còn gần đáy. Sau khi có hai mốc, phần trăm được nội suy theo chiều cao mức chứa, không phải khối lượng/thể tích chính xác.
- Cảm biến timeout/cũ/không nguồn luôn hiển thị “Chưa có dữ liệu” và percent=null, không hiện số cũ/0% giả.

## Trạng thái thực tế cuối lượt

Trong lúc sửa, UART cũ mất dữ liệu; probe12s không nhận byte nào dù người dùng báo OLED còn sáng. Người dùng yêu cầu đổi về USB và xác nhận tắt VIN ESP32, cắm USB vào Jetson. Đã nạp bản USB-UART0; xem `../usb_return_20261111/README.md`.

Người dùng xác nhận **chưa cấp nguồn cảm biến và muốn hoàn tất code trước**. Sau đổi USB, E2/D2 đang timeout nên web thực tế hiển thị “— / Chưa có dữ liệu”. Chưa xác minh0% trên cảm biến thật sau khi cấp nguồn lại; mốc cạn vẫn đã lưu từ lượt đo thật trước đó. Chưa thử bơm hay hiệu chuẩn đầy thật. Không xóa/tự lấy lại mốc cân.

## Kiểm tra

- 7 kiểm thử Python PASS: mappingE2/D2, thayD1 không đổi dự trữ, bật/tắtpump không ngừng D2, cạn0%, không tự tạo% khi thiếu đầy, nội suy hai mốc, lưu bền, timeout/stale, fileconfiglỗi không làm mất trạng thái thiết bị, từ chối lấy đáy làm đầy, route cần xác nhận.
- 31 kiểm thử Flutter PASS, gồm UI cạn0%, D2 không phụ thuộcpumpOff, không hiện97% khi thiếu mốc đầy, offline/stale, form/On/Off, màn320–1280px. Analyzer không có lỗi; buildREAL/basehref/flutter/CanvasKit/font cục bộ PASS.
- Backend/web HTTP và SHA checks PASS; API/bridge/AI active. Không có lệnh pump_enable hay thử cấp thức ăn trong triển khai.
- Giao diện thật1024×600 kiểm tra cả Tổng quan và Cài đặt. Ảnh `reserves_overview.jpg`, `reserves_settings.jpg`.

## Source

Flutter chính `D:/DA_KT_NC/feeder_demo`: mới `lib/reservoir_cards.dart`, cập nhật main/user_pages/water_control_panel/feeder_backend/real_backend. Backend `/home/toan/for_cat/jetson`: mới `app/reservoir_levels.py`, `app/api/reservoir_routes.py`; sửa main/system_state. `backend_plan.json` ghi SHA trước/sau và `live_before/` trên Jetson giữ backup.

MainSHA `1793f36fcbc8a59f972782cf0cce07573f82ba34c6bf09e7ce8c0773af1b8796`; system_stateSHA `34479a5ee67b085a90f8d36aa4c34e71e2bc09c543e4ed113379b6f0da8039b9`; levelsSHA `136021189f898739b65d2644ced4d8ea0bafcf2418fc05825327bc071ef99601`; routesSHA `a048693b51950e2e5860e135f397703270edd83c0fd943e5b4553e19069cf524`.

Live web `/home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2`, mainJS SHA `59ef40a45169aa5093c14704555e54c4c027b04a2f231ef30ad4892544fbae90`. Backup `.before_reserves_20261111` cùng thư mục cha. Remoteevidence `/home/toan/for_cat/evidence/reserves_20261111`.

Chân native là nguồn đối chiếu dây: bridge/ultrasonicmetadata cũ vẫn mang tên JSN, roleTBD và D2echo10. Tác vụ này dùng rõ khóaE2/D2 để sửa ứng dụng, không đổi protocollegacy hay sơ đồ chân. NativeD2 thật vẫn18/19; không dùng metadataecho10 để đấu dây.
