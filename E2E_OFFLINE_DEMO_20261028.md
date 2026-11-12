# E2E OFFLINE DEMO — for_cat — 2026-10-28

**Kết quả: bốn kịch bản E2E PASS, simulation-only. Production servo/pump vẫn LOCKED; HX711_PHYSICAL_PASS không được tuyên bố.**

Run bằng chứng: `E2E_OFFLINE_DEMO_20261028/runs/20261028T080505213294Z/`. C++14 Windows native; toàn bộ thời gian bên dưới là **fake clock UTC**, không phải camera/cân/ăn thật.

## 1. Architecture flow thực sự được chạy

```text
Synthetic detector CAT/DOG bbox (normalized original frame)
  -> production Food ROI / RoiSpecies (FULL_FRAME default; ROI_ENABLED test)
  -> shared HC-SR04 Approach FSM + ApproachFusion / temporal timestamps
  -> existing FeedArbiter (qualification only; actuator_execution=false)
     CAT -> SIMULATION-only dispatch capability
       -> existing safety::FeedController + DailyStore interface (fake store)
       -> FakeServo OPEN45 / CLOSED90, no GPIO implementation
       <- existing Hx711 driver / signed24 / median3 / calibration
          with synthetic raw ADC bits on fake PinIO
     DOG -> existing UARTv1 encode + CRC / Parser / warning Receiver
       -> existing buzzer FSM -> fake GPIO2 edges only
  -> separate60s simulated consumption observer / LIKE-DISLIKE-UNCERTAIN
  -> JSONL -> Python recorder -> isolated SQLite + production DryRunRequests
```

- Không chạy YOLO inference thật: input camera là output detector mô phỏng có bbox rõ nguồn. Không train/download model.
- Không thêm đường production AI→servo. Arbiter vẫn trả DRY_RUN; adapter chỉ cho phép **FakeServo** trong executable offline. Bản native từ chối `--production`; source chặn build khi ARDUINO/ESP_PLATFORM được định nghĩa.
- Cấp thức ăn và theo dõi tiêu thụ là hai phase riêng. Khối lượng giảm trong phase ăn không gọi lại controller cấp thức ăn.
- Daily giới hạn được tái sử dụng từ `safety::FeedController`:4 portions/150g; cooldown dùng mức2h cho AUTO_CAT. Đó là composition trong harness, không phải deployment mới cho production.

## 2. Kết quả build / tests

| Kiểm tra | Kết quả |
|---|---|
| Windows C++14, `-Wall -Wextra -Wpedantic -Werror` | PASS, không warning |
| Bốn kịch bản đầy đủ input→event cuối→SQLite | PASS4/4 |
| Native safety/boundary cases mới | PASS56 cases / 97 explicit assertions |
| SQLite recorder / timeline / event association | PASS |
| UART bytes / LE fields / CRC đối chiếu bằng Python độc lập | PASS46 frames; CRC corrupt bị loại1 |
| Unsafe DB path guards | PASS: không chạm os.open/sqlite3.connect |
| Non-simulation CLI | PASS: exit2, không xuất event |
| SQLite integrity / all events persisted | PASS / `ok` |
| Production source hashes trước/sau | Không đổi |
| Jetson ARM64 / CUDA / TensorRT / camera / GPIO | NOT_VERIFIED trong milestone này |

Safety coverage: ROI ON/OFF/outside/unreviewed, CAT+DOG, NONE, boot gần, biên5/20/30cm/hysteresis,3 mẫu quá1.5s, CAT đứng gần120s, DOG đứng gần120s, cooldown/duplicate, daily meals/grams, request khi busy, HX chưa validated, persistence failure, sensor INVALID/NaN/âm/overflow/disconnect, timeout/no-progress, giảm cân khi đang cấp, tare epoch đổi, AI/UART stale, CRC sai/expired/replay, overshoot và production lock.

Preference coverage: consumed0/5/5.000001/10/17.999999/18/30/35g; stable noise; unstable/negative/NaN/INVALID/tare/future timestamp/stale/gap/refill; đủ60s mới kết luận. Dữ liệu không hợp lệ trả UNCERTAIN và consumed=null, không ép thành0 hoặc LIKE/DISLIKE.

## 3. Bốn kịch bản demo

| Kịch bản | Fake time hoàn tất | Kết quả có bằng chứng |
|---|---|---|
| 1 | +00:00:13.500 | PASS — CAT: đúng1 request; feedback đạt35g; fake servo45°→90°; giữ gần không cấp lặp. |
| 2 | +00:02:18.400 | PASS — DOG: không feed, không mở servo; đúng2 ON200ms/gap200ms; giữ gần120s không lặp. |
| 3 | +00:03:19.900 | PASS — FOOD_A:35→25→5g, consumed30g, LIKE;60s; không gọi lại servo. |
| 4 | +02:04:33.100 | PASS — FOOD_B: meal mới sau fake cooldown>2h,35→30g, consumed5g, DISLIKE;60s. |

### Event records chính đọc lại từ SQLite

| Type / request | Food | Actual / starting | Remaining | Consumed | Result | Timestamp UTC (fake) |
|---|---|---:|---:|---:|---|---|
| SIMULATED_FEED `PRIMARY_AUTO_1` | FOOD_A | 35g | — | — | SIMULATION_SUCCESS | 2026-10-28T00:00:10.500000+00:00 |
| SIMULATED_FEED `PRIMARY_AUTO_2` | FOOD_B | 35g | — | — | SIMULATION_SUCCESS | 2026-10-28T02:03:31.600000+00:00 |
| SIMULATED_MEAL `PRIMARY_AUTO_1` | FOOD_A | 35g | 5g | 30g | LIKE | 2026-10-28T00:03:19.900000+00:00 |
| SIMULATED_MEAL `PRIMARY_AUTO_2` | FOOD_B | 35g | 30g | 5g | DISLIKE | 2026-10-28T02:04:33.100000+00:00 |

### Fake clock timeline rút gọn

| Seq | Fake clock | Event | Nội dung |
|---:|---|---|---|
| 1 | +00:00:00.000 | SIMULATED_BUZZER_EDGE | {"level": "HIGH"} |
| 47 | +00:00:05.600 | AUTO_CAT_REQUEST | {"request_id": "PRIMARY_AUTO_1", "food_name": "FOOD_A"} |
| 51 | +00:00:05.600 | SIMULATED_SERVO | {"angle_degrees": 45, "state": "OPEN"} |
| 79 | +00:00:09.300 | SIMULATED_SERVO | {"angle_degrees": 90, "state": "CLOSED"} |
| 89 | +00:00:10.500 | FEED_COMPLETED | {"request_id": "PRIMARY_AUTO_1", "food_name": "FOOD_A", "status": "SIMULATION_SUCCESS", "actual_dispensed_grams": 35} |
| 112 | +00:00:13.500 | SCENARIO_RESULT | {"scenario_number": 1, "status": "PASS", "actual_dispensed_grams": 35} |
| 145 | +00:00:17.700 | SIMULATED_BUZZER_EDGE | {"level": "LOW"} |
| 146 | +00:00:17.700 | DOG_WARNING | {"status": "SIMULATED_RECEIVED_SEQUENCE_STARTED"} |
| 149 | +00:00:17.900 | SIMULATED_BUZZER_EDGE | {"level": "HIGH"} |
| 151 | +00:00:18.100 | SIMULATED_BUZZER_EDGE | {"level": "LOW"} |
| 154 | +00:00:18.300 | SIMULATED_BUZZER_EDGE | {"level": "HIGH"} |
| 1036 | +00:02:18.400 | SCENARIO_RESULT | {"scenario_number": 2, "status": "PASS"} |
| 1048 | +00:02:19.900 | CONSUMPTION_OBSERVATION_STARTED | {"food_name": "FOOD_A", "request_id": "PRIMARY_AUTO_1"} |
| 1489 | +00:03:19.900 | MEAL_PREFERENCE | {"request_id": "PRIMARY_AUTO_1", "food_name": "FOOD_A", "consumed_mass": 30, "classification": "LIKE"} |
| 1490 | +00:03:19.900 | SCENARIO_RESULT | {"scenario_number": 3, "status": "PASS", "food_name": "FOOD_A", "consumed_mass": 30, "classification": "LIKE"} |
| 1491 | +02:03:20.900 | FAKE_CLOCK_ADVANCE | {"advanced_ms": 7201000} |
| 1535 | +02:03:26.500 | AUTO_CAT_REQUEST | {"request_id": "PRIMARY_AUTO_2", "food_name": "FOOD_B"} |
| 1540 | +02:03:26.500 | SIMULATED_SERVO | {"angle_degrees": 45, "state": "OPEN"} |
| 1568 | +02:03:30.400 | SIMULATED_SERVO | {"angle_degrees": 90, "state": "CLOSED"} |
| 1580 | +02:03:31.600 | FEED_COMPLETED | {"request_id": "PRIMARY_AUTO_2", "food_name": "FOOD_B", "status": "SIMULATION_SUCCESS", "actual_dispensed_grams": 35} |
| 1592 | +02:03:33.100 | CONSUMPTION_OBSERVATION_STARTED | {"food_name": "FOOD_B", "request_id": "PRIMARY_AUTO_2"} |
| 2033 | +02:04:33.100 | MEAL_PREFERENCE | {"request_id": "PRIMARY_AUTO_2", "food_name": "FOOD_B", "consumed_mass": 5, "classification": "DISLIKE"} |
| 2034 | +02:04:33.100 | SCENARIO_RESULT | {"scenario_number": 4, "status": "PASS", "food_name": "FOOD_B", "consumed_mass": 5, "classification": "DISLIKE"} |

Một clock domain PRIMARY chạy liên tục bốn demo. Mỗi safety case có clock domain riêng nên reset test về0 là tường minh, không phải timestamp production bị lùi. Bước nhảy2h chỉ được phép khi controller/meal/buzzer không hoạt động.

## 4. Log đầy đủ và database test

- **5876 event** trong `events.jsonl` và `simulation_events`; số lượng được đối chiếu, không chỉ kiểm tra vài hàm riêng.
- Bốn log riêng: `SCENARIO_1_CAT_FEED.jsonl`, `SCENARIO_2_DOG_WARNING.jsonl`, `SCENARIO_3_FOOD_A.jsonl`, `SCENARIO_4_FOOD_B.jsonl`.
- `safety_checks.jsonl`, `timeline.csv`, `compile.log`, `native.stderr.log`, `negative_production_cli.log`, `result.json` và hashes giữ bằng chứng.
- Input logs giữ species/confidence/bbox thật của simulator, frame size, ROI scope và HC timestamp/validity; UART logs giữ frame_hex để kiểm tra lại byte/CRC. Đây đều là input synthetic, không phải inference camera thật.
- `simulation.sqlite3` chỉ được tạo độc quyền dưới một run directory mới. Runner không có option nhận DB/device production.
- SQLite có CHECK simulation=1, physical_execution=0 cho events. Các bảng feed/meal là simulation-only. Production-style inbox được tái sử dụng bằng `DryRunRequests.enqueue_in_transaction` với clock được mock đúng phạm vi test.
- `feed_dry_run_requests` vẫn giữ actuator_execution=false và actual_dispensed_grams=null; actual35g mô phỏng chỉ nằm trong bảng/event SIMULATION riêng. Retry không ghi đè quyết định đầu.
- Lần chạy trước được giữ lại. Không cleanup/xóa data, không sửa frontend hay database/source production.

| Table test | Rows |
|---|---:|
| simulation_events | 5876 |
| simulation_feeds | 22 |
| simulation_meals | 3 |
| feed_dry_run_requests | 29 |

## 5. Files changed

Chỉ thêm source/tooling dưới `D:\for_cat\E2E_OFFLINE_DEMO_20261028\`:
- `sim_support.h`: fake clock/PinIO/raw ADC/fake servo/daily store/UART link và composition các core hiện có.
- `simulation_preference.h`: observer tiêu thụ60s, ngưỡng18/5g, validation/noise/tare/stale; không có identity hoặc actuator API.
- `e2e_demo.cpp`:4 demo chính và safety matrix; chỉ có entry point `--simulation-only`.
- `run_demo.py`: C++14 build, stream recorder, test SQLite, gọi class inbox production và assertion độc lập.
- `make_report.py`: đọc evidence bằng SQLite read-only, tạo đúng report milestone này.
- `runs/<UTC>/...`, `latest_run.json`: artifacts chạy thực tế, không phải physical evidence.

Không sửa các source production được tái sử dụng. Các hash nằm trong `result.json` (HX711/ROI/approach/arbiter/UART/safety policy/dry-run inbox/scheduled worker).

## 6. Chạy lại trên Windows

```powershell
& "D:\for_cat\.venv\Scripts\python.exe" "D:\for_cat\E2E_OFFLINE_DEMO_20261028\run_demo.py"
```

Lệnh build bằng Zig C++ có sẵn, không tải dependency/model. Fake clock không sleep60s/2h. Mỗi lần tạo run directory mới; chat/console chỉ in summary.

Chỉ đọc lại evidence / tạo report, không chạy demo lại:

```powershell
& "D:\for_cat\.venv\Scripts\python.exe" "D:\for_cat\E2E_OFFLINE_DEMO_20261028\make_report.py"
```

## 7. Những điểm còn thiếu trong production integration

- Camera/YOLO/TensorRT thật và producer/bridge POSIX không được chạy trên Windows: harness nhập bbox tổng hợp vào core ROI/fusion có thật. Không suy Windows build là Jetson build PASS.
- Portable safety controller và daily store đã compose thành pipeline simulation. Production arbiter vẫn dry-run; durable quota/journal/restart recovery và đường dispatch tới firmware thật chưa được bật/tuyên bố hoàn chỉnh.
- UARTv1 envelope/version/CRC và DOG_WARNING receiver được dùng nguyên. Feeding trong harness là in-process simulation dispatch; không bịa rằng binary FEED_REQUEST production đã điều khiển servo thật.
- Preference18/5g là module demo theo lượng tiêu thụ. Legacy analytics nhiều phiên/identity không được dùng để giả nhận diện nhai/ngửi và chưa được thay thế hoặc đưa kết quả demo vào API production.
- Fake servo45°/90° là angle target thuần dữ liệu. Khả năng gate đóng thật, flow/in-flight food/overshoot, động cơ, loadcell drift và nguồn đều chưa được xác minh bằng harness.

## 8. Chuẩn bị port Jetson sau này

1. Rebuild các producer/bridge/consumer bằng toolchain C++14 ARM64 và SDK Jetson thực. Binary Windows trong run này không phải firmware hay ELF ARM.
2. JSON boundary giữa detector/ROI/AI state mang CAT/DOG/NONE, bbox NORMALIZED_ORIGINAL, mode, timestamp và eligibility. C++ struct chỉ dùng nội bộ; không gửi raw struct phụ thuộc ABI qua UART. Rebuild đồng bộ consumer sau thay đổi header.
3. UARTv1 dùng fixed-width LE32/length/CRC hiện hành; không đổi IDs hoặc schema để chạy mock. Cần xác minh thực tế baud, by-id port, reconnect/CRC/TTL và một UART owner trên Jetson.
4. Giữ engine production `/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine`, dùng lại detector C++ OpenCV/YOLOv8n320/TensorRT FP16. Khi có Jetson, kiểm tra hash/bindings/SDK compatibility trước khi load; không train/re-export hoặc tải model mới cho milestone này.
5. ARM64 ABI/linker, CUDA/TensorRT engine execution, camera latency/ROI thật: **NOT_VERIFIED**. Không SSH hoặc mở webcam để kiểm tra trong lần làm này.

## 9. Checklist physical sau này

- [ ] HX711 calibration/zero ổn định và kiểm tra khối lượng sau reboot trên mounting thật; giữ PHYSICAL_VALIDATION_PENDING cho tới khi có evidence.
- [ ] Xác minh camera cố định/bbox thật, FULL_FRAME không giả IN_ROI, ROI_ENABLED review từ ảnh thật; thời gian AI/HC cùng cửa sổ và không stale.
- [ ] Servo MG996R góc45°/90° thực tế, nguồn5V riêng/chung GND, gate close/fault/timeout và food flow được kiểm tra trong phiên giám sát riêng; pump vẫn locked.
- [ ] Thử cấp feedback35g có cân thật, ghi actual/overshoot, sensor fault/USB loss/abort không giả success. Chỉ mở quyền production khi được owner cho phép sau đủ validation.
- [ ] MH-FMD GPIO2/VCC3V3/ACTIVE_LOW: boot OFF,2 tiếng200/200/200ms, cooldown60s; test an toàn riêng không chạy servo/pump.
- [ ] SQLite quota/idempotency/restart thật và meal consumption từ cân thật được đánh dấu đúng nguồn; kết quả fake không đưa vào lịch sử VALIDATED_SENSOR.

Native binary SHA256: `91913211d156f79aebd5d79e01d002da70333d60f555b9102ab3655f7560ce07`.

**E2E_OFFLINE_DEMO_READY: YES**
