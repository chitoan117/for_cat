# FOR_CAT — REAL HARDWARE PHYSICAL VALIDATION KIT

Kit riêng ngày29/10/2026, chuẩn bị **OFFLINE** cho người dùng cùng ChatGPT nghiệm thu.
Không phải production release/cutover. `release_candidate_v2` được giữ nguyên.

## Bắt đầu ở đâu?

**Handoff mới nhất:** `web_hardware/BACKUP_AND_WEB_HANDOFF.md`. A/B16MB đãcomplete,
directreadonlySHA đều56a04d58…6d9a8e16; không yêu cầu lượt3/oldLASTEXITCODE.
Layout/OTA vàlocalrollback đãinspect; runtimebank/ECHOvoltage/physicalrestore còn
NOT_VERIFIED. Không mởCOM8/reset/service hoặcdeploy để đẩyqua cácgate.
HX711 đo tĩnh đãphysicalPASS/owneraccepted; persistence/closedloop riêngchưaxácminh.

**Recovery lịch sử (đãsuperseded vềcompletion):** `recovery/OPERATOR_HANDOFF.md`. Owner đã
báo nhiều lầnROMread/reset với esptool3.3.3 và backup16MB chưa hoàn tất; bước hiện
tại đã có A/B matchingfiles; không reset/đổiUSB/flash tiếp. Oldprobes vẫngiữ nguyên.
Firmware sensor mới vẫn SHA`a6ad4b3f...ebb4b56`, không nhầm bảncũ`73b4b65f...527d621`.

**Lệnh đầu tiên trên Jetson, chỉ đọc, chưa mở serial:**

```sh
systemctl --user is-active for-cat-esp32-bridge.service
```

Nếu user-unit không tồn tại, kiểm tra `systemctl is-active for-cat-esp32-bridge.service`
và ghi đúng scope; không đoán rồi stop nhiều service. Agent chưa chạy lệnh này trênJetson.

**Trước ROM/flash/reset/unplug tiếp:** lưu status/log HX711 hiện tại. Calibration từng
RAM_ONLY; sau các reset hiệnRAMUNKNOWN, **không nằm trong full-flash backup**. Dữ liệu5/10/20/35g
đã có được giữ là owner evidence; không yêu cầu thử lại38g. Xem `HX711_EVIDENCE_NOTES.md`.

Thứ tự: electrical/port identification → capture HXstatus hiện tại → full16MBbackup
→ đối chiếu existing partition/active bootbank → sensor-only app flash do OWNER
→4ultrasonic/PIR → buzzer riêng → servo unloaded riêng → pump inert/polarityreview
→ chỉ sau đó mới conditional pump image/short supervised wet pulse.

## Các phần trong kit

- `firmware/`: snapshot từ Windows authoritative `FULL_HARDWARE_INTEGRATION_20261027/guard_tuning/esp32`, chỉ chỉnh kit-local. Không thay platform/framework/pinmap để chữa build.
- `SOURCE_REFERENCE.json`: hashes upstream trước chỉnh kit, đường dẫn remote owner cung cấp và acceptedRC hash. Không SSH nên không claim source remote đã trùng Windows.
- `artifacts/PROFILE/`: appbin, ELF, bootloader, partitions, boot_app0 và `layout.json` với offsets lấy từ actualPlatformIO/SCons + binary partition table. Factory merged image **không phát hành để flash**.
- `build_result.json`, `build_logs/`: kết quả Windows thực tế, version/packages/flags/image-info.
- `tools/`: build-only, flash-plan-only, bridgeguard/capture có explicit owner execution, existing HXlog analyzer.
- `tests/`, `test_output/`: software fakes/negative compile guards, không hardwarepass.
- `WINDOWS_BUILD.md`, `FLASH_AND_ROLLBACK.md`, `SENSOR_TESTS.md`, `ACTUATOR_PROCEDURES.md`.
- `FINAL_HARDWARE_REPORT_TEMPLATE.md`, `OWNER_OBSERVATIONS_TEMPLATE.json` để ghi evidence thật.
- `manifest.json`, `manifest.sha256`, `SHA256SUMS`, `result.json` sau finalize: integrity và readiness, không tự nghiệm thu phần cứng.

Kiểm integrity trênWindows, không SDK/device:

```powershell
& "D:\for_cat\.venv\Scripts\python.exe" -B "D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\tools\verify_manifest.py"
```

Copy templates thành file mới trong `evidence/` đểghi observations/report, không
sửa baseline đãhash. Conditionalpump artifacts/logs táchriêng, không ghi đè4image
banđầu hoặc baselinebuildlogs; kết quảfuturebuild không tựthayphysicalacceptance.

## Board/pins và mức quyền

ESP32-S3, flash16MB, **NO VERIFIED PSRAM**; baud115200. Giữ UART0 flags của source
đã dùng, không tự đổi sang nativeCDC vì tên `/dev/ttyACM0`. Owner chạy readonly
`udevadm info -q property -n /dev/ttyACM0`/`lsusb` và so sánh USB bridge/board. Nếu
port là nativeUSB khác contract UART0 thì DỪNG review, không vượt compileguard.

| Thành phần | GPIO | Image/quyền mặc định |
|---|---|---|
|HX711|DOUT4/SCK5|Sensor image đọc; không auto/manual tare/cal/save trong kitstation|
|SSD1306|SDA8/SCL9|Telemetry/display hiện có; không chứng minh panel thật đã hiển thị|
|HC-SR04#1|TRIG12/ECHO13|OFF tại boot, enable explicit từng kênh|
|HC-SR04#2|TRIG16/ECHO17|OFF tại boot, enable explicit từng kênh|
|JSN-SR04T#1|TRIG14/ECHO15|OFF tại boot; water role không tự bật pump|
|JSN-SR04T#2|TRIG18/ECHO10|OFF tại boot; geometry chưa nghiệm thu|
|PIR|11|Warm-up60s/debounce100ms, telemetry only|
|MH-FMD|2,3.3V|SeparateACTIVE_LOW image, HIGHoff trướcOUTPUT, driverack rồi testmanual|
|Servo|6,nguồn5Vngoài|Separatebench, PWMoff/DISARMED boot; explicitconfigure/ARM mới cóPWM|
|Pump/F5305S|7,nguồn5Vngoài|Image shippedINERT, không chạmGPIO7; chưa chọn cực tính|
|Button|21,activeLOW|Pullup, request log blocked; không feed|

RTC đã loại trong sensor image:16/17/18 thuộc HC2/JSN2, không DS1302 polling.
Sensor-only không chạmGPIO2/6/7. Buzzer chỉGPIO2. Servo chỉ actuatorGPIO6, pump
không bị điều khiển; pump bench chỉ actuatorGPIO7, servo không bị điều khiển.
UART và flash/I2C peripheral pins vẫn phục vụ giao tiếp; “onlyGPIO” chỉ scope driver.

## Giới hạn an toàn bắt buộc

- Bốn ECHO phải có bảo vệ≤3.3V phù hợpESP32-S3; owner đo thực tế và lưu ảnh/số đo.
  LệnhCONFIRM chỉ là acknowledgment, **không phải electricalproof**; firmware giữ
  `voltage_physically_verified=false` và `hardware_verified=false`.
- HXmodule5V không chứng minh DOUT/SCK logic3.3V. CommonGND, chén không chạm khung;
  không re-tare/refit để che drift. Sai sốstatic35g đãđượcchấpnhận; không yêu cầu
  tốiưu0.019g hoặc lặplạiweightseries. Không dùng displaydeadband làm bằng chứng zero.
- Ngắt nguồn tải servo/pump và nguồn buzzer khi flash, reset, thay image hoặc kiểm
  cực tính. Software không giữ được OFF trướcCPUsetup hoặc khi mất nguồn/reset.
- Bench không có autoCAT/feed/water/AI; global production ACTUATOR_OUTPUTS_ENABLED=0.
  Servo bench có quyềnPWM cục bộ sauARM, không phải unlock production.
- ServoARM tự attach candidateCLOSE có thể làm horn chuyển động; tháo tải/khôngfood,
  bàn tay tránh cơ cấu. STOP bỏPWM không chứng minh cơ khíđóng hoặc cắt5V motor.
- Pump không chạy khô. Chưa đoOFFpolarity/bootbias thì giữ imageINERT và tải ngắt.
- Script chỉ restore bằng finally/trap khi process còn chạy; SIGKILL/mất điện không
  bảo đảmcleanup. Khi lỗi, kiểm tra/khôi phục bridge thủ công theo scope đã ghi.

## Thu evidence dưới giám sát

Copy `tools/` vào thư mục mới trênJetson, ví dụ `/home/toan/hardware-kit-20261029/tools`.
Không cần chuyển `.pio` cache hoặc hostnative.exe lênJetson. Để flash từWindows,
giữ `artifacts/`, `build_result.json` và tools trênWindows; owner discover COM thật.

```sh
PY=/home/toan/for_cat/.venv/jetson-integration/bin/python
TOOLS=/home/toan/hardware-kit-20261029/tools
"$PY" "$TOOLS/serial_evidence.py" --profile hx_reference_legacy --output /home/toan/hx-status-before-reset --seconds 10
```

Mặc định PLAN_ONLY, không stopservice/openport. Sau khi review scope/port/power,
owner lặp với `--execute --confirm OWNER_SUPERVISED_SERIAL` để capture thật.
Tool stop bridge, kiểm portexclusive, mở **một** serial vớiDTR/RTSfalse, chỉTXstatus,
lưuraw+timestamp+ASCII/JSON/config/firmwareID, đóngport rồi restore originalbridge
state và kiểm lại. Serialopen/close có thể reset tùy board; không hứa bảo toànRAM.

Sensor/motion/bench commands trong quy trình dùng humanTTY `--interactive`:
`SEND <exactcommand>`, `OBSERVE <mô tả/measurementfile>`, `STOP`, `QUIT`.
Defaultkhông gửi ARM/ON/test. Muốn human-actuator commands phải thêm
`--actuator-supervised`; không nhận commandpipe. SENSORS enable cần
`--electrical-reviewed`; đây vẫn chỉ ownerack, không kết luận điện áp.
Không mởpicocom/screen/monitor thứhai cùng port. Thu video/âm thanh bằngthiết bị khác.

## Kết quả phần cứng

NgoàiHX711staticđãowneraccepted (xemHX711_ACCEPTANCE.json), cácphysicalflagsmới
trongkit/result/template giữ NOT_VERIFIED cho đến review rawlog,
đấu dây, quan sát owner và điều kiện test. ACK hoặc movementGPIOsimulated không đủ.
Bridge có thể kết nốiUART nhưng validtelemetry0 nếu firmwareHX711_REFERENCE không
đúngdiag_current_hardware. Không sửa parser để che mismatch; lưu hai kết quả riêng.
