# Future USER maintenance window — READ only, not flash approval

## 0. Preflight / phê duyệt riêng
Hiện tại NO_GO. USER trước hết chạy metadata collect trong SAFE_READONLY_CHECKS.
Review evidence ECHO13/17/15/10 peak/protection, isolate servo/pump/buzzer external
loads, chấp nhận reset/USB mất HX RAMstate, nguồn ổn định, normalboot/handback route.
Không coi installation complete hoặc checkbox là voltage measurement.

Copy exampleapproval thành NEW file bằng USER, điền approver/UTCexpiry<=24h và
actualreviewedconditions; originalexamplefalsegiữnguyên. Scope chỉ boot_capture,
getsecurityinfo, efuse summary; `flash_authorized=false`. Metadata trước session
phải đúng USERunit/exe/stableUSB/solefreshPID, AI/APIactive, unitconfigkhôngpending.

## 1. Mở read-window trong phiên USER đã duyệt (CHƯA THỰC HIỆN)
```bash
WIN="$M/read_window_$(date +%Y%m%d_%H%M%S)"
python3 -B "$M/serial_window.py" --execute OWNER_APPROVED_READ_MAINTENANCE --approval "$M/ACTUAL_OWNER_READ_APPROVAL.json" --output "$WIN"
```
Script snapshot unit/config/output vàoNEWprivatefolder; checkPID/exe/USB/fuser lại,
chỉ stop `systemctl --user for-cat-esp32-bridge.service`. Không kill3989, không
stopAI/API, không đổiunitfile/enable/mask. Lease dừng tối đa30phút hoặc tới expiry;
INT/TERM/HUP/timeout đi qua handback, SIGKILL/powerloss không đảm bảo cleanup.
Script **không chạy tooldevice tự động**. Trong terminal thứ2 đặt cùng `M`, `WIN`,
`PORT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C85066678-if00`.

## 2. Actual running partition — normal app boot capture trước ROMread
```bash
python3 -B "$M/boot_capture.py" --execute OWNER_APPROVED_BOOT_CAPTURE --lease "$WIN" --seconds 60
```
Helper kiểm leaseopen/coordinatoralive/inactiveBridge/fuserfree/stableUSB. Nó mở
UART115200 RXonly, DTR/RTSfalse, exclusive, max2MiB, raw/chunktimestamps/SHA trong
NEWsubfolder. **UARTopen có thể glitch/reset**, dù không TX/reset tự động.
Chỉ sau USER đã duyệt, quan sát reset EN **normal boot, GPIO0khônghelddownload**
để bắt actual bootloader `Loaded app from partition at offset ...`. Ghi board/time
và thao tácreset thực. Nếu bootloader không inoffset và currentfirmware không có
`esp_ota_get_running_partition` status thì bankvẫnNOT_VERIFIED; không flash để thêm
status chỉ nhằm lấp gate. Không suy từOTA, ROMentry, read_flash hoặc retainedRAM.

Capture kết thúc và port đóng trước tool tiếp theo. Boot sauROMsecurityread có
thể khác sessionboot; cần normalbootcapture sau cùng để bind actualbank trướcflash.
Không dùng boot evidence cũ nếu có subsequentflash/boot-selection change.

## 3. Security/eFuse: toolcommands USER-only, mỗi lần một serialowner
Chỉ khi leaseopen, đúngapproval, Bridgeinactive, portfree; lưu logs vàoNEWpaths.
Các lệnh **mở Serial, vào ROM/reset**; chúng không ghi flash/eFuse nhưng không
passive. Nếu giữGPIO0đểvàoROM phải release trước normalboot handback.

Jetson3.3.3, explicitS3/ROM/no-stub, capturestdout+stderr+realexitcode:
```bash
test ! -e "$WIN/security_info.log" || exit 1
python3 -B -m esptool --chip esp32s3 --port "$PORT" --baud 115200 --before default_reset --after no_reset --no-stub get_security_info >"$WIN/security_info.log" 2>&1
RC=$?
printf '%s\n' "$RC" >"$WIN/security_info.exit"
```
Không dùng pipe/tee để vô tình lấy exitcode sai; chưa kết luậnPASS chỉ vìexit0.
3.3 inrawflags; cần đốichiếuS3definitions, không dùng ESP32/S2bitmapping nhầm.

```bash
test ! -e "$WIN/efuse_raw.json" || exit 1
test ! -e "$WIN/efuse_console.log" || exit 1
espefuse.py --chip esp32s3 --port "$PORT" --baud 115200 --before no_reset summary --format json --file "$WIN/efuse_raw.json" >"$WIN/efuse_console.log" 2>&1
RC=$?
printf '%s\n' "$RC" >"$WIN/efuse.exit"
python3 -B "$M/security_flags.py" --source "$WIN/efuse_raw.json" --output "$WIN/selected_security.json"
```
`espefuse.py` đã có theoUSER; kiểm `command -v espefuse.py` trướcwindow.3.3 không
nhận listfield sau summary; không thêm `--after` (không có), không `--debug`, không
burn/protect/check_error--recovery. FullJSONprivate có thể chứa keymaterial; chỉ
chia sẻ selectedflags + contextboard/MAC. Lệnhfail/permission/secure-mode restriction
→ giữrawerror, không chuyểnstub/burn/force hoặc suyflagmissing=disabled.

Nếu cần Windows4.8.1 thayJetson: phê duyệt route/USBtransfer riêng, không tự chuyển
USB lúc này. `python -m espefuse --chip esp32s3 --port ACTUAL_COM --before no_reset
summary SECURE_BOOT_EN SPI_BOOT_CRYPT_CNT SECURE_VERSION DIS_DOWNLOAD_MODE
ENABLE_SECURITY_DOWNLOAD DIS_DOWNLOAD_MANUAL_ENCRYPT DIS_USB_SERIAL_JTAG_DOWNLOAD_MODE`
là syntaxfieldfilter đã review4.8.1, không phải cho3.3. Không auto-installtool.

## 4. Review security policy, tuyệt đối chưa flash
Gắn decodedflags/MAC/boot/time vớiboard/backups. Secureversionimage mới0; yêu cầu
antirollbackpolicy của bootloader và countertươngthích với cảold/newimages. Secure
boot/encryption/restricteddownload bật cần qualified signing/encryption/recovery
flowriêng; app_plan không hỗ trợ nhánh đó. Flags/rawimage không tựapprove.

## 5. Handback, cả success và failure
ĐóngmọitoolSerial. Sau summary/no_reset, ESPcóthểvẫnởROM. USER thực hiện **approved
normalboot** bằng route đã review và capture/quan sát actualapp; không giảtoolclose
= appboot. Terminallease nhập đúng:
```text
NORMAL_APP_BOOT_AND_PORT_TOOLS_CLOSED
```
Finally kiểmUSB, unit/config và binaryhashkhôngđổi; chỉ startBridge vốnactive,
khôngrestartAI/API. Checkbounded Bridgeactive/newPID/soleowner và AI/APIsamePIDactive.
`handback.json` táchservice-restored khỏi appmode/validtelemetry: lỗiunsupportedmode
vẫncóthểtồn tại. KhôngdeployGCC75candidate trongwindow này.

Nếu busyport/configchanged/USBmissing/binarychanged/startfail → khôngforce; ghi
manual_recovery_required. USER kiểm holders và currentstate trước khi quyếtđịnh
manual `systemctl --user start for-cat-esp32-bridge.service` chooriginallyactiveunit.
Không cóautomatickill, configrestore hoặc auto-reset. Giữsnapshot/logkểcảrunFAIL.
Mấtđiện/SIGKILL: dựa vào snapshotoriginalstate, đóngtools, normalboot, xácminhUSB/
fuser rồi ownerrestoređúnguserunit; khôngchạy lạimaintenanceblindly.

Gửi snapshot, bootraw/context, securityselected/rawprivatehash+exitlogs, handback.
Phiên này kết thúc bằng reviewNO_GO/GO riêng, **không nối sang flash**.
