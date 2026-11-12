# 🐱 FOR_CAT — Hệ thống chăm sóc mèo thông minh

Dự án sử dụng **USB Webcam + Jetson Nano + ESP32-S3** để theo dõi mèo, nhận diện bằng AI và hướng tới quản lý thức ăn, nước uống tự động.

**Canonical current state: 2026-10-21 — [trạng thái thực tế](docs/CURRENT_PROJECT_STATE.md),
[pin/bring-up](docs/ESP32_S3_SENSOR_STATION.md), [roadmap](docs/ROADMAP.md).**
Phạm vi chính **CAT / DOG / NONE**, một mèo đen. OWNER_CAT/OTHER_CAT là future/legacy.
Production vision tiếp tục C++14/OpenCV/TensorRT/CUDA; không chuyển sang Python inference.
Chén ăn trước-trái = FOOD_ROI; chén uống trước-phải = WATER_ROI. Chén inox có thể
cùng màu; RED/BLUE của nắp quay cũ không phải điều kiện nhận diện.
Board ESP32-S3 16MB/no PSRAM; bộ dây mới chưa được cấp physical PASS.
HX711 có trong kế hoạch/lắp ráp; installation/calibration hiện chưa được kiểm chứng
trong rig mới, không tiếp tục mặc định rằng vĩnh viễn chưa lắp.

Runtime C++ đã được compile và đo trên Nano thật: latest-frame một application
slot, hai V4L2 buffers sau khi đo thấy một buffer làm FPS giảm một nửa.
Headless khoảng 30 FPS; X11 khoảng 20 FPS trong phép đo hiện tại. Driver timestamp
age qua X11 giảm 254.7 -> 105.5 ms. Xem [kết quả thật](docs/JETSON_CAMERA_LATENCY_RESULT.md).
Binary đã được thay sau validation, có backup trước latency. Engine không đổi.
CAT/DOG đã được chủ xác nhận chạy thật trước webcam. Đây là bằng chứng do chủ
cung cấp, không phải phép test vật lý mới trong lần audit này. Không gọi các số đo
latency cũ là sensor-exposure latency.

[Workflow Behavior V2](docs/SINGLE_CAT_BEHAVIOR_V2.md) đã có schema versioned,
import/extraction2FPS/annotation/session split/validation/export. Trên Windows đã
trích3.063 ảnh từ22video, chốt pilot165ảnh và train thử baselineCPU; test25%, chưa
đưa vào production. **Hiện không cần train EATING mới ngay:** ưu tiên CAT near food
+ xu hướng giảm cân có ý nghĩa + filter/hysteresis/FSM. Tracker/fusion chưa nối vào camera C++.
ROI JSON là template chưa cấu hình, không chứa tọa độ giả. **Actuator vẫn disabled.**
Đã có [thư viện C++14 shadow độc lập](docs/CPP_BEHAVIOR_SHADOW.md): single-cat
tracker, ROI/geometry, smoothing/FSM theo thời gian và START/END events; Nano native,
ASan/UBSan/TSan PASS. Chỉ test offline/synthetic, chưa nối vào runtime camera,
không có behavior model production và không ghi dữ liệu giả vào history.

[Công cụ ROI/geometry](docs/GEOMETRY_CAMERA_VALIDATION.md) đã có capture frame gốc,
chọn FOOD/WATER qua GUI hoặc tọa độ pixel CLI, overlay và kiểm tra MP4 bằng detector
hiện có trong executable riêng. Chưa có video camera cố định để xác nhận ROI thật;
NEAR/APPROACHING/LEAVING là geometry, không phải nhận diện EATING/DRINKING.

Workflow MP4 thật đã có batch import, quality flags, annotation/correction theo time
interval, group split và JSON/Markdown readiness: [hướng dẫn Windows/HOST/Jetson](docs/BEHAVIOR_V2_VIDEO_WORKFLOW.md).
Không auto-label cả video thành EATING. Food preference là metadata thí nghiệm;
so sánh biến thể thức ăn qua các session tại cùng FOOD_ROI, giữ WATER_ROI cho nước,
không tạo nhãn LIKE/DISLIKE. Ưu tiên hiện tại là đo cân/cảm biến thật, không phải quay thêm để train NN.

---

## 1. Kiến trúc mục tiêu — xem current state để phân biệt phần đã tích hợp

```text
USB Webcam
     ↓
Jetson Nano
     ├── OpenCV + TensorRT
     ├── Nhận diện CAT / DOG
     ├── Tracker + fusion cân/FSM (next)
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

- Firmware đọc tổng hợp cảm biến ESP32-S3 và monitor USB serial đã có:
  [hướng dẫn sensor station](docs/ESP32_S3_SENSOR_STATION.md). RTC hiện tại là DS1302;
  build/test phần mềm PASS, chưa nạp/kiểm chứng cảm biến thật; servo và pump vẫn khóa.
- [Kiểm thử offline firmware V2](docs/ESP32_S3_OFFLINE_VALIDATION.md) chạy setup/loop
  thật với I/O giả lập và parser Jetson; đã sửa lỗi mất hệ số HX711 khi chỉnh geometry.

- ✅ Jetson Nano hoạt động
- ✅ USB Webcam hoạt động
- ✅ OpenCV C++ hoạt động
- ✅ TensorRT FP16 hoạt động
- ✅ C++ CAT/DOG latest-frame chạy khoảng 30 FPS headless; X11 đã đo riêng
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

CAT  → observation, không tự cho ăn
DOG  → không đưa vào behavior của mèo
NONE → không có pet detection đủ ngưỡng
```

Model hiện tại dùng để thử nghiệm và đánh giá, chưa dùng làm điều kiện duy nhất để điều khiển phần cứng.

---

## 4. Luồng mục tiêu — chưa tự động chạy actuator

```text
CAT + HC-SR04 #1 near ổn định + safety/cooldown
   → unified feed arbiter → ESP32 safety
   → servo pulse / close / settle / cân → cấp THÊM khoảng40g
CAT near food + cân giảm vượt noise → EATING / consumed grams (next)
DOG hoặc NONE → NO FEED
Water operational LOW/TARGET → ESP32 safety → pump (không qua DRINKING AI)
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
ssh -Y toan@server-jetson.local
```

### Chạy nhận diện CAT / DOG

```bash
cd /home/toan/for_cat/jetson/ai
./cat_dog_trt

# Benchmark bounded, không ghi JPEG:
./cat_dog_trt --headless --no-snapshot --seconds 30
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

Hiện decoder chỉ so score CAT/DOG, chưa enforce winner toàn bộ 80 COCO classes;
không tuyên bố PERSON/UNKNOWN được chặn hoàn toàn ở decoder. Không có AI-to-actuator path.
IP dùng DHCP; dùng hostname hoặc địa chỉ thực tế đang được cấp, không hard-code vào source.

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
git status --short
git diff --check
# Ví dụ: stage đúng file đã review, không stage dataset/model/backup:
git add -- jetson/ai/cat_dog_trt.cpp JETSON_COMMANDS.md
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
- ESP32-S3 16 MB / no PSRAM (actuator outputs vẫn disabled)
- USB Webcam
- Servo
- Water Pump
- Load Cell + HX711
- PIR HC-SR501 x1
- HC-SR04 x2: #1 approach12/13; #2 hopper inventory TBD
- JSN-SR04T V3.0 x2: #1 operational water14/15; #2 reservoir inventory TBD
- F5305S MOSFET module điều khiển pump GPIO7; servo signalGPIO6
- RTC DS1302 GPIO16/17/18
- OLED SSD1306 0x3C GPIO8/9

Target Web: **one backend + one SQLite + one REST API + one responsive Web**, hai
layout `/kiosk` và `/app`. Scheduler một-lần/hàng-ngày/thứ-trong-tuần và Feed Now
cùng qua feed arbiter; hiện chưa có scheduler/UI này. Backend Python cũ là source
host-tested, không phải production AI runtime C++ và chưa được xác minh deploy trên Nano.

---

## Trạng thái an toàn hiện tại

```text
AI_SHADOW_MODE       = ON
AUTO_ACTUATOR_CONTROL = OFF
```

Điều khiển tự động chỉ được bật sau khi AI, cảm biến và cơ chế an toàn được kiểm tra đầy đủ.
