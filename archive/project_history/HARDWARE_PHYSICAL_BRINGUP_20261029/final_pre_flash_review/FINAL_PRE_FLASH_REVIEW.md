# FOR_CAT — Final pre-flash review

## Quyết định hiện tại: **NO-GO — chưa đề xuất APP-only flash**

Đã ghi nhận **GCC75_R1 native ARM64 PASS** và **lắp đặt phần cứng hoàn tất** theo
xác nhận mới của USER. Giữ nguyên PASS; không build/replay/test lại. Existing
`result.json` native chưa có trong local kit được review: chỉ cần đính kèm file
đã có để hoàn chỉnh provenance, không chạy lại bài kiểm thử.

Hồ sơ hiện hành là `GO_NO_GO.json` trong thư mục này. Các trạng thái ARM64 FAIL /
NOT_RUN trong hồ sơ GCC75_R1 cũ là lịch sử trước xác nhận mới. Hồ sơ qualified
590 files / manifest `2d9c5d18e8b911874b033b4e93784ba7a34f591011002c46411a191c5196099c`
được giữ nguyên; addendum này có integrity record riêng, không sửa 9-file SFTP delta.

## 1. Những bằng chứng được giữ PASS

| Gate | Kết quả / nguồn |
|---|---|
| ARM64 native | PASS do USER xác nhận trên Jetson; không retest |
| Lắp đặt | Hoàn tất do USER xác nhận; không tự suy thành số đo điện áp/nguồn |
| Backup A/B | Hai file hoàn tất, mỗi file 16777216 bytes; SHA256 `56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16` |
| Existing partition table | Unique MD5 table tại 0x8000 khớp sensor layout |
| Capacity | Sensor app 400304 bytes nằm trong app0 0x10000 / size0x640000 |
| Local rollback | Original app 381984 bytes, checksum/hash hợp lệ, SHA256 `820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826` |
| HX711 static/35g | OWNER-accepted PASS; không cân lại, không tối ưu calibration |

Nguồn: `web_hardware/accepted_backup_pair.json`, `backup_and_contract_review.json`,
`artifacts/diag_four_ultrasonic/layout.json`, `HX711_ACCEPTANCE.json` và owner message.
Không yêu cầu backup lượt3 hoặc LASTEXITCODE cũ.

## 2. Running partition — vẫn thiếu bằng chứng bắt buộc

Backup cho thấy standard OTA metadata chọn **candidate app0/0x10000**. App1 tại
0x650000 toàn FF, không có valid app để dựa vào automatic fallback. Đây không phải
runtime bank proof của ESP32 ở thời điểm hiện tại.

Cần existing log từ **lần boot ESP32 hiện hành**, có line actual loaded/running
partition, ví dụ `Loaded app from partition at offset ...` do bootloader phát ra
hoặc actual runtime partition report của firmware. Phải đối chiếu board identity,
timestamp/boot continuity và không có flash/reboot thay đổi state sau log đó.
ROM `entry` / RAM load address 0x403... không phải partition offset. Không điền
0x10000 chỉ vì đó là build default hoặc OTA candidate; không tạo line log giả.

Đọc journal hoặc existing capture theo `USER_READ_ONLY_CHECKS.md`. Bridge có thể
không lưu raw boot lines; không tìm thấy log nghĩa là gate vẫn UNKNOWN. Jetson
sysfs/service metadata không thể tự tiết lộ running partition của MCU. Nếu không
có existing evidence, giữ NO-GO; việc thu dữ liệu qua Serial cần một maintenance
scope được USER duyệt riêng, không thực hiện trong phiên review này.

## 3. Security/eFuse — cần decoded evidence, không suy từ checksum

Existing `build_logs/diag_four_ultrasonic_image_info.log` cho thấy:
- ESP32-S3 chip ID9, min chiprev0.0; owner board rev0.2.
- **Secure version của image mới = 0** (line48).
- Image checksum/validation hash valid là integrity bytes, không chứng minh
  Secure Boot signature acceptance, flash-encryption state hoặc anti-rollback.

Cần existing security/eFuse report gắn đúng board và thời điểm còn hiệu lực:
`SECURE_BOOT_EN`, decoded flash-encryption state / `SPI_BOOT_CRYPT_CNT`,
`SECURE_VERSION` và bootloader anti-rollback policy; `DIS_DOWNLOAD_MODE`,
`ENABLE_SECURITY_DOWNLOAD`, manual-encryption/download/transport restrictions
áp dụng (ví dụ `DIS_DOWNLOAD_MANUAL_ENCRYPT`, `DIS_USB_SERIAL_JTAG_DOWNLOAD_MODE`).
Chỉ gửi flags/decoded policy, không gửi key material.

Điều kiện xem xét:
- Nếu anti-rollback được enforce và eFuse secure-version lớn hơn0, image mới
  secure_version0 không đạt; phải dừng. Không burn/lower/bypass eFuse để ép flash.
- Secure Boot bật: cần chứng minh **cả image mới và rollback** có signature/key
  trust/revocation policy phù hợp. Bộ kit chưa cung cấp proof này.
- Flash encryption bật: cần reviewed provisioning/write/recovery path phù hợp
  với download restrictions và bản backup. Không giả định raw16MB/app restore
  plaintext là đường khôi phục hợp lệ cho encrypted device.
- Download bị khóa/restricted: phải review khả năng recovery trước khi ghi.

Không chạy `espefuse summary`, `esptool get_security_info`, flash-ID/read/verify
qua device trong phiên này. Dù không ghi flash/eFuse, các thao tác đó vẫn mở
Serial và có thể reset vào ROM, xung đột Bridge và làm mất HX711 RAM state.
Không có eFuse evidence sẵn thì gate MISSING; không có command file-only nào
thay thế được phép đo/đọc trạng thái phần cứng này.

## 4. Serial production: hoàn thiện kế hoạch, chưa thực hiện maintenance

Bridge đang dùng Serial theo owner report gần nhất. Dùng readonly commands để xác
định user-vs-system unit, MainPID, executable, stable USB identity và các holders.
Scope/unit không rõ hoặc fuser không đủ quyền thì UNKNOWN, không kết luận port free.

Kế hoạch cần USER duyệt trước một phiên thao tác về sau:
1. Chốt host/port/board/transport, tool path/version; ghi original unit/state,
   binary/ExecStart/config và current telemetry/HX RAM observations đã có.
2. Chốt maintenance window cho **ESP32 Serial**. Flash không thể đồng thời với
   Bridge giữ cùng port; AI/FastAPI/Flutter có thể giữ nguyên, ESP telemetry sẽ
   mất tạm thời. Phiên hiện tại không dừng Bridge hoặc chuyển USB.
3. Trong scope riêng đã được duyệt mới chuyển port cho đúng một owner; phải kiểm
   không còn holder trước khi tool mở port. Không kill PID/stop nhầm scope.
4. Chốt người chịu trách nhiệm cleanup/handback trên success, failure, interruption
   và mất điện. Restore original state đúng scope; có manual recovery nếu trap
   không chạy. Không auto-start unit vốn inactive, không đổi enable/mask/config.
5. Post-window: trả Serial cho consumer đã review và kiểm identity/health. Current
   production Bridge4096 không chứa được kit reports4280–4295 bytes; candidate
   ARM64 PASS không đồng nghĩa đã deploy. Phải chốt đường kiểm telemetry/cutover
   riêng; không mở thêm terminal Serial khi Bridge đang giữ port.

`tools/bridge_flash_session.sh` là helper **read-backup** cũ, có stop/reset khi
execute, không phải read-only inventory hoặc APP-flash wrapper. Không chạy lại.

## 5. Khả năng khôi phục firmware cũ

Local image `web_hardware/rollback_original_app_00010000.bin` và A/B off-device đã
có proof bytes. Firmware gốc là HX711_REFERENCE. Local extraction PASS không phải
hardware restore PASS; không yêu cầu thử restore chỉ để hoàn thiện pre-flash gate.

Recovery readiness còn cần:
- File sensor và original rollback đúng hash có sẵn trên **flash host được chọn**;
  có đường truy cập nếu mạng/USB disconnect. Backup16MB lưu off-device không bị ghi đè.
- Tool/interpreter phù hợp ESP32-S3 và version syntax; Python3.6.9 native-build host
  không tự chứng minh esptool4.8.1 chạy được (4.8.1 cần Python>=3.7; Windows3.11 là
  môi trường đã dùng trước đây). Không auto-install/upgrade tool.
- BOOT/RESET/USB-UART recovery route còn khả dụng theo eFuse/security thực; owner
  có khả năng tiếp cận vật lý và nguồn ổn định.
- Giữ bootloader0x0, table0x8000, NVS0x9000, otadata0xe000 nguyên vẹn trong eventual
  APP-only plan. Nếu actualbank/layout khác dự kiến thì dừng, không đổi bank/table
  để ép boot. App1 erased không bảo đảm tự quay về firmware cũ.
- Restore app không hồi sinh RAM tare/calibration. Chấp nhận mất RAM state phải
  được USER xác nhận riêng; HX static PASS vẫn giữ, persistence/closed-loop UNKNOWN.
- Restore original HX firmware có thể trở lại lỗi unsupported-mode của Bridge cũ;
  đó là known compatibility state, không suy restore firmware = valid telemetry.

## 6. Bằng chứng còn thiếu và điều kiện mở lại quyết định

Gửi **existing** native result, latest boot/partition lines, decoded security flags,
readonly unit/PID/USB/holder output, host/tool và recovery-file availability,
ảnh/số đo ECHO13/17/15/10 đã có, cùng xác nhận load isolation và RAM-loss scope.
Không làm lại native tests/HX/static hoặc sensor tests đã PASS.

Installation complete được chấp nhận. Hiện chưa nhận số đo peak ECHO<=3.3V từng kênh,
protection details hoặc xác nhận servo/pump/buzzer power isolated cho flash/boot.
LOCKED là software policy, không phải physical OFF evidence. DMM trung bình xung
không tự chứng minh peak; ưu tiên existing measured evidence/phương pháp đã review.

Chỉ khi mọi blocking gate trong `GO_NO_GO.json` có evidence phù hợp, mới đánh giá
GO và **đề xuất một bước APP-only flash có giám sát** bằng đúng sensor image/hash,
đúng bank đã xác minh, write/verify/rollback plan và Serial handback đã duyệt.
Phiên này không phát hành executable write/erase commands, không ngắt Bridge,
không flash/Serial/camera/actuator access. Servo/pump LOCKED; manual buzzer disabled.
