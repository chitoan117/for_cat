# Command reference — chuẩn bị cho các gate SAU, không chạy ngay

Bước hiện tại: chỉ inventoryreadonly rồi báo kết quả. Các placeholders phía dưới
phải thay bằngMAC/COM thực saukhi đãreviewpower/status/ROM; không sao chép chạy
nối tiếp. Không có APPwritecommand trong tài liệu này.

## Windows: lập session mới, không mởdevice

Sau khi venvPython3.11/esptool4.8.1 riêng đãđượcownerreview:

```powershell
$kit = 'D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029'
$py = "$kit\recovery_workspace\env-esptool481\Scripts\python.exe"
$session = "$kit\recovery_workspace\NEW_snapshot_session"
& $py -B "$kit\tools\backup_recovery.py" plan --session "$session" --device-id 'ACTUAL_MAC' --port COMn --tool-python "$py" --chunk-size 0x10000
```

Tool refuse invalidMAC/COM hoặcexistingdirectory. No read được thực hiện bởiplan.
MẫuMAC hợp lệ là6octets hex từ ROMread_mac/flash_id, không làvídụtesthoặcportname.

## Xem đúngmột read request trước khi ownerthực hiện

```powershell
& $py -B "$kit\tools\backup_recovery.py" read --session "$session" --index 32 --pass a
```

Đây vẫn PLANONLY, index32=0x200000 khi chunksize64KB. Owner chỉ thêm explicit
`--execute --confirm OWNER_READ_ONLY_BACKUP --rom-ready-ack` khi đã tớiGate4,
đúngboard trongROM/powerisolated. Không tựstopJetsonservice từWindows; USBboard
đãđượcchuyển một cáchcógiámsát, monitorWindowskhác đóng. No write/erase có trongtool.
Passb là lầnreadđộc lập, khôngcopyfilea. `--attempt 2` dùngNEWfiles nếuretryđược
ownerquyếtđịnh; khôngxóa partialtry1. Pilotreview index0/32/255 trướcfullcoverage.

## Offlineassembly/receipt vàlayoutinspection

Chỉ sau khi mọichunk cóđủ2successfulmatchingreads và ROMcontinuity đãreview:

```powershell
& $py -B "$kit\tools\backup_recovery.py" assemble --session "$session" --output "$kit\recovery_workspace\NEW_full16MB.bin" --receipt "$kit\recovery_workspace\NEW_backup_receipt.json" --owner-reviewed-rom-continuity
& $py -B "$kit\tools\backup_recovery.py" inspect "$kit\recovery_workspace\NEW_full16MB.bin"
```

Assembly không đọcboard; khôngpad hoặc overwrite. Output/receiptphảiNEW; nếu
incomplete/gap/differentpasses/mismatchMAC/hash thìrefuse. Layoutinspection không
tựchọnbootbank hoặc cho phépflash. Gửireceipt/table/bootreview choChatGPT/OpenCode
để đượcgiao bước tiếp; chưa cấpAPP-onlycommand khi thiếu cácđiềukiện này.

## Jetson: inventory file-only nếu đãcopytools

```sh
python3 /PATH_TO_COPIED_TOOLS/backup_recovery.py inventory /home/toan/for_cat/evidence/esp32_backup_20261029
```

Đây là stdlib-only, không import esptool/serial hoặcđổiservice; coretoolcompatible
Python3.6 cho inventory/analysis. Actualreader thìrequireWindows+esptool4.8.1 và
không dùngPython3.6 để cài/run package4.8.1. Không cần copytool cho bướcfirst:
có thểpastereadonlyMobaXterminventory command được giao trongchat.
