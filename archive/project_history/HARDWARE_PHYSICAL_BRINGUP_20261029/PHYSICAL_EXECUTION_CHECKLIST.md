# Physical acceptance execution — chuẩn bị, chưa thực hiện

**A/B đã hoàn tất và accepted readonly:** mỗi file16777216bytes, SHA256 cùng
`56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16`.
Không còn backup đangchạy theoowner; đãphântích file thực, không mởCOM8/reset/
queryPID/service. Không yêu cầu lượt3 hoặc LASTEXITCODE cũ. Xemhandoff mới nhất
`web_hardware/BACKUP_AND_WEB_HANDOFF.md`. PID17448/10604 chỉ làlịch sử.

## Bản đồ tài liệu, không nhân đôi quy trình

| Nhu cầu | Tài liệu chính |
|---|---|
|Backup acceptance/recovery/rollback|`BACKUP_ACCEPTANCE_CHECKLIST.md`|
|SENSOR_TEST_PROCEDURE|Dùng bản cập nhật `SENSOR_TESTS.md`|
|ACTUATOR_SAFETY_PROCEDURE|Dùng bản cập nhật `ACTUATOR_PROCEDURES.md`|
|ESP32↔Jetson↔App|`JETSON_ESP32_INTEGRATION_TEST.md`|
|Raw evidence và biểu mẫu|`PHYSICAL_EVIDENCE_COLLECTION.md`, `FINAL_HARDWARE_REPORT_TEMPLATE.md`|

## Gate thực hiện từng bước nhỏ

| Gate | Điều kiện trước khi qua gate | Hiện tại |
|---|---|---|
|G0 Quản lý lượtA|Owner đãxácnhận A/Bcomplete vàterminalmarkers|PASS_OWNER_CONFIRMED|
|G1 AcceptA|Directreadonly exact16777216bytes vàownerSHA|PASS_FILE_INTEGRITY|
|G2 IndependentB|File riêng đủ16MB, fullSHAkhớpA/ownerSHA|PASS_FILE_INTEGRITY|
|G3 Probes/layout/OTA|ActualMD5table/imagechecksum/OTAdecoded PASS; oldJetsonprobes chưa đượccopyvề|PASS_LAYOUT / PROBE_COMPARISON_NOT_VERIFIED|
|G4 Bootbank/rollback|Actualrunningpartitionevidence boundfullSHA, compatiblelayout, recoverableapp extract|BLOCKED_PENDING_EVIDENCE|
|G5 Electrical|Power/commonGND,4ECHOpeakđãđo, safevoltage/loadisolation|NOT_VERIFIED|
|G6 Sensorimage|MỚIsha a6ad…ebb4b56, app-onlyplanđãreview, ownerflashverify/ID|NOT_EXECUTED|
|G7 5sensors|Từngkênh3repeats/reference, invalid/timeout/crosstalk, PIRmotion/no-motion|NOT_VERIFIED|
|G8 Actuatorbench|Separateimage, power/OFF/polarity/mechanicsproof, humanmanualcontrols|NOT_VERIFIED|
|G9 Integration|Đúngtelemetryprofile/protocol, bridgefresh, API/UIkhớp, nofeedauthority|NOT_EXECUTED|

**HX711 đã qua staticphysicalacceptance**, không thêmweight-retestgate: xem
`HX711_ACCEPTANCE.json`/`HX711_EVIDENCE_NOTES.md`. Persistence vàclosed-loop35g
vẫn làscope riêngNOT_VERIFIED, không phải lýdo đánhstaticFAIL hoặc yêu cầuoptimize.

Gatefail/ambiguous→BLOCKED, giữrawdata. Không ghép hai lượt khácsnapshot hoặc pad
vùngthiếuFF; không tự approve từACK/CONFIRM, CRC hoặcfileđủsize. Không vượt gate
bằng flashfactory/partition/boot_app0/eraseNVS hoặc đổi parser. Chưa cungcấplệnh
APP-only trongmilestone này; hostgenerator chỉ đưaplan khi gatefileevidenceđủ.

## Facts phải ghi đúng

- ChipS3rev0.2/flash16MB, CH343/COM8 làownerfacts. esptool báoEmbeddedPSRAM8MB là
  feature/packageinfo, không phải firmware allocation/testPASS. GiữNoVerifiedPSRAM;
  không đổi BOARD_HAS_PSRAM hoặc rebuild để thửPSRAM trongnhiệmvụ này.
- Firmware chính sensorSHA `a6ad4b3f6e21c1cfb0714f41f518ca90a75f031705a7bae5a2bb4fa99ebb4b56`.
  Bảncũ73b4…527d621 không dùng thay thế. Image/source/RCv2 không sửa.
- HXstaticrealtest5/10/20/35g/35g34.981g đãđượcownerchấpnhận; RETEST_REQUIRED=NO.
  CurrentRAMcalibrationUNKNOWN saureset, persistence/closedloopchưa xácminh;
  khôngnhập lại reference/tare, khôngbắt fullweightseries hoặc38g.
- OLED đã cóownerdisplayevidence; dẫnlinkcũ, khôngyêucầu tựđộngtestlại.
- Servo/pumpproductionLOCKED đến khi có từngsafetygate riêng; kit sensorimage
  không tựfeed, emitter/buzzer tests làprocedure riêng saubackup/electricalreview.

## Bước kế tiếp

Không đọcFlash lần3 hoặc lấy lạioldLASTEXITCODE. Review actualbackup/layout/
rollbackreport, cungcấpexistingbootpartition/electricalevidence; runtimebank và
ECHOpeak chưaverify nênchưaAPPflash. Webextension/candidate trongkit chưadeploy,
cóblockerbridge4KB/PIR/grams/buzzer đượcghi rõ, không épvalidframes giả.
