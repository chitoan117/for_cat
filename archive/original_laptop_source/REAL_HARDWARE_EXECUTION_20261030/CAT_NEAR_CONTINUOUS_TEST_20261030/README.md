# FOR_CAT — complete continuous-servo CAT/near/HX711 supervised test project

Đây là project PlatformIO ESP32-S3 đầy đủ và sender Jetson riêng. Đã build/test
offline; chưa nạp, chưa mở Serial, chưa chạy tải. Đây là giao thức test mới,
không phải bản thay thế trực tiếp cho Bridge/API production hiện tại.

## Luồng hoạt động

1. Boot: GPIO6 không phát PWM; không tự ARM/chạy. Đọc calibration NVS
   `m4-calibration/sensors-v2` ở chế độ read-only. Không tự tare/refit/save.
2. Owner xác nhận đã kiểm tra cửa đóng bằng `inspect closed`. Journal riêng
   `fc-cr-test/journal` ghi nhận inspection; không xóa high-water dose ID.
3. `arm A` hoặc `arm B` cấp quyền cho **một lần** trong 30 giây, chưa quay servo.
4. AI CAT confidence ≥0.8, tuổi nguồn + biên vận chuyển ≤750 ms; ba mẫu
   HC-SR04 liên tiếp 2..20 cm, cách nhau không quá 250 ms. Cần heartbeat owner.
5. Ghi pending/dose ID trước motion; lấy bốn mẫu baseline ổn định; quay chiều
   mở trong thời gian đã đo rồi phát neutral; tiếp tục đọc khối lượng.
6. Khi **khối lượng tăng so baseline ≥25 g**, quay chiều đóng trong thời gian
   đã đo rồi neutral. Đợi settle, lấy bốn mẫu ổn định. Mục tiêu nominal 35 g;
   dải cuối được chấp nhận để quan sát là **30..40 g**. Không tự bù thêm.
7. Kết quả trong dải là `MEASURED_NEEDS_OWNER_CONFIRMATION`, journal vẫn pending.
   Không có position feedback nên không báo physical closed/auto COMPLETE.
   Frame CAT lặp lại không tạo khẩu phần mới. Muốn bữa khác phải owner inspect
   rồi ARM lại; không có tự động refeed theo timer.

**25 g chỉ là cutoff thử, không đảm bảo final 35 g.** Độ trễ cân median-3,
chu kỳ HX711, servo và hạt đang rơi có thể làm final vượt 40 g. Cần đo thực tế
và điều chỉnh flow/cutoff; thời gian quay không thay cho cân lượng cấp.

## Cấu trúc

| File | Vai trò |
|---|---|
| `firmware/platformio.ini` | ESP32-S3, Arduino, UART0 115200, build riêng |
| `firmware/src/cat_continuous.cpp` | Toàn bộ setup/loop, parser, sensor, journal |
| `firmware/include/user_settings.h` | Thông số thực cần điền |
| `firmware/include/continuous_dispense.h` | FSM; cutoff 25 g supervised-only |
| `firmware/include/continuous_servo.h` | Pulse neutral/hai chiều quay; không dùng góc |
| `firmware/include/m4/hx711*.h` | Driver HX711 cũ giữ nguyên |
| `jetson/sender.py` | Một chủ UART; nhận AI qua Unix socket, console và JSONL |
| `jetson/cat_ai_publish.h` | Hook C++ cho kết quả inference hiện có |
| `jetson/meal_report.py` | Tổng hợp hai cửa sổ cân ổn định A/B từ log |
| `tests/`, `verify.py` | Kiểm tra mới; có chạy actual app loop với mock hardware |

## Thông số cần điền trước một lần thử thực

Trong `firmware/include/user_settings.h`, tất cả pulse/hành trình thực đang
để **0/false** nên mặc định không thể ARM:

- Xác minh servo đúng loại quay liên tục; đo neutral và biên deadband.
- Điền `safe_min_us`, `safe_max_us`, `neutral_us`, `neutral_low_us`,
  `neutral_high_us`, `open_rotation_us`, `close_rotation_us`; xác nhận các flag.
  Hai chiều phải nằm hai phía deadband; cửa sổ pulse ban đầu ≤100 µs trong
  1000..2000 µs. Các số trong test là **fixture**, không phải preset phần cứng.
- Điền `opening_ms`, `closing_ms`, `travel_timing_verified` theo hành trình thực.
- Xác minh điện áp ECHO và range rồi đặt `hc_sr04_wiring_reviewed=true`.
- Giữ cutoff thử `closing_lead_g=10` → 35−10=25 g. Cờ
  `supervised_early_close_trial=true` chặn Mode::Automatic ở controller.
- `supervised_bounded_fault_close=false` mặc định: lỗi cân/overshoot yêu cầu
  neutral và inspection. Có thể chọn true sau khi review cơ cấu: lỗi khi đang
  mở/chờ khối lượng có một lần đóng bounded chưa xác minh. **STOP/lease loss
  luôn yêu cầu neutral**, không tự đảo chiều. Neutral không bảo đảm chặn hạt.
- Nếu NVS thiếu calibration, code báo chưa calibrated. Chỉ import RAM backup
  **đúng full precision** bằng `exact_calibration_import_reviewed`, `tare_counts`,
  `grams_per_count` và provenance. Factor ở đây là **g/count**, không counts/g.
  Không dùng offset xấp xỉ hoặc offset từ sketch reference lịch sử để restore.

Pin: HX711 DOUT4/SCK5; servo6; HC-SR04 TRIG12/ECHO13. Pump7 và buzzer2 không
được khởi tạo/kích. Mạch ECHO và DOUT phải tương thích đầu vào ESP32 3.3 V.

## Build offline

Từ thư mục `firmware`:

```sh
python -m platformio run -e cat_continuous_test
```

Đầu ra APP: `.pio/build/cat_continuous_test/firmware.bin`. Toolchain cũng sinh
factory image trong cache build; file gộp đó không được đưa vào gói handoff.
Build offset không chứng minh runtime bank/recovery/calibration preservation.
Các điểm chưa giải quyết về flash/bank/security và giữ calibration vẫn tồn tại;
gói này không kèm lệnh upload.

Kiểm tra mới, từ project root (chọn label chưa có; chỉ chạy offline):

```sh
python verify.py --label local --cxx /path/to/zig
```

Có thể dùng `--cxx /usr/bin/g++`. `BASELINE.json` chứa hash để kiểm tra các
header kế thừa; `continuous_dispense.h` là header kế thừa duy nhất được sửa.

## Jetson: một chủ Serial

Sender dùng pyserial 3.5 (`jetson/requirements.txt`), yêu cầu Linux,
`systemctl --user`, `fuser`. Nó từ chối khi Bridge active hoặc TTY đang bị giữ,
không tự stop/start service. DTR/RTS được đặt false trước open, nhưng mở port
vẫn có thể reset một số board/adapter và làm mất calibration chỉ có trong RAM.
Không mở port hiện tại trước khi xử lý backup/đồng ý maintenance như đã bàn.

Sau khi firmware này đã được review/nạp theo kế hoạch riêng và UART được bàn
giao, ví dụ owner-run từ project root trên Jetson:

```sh
python3 jetson/sender.py \
  --ai-socket /run/user/$(id -u)/for-cat-test-ai.sock \
  --log meal-session-001.jsonl
```

Tên log/socket phải mới; không ghi đè. Console:

```text
inspect closed
arm A
stop
quit
```

Chỉ gõ `inspect closed` sau kiểm tra thực sự; lệnh này ghi journal. Một `arm A`
không tự tạo CAT. Sender gửi HB mỗi 300 ms; mất lease 1500 ms thì MCU neutral
và khóa. Ctrl-C/thoát gửi STOP best-effort; nếu UART mất, lease MCU vẫn hết hạn.
ACK là tiếp nhận lệnh, không phải xác nhận cửa đóng/kết quả cấp. Partial write
không retry. Boot thay đổi thì sender thoát, không tự khôi phục ARM.

Bridge production dùng protocol khác: **không handback Bridge cũ vào firmware
test này**. Trước khi trở về production cần phục hồi firmware/protocol tương
thích theo kế hoạch maintenance. Service vốn bị dừng từ phiên trước có thể
được owner hoàn trả ngay trong khi board vẫn chạy firmware cũ; agent chưa thực
hiện việc này và không có xác nhận trạng thái service live mới.

## Gắn vào AI C++ hiện tại

Không cần mở camera hoặc Serial thứ hai. Include `jetson/cat_ai_publish.h`, tạo
một Publisher trỏ đúng socket của sender. Trong callback inference hiện có:

```cpp
cat_test_ai::Publisher publish("/run/user/1000/for-cat-test-ai.sock");
// once per ORIGINAL inference result, not repeated from cached detections:
publish.publish(frame_sequence, original_capture_monotonic_ns,
                cat_detected ? cat_test_ai::Label::Cat : cat_test_ai::Label::None,
                detection_confidence);
```

Thay UID/path bằng giá trị thực. Timestamp phải lấy từ CLOCK_MONOTONIC trên
**cùng Jetson**, ở thời điểm capture; confidence 0..1; sequence uint32 tăng.
Gửi cả kết quả không-CAT; không đổi timestamp/sequence của detection cũ để giữ
CAT sống. Hook nonblocking, lỗi gửi không được coi như inference đã đến MCU.
Generic CAT không xác định đúng con mèo nào.

UART mới: `FC1 boot seq echoed_device_ms OP args*CRC16\n`, CRC16-CCITT init
FFFF. Telemetry JSON mỗi 250 ms cung cấp boot/ms/seq. CRC, boot nonce, seq tăng
và echo tuổi ≤750 ms chống lỗi/lặp/trễ; đây không phải cơ chế authentication.

## Quan sát món A/B

JSONL ghi dữ liệu thiết bị cùng giờ nhận UTC/monotonic: dose ID, food A/B,
baseline, actual dose, cân hiện tại, sample time, calibration generation,
offset/factor đầy đủ, nguồn calibration và physical_closed=null.

Owner xác nhận cửa đã đóng và ghi điều kiện quan sát (bát không bị nhấc,
thêm/bớt hạt, đổ vãi, con vật khác…). Chọn hai cửa sổ **≥4 status cân ổn định**
đầu/cuối cùng bữa trong log, không gồm dòng ACK. Các số dòng 1-based inclusive:

```sh
python3 jetson/meal_report.py --log meal-session-001.jsonl \
  --meal-id A-001 --start-lines 100 103 --end-lines 500 503 \
  --notes "owner confirmed closure; describe spillage/other animals/bowl handling" \
  --output meal-A-001.json
```

Đây chỉ là ví dụ số dòng, phải chọn từ log thật. Tool loại dữ liệu stale,
không ổn định, đổi calibration/boot/dose, thêm khối lượng hoặc cửa sổ chồng nhau.
Nó lưu lượng đầu/còn lại và **apparent_removed_g**, không khẳng định toàn bộ
lượng giảm là mèo ăn; không tự kết luận thích/không thích. So sánh A/B cần nhiều
bữa với điều kiện/giờ/độ đói có thể so sánh. Project không tạo lịch sử bữa thật.

## Kiểm chứng và giới hạn

Xem `RESULT.json`, `verification_*/RESULT.json` và log build trong `evidence_*/`.
Các thư mục evidence cũ giữ lỗi thử syntax-only của Zig wrapper; kết quả cuối
dùng compile-only object ARM64 từ `tests/ai_hook.cpp`, không chạy trên Jetson.
Test loop dùng setup/loop, parser, HX711 bits, HC-SR04, LEDC/NVS adapter thật
trên mock I/O; tham số pulse/test mass không phải calibration thực.
Không có test trên board/Jetson ARM64, không xác minh cơ khí hoặc kết quả final
thực tế. Những phần này cần thông số/đo đạc owner trước lần thử supervised.
