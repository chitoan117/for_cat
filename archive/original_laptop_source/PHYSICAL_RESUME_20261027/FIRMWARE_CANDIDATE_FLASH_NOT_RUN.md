# 4 ultrasonic candidate r2 — SOFTWARE_READY, CHƯA FLASH

## Phạm vi

- Source: `firmware_candidate/esp32/`, profile **diag_four_ultrasonic**.
- Candidate được tạo từ source tham chiếu Windows riêng; cached app của source tham chiếu có SHA256 `118bfb14cb8adc3fe435857c5dc463cad4874552bba072bab482584158c326a1`, khớp hồ sơ flash23/10.
- Đây không phải ROM readback mới. Không dùng staged firmware legacy trên Jetson làm nguồn flash và không ghi đè staged work.
- Production firmware hiện chưa được thay. RTC còn trong code tham chiếu bản cũ; **không coi GPIO16/17/18 là rảnh khi chưa đổi firmware**.
- Candidate r2 không init/poll/set RTC; RTC pins=-1. HC#1 12/13 CAT_APPROACH; JSN#1 14/15 WATER_LEVEL; HC#2 16/17 TBD; JSN#2 18/10 TBD.
- Các chân #2 vẫn **PROPOSED / NOT YET PHYSICAL VERIFIED**, wiring=null. Không tự đổi NOT_TESTED thành PHYSICAL_PASS.
- All echo acquisitions OFF khi boot; chỉ `ultra-select ... CONFIRM` mới bật một kênh. Multiplex chỉ sau khi từng kênh đã review; một echo acquisition tại một thời điểm, quiet80ms sau completion/failure và min500ms/kênh. Đây là thông số bench ban đầu, chưa là ngưỡng vật lý cuối.
- GPIO6/7 bị chặn, không PWM, không servo/pump/auto command. GPIO10 chỉ input trong profile mới. NVS/calibration codec không sửa.
- Candidate thêm **raw serial** `ultrasonic4`; parser production giữ hai kênh cũ và bỏ qua extension. **API/Flutter production chưa đọc raw #2 qua contract hiện có**. Sau flash, bench #2 cần capture raw có kiểm soát hoặc đợt tích hợp additive được review; không bịa số #2 trên app.
- Đã test candidate raw frame với parser C++ hiện có: cả boot disabled và synthetic HC#1 valid giữ invariant `valid => ACK`. Không đổi backend để nhận frame cũ.

## Bằng chứng software

Profile build thành công, 16MB/no-PSRAM/HW_SAFE/output0.
Native UBSan: scheduler65 assertions, real setup/loop28 assertions; bridge compatibility2 frames;
legacy native3351 assertions; canonical policy36, decision67, fake dispense9 checks.
Tất cả là SOFTWARE_READY / synthetic I/O; **không là thử servo/pump hoặc sensor thật**.
`changes.json`, `candidate.patch`, `deploy/manifest.json`, `platformio_build.log` và remote `firmware_candidate_r2/software_test_summary.json` giữ chi tiết.
Các attempt r1/link-command thiếu json-c được giữ trong evidence; r2 là candidate cuối.

## Lệnh flash thủ công — KHÔNG CHẠY NGAY

**BLOCKED** đến khi người dùng duyệt pin #2, RTC đã cách ly vật lý, ECHO đã có bảo vệ mức áp và common GND đúng;
servo/pump phải tách nguồn. Hiện runtime venv Jetson **chưa có esptool**, không cài vào production/AI venv.
Chưa chạy bất kỳ lệnh esptool/flash nào trong phiên này.

Các lệnh dưới dành cho **phiên flash riêng trên Jetson**, sau các điều kiện trên. Nếu dependency install/verify thất bại thì dừng,
không erase-all, không factory image, không ghi bootloader/partitions hoặc NVS để lách lỗi.

```sh
cd /home/toan/for_cat
E=/home/toan/for_cat/evidence/physical_resume_20261027_20261027T004813554339Z
F="$E/firmware_candidate_r2"
# Tạo tool venv riêng, không thay dependency production. Các lệnh này chưa được chạy.
/home/toan/for_cat/.venv/jetson-integration/bin/python -m venv "$E/flash_tool_venv"
"$E/flash_tool_venv/bin/python" -m pip install 'esptool==5.3.0'
P="$E/flash_tool_venv/bin/python"
"$P" -m esptool version
# Đối chiếu checksum firmware/bootloader/partitions với deploy/manifest.json trước.
sha256sum "$F/deploy/firmware.bin" "$F/deploy/bootloader.bin" "$F/deploy/partitions.bin"
```

**Khối ghi chỉ được người dùng chạy sau khi kiểm tra điện/pin và source/manifest:**

```bash
set -euo pipefail
systemctl --user stop for-cat-esp32-bridge.service
trap 'systemctl --user start for-cat-esp32-bridge.service' EXIT
# Xác nhận không còn serial owner khác. Không chạy miniterm song song.
if fuser /dev/ttyACM0; then echo 'BLOCKED: serial still owned' >&2; exit 1; fi
udevadm info --query=property --name=/dev/ttyACM0 | grep -qx 'ID_VENDOR_ID=1a86'
udevadm info --query=property --name=/dev/ttyACM0 | grep -qx 'ID_MODEL_ID=55d3'
udevadm info --query=property --name=/dev/ttyACM0 | grep -qx 'ID_SERIAL_SHORT=5C85066678'
"$P" -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub --after no-reset flash-id 2>&1 | tee "$E/manual_flash_identity.log"
# Identity/flash size phải khớp board được kiểm; sai thì DỪNG trước dòng write-flash.
grep -Eq 'Detected flash size:[[:space:]]*16MB' "$E/manual_flash_identity.log"
"$P" -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub --after no-reset verify-flash 0x0 "$F/deploy/bootloader.bin"
"$P" -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub --after no-reset verify-flash 0x8000 "$F/deploy/partitions.bin"
"$P" -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub --after no-reset read-flash 0x9000 0x5000 "$E/manual_nvs_before.bin"
# CHỈ APP 0x10000. Không dùng firmware.factory.bin hoặc upload target ghi nhiều vùng.
"$P" -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub --after no-reset write-flash 0x10000 "$F/deploy/firmware.bin"
"$P" -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub --after no-reset verify-flash 0x10000 "$F/deploy/firmware.bin"
"$P" -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 115200 --no-stub --after hard-reset read-flash 0x9000 0x5000 "$E/manual_nvs_after.bin"
cmp "$E/manual_nvs_before.bin" "$E/manual_nvs_after.bin"
sha256sum "$E/manual_nvs_before.bin" "$E/manual_nvs_after.bin"
```

Không chỉ nhìn exit của `tee` để kết luận identity đã đúng; phải đọc output và đối chiếu thiết bị trước dòng write.
Nếu mất owner exclusivity, boot/partition không khớp hoặc bất kỳ lỗi nào, **dừng và lưu nguyên log**.
Sau flash phải kiểm lại boot, safety, no-RTC, calibration metadata và từng kênh; chưa có physical kết quả từ lệnh này.
Không tự chạy4 kênh: lần lượt `ultra-select hc1 CONFIRM`, `jsn1`, `hc2`, `jsn2` trong phiên serial diagnostic độc quyền;
kiểm điện riêng từng kênh trước CONFIRM. Bridge RX-only không được thay bằng một serial writer cạnh tranh.
