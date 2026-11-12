# Gợi ý trình bày ngắn

- **Kiến trúc:** “Camera USB nối Jetson; Jetson lưu lịch sử và REST; ESP32-S3 chịu trách nhiệm cảm biến và quyền chấp hành cuối cùng.”
- **Jetson:** “Đã chuẩn bị backend, camera/replay và vòng đời quan sát. Chưa xác nhận môi trường hoặc tốc độ Nano thật.”
- **ESP32:** “Có policy an toàn, driver/diagnostic foundation và build an toàn. GPIO chưa gán; servo/bơm vẫn tắt.”
- **AI:** “Tách detector, nhận diện và hành vi; hiện chỉ có interface, candidate và evaluation tooling. Chưa có mô hình train hay độ chính xác thật.”
- **Ăn/uống:** “Temporal engine xác nhận nhiều frame và kết thúc tại evidence cuối. Không tính thời gian ăn qua khoảng không quan sát.”
- **Thức ăn:** “Báo cáo xu hướng hành vi trên nhiều phiên sạch, cân hợp lệ và confounder đã ghi; không khẳng định cảm xúc hay suy ra đói.”
- **An toàn:** “AI shadow, MCU authority, invalid RTC/cân/nước chặn request; ACK không có nghĩa thao tác thành công.”
- **Web/App:** “API hợp đồng đã chuẩn bị; frontend cũ nằm ngoài repo và chưa kiểm chứng tích hợp/network thật.”
- **Kết luận:** “M2 là ứng viên phần mềm trước phần cứng. Số test/build là bằng chứng host; phần vật lý, dataset, AI thật và demo cuối còn cần kiểm chứng.”
