# Operator handoff — phục hồi backup ESP32-S3 đang dở

> SUPERSEDED về completion: A/B đãcomplete vàdirectfileSHA/sizePASS. Không gọi
> read/planB/oldexitcode nữa. Currenthandoff ở `../web_hardware/BACKUP_AND_WEB_HANDOFF.md`;
> giữ nguyênphầnfailure/proberecovery cũ bên dưới làmhistory, không chạy lại.

OpenCode CHUẨN BỊ → USER thực hiện từng bước → USER báo kết quả. Chưa có fullbackup
16MB hợp lệ; chưa flash firmware mới. Chỉ thực hiện bước được giao, không chạy
nối tiếp các gate hoặc lấy runbook này làm autorun. Bước hiện tại chỉ inventory.

## A. Integrity/source và phân biệt firmware

Kit trước sửa recovery thực chạycheck: PASS196files, manifestSHA
`c9a8270ee05e4f7ca5d643baca95fd92a8b14b7ce303820c1761ff3659773f17`.
Đã đọc README/build_result/manifests/layout/SConsflags/flashplan vàbackup/rollback.

- **MỚI:** `artifacts/diag_four_ultrasonic/firmware.bin`,400304bytes,
  SHA256`a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56`.
- **CŨ owner đã chuyểnJetson:** SHA256
  `73b4b65fb09c798b42345a1a3544f6d93ce0835f5d6651c3f53a01735527d621`.
  Không chọn bảncũ làm firmwarekit hoặc overwritefilecũ.

Image mới:S3/16MB/no BOARD_HAS_PSRAM; MODE7/QUAD1/CURRENT1; ordinaryactuator0;
default4echoDISABLED, khôngGPIO2/6/7; RTCremoved. Buildoffsets0/0x8000/0x10000
chỉ mô tảimage mới, không chứng minh oldtable/activebank. Không rebuild firmware
vì recovery chỉ sửahosttools/docs. Sourceproduction/RCv2 giữ nguyên.

## B. Đọc lỗi hiện tại có nghĩa gì?

Owner báo esptool3.3.3/Python3.6.9: flash-ID16MB; stub64KBđầuPASS; ROM4KBđầu
khớp; ROM1MB/part_00/part_01mỗi1MBPASS; ROM0x200000 lỗi01090000 nhưngstub64/256KB
cùngvùngPASS; stub256KB0xFC0000→16MB lỗihead0x6F, stub64KB0xFC0000PASS.
Bridge đãrestoreactive saucácattempts (ownerreported, agent chưaSSHđọcfiles).

Các dấu hiệu phù hợp với vấn đề protocol/tool/USB/length/reset nhưng chưa đủ
log/trace/nguồn đểchốt rootcause. Không kết luận sectorhỏng, khôngerase/force/tăng
baud đểchữa. 64KB0xFC0000 không kiểm tra64KBcuối0xFF0000; flash-ID16MB cũng không
thay bằngchứng fullread. Giữ nguyên mọi partial/probe/log. Không ghép chúng rồi
padFF/0 thành16MB; filefailed có đủsize vẫn không được chấp nhận.

## Gate1 — inventory readonly, chưa reset/đổiUSB

Trên MobaXtermtoan, lấy tên/size/SHA256 cácfile trong
`/home/toan/for_cat/evidence/esp32_backup_20261029`, bridgeuser/systemstate và
USBproperties nếu cần. Không stop/restart, không serialopen. Gửioutput về review.
Tool `backup_recovery.py inventory EXISTING_DIR` chỉ đọc, không suy offset từtên.

**HX calibrationRAM hiệnUNKNOWN sau nhiềuROMreset.** Các sốtare/reference5–35g
trước là evidence lịch sử, không mặc định cònRAM. Không nhập lại hệ số/tare để
“khôi phục số đẹp”, không yêu cầu38g.

## Gate2 — currentstatus/electrical trước mọi ROMreset tiếp

Sau inventoryreview: xác định đúngservice scope/USBidentity/currentfirmware.
Nếu cầnstatusUART dùng `serial_evidence.py` readonly profilephùhợp, pause đúng
bridge vàmộtopen, finallyrestore/checkoriginalstate. Lưu mode/calibration-source,
raw/valid/invalid vàoffset/slope nếu thực sựđangcó; thiếu thìghi thiếu. Không mở
monitor thứhai hoặc chỉnhparser để biếnHX711_REFERENCE thànhdiag_current_hardware.

Trước unplug/reset: lưu currentlogs; ngắtnguồnservo/pump/buzzer, commonGND,
4ECHOprotection vàđo mứcHIGH thực≤3.3V. DMMaveragepulse/CONFIRM không làproof.
ReviewUSB/cable/nguồn vàUART0route: ttyACM0 không tựchứngminh nativeCDC haybridge.
ServopumpproductionLOCKED; không dùng backupROM/reset làm physicalbenchtest.

## Gate3 — esptool4.8.1 trên WindowsPython3.11 RIÊNG

Official4.8.1 yêu cầuPython>=3.7, có Windows/Python3.11 support; không tươngthích
Jetsonsystem3.6.9. Không nângPython/OSJetson hoặc cài vàoPIOvenv. Agent chỉreview
source, chưa cài4.8.1 hoặc đọc thiết bị. Owner thực hiện môi trường riêng SAUreview:

```powershell
$kit = 'D:\for_cat\HARDWARE_PHYSICAL_BRINGUP_20261029'
$envdir = "$kit\recovery_workspace\env-esptool481"
if (Test-Path -LiteralPath $envdir) { throw 'Chọn thư mục môi trường MỚI' }
py -3.11 -m venv "$envdir"
& "$envdir\Scripts\python.exe" -m pip install --isolated --disable-pip-version-check 'esptool==4.8.1'
& "$envdir\Scripts\python.exe" -c 'import sys, esptool; print(sys.version); print(esptool.__version__)'
```

Đây chưa phải bước được giao ngay. Version/importcheck không mởport. Chỉ khi
được hướngdẫn đổiUSB mới xác nhậnCOM/MAC/ROM S3rev0.2/16MB vàdriverWindows.
Không chọnCOMtựđộng, không lấyportname làmdeviceidentity. Venv/workspace riêng
không thuộc manifestbaseline; giữ4firmware vàoldprobes bất biến.

## Gate4 — pilot nhỏ, ROM ổn định, backup mới

Ưu tiênSTUB4.8.1,115200, explicitchipS3/flashsize16MB, không fallbackROM3.3.3.
Owner enterROMcókiểmsoát vàgiữapp không chạy/ghiNVS giữa reads. Tool dùng
before/after`no_reset`, nhưngUSBopen/close vẫn có thểreset tùyboard: cầnlog/owner
reviewROMcontinuity, không coiCLIflag làphysicalproof. Nếuappchạy giữa reads,
dừng vàlập newsnapshot/session.

`backup_recovery.py`:
- `plan`: NEWsession/MAC/COM/toolPython, default64KB=256chunks0..255/A+B, khôngIO.
- `read`: default inargv; actualWindowsread phải explicitexecute/confirm/ROMack,
  exact4.8.1, chỉread_flash. MỗiattemptNEW.bin/.log/.json, nooverwrite kểcảfailed.
  Exit0/exactsize/logMAC/S3 phảiđủ mớicomplete. Không cóerase/write/servicecommand.
- Pilot2lần ởindex0,32(0x200000),255(0xFF0000). Tail64KB mới thực chạm16MBboundary.
  Fail lặp lại thìSTOPreviewcable/power/driver, khôngretryvôhạn/tăngbaud. Có thể
  NEW16KB/4KBplan saureview, không tựfillmissingbytes.
- Pilotổn: hoặc đọc tiếp các64KB dưới giám sát, hoặc NEWplan full16MB với
  chunk-size0x1000000 rồi2fullreads. Fullreadfail giữpartial, không tin đủsize.
  Không toolnào tựchạy512reads; owner quyết từngrequest/batch saureview.
- `assemble`: offline,newoutput/newreceipt; toàn0..16MBcontiguous, A/Bđộclập
  khớp,tấtcảreturncode/size/hash/deviceid; gap/overlap/changeddata→refuse. Không
  padFF/0, khôngreusepart_00/01cũ mùquáng; failedfiles vẫn giữ.

Receipt làlocal consistencyproof, không physicalPASS/bootbankproof. Copyoldprobes
readonly về đểsooverlaps, ghi khácbiệt; không mixold/newbytes. ManyFFchunks có thể
erasedhợp lệ; không suywrap hay tựvá từhashlặp. Lưu plan/fullSHA/receipt/readlogs.

## Gate5 — actual partition/boot bank/rollback

`inspect FULL16MB_FILE` chỉ đọc, tìm actualMD5-valid tables vàappheaders thay vì
đoán oldtable0x8000/bank0x10000. Đối chiếu vớilayoutfirmwareMỚI. Nhiềucandidate,
tablekhác/chipkhác, chưa rõbootloader/bank hoặc signing/encryption: **DỪNG**.
OTAselection/revert/fallback không được suy từapp0label/ROMvirtualentry/newtable.
Inspector luôn active_boot_bankNOT_VERIFIED; cần ownerbootevidence đượcreview.

Giữfullbackup+receipt ởnơi antoàn, verifySHA saucopy. Approllbackextract phảiđúng
activepartition, cóverifyplan vàrestoreoriginalbridge. Không auto-fullrestore:
wholeflash ghioldNVS/otadata, không hồi sinh RAMtare/reference. Không xóaNVS.

Flashplan đãfixv4underscoreoptions/v5hyphens. Bâygiờ thiếu verifiedtwo-passreceipt
thì giữwriteplan, dùfileđủ16MB/header/tablecóvẻđúng. Receipt phải khớpfullSHA và
rangeSHA; layout/bank/RAMloss/powerisolation vẫn làgate riêng.

## Gate6 — chuyển đúngfirmware, chỉ SAU đủ điều kiện mới xin bướcAPP-only

SauGate1–5 vàreviewevidence, owner mới chuyểnappMỚI vàoNEWJetsonpath, không
replacebảncũ73b4... . SHAWindowsvàJetson phải
`a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56`.
Không dùngmergedfactory/bootloader/partitions/boot_app0 hoặc filecũ têntrùng.

**HiệnkhôngcungcấpAPP-onlyflashcommand:** fullbackup, actualtable/bank/rollback
chưa đượcnghiệmthu. Sau khigửireceipt/hash/boot/electricaldata, ChatGPT/OpenCode
mớireview vàtrả đúngmột bướcwriteAPP-only cógiám sát. Generatorchỉ PLAN, không
tựflash. Nếu vẫn chọnJetsonesptool3.3.3 đểwrite, compatibilityreview riêng;
không coi fixv4 tựápcho3.3.3.

## Gate7 — từngsensor vàevidence trả về

Sauflashverify/bootidentity đúng, theoSENSOR_TESTS: từngkênh, HC1 40→15→40,
HC2referencephùhợp, JSNngoàiblindzone (không mặcđịnh20cm), PIRwarm-up/qualified,
rồi multiplex. Invalid/noecho/outofrange phải nullkhông0. Không actuator.
Lưu rawbin/records/sessionconfig/time vàUSER_OBSERVED/ảnh/thước/voltagetrace,
giữcảfailedpoints. Bridgeconnected != validtelemetry != physicalsensorPASS.

Gửi về: inventoryoldfiles; currentfirmwarestatus/RAMsource; toolversion/MAC/COM/
flashID; pilotlogs/exitcodes; plan/fullsize+SHA/two-passreceipt; actualtable/bank;
rollbackhash/newappSHA; electricalphotos; sensorraw/observations; bridgebefore/
after/validtelemetrycount. Khôngpaste16MBbinaryvàochat. Khôngtựnângphysicalflags.

Officialsources đãreview (khônginstall hoặc dùngdevice):
- https://github.com/espressif/esptool/blob/v4.8.1/pyproject.toml
- https://github.com/espressif/esptool/blob/v4.8.1/esptool/__init__.py
