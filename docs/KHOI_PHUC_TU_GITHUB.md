# Khôi phục source FOR_CAT từ GitHub

## Lấy lại toàn bộ source

```sh
git clone https://github.com/chitoan117/for_cat.git
cd for_cat
```

`archive/` chỉ để tham khảo lịch sử. Các phần dùng để build lại nằm ở `esp32/`, `jetson/`, `frontend/`, `ai/`, `models/`. Kiểm tra checksum trong `BACKUP_MANIFEST.json` sau khi tải. Bản ZIP tải từ GitHub cũng có các tệp này, nhưng clone giữ được lịch sử.

## Web Flutter

Giữ SDK Flutter tương thích `frontend/pubspec.yaml` (gói bàn giao trước dùng Flutter 3.47.6/Dart 3.13.5). `frontend/pubspec.lock` đã được lưu.

```sh
cd frontend
flutter pub get
flutter run -d chrome --dart-define=FEEDER_MODE=mock
```

Lệnh trên dùng MOCK để xem giao diện trên laptop, không chứng minh phần cứng thật. `web_release/` là bản REAL đã build với `/flutter/`, có `forcat_build.json` và CanvasKit/tài nguyên cục bộ; dùng bản này khi khôi phục giao diện offline trên Jetson. Khi build mới cần giữ cấu hình REAL, base href `/flutter/`, target35g và marker theo `jetson/app/frontend_assets.py`; không trộn bản mock với điều khiển thật.

## Backend và Jetson

Đọc các requirement trong `jetson/` và các unit `systemd/user/` trước khi cài. Môi trường Python tích hợp cũ nằm tại `~/for_cat/.venv/jetson-integration`; không có venv trong Git, phải tạo lại và cài các requirement phù hợp, thường bắt đầu từ `jetson/requirements-realtime.txt`. TensorRT/CUDA/OpenCV cần đúng JetPack và kiến trúc Jetson, không cài môi trường Windows sang Jetson.

Các unit đang dùng `%h/for_cat`; clone vào vị trí đó hoặc chỉnh đường dẫn trong unit. Backend chạy `python -m tools.run_api` từ thư mục `jetson/`. Cấu hình API hiện tại dùng cổng8000 và `FORCAT_FLUTTER_WEB_DIR` trỏ tới thư mục artifact web. Có thể chép nội dung `web_release/` vào vị trí đó rồi kiểm tra `/app`. SQLite vận hành được tạo mới; database lịch sử không được công khai trong repo.

Ba unit chính: `for-cat-api.service`, `for-cat-esp32-bridge.service`, `for-cat-ai.service`. Cần cài lại user units, kiểm tra quyền UART và bật autostart/linger trên máy mới; không chỉ mở icon desktop. `systemd/99-forcat-uart.rules` và scripts UART trong archive là tài liệu tham khảo. Tailscale phải cài/đăng nhập/cấp quyền lại trên thiết bị mới; source không chứa thông tin đăng nhập.

Model `models/tensorrt/yolov8n_320_fp16.engine` lấy từ bản export Jetson. Engine TensorRT phụ thuộc phần cứng/phiên bản; khi không tương thích, build lại bằng môi trường tương ứng. `models/reference/` giữ các model tham chiếu trên laptop; chưa xác nhận mọi model đó chính là đầu vào tạo engine. Source build C++ có ở `scripts/build_cat_dog_trt.sh`.

File `config/reservoir_calibration.saved.json` giữ mốc cạn E2/D2 đã xác nhận. Muốn dùng lại phải đối chiếu vị trí cảm biến thực rồi mới chép vào `jetson/data/reservoir_calibration.json`; chưa có mốc đầy thật. Không khôi phục cấu hình hình học cũ sang hộp mới một cách tự động.

## ESP32-S3

Mở `esp32/esp32.ino`, giữ cả7header cùng thư mục. Build đã dùng ESP32 core3.3.12, ESP32-S3, Flash4MB, USBMode HardwareCDC/JTAG, CDCOnBoot disabled, PSRAM disabled. FQBN: `esp32:esp32:esp32s3:UploadSpeed=921600,USBMode=hwcdc,CDCOnBoot=default,FlashSize=4M,PSRAM=disabled`.

Ứng dụng giao tiếp UART1 RX41/TX42 ở115200baud; USB WCH GPIO43/44 dùng nạp. Khi nạp tạm bằng USB phải tắt nguồn VIN5V riêng theo cấu hình bo hiện tại. File build tương ứng trong `firmware/offline_r2/`. Không erase toàn chip hoặc ghi đè NVS để sửa lỗi nút: NVS trên bo đang giữ mốc cân. Không nạp dump NVS của bo khác.

Tệp nguồn không chứa toàn bộ dữ liệu NVS của bo: nếu thay ESP32/HX711/loadcell phải hiệu chuẩn lại bằng chén rỗng và quả cân chuẩn. Việc sao lưu Git không tự sao lưu SQLite, dữ liệu Tailscale hoặc ảnh/video cá nhân.


Thư viện Arduino đã dùng: Adafruit SSD1306 2.5.17, Adafruit GFX Library 1.13.0, Adafruit BusIO 1.17.4. Cài bằng Library Manager trước khi build.

