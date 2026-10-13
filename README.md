# 🐱 FOR_CAT — Hệ thống chăm sóc mèo thông minh

Dự án sử dụng **USB Webcam + Jetson Nano + ESP32-S3** để theo dõi mèo, nhận diện bằng AI và hướng tới quản lý thức ăn, nước uống tự động.

---

## 1. Kiến trúc hệ thống

```text
USB Webcam
     ↓
Jetson Nano
     ├── OpenCV + TensorRT
     ├── Nhận diện CAT / DOG
     ├── Phân tích hành vi
     ├── Lưu lịch sử
     └── REST API
     ↓ USB Serial
ESP32-S3
     ├── Cảm biến
     ├── Servo thức ăn
     ├── Bơm nước
     └── Kiểm tra an toàn
```

### Vai trò

| Thiết bị | Nhiệm vụ |
|---|---|
| Webcam | Thu hình ảnh |
| Jetson Nano | Chạy AI và xử lý logic |
| ESP32-S3 | Điều khiển phần cứng và kiểm tra an toàn |
| Servo | Cấp thức ăn |
| Pump | Cấp nước |
| Sensors | Theo dõi thức ăn, nước và trạng thái |

---

## 2. Trạng thái hiện tại

- ✅ Jetson Nano hoạt động
- ✅ USB Webcam hoạt động
- ✅ OpenCV C++ hoạt động
- ✅ TensorRT FP16 hoạt động
- ✅ Nhận diện CAT / DOG chạy khoảng 30 FPS
- ✅ ESP32-S3 đã có firmware nền tảng
- ✅ Source code đã lưu trên GitHub
- ⚠️ AI hiện vẫn ở **SHADOW MODE**
- ⚠️ AI chưa tự động kích hoạt Servo/Pump

---

## 3. AI hiện tại

```text
Model: YOLOv8n
Input: 320 x 320
Runtime: TensorRT FP16

CAT  → cho phép đi tiếp vào logic
DOG  → BLOCK
NONE → BLOCK
```

Model hiện tại dùng để thử nghiệm và đánh giá, chưa dùng làm điều kiện duy nhất để điều khiển phần cứng.

---

## 4. Luồng hoạt động

```text
Mèo đến
   ↓
Webcam ghi hình
   ↓
Jetson nhận diện
   ↓
Phân tích hành vi
   ↓
Kiểm tra điều kiện
   ↓
Gửi yêu cầu sang ESP32-S3
   ↓
ESP32 kiểm tra an toàn
   ↓
Servo / Pump
```

---

## 5. Cấu trúc dự án

```text
for_cat/
├── jetson/      Code chạy trên Jetson Nano
├── esp32/       Firmware ESP32-S3
├── ai/          Dataset và công cụ AI
├── docs/        Tài liệu dự án
├── scripts/     Script kiểm tra/build
├── README.md
└── JETSON_COMMANDS.md
```

---

## 6. Chạy AI trên Jetson

### SSH từ laptop

```bash
ssh -Y toan@192.168.123.10
```

### Chạy nhận diện CAT / DOG

```bash
cd /home/toan/for_cat/jetson/ai
./cat_dog_trt
```

Thoát bằng:

```text
q
```

hoặc:

```text
Ctrl + C
```

---

## 7. Các chức năng hướng tới

- Nhận diện mèo và chó
- Theo dõi thời gian mèo đến
- Nhận diện hành vi ăn/uống
- Ghi thời gian bắt đầu và kết thúc
- Tính thời gian ăn
- Theo dõi lượng thức ăn
- Theo dõi lượng nước
- Nghiên cứu món mèo thích
- Lưu lịch sử vào cơ sở dữ liệu
- Hiển thị dữ liệu trên Web/App

---

## 8. Nguyên tắc an toàn

```text
Jetson Nano = AI + xử lý cấp cao
ESP32-S3    = kiểm tra an toàn cuối cùng
```

Jetson không trực tiếp điều khiển Servo/Pump.

ESP32-S3 phải kiểm tra điều kiện an toàn trước khi phần cứng hoạt động.

---

## 9. Lệnh sử dụng

Các lệnh Jetson, TensorRT, Webcam, Compile C++ và Git được lưu tại:

```text
JETSON_COMMANDS.md
```

---

## 10. Cập nhật GitHub

Sau khi sửa code:

```bash
cd /home/toan/for_cat
git add .
git commit -m "Update project"
git push
```

Lấy phiên bản mới từ GitHub:

```bash
git pull
```

---

## 11. Phần cứng chính

- Jetson Nano 2GB
- ESP32-S3
- USB Webcam
- Servo
- Water Pump
- Load Cell + HX711
- Cảm biến mức nước
- RTC
- Display

---

## Trạng thái an toàn hiện tại

```text
AI_SHADOW_MODE       = ON
AUTO_ACTUATOR_CONTROL = OFF
```

Điều khiển tự động chỉ được bật sau khi AI, cảm biến và cơ chế an toàn được kiểm tra đầy đủ.
