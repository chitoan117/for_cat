# FOR_CAT — Overnight offline continuation

## Kết quả thực hiện

Đã hoàn thành phần offline khả thi, theo thứ tự maintenance → contract/integration
→ behavior/identity → closed-loop simulation → API/Flutter validation. Mọi thay đổi
mới ở `offline_continuation/` và kit `maintenance_readiness/`. Các release cũ trong
thư mục này, production, firmware artifacts và manifest590 được giữ nguyên.

### 0. Maintenance readiness
Hoàn tất 5 tài liệu bắt buộc và default-PLAN tooling. **21 fake-service tests PASS**,
gồm interrupt, stop lỗi nhưng state đã đổi, evidence-write failure, busyport,
changedunit/binary, originallyinactive và no-write-plan khi gate thiếu. Tests dùng
injected fake runners, không gọi services/Serial. Source/tool audit đã xác nhận
WindowsPython3.14.3/esptool4.8.1 và giới hạn3.3.3/efuse filtering. Hồ sơ và lệnh USER
ở `HARDWARE_PHYSICAL_BRINGUP_20261029/maintenance_readiness/`.

### 1. Telemetry → API → Flutter
- Dùng full4339-byte **synthetic mutation của actual firmware-loop report**.
- Wiremode giữ `diag_current_hardware`, kitprofile `diag_four_ultrasonic`.
- Real C++14/json-c parser/framer executable xử lý fragment1/7/127/8192,
  exact8192accepted/8193dropped, typedschema/missing/duplicate/unsafe rejection.
- Real reader/provider đọc SQLite tạm, optional candidate router và ASGI tạo
  `fixtures/api_contract.json`, gồm8states cho Flutter dùng trực tiếp.
- New C++ session timeline chứng minh frozen uptime không được heartbeat giả làm
  fresh, reconnectchưa có data vẫnSTALE, unsafe latch không tựclear.
- 2HC/2JSN độc lập, JSN1 geometry/null, JSN2TBD, HXgrams authority, PIR/OLED/button
  mapping. Monotonic hostage tách device uptime, không giả là UTC.

### 2. Identity / FOOD_ROI / preference
New portable C++14 `owner_behavior.h` là **policy simulation**, không phải model.
UNKNOWN/OTHER_CAT/DOG/publicCAT không được tự thành OWNER_CAT. OWNER_CAT chỉ được
assert trong explicit synthetic-owner fixtures; production actuator executionfalse.
Test reviewedFOOD_ROI+distance+debounce, stale/lost/duplicateAI, mixedDOG, leave/
rearrival/cooldown2h, eating-vs-sniffing và không top-up khi cân giảm. Preference
LIKE/DISLIKE/UNCERTAIN dựa trên thresholds cấu hình, freshstableweight/generation/
observationcontinuity. Không gọi đó là chứng minh ý thích thật của mèo.

### 3. 35g software closed-loop
Tái sử dụng actual portable `m4::dispense_bench::Controller` qua fakeOutput/fakeHX
observations. Đã phát hiện và sửa **candidate-only**: globalmax45g trước đây cho
phép36g thành COMPLETE dù target35/tolerance0.2. Newtargetband guard trảFAULT /
TARGET_OVERSHOOT. Probe baseline/fixed và regression được lưu nguyên output.
Nominal bowl95→130g = added35g; duplicate, timeout, invalid/staleHX, no-progress,
disconnect và uncalibrated đều có deterministic coverage. Không điều khiểnservo.

### 4. API / Web
Actual endpoints `/api/v1/status`, `/feed/manual`, `/feeding-history`,
`/drinking-history`, `/sessions/feeding` được dùng qua mock transport/temporaryDB.
ACK-only poll không thànhSUCCESS; disconnect giữPENDING; terminalSUCCESS/ERROR chỉ
sau FEED_STATUS. Idempotency không tạo request thứ2. Mockdrinkinghistory ghi rõ
MOCK, volumeNULL, không suy drinkingAI hoặc WATER_ROI.
Flutter candidate reuse AppCard/LiveCameraPanel dependency; widget camera bị tắt
trongtests. Simulationbanner, null/states/age/reasons và ACK/finalhistory đã kiểm.

## Trạng thái cuối
- VERIFIED PASS: host builds/analyze, new artifact/source integrity checks.
- SIMULATION PASS:21maintenance tests;11C++groups/158checks;6timelines;
  26uniquebackendcases;12uniqueFluttercases (chi tiết focused runs ở TEST_RESULTS).
- NOT_RUN: newcandidateARM64, actualOpenCV/TRT/camera integration, productiondeploy.
- BLOCKED: ownercatdataset/model và pre-flash runningbank/security/electricalgates.
- NEEDS_PHYSICAL_VALIDATION: closed-loop35g, mechanism/overshoot, recovery thực.

**APP FLASH NO_GO. Servo/pumpLOCKED, manualbuzzerDISABLED.** Không SSH, camera,
Serial, flash hoặc runtime/service mutation đã được agent thực hiện.
