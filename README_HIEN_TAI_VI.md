# SOURCE JETSON HIỆN TẠI — lấy trực tiếp ngày10/11/2026

Gói này lấy trực tiếp từ `/home/toan/for_cat` trên server-jetson sau khi người dùng bật máy. Không phải source backend cũ của gói báo cáo08/11. `SOURCE_MANIFEST.json` ghi đường dẫn gốc, thời điểm UTC và SHA256 của từng file đã lấy.

## Mở các phần chính để đọc/báo cáo

| File | Vai trò |
|---|---|
| jetson/tools/fc_live_bridge.py | Bridge UART115200 `/dev/ttyTHS1`, gửi lệnh/heartbeat, nhận status, trao đổi AI và SQLite. Bản mới nhất có ghép dòng UART bị chia bởi timeout, bỏ PIR, xử lý lưu DB/outbox. |
| jetson/tools/fc_auto_cat_gate.py | Kiểm tra trạng thái thiết bị và dữ liệu mới trước yêu cầu CAT. |
| jetson/tools/fc_bridge_storage.py | Ghi trạng thái có giới hạn chờ và hàng đợi sự kiện bền khi SQLite bận. |
| jetson/tools/fc_ai_tap.py | Đọc kết quả CAT/DOG từ tiến trình TensorRT vào SQLite. |
| jetson/tools/fc_camera_health.py | Trạng thái thiếu camera/bận và loại bỏ dữ liệu AI cũ. |
| jetson/ai/cat_dog_trt.cpp | MãC++ nhận hình camera, chạy TensorRT và đưa kết quả nhận diện. |
| scripts/run_existing_ai.sh | Giám sát camera và chạy detector cùng Python tap. |
| scripts/build_cat_dog_trt.sh | Biên dịch detectorC++ trên Jetson. |
| jetson/app/main.py và app/api/ | FastAPI, các endpoint và tích hợp giao diện web. |
| jetson/app/system_state.py | Tổng hợp trạng thái hệ thống cung cấp cho web. |
| jetson/app/storage/ | Lưu trữ SQLite và xử lý dữ liệu. |
| systemd/user/ | Bản cấu hình3 dịch vụ tự chạy và drop-in thật trên máy. |

Các thư mục/tests và script chẩn đoán cũng được giữ để đọc tham khảo; không phải tất cả các module lịch sử đều là đường chạy hiện tại. Đường chạy thật theo3 unit trong systemd/user.

## Luồng hoạt động đang dùng

Camera → detector TensorRTC++ → fc_ai_tap.py → SQLite → fc_live_bridge.py → UART → ESP32. ESP32 gửi số đo/trạng thái về bridge → SQLite → FastAPI → giao diện Flutter. Điều khiển cân/servo/pump nằm trong firmware ESP32; giao diện web không trực tiếp điều khiển chân GPIO.

API unit dùng `ESP32_TRANSPORT=MOCK`, `CAMERA_PROVIDER=MOCK`, `AI_RUNTIME=MOCK` trong lớp adapter cũ, đồng thời `ESP32_BRIDGE_ENABLED=1` và `SYSTEM_STATE_PROVIDER=REAL`. Dữ liệu thiết bị/AI thật được các tiến trình riêng cập nhật vào SQLite. Vì vậy không suy luận rằng cả hệ thống chỉ mô phỏng từ một biến môi trường này.

## Các thành phần runtime kèm theo

- jetson/ai/cat_dog_trt: binaryARM lấy từ Jetson.
- models/tensorrt/yolov8n_320_fp16.engine: model engine đang được detector mặc định sử dụng.
- requirements*.txt: dependencyPython.

Binary/engine phụ thuộc kiến trúcARM, CUDA/TensorRT và môi trường Jetson tương thích; không chạy trực tiếp như chương trìnhWindows. Nguồn mô hình huấn luyện/dataset và môi trườngvenv không nằm trong gói. Engine là tệp suy luận đã có trên máy, không phải mã huấn luyện.

## Cấu hình và khởi động

Mở thư mục JETSON trong VSCode để đọc code. Để xem lệnh máy thật đang dùng, đọc lần lượt systemd/user/for-cat-api.service, for-cat-ai.service và for-cat-esp32-bridge.service cùng các thư mục .service.d.

Các cấu hình hiện tại dùng `/home/toan/for_cat`, Pythonvenv `.venv/jetson-integration`, UARTttyTHS1 và web build tại `.native-build/flutter/four_ultrasonic_20261027_r2`. Muốn triển khai lên máy khác phải chuẩn bị môi trường và đổi các đường dẫn phù hợp. Gói mã này không tự cài đặt hoặc ghi đè dịch vụ đang chạy.

Nội dung database, nhật ký, ảnh/video, môi trườngPython và tệp mật khẩu không được đưa vào gói source. Vì vậy lịch sử/lịch ăn đã lưu trên máy không phải một phần của gói mã này. Source giao diện Flutter nằm riêng tại D:/DA_KT_NC/feeder_demo.

## Giới hạn kết quả báo cáo

Mục tiêu cấp35 g không đồng nghĩa chính xác vật lý35.000 g. Kết quả A/B đã kiểm thử bằng lấy thức ăn bằng tay, chưa chứng minh mèo thật thíchA/ghétB. Phần trăm mức nước/thức ăn, bảo vệ cạn bình và kiểm thử mất điện thật còn phụ thuộc hiệu chuẩn/kiểm thử phần cứng. Các tài liệu lịch sử trong gói có thể nhắc PIR hoặc sơ đồ cũ; bản hiện tại đọc ESP32/README_VI.md và bridge mới nhất.
