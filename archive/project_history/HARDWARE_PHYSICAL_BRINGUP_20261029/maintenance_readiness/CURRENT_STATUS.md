# Phase2 maintenance readiness — current status

**APP FLASH = NO_GO. Read-maintenance execution is not approved by this package.**
Không chạy lại native/HX/firmware tests đã PASS. Không sửa root590-file manifest,
GCC75_R1 checksums, backup, production hoặc prior review. Thư mục này là phần tiếp
nối kỹ thuật của `final_pre_flash_review`, có integrity riêng.

## Đã tiếp nhận / đối chiếu
- **OWNER_CONFIRMED:** ARM64 GCC75_R1 PASS, FOOD_ROI115, session17, replay26,
  fullGCC7.5compile PASS, exit0; existing result:
  `/home/toan/for_cat/hardware_diag_candidate_20261029/web_hardware/native_arm64_gcc75_r1_20261029_171958/result.json`.
- **OWNER_CONFIRMED:** SFTP29/29, Windows590 integrity, firmware mới400304bytes
  đã có trên Jetson staging với SHA256MATCH. Rollback381984bytes có trên cả2host.
- **VERIFIED trước đây, giữ PASS:** A/B16MB/SHA, matching partition table,
  rollback bytes và sensor image; HX static accepted. Không test lại.
- **VERIFIED offline trong phase này:** `.venv-esptool/Scripts/python.exe` là
  Python3.14.3/esptool4.8.1; đã import metadata, không connect thiết bị. Source4.8.1
  ESP32-S3/CLI được đọc trực tiếp; upstream3.3.3 source được đối chiếu.
- **OWNER_CONFIRMED, historical observation:** USER unit `for-cat-esp32-bridge.service`,
  binary `/home/toan/for_cat/.native-build/esp32/esp32_bridge`, MainPID3989 tại lần
  quan sát; stable by-id `usb-1a86_USB_Single_Serial_5C85066678-if00`→ttyACM0,
  Bridge sole holder. AI/API/BridgeACTIVE. PID phải refresh, không kill PID3989.
- **OWNER_CONFIRMED:** lắp đặt xong. Chưa có numeric ECHO evidence hoặc load-isolation
  acknowledgement trong message; không suy physical PASS từ assembly.

## NOT_VERIFIED / NO_GO
Actual running bank; decoded current security/eFuse/antirollback; ECHO13/17/15/10
peak/protection evidence; load isolation; HX RAM-loss ACK; reviewed maintenance
window/normal-boot/handback; actual flash executor/ROM recovery compatibility.
Firmware mới secure_version0; OTA candidate0x10000 không phải actualbankproof.
App1 erased; rollback file đúng hash không chứng minh restore hardware thành công.

## Scripts có sẵn
- `readiness.py`: defaultPLAN; explicit USER metadata collection, unit/output backup.
- `serial_window.py`: defaultPLAN; **future explicit approval only**, stop đúng USER
  Bridge, chờ operator, bounded handback. Không chạy device tools/flash tự động.
- `boot_capture.py`: defaultPLAN; future approved lease only, bounded RX-only,
  không auto reset/TX. UARTopen vẫn có thể glitch/reset.
- `security_flags.py`: trích flag từ existingJSON, không đọc eFuse/device.
- `app_plan.py`: offline gated argv generator; template thiếu gate không xuấtwriteargv.

Agent không dùng các execute flags. Chỉ kiểm thử logic mới bằng fake services,
fake holders, temporary files; không gọi systemctl/device commands trong tests.
Chỉ sau USER review mới copy riêng thư mục này lên staging. Production unchanged;
servo/pump LOCKED, manual buzzerDISABLED. Xem `SAFE_READONLY_CHECKS.md` cho bước kế tiếp.
