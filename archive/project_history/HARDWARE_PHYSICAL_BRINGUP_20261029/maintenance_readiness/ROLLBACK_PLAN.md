# Conditional APP-only proposal and rollback — OFFLINE preparation

Hiện APP FLASH NO_GO. Existing helper `tools/flash_prepare.py` chỉ kiểm backup/
layout/bank/RAM/power; nó chưa đủ để tựapprove security/eFuse. `app_plan.py` mới
bọc thêm currentreview/expiry/evidence-hashes/security/explicitbank và **không có
subprocess hay serial execution**. Dùng từ Windowsfullkit khi mọi gate đượcreview.

## Artifacts đã qualified
- New sensor400304bytes SHA`a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56`.
- OldHX711_REFERENCE381984bytes SHA`820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826`.
- A/B16MB SHA`56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16`.
Remoteold/newavailable+MATCHtheoUSER. Khôngthirdread hoặc erasebackup.

Existingtable: app0offset0x10000/size0x640000, app1offset0x650000/size0x640000
erased. Table0x8000, NVS0x9000, otadata0xe000, bootloader0x0 giữ nguyên. Current
runningoffset chưa VERIFIED; không fill0x10000 từdefault/OTAcandidate.

## Gate đóng trước khi có executable argv
SeparateFLASHapproval (khác readlease); currentESPboot/devicebinding; rawbootreview
boundbackuphash qua `physical_acceptance.boot_gate`; decodedsecuritypolicy chấpnhận
old/new; fourECHOevidence; loadisolation; RAMlossACK; actualexecutorport vàROMready;
reviewednostubwrite/verifypath; usableBOOT/RESET/recovery/Bridgehandback.
`flash_review.example.json` để null/false, không thaythế physicalmeasurements.
Reviewphải có tênngười duyệt, expiry<=24h, ít nhấtboot/securityevidencefilehashes.

CurrentavailabletoolWindows `.venv-esptool/Scripts/python.exe`4.8.1, importPASS3.14.3.
Hardwarepath chưaqualify. Jetson3.3.3 không được auto chọn làmflashexecutor. Source
củatool hỗ trợS3 không tự là boardexecutionPASS; fallbackPython3.11 riêng nếu
3.14dependencyerror chỉ sauUSERreview, không sửaenv đangdùng/systemPython.

Offlineusage (default chưa xuấtwriteargv):
```powershell
& 'D:\for_cat\.venv\Scripts\python.exe' -B 'D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029\maintenance_readiness\app_plan.py'
```
Sau khi gates cóproof và **phê duyệt flash riêng**, USER cóthể tạoNEWreviewfile và
chạy offlinegenerator với `--review ACTUAL_APPROVED_REVIEW.json --output NEW_PLAN.json`.
Nó kiểm receipt/fullbackuplayout, currentbootreview, exactartifacthash vàknownapp
descriptor secureversion; chỉversion0/unencrypted/unsigned/unrestrictedbranch.
Securitybật/khôngrõ/counterkhác0/bankkhác0x10000/toolkhác4.8.1 → refuseargv, reviewriêng.

Proposedargv khi đãđủgate: explicitchipesp32s3, reviewedport,115200,
`--before no_reset --after no_reset --no-stub`, write_flash`--no-compress`,
keepflashmode/freq/size, **một APPoffset duy nhất từactualreview**; verify_flash
sameoffset/file. Đây là ROM-readyworkflow, không auto reset, không full/factoryflash,
khôngtable/bootloader/NVS/otadatawrite. Chưa có executablewriteargv trong hồ sơ hiện tại.

## Khi app mới không boot/không đúng identity
USER dừng đểreview, không tựloopflash. Trong FLASHwindow đãduyệt và đúngROMroute,
conditionalrollback dùng **oldusedapp381984bytes** cùng actualbank và giữ các vùng
khác. Oldimage có metadata/checksum xácđịnhend; trailingbytesngoàiimage không được
coilà data/NVSrestore. Verifybytes, normalbootcapture, kiểmoldidentity vàhandback.
Rollbackfile đúngSHA không chứngminh SecureBoot/FlashEncryption acceptance hoặc
ROMaccess cònkhảdụng; đó là gate phải giải quyết trướcwrite.

App1erased không có automaticfallback. App-only rollback không sửa table/bootloader/
otadatađãbịthayngoàiplan, không hồiRAMtare/calibration; không tựfull16MBrestore hay
eraseNVS. HXstaticPASSgiữnguyên, persistence/closedloop35gNOT_VERIFIED. Oldfirmware
cóthểvẫnunsupportedmode vớiproductionBridge: restorefirmwarekhôngđồngnghĩa sensorPASS.

Mọi physicalrestore/flash thật là NEEDS_PHYSICAL_VALIDATION và USER thực hiện sau
reviewriêng. Không dùng serial_window READapproval để chạy write commands.
