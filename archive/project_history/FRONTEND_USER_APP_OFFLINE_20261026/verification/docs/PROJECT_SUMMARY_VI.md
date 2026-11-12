# Tóm tắt đề tài forr_cat

## Tên đề tài
Hệ thống theo dõi hành vi ăn, uống và hỗ trợ cấp thức ăn/nước cho mèo sử dụng camera USB, Jetson Nano và ESP32-S3.

## Mục tiêu và đối tượng sử dụng
Hỗ trợ người nuôi theo dõi lịch sử ăn/uống, nhận diện mèo mục tiêu và nghiên cứu xu hướng lựa chọn thức ăn dựa trên nhiều phiên quan sát. Đây là đề tài nguyên mẫu; không chẩn đoán sức khỏe hoặc khẳng định chắc chắn mèo thích một loại thức ăn.

## Kiến trúc
Camera USB thông thường cung cấp hình ảnh cho Jetson Nano. Jetson dự kiến xử lý AI, xác nhận phiên hành vi, lưu SQLite và phục vụ REST cho Web/App hiện có. ESP32-S3 nhận ý định qua USB serial, đọc cảm biến và giữ quyền quyết định an toàn cuối cùng đối với servo/bơm.

## Chức năng, AI và IoT
Phần mềm chuẩn bị nhận diện OWNER_CAT/OTHER_CAT/UNKNOWN, theo dõi EATING/DRINKING theo thời gian, kết hợp cân khi có dữ liệu ổn định đã kiểm chứng, lịch sử/yêu cầu cấp thức ăn và báo cáo hoạt động. AI được tách thành detector, crop/track, nhận diện và hành vi; không bắt buộc một mô hình lớn duy nhất. IoT là kết nối camera–máy tính nhúng–MCU–cảm biến/API, không cần đưa thiết bị lên Internet.

## Phần cứng và an toàn
Ứng viên gồm Nano, webcam USB, board ESP32-S3 N16R8, load cell/HX711, cảm biến khoảng cách, RTC, OLED, nút/buzzer, servo và bơm. GPIO, nguồn, cơ khí và thông số board chưa kiểm chứng. Servo/bơm bị vô hiệu hóa; RTC/cân/nước lỗi phải chặn ý định không an toàn. AI chạy shadow mặc định, không cấp quyền chấp hành.

## Tiến độ và phần chưa kiểm chứng
Milestone **M2 — ứng viên phần mềm trước phần cứng**. Host tests, simulator và firmware compile có kết quả riêng trong `PRE_HARDWARE_FINAL_BASELINE.md`; chúng không phải kết quả Jetson/cảm biến/mèo thật. Đã thêm capture session, manifest/version/leakage, chuẩn bị thí nghiệm/registry/evaluation và báo cáo/traceability. Chưa có dataset mèo thật, mô hình đã huấn luyện, FPS Nano, hiệu chuẩn cảm biến hoặc demo hệ thống thật. Các bước tiếp theo phụ thuộc thiết bị/dữ liệu thực và evidence; không tăng tiến độ vật lý từ số lượng tài liệu hay fixture tests.
