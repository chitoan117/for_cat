# Flash preparation, backup và rollback — OWNER ONLY

**Recovery supersedes đường đọc đơn giản bên dưới:** xem `recovery/OPERATOR_HANDOFF.md`.
Owner đang dùngesptool3.3.3/Python3.6.9, đã cóCRC/headerrors và chưa cófullbackup.
Không chạy lại fullread mùquáng hoặc dùngpartfiles để suy đủ16MB. Writeplan hiện
bắt buộc `--backup-receipt` cófullcoverage/two-passmatch/hash; fileđủsize không đủ.

**Không dùng erase_flash, factorymergedbin hoặc auto-full-flash.** Agent không
flash/reset/đọcdevice. `flash_prepare.py` chỉ đọc localartifacts/backup và inargv.
Trước mọiROMread/reset/unplug lưu currentHXRAMstatus; full16MBflashbackup không
chứa RAMcalibration. NVS và RAM là hai thứ khác nhau.

## Địa chỉ được xác minh OFFLINE

Metadata SCons thực tế và binarypartitiontable khớp cho4profiles:
- ESP32-S3 chipID9, appheader16MB.
- bootloader:0x0000; partitiontable:0x8000.
- boot_app0:0xe000 (**OTADATA**, không viết trong defaultplan).
- app0:0x10000, size0x640000; app1:0x650000, size0x640000.
- NVS:0x9000/0x5000; otadata:0xe000/0x2000.

Không suy các offset này là existingflash của owner. Generator chỉ cung cấp
APP-onlywriteplan khi fullbackup16MB có verifiedtwo-passreceipt/running-partitionreview, ESP32-S3header và MD5-valid table giống
build, activebootbank được owner xác nhận và RAMloss/powerisolation acknowledgments.
Nếu partitionmismatch/bankUNKNOWN, dừngreview cùngChatGPT; không tự nạp partitions
để ép boot hoặc ghi boot_app0 làm đổi bank. Địa chỉROMentry/load virtual không
đồng nghĩa flashpartitionoffset; cần bootloaderpartitionlog/previousflash+boot
evidence được review, không điền0x10000 chỉ vì đây là default mới.

## 1. Port/tool và electrical trước backup

Owner ngắt nguồnservo/pump/buzzer, commonGND và echo-protection review, xác nhận
board/port/driver. Windows dùng COM hiện tại, không mặc địnhCOM8. Nếu nạp trên
Jetson, một serialowner và bridge phải pause; không mởscreen/picocom cùng lúc.
ROMflash-ID phải là esp32s3/16MB dự kiến; serialname `/dev/ttyACM0` không tự chứng
minh nativeUSB hay UART0route. RAMstatus lưu trước khi ROMtoolreset board.

```powershell
$py = 'D:\for_cat\.venv\Scripts\python.exe'
$kit = 'D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029'
& $py -B "$kit\tools\flash_prepare.py" --port COMx --backup "D:\OWNER_NEW_BACKUPS\esp32_before_kit_16MB.bin"
```

Lệnh trên **không execute gì trêndevice**. Nó in flash-ID/fullreadbackupcommands
và blockwrite khi backup chưa có. Dùng đúng toolPython/script hiện trong generated
argv (Windows PIOpython + esptool5.3.0 đãcheck); `--esptool-python`/`--esptool-script`
cho phép chỉ đúng installedtool nếu flash tạiJetson. Kiểm `version` trước, không
nâng systemPython3.6. `--esptool-style v4` đổi sang legacyunderscorecommand names
khi owner đang dùng toolv4. Không đoán là mọivenv đã có moduleesptool.

## 2. Backup trênJetson nếu owner chọn dùng esptool ở đó

Sau khi lưu HXstatus và reviewRAMloss/power, copytools vào thư mục riêng, kiểm
interpreter/moduleversion trước. `bridge_flash_session.sh` mặc địnhPLANONLY;
actualreadback chỉ khi owner gọi explicit:

```sh
export ESPTOOL_PYTHON=/home/toan/for_cat/.venv/jetson-integration/bin/python
# Nếu dùng esptool.py riêng: export ESPTOOL_SCRIPT=/ACTUAL/INSTALLED/esptool.py
sh /home/toan/hardware-kit-20261029/tools/bridge_flash_session.sh
# OWNER: chỉ sau các preconditions ở trên:
# sh .../bridge_flash_session.sh --read-backup-owner-confirmed /home/toan/NEW_16MB_BACKUP.bin
```

Helper chỉ READFLASH, stop userbridge trướcopen, kiểmfuserkhôngerror, traprestore
originalservicestate cảkhifail/INT/TERM/HUP, kiểm16MB/hash. Không cówrite/erase path.
Nếu service làsystemscope, helper này không áp dụng: dùng scope đã xác định và
explicit owner maintenance plan; không chạy sudo/stop scopekhác mù quáng.

Windows readbackup cũng vàoROM/reset; không có bridgeWindowsservice tương ứng
nhưng phải đóng mọi monitor và giữportexclusive. Copy fullbackup sang nơi an toàn,
lưuROMchip/MAC/flashID/outputtool/timestamp. Không ghi đè filebackup đã có.

## 3. APP-only plan sau backup có thật

Ví dụ dưới **chỉ** khi oldtable/bank đãreview và ownerbootbank thật là0x10000:

```powershell
& $py -B "$kit\tools\flash_prepare.py" --profile diag_four_ultrasonic --port COMx --backup "D:\OWNER_NEW_BACKUPS\esp32_before_kit_16MB.bin" --backup-receipt "D:\OWNER_NEW_BACKUPS\verified_two_pass_receipt.json" --running-partition-review "D:\OWNER_NEW_BACKUPS\reviewed_running_partition.json" --boot-app-offset 0x10000 --ram-loss-ack --external-actuator-power-isolated --extract-rollback-path "D:\OWNER_NEW_BACKUPS\original_app_partition.bin"
```

Tool kiểm hash từngartifact, MD5partitiontable, chipheader, flashsize/bounds và
không overlapNVS. Nó chỉ **extractlocalrollback** vàoNEWfile và inwrite/verifyargv;
không gọi esptool. Owner cùngChatGPT review `application_write_command` rồi mới
tự chạy. APP-only giữ bootloader/partitions/otadata/NVS hiện có. Flashsensorfirst,
khôngflashservo/buzzer image khi tải còn cấpnguồn. Nếu esptool boot/remap behavior
khác expected, dừng review, không dùngforce/erase/auto-port-selection.

Sauwrite, owner chạy generatedverify_flash/verify-flash rồi quan sátbootidentity,
profile/status và nguồnoutputOFF. ADCcalibrationRAM cũ đã mất, không tự phục hồi
pair reference để tuyên bố đạt. Mọicalibrationwrite/reboot validation là flow riêng.

## 4. Rollback

Default rollback là apppartition đã extract từ ownfullbackup, cùng confirmedbank.
Dừng/đóngserialowner, ngắt externalactuatorpower; owner chạy `rollback_command` và
`rollback_verify_command` do generatorin, không tự thay đổiNVS/table/bootbank.
Extract chứa đúng existingapppartition extent, không data/NVS. Kiểm bootfirmwareID
và restorebridge originalstate sauđó. Quay vềHX711_REFERENCE vẫn có thể0validtelemetry
với bridge chỉ chấpnhậndiag_current_hardware: đó là compatibilityblocker đãbiết,
không sửa parser đểgiảPASS. RAM tare/reference không hồi sinh nhờ apprestore.

Nếu bootloader/table đã bị thay ngoàiplan hoặc bank khôngkhớp, APP-only rollback
có thểkhôngđủ. Giữ nguyên fullbackup; dừng để ownerreview dedicatedrecovery.
Wholeflashrestore sẽ phục hồi cảoldNVS và có thể ghi đècalibration mới, nên không
có automaticfullrestore trongkit. Không xóa NVS hoặc erase_flash để vượt lỗi.

Trap/finally không chịuđược SIGKILL/powerloss. Owner biếtwas-active trướcsession,
kiểm `systemctl --user is-active for-cat-esp32-bridge.service`; nếu originallyactive
vàrestorefail, explicit owner `systemctl --user start ...` rồi kiểmstatus/journal.
Không tự khởi động bridge originallyinactive.
