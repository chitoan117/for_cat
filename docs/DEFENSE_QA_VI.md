# DEFENSE Q&A — trả lời miệng ngắn, checkpoint26/10/2026

**Nguyên tắc:** tách đã làm / đã đo / còn kế hoạch. PASS phần mềm không thay PHYSICAL_PASS.
Các câu nói về thiết bị chạy thật là hồ sơ checkpoint trước, không phải live trong demo offline.

### 1. Vì sao dùng Jetson Nano?
Vì cần GPU để xử lý ảnh tại thiết bị và có stack CUDA/TensorRT. Nó phù hợp thử nghiệm edge AI, nhưng Nano2GB có giới hạn RAM, nhiệt và hiệu năng; em không mặc định mọi model đều realtime.

### 2. Vì sao dùng ESP32-S3?
Để tách đọc cảm biến/I/O và kiểm soát cơ cấu khỏi tác vụ thị giác nặng. ESP32 kiểm tra quyền đầu ra cuối cùng; Jetson không trực tiếp thay thế safety ở MCU.

### 3. Vì sao dùng C++ thay Python runtime?
Inference hiện có là C++ OpenCV/TensorRT để tích hợp native và kiểm soát tài nguyên trên Jetson cũ. Bridge serial cũng C++. FastAPI, scheduling và tooling vẫn dùng Python; em không tuyên bố C++ luôn nhanh hơn trong mọi bài toán.

### 4. TensorRT làm gì?
Nó tối ưu và thực thi mạng neural trên GPU NVIDIA, có thể chọn kernel/fusion/precision phù hợp. Engine phụ thuộc môi trường; không tùy tiện lấy engine khác máy để thay.

### 5. ONNX là gì?
Là định dạng biểu diễn mô hình trung gian, thường dùng trao đổi từ framework huấn luyện sang công cụ triển khai như TensorRT. File ONNX không tự chứng minh accuracy hoặc compatibility engine.

### 6. YOLOv8n là gì?
Là biến thể nano, nhỏ của họ detector YOLOv8. Pipeline này dùng model320 để nhận CAT/DOG; NONE là không có detection chấp nhận được, không phải một lớp vật thể thứ ba được học riêng.

### 7. Vì sao TensorRT FP16?
FP16 có thể giảm dung lượng và chi phí tính toán so với FP32 trên phần cứng hỗ trợ. Lợi ích thực tế và chênh accuracy phải đo; ở phiên RC em giữ engine hiện có, không benchmark hay rebuild.

### 8. AI có nhận diện đúng con mèo của chủ không?
Chưa. Contract hiện phân loài CAT/DOG/NONE, không định danh cá thể và không kết luận hành vi ăn chỉ bằng nhãn CAT.

### 9. Vì sao không để AI mở servo trực tiếp?
Một detection có thể sai hoặc cũ. AI chỉ là evidence tạo intent; arbiter và gate còn kiểm freshness, khoảng cách/thời gian, cân, cooldown và quyền cơ cấu.

### 10. Feed Arbiter là gì?
Là điểm phân xử chung các intent MANUAL/SCHEDULED/AUTO_CAT. Nó áp dụng cùng policy và safety để trả quyết định, tránh mỗi nguồn có một đường mở servo riêng. Hiện execution vẫn blocked dry-run.

### 11. Vì sao cần HC-SR04 khi đã có camera?
Camera cho biết loại đối tượng; ultrasonic bổ sung khoảng cách ở vùng quan tâm. Hai loại evidence bổ sung nhau nhưng ultrasonic cũng có blind zone, vật liệu/góc phản xạ và timeout.

### 12. Sensor fusion là gì?
Là kết hợp nhiều nguồn bằng chứng, ví dụ CAT từ ảnh cùng near từ ultrasonic và thay đổi cân ổn định. Không phải cứ có nhiều sensor thì mặc định quyết định đúng hơn; nguồn lỗi phải bị loại/chặn.

### 13. Vì sao cần temporal confirmation?
Để không hành động theo một frame hoặc một echo nhiễu. Điều kiện phải giữ đủ thời gian/mẫu và dữ liệu phải fresh; thời gian cụ thể cần cấu hình/kiểm chứng, không tự đặt để demo pass.

### 14. HX711 dùng làm gì?
Đọc tín hiệu nhỏ từ loadcell thành raw ADC. Muốn gram phải có offset/factor, reference thật, độ ổn định và verify; raw hoạt động chưa nghĩa là đã calibrated.

### 15. Vì sao target35g không dùng thời gian servo?
Khối lượng chảy thay đổi theo hạt, mức kho, độ mở và kẹt. Thời gian servo chỉ có thể là giới hạn/tham số điều khiển, không là phép đo khối lượng35g.

### 16. actual_dispensed được tính thế nào?
Về closed-loop dự kiến: actual=stable_after−stable_before của khay nhận trong cùng lần cấp, với cân hợp lệ và kiểm tra điều kiện đo. Nếu mất sample, không ổn định, mèo tác động hay cơ cấu chưa chạy thì không bịa actual; checkpoint hiện tại là null.

### 17. Cân đang35g có nghĩa đã cấp35g không?
Không. Đó có thể là thức ăn cũ hoặc tải khác trong khay. Phải đo phần tăng thêm của một lần cấp có provenance, không lấy bowl total làm actual.

### 18. HX711 đã hiệu chuẩn chưa?
Có raw và đã thu FIT với tải thật, nhưng validation zero/35g và persistence chưa đạt đủ nên chưa gram calibration PHYSICAL_PASS, chưa active model hợp lệ ở checkpoint cuối. Không gọi candidate là đã calibrated.

### 19. Scheduled Worker chống duplicate thế nào?
Occurrence có unique identity theo plan_id và ngày Việt Nam, độc lập revision; occurrence và request inbox được ghi atomically trong cùng SQLite transaction. Poll/preview/restart đọc lại identity thay vì enqueue mới.

### 20. Restart Jetson có cấp trùng không?
Đã có proof restart API không tạo thêm scheduled request trong cùng cửa sổ, và unit tests kiểm persistence/dedupe. Điều đó bảo đảm phạm vi ledger/request được thử; em chưa tuyên bố exactly-once physical dispensing qua mọi mất điện hoặc mất DB.

### 21. Trễ giờ có chạy bù không?
Không trong policy hiện tại. Cửa sổ đến hạn60giây, phải có TIME_VALID và trạng thái phù hợp. Qua cửa sổ thì bỏ qua, không dồn bữa sau reboot.

### 22. SQLite dùng làm gì?
Lưu plan, occurrence, request/decision, telemetry/AI view và calibration metadata trong database canonical hiện có. Transaction/unique constraint hỗ trợ atomicity và dedupe; không dùng JSON frontend làm nguồn sự thật cho lịch REAL.

### 23. WebSocket khác REST thế nào?
REST phù hợp lấy snapshot/thao tác có request-response. WebSocket giữ kết nối để đẩy state cập nhật; mất kết nối thì UI phải stale/unknown, không giữ số cũ như live. Chúng dùng cùng backend/state.

### 24. REAL và MOCK khác nhau thế nào?
REAL đọc API hiện có, chỉ dùng dữ liệu trả về hợp lệ. MOCK là bản compile có fixture và badge, dùng kiểm UI; nó không phải cảm biến hoặc Jetson giả trong production.

### 25. Vì sao không tự fallback REAL sang MOCK?
Vì người dùng có thể tưởng số giả là sensor thật hoặc tưởng cơ cấu an toàn. Khi lỗi, REAL phải hiện OFFLINE/UNKNOWN và giữ hành động phù hợp bị chặn.

### 26. AUTO_CAT hoạt động thế nào?
Concept là CAT ổn định, đủ gần, cooldown và cân/safety hợp lệ tạo intent qua arbiter. Dedicated state backend chưa expose đầy đủ nên UI hiện UNKNOWN/NOT_AVAILABLE; physical feeding chưa hoàn tất.

### 27. AUTO_WATER hoạt động thế nào?
Concept là đọc JSN, đổi distance ra level theo geometry rồi dùng threshold/hysteresis và time limit để yêu cầu pump. Cần kiểm nguồn nước/sensor lỗi/stop; hiện threshold và physical pump chưa đạt, AUTO_WATER vẫn false.

### 28. Vì sao servo/pump đang bị khóa?
Vì chưa có đủ bằng chứng calibration, closed-loop/flow và thử cơ cấu có kiểm soát. Build/test software không phải quyền cấp điện chuyển động thật.

### 29. Sensor lỗi thì xử lý thế nào?
Tùy loại lỗi phải phân biệt timeout, stale, chưa đấu, chưa cấu hình và unknown; dữ liệu không hợp lệ không được dùng để cấp phép tự động. Không đổi missing thành0 hoặc tự giả sensor khỏe.

### 30. Sensor #2 đã hoạt động chưa?
Chưa đấu/test theo checkpoint. UI chỉ chuẩn bị schema; đề xuất HC#2 16/17 và JSN#2 18/10 còn xung đột RESERVED. Em không nói wiring hoặc physical pass.

### 31. Lịch sử có thể hiển thị trùng hoặc bịa bữa ăn không?
UI ghép event ring, occurrence lưu bền và receipt, dedupe theo request ID; blocked không bị pending ghi đè. Không tạo completed feed từ target/dry-run, và không suy AI transition chỉ từ đổi snapshot.

### 32. Làm sao biết nút bấm không gửi hai request?
Flow có xác nhận, guard khi đang gửi, lưu ID trước POST và retry cùng ID. Reload chỉ GET receipt đã lưu. Regression có double-click/lost-response/reload cases; nút hardware trước đây cũng kiểm hold không repeat.

### 33. Clock/RTC dùng thế nào?
Lịch hiện dùng giờ Jetson đã TIME_VALID và ngày VN UTC+7; không có RTC fallback tự cho ăn ở ESP32 trong scope này. Clock chưa xác nhận thì không xét như due hợp lệ.

### 34. Kết quả RC chứng minh điều gì?
Chứng minh checkpoint phần mềm offline sạch:54 Flutter,393 backend offline,14 JS tests; REAL/MOCK build và36 ảnh UI đã xác minh trên cùng source. Không chứng minh hardware đang online, accuracy toàn tập, servo/pump hoặc actual35g.

### 35. Vì sao một bài Linux/PTY chưa chạy?
Host này là Windows không có Linux PTY/native bridge runtime tương ứng. Em ghi NOT RUN rõ ràng, không sửa test thành fake pass; sẽ chạy lại trong môi trường phù hợp.

### 36. Việc đầu tiên khi hardware trở lại?
Kiểm nguồn/common GND và mức áp, rồi enumerate đúng ESP32, connectivity/telemetry/safety. Sau đó theo checklist cảm biến → calibration/persistence → cơ cấu riêng → closed loop → auto, không bắt đầu bằng enable servo.
