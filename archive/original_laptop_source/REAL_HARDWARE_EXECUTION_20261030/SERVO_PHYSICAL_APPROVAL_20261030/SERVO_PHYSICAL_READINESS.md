# SERVO GPIO6 — BLOCKED

Kiểm tra offline ngày30/10/2026, hash thực đo lúc **08:53:08 UTC**. Không build, không chạy lại suite, không mở thiết bị.

## Image chọn cho đợt này

`D:\for_cat\REAL_HARDWARE_EXECUTION_20261030\INTEGRATED_MANUAL_CANDIDATE\build_safe_txatomic\artifacts\firmware.bin`

- **415456 bytes**, SHA256 **MATCH**: `77faf09775e55731b08c511ac852273b9839963c081ebe924035f8f9aecaac93`.
- Build result và hai helper `manual_console.py`, `flash_plan.py` khớp `RELEASE_RECEIPT.json`. Build/header/image-info đã PASS được giữ nguyên: ESP32-S3 chip9,16MB/no PSRAM/UART0, secure_version0; partition table khớp baseline.
- Phù hợp **thử manual biên nhỏ sau các gate**, không phải image closed-loop tự động. Không thay bằng feed-link377840bytes hoặc dual423712bytes; hai bản đó, Bridge mới và Web giữ nguyên.
- Build offset0x10000 không phải bằng chứng running partition. Chưa có offset được phép ghi.

## Những điều được giữ nguyên

| Bằng chứng | Phạm vi đã đủ |
|---|---|
| Manual build/30 regression | PASS_OFFLINE, không chạy lại |
| BackupA/B16MB và rollback381984bytes | Integrity/layout đã được chấp nhận; không đọc backup lượt3 hoặc thử restore để lấy PASS |
| HX711/load-cell35g đo34.981g | OWNER_ACCEPTED static PASS; không cân/tare/refit lại |
| GPIO6servo,7pump,2buzzer; nguồn chung5V–10A | OWNER_CONFIRMED; không chứng minh model/điện áp tại servo/pulse an toàn |
| Hai dây motor tháo khỏi OUTPUT F5305S | OWNER_CONFIRMED cách ly tải; **chưa có ảnh hai đầu dây được cách điện/cố định**; không yêu cầu tháo lại |

## Điều kiện còn thiếu

Xem `BLOCKERS_TO_FLASH.md`: running bank/security/recovery/executor; hệ số HX chính xác hoặc NVS tương thích được chứng minh; servo model/V+/GND/ngắt tải và pulse được duyệt; bảo vệ ECHO; cách điện đầu dây motor; scope/approval và handback. **Chưa đủ READY_FOR_OWNER_APPROVAL.**

## Lệnh/timing đã xác định từ source — chưa cấp quyền thực thi

Boot DISARMED/PWMoff. Configure một lần/boot;1000–2000µs điện, span≤100µs, tối đa3arms/moves. ARM có thể chuyển động ngay về CLOSE; armexpiry2s, OPEN250ms→CLOSE350ms→PWMoff, harddeadline3s. Không đoán góc hoặc dùng1450/1550 từ mock làm preset thật.

Sau flash/boot/hash và phê duyệt chuyển động, trong console người thật:

```text
SESSION
SEND servo status
SEND servo configure MIN_US MAX_US CLOSED_US OPEN_US CONFIRM
SEND servo arm YES
SEND servo open
```

Các pulse là placeholder phải được xác minh/duyệt. OPEN tới MCU trong2s sau ARM. Chờ tự đóng/PWMoff rồi đọc status/log/video; không gửi thêm CLOSE sau DISARMED để tìm ACK. `SEND servo close`/`SEND servo disarm` chỉ dùng khi còn ARMED/MOVING và đã duyệt. `STOP`/QUIT chốt FAULT/PWMoff; không tự reset/re-arm để vượt budget. Khi bất thường, ngắt tải servo bằng đường đã duyệt; PWMoff không chứng minh cửa đã đóng.

Full CLOSED→OPEN→CLOSED chỉ được thử khi hai pulse thực tế an toàn nằm trong envelope hiện có. Nếu hành trình cần >100µs: dừng, lưu kết quả biên nhỏ; không nới/rebuild trong đợt này. Manual có thể được nghiệm thu bằng quan sát/video của owner; thiếu cảm biến cửa không được biến thành chứng cứ đóng cửa tự động cho E2E35g.

**Kết luận: BLOCKED. APP FLASH NO-GO; chưa có phê duyệt kích servo.**
