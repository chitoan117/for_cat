# Tiếp tục phần cứng thật — M3 closeout / M4 sensor-only

## 1. Đã có evidence gì?

Theo facts người dùng đã quan sát: Nano2GB/Ubuntu18.04.6/L4T32.7.6/Python3.6.9 và GPU/custom OpenCV stack; camera4a54:5233,/dev/video0,MJPG720p300frames/0fail/10.008s/29.97FPS; ESP32-S3 revv0.2,40MHz,flash16MB,**PSRAM NOT DETECTED**; bridge1a86:55d3/cdc_acm,/dev/ttyACM0; factory flash397312B/no-stub/hash verified/reset; PING100/ACK01 and GET_STATUS101/SYSTEM_STATUS01 correlated/CRC PASS; unplug/re-enumeration PASS. **Post-reconnect protocol chỉ USER-REPORTED PASS**, chưa có raw receipt; xem `M3_PHYSICAL_VALIDATION_RECORD.md` / machine record. Không dùng1080p quảng cáo làm FPS đã đo.

M4 chưa có kết quả sensor/servo/pump. GPIO mapping là candidate, actuator0 và pins14/15 vẫn-1; không nối chấp hành. Full modern API không chạy Python3.6; dùng utilities độc lập, không đổi system Python/CUDA/OpenCV/TRT. Mốc chính thức giữ M2→M3 closeout pending; không tự công nhận M3 hoàn chỉnh/M4.

## 2. Đóng evidence USB trước nếu cần

Trong `jetson/` trên Nano:

```sh
python3 -m bringup.devices
python3 -m bringup.serial_probe --device /dev/ttyACM0 --count 3 --save ../evidence/serial/UNIQUE_connected.json
```

Giữ HW_SAFE binary, sensor/servo/pump ngắt. Unplug thật → node biến mất → một probe cũ phải FAIL; reconnect/re-enumerate → probe mới phải matched ID/CRC/ACK/SYSTEM_STATUS. Lưu tên mới và actual image hash/date; không dựng transcript từ facts ban đầu.

## 3. Firmware đầu tiên: diag_i2c

**First M4 = OLED I2C ONLY:** tắt nguồn trước khi đấu; chỉ OLED3.3V-compatible, SDA→GPIO8,SCL→GPIO9,GNDchung/pull-ups3.3V. Không nốiRTC/HX711/ultrasonic/button/buzzer/servo/pump trong phép scanOLED đầu. Voltage/wiringkhôngrõ/bấtthường→STOP. **RTC hardware changed from planned DS3231 to available DS1302 during M4 physical bring-up.** RTC là3-wireCLK16/DAT17/CE18, khôngI2C; bước riêng sauOLED, xem `DS1302_BRINGUP.md`.

Sauwiringreview: builddiag_i2cWindows→transferbundle→Jetsondry-run/no-stubflash→ASCIIscan. OLEDcandidate0x3CphảiACKthực; thiếu0x68khônglàRTClỗi vìDS1302khôngI2C. Unexpected/missingOLEDaddress/busunstable→reviewactualmodule/wiring/power; khônghardcodePASS. Handoff: `FINAL_OPENCODE_HANDOFF.md`.

Windows root:

```powershell
& .\scripts\build_esp32_windows.ps1 -EnvName diag_i2c
```

Transfer bundle/hash rồi Jetson root:

```sh
sh scripts/flash_esp32_from_jetson.sh --profile diag_i2c --port /dev/ttyACM0 --image /ACTUAL_PATH/firmware.factory.bin --sha256 ACTUAL_SHA256
# DRY_RUN; sau khi review range/NVS, thêm --apply --allow-factory-overwrite.
```

Actual esptool luôn3.6 system/no-stub/115200, ROM flash_id16MB, write0x0 và verify; no erase-all. Các lần đổi mode sau giữ cùng partition/bootloader dùng firmware.bin0x10000 `--application-only` để không mất NVS. Chi tiết/hash/verify/recovery: `WINDOWS_BUILD_JETSON_FLASH.md`.

## 4. Thứ tự nối M4 (tắt nguồn khi đổi wiring)

| Bước | Nối candidate / firmware | Quan sát cần ghi |
| --- | --- | --- |
| I2C scan/OLED |SDA8,SCL9,3.3VcompatibleVCC/pull-ups,GNDchung; RTCkhôngtrênbus |ActualACK/summary;OLED0x3Ccandidate, khôngcần0x68 |
| RTC DS1302 |3V3→VCC,GND,CLK16,DAT/IO17bidirectional,CE/RST18; label/batteryreview; `diag_rtc` |BCD/date/CH/WP/readback/reboot/retention; bootreadonly, explicitsetonly |
| HX711 | DOUT4,SCK5,logic rail/cell excitation/leads/mount được review; `diag_hx711` | Raw readiness/stability/timeout trước; tare/reference/errors là bước riêng |
| Food echo | TRIG6,ECHO→divider/shifter→GPIO7,GND; `diag_food_sensor` | Actual range, raw/filtered distance,no echo/OUT_OF_RANGE trước geometry |
| Water echo | TRIG10,ECHO→divider/shifter→GPIO11,GND; `diag_water_sensor` | JSN variant/blind zone/mount/surface, raw/filtered/timeout, state/would-request; pump luôn OFF |
| OLED/button/buzzer | SDA8/SCL9,button GPIO12→GND INPUT_PULLUP active LOW;GPIO13 chỉ sau review active/passive/current/driver/polarity; `diag_oled_button_buzzer` | Actual display, one short intent/rejection, bounded sound if safe reviewed driver |

**ECHO5V không được nối thẳng GPIO7/11.** Divider minh họa: ECHO→10kΩ→GPIO,GPIO→15kΩ→GND, cho khoảng3.0V ở nguồn5.0V. Đây là ví dụ tính toán, không voltage PASS; review tolerances/actual high level/edges bằng dụng cụ phù hợp, DMM trung bình pulse không chứng minh peak. Hoặc dùng level shifter đúng hướng. Trigger3.3V compatibility cũng phải review. Servo/pump nguồn/tín hiệu vẫn ngắt, không dùng rail logic nuôi chúng.

## 5. Output/commands mong đợi — mẫu, KHÔNG là kết quả thật

Miniterm ASCII115200, close bằngCtrl+]. `help`, `status` sẵn; JSON1 lần/s, scan one address/tick, không binaryv1 đồng thời.

- Startup: `FORR_CAT M4 mode=diag_i2c HW_SAFE actuator=0 servo=0 pump=0 pins_reviewed=1 ... ASCII diagnostics, NOT UART v1`; candidate pins/PSRAM NOT USED line. Wrong mode/SIM/output → STOP.
- Scan:actual`I2C_ACK address=0x3C identity NOT_VERIFIED`nếuOLEDresponds,summary112probes/respondingN;0x68khôngcònRTCexpectation. Gõscanđểrepeat;addresskhôngchứngminhidentity/accuracy.
- RTC DS1302: `rtc_result=HEALTHY`/NOT_CONNECTED/INVALID_TIME/CLOCK_HALTED/IO_ERROR; valid`rtc_utc`YYYY-MM-DD HH:MM:SSelseNULL. Explicit`set-utc ACTUAL_UTC_DATETIMEZ CONFIRM`→readbackvalidated/display; priorWPpreserved,CHclearedonlyatset,year2000–2099. NoOSF/I2Cstatus/buildtimefallback. UTCreference`date -u`chỉkhiclockJetsonđượcvalidate.
- HX711: đọc raw có thể NOT_CALIBRATED/grams=null; `avg 16`→`AVERAGE raw=...`; DOUT không ready→NOT_CONNECTED/TIMEOUT. Sau khi stable, `tare 16`, `cal ACTUAL_REFERENCE_GRAMS 16`, `validate ACTUAL_MASS 16`; ghi thật factor/error/repeatability, không tolerance/accuracy giả. `save YES` chỉ khi calibration accepted; application-only switch/reboot để kiểm tra load.
- Ultrasonic startup chưa toggleTRIG: `ECHO REVIEW REQUIRED...`; sau voltage/module review nhập `range ACTUAL_MIN_CM ACTUAL_MAX_CM` (software≤400cm), rồi `echo-3v3 CONFIRM`. `range` không là geometry calibration. Software default1..400 không phải measured blind zone. No echo→TIMEOUT, invalid range→RANGE_INVALID/null; geometry `food-geometry FULL EMPTY` / `water-geometry FULL EMPTY` chỉ giá trị đo. Không lấy false blind-zone echo làm FULL.
- Button: `FEED_INTENT REJECTED SAFE_BUILD_ACTUATORS_DISABLED (no servo call)`; short release one event.
- Buzzer mặc định NOT_CONFIGURED,GPIO chưa drive. Chỉ reviewed active-high driver mới `buzzer-driver ACTIVE_HIGH CONFIRM`, rồi `buzz confirm|warning|fault`. Passive/module khác cần review, không gắn tải lớn trực tiếpGPIO.

## 6. STOP, actuator gate và thesis evidence

STOP nếuchip/flash/hash/partition/node/flags sai,5V input/pull-ups, unstable power,ADC rails/no echo/RTC fault, wrong geometry/blind zone, buzzer type/current không rõ hoặc bất kỳ chấp hành chuyển động. GhiFAIL; không bậtPSRAM/servo/pump hay giảgramstime để bỏ lỗi.

Servo14/pump15 mới là candidate tài liệu; code vẫn-1/output0. Không enable trong pass sensor này. Chỉ sau evidence sensors/time/NVS/power/mechanics và riêng actuator firmware/interlocks/closure/stop/current/jam/leak/timeouts đã review mới xét enable ở task khác; M4 integrated PASS cần dữ liệu thật, không compile/genericGPIOattestation.

Lưu actual source/image/hash/profile,device/module/wiring/voltage/reference/timezone/commands/raw logs/photos, expected-vs-actual/pass-fail và lỗi/recovery theo `LAB_NOTE_TEMPLATE.md` / `EVIDENCE_NAMING_STANDARD.md`. Không MAC/person IDs dư thừa, không data/rawcatvideo trong source. Agent host builds/fakeI/O không thay kết quả bench.
