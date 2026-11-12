# Backup acceptance + Web hardware diagnostic preparation

Current milestone handoff: **`TELEMETRY_COMPATIBILITY_HANDOFF.md`** và
`PRE_FLASH_GATES.json` (ARM64 native NOT_RUN, APP flash NO-GO).

Mode: OpenCode chuẩn bị/file-only → USER tự chạy sau review → báo evidence.
Khôngflash/reset/COM8/webcam/service/network/productionDB hoặc actuator action.

## 1. BACKUP A/B ĐÃ PASS — không đọc lượt3/không lấy LASTEXITCODE cũ

Đã trực tiếp đọc **readonly** hai filecompleted:
- `D:\for_cat\ESP32_FULL_BACKUP_20261029\esp32s3_flash_16mb.bin`
- `D:\for_cat\ESP32_FULL_BACKUP_20261029\esp32s3_flash_16mb_B.bin`

Mỗi file16777216bytes, cùngSHA256
`56a04d58bd8063e64f6b043a6b91d2d412c64d75e563ee58d81a83666d9a8e16`.
Đối chiếuownerSHA đúng, mtime/size khôngđổi sauhash. `accepted_backup_pair.json`
ghi ownercompletionmarkers vàdirectfilehash; không bịaMAC/oldexitlog chưađượccungcấp.
Đây làreceiptkind mới rõprovenance, đượcsharedvalidator hỗtrợ màkhông épđọc lại.

## 2. Actuallayout/OTA/app/rollback

Primary analysis: **`backup_and_contract_review.json`**. File
`actual_backup_layout.json` là bản exploratory đầu; khiđó seq0 bị đánhconservative
unusable. Latestanalysis đãfix theoIDFCRC/uint32sequenceconvention; dùngprimaryreport.

| Region | Actualoffset | Size / kếtquả |
|---|---:|---|
|Bootloader|0x0000|19968usedbytes, S3chip9/16MB/DIO, checksum+appendedSHA valid|
|Partitiontable|0x8000|MD5-valid, uniqueidentified, khớptable củasensorbuild mới|
|NVS|0x9000|0x5000; không plannedwrite/erase|
|otadata|0xe000|0x2000; hai copies tại0xe000/0xf000|
|app0/ota_0|0x10000|0x640000; validimage381984bytes|
|app1/ota_1|0x650000|0x640000; entirepartitionFF, khôngvalidappheader|
|spiffs|0xc90000|0x360000|
|coredump|0xff0000|0x10000|

App0usedimageSHA:
`820cdeecde2c4af7b7b2c7f4a1090a3b5c775809886df662522a44e83a4b9826`.
Đúng knownoldHX711_REFERENCEimage, cóliteralHX711_REFERENCE; khôngphải newquadsensor
a6ad… hoặc bảnquad73b4… ownerđãcopy trướcđó. BootloaderSHA đúng
`31b3c1be45dc5a76aa85c82540d6787b675e711eaf11021a5eea7e36f469c6de`.

OTAcopy0:seq1/stateUNDEFINED/CRC0x4743989a valid→standardsequencecandidate app0.
Copy1:seq0/stateUNDEFINED/CRC0xffffffff matches computed; unsignedseq-1 mapsapp1.
StandardIDF max-validseq choosescopy0, app0valid/app1erased củngcốcandidateapp0.
**Metadata-derived selection làapp0; actualRUNTIMEbank vẫnNOT_VERIFIED** vì chưa có
runningpartitionlog trongfileanalysis. Không suyphysicalbootSUCCESS hoặc eFuse/
securebootacceptance từCRC; candidate khôngthayactualrunningevidence yêu cầubởigate.

Đãextractlocalrollback **`rollback_original_app_00010000.bin`**,381984bytes,
SHA820c…3a4b9826, độc lậpkhông sửabackup. Đây làvalidoriginalapp recoveryartifact;
**restore trênhardware NOT_VERIFIED**. Phạmviapp0 khôngđụngNVS/otadata/table.
Không cấpflashcommand khi actualbank/electrical chưađượcreview. Full16MBbackup
và app-extract lưuoffdevice riêng; chưaautomaticrestore/erase. RAMcalibration không
nằmtrongbackup và khôngđược hồi sinh bởirestoreapp.

## 3. Những phầnđãcó vàgap được review bằngsource/data thật

| Thànhphần | Đãcó | Gap/trạngthái hiện tại |
|---|---|---|
|C++TensorRT CAT/DOG/NONE|Framedstdout/soleStateTapwriter, frameID/epoch/freshness|ActualARM64/camera runtime mới chưa deploy/verify|
|Livecam|Singlecapture, previewworker/latest1, FastAPIMJPEG, existingFlutterLiveCameraPanel|Không mởcamera thứhai; actualstream phụthuộccutover riêng|
|FOOD_ROI|OptionalC++ROI, FULL_FRAMEdefault, sameframeJPEGoverlay|ChỉFOOD_ROI trongextension; config phảireview/matchactualproducer, khôngtrayproof từstatus|
|4ultrasonic|Canonical4IDs/pins, Bridgeextension/parser, FlutterUltrasonicState|**Kit rawJSON4280–4295bytes > old4096limit** nêncurrentbridge sẽdrop|
|PIR|Firmwarewarmup/qualifiedvalid/stable|Currentbridge chỉforwardrawmotion; currentAPI/UI không cóqualifiedfields|
|HX711|StaticphysicalPASS/accuracyaccepted, raw+hostcalibratedview|Currentbridge bỏfirmwaregrams; currentRAM/persistenceunknown, không tựrecal/weightretest|
|JSN1waterlevel/JSN2TBD|Hai distances độc lập|Chỉ JSN1 được tính percent với measured geometry; JSN2 giữ TBD/null%|
|BuzzerGPIO2ACTIVE_LOW|Isolatedserialbench antoàn đãcó|Sensorimagea6ad…không cóGPIO2manualdriver; currentBridge khôngmanualRPC; Webtest khôngđượctriggerDOGwarning thaythế|
|Logs/auth|Existingevents/VIEW_CAMERA/sameoriginHTTPS|Hardwaretest routes/journal riêng chưa đượcmount/deploy|

Không WATER_ROI, không AI drinking hoặcOWNER_CATidentity được thêm. OldPython
legacyconfig khác có thể cònfields, nhưngkhôngđượcsửdụngbởinewdiagnosticview.

## 4. Code đãchuẩnbị, KHÔNG thayproduction/release_candidate_v2

### Bridgecandidate riêng

`bridge_candidate/` copycurrentauthoritativesource, beforehash ở
`bridge_source_reference.json`. Candidate sửa parser/channel validation, Bridge
lifecycle/default PLAN và thêm shared session/file replay tests:
- parser/framerbounded8192bytes choactualkitframes; vẫnrejectoversize, duplicate
  keys, invalidschema, modekhácdiag_current_hardware và mọiunsafeactuatorstate;
- qualifiedPIRfields cótypedvalidation, legacykhôngcó thìexplicitunavailable;
- forwardedFWgrams chỉread-onlyobservation vớicalibrationID/sampleage, không thay
  canonicalcalibration/arbiter/feedauthority; kitfirmwareidentityforwarded.

Windows đã local-build pinned json-c0.17, **C++14 parser 12 test groups và session
17 checks PASS** bằng native executables. Toàn bộ POSIX Bridge/ARM64 vẫn NOT_RUN.
Trướcdeployowner phải nativebuild trênNano vàoNEWpath,
run parsercompatibilitytest vớifullactualkitJSON (not truncated), rồicontrolled
single-serial-owner rollout; no feed/pumpTX, `--dog-warning 0`. Không updateRCv2.

### OptionalFastAPIextension

`diagnostics.py` cungcấp `mount(app, diagnostic_log_path, config, ...)` choappfactory
hiệncó; currentproduction `app.main` không sửa, endpointnày hiệnchưa tồn tại live.
Mount vàoNEWstaging/sandbox saubackup/deployreview; logDBphảikhác canonicalDB.

Routesprepared:
- GET `/api/v1/hardware-diagnostics/status` và `/events`: VIEW_CAMERA.
- GET `/events/export`: VIEW_CAMERA, bounded256 JSON export, physical_pass=false.
- POST `/observations`: CONTROL_SYSTEM, boundedUSER_OBSERVED, khôngautoPASS.
- POST `/buzzer-test`: CONTROL_SYSTEM +explicitconfirm +freshREALlink +trusted
  qualifiedmanualfirmwarecapability +explicitexecutor. **Default409/disabled**.

Waterlevel: chỉJSN1, ownerreviewedmount/min/max/full/empty, top-downmeasured
distanceorientation full<empty; invalid/stale/outsidegeometry→null, khôngclamp để
giả0/100 và khôngpumpaction. `diagnostic_config.example.json` đểnullgeometry;
sampletests75% làSYNTHETIC, không actualtankconfig. JSN2 là TBD, không tính %.
PIR khôngcóqualifiedfields→UNKNOWN, khôngfallbackrawtrue. HX cócurrenthostvalue
hoặctypedfreshFWobservation mớishownumber; otherwise null, staticPASSbadge vẫn có.
FOOD_ROI config chỉmô tảproposedsetting, không tựenableactualC++ROI/membership.

### Flutterpanel táisửdụngUI cũ

`flutter/hardware_diagnostics_panel.dart` optionalpanel, dùngprimary
`feeder_demo` package/pathdependency vàexistingAppCard/LiveCameraPanel. Không
redesign hoặc mountvàoprimaryproductionUI trongtasknày. Có4sensorrows, waterlevel,
qualifiedPIR,HXauthority/staticPASS, connection/AI/FOOD_ROI, observationlog,
buzzerbuttoncapability-gated+ownerdialog.404khiextensionchưadeployhiệnexplicit,
khôngmockfallback; failures clearstaledata; sameoriginHTTPS (httploopbackdemoonly).
Khôngsecret/producer token ởfrontend; sourceSIM khôngđượctestrealbuzzer.

### Buzzerlive còn BLOCKED — không giả feature đãcó

KhôngrealUARTexecutor đượcimplement/inject; KHÔNGcóGPIO2capability trongcurrent
sensorfirmware. Fakeexecutor chỉtestcontractfixed2x200ms/gap200ms, serverbudget/
cooldown/idempotency/unknownACKconsumedidentity; actualfutureMCUphải tựenforce
600msauto-off/60scooldown/3testsboot, không dựavào APIpolling/timer.
Futurequalifiedmanual-onlyprofile+singleownerbridgeRPC cần được chuẩn bị và
nghiệmthu riêng. Không bậtcat/dogautomaticwarningprofile đểlàmmanualWebtest.
Existingserialbuzzerbench làquytrìnhriêng, khôngchạy cùngsensorbridgeprofile.
Servo/pump khôngcócontrolroutes, giữLOCKED. AcceptedstaticHXkhôngtựauthorizefeed.

## 5. Verification vàtrìnhtự owner

Source/tests trong`web_hardware`; `verify.py` chạyfocusedASGI/fakes vàFlutterharness
offline(packagecache), khôngPIO/buildfirmware/nativebridge hoặcdevice/service.
`result.json`, `backend_tests.log`, `flutter_tests.log`, `flutter_analyze.log` là
evidence cuối. SoftwaretestPASS không làWebphysical/camera/buzzer PASS.

Kết quảcuối: **31 backend/file/ASGItests PASS**, **8 Fluttercontroller/widgettests
PASS**, Flutteranalyze**Noissues**. Sharedkittools**58tests PASS** vìreceipt/
OTAinspect cóthayđổi. Khôngre-runfirmware/nativebench hoặcphase1–5regression.
Fakebuzzerexecutor khônglàrealUART; toàn bộ C++Bridge vẫn require target compile.

Khi tíchhợp panel, dùngmột hardware-test view rõràng, khônghiện legacyrawPIRtile
như qualifiedmotion bên cạnh panelmới. Currentprimaryapp không được sửa/mount
trongmilestone này; futureUIintegration phải chọn đúngview vàqualifytạibundle mới.

Ownernextsteps theo thứtự, không chạy nối tiếp mùquáng:
1. Windowsfile-only kiểm `tools/verify_manifest.py` vàreadprimarybackupreview;
   không thirdFlashread/oldexitcode. GiữA/B và derivedrollbackởnơi antoàn.
2. Cungcấpexistingactualrunningpartition/bootlog và4ECHOelectricalevidence. Thiếu
   bank/voltage/rollbackreview thìBLOCKEDAPPflash; khôngreset đểthử mù.
3. Saugateđủ, owner cùngChatGPTreviewAPP-onlyplan bằngacceptedpairreceipt và
   runningpartitionreview; chỉuser tựflashsensorMỚI vàverify. Khôngerase/NVSwrite.
4. Sensorcaptureoneport: từngHC1/HC2/JSN1/JSN2/PIR theoSENSOR_TESTS; enableultras
   explicit sauelectricalreview. Portopen/reset cóthểđểsensorDISABLED, khôngsuy0cm.
5. TrướcWebrealtest: build/testcandidatebridge trêntarget riêng, mountbackend/router
   vàpaneltrongNEWqualifiedbundle, reviewTailscale/scopes/configgeometry. Controlled
   deploy/cutover doowner trongtaskriêng, mộtserial/camera/statewriter, khôngsửaRCv2.
6. ReadonlyGETstatus/events rồi app: comparephysicalreference/logticks, sourceREAL,
   fresh/invalid/missing đúng; JSNlevelnullnếuchưaconfig, PIRwarmupunknown, HXnull
   nếucurrentcalunknown. Livecamera/CAT/DOG/NONE/FOOD_ROIđúngsameframeJPEG.
7. BuzzerWebbutton phảidisabled trêncurrentfirmware. Chỉsauprofile/RPC/electrical
   gate riêng mới explicituser test; không thử servo/pump hoặc manualfeed quaWeb.

Không agentSSH, COM8, webcam, services hoặcGPIOđãđượctácđộng. Backup/layout/local
rollbackfile đãPASS; runtimebootbank/hardware-restore/sensors/buzzer/realWeb vẫn
NOT_VERIFIED. HXstaticđãaccepted, persistence vàclosedloop35g tiếp tụcNOT_VERIFIED.
